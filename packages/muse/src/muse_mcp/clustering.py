"""Fragment clustering for Muse MCP.

Groups similar fragments automatically based on semantic similarity.
Clusters represent coherent themes or ideas that emerge from fragments.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from collections import defaultdict

import numpy as np

from .database import Database
from .embeddings import EmbeddingModel
from .models import Fragment, Cluster, LifecycleState, DEFAULT_TTL


# Clustering parameters
MIN_CLUSTER_SIZE = 2
MAX_CLUSTER_SIZE = 10
SIMILARITY_THRESHOLD = 0.7  # Minimum similarity to join a cluster
CLUSTER_MERGE_THRESHOLD = 0.8  # Similarity for merging clusters


class FragmentClusterer:
    """Groups similar fragments into clusters."""

    def __init__(self, db: Database, embedder: EmbeddingModel):
        """Initialize fragment clusterer.

        Args:
            db: Database instance
            embedder: Embedding model instance
        """
        self.db = db
        self.embedder = embedder

    def cluster_fragments(
        self,
        user_id: str,
        min_similarity: float = SIMILARITY_THRESHOLD,
        max_cluster_size: int = MAX_CLUSTER_SIZE,
    ) -> list[Cluster]:
        """Cluster all unclustered fragments for a user.

        Args:
            user_id: User ID
            min_similarity: Minimum similarity to cluster together
            max_cluster_size: Maximum fragments per cluster

        Returns:
            List of created/updated clusters
        """
        # Get unclustered fragments with embeddings
        fragments_data = self.db.get_fragments_by_user(
            user_id=user_id,
            state=LifecycleState.FRAGMENT,
            include_expired=False,
            limit=500,
        )

        if len(fragments_data) < MIN_CLUSTER_SIZE:
            return []

        # Extract fragments and embeddings
        fragments = []
        embeddings = []
        for f, e in fragments_data:
            if e is not None and f.cluster_id is None:
                fragments.append(f)
                embeddings.append(e)

        if len(fragments) < MIN_CLUSTER_SIZE:
            return []

        # Build similarity matrix
        embeddings_array = np.array(embeddings)
        similarity_matrix = self._compute_similarity_matrix(embeddings_array)

        # Greedy clustering
        clusters = self._greedy_cluster(
            fragments, similarity_matrix, min_similarity, max_cluster_size
        )

        # Create cluster objects and store
        created_clusters = []
        for fragment_indices in clusters:
            if len(fragment_indices) >= MIN_CLUSTER_SIZE:
                cluster_fragments = [fragments[i] for i in fragment_indices]
                cluster_embeddings = [embeddings[i] for i in fragment_indices]

                cluster = self._create_cluster(
                    user_id, cluster_fragments, cluster_embeddings
                )
                created_clusters.append(cluster)

        return created_clusters

    def _compute_similarity_matrix(self, embeddings: np.ndarray) -> np.ndarray:
        """Compute pairwise cosine similarity matrix.

        Args:
            embeddings: Array of embeddings (n_samples x embedding_dim)

        Returns:
            Similarity matrix (n_samples x n_samples)
        """
        # Normalize embeddings (should already be normalized, but ensure)
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        normalized = embeddings / (norms + 1e-10)

        # Cosine similarity via dot product
        return np.dot(normalized, normalized.T)

    def _greedy_cluster(
        self,
        fragments: list[Fragment],
        similarity_matrix: np.ndarray,
        min_similarity: float,
        max_cluster_size: int,
    ) -> list[list[int]]:
        """Greedy clustering algorithm.

        Args:
            fragments: List of fragments
            similarity_matrix: Pairwise similarities
            min_similarity: Threshold for clustering
            max_cluster_size: Maximum cluster size

        Returns:
            List of clusters (each cluster is list of fragment indices)
        """
        n = len(fragments)
        assigned = [False] * n
        clusters = []

        # Sort fragments by salience (cluster high-salience first)
        indices_by_salience = sorted(
            range(n), key=lambda i: fragments[i].salience, reverse=True
        )

        for seed_idx in indices_by_salience:
            if assigned[seed_idx]:
                continue

            # Start new cluster with seed
            cluster = [seed_idx]
            assigned[seed_idx] = True

            # Find similar unassigned fragments
            similarities = similarity_matrix[seed_idx]
            candidates = [
                (i, similarities[i])
                for i in range(n)
                if not assigned[i] and similarities[i] >= min_similarity
            ]

            # Sort by similarity and add to cluster
            candidates.sort(key=lambda x: x[1], reverse=True)

            for idx, sim in candidates:
                if len(cluster) >= max_cluster_size:
                    break

                # Check similarity to all cluster members
                min_sim_to_cluster = min(
                    similarity_matrix[idx][c] for c in cluster
                )
                if min_sim_to_cluster >= min_similarity:
                    cluster.append(idx)
                    assigned[idx] = True

            if len(cluster) >= MIN_CLUSTER_SIZE:
                clusters.append(cluster)

        return clusters

    def _create_cluster(
        self,
        user_id: str,
        fragments: list[Fragment],
        embeddings: list[np.ndarray],
    ) -> Cluster:
        """Create a cluster from fragments.

        Args:
            user_id: User ID
            fragments: Fragments in the cluster
            embeddings: Corresponding embeddings

        Returns:
            Created Cluster
        """
        # Compute centroid
        centroid = np.mean(embeddings, axis=0)
        centroid = centroid / (np.linalg.norm(centroid) + 1e-10)

        # Generate label from common terms
        label = self._generate_label(fragments)

        # Generate summary
        summary = self._generate_summary(fragments)

        # Create cluster
        cluster = Cluster(
            user_id=user_id,
            label=label,
            summary=summary,
            fragment_ids=[f.id for f in fragments],
            centroid_embedding=centroid.tolist(),
            salience=max(f.salience for f in fragments),  # Max salience
        )

        # Store cluster
        self._store_cluster(cluster)

        # Update fragments to reference cluster
        for fragment in fragments:
            self.db.update_fragment_state(fragment.id, LifecycleState.CLUSTERED)
            # Note: Would also update cluster_id in a full implementation

        return cluster

    def _generate_label(self, fragments: list[Fragment]) -> str:
        """Generate a label for a cluster based on common terms."""
        from collections import Counter
        import re

        # Extract words from all fragments
        all_words = []
        for f in fragments:
            words = re.findall(r'\b[a-z]{4,}\b', f.content.lower())
            all_words.extend(words)

        # Filter common words
        common_words = {
            'that', 'this', 'with', 'from', 'have', 'been', 'were',
            'they', 'their', 'about', 'would', 'could', 'should',
            'being', 'which', 'more', 'some', 'into', 'will',
        }
        filtered = [w for w in all_words if w not in common_words]

        # Get top terms
        term_counts = Counter(filtered)
        top_terms = [term for term, _ in term_counts.most_common(3)]

        if top_terms:
            return " ".join(top_terms)
        return f"cluster-{len(fragments)}-fragments"

    def _generate_summary(self, fragments: list[Fragment]) -> str:
        """Generate a summary for a cluster."""
        # Simple summary: combine first sentences
        summaries = []
        for f in fragments[:3]:  # Top 3 by position (already sorted by salience)
            first_sentence = f.content.split('.')[0].strip()
            if len(first_sentence) > 10:
                summaries.append(first_sentence[:100])

        if summaries:
            return " | ".join(summaries)
        return f"Cluster of {len(fragments)} related fragments"

    def _store_cluster(self, cluster: Cluster) -> None:
        """Store a cluster in the database."""
        # Insert into clusters table
        with self.db._get_connection() as conn:
            import json
            conn.execute("""
                INSERT INTO clusters (
                    id, user_id, label, summary, fragment_ids,
                    centroid_embedding, state, salience, created_at, expires_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                cluster.id,
                cluster.user_id,
                cluster.label,
                cluster.summary,
                json.dumps(cluster.fragment_ids),
                np.array(cluster.centroid_embedding, dtype=np.float32).tobytes() if cluster.centroid_embedding else None,
                cluster.state.value,
                cluster.salience,
                cluster.created_at.isoformat(),
                cluster.expires_at.isoformat() if cluster.expires_at else None,
            ))
            conn.commit()

    def find_cluster_for_fragment(
        self,
        fragment: Fragment,
        fragment_embedding: np.ndarray,
        user_id: str,
        min_similarity: float = SIMILARITY_THRESHOLD,
    ) -> Cluster | None:
        """Find an existing cluster that a fragment could join.

        Args:
            fragment: Fragment to place
            fragment_embedding: Fragment's embedding
            user_id: User ID
            min_similarity: Minimum similarity to join

        Returns:
            Matching cluster or None
        """
        # Get existing clusters
        clusters = self._get_clusters_by_user(user_id)

        best_cluster = None
        best_similarity = min_similarity

        for cluster in clusters:
            if cluster.centroid_embedding:
                centroid = np.array(cluster.centroid_embedding, dtype=np.float32)
                similarity = self.embedder.similarity(fragment_embedding, centroid)

                if similarity > best_similarity:
                    # Check cluster isn't full
                    if len(cluster.fragment_ids) < MAX_CLUSTER_SIZE:
                        best_similarity = similarity
                        best_cluster = cluster

        return best_cluster

    def _get_clusters_by_user(self, user_id: str, limit: int = 100) -> list[Cluster]:
        """Get clusters for a user."""
        import json

        with self.db._get_connection() as conn:
            rows = conn.execute("""
                SELECT * FROM clusters
                WHERE user_id = ? AND (expires_at IS NULL OR expires_at > ?)
                ORDER BY salience DESC, created_at DESC
                LIMIT ?
            """, (user_id, datetime.utcnow().isoformat(), limit)).fetchall()

            clusters = []
            for row in rows:
                cluster = Cluster(
                    id=row["id"],
                    user_id=row["user_id"],
                    label=row["label"] or "",
                    summary=row["summary"] or "",
                    fragment_ids=json.loads(row["fragment_ids"]) if row["fragment_ids"] else [],
                    centroid_embedding=list(np.frombuffer(row["centroid_embedding"], dtype=np.float32)) if row["centroid_embedding"] else None,
                    state=LifecycleState(row["state"]),
                    salience=row["salience"],
                    created_at=datetime.fromisoformat(row["created_at"]),
                    expires_at=datetime.fromisoformat(row["expires_at"]) if row["expires_at"] else None,
                )
                clusters.append(cluster)

            return clusters

    def auto_cluster_on_create(
        self,
        fragment: Fragment,
        fragment_embedding: np.ndarray,
    ) -> Cluster | None:
        """Automatically cluster a newly created fragment.

        Args:
            fragment: New fragment
            fragment_embedding: Fragment's embedding

        Returns:
            Cluster if fragment was added to one, else None
        """
        # Try to find an existing cluster
        cluster = self.find_cluster_for_fragment(
            fragment, fragment_embedding, fragment.user_id
        )

        if cluster:
            # Add to existing cluster
            cluster.fragment_ids.append(fragment.id)

            # Update centroid (simple average)
            # In production, would retrieve all fragment embeddings
            # For now, just update the fragment's state
            self.db.update_fragment_state(fragment.id, LifecycleState.CLUSTERED)

            return cluster

        return None

    def to_response(self, clusters: list[Cluster]) -> dict[str, Any]:
        """Convert clusters to API response format."""
        return {
            "clusters": [c.to_dict() for c in clusters],
            "count": len(clusters),
            "total_fragments": sum(len(c.fragment_ids) for c in clusters),
        }
