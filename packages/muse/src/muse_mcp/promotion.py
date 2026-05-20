"""Promotion manager for Muse MCP.

Handles selective consolidation of ideas from Muse (working memory)
to Mind (long-term memory).

Promotion criteria:
- Useful more than once
- Connected to active project
- High novelty AND feasibility
- Captures a decision or mistake
- Captures a reusable pattern
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from .database import Database
from .models import Candidate, LifecycleState


# Promotion thresholds
MIN_VALUE_SCORE_FOR_PROMOTION = 0.6
MIN_USEFULNESS_FOR_PROMOTION = 0.5
MIN_NOVELTY_FOR_PROMOTION = 0.4
MAX_RISK_FOR_PROMOTION = 0.7


class PromotionManager:
    """Manages promotion of candidates to Mind MCP."""

    def __init__(self, db: Database):
        """Initialize promotion manager.

        Args:
            db: Database instance
        """
        self.db = db

    def check_promotion_eligibility(self, candidate: Candidate) -> dict[str, Any]:
        """Check if a candidate is eligible for promotion.

        Args:
            candidate: Candidate to check

        Returns:
            Dict with eligibility status and reasons
        """
        reasons = []
        eligible = True

        # Check value score
        if candidate.value_score < MIN_VALUE_SCORE_FOR_PROMOTION:
            reasons.append(f"Value score {candidate.value_score:.2f} below threshold {MIN_VALUE_SCORE_FOR_PROMOTION}")
            eligible = False

        # Check usefulness
        if candidate.usefulness < MIN_USEFULNESS_FOR_PROMOTION:
            reasons.append(f"Usefulness {candidate.usefulness:.2f} below threshold {MIN_USEFULNESS_FOR_PROMOTION}")
            eligible = False

        # Check novelty
        if candidate.novelty < MIN_NOVELTY_FOR_PROMOTION:
            reasons.append(f"Novelty {candidate.novelty:.2f} below threshold {MIN_NOVELTY_FOR_PROMOTION}")
            eligible = False

        # Check risk
        if candidate.risk > MAX_RISK_FOR_PROMOTION:
            reasons.append(f"Risk {candidate.risk:.2f} above threshold {MAX_RISK_FOR_PROMOTION}")
            eligible = False

        # Already promoted?
        if candidate.promoted:
            reasons.append("Already promoted")
            eligible = False

        return {
            "eligible": eligible,
            "reasons": reasons if not eligible else ["Meets all promotion criteria"],
            "scores": {
                "value": candidate.value_score,
                "usefulness": candidate.usefulness,
                "novelty": candidate.novelty,
                "feasibility": candidate.feasibility,
                "alignment": candidate.alignment,
                "risk": candidate.risk,
            },
        }

    def promote_to_mind(
        self,
        candidate: Candidate,
        mind_client: Any | None = None,
        memory_type: str = "semantic",
        reason: str | None = None,
    ) -> dict[str, Any]:
        """Promote a candidate to Mind MCP.

        Args:
            candidate: Candidate to promote
            mind_client: Mind MCP client for creating memory
            memory_type: Type of memory to create in Mind
            reason: Reason for promotion

        Returns:
            Promotion result
        """
        # Check eligibility
        eligibility = self.check_promotion_eligibility(candidate)
        if not eligibility["eligible"]:
            return {
                "success": False,
                "error": "Not eligible for promotion",
                "reasons": eligibility["reasons"],
            }

        # Determine memory type based on content
        if memory_type == "auto":
            memory_type = self._infer_memory_type(candidate)

        # Build promotion reason
        if reason is None:
            reason = self._generate_promotion_reason(candidate)

        # Create memory in Mind MCP
        memory_id = None
        if mind_client is not None:
            try:
                result = mind_client.remember(
                    user_id=candidate.user_id,
                    content=candidate.content,
                    memory_type=memory_type,
                    salience=candidate.value_score,
                    importance=candidate.usefulness,
                )
                memory_id = result.get("id") or result.get("memory_id")
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Failed to create memory in Mind: {str(e)}",
                }

        # Mark as promoted in Muse
        if memory_id:
            self.db.mark_candidate_promoted(
                candidate_id=candidate.id,
                memory_id=memory_id,
                reason=reason,
            )

        return {
            "success": True,
            "candidate_id": candidate.id,
            "memory_id": memory_id,
            "memory_type": memory_type,
            "reason": reason,
            "scores": eligibility["scores"],
        }

    def _infer_memory_type(self, candidate: Candidate) -> str:
        """Infer the best memory type for Mind MCP."""
        content_lower = candidate.content.lower()

        # Procedural: workflows, how-to, steps
        if any(term in content_lower for term in ["step", "process", "workflow", "how to", "procedure"]):
            return "procedural"

        # Preference: style, preference, like, prefer
        if any(term in content_lower for term in ["prefer", "style", "like", "want", "should always"]):
            return "preference"

        # Episodic: events, decisions, happened
        if any(term in content_lower for term in ["decided", "happened", "learned", "mistake", "success"]):
            return "episodic"

        # Default to semantic (facts, knowledge)
        return "semantic"

    def _generate_promotion_reason(self, candidate: Candidate) -> str:
        """Generate a reason for promotion."""
        reasons = []

        if candidate.value_score >= 0.8:
            reasons.append("high value score")
        if candidate.usefulness >= 0.7:
            reasons.append("highly useful")
        if candidate.novelty >= 0.7:
            reasons.append("novel insight")
        if candidate.feasibility >= 0.7:
            reasons.append("highly feasible")
        if candidate.risk <= 0.3:
            reasons.append("low risk")

        if reasons:
            return f"Promoted due to: {', '.join(reasons)}"
        return "Met promotion criteria"

    def get_promotion_candidates(
        self,
        user_id: str,
        limit: int = 10,
    ) -> list[tuple[Candidate, dict[str, Any]]]:
        """Get candidates ready for promotion with eligibility info.

        Args:
            user_id: User ID
            limit: Maximum candidates to return

        Returns:
            List of (candidate, eligibility) tuples
        """
        candidates = self.db.get_top_candidates(
            user_id=user_id,
            limit=limit * 2,  # Get more to filter
            min_value_score=MIN_VALUE_SCORE_FOR_PROMOTION - 0.1,
            exclude_promoted=True,
        )

        results = []
        for candidate in candidates:
            eligibility = self.check_promotion_eligibility(candidate)
            results.append((candidate, eligibility))

        # Sort by value score, eligible first
        results.sort(key=lambda x: (x[1]["eligible"], x[0].value_score), reverse=True)

        return results[:limit]

    def auto_promote(
        self,
        user_id: str,
        mind_client: Any | None = None,
        max_promotions: int = 3,
    ) -> list[dict[str, Any]]:
        """Automatically promote eligible candidates.

        Args:
            user_id: User ID
            mind_client: Mind MCP client
            max_promotions: Maximum candidates to promote

        Returns:
            List of promotion results
        """
        candidates = self.get_promotion_candidates(user_id, limit=max_promotions * 2)

        results = []
        promoted = 0

        for candidate, eligibility in candidates:
            if not eligibility["eligible"]:
                continue

            result = self.promote_to_mind(
                candidate=candidate,
                mind_client=mind_client,
                memory_type="auto",
            )

            results.append(result)

            if result["success"]:
                promoted += 1
                if promoted >= max_promotions:
                    break

        return results

    def to_response(self, promotion_result: dict[str, Any]) -> dict[str, Any]:
        """Convert promotion result to API response format."""
        return promotion_result
