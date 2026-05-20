"""Fragment storage and decay management for Muse MCP.

Fragments are the atomic unit of transient memory - raw ideas that
decay unless clustered, evaluated, or promoted.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import numpy as np

from .database import Database
from .embeddings import EmbeddingModel
from .models import Fragment, LifecycleState, DEFAULT_TTL, DEFAULT_DECAY_RATE


class FragmentStore:
    """High-level fragment operations with automatic embedding and decay."""

    def __init__(self, db: Database, embedder: EmbeddingModel):
        """Initialize fragment store.

        Args:
            db: Database instance
            embedder: Embedding model instance
        """
        self.db = db
        self.embedder = embedder

    def create(
        self,
        user_id: str,
        content: str,
        source_prompt: str = "",
        source_working_object_id: str | None = None,
        domains: list[str] | None = None,
        tags: list[str] | None = None,
        parent_id: str | None = None,
        ttl_seconds: int | None = None,
        decay_rate: float | None = None,
        initial_salience: float = 1.0,
    ) -> Fragment:
        """Create a new fragment with embedding.

        Args:
            user_id: User ID who owns this fragment
            content: Fragment content text
            source_prompt: Original prompt that spawned this
            source_working_object_id: Working object this came from
            domains: Relevant domains
            tags: Tags for categorization
            parent_id: Parent fragment if derived
            ttl_seconds: Time to live (default: 1 hour)
            decay_rate: Salience decay per hour (default: 0.1)
            initial_salience: Starting salience (default: 1.0)

        Returns:
            Created Fragment object
        """
        # Sanitize content
        content = self._sanitize_content(content)

        # Use defaults for TTL and decay
        if ttl_seconds is None:
            ttl_seconds = DEFAULT_TTL[LifecycleState.FRAGMENT]
        if decay_rate is None:
            decay_rate = DEFAULT_DECAY_RATE[LifecycleState.FRAGMENT]

        # Create fragment
        fragment = Fragment(
            user_id=user_id,
            content=content,
            source_prompt=source_prompt,
            source_working_object_id=source_working_object_id,
            domains=domains or [],
            tags=tags or [],
            parent_id=parent_id,
            ttl_seconds=ttl_seconds,
            decay_rate=decay_rate,
            salience=initial_salience,
        )

        # Generate embedding
        embedding = self.embedder.encode_single(content, is_query=False)

        # Store in database
        self.db.insert_fragment(fragment, embedding)

        return fragment

    def get(self, fragment_id: str, refresh: bool = True) -> Fragment | None:
        """Get a fragment by ID.

        Args:
            fragment_id: Fragment ID to retrieve
            refresh: If True, extends TTL on access

        Returns:
            Fragment object or None if not found
        """
        fragment = self.db.get_fragment(fragment_id)

        if fragment is None:
            return None

        if fragment.is_expired():
            self.db.delete_fragment(fragment_id)
            return None

        if refresh:
            new_expires = datetime.utcnow() + timedelta(seconds=fragment.ttl_seconds)
            self.db.refresh_fragment(fragment_id, new_expires)
            fragment.last_accessed = datetime.utcnow()
            fragment.expires_at = new_expires

        return fragment

    def list_active(
        self,
        user_id: str,
        state: LifecycleState | None = None,
        min_salience: float = 0.0,
        limit: int = 100,
    ) -> list[Fragment]:
        """List active (non-expired) fragments for a user.

        Args:
            user_id: User ID to filter by
            state: Optional lifecycle state filter
            min_salience: Minimum salience threshold
            limit: Maximum fragments to return

        Returns:
            List of active fragments sorted by salience
        """
        results = self.db.get_fragments_by_user(
            user_id=user_id,
            state=state,
            include_expired=False,
            limit=limit,
        )

        fragments = [f for f, _ in results if f.salience >= min_salience]
        return fragments

    def apply_decay(self, user_id: str, hours_passed: float = 1.0) -> int:
        """Apply decay to all fragments for a user.

        Args:
            user_id: User ID to decay fragments for
            hours_passed: Hours of decay to apply

        Returns:
            Number of fragments updated
        """
        fragments = self.db.get_fragments_by_user(
            user_id=user_id,
            include_expired=False,
            limit=1000,
        )

        updated = 0
        for fragment, _ in fragments:
            new_salience = max(0.0, fragment.salience - (fragment.decay_rate * hours_passed))
            if new_salience != fragment.salience:
                self.db.update_fragment_salience(fragment.id, new_salience)
                updated += 1

        return updated

    def promote_to_clustered(
        self,
        fragment_id: str,
        cluster_id: str,
    ) -> bool:
        """Promote a fragment to clustered state with extended TTL.

        Args:
            fragment_id: Fragment to promote
            cluster_id: Cluster it's joining

        Returns:
            True if promoted, False if fragment not found
        """
        fragment = self.db.get_fragment(fragment_id)
        if fragment is None:
            return False

        # Update state and extend TTL
        self.db.update_fragment_state(fragment_id, LifecycleState.CLUSTERED)

        # Set new TTL (24 hours for clustered)
        new_ttl = DEFAULT_TTL[LifecycleState.CLUSTERED]
        new_expires = datetime.utcnow() + timedelta(seconds=new_ttl)
        self.db.refresh_fragment(fragment_id, new_expires)

        return True

    def find_similar(
        self,
        content: str,
        user_id: str,
        limit: int = 10,
        min_similarity: float = 0.5,
    ) -> list[tuple[Fragment, float]]:
        """Find fragments similar to given content.

        Args:
            content: Content to search for
            user_id: User ID to search within
            limit: Maximum results
            min_similarity: Minimum similarity threshold

        Returns:
            List of (fragment, similarity) tuples
        """
        # Get query embedding
        query_embedding = self.embedder.encode_single(content, is_query=True)

        # Get all user fragments with embeddings
        results = self.db.get_fragments_by_user(
            user_id=user_id,
            include_expired=False,
            limit=500,  # Get more to filter
        )

        # Score by similarity
        scored = []
        for fragment, embedding in results:
            if embedding is not None:
                similarity = self.embedder.similarity(query_embedding, embedding)
                if similarity >= min_similarity:
                    scored.append((fragment, similarity))

        # Sort by similarity descending
        scored.sort(key=lambda x: x[1], reverse=True)

        return scored[:limit]

    def cleanup_expired(self) -> int:
        """Delete all expired fragments.

        Returns:
            Number of fragments deleted
        """
        return self.db.cleanup_expired_fragments()

    def delete(self, fragment_id: str) -> bool:
        """Delete a fragment.

        Args:
            fragment_id: Fragment ID to delete

        Returns:
            True if deleted, False if not found
        """
        return self.db.delete_fragment(fragment_id)

    def _sanitize_content(self, content: str) -> str:
        """Sanitize fragment content."""
        if not isinstance(content, str):
            content = str(content)

        # Remove control characters except newlines and tabs
        content = "".join(
            char for char in content
            if char == "\n" or char == "\t" or (ord(char) >= 32 and ord(char) != 127)
        )

        # Limit length (shorter than Mind MCP since these are fragments)
        max_chars = 8000
        if len(content) > max_chars:
            content = content[:max_chars]

        return content.strip()

    def to_response(self, fragment: Fragment) -> dict[str, Any]:
        """Convert fragment to API response format."""
        return {
            "id": fragment.id,
            "user_id": fragment.user_id,
            "content": fragment.content,
            "state": fragment.state.value,
            "salience": fragment.salience,
            "domains": fragment.domains,
            "tags": fragment.tags,
            "created_at": fragment.created_at.isoformat(),
            "expires_at": fragment.expires_at.isoformat() if fragment.expires_at else None,
            "time_remaining_seconds": self._time_remaining(fragment),
        }

    def _time_remaining(self, fragment: Fragment) -> int | None:
        """Calculate seconds remaining before expiry."""
        if fragment.expires_at is None:
            return None
        remaining = (fragment.expires_at - datetime.utcnow()).total_seconds()
        return max(0, int(remaining))
