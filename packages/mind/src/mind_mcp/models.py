"""Data models for Mind MCP v2.

Enhanced with cognitive science-inspired memory types:
- Episodic: events, tasks, what happened
- Semantic: distilled knowledge, facts, domain expertise
- Procedural: workflows, how-to patterns, best practices
- Preference: user/project style, communication preferences
- Reflection: meta-insights, patterns across memories, lessons learned
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal
from pydantic import BaseModel, Field
import uuid


class MemoryType(str, Enum):
    """Cognitive memory types for enhanced classification."""
    EPISODIC = "episodic"      # Events, tasks, what happened (timestamped, contextual)
    SEMANTIC = "semantic"      # Distilled knowledge, facts, domain expertise
    PROCEDURAL = "procedural"  # Workflows, how-to patterns, best practices
    PREFERENCE = "preference"  # User/project style, communication preferences
    REFLECTION = "reflection"  # Meta-insights, patterns across memories, lessons learned


# Map old content_type to new memory_type for backwards compatibility
CONTENT_TYPE_TO_MEMORY_TYPE = {
    "fact": MemoryType.SEMANTIC,
    "preference": MemoryType.PREFERENCE,
    "event": MemoryType.EPISODIC,
    "goal": MemoryType.EPISODIC,
    "observation": MemoryType.SEMANTIC,
    "decision": MemoryType.EPISODIC,
}

# Default importance scores by memory type
DEFAULT_IMPORTANCE_BY_TYPE = {
    MemoryType.EPISODIC: 0.5,
    MemoryType.SEMANTIC: 0.7,
    MemoryType.PROCEDURAL: 0.8,
    MemoryType.PREFERENCE: 0.9,
    MemoryType.REFLECTION: 0.95,
}

# Decay rates by memory type (per 30 days, 0=no decay, 1=full decay)
DECAY_RATE_BY_TYPE = {
    MemoryType.EPISODIC: 0.3,     # Episodes decay moderately
    MemoryType.SEMANTIC: 0.1,     # Facts decay slowly
    MemoryType.PROCEDURAL: 0.05,  # Procedures are stable
    MemoryType.PREFERENCE: 0.02,  # Preferences rarely change
    MemoryType.REFLECTION: 0.05,  # Reflections are stable insights
}


class Memory(BaseModel):
    """A memory stored in Mind with cognitive type classification."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    content: str

    # New: Cognitive memory type (episodic, semantic, procedural, preference, reflection)
    memory_type: MemoryType = MemoryType.SEMANTIC

    # Legacy: content_type for backwards compatibility
    content_type: str = "observation"  # fact, preference, event, goal, observation, decision

    temporal_level: int = 2  # 1=immediate(hours), 2=situational(days), 3=seasonal(months), 4=identity(years)

    # Salience: dynamic score adjusted by decision outcomes
    salience: float = 1.0  # 0.0-1.0

    # New: Static importance score (type-dependent baseline)
    importance: float = Field(default=0.7)  # 0.0-1.0

    # New: Access tracking for recency calculations
    last_accessed: datetime | None = None
    access_count: int = 0

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime | None = None

    def __init__(self, **data):
        """Initialize with type inference and default importance."""
        # Infer memory_type from content_type if not provided
        if "memory_type" not in data and "content_type" in data:
            content_type = data["content_type"]
            data["memory_type"] = CONTENT_TYPE_TO_MEMORY_TYPE.get(
                content_type, MemoryType.SEMANTIC
            )

        super().__init__(**data)

        # Set default importance based on type if not explicitly set
        if "importance" not in data:
            self.importance = DEFAULT_IMPORTANCE_BY_TYPE.get(self.memory_type, 0.7)

    @property
    def decay_rate(self) -> float:
        """Get decay rate for this memory's type."""
        return DECAY_RATE_BY_TYPE.get(self.memory_type, 0.1)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "content": self.content,
            "memory_type": self.memory_type.value,
            "content_type": self.content_type,  # Backwards compat
            "temporal_level": self.temporal_level,
            "salience": self.salience,
            "importance": self.importance,
            "last_accessed": self.last_accessed.isoformat() if self.last_accessed else None,
            "access_count": self.access_count,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    model_config = {"frozen": False}


class Decision(BaseModel):
    """A tracked decision with outcome."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    memory_ids: list[str]  # Memories that influenced this decision
    decision_summary: str
    outcome_quality: float  # -1.0 (bad) to 1.0 (good)
    outcome_signal: str = "agent_feedback"  # user_accepted, user_rejected, task_completed, agent_feedback
    salience_changes: dict[str, float] = Field(default_factory=dict)  # memory_id -> delta
    created_at: datetime = Field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "memory_ids": self.memory_ids,
            "decision_summary": self.decision_summary,
            "outcome_quality": self.outcome_quality,
            "outcome_signal": self.outcome_signal,
            "salience_changes": self.salience_changes,
            "created_at": self.created_at.isoformat(),
        }

    model_config = {"frozen": False}


class RetrievalResult(BaseModel):
    """Result from memory retrieval."""

    retrieval_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    memories: list[Memory]
    scores: dict[str, float] = Field(default_factory=dict)  # memory_id -> relevance score

    @property
    def memory_ids(self) -> list[str]:
        """Get list of memory IDs for decision tracking."""
        return [m.id for m in self.memories]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "retrieval_id": self.retrieval_id,
            "memories": [m.to_dict() for m in self.memories],
            "scores": self.scores,
        }

    model_config = {"frozen": False}


# Content type descriptions for documentation (legacy)
CONTENT_TYPES = {
    "fact": "Objective information",
    "preference": "User/project preferences",
    "event": "Something that happened",
    "goal": "Objectives and targets",
    "observation": "Learned patterns",
    "decision": "Choices made and why",
}

# Memory type descriptions (new cognitive types)
MEMORY_TYPES = {
    MemoryType.EPISODIC: "Events, tasks, what happened - timestamped contextual memories",
    MemoryType.SEMANTIC: "Distilled knowledge, facts, domain expertise - stable information",
    MemoryType.PROCEDURAL: "Workflows, how-to patterns, best practices - action sequences",
    MemoryType.PREFERENCE: "User/project style, communication preferences - personal attributes",
    MemoryType.REFLECTION: "Meta-insights, patterns across memories, lessons learned - higher-order",
}

# Temporal level descriptions
TEMPORAL_LEVELS = {
    1: "immediate (hours) - current session context",
    2: "situational (days-weeks) - recent patterns",
    3: "seasonal (months) - recurring patterns",
    4: "identity (years) - core preferences/patterns",
}


class ConflictStatus(str, Enum):
    """Status of a memory conflict."""
    PENDING = "pending"      # Needs resolution
    RESOLVED = "resolved"    # Manually or auto resolved
    SUPERSEDED = "superseded"  # Old memory superseded by new


class Conflict(BaseModel):
    """A detected conflict between two memories."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str

    # The conflicting memories
    old_memory_id: str
    new_memory_id: str
    old_claim: str
    new_claim: str

    # Confidence scores
    old_confidence: float = 0.5  # 0.0-1.0
    new_confidence: float = 0.5  # 0.0-1.0

    # Detection info
    similarity_score: float = 0.0  # How similar the memories are
    conflict_type: str = "semantic"  # semantic, temporal, factual

    # Resolution
    status: ConflictStatus = ConflictStatus.PENDING
    resolution_note: str | None = None
    resolved_at: datetime | None = None

    detected_at: datetime = Field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "old_memory_id": self.old_memory_id,
            "new_memory_id": self.new_memory_id,
            "old_claim": self.old_claim,
            "new_claim": self.new_claim,
            "old_confidence": self.old_confidence,
            "new_confidence": self.new_confidence,
            "similarity_score": self.similarity_score,
            "conflict_type": self.conflict_type,
            "status": self.status.value,
            "resolution_note": self.resolution_note,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "detected_at": self.detected_at.isoformat(),
        }

    model_config = {"frozen": False}


class Reflection(BaseModel):
    """A reflection generated from analyzing memories."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str

    # Time period covered
    period_start: datetime
    period_end: datetime

    # Source memories
    source_memory_ids: list[str] = Field(default_factory=list)
    memory_count: int = 0

    # Reflection content
    content: str  # Main reflection text
    patterns: list[str] = Field(default_factory=list)  # Identified patterns
    unresolved_goals: list[str] = Field(default_factory=list)  # Open goals
    key_decisions: list[str] = Field(default_factory=list)  # Important decisions
    contradictions: list[str] = Field(default_factory=list)  # Found contradictions
    action_items: list[str] = Field(default_factory=list)  # Suggested next steps

    # Metadata
    trigger: str = "count"  # count, manual, event
    created_at: datetime = Field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "source_memory_ids": self.source_memory_ids,
            "memory_count": self.memory_count,
            "content": self.content,
            "patterns": self.patterns,
            "unresolved_goals": self.unresolved_goals,
            "key_decisions": self.key_decisions,
            "contradictions": self.contradictions,
            "action_items": self.action_items,
            "trigger": self.trigger,
            "created_at": self.created_at.isoformat(),
        }

    model_config = {"frozen": False}
