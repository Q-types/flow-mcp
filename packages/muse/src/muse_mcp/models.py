"""Data models for Muse MCP - Associative Working Memory.

Memory lifecycle: fragment → cluster → candidate → evaluated → promoted/expired

Value scoring formula: V = w_u*U + w_n*N + w_f*F + w_a*A - w_r*R
Where:
- U = usefulness (0-1)
- N = novelty (0-1)
- F = feasibility (0-1)
- A = alignment with goals (0-1)
- R = risk/hallucination likelihood (0-1)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any
from uuid import uuid4


class LifecycleState(str, Enum):
    """Lifecycle states for transient memories."""
    FRAGMENT = "fragment"      # Raw idea, high decay
    CLUSTERED = "clustered"    # Grouped with related fragments
    CANDIDATE = "candidate"    # Under evaluation
    EVALUATED = "evaluated"    # Scored and ranked
    PROMOTED = "promoted"      # Sent to Mind MCP
    EXPIRED = "expired"        # Decayed and removed


class MutationType(str, Enum):
    """Types of idea mutations."""
    INVERT = "invert"              # Flip the core assumption
    COMBINE = "combine"            # Merge with another idea
    COMPRESS = "compress"          # Simplify to essence
    MODULARIZE = "modularize"      # Break into components
    MAKE_SAFER = "make_safer"      # Reduce risk
    MAKE_EXPLAINABLE = "make_explainable"  # Add clarity
    MAKE_TESTABLE = "make_testable"        # Add verification
    MAKE_SELLABLE = "make_sellable"        # Add appeal
    SCALE_UP = "scale_up"          # Expand scope
    SCALE_DOWN = "scale_down"      # Narrow focus


class RetrievalMode(str, Enum):
    """Modes for multi-modal retrieval from Mind MCP."""
    NEAREST = "nearest"            # Semantically similar
    DISTANT_ANALOGY = "distant_analogy"   # Cross-domain structural match
    PAST_FAILURES = "past_failures"       # What went wrong before
    SUCCESSFUL_WORKFLOWS = "successful_workflows"  # What worked
    CONTRADICTORY = "contradictory"       # Arguments against
    DOMAIN_PATTERNS = "domain_patterns"   # Established patterns
    USER_PREFERENCES = "user_preferences" # User/project style


# Default TTLs by lifecycle state (in seconds)
DEFAULT_TTL = {
    LifecycleState.FRAGMENT: 3600,       # 1 hour
    LifecycleState.CLUSTERED: 86400,     # 24 hours
    LifecycleState.CANDIDATE: 604800,    # 7 days
    LifecycleState.EVALUATED: 604800,    # 7 days
}

# Default decay rates (salience reduction per hour)
DEFAULT_DECAY_RATE = {
    LifecycleState.FRAGMENT: 0.1,        # Fast decay
    LifecycleState.CLUSTERED: 0.05,      # Medium decay
    LifecycleState.CANDIDATE: 0.02,      # Slow decay
    LifecycleState.EVALUATED: 0.01,      # Very slow decay
}

# Default weights for value scoring
DEFAULT_VALUE_WEIGHTS = {
    "usefulness": 0.25,
    "novelty": 0.20,
    "feasibility": 0.25,
    "alignment": 0.20,
    "risk": 0.10,
}


@dataclass
class Fragment:
    """A transient idea fragment with decay.

    Fragments are the atomic unit of Muse MCP - raw ideas that
    decay unless clustered, evaluated, or promoted.
    """
    id: str = field(default_factory=lambda: str(uuid4()))
    user_id: str = ""
    content: str = ""

    # Lifecycle
    state: LifecycleState = LifecycleState.FRAGMENT

    # Source context
    source_prompt: str = ""           # Original prompt that spawned this
    source_working_object_id: str | None = None

    # Decay mechanics
    salience: float = 1.0             # Current importance (decays over time)
    decay_rate: float = 0.1           # Salience reduction per hour
    ttl_seconds: int = 3600           # Time to live

    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_accessed: datetime | None = None
    expires_at: datetime | None = None

    # Relationships
    parent_id: str | None = None      # If derived from another fragment
    cluster_id: str | None = None     # If part of a cluster

    # Tags and metadata
    domains: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.expires_at is None:
            self.expires_at = self.created_at + timedelta(seconds=self.ttl_seconds)

    def is_expired(self) -> bool:
        """Check if fragment has expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at

    def decay(self, hours_passed: float = 1.0) -> float:
        """Apply decay to salience. Returns new salience."""
        self.salience = max(0.0, self.salience - (self.decay_rate * hours_passed))
        return self.salience

    def refresh(self, extend_ttl: bool = True) -> None:
        """Mark as accessed, optionally extending TTL."""
        self.last_accessed = datetime.utcnow()
        if extend_ttl and self.expires_at:
            self.expires_at = datetime.utcnow() + timedelta(seconds=self.ttl_seconds)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "content": self.content,
            "state": self.state.value,
            "source_prompt": self.source_prompt,
            "salience": self.salience,
            "decay_rate": self.decay_rate,
            "ttl_seconds": self.ttl_seconds,
            "created_at": self.created_at.isoformat(),
            "last_accessed": self.last_accessed.isoformat() if self.last_accessed else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "parent_id": self.parent_id,
            "cluster_id": self.cluster_id,
            "domains": self.domains,
            "tags": self.tags,
        }


@dataclass
class WorkingObject:
    """An expanded prompt - rich context for idea generation.

    Converts raw prompts into structured working objects with:
    - Goal: what we're trying to achieve
    - Domains: relevant knowledge areas
    - Constraints: limitations and requirements
    - Desired outputs: what success looks like
    """
    id: str = field(default_factory=lambda: str(uuid4()))
    user_id: str = ""

    # Original input
    raw_prompt: str = ""

    # Expanded structure
    goal: str = ""
    domains: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    desired_outputs: list[str] = field(default_factory=list)

    # Context from Mind MCP
    relevant_memories: list[str] = field(default_factory=list)  # Memory IDs
    relevant_patterns: list[str] = field(default_factory=list)
    relevant_failures: list[str] = field(default_factory=list)

    # Generated fragments
    fragment_ids: list[str] = field(default_factory=list)

    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: datetime | None = None

    def __post_init__(self):
        if self.expires_at is None:
            # Working objects live for 24 hours
            self.expires_at = self.created_at + timedelta(hours=24)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "raw_prompt": self.raw_prompt,
            "goal": self.goal,
            "domains": self.domains,
            "constraints": self.constraints,
            "desired_outputs": self.desired_outputs,
            "relevant_memories": self.relevant_memories,
            "relevant_patterns": self.relevant_patterns,
            "relevant_failures": self.relevant_failures,
            "fragment_ids": self.fragment_ids,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }


@dataclass
class Cluster:
    """A group of related fragments.

    Clusters form when multiple fragments share semantic similarity
    or relate to the same goal/domain.
    """
    id: str = field(default_factory=lambda: str(uuid4()))
    user_id: str = ""

    # Cluster content
    label: str = ""                   # Descriptive label
    summary: str = ""                 # Generated summary of clustered ideas
    fragment_ids: list[str] = field(default_factory=list)

    # Centroid for similarity matching
    centroid_embedding: list[float] | None = None

    # Lifecycle
    state: LifecycleState = LifecycleState.CLUSTERED
    salience: float = 1.0

    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: datetime | None = None

    def __post_init__(self):
        if self.expires_at is None:
            self.expires_at = self.created_at + timedelta(hours=24)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "label": self.label,
            "summary": self.summary,
            "fragment_ids": self.fragment_ids,
            "state": self.state.value,
            "salience": self.salience,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }


@dataclass
class Candidate:
    """An evaluated idea ready for ranking.

    Candidates have been scored on the value dimensions:
    V = w_u*U + w_n*N + w_f*F + w_a*A - w_r*R
    """
    id: str = field(default_factory=lambda: str(uuid4()))
    user_id: str = ""

    # Content
    content: str = ""
    summary: str = ""

    # Source lineage
    source_fragment_ids: list[str] = field(default_factory=list)
    source_cluster_id: str | None = None
    source_working_object_id: str | None = None

    # Value scoring dimensions (0-1)
    usefulness: float = 0.5           # U: How useful is this?
    novelty: float = 0.5              # N: How new/different?
    feasibility: float = 0.5          # F: How achievable?
    alignment: float = 0.5            # A: How aligned with goals?
    risk: float = 0.5                 # R: How risky/uncertain?

    # Computed value score
    value_score: float = 0.0          # V = weighted combination

    # Lifecycle
    state: LifecycleState = LifecycleState.CANDIDATE

    # Promotion tracking
    promoted: bool = False
    promoted_memory_id: str | None = None
    promotion_reason: str | None = None

    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    evaluated_at: datetime | None = None
    promoted_at: datetime | None = None
    expires_at: datetime | None = None

    def __post_init__(self):
        if self.expires_at is None:
            self.expires_at = self.created_at + timedelta(days=7)

    def compute_value(self, weights: dict[str, float] | None = None) -> float:
        """Compute value score using weighted formula."""
        w = weights or DEFAULT_VALUE_WEIGHTS
        self.value_score = (
            w["usefulness"] * self.usefulness +
            w["novelty"] * self.novelty +
            w["feasibility"] * self.feasibility +
            w["alignment"] * self.alignment -
            w["risk"] * self.risk
        )
        return self.value_score

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "content": self.content,
            "summary": self.summary,
            "source_fragment_ids": self.source_fragment_ids,
            "source_cluster_id": self.source_cluster_id,
            "scores": {
                "usefulness": self.usefulness,
                "novelty": self.novelty,
                "feasibility": self.feasibility,
                "alignment": self.alignment,
                "risk": self.risk,
                "value": self.value_score,
            },
            "state": self.state.value,
            "promoted": self.promoted,
            "promoted_memory_id": self.promoted_memory_id,
            "created_at": self.created_at.isoformat(),
            "evaluated_at": self.evaluated_at.isoformat() if self.evaluated_at else None,
            "promoted_at": self.promoted_at.isoformat() if self.promoted_at else None,
        }


@dataclass
class Analogy:
    """A cross-domain structural mapping.

    Analogies connect concepts from different domains based on
    structural similarity rather than surface similarity.

    Example:
        Source: "KSP estimator: messy knowledge → schema → estimator → feedback"
        Target: "MCP memory: messy experience → memory → retrieval → reflection"
    """
    id: str = field(default_factory=lambda: str(uuid4()))
    user_id: str = ""

    # Source domain
    source_domain: str = ""
    source_concept: str = ""
    source_structure: str = ""        # Abstract pattern

    # Target domain
    target_domain: str = ""
    target_concept: str = ""
    target_structure: str = ""

    # Mapping quality
    structural_similarity: float = 0.0   # How well structures match
    surface_distance: float = 0.0        # How different the domains are
    usefulness: float = 0.0              # How productive is this bridge

    # Generated insights
    insights: list[str] = field(default_factory=list)

    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: datetime | None = None

    def __post_init__(self):
        if self.expires_at is None:
            self.expires_at = self.created_at + timedelta(hours=24)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "source": {
                "domain": self.source_domain,
                "concept": self.source_concept,
                "structure": self.source_structure,
            },
            "target": {
                "domain": self.target_domain,
                "concept": self.target_concept,
                "structure": self.target_structure,
            },
            "scores": {
                "structural_similarity": self.structural_similarity,
                "surface_distance": self.surface_distance,
                "usefulness": self.usefulness,
            },
            "insights": self.insights,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class Contradiction:
    """A tension or counter-evidence for an idea.

    Contradictions serve as the "inner critic" - surfacing reasons
    why an idea might fail or assumptions that are fragile.
    """
    id: str = field(default_factory=lambda: str(uuid4()))
    user_id: str = ""

    # The idea being challenged
    target_content: str = ""
    target_fragment_id: str | None = None
    target_candidate_id: str | None = None

    # The contradiction
    contradiction_type: str = ""       # "evidence", "assumption", "risk", "cost"
    contradiction_content: str = ""
    source: str = ""                   # Where this came from (memory ID, analysis, etc.)

    # Strength of contradiction
    severity: float = 0.5              # How serious is this challenge (0-1)
    confidence: float = 0.5            # How confident are we in this (0-1)

    # Resolution
    resolved: bool = False
    resolution: str | None = None

    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "target_content": self.target_content,
            "target_fragment_id": self.target_fragment_id,
            "target_candidate_id": self.target_candidate_id,
            "type": self.contradiction_type,
            "content": self.contradiction_content,
            "source": self.source,
            "severity": self.severity,
            "confidence": self.confidence,
            "resolved": self.resolved,
            "resolution": self.resolution,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class Mutation:
    """A transformation applied to an idea.

    Mutations systematically transform ideas through operations like
    invert, combine, compress, modularize, etc.
    """
    id: str = field(default_factory=lambda: str(uuid4()))
    user_id: str = ""

    # Source
    source_content: str = ""
    source_fragment_id: str | None = None

    # Transformation
    mutation_type: MutationType = MutationType.COMPRESS

    # Result
    result_content: str = ""
    result_fragment_id: str | None = None

    # Quality
    improvement_score: float = 0.0     # Did this help? (-1 to 1)

    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "source_content": self.source_content,
            "source_fragment_id": self.source_fragment_id,
            "mutation_type": self.mutation_type.value,
            "result_content": self.result_content,
            "result_fragment_id": self.result_fragment_id,
            "improvement_score": self.improvement_score,
            "created_at": self.created_at.isoformat(),
        }
