"""Memory operations for Mind MCP v2.

Enhanced with cognitive memory types and importance scoring.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from .database import Database
from .embeddings import EmbeddingModel
from .models import Memory, MemoryType, DEFAULT_IMPORTANCE_BY_TYPE


class MemoryStore:
    """High-level memory operations with automatic embedding."""

    def __init__(self, db: Database, embedder: EmbeddingModel):
        """Initialize memory store.

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
        content_type: str = "observation",
        memory_type: MemoryType | None = None,
        temporal_level: int = 2,
        salience: float = 1.0,
        importance: float | None = None,
    ) -> Memory:
        """Create a new memory with embedding.

        Args:
            user_id: User ID who owns this memory
            content: Memory content text
            content_type: Legacy type (fact, preference, event, goal, observation, decision)
            memory_type: Cognitive type (episodic, semantic, procedural, preference, reflection)
            temporal_level: Persistence level (1=hours, 2=days, 3=months, 4=years)
            salience: Dynamic importance score (0.0-1.0), adjusts based on outcomes
            importance: Static importance score (0.0-1.0), defaults by type

        Returns:
            Created Memory object
        """
        # Validate inputs
        content_type = self._validate_content_type(content_type)
        temporal_level = max(1, min(4, temporal_level))
        salience = max(0.0, min(1.0, salience))

        # Sanitize content
        content = self._sanitize_content(content)

        # Build memory kwargs
        kwargs = {
            "user_id": user_id,
            "content": content,
            "content_type": content_type,
            "temporal_level": temporal_level,
            "salience": salience,
            "created_at": datetime.utcnow(),
        }

        # Handle memory_type (new cognitive type)
        if memory_type is not None:
            kwargs["memory_type"] = memory_type
            # Set default importance for the type if not specified
            if importance is None:
                importance = DEFAULT_IMPORTANCE_BY_TYPE.get(memory_type, 0.7)

        # Handle importance
        if importance is not None:
            kwargs["importance"] = max(0.0, min(1.0, importance))

        # Create memory object
        memory = Memory(**kwargs)

        # Generate embedding
        embedding = self.embedder.encode_single(content, is_query=False)

        # Store in database
        self.db.insert_memory(memory, embedding)

        return memory

    def get(self, memory_id: str) -> Memory | None:
        """Get a memory by ID.

        Args:
            memory_id: Memory ID to retrieve

        Returns:
            Memory object or None if not found
        """
        return self.db.get_memory(memory_id)

    def update_salience(self, memory_id: str, delta: float) -> tuple[float, float] | None:
        """Update memory salience by a delta.

        Args:
            memory_id: Memory ID to update
            delta: Change in salience (-1.0 to 1.0)

        Returns:
            Tuple of (old_salience, new_salience) or None if not found
        """
        memory = self.db.get_memory(memory_id)
        if memory is None:
            return None

        old_salience = memory.salience
        new_salience = max(0.0, min(1.0, old_salience + delta))

        self.db.update_salience(memory_id, new_salience)

        return (old_salience, new_salience)

    def delete(self, memory_id: str) -> bool:
        """Delete a memory.

        Args:
            memory_id: Memory ID to delete

        Returns:
            True if deleted, False if not found
        """
        return self.db.delete_memory(memory_id)

    def _validate_content_type(self, content_type: str) -> str:
        """Validate and normalize content type."""
        valid_types = {"fact", "preference", "event", "goal", "observation", "decision"}
        content_type = content_type.lower().strip()
        if content_type not in valid_types:
            return "observation"
        return content_type

    def _sanitize_content(self, content: str) -> str:
        """Sanitize memory content."""
        if not isinstance(content, str):
            content = str(content)
        # Remove control characters except newlines and tabs
        content = "".join(
            char for char in content
            if char == "\n" or char == "\t" or (ord(char) >= 32 and ord(char) != 127)
        )
        # Limit length (8K tokens ~= 32K chars for safety)
        max_chars = 32000
        if len(content) > max_chars:
            content = content[:max_chars]
        return content.strip()

    def to_response(self, memory: Memory) -> dict[str, Any]:
        """Convert memory to API response format."""
        return {
            "id": memory.id,
            "memory_id": memory.id,  # Alias for compatibility
            "user_id": memory.user_id,
            "content": memory.content,
            "memory_type": memory.memory_type.value,
            "content_type": memory.content_type,  # Legacy, for backwards compat
            "temporal_level": memory.temporal_level,
            "salience": memory.salience,
            "importance": memory.importance,
            "access_count": memory.access_count,
            "last_accessed": memory.last_accessed.isoformat() if memory.last_accessed else None,
            "created_at": memory.created_at.isoformat(),
        }
