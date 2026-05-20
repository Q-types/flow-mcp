"""Decision tracking and learning for Mind MCP v2.

Implements a feedback loop that adjusts memory salience based on
decision outcomes. Good outcomes increase salience of memories
that contributed to the decision; bad outcomes decrease it.
"""

from __future__ import annotations

from typing import Any

from .database import Database
from .models import Decision


class DecisionTracker:
    """Track decisions and adjust memory salience based on outcomes."""

    def __init__(self, db: Database):
        """Initialize decision tracker.

        Args:
            db: Database instance
        """
        self.db = db

    def record(
        self,
        user_id: str,
        memory_ids: list[str],
        decision_summary: str,
        outcome_quality: float,
        outcome_signal: str = "agent_feedback",
        memory_scores: dict[str, float] | None = None,
    ) -> Decision:
        """Record a decision and adjust memory salience.

        This creates a feedback loop that helps Mind learn which
        memories are useful for good decisions.

        Good outcomes (+quality) increase memory salience.
        Bad outcomes (-quality) decrease salience.

        The adjustment is weighted by the memory's contribution
        (from memory_scores) if provided.

        Args:
            user_id: User ID
            memory_ids: List of memory IDs that influenced this decision
            decision_summary: Short summary of what was decided (no PII)
            outcome_quality: How well it worked (-1.0 to 1.0)
            outcome_signal: How outcome was detected
                - "user_accepted": User explicitly approved
                - "user_rejected": User explicitly rejected
                - "task_completed": Task finished successfully
                - "agent_feedback": Agent's own assessment
            memory_scores: Optional dict of memory_id -> retrieval score
                Used for weighted salience adjustment

        Returns:
            Decision object with salience changes recorded
        """
        # Validate outcome quality
        outcome_quality = max(-1.0, min(1.0, outcome_quality))

        # Calculate salience adjustments
        salience_changes = self._calculate_salience_changes(
            memory_ids=memory_ids,
            outcome_quality=outcome_quality,
            memory_scores=memory_scores,
        )

        # Apply salience changes
        for memory_id, delta in salience_changes.items():
            self.db.update_salience(
                memory_id,
                self._get_new_salience(memory_id, delta),
            )

        # Create decision record
        decision = Decision(
            user_id=user_id,
            memory_ids=memory_ids,
            decision_summary=self._sanitize_summary(decision_summary),
            outcome_quality=outcome_quality,
            outcome_signal=outcome_signal,
            salience_changes=salience_changes,
        )

        # Store in database
        self.db.insert_decision(decision)

        return decision

    def _calculate_salience_changes(
        self,
        memory_ids: list[str],
        outcome_quality: float,
        memory_scores: dict[str, float] | None = None,
    ) -> dict[str, float]:
        """Calculate salience adjustments for each memory.

        Adjustment formula:
        - Base adjustment = outcome_quality * 0.1 (max +/- 0.1 per decision)
        - If memory_scores provided, weight by normalized score

        Args:
            memory_ids: Memories that influenced the decision
            outcome_quality: Outcome quality (-1.0 to 1.0)
            memory_scores: Optional retrieval scores for weighting

        Returns:
            Dictionary of memory_id -> salience delta
        """
        if not memory_ids:
            return {}

        # Base adjustment (max 0.1 change per decision)
        base_adjustment = outcome_quality * 0.1

        changes = {}

        if memory_scores:
            # Normalize scores for weighting
            total_score = sum(memory_scores.get(mid, 0.0) for mid in memory_ids)
            if total_score > 0:
                for mid in memory_ids:
                    score = memory_scores.get(mid, 0.0)
                    weight = score / total_score
                    changes[mid] = base_adjustment * weight * 2  # Scale up for weighted
            else:
                # Equal weights if scores are zero
                for mid in memory_ids:
                    changes[mid] = base_adjustment / len(memory_ids)
        else:
            # Equal adjustment for all memories
            adjustment_per_memory = base_adjustment / len(memory_ids)
            for mid in memory_ids:
                changes[mid] = adjustment_per_memory

        return changes

    def _get_new_salience(self, memory_id: str, delta: float) -> float:
        """Calculate new salience after applying delta.

        Args:
            memory_id: Memory to update
            delta: Salience change

        Returns:
            New salience value (clamped to 0.0-1.0)
        """
        memory = self.db.get_memory(memory_id)
        if memory is None:
            return 0.5  # Default if memory not found

        current = memory.salience
        new_salience = max(0.0, min(1.0, current + delta))
        return new_salience

    def _sanitize_summary(self, summary: str) -> str:
        """Sanitize decision summary."""
        if not isinstance(summary, str):
            summary = str(summary)
        # Remove control characters
        summary = "".join(
            char for char in summary
            if char == "\n" or char == "\t" or (ord(char) >= 32 and ord(char) != 127)
        )
        # Limit length
        max_chars = 1000
        if len(summary) > max_chars:
            summary = summary[:max_chars]
        return summary.strip()

    def get_history(self, user_id: str, limit: int = 50) -> list[Decision]:
        """Get decision history for a user.

        Args:
            user_id: User ID
            limit: Maximum decisions to return

        Returns:
            List of Decision objects (newest first)
        """
        return self.db.get_decisions_by_user(user_id, limit)

    def to_response(self, decision: Decision) -> dict[str, Any]:
        """Convert decision to API response format."""
        return {
            "decision_id": decision.id,
            "user_id": decision.user_id,
            "memory_ids": decision.memory_ids,
            "decision_summary": decision.decision_summary,
            "outcome_quality": decision.outcome_quality,
            "outcome_signal": decision.outcome_signal,
            "salience_changes": decision.salience_changes,
            "created_at": decision.created_at.isoformat(),
        }
