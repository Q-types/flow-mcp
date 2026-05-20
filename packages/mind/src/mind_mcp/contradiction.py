"""Contradiction detection and handling for Mind MCP v2.

Detects semantic conflicts between memories and manages resolution.
Prevents semantic drift by tracking conflicting claims with confidence scores.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Any

import numpy as np

from .database import Database
from .embeddings import EmbeddingModel, cosine_similarity
from .models import Memory, Conflict, ConflictStatus


# Similarity threshold for potential conflict detection
CONFLICT_SIMILARITY_THRESHOLD = 0.85

# Confidence delta for auto-resolution (new wins if > old by this amount)
AUTO_RESOLVE_CONFIDENCE_DELTA = 0.3

# Time delta for auto-resolution (new supersedes old if > this many days apart)
AUTO_RESOLVE_TIME_DELTA_DAYS = 30

# Salience reduction for conflicted memories
CONFLICT_SALIENCE_PENALTY = 0.2

# Negation patterns for conflict detection
NEGATION_PATTERNS = [
    r"\b(is not|isn't|are not|aren't|was not|wasn't|were not|weren't)\b",
    r"\b(does not|doesn't|do not|don't|did not|didn't)\b",
    r"\b(cannot|can't|could not|couldn't|will not|won't|would not|wouldn't)\b",
    r"\b(never|no longer|not anymore|stopped)\b",
    r"\b(incorrect|wrong|false|invalid|outdated|deprecated)\b",
]


class ConflictDetector:
    """Detects and handles contradictions between memories."""

    def __init__(self, db: Database, embedder: EmbeddingModel):
        """Initialize conflict detector.

        Args:
            db: Database instance
            embedder: Embedding model for similarity calculation
        """
        self.db = db
        self.embedder = embedder

    def check_for_conflicts(
        self,
        new_memory: Memory,
        new_embedding: np.ndarray,
        user_id: str,
        auto_resolve: bool = True,
    ) -> list[Conflict]:
        """Check if a new memory conflicts with existing memories.

        Args:
            new_memory: The new memory being stored
            new_embedding: Embedding vector of the new memory
            user_id: User ID to search within
            auto_resolve: Whether to auto-resolve clear conflicts

        Returns:
            List of detected conflicts
        """
        # Get existing memories with embeddings
        memory_data = self.db.get_memories_by_user(
            user_id=user_id,
            limit=500,
            min_salience=0.0,
        )

        if not memory_data:
            return []

        conflicts: list[Conflict] = []

        for old_memory, old_embedding in memory_data:
            if old_embedding is None:
                continue

            # Skip if same memory
            if old_memory.id == new_memory.id:
                continue

            # Calculate similarity
            similarity = float(cosine_similarity(new_embedding, old_embedding.reshape(1, -1))[0])

            # Check if similar enough to be potential conflict
            if similarity < CONFLICT_SIMILARITY_THRESHOLD:
                continue

            # Check for negation/contradiction patterns
            conflict_type = self._detect_conflict_type(old_memory.content, new_memory.content)
            if conflict_type is None:
                continue

            # Create conflict record
            conflict = Conflict(
                user_id=user_id,
                old_memory_id=old_memory.id,
                new_memory_id=new_memory.id,
                old_claim=self._extract_claim(old_memory.content),
                new_claim=self._extract_claim(new_memory.content),
                old_confidence=old_memory.salience,
                new_confidence=new_memory.salience,
                similarity_score=similarity,
                conflict_type=conflict_type,
            )

            # Attempt auto-resolution
            if auto_resolve:
                resolution = self._attempt_auto_resolve(conflict, old_memory, new_memory)
                if resolution:
                    conflict.status = resolution["status"]
                    conflict.resolution_note = resolution["note"]
                    conflict.resolved_at = datetime.utcnow()

                    # Apply salience penalty to losing memory
                    if resolution.get("penalize_old"):
                        new_salience = max(0.0, old_memory.salience - CONFLICT_SALIENCE_PENALTY)
                        self.db.update_salience(old_memory.id, new_salience)
                    elif resolution.get("penalize_new"):
                        new_salience = max(0.0, new_memory.salience - CONFLICT_SALIENCE_PENALTY)
                        self.db.update_salience(new_memory.id, new_salience)

            # Store conflict
            self.db.insert_conflict(conflict)
            conflicts.append(conflict)

        return conflicts

    def _detect_conflict_type(self, old_content: str, new_content: str) -> str | None:
        """Detect if two pieces of content are in conflict.

        Args:
            old_content: Content of existing memory
            new_content: Content of new memory

        Returns:
            Conflict type string or None if no conflict detected
        """
        old_lower = old_content.lower()
        new_lower = new_content.lower()

        # Check for negation patterns in new content
        for pattern in NEGATION_PATTERNS:
            if re.search(pattern, new_lower):
                # Check if the negation relates to something in old content
                # Extract key terms from old content
                old_terms = set(re.findall(r'\b\w{4,}\b', old_lower))
                new_terms = set(re.findall(r'\b\w{4,}\b', new_lower))

                # If significant overlap in terms and negation present, it's a conflict
                overlap = old_terms & new_terms
                if len(overlap) >= 2:  # At least 2 shared terms
                    return "semantic"

        # Check for direct contradictions (A is X vs A is Y)
        # Pattern: "<subject> is <value>" vs "<subject> is <different value>"
        is_pattern = r'(\w+)\s+(?:is|are|was|were)\s+(\w+)'
        old_matches = re.findall(is_pattern, old_lower)
        new_matches = re.findall(is_pattern, new_lower)

        for old_subj, old_val in old_matches:
            for new_subj, new_val in new_matches:
                if old_subj == new_subj and old_val != new_val:
                    return "factual"

        # Check for temporal contradictions (dates/times)
        date_pattern = r'\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b|\b(?:january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2},?\s+\d{4}\b'
        old_dates = re.findall(date_pattern, old_lower)
        new_dates = re.findall(date_pattern, new_lower)

        if old_dates and new_dates and old_dates != new_dates:
            # Check if they're referring to the same event
            old_terms = set(re.findall(r'\b\w{4,}\b', old_lower))
            new_terms = set(re.findall(r'\b\w{4,}\b', new_lower))
            if len(old_terms & new_terms) >= 3:
                return "temporal"

        return None

    def _extract_claim(self, content: str, max_length: int = 200) -> str:
        """Extract the main claim from memory content.

        Args:
            content: Full memory content
            max_length: Maximum claim length

        Returns:
            Extracted claim string
        """
        # Take first sentence or first max_length characters
        sentences = re.split(r'[.!?]', content)
        claim = sentences[0].strip() if sentences else content

        if len(claim) > max_length:
            claim = claim[:max_length-3] + "..."

        return claim

    def _attempt_auto_resolve(
        self,
        conflict: Conflict,
        old_memory: Memory,
        new_memory: Memory,
    ) -> dict[str, Any] | None:
        """Attempt to automatically resolve a conflict.

        Resolution strategies:
        1. Confidence delta: New wins if confidence > old by threshold
        2. Time-based: New supersedes old if > 30 days apart
        3. Both high confidence: Flag for manual review

        Args:
            conflict: The conflict to resolve
            old_memory: The existing memory
            new_memory: The new memory

        Returns:
            Resolution dict with status, note, and penalty flags, or None
        """
        confidence_delta = new_memory.salience - old_memory.salience
        time_delta = (new_memory.created_at - old_memory.created_at).days

        # Strategy 1: Significant confidence difference
        if confidence_delta > AUTO_RESOLVE_CONFIDENCE_DELTA:
            return {
                "status": ConflictStatus.RESOLVED,
                "note": f"Auto-resolved: New memory has higher confidence ({confidence_delta:.2f} delta)",
                "penalize_old": True,
            }
        elif confidence_delta < -AUTO_RESOLVE_CONFIDENCE_DELTA:
            return {
                "status": ConflictStatus.RESOLVED,
                "note": f"Auto-resolved: Old memory has higher confidence ({-confidence_delta:.2f} delta)",
                "penalize_new": True,
            }

        # Strategy 2: Significant time difference (newer information)
        if time_delta > AUTO_RESOLVE_TIME_DELTA_DAYS:
            return {
                "status": ConflictStatus.SUPERSEDED,
                "note": f"Auto-resolved: New memory supersedes old ({time_delta} days apart)",
                "penalize_old": True,
            }

        # Both recent and similar confidence - needs manual review
        return None

    def get_unresolved_conflicts(
        self,
        user_id: str,
        limit: int = 10,
    ) -> list[Conflict]:
        """Get unresolved conflicts for a user.

        Args:
            user_id: User ID to filter by
            limit: Maximum conflicts to return

        Returns:
            List of pending conflicts
        """
        return self.db.get_conflicts_by_user(
            user_id=user_id,
            status=ConflictStatus.PENDING,
            limit=limit,
        )

    def resolve_conflict(
        self,
        conflict_id: str,
        resolution: str,
        keep_memory_id: str | None = None,
    ) -> bool:
        """Manually resolve a conflict.

        Args:
            conflict_id: ID of conflict to resolve
            resolution: Resolution note/explanation
            keep_memory_id: Optional ID of memory to keep (other gets salience penalty)

        Returns:
            True if resolved successfully
        """
        # Get the conflict first
        conflicts = self.db.get_conflicts_by_user(
            user_id="",  # We don't know user_id, search all
            limit=1000,
        )
        conflict = next((c for c in conflicts if c.id == conflict_id), None)

        if not conflict:
            return False

        # Apply salience penalty if specified which to keep
        if keep_memory_id:
            if keep_memory_id == conflict.old_memory_id:
                # Penalize new memory
                new_memory = self.db.get_memory(conflict.new_memory_id)
                if new_memory:
                    self.db.update_salience(
                        conflict.new_memory_id,
                        max(0.0, new_memory.salience - CONFLICT_SALIENCE_PENALTY)
                    )
            elif keep_memory_id == conflict.new_memory_id:
                # Penalize old memory
                old_memory = self.db.get_memory(conflict.old_memory_id)
                if old_memory:
                    self.db.update_salience(
                        conflict.old_memory_id,
                        max(0.0, old_memory.salience - CONFLICT_SALIENCE_PENALTY)
                    )

        return self.db.resolve_conflict(
            conflict_id=conflict_id,
            status=ConflictStatus.RESOLVED,
            resolution_note=resolution,
        )

    def to_response(self, conflicts: list[Conflict]) -> dict[str, Any]:
        """Convert conflicts to API response format.

        Args:
            conflicts: List of conflicts

        Returns:
            API response dict
        """
        return {
            "conflicts": [c.to_dict() for c in conflicts],
            "count": len(conflicts),
            "pending_count": len([c for c in conflicts if c.status == ConflictStatus.PENDING]),
        }
