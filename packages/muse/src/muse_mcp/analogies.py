"""Analogy generation for Muse MCP.

Creates cross-domain structural mappings - connecting concepts from
different domains based on structural similarity rather than surface similarity.

Example:
    Source: "KSP estimator: messy knowledge → schema → estimator → feedback"
    Target: "MCP memory: messy experience → memory → retrieval → reflection"
"""

from __future__ import annotations

import re
from typing import Any

from .database import Database
from .embeddings import EmbeddingModel
from .models import Analogy


# Common structural patterns
STRUCTURAL_PATTERNS = {
    "transformation": {
        "pattern": r"(.+?)\s*(?:→|->|leads to|becomes|transforms into)\s*(.+)",
        "structure": "X → Y",
        "description": "Input transforms to output",
    },
    "pipeline": {
        "pattern": r"(.+?)\s*(?:→|->)\s*(.+?)\s*(?:→|->)\s*(.+)",
        "structure": "X → Y → Z",
        "description": "Multi-stage processing",
    },
    "feedback_loop": {
        "pattern": r"(.+?)\s*(?:→|->).+?(?:feedback|loop|cycle|iterate)",
        "structure": "X → process → feedback → X",
        "description": "Iterative refinement",
    },
    "composition": {
        "pattern": r"(.+?)\s*(?:contains|includes|has|comprises)\s*(.+)",
        "structure": "X contains Y",
        "description": "Hierarchical containment",
    },
    "combination": {
        "pattern": r"(.+?)\s*(?:\+|and|combined with|merged with)\s*(.+?)\s*(?:=|gives|produces|creates)\s*(.+)",
        "structure": "X + Y = Z",
        "description": "Synthesis of parts",
    },
    "conditional": {
        "pattern": r"if\s+(.+?)\s+then\s+(.+)",
        "structure": "if X then Y",
        "description": "Conditional relationship",
    },
    "trade_off": {
        "pattern": r"(.+?)\s*(?:vs|versus|or|trade-off|balance)\s*(.+)",
        "structure": "X vs Y",
        "description": "Competing alternatives",
    },
}


class AnalogyGenerator:
    """Generates cross-domain structural analogies."""

    def __init__(self, db: Database, embedder: EmbeddingModel):
        """Initialize analogy generator.

        Args:
            db: Database instance
            embedder: Embedding model instance
        """
        self.db = db
        self.embedder = embedder

    def generate_analogies(
        self,
        user_id: str,
        source_content: str,
        source_domain: str,
        target_memories: list[dict[str, Any]],
        limit: int = 5,
    ) -> list[Analogy]:
        """Generate analogies between source content and target memories.

        Args:
            user_id: User ID
            source_content: Source content to find analogies for
            source_domain: Domain of the source
            target_memories: Potential target memories from Mind MCP
            limit: Maximum analogies to generate

        Returns:
            List of generated analogies
        """
        # Extract structure from source
        source_structure = self._extract_structure(source_content)

        if not source_structure:
            return []

        analogies = []

        for memory in target_memories:
            target_content = memory.get("content", "")
            target_domain = self._infer_domain(target_content)

            # Skip if same domain (we want cross-domain)
            if target_domain.lower() == source_domain.lower():
                continue

            # Extract target structure
            target_structure = self._extract_structure(target_content)

            if not target_structure:
                continue

            # Compare structures
            structural_similarity = self._compare_structures(
                source_structure, target_structure
            )

            # Calculate surface distance (semantic difference)
            source_embedding = self.embedder.encode_single(source_content)
            target_embedding = self.embedder.encode_single(target_content)
            semantic_similarity = self.embedder.similarity(source_embedding, target_embedding)
            surface_distance = 1.0 - semantic_similarity

            # Good analogies have high structural similarity but low surface similarity
            if structural_similarity > 0.3 and surface_distance > 0.3:
                # Generate insights from the analogy
                insights = self._generate_insights(
                    source_content, source_structure,
                    target_content, target_structure
                )

                analogy = Analogy(
                    user_id=user_id,
                    source_domain=source_domain,
                    source_concept=source_content[:200],
                    source_structure=source_structure["type"],
                    target_domain=target_domain,
                    target_concept=target_content[:200],
                    target_structure=target_structure["type"],
                    structural_similarity=structural_similarity,
                    surface_distance=surface_distance,
                    usefulness=self._score_usefulness(
                        structural_similarity, surface_distance, len(insights)
                    ),
                    insights=insights,
                )

                self.db.insert_analogy(analogy)
                analogies.append(analogy)

        # Sort by usefulness and return top N
        analogies.sort(key=lambda a: a.usefulness, reverse=True)
        return analogies[:limit]

    def _extract_structure(self, content: str) -> dict[str, Any] | None:
        """Extract structural pattern from content."""
        content_lower = content.lower()

        for pattern_type, pattern_info in STRUCTURAL_PATTERNS.items():
            match = re.search(pattern_info["pattern"], content_lower, re.IGNORECASE)
            if match:
                return {
                    "type": pattern_type,
                    "structure": pattern_info["structure"],
                    "description": pattern_info["description"],
                    "groups": match.groups(),
                }

        # Try to infer structure from keywords
        if "→" in content or "->" in content:
            return {
                "type": "transformation",
                "structure": "X → Y",
                "description": "Input transforms to output",
                "groups": (),
            }

        return None

    def _compare_structures(
        self,
        source: dict[str, Any],
        target: dict[str, Any],
    ) -> float:
        """Compare two structures for similarity."""
        # Same type = high similarity
        if source["type"] == target["type"]:
            return 0.9

        # Related types
        related_pairs = [
            ("transformation", "pipeline"),
            ("pipeline", "feedback_loop"),
            ("composition", "combination"),
        ]

        for pair in related_pairs:
            if (source["type"], target["type"]) in [pair, pair[::-1]]:
                return 0.6

        return 0.2

    def _infer_domain(self, content: str) -> str:
        """Infer domain from content."""
        content_lower = content.lower()

        domain_keywords = {
            "software": ["code", "function", "class", "api", "programming", "software"],
            "business": ["revenue", "customer", "market", "sales", "business"],
            "science": ["hypothesis", "experiment", "data", "research", "scientific"],
            "design": ["user", "interface", "experience", "design", "ux"],
            "engineering": ["system", "architecture", "component", "engineering"],
            "communication": ["message", "feedback", "communication", "dialogue"],
            "learning": ["learn", "knowledge", "memory", "understand", "teach"],
        }

        for domain, keywords in domain_keywords.items():
            if any(kw in content_lower for kw in keywords):
                return domain

        return "general"

    def _generate_insights(
        self,
        source_content: str,
        source_structure: dict[str, Any],
        target_content: str,
        target_structure: dict[str, Any],
    ) -> list[str]:
        """Generate insights from the analogy."""
        insights = []

        # Basic structural insight
        insights.append(
            f"Both follow a {source_structure['description']} pattern"
        )

        # If same structure type, look for transferable lessons
        if source_structure["type"] == target_structure["type"]:
            insights.append(
                f"Solutions from {self._infer_domain(target_content)} "
                f"may transfer to {self._infer_domain(source_content)}"
            )

        # Look for specific transferable elements
        if source_structure["type"] in ["transformation", "pipeline"]:
            insights.append(
                "Consider what intermediate steps might improve the transformation"
            )

        if source_structure["type"] == "feedback_loop":
            insights.append(
                "Both benefit from iterative refinement cycles"
            )

        return insights[:3]  # Limit to 3 insights

    def _score_usefulness(
        self,
        structural_similarity: float,
        surface_distance: float,
        insight_count: int,
    ) -> float:
        """Score the usefulness of an analogy."""
        # Good analogies: high structural similarity, high surface distance
        base_score = (structural_similarity * 0.4) + (surface_distance * 0.4)

        # Bonus for insights
        insight_bonus = min(0.2, insight_count * 0.067)

        return min(1.0, base_score + insight_bonus)

    def find_analogies_for_concept(
        self,
        user_id: str,
        concept: str,
        limit: int = 5,
    ) -> list[Analogy]:
        """Find existing analogies relevant to a concept.

        Args:
            user_id: User ID
            concept: Concept to find analogies for
            limit: Maximum analogies to return

        Returns:
            List of relevant analogies
        """
        analogies = self.db.get_analogies_by_user(user_id, limit=limit * 2)

        # Score by relevance to concept
        concept_embedding = self.embedder.encode_single(concept)

        scored = []
        for analogy in analogies:
            source_embedding = self.embedder.encode_single(analogy.source_concept)
            target_embedding = self.embedder.encode_single(analogy.target_concept)

            source_sim = self.embedder.similarity(concept_embedding, source_embedding)
            target_sim = self.embedder.similarity(concept_embedding, target_embedding)

            relevance = max(source_sim, target_sim)
            scored.append((analogy, relevance))

        scored.sort(key=lambda x: x[1], reverse=True)
        return [a for a, _ in scored[:limit]]

    def to_response(self, analogies: list[Analogy]) -> dict[str, Any]:
        """Convert analogies to API response format."""
        return {
            "analogies": [a.to_dict() for a in analogies],
            "count": len(analogies),
        }
