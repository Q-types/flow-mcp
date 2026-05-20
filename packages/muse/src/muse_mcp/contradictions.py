"""Contradiction detection for Muse MCP.

Serves as the "inner critic" - surfacing reasons why an idea might fail
or assumptions that are fragile.

Questions it asks:
- What stored memory argues against this?
- What assumption is fragile?
- What would make this fail in production?
- What would a sceptical engineer reject?
- What would make this expensive or noisy?
"""

from __future__ import annotations

import re
from typing import Any

from .database import Database
from .embeddings import EmbeddingModel
from .models import Contradiction, Fragment, Candidate


# Contradiction categories and their detection patterns
CONTRADICTION_TYPES = {
    "evidence": {
        "description": "Evidence that contradicts the claim",
        "patterns": [
            r"(?:but|however|although|contrary to|despite)",
            r"(?:research shows|data indicates|evidence suggests)",
            r"(?:in reality|actually|in fact)",
        ],
    },
    "assumption": {
        "description": "Fragile or untested assumption",
        "patterns": [
            r"(?:assumes?|assuming|presumes?|presuming)",
            r"(?:if and only if|depends on|requires that)",
            r"(?:may not|might not|could fail if)",
        ],
    },
    "risk": {
        "description": "Potential failure mode or risk",
        "patterns": [
            r"(?:risk|danger|threat|vulnerability)",
            r"(?:could fail|might break|may not work)",
            r"(?:security|privacy|safety) (?:concern|issue|risk)",
        ],
    },
    "cost": {
        "description": "Hidden cost or complexity",
        "patterns": [
            r"(?:expensive|costly|resource-intensive)",
            r"(?:complex|complicated|difficult to)",
            r"(?:maintenance|overhead|technical debt)",
        ],
    },
    "scalability": {
        "description": "Won't work at scale",
        "patterns": [
            r"(?:doesn't scale|won't scale|scaling)",
            r"(?:performance|latency|throughput) (?:issue|problem|concern)",
            r"(?:bottleneck|limitation|constraint)",
        ],
    },
    "alternative": {
        "description": "Better alternative exists",
        "patterns": [
            r"(?:instead|alternatively|better approach)",
            r"(?:existing solution|already solved|prior art)",
            r"(?:why not just|simpler to|easier to)",
        ],
    },
}


class ContradictionFinder:
    """Finds contradictions and challenges for ideas."""

    def __init__(self, db: Database, embedder: EmbeddingModel):
        """Initialize contradiction finder.

        Args:
            db: Database instance
            embedder: Embedding model instance
        """
        self.db = db
        self.embedder = embedder

    def find_contradictions(
        self,
        user_id: str,
        target_content: str,
        target_id: str | None = None,
        target_type: str = "fragment",  # "fragment" or "candidate"
        memories: list[dict[str, Any]] | None = None,
    ) -> list[Contradiction]:
        """Find contradictions for a target idea.

        Args:
            user_id: User ID
            target_content: Content to find contradictions for
            target_id: ID of target fragment or candidate
            target_type: Type of target ("fragment" or "candidate")
            memories: Retrieved memories that might contain contradictions

        Returns:
            List of found contradictions
        """
        contradictions = []

        # 1. Check retrieved memories for contradictions
        if memories:
            memory_contradictions = self._find_memory_contradictions(
                user_id, target_content, target_id, target_type, memories
            )
            contradictions.extend(memory_contradictions)

        # 2. Generate assumption-based contradictions
        assumption_contradictions = self._find_assumption_contradictions(
            user_id, target_content, target_id, target_type
        )
        contradictions.extend(assumption_contradictions)

        # 3. Generate risk-based contradictions
        risk_contradictions = self._find_risk_contradictions(
            user_id, target_content, target_id, target_type
        )
        contradictions.extend(risk_contradictions)

        # Store contradictions
        for c in contradictions:
            self.db.insert_contradiction(c)

        return contradictions

    def _find_memory_contradictions(
        self,
        user_id: str,
        target_content: str,
        target_id: str | None,
        target_type: str,
        memories: list[dict[str, Any]],
    ) -> list[Contradiction]:
        """Find contradictions from retrieved memories."""
        contradictions = []
        target_embedding = self.embedder.encode_single(target_content)

        for memory in memories:
            mem_content = memory.get("content", "")

            # Check for explicit contradiction indicators
            contradiction_type = self._detect_contradiction_type(mem_content)

            if contradiction_type:
                # Calculate semantic relationship
                mem_embedding = self.embedder.encode_single(mem_content)
                similarity = self.embedder.similarity(target_embedding, mem_embedding)

                # Contradictions often have moderate similarity (same topic, opposing view)
                if 0.3 < similarity < 0.8:
                    severity = self._calculate_severity(mem_content, contradiction_type)
                    confidence = self._calculate_confidence(similarity, mem_content)

                    c = Contradiction(
                        user_id=user_id,
                        target_content=target_content[:500],
                        target_fragment_id=target_id if target_type == "fragment" else None,
                        target_candidate_id=target_id if target_type == "candidate" else None,
                        contradiction_type=contradiction_type,
                        contradiction_content=mem_content[:500],
                        source=f"memory:{memory.get('id', 'unknown')}",
                        severity=severity,
                        confidence=confidence,
                    )
                    contradictions.append(c)

        return contradictions

    def _find_assumption_contradictions(
        self,
        user_id: str,
        target_content: str,
        target_id: str | None,
        target_type: str,
    ) -> list[Contradiction]:
        """Find fragile assumptions in the target content."""
        contradictions = []
        content_lower = target_content.lower()

        # Look for assumption indicators
        assumption_patterns = [
            (r"(?:always|never|every|all|none)", "Absolutist assumption"),
            (r"(?:should|must|will)\s+\w+", "Prescriptive assumption"),
            (r"(?:easy|simple|trivial|just)", "Complexity underestimation"),
            (r"(?:users? will|people will|they will)", "Behavioral assumption"),
            (r"(?:fast|quick|instant)", "Performance assumption"),
            (r"(?:secure|safe|protected)", "Security assumption"),
        ]

        for pattern, description in assumption_patterns:
            matches = re.findall(pattern, content_lower)
            if matches:
                c = Contradiction(
                    user_id=user_id,
                    target_content=target_content[:500],
                    target_fragment_id=target_id if target_type == "fragment" else None,
                    target_candidate_id=target_id if target_type == "candidate" else None,
                    contradiction_type="assumption",
                    contradiction_content=f"{description}: Found '{matches[0]}' - this assumption may not hold in all cases",
                    source="assumption_analysis",
                    severity=0.4,
                    confidence=0.6,
                )
                contradictions.append(c)

        return contradictions[:3]  # Limit to top 3

    def _find_risk_contradictions(
        self,
        user_id: str,
        target_content: str,
        target_id: str | None,
        target_type: str,
    ) -> list[Contradiction]:
        """Find potential risks and failure modes."""
        contradictions = []
        content_lower = target_content.lower()

        # Risk patterns
        risk_checks = [
            {
                "check": lambda c: "api" in c and "external" in c,
                "risk": "External API dependency may cause availability issues",
                "severity": 0.6,
            },
            {
                "check": lambda c: "database" in c or "sql" in c,
                "risk": "Database operations may become bottleneck at scale",
                "severity": 0.5,
            },
            {
                "check": lambda c: "user input" in c or "user data" in c,
                "risk": "User input handling requires validation and sanitization",
                "severity": 0.7,
            },
            {
                "check": lambda c: "cache" in c,
                "risk": "Cache invalidation is a known hard problem",
                "severity": 0.5,
            },
            {
                "check": lambda c: "real-time" in c or "realtime" in c,
                "risk": "Real-time requirements add significant complexity",
                "severity": 0.6,
            },
            {
                "check": lambda c: "ml" in c or "machine learning" in c or "model" in c,
                "risk": "ML models require ongoing maintenance and can drift",
                "severity": 0.5,
            },
        ]

        for check in risk_checks:
            if check["check"](content_lower):
                c = Contradiction(
                    user_id=user_id,
                    target_content=target_content[:500],
                    target_fragment_id=target_id if target_type == "fragment" else None,
                    target_candidate_id=target_id if target_type == "candidate" else None,
                    contradiction_type="risk",
                    contradiction_content=check["risk"],
                    source="risk_analysis",
                    severity=check["severity"],
                    confidence=0.7,
                )
                contradictions.append(c)

        return contradictions[:3]  # Limit to top 3

    def _detect_contradiction_type(self, content: str) -> str | None:
        """Detect contradiction type from content."""
        content_lower = content.lower()

        for ctype, info in CONTRADICTION_TYPES.items():
            for pattern in info["patterns"]:
                if re.search(pattern, content_lower):
                    return ctype

        return None

    def _calculate_severity(self, content: str, contradiction_type: str) -> float:
        """Calculate severity of a contradiction."""
        base_severity = {
            "evidence": 0.7,
            "assumption": 0.5,
            "risk": 0.6,
            "cost": 0.5,
            "scalability": 0.6,
            "alternative": 0.4,
        }.get(contradiction_type, 0.5)

        # Adjust based on content strength indicators
        content_lower = content.lower()

        strength_indicators = [
            ("critical", 0.2),
            ("major", 0.15),
            ("serious", 0.15),
            ("significant", 0.1),
            ("minor", -0.1),
            ("slight", -0.1),
        ]

        for indicator, adjustment in strength_indicators:
            if indicator in content_lower:
                base_severity += adjustment
                break

        return max(0.1, min(1.0, base_severity))

    def _calculate_confidence(self, similarity: float, content: str) -> float:
        """Calculate confidence in the contradiction."""
        # Higher similarity = more confident it's relevant
        base_confidence = 0.5 + (similarity * 0.3)

        # Evidence-based content is more confident
        content_lower = content.lower()
        if any(term in content_lower for term in ["data", "research", "study", "evidence"]):
            base_confidence += 0.1

        return min(1.0, base_confidence)

    def get_contradictions(
        self,
        target_fragment_id: str | None = None,
        target_candidate_id: str | None = None,
    ) -> list[Contradiction]:
        """Get existing contradictions for a target."""
        return self.db.get_contradictions_for_target(
            target_fragment_id=target_fragment_id,
            target_candidate_id=target_candidate_id,
        )

    def to_response(self, contradictions: list[Contradiction]) -> dict[str, Any]:
        """Convert contradictions to API response format."""
        by_type = {}
        for c in contradictions:
            if c.contradiction_type not in by_type:
                by_type[c.contradiction_type] = []
            by_type[c.contradiction_type].append(c.to_dict())

        return {
            "contradictions": [c.to_dict() for c in contradictions],
            "by_type": by_type,
            "count": len(contradictions),
            "total_severity": sum(c.severity for c in contradictions) / len(contradictions) if contradictions else 0,
        }
