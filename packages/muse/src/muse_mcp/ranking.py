"""Candidate ranking for Muse MCP.

Implements the value scoring formula:
V = w_u*U + w_n*N + w_f*F + w_a*A - w_r*R

Where:
- U = usefulness (0-1)
- N = novelty (0-1)
- F = feasibility (0-1)
- A = alignment with goals (0-1)
- R = risk/hallucination likelihood (0-1)
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import numpy as np

from .database import Database
from .embeddings import EmbeddingModel
from .models import Candidate, Fragment, WorkingObject, DEFAULT_VALUE_WEIGHTS


class CandidateRanker:
    """Scores and ranks candidates using the value formula."""

    def __init__(self, db: Database, embedder: EmbeddingModel):
        """Initialize candidate ranker.

        Args:
            db: Database instance
            embedder: Embedding model instance
        """
        self.db = db
        self.embedder = embedder

    def create_candidate(
        self,
        user_id: str,
        content: str,
        source_fragment_ids: list[str] | None = None,
        source_cluster_id: str | None = None,
        source_working_object_id: str | None = None,
    ) -> Candidate:
        """Create a new candidate from content.

        Args:
            user_id: User ID
            content: Candidate content
            source_fragment_ids: Fragment IDs this came from
            source_cluster_id: Cluster ID if from clustering
            source_working_object_id: Working object ID

        Returns:
            Created Candidate (not yet scored)
        """
        candidate = Candidate(
            user_id=user_id,
            content=content,
            summary=content[:200],
            source_fragment_ids=source_fragment_ids or [],
            source_cluster_id=source_cluster_id,
            source_working_object_id=source_working_object_id,
        )

        # Generate embedding
        embedding = self.embedder.encode_single(content)

        # Store in database
        self.db.insert_candidate(candidate, embedding)

        return candidate

    def score_candidate(
        self,
        candidate: Candidate,
        working_object: WorkingObject | None = None,
        existing_memories: list[dict[str, Any]] | None = None,
        weights: dict[str, float] | None = None,
    ) -> Candidate:
        """Score a candidate on all value dimensions.

        Args:
            candidate: Candidate to score
            working_object: Working object for alignment scoring
            existing_memories: Existing memories for novelty scoring
            weights: Custom weights (default: DEFAULT_VALUE_WEIGHTS)

        Returns:
            Scored candidate
        """
        w = weights or DEFAULT_VALUE_WEIGHTS

        # Score each dimension
        candidate.usefulness = self._score_usefulness(candidate.content)
        candidate.novelty = self._score_novelty(candidate.content, existing_memories)
        candidate.feasibility = self._score_feasibility(candidate.content)
        candidate.alignment = self._score_alignment(candidate.content, working_object)
        candidate.risk = self._score_risk(candidate.content)

        # Compute value score
        candidate.value_score = (
            w["usefulness"] * candidate.usefulness +
            w["novelty"] * candidate.novelty +
            w["feasibility"] * candidate.feasibility +
            w["alignment"] * candidate.alignment -
            w["risk"] * candidate.risk
        )

        candidate.evaluated_at = datetime.utcnow()

        # Update in database
        self.db.update_candidate_scores(
            candidate.id,
            usefulness=candidate.usefulness,
            novelty=candidate.novelty,
            feasibility=candidate.feasibility,
            alignment=candidate.alignment,
            risk=candidate.risk,
            value_score=candidate.value_score,
        )

        return candidate

    def _score_usefulness(self, content: str) -> float:
        """Score usefulness (0-1)."""
        content_lower = content.lower()

        # Positive indicators
        positive = [
            "solve", "fix", "improve", "optimize", "automate",
            "save", "reduce", "increase", "enable", "help",
            "practical", "actionable", "concrete", "specific",
        ]

        # Negative indicators
        negative = [
            "theoretical", "abstract", "vague", "maybe", "possibly",
            "interesting but", "nice to have", "someday",
        ]

        pos_count = sum(1 for term in positive if term in content_lower)
        neg_count = sum(1 for term in negative if term in content_lower)

        # Base score from indicators
        score = 0.5 + (pos_count * 0.05) - (neg_count * 0.1)

        # Bonus for specificity (has numbers, code, or technical terms)
        if any(char.isdigit() for char in content):
            score += 0.05
        if "`" in content or "```" in content:
            score += 0.05

        return max(0.0, min(1.0, score))

    def _score_novelty(
        self,
        content: str,
        existing_memories: list[dict[str, Any]] | None,
    ) -> float:
        """Score novelty compared to existing memories (0-1)."""
        if not existing_memories:
            return 0.7  # Assume moderate novelty if no comparison

        content_embedding = self.embedder.encode_single(content)

        # Find max similarity to existing memories
        max_similarity = 0.0
        for memory in existing_memories:
            mem_content = memory.get("content", "")
            if mem_content:
                mem_embedding = self.embedder.encode_single(mem_content)
                similarity = self.embedder.similarity(content_embedding, mem_embedding)
                max_similarity = max(max_similarity, similarity)

        # Novelty is inverse of similarity
        # High similarity (>0.8) = low novelty
        # Low similarity (<0.4) = high novelty
        novelty = 1.0 - max_similarity

        return max(0.0, min(1.0, novelty))

    def _score_feasibility(self, content: str) -> float:
        """Score feasibility (0-1)."""
        content_lower = content.lower()

        # Complexity indicators (reduce feasibility)
        complexity_terms = [
            "complex", "difficult", "challenging", "requires",
            "dependency", "integration", "coordination",
            "scale", "distributed", "real-time",
        ]

        # Simplicity indicators (increase feasibility)
        simplicity_terms = [
            "simple", "straightforward", "easy", "existing",
            "standard", "built-in", "library", "tool",
            "local", "single", "minimal",
        ]

        complexity_count = sum(1 for term in complexity_terms if term in content_lower)
        simplicity_count = sum(1 for term in simplicity_terms if term in content_lower)

        # Start at moderate feasibility
        score = 0.6 + (simplicity_count * 0.05) - (complexity_count * 0.08)

        return max(0.0, min(1.0, score))

    def _score_alignment(
        self,
        content: str,
        working_object: WorkingObject | None,
    ) -> float:
        """Score alignment with goals (0-1)."""
        if working_object is None:
            return 0.5  # Neutral if no goals to align with

        # Check alignment with goal
        content_embedding = self.embedder.encode_single(content)

        alignment_scores = []

        if working_object.goal:
            goal_embedding = self.embedder.encode_single(working_object.goal)
            alignment_scores.append(
                self.embedder.similarity(content_embedding, goal_embedding)
            )

        # Check alignment with desired outputs
        for output in working_object.desired_outputs:
            output_embedding = self.embedder.encode_single(output)
            alignment_scores.append(
                self.embedder.similarity(content_embedding, output_embedding)
            )

        if not alignment_scores:
            return 0.5

        # Use max alignment (if it matches any goal well, it's aligned)
        return max(alignment_scores)

    def _score_risk(self, content: str) -> float:
        """Score risk/hallucination likelihood (0-1)."""
        content_lower = content.lower()

        # Risk indicators
        risk_terms = [
            "risk", "danger", "security", "vulnerability",
            "external", "dependency", "api", "third-party",
            "complex", "untested", "experimental",
            "might", "could", "possibly", "theoretically",
        ]

        # Safety indicators
        safety_terms = [
            "tested", "proven", "standard", "validated",
            "secure", "safe", "reliable", "stable",
            "documented", "supported", "maintained",
        ]

        risk_count = sum(1 for term in risk_terms if term in content_lower)
        safety_count = sum(1 for term in safety_terms if term in content_lower)

        # Start at moderate risk
        score = 0.4 + (risk_count * 0.08) - (safety_count * 0.05)

        # Vague or overly broad claims are risky
        vague_terms = ["everything", "always", "never", "perfect", "revolutionary"]
        vague_count = sum(1 for term in vague_terms if term in content_lower)
        score += vague_count * 0.1

        return max(0.0, min(1.0, score))

    def rank_candidates(
        self,
        user_id: str,
        limit: int = 10,
        min_value_score: float = 0.0,
    ) -> list[Candidate]:
        """Get ranked list of candidates for a user.

        Args:
            user_id: User ID
            limit: Maximum candidates to return
            min_value_score: Minimum value score threshold

        Returns:
            List of candidates sorted by value score
        """
        return self.db.get_top_candidates(
            user_id=user_id,
            limit=limit,
            min_value_score=min_value_score,
            exclude_promoted=True,
        )

    def to_response(self, candidates: list[Candidate]) -> dict[str, Any]:
        """Convert candidates to API response format."""
        return {
            "candidates": [c.to_dict() for c in candidates],
            "count": len(candidates),
            "top_score": candidates[0].value_score if candidates else 0.0,
            "score_distribution": {
                "high": len([c for c in candidates if c.value_score >= 0.7]),
                "medium": len([c for c in candidates if 0.4 <= c.value_score < 0.7]),
                "low": len([c for c in candidates if c.value_score < 0.4]),
            },
        }
