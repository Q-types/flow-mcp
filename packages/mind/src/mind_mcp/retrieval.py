"""Hybrid retrieval for Mind MCP v2.

Enhanced scoring formula:
S_i = α·sim(q,m_i) + β·I_i + γ·R_i - δ·A_i

Where:
- sim(q,m_i) = embedding similarity (semantic + keyword via RRF)
- I_i = importance score (static type-based baseline)
- R_i = recency boost (based on last_accessed)
- A_i = age decay penalty (type-specific decay rate)

Combines semantic search (embeddings) with keyword search (BM25)
using Reciprocal Rank Fusion (RRF) for optimal results.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import numpy as np

from .database import Database
from .embeddings import EmbeddingModel, cosine_similarity
from .models import Memory, RetrievalResult, MemoryType, DECAY_RATE_BY_TYPE


# RRF constant (standard value from literature)
RRF_K = 60

# Default scoring coefficients
DEFAULT_ALPHA = 0.5  # Similarity weight
DEFAULT_BETA = 0.2   # Importance weight
DEFAULT_GAMMA = 0.2  # Recency boost weight
DEFAULT_DELTA = 0.1  # Age decay penalty weight

# Type-specific coefficient adjustments
TYPE_COEFFICIENTS = {
    MemoryType.EPISODIC: {"alpha": 0.4, "beta": 0.15, "gamma": 0.35, "delta": 0.1},  # Higher recency for events
    MemoryType.SEMANTIC: {"alpha": 0.5, "beta": 0.3, "gamma": 0.15, "delta": 0.05},  # Higher importance for facts
    MemoryType.PROCEDURAL: {"alpha": 0.5, "beta": 0.25, "gamma": 0.2, "delta": 0.05},  # Balanced for workflows
    MemoryType.PREFERENCE: {"alpha": 0.4, "beta": 0.4, "gamma": 0.15, "delta": 0.05},  # High importance, stable
    MemoryType.REFLECTION: {"alpha": 0.45, "beta": 0.35, "gamma": 0.15, "delta": 0.05},  # High importance insights
}


class HybridRetriever:
    """Hybrid semantic + keyword retrieval with RRF fusion and multi-factor scoring."""

    def __init__(self, db: Database, embedder: EmbeddingModel):
        """Initialize retriever.

        Args:
            db: Database instance
            embedder: Embedding model instance
        """
        self.db = db
        self.embedder = embedder

    def retrieve(
        self,
        user_id: str,
        query: str,
        limit: int = 10,
        min_salience: float = 0.0,
        memory_types: list[MemoryType] | None = None,
        include_reflections: bool = True,
        update_access: bool = True,
        # Legacy params for backwards compat
        semantic_weight: float | None = None,
        keyword_weight: float | None = None,
        salience_weight: float | None = None,
        recency_weight: float | None = None,
    ) -> RetrievalResult:
        """Retrieve relevant memories using hybrid search with multi-factor scoring.

        Enhanced scoring formula:
        S_i = α·sim(q,m_i) + β·I_i + γ·R_i - δ·A_i

        Where coefficients vary by memory type for optimal retrieval.

        Args:
            user_id: User ID to search within
            query: Natural language query
            limit: Maximum memories to return
            min_salience: Minimum salience threshold
            memory_types: Filter to specific memory types (optional)
            include_reflections: Include reflection-type memories (default True)
            update_access: Update last_accessed for retrieved memories (default True)
            semantic_weight: Legacy param, ignored in v2
            keyword_weight: Legacy param, ignored in v2
            salience_weight: Legacy param, ignored in v2
            recency_weight: Legacy param, ignored in v2

        Returns:
            RetrievalResult with ranked memories and scores
        """
        # Get all memories for user with embeddings
        memory_data = self.db.get_memories_by_user(
            user_id=user_id,
            limit=1000,  # Get more for reranking
            min_salience=min_salience,
        )

        if not memory_data:
            return RetrievalResult(memories=[], scores={})

        memories = [m for m, _ in memory_data]
        embeddings = [e for _, e in memory_data if e is not None]

        # Filter by memory type if specified
        if memory_types:
            type_set = set(memory_types)
            if not include_reflections:
                type_set.discard(MemoryType.REFLECTION)
            memories = [m for m in memories if m.memory_type in type_set]
            memory_data = [(m, e) for (m, e) in memory_data if m.memory_type in type_set]
            embeddings = [e for (m, e) in memory_data if e is not None]

        if not memories:
            return RetrievalResult(memories=[], scores={})

        # Build memory lookup
        memory_by_id = {m.id: m for m in memories}

        # 1. Semantic search
        semantic_scores = {}
        if embeddings:
            query_embedding = self.embedder.encode_query(query)
            doc_embeddings = np.stack(embeddings)
            similarities = cosine_similarity(query_embedding, doc_embeddings)

            for i, (memory, _) in enumerate(memory_data):
                if i < len(similarities):
                    semantic_scores[memory.id] = float(similarities[i])

        # 2. Keyword search (FTS5 BM25)
        keyword_results = self.db.fts_search(user_id, query, limit=100)
        keyword_scores = {mid: score for mid, score in keyword_results}

        # Normalize keyword scores
        if keyword_scores:
            max_kw = max(keyword_scores.values())
            if max_kw > 0:
                keyword_scores = {k: v / max_kw for k, v in keyword_scores.items()}

        # 3. RRF fusion for similarity component
        all_memory_ids = set(semantic_scores.keys()) | set(keyword_scores.keys())

        # Create ranked lists
        semantic_ranked = sorted(
            semantic_scores.items(), key=lambda x: x[1], reverse=True
        )
        keyword_ranked = sorted(
            keyword_scores.items(), key=lambda x: x[1], reverse=True
        )

        # Compute RRF scores
        rrf_scores = self._rrf_merge([
            [mid for mid, _ in semantic_ranked],
            [mid for mid, _ in keyword_ranked],
        ])

        # 4. Compute final scores using multi-factor formula
        # S_i = α·sim(q,m_i) + β·I_i + γ·R_i - δ·A_i
        final_scores = {}
        now = datetime.utcnow()

        for mid in all_memory_ids:
            memory = memory_by_id.get(mid)
            if memory is None:
                continue

            # Get type-specific coefficients
            coeffs = TYPE_COEFFICIENTS.get(memory.memory_type, {
                "alpha": DEFAULT_ALPHA,
                "beta": DEFAULT_BETA,
                "gamma": DEFAULT_GAMMA,
                "delta": DEFAULT_DELTA,
            })

            # sim(q, m_i): Combined similarity from RRF + semantic + keyword
            rrf = rrf_scores.get(mid, 0.0)
            sem = semantic_scores.get(mid, 0.0)
            kw = keyword_scores.get(mid, 0.0)
            # Combine into single similarity score
            similarity = (rrf * 0.4 + sem * 0.4 + kw * 0.2)

            # I_i: Importance score (combines static importance with dynamic salience)
            importance = (memory.importance * 0.6 + memory.salience * 0.4)

            # R_i: Recency boost based on last_accessed (or created_at if never accessed)
            access_time = memory.last_accessed or memory.created_at
            access_age_days = (now - access_time).total_seconds() / 86400
            recency = max(0.0, 1.0 - (access_age_days / 30))

            # A_i: Age decay penalty using type-specific decay rate
            creation_age_days = (now - memory.created_at).total_seconds() / 86400
            decay_rate = DECAY_RATE_BY_TYPE.get(memory.memory_type, 0.1)
            age_penalty = min(1.0, (creation_age_days / 30) * decay_rate)

            # Final score: S_i = α·sim + β·I_i + γ·R_i - δ·A_i
            final = (
                coeffs["alpha"] * similarity +
                coeffs["beta"] * importance +
                coeffs["gamma"] * recency -
                coeffs["delta"] * age_penalty
            )

            final_scores[mid] = max(0.0, final)  # Ensure non-negative

        # 5. Sort and limit
        ranked = sorted(final_scores.items(), key=lambda x: x[1], reverse=True)
        top_ids = [mid for mid, _ in ranked[:limit]]

        # 6. Update access timestamps for retrieved memories
        if update_access:
            for mid in top_ids:
                self.db.update_last_accessed(mid)

        # Build result
        result_memories = [memory_by_id[mid] for mid in top_ids if mid in memory_by_id]
        result_scores = {mid: final_scores[mid] for mid in top_ids}

        return RetrievalResult(
            memories=result_memories,
            scores=result_scores,
        )

    def _rrf_merge(self, ranked_lists: list[list[str]], k: int = RRF_K) -> dict[str, float]:
        """Reciprocal Rank Fusion to merge multiple ranked lists.

        RRF score = sum(1 / (k + rank)) across all lists

        Args:
            ranked_lists: List of ranked ID lists
            k: RRF constant (default 60)

        Returns:
            Dictionary of ID -> RRF score
        """
        scores = {}
        for ranked in ranked_lists:
            for idx, mid in enumerate(ranked):
                scores[mid] = scores.get(mid, 0.0) + 1.0 / (k + idx + 1)
        return scores

    def to_response(self, result: RetrievalResult) -> dict[str, Any]:
        """Convert retrieval result to API response format."""
        return {
            "retrieval_id": result.retrieval_id,
            "memories": [
                {
                    "id": m.id,
                    "memory_id": m.id,
                    "content": m.content,
                    "content_type": m.content_type,
                    "temporal_level": m.temporal_level,
                    "salience": m.salience,
                    "score": result.scores.get(m.id, 0.0),
                    "created_at": m.created_at.isoformat(),
                }
                for m in result.memories
            ],
            "count": len(result.memories),
        }
