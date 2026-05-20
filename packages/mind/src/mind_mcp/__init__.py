"""Mind MCP v2.1 - Long-term memory server for Claude with cognitive memory types.

Enhanced with:
- Cognitive memory types (episodic, semantic, procedural, preference, reflection)
- Multi-factor scoring: S_i = α·sim(q,m_i) + β·I_i + γ·R_i - δ·A_i
- Reflection jobs for periodic insight generation
- Contradiction detection and handling
"""

__version__ = "2.1.0"

from .models import (
    Memory,
    Decision,
    RetrievalResult,
    Conflict,
    Reflection,
    MemoryType,
    ConflictStatus,
)
from .database import Database
from .embeddings import EmbeddingModel
from .memory import MemoryStore
from .retrieval import HybridRetriever
from .decisions import DecisionTracker
from .contradiction import ConflictDetector
from .reflection import ReflectionJob

__all__ = [
    # Models
    "Memory",
    "Decision",
    "RetrievalResult",
    "Conflict",
    "Reflection",
    "MemoryType",
    "ConflictStatus",
    # Core components
    "Database",
    "EmbeddingModel",
    "MemoryStore",
    "HybridRetriever",
    "DecisionTracker",
    # New v2.1 components
    "ConflictDetector",
    "ReflectionJob",
]
