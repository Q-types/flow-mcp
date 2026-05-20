"""Reflection job system for Mind MCP v2.

Periodic reflection process that analyzes patterns, unresolved goals,
decisions, contradictions, and generates compressed insights.

Reflections are "compressed gradients through experience" - they distill
raw noisy memories into higher-order patterns and lessons learned.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Any
from collections import Counter

import numpy as np

from .database import Database
from .embeddings import EmbeddingModel
from .models import Memory, Reflection, MemoryType


# Default trigger: run reflection every N memories
DEFAULT_REFLECTION_TRIGGER_COUNT = 50

# Minimum memories needed for reflection
MIN_MEMORIES_FOR_REFLECTION = 10

# How far back to look for memories (in days)
REFLECTION_LOOKBACK_DAYS = 30

# Number of clusters for theme detection
NUM_THEME_CLUSTERS = 5


class ReflectionJob:
    """Generates periodic reflections from memory analysis."""

    def __init__(
        self,
        db: Database,
        embedder: EmbeddingModel,
        trigger_count: int = DEFAULT_REFLECTION_TRIGGER_COUNT,
    ):
        """Initialize reflection job.

        Args:
            db: Database instance
            embedder: Embedding model for clustering
            trigger_count: Number of memories before triggering reflection
        """
        self.db = db
        self.embedder = embedder
        self.trigger_count = trigger_count

    def should_trigger(self, user_id: str) -> bool:
        """Check if reflection should be triggered for a user.

        Args:
            user_id: User ID to check

        Returns:
            True if reflection should run
        """
        count = self.db.get_memory_count_since_last_reflection(user_id)
        return count >= self.trigger_count

    def generate_reflection(
        self,
        user_id: str,
        trigger: str = "count",
        force: bool = False,
    ) -> Reflection | None:
        """Generate a reflection for a user's recent memories.

        Args:
            user_id: User ID to reflect on
            trigger: What triggered this reflection (count, manual, event)
            force: Run even if trigger count not reached

        Returns:
            Generated Reflection or None if not enough data
        """
        if not force and not self.should_trigger(user_id):
            return None

        # Get recent memories
        memory_data = self.db.get_memories_by_user(
            user_id=user_id,
            limit=500,
            min_salience=0.0,
        )

        if len(memory_data) < MIN_MEMORIES_FOR_REFLECTION:
            return None

        memories = [m for m, _ in memory_data]
        embeddings = [e for _, e in memory_data if e is not None]

        # Filter to recent memories for this reflection
        cutoff = datetime.utcnow() - timedelta(days=REFLECTION_LOOKBACK_DAYS)
        recent_memories = [m for m in memories if m.created_at > cutoff]

        if len(recent_memories) < MIN_MEMORIES_FOR_REFLECTION:
            recent_memories = memories[:50]  # Use most recent 50 if not enough in window

        # Analyze memories
        patterns = self._identify_patterns(recent_memories)
        unresolved_goals = self._find_unresolved_goals(recent_memories)
        key_decisions = self._extract_key_decisions(recent_memories)
        contradictions = self._find_contradictions(recent_memories)
        action_items = self._generate_action_items(patterns, unresolved_goals, contradictions)

        # Generate reflection content
        content = self._generate_reflection_content(
            patterns, unresolved_goals, key_decisions, contradictions, action_items
        )

        # Determine time period
        period_start = min(m.created_at for m in recent_memories)
        period_end = max(m.created_at for m in recent_memories)

        # Create reflection
        reflection = Reflection(
            user_id=user_id,
            period_start=period_start,
            period_end=period_end,
            source_memory_ids=[m.id for m in recent_memories],
            memory_count=len(recent_memories),
            content=content,
            patterns=patterns,
            unresolved_goals=unresolved_goals,
            key_decisions=key_decisions,
            contradictions=contradictions,
            action_items=action_items,
            trigger=trigger,
        )

        # Store reflection
        self.db.insert_reflection(reflection)

        # Also store reflection as a memory for future retrieval
        reflection_memory = Memory(
            user_id=user_id,
            content=content,
            memory_type=MemoryType.REFLECTION,
            content_type="observation",
            temporal_level=3,  # Seasonal - reflections are medium-term insights
            salience=0.9,  # High salience for reflections
            importance=0.95,
        )

        # Generate embedding for reflection
        reflection_embedding = self.embedder.encode_single(content)
        self.db.insert_memory(reflection_memory, reflection_embedding)

        return reflection

    def _identify_patterns(self, memories: list[Memory]) -> list[str]:
        """Identify repeated patterns in memories.

        Args:
            memories: List of memories to analyze

        Returns:
            List of identified pattern descriptions
        """
        patterns = []

        # Count memory types
        type_counts = Counter(m.memory_type for m in memories)
        dominant_type = type_counts.most_common(1)[0] if type_counts else None
        if dominant_type and dominant_type[1] > len(memories) * 0.3:
            patterns.append(f"Heavy focus on {dominant_type[0].value} memories ({dominant_type[1]}/{len(memories)})")

        # Find frequently mentioned terms
        all_content = " ".join(m.content.lower() for m in memories)
        words = re.findall(r'\b[a-z]{4,}\b', all_content)
        word_counts = Counter(words)

        # Filter out common words
        common_words = {'that', 'this', 'with', 'from', 'have', 'been', 'were', 'they', 'their', 'about', 'would', 'could', 'should', 'being', 'which'}
        filtered_counts = {w: c for w, c in word_counts.items() if w not in common_words}

        top_terms = [term for term, count in Counter(filtered_counts).most_common(5) if count >= 3]
        if top_terms:
            patterns.append(f"Recurring themes: {', '.join(top_terms)}")

        # Check for time-based patterns
        days_of_week = Counter()
        for m in memories:
            days_of_week[m.created_at.strftime('%A')] += 1

        if days_of_week:
            most_active_day = days_of_week.most_common(1)[0]
            if most_active_day[1] > len(memories) * 0.25:
                patterns.append(f"Most active on {most_active_day[0]}s")

        # Check for project/topic clustering
        project_patterns = re.findall(r'(?:project|building|working on|implementing)\s+(\w+)', all_content)
        if project_patterns:
            top_projects = Counter(project_patterns).most_common(3)
            patterns.append(f"Active projects: {', '.join(p[0] for p in top_projects)}")

        return patterns[:5]  # Limit to 5 patterns

    def _find_unresolved_goals(self, memories: list[Memory]) -> list[str]:
        """Find unresolved goals from memories.

        Args:
            memories: List of memories to analyze

        Returns:
            List of unresolved goal descriptions
        """
        goals = []

        # Look for goal indicators in episodic memories
        goal_patterns = [
            r'(?:need to|should|want to|plan to|going to|will)\s+(.{10,50})',
            r'(?:todo|task|goal):\s*(.{10,50})',
            r'(?:haven\'t|need to finish|incomplete)\s+(.{10,50})',
        ]

        for memory in memories:
            if memory.memory_type == MemoryType.EPISODIC:
                content_lower = memory.content.lower()
                for pattern in goal_patterns:
                    matches = re.findall(pattern, content_lower)
                    for match in matches:
                        goal = match.strip().rstrip('.,;:')
                        if len(goal) > 10 and goal not in goals:
                            goals.append(goal)

        # Look for explicit goals
        goal_memories = [m for m in memories if m.content_type == "goal"]
        for m in goal_memories:
            claim = m.content[:100].strip()
            if claim not in goals:
                goals.append(claim)

        return goals[:5]  # Limit to 5 goals

    def _extract_key_decisions(self, memories: list[Memory]) -> list[str]:
        """Extract key decisions from memories.

        Args:
            memories: List of memories to analyze

        Returns:
            List of key decision descriptions
        """
        decisions = []

        # Look for decision indicators
        decision_patterns = [
            r'(?:decided to|chose to|went with|selected|picked)\s+(.{10,60})',
            r'(?:decision|choice):\s*(.{10,60})',
            r'(?:instead of|rather than|over)\s+(.{10,40})',
        ]

        for memory in memories:
            if memory.content_type == "decision" or memory.memory_type == MemoryType.EPISODIC:
                content_lower = memory.content.lower()
                for pattern in decision_patterns:
                    matches = re.findall(pattern, content_lower)
                    for match in matches:
                        decision = match.strip().rstrip('.,;:')
                        if len(decision) > 10 and decision not in decisions:
                            decisions.append(decision)

        # Also include explicit decision memories
        decision_memories = [m for m in memories if m.content_type == "decision"]
        for m in decision_memories[:3]:  # Top 3 decision memories
            claim = m.content[:100].strip()
            if claim not in decisions:
                decisions.append(claim)

        return decisions[:5]  # Limit to 5 decisions

    def _find_contradictions(self, memories: list[Memory]) -> list[str]:
        """Find potential contradictions in memories.

        Args:
            memories: List of memories to analyze

        Returns:
            List of contradiction descriptions
        """
        contradictions = []

        # Get pending conflicts from database
        if memories:
            user_id = memories[0].user_id
            conflicts = self.db.get_conflicts_by_user(user_id, limit=10)
            for conflict in conflicts:
                if conflict.status.value == "pending":
                    contradictions.append(
                        f"Conflict: '{conflict.old_claim[:50]}...' vs '{conflict.new_claim[:50]}...'"
                    )

        return contradictions[:3]  # Limit to 3 contradictions

    def _generate_action_items(
        self,
        patterns: list[str],
        unresolved_goals: list[str],
        contradictions: list[str],
    ) -> list[str]:
        """Generate suggested action items based on analysis.

        Args:
            patterns: Identified patterns
            unresolved_goals: Unresolved goals
            contradictions: Found contradictions

        Returns:
            List of action items
        """
        actions = []

        # Actions from unresolved goals
        for goal in unresolved_goals[:2]:
            actions.append(f"Complete: {goal}")

        # Actions from contradictions
        if contradictions:
            actions.append("Resolve pending memory conflicts")

        # Actions from patterns
        for pattern in patterns:
            if "heavy focus" in pattern.lower():
                actions.append("Consider diversifying work across different areas")
            elif "recurring themes" in pattern.lower():
                actions.append("Document key learnings from recurring themes")

        return actions[:5]  # Limit to 5 actions

    def _generate_reflection_content(
        self,
        patterns: list[str],
        unresolved_goals: list[str],
        key_decisions: list[str],
        contradictions: list[str],
        action_items: list[str],
    ) -> str:
        """Generate the main reflection text content.

        Args:
            patterns: Identified patterns
            unresolved_goals: Unresolved goals
            key_decisions: Key decisions
            contradictions: Found contradictions
            action_items: Suggested actions

        Returns:
            Formatted reflection content
        """
        sections = []

        sections.append(f"Reflection generated on {datetime.utcnow().strftime('%Y-%m-%d')}")
        sections.append("")

        if patterns:
            sections.append("PATTERNS OBSERVED:")
            for p in patterns:
                sections.append(f"  - {p}")
            sections.append("")

        if key_decisions:
            sections.append("KEY DECISIONS:")
            for d in key_decisions:
                sections.append(f"  - {d}")
            sections.append("")

        if unresolved_goals:
            sections.append("UNRESOLVED GOALS:")
            for g in unresolved_goals:
                sections.append(f"  - {g}")
            sections.append("")

        if contradictions:
            sections.append("CONTRADICTIONS TO RESOLVE:")
            for c in contradictions:
                sections.append(f"  - {c}")
            sections.append("")

        if action_items:
            sections.append("SUGGESTED ACTIONS:")
            for a in action_items:
                sections.append(f"  - {a}")

        return "\n".join(sections)

    def get_recent_reflections(
        self,
        user_id: str,
        limit: int = 5,
    ) -> list[Reflection]:
        """Get recent reflections for a user.

        Args:
            user_id: User ID to get reflections for
            limit: Maximum reflections to return

        Returns:
            List of recent reflections
        """
        return self.db.get_reflections_by_user(user_id, limit)

    def to_response(self, reflection: Reflection | None) -> dict[str, Any]:
        """Convert reflection to API response format.

        Args:
            reflection: Reflection object or None

        Returns:
            API response dict
        """
        if reflection is None:
            return {
                "generated": False,
                "message": "Not enough memories for reflection or trigger count not reached",
            }

        return {
            "generated": True,
            "reflection": reflection.to_dict(),
            "summary": {
                "patterns_count": len(reflection.patterns),
                "goals_count": len(reflection.unresolved_goals),
                "decisions_count": len(reflection.key_decisions),
                "contradictions_count": len(reflection.contradictions),
                "actions_count": len(reflection.action_items),
            },
        }
