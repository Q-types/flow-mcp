"""Multi-mode association retrieval for Muse MCP.

Retrieves from Mind MCP using multiple modes:
- Nearest memories (semantic similarity)
- Distant analogies (cross-domain structural matches)
- Past failures (what went wrong)
- Successful workflows (what worked)
- Contradictory evidence (arguments against)
- Domain patterns (established patterns)
- User preferences (style and preferences)
"""

from __future__ import annotations

from typing import Any

from .database import Database
from .embeddings import EmbeddingModel
from .models import RetrievalMode


class AssociationRetriever:
    """Multi-mode retrieval engine for productive associations."""

    def __init__(self, db: Database, embedder: EmbeddingModel):
        """Initialize association retriever.

        Args:
            db: Database instance
            embedder: Embedding model instance
        """
        self.db = db
        self.embedder = embedder

    def retrieve_associations(
        self,
        user_id: str,
        query: str,
        modes: list[RetrievalMode] | None = None,
        limit_per_mode: int = 5,
        mind_client: Any | None = None,
    ) -> dict[str, list[dict[str, Any]]]:
        """Retrieve associations using multiple modes.

        Args:
            user_id: User ID for retrieval
            query: Query text
            modes: Which retrieval modes to use (default: all)
            limit_per_mode: Max results per mode
            mind_client: Optional Mind MCP client for external retrieval

        Returns:
            Dict mapping mode names to retrieved results
        """
        if modes is None:
            modes = list(RetrievalMode)

        results: dict[str, list[dict[str, Any]]] = {}

        for mode in modes:
            if mode == RetrievalMode.NEAREST:
                results["nearest"] = self._retrieve_nearest(
                    user_id, query, limit_per_mode, mind_client
                )
            elif mode == RetrievalMode.DISTANT_ANALOGY:
                results["distant_analogies"] = self._retrieve_distant_analogies(
                    user_id, query, limit_per_mode, mind_client
                )
            elif mode == RetrievalMode.PAST_FAILURES:
                results["past_failures"] = self._retrieve_failures(
                    user_id, query, limit_per_mode, mind_client
                )
            elif mode == RetrievalMode.SUCCESSFUL_WORKFLOWS:
                results["successful_workflows"] = self._retrieve_workflows(
                    user_id, query, limit_per_mode, mind_client
                )
            elif mode == RetrievalMode.CONTRADICTORY:
                results["contradictory"] = self._retrieve_contradictory(
                    user_id, query, limit_per_mode, mind_client
                )
            elif mode == RetrievalMode.DOMAIN_PATTERNS:
                results["domain_patterns"] = self._retrieve_patterns(
                    user_id, query, limit_per_mode, mind_client
                )
            elif mode == RetrievalMode.USER_PREFERENCES:
                results["user_preferences"] = self._retrieve_preferences(
                    user_id, query, limit_per_mode, mind_client
                )

        return results

    def _retrieve_nearest(
        self,
        user_id: str,
        query: str,
        limit: int,
        mind_client: Any | None,
    ) -> list[dict[str, Any]]:
        """Retrieve semantically similar memories."""
        if mind_client is None:
            return []

        # Standard semantic retrieval from Mind MCP
        try:
            result = mind_client.retrieve(
                user_id=user_id,
                query=query,
                limit=limit,
            )
            return result.get("memories", [])
        except Exception:
            return []

    def _retrieve_distant_analogies(
        self,
        user_id: str,
        query: str,
        limit: int,
        mind_client: Any | None,
    ) -> list[dict[str, Any]]:
        """Retrieve distant but structurally similar memories.

        This looks for memories that are semantically different
        but share structural patterns.
        """
        if mind_client is None:
            return []

        # Extract structural elements from query
        structural_terms = self._extract_structure(query)

        if not structural_terms:
            return []

        # Search for structural matches with low semantic similarity
        try:
            result = mind_client.retrieve(
                user_id=user_id,
                query=structural_terms,
                limit=limit * 2,
                memory_types=["procedural", "semantic"],  # Patterns and facts
            )
            memories = result.get("memories", [])

            # Filter for low direct similarity but structural match
            query_embedding = self.embedder.encode_single(query)
            distant = []

            for m in memories:
                content = m.get("content", "")
                mem_embedding = self.embedder.encode_single(content)
                similarity = self.embedder.similarity(query_embedding, mem_embedding)

                # We want low semantic similarity (< 0.5) but present in results
                # (meaning structural match)
                if similarity < 0.5:
                    m["analogy_distance"] = 1.0 - similarity
                    distant.append(m)

            # Sort by distance (higher = more distant)
            distant.sort(key=lambda x: x.get("analogy_distance", 0), reverse=True)
            return distant[:limit]

        except Exception:
            return []

    def _extract_structure(self, text: str) -> str:
        """Extract structural elements from text.

        Looks for patterns like:
        - X → Y (transformation)
        - A + B = C (combination)
        - if X then Y (conditional)
        - X contains Y (composition)
        """
        import re

        structures = []

        # Look for arrows/transformations
        if "→" in text or "->" in text or "leads to" in text.lower():
            structures.append("transformation process flow")

        # Look for combinations
        if "+" in text or "combine" in text.lower() or "merge" in text.lower():
            structures.append("combination synthesis")

        # Look for conditionals
        if "if" in text.lower() and "then" in text.lower():
            structures.append("conditional logic rule")

        # Look for hierarchies
        if "contains" in text.lower() or "includes" in text.lower():
            structures.append("hierarchy composition structure")

        # Look for sequences
        if re.search(r'\d+\.\s|\bfirst\b|\bthen\b|\bfinally\b', text.lower()):
            structures.append("sequence steps process")

        return " ".join(structures)

    def _retrieve_failures(
        self,
        user_id: str,
        query: str,
        limit: int,
        mind_client: Any | None,
    ) -> list[dict[str, Any]]:
        """Retrieve past failures related to the query."""
        if mind_client is None:
            return []

        # Search for failure-related memories
        failure_query = f"failed mistake error problem issue: {query}"

        try:
            result = mind_client.retrieve(
                user_id=user_id,
                query=failure_query,
                limit=limit,
                memory_types=["episodic"],  # Failures are events
            )
            memories = result.get("memories", [])

            # Filter to those with failure indicators
            failure_terms = ["fail", "error", "mistake", "wrong", "problem", "issue", "bug"]
            failures = [
                m for m in memories
                if any(term in m.get("content", "").lower() for term in failure_terms)
            ]

            return failures[:limit]

        except Exception:
            return []

    def _retrieve_workflows(
        self,
        user_id: str,
        query: str,
        limit: int,
        mind_client: Any | None,
    ) -> list[dict[str, Any]]:
        """Retrieve successful workflows related to the query."""
        if mind_client is None:
            return []

        try:
            result = mind_client.retrieve(
                user_id=user_id,
                query=query,
                limit=limit,
                memory_types=["procedural"],  # Workflows are procedural
            )
            return result.get("memories", [])

        except Exception:
            return []

    def _retrieve_contradictory(
        self,
        user_id: str,
        query: str,
        limit: int,
        mind_client: Any | None,
    ) -> list[dict[str, Any]]:
        """Retrieve memories that contradict or challenge the query."""
        if mind_client is None:
            return []

        # Construct negation query
        negation_query = f"not {query} | against {query} | alternative to {query}"

        try:
            result = mind_client.retrieve(
                user_id=user_id,
                query=negation_query,
                limit=limit * 2,
            )
            memories = result.get("memories", [])

            # Score by contradiction indicators
            contradiction_terms = [
                "but", "however", "instead", "not", "don't", "avoid",
                "risk", "problem", "issue", "concern", "alternative"
            ]

            scored = []
            for m in memories:
                content = m.get("content", "").lower()
                score = sum(1 for term in contradiction_terms if term in content)
                if score > 0:
                    m["contradiction_score"] = score
                    scored.append(m)

            scored.sort(key=lambda x: x.get("contradiction_score", 0), reverse=True)
            return scored[:limit]

        except Exception:
            return []

    def _retrieve_patterns(
        self,
        user_id: str,
        query: str,
        limit: int,
        mind_client: Any | None,
    ) -> list[dict[str, Any]]:
        """Retrieve domain patterns related to the query."""
        if mind_client is None:
            return []

        pattern_query = f"pattern best practice standard approach: {query}"

        try:
            result = mind_client.retrieve(
                user_id=user_id,
                query=pattern_query,
                limit=limit,
                memory_types=["semantic", "procedural"],
            )
            return result.get("memories", [])

        except Exception:
            return []

    def _retrieve_preferences(
        self,
        user_id: str,
        query: str,
        limit: int,
        mind_client: Any | None,
    ) -> list[dict[str, Any]]:
        """Retrieve user preferences related to the query."""
        if mind_client is None:
            return []

        try:
            result = mind_client.retrieve(
                user_id=user_id,
                query=query,
                limit=limit,
                memory_types=["preference"],
            )
            return result.get("memories", [])

        except Exception:
            return []

    def to_response(self, associations: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
        """Convert associations to API response format."""
        total_count = sum(len(v) for v in associations.values())

        return {
            "associations": associations,
            "modes_used": list(associations.keys()),
            "total_count": total_count,
            "summary": {
                mode: len(items) for mode, items in associations.items()
            },
        }
