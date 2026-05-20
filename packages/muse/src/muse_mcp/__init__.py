"""Muse MCP v0.1 - Associative working-memory server for creative recombination.

Muse MCP is a temporary generative workspace that complements Mind MCP:
- Mind MCP = stores what has mattered (long-term semantic memory)
- Muse MCP = explores what might matter (transient working memory)

Core theory: Associative Working Memory
An MCP that generates useful novelty by combining current context, long-term memory,
semantic retrieval, analogy search, contradiction detection, and controlled mutation.

Value scoring: V = w_u*U + w_n*N + w_f*F + w_a*A - w_r*R
Where: U=usefulness, N=novelty, F=feasibility, A=alignment, R=risk

Memory lifecycle: fragment → cluster → candidate → evaluated insight → promoted memory
"""

__version__ = "0.1.0"

from .models import (
    Fragment,
    WorkingObject,
    Cluster,
    Candidate,
    Analogy,
    Contradiction,
    LifecycleState,
    MutationType,
)
from .database import Database
from .embeddings import EmbeddingModel
from .fragments import FragmentStore
from .expansion import PromptExpander
from .associations import AssociationRetriever
from .analogies import AnalogyGenerator
from .contradictions import ContradictionFinder
from .mutations import IdeaMutator
from .ranking import CandidateRanker
from .promotion import PromotionManager
from .clustering import FragmentClusterer
from .mind_client import MindClient, MindClientAsync, get_mind_client

__all__ = [
    # Models
    "Fragment",
    "WorkingObject",
    "Cluster",
    "Candidate",
    "Analogy",
    "Contradiction",
    "LifecycleState",
    "MutationType",
    # Core components
    "Database",
    "EmbeddingModel",
    "FragmentStore",
    "PromptExpander",
    "AssociationRetriever",
    "AnalogyGenerator",
    "ContradictionFinder",
    "IdeaMutator",
    "CandidateRanker",
    "PromotionManager",
    "FragmentClusterer",
    # Mind integration
    "MindClient",
    "MindClientAsync",
    "get_mind_client",
]


def main():
    """Entry point for the MCP server."""
    import asyncio
    from .server import run_server
    asyncio.run(run_server())
