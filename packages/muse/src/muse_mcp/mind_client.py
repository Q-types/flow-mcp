"""Mind MCP client for Muse MCP integration.

Provides a wrapper around Mind MCP tool calls for seamless integration
between Muse (working memory) and Mind (long-term memory).
"""

from __future__ import annotations

import json
import subprocess
from typing import Any


class MindClient:
    """Client for interacting with Mind MCP.

    This client wraps Mind MCP tool calls, allowing Muse to:
    - Retrieve memories for associations
    - Check for contradictions against stored knowledge
    - Promote candidates to long-term memory
    """

    def __init__(self, user_id: str | None = None):
        """Initialize Mind client.

        Args:
            user_id: Default user ID for operations
        """
        self.default_user_id = user_id
        self._available = None

    def is_available(self) -> bool:
        """Check if Mind MCP is available.

        Returns:
            True if Mind MCP responds to health check
        """
        if self._available is not None:
            return self._available

        try:
            result = self.health()
            self._available = result.get("status") == "healthy"
        except Exception:
            self._available = False

        return self._available

    def health(self) -> dict[str, Any]:
        """Check Mind MCP health.

        Returns:
            Health status dict
        """
        # In MCP context, tools are called directly
        # This is a placeholder - actual integration depends on MCP client setup
        return {
            "status": "healthy",
            "note": "Direct MCP tool calls available in server context",
        }

    def remember(
        self,
        content: str,
        user_id: str | None = None,
        memory_type: str = "semantic",
        content_type: str = "observation",
        temporal_level: int = 2,
        salience: float = 1.0,
        importance: float | None = None,
    ) -> dict[str, Any]:
        """Store a memory in Mind MCP.

        Args:
            content: Memory content
            user_id: User ID (uses default if not provided)
            memory_type: Cognitive type (episodic, semantic, procedural, preference)
            content_type: Legacy type (fact, preference, event, goal, observation, decision)
            temporal_level: Persistence level (1=hours, 2=days, 3=months, 4=years)
            salience: Initial importance (0-1)
            importance: Static importance (0-1)

        Returns:
            Result with memory ID
        """
        uid = user_id or self.default_user_id
        if not uid:
            raise ValueError("user_id required")

        return {
            "success": True,
            "tool": "mind_remember",
            "args": {
                "user_id": uid,
                "content": content,
                "memory_type": memory_type,
                "content_type": content_type,
                "temporal_level": temporal_level,
                "salience": salience,
                "importance": importance,
            },
            "note": "Call mcp__mind__mind_remember with these args",
        }

    def retrieve(
        self,
        query: str,
        user_id: str | None = None,
        limit: int = 10,
        min_salience: float = 0.0,
        memory_types: list[str] | None = None,
        include_reflections: bool = True,
    ) -> dict[str, Any]:
        """Retrieve memories from Mind MCP.

        Args:
            query: Search query
            user_id: User ID (uses default if not provided)
            limit: Maximum results
            min_salience: Minimum salience threshold
            memory_types: Filter by memory types
            include_reflections: Include reflection memories

        Returns:
            Retrieved memories
        """
        uid = user_id or self.default_user_id
        if not uid:
            raise ValueError("user_id required")

        return {
            "success": True,
            "tool": "mind_retrieve",
            "args": {
                "user_id": uid,
                "query": query,
                "limit": limit,
                "min_salience": min_salience,
                "memory_types": memory_types,
                "include_reflections": include_reflections,
            },
            "note": "Call mcp__mind__mind_retrieve with these args",
            "memories": [],  # Placeholder - actual memories come from MCP call
        }

    def decide(
        self,
        memory_ids: list[str],
        decision_summary: str,
        outcome_quality: float,
        user_id: str | None = None,
        outcome_signal: str = "agent_feedback",
        memory_scores: dict[str, float] | None = None,
    ) -> dict[str, Any]:
        """Record a decision and update memory salience.

        Args:
            memory_ids: Memory IDs that influenced the decision
            decision_summary: Summary of the decision
            outcome_quality: Quality (-1 to 1)
            user_id: User ID
            outcome_signal: How outcome was detected
            memory_scores: Optional retrieval scores for weighted attribution

        Returns:
            Decision result
        """
        uid = user_id or self.default_user_id
        if not uid:
            raise ValueError("user_id required")

        return {
            "success": True,
            "tool": "mind_decide",
            "args": {
                "user_id": uid,
                "memory_ids": memory_ids,
                "decision_summary": decision_summary,
                "outcome_quality": outcome_quality,
                "outcome_signal": outcome_signal,
                "memory_scores": memory_scores,
            },
            "note": "Call mcp__mind__mind_decide with these args",
        }

    def reflect(
        self,
        user_id: str | None = None,
        force: bool = False,
    ) -> dict[str, Any]:
        """Trigger reflection generation.

        Args:
            user_id: User ID
            force: Force reflection even if not triggered

        Returns:
            Reflection result
        """
        uid = user_id or self.default_user_id
        if not uid:
            raise ValueError("user_id required")

        return {
            "success": True,
            "tool": "mind_reflect",
            "args": {
                "user_id": uid,
                "force": force,
            },
            "note": "Call mcp__mind__mind_reflect with these args",
        }

    def get_conflicts(
        self,
        user_id: str | None = None,
        limit: int = 10,
        include_resolved: bool = False,
    ) -> dict[str, Any]:
        """Get memory conflicts.

        Args:
            user_id: User ID
            limit: Maximum conflicts
            include_resolved: Include resolved conflicts

        Returns:
            Conflicts result
        """
        uid = user_id or self.default_user_id
        if not uid:
            raise ValueError("user_id required")

        return {
            "success": True,
            "tool": "mind_conflicts",
            "args": {
                "user_id": uid,
                "limit": limit,
                "include_resolved": include_resolved,
            },
            "note": "Call mcp__mind__mind_conflicts with these args",
        }


class MindClientAsync:
    """Async Mind MCP client for use in MCP server context.

    This version is designed to be used within the Muse MCP server,
    where it can make direct MCP tool calls.
    """

    def __init__(self, mcp_context: Any = None, user_id: str | None = None):
        """Initialize async Mind client.

        Args:
            mcp_context: MCP server context for making tool calls
            user_id: Default user ID
        """
        self.mcp_context = mcp_context
        self.default_user_id = user_id

    async def retrieve(
        self,
        query: str,
        user_id: str | None = None,
        limit: int = 10,
        min_salience: float = 0.0,
        memory_types: list[str] | None = None,
    ) -> dict[str, Any]:
        """Retrieve memories from Mind MCP asynchronously.

        In MCP server context, this would make an actual tool call.
        For now, returns the call specification.
        """
        uid = user_id or self.default_user_id

        # When integrated with MCP, this would be:
        # result = await self.mcp_context.call_tool("mind_retrieve", {...})

        return {
            "tool": "mind_retrieve",
            "args": {
                "user_id": uid,
                "query": query,
                "limit": limit,
                "min_salience": min_salience,
                "memory_types": memory_types,
            },
            "memories": [],
        }

    async def remember(
        self,
        content: str,
        user_id: str | None = None,
        memory_type: str = "semantic",
        salience: float = 1.0,
        importance: float | None = None,
    ) -> dict[str, Any]:
        """Store a memory in Mind MCP asynchronously."""
        uid = user_id or self.default_user_id

        return {
            "tool": "mind_remember",
            "args": {
                "user_id": uid,
                "content": content,
                "memory_type": memory_type,
                "salience": salience,
                "importance": importance,
            },
        }


# Singleton instance for convenience
_default_client: MindClient | None = None


def get_mind_client(user_id: str | None = None) -> MindClient:
    """Get the default Mind client instance.

    Args:
        user_id: User ID to set as default

    Returns:
        MindClient instance
    """
    global _default_client
    if _default_client is None:
        _default_client = MindClient(user_id)
    elif user_id:
        _default_client.default_user_id = user_id
    return _default_client
