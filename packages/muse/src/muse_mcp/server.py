"""MCP server for Muse - Associative working memory for creative recombination.

Tools:
- muse_health: Check server status
- muse_expand_prompt: Expand raw prompt into rich working object
- muse_retrieve_associations: Multi-mode retrieval from Mind MCP
- muse_generate_analogies: Find cross-domain structural mappings
- muse_find_contradictions: Surface tensions and counter-evidence
- muse_mutate_ideas: Apply transformation operators
- muse_rank_candidates: Score ideas using V formula
- muse_promote_to_mind: Selective consolidation to long-term memory
"""

from __future__ import annotations

import os
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

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
from .mind_client import MindClient, get_mind_client
from .models import RetrievalMode, MutationType


# Initialize server
server = Server("muse-mcp")

# Lazy-loaded components
_db: Database | None = None
_embedder: EmbeddingModel | None = None
_fragment_store: FragmentStore | None = None
_expander: PromptExpander | None = None
_retriever: AssociationRetriever | None = None
_analogy_gen: AnalogyGenerator | None = None
_contradiction_finder: ContradictionFinder | None = None
_mutator: IdeaMutator | None = None
_ranker: CandidateRanker | None = None
_promoter: PromotionManager | None = None
_clusterer: FragmentClusterer | None = None
_mind_client: MindClient | None = None


def get_db() -> Database:
    """Get or create database instance."""
    global _db
    if _db is None:
        db_path = os.environ.get("MUSE_DB_PATH")
        _db = Database(db_path)
    return _db


def get_embedder() -> EmbeddingModel:
    """Get or create embedding model instance."""
    global _embedder
    if _embedder is None:
        model_name = os.environ.get("MUSE_MODEL")
        _embedder = EmbeddingModel(model_name)
    return _embedder


def get_fragment_store() -> FragmentStore:
    """Get or create fragment store instance."""
    global _fragment_store
    if _fragment_store is None:
        _fragment_store = FragmentStore(get_db(), get_embedder())
    return _fragment_store


def get_expander() -> PromptExpander:
    """Get or create prompt expander instance."""
    global _expander
    if _expander is None:
        _expander = PromptExpander(get_db())
    return _expander


def get_retriever() -> AssociationRetriever:
    """Get or create association retriever instance."""
    global _retriever
    if _retriever is None:
        _retriever = AssociationRetriever(get_db(), get_embedder())
    return _retriever


def get_analogy_generator() -> AnalogyGenerator:
    """Get or create analogy generator instance."""
    global _analogy_gen
    if _analogy_gen is None:
        _analogy_gen = AnalogyGenerator(get_db(), get_embedder())
    return _analogy_gen


def get_contradiction_finder() -> ContradictionFinder:
    """Get or create contradiction finder instance."""
    global _contradiction_finder
    if _contradiction_finder is None:
        _contradiction_finder = ContradictionFinder(get_db(), get_embedder())
    return _contradiction_finder


def get_mutator() -> IdeaMutator:
    """Get or create idea mutator instance."""
    global _mutator
    if _mutator is None:
        _mutator = IdeaMutator(get_db(), get_embedder(), get_fragment_store())
    return _mutator


def get_ranker() -> CandidateRanker:
    """Get or create candidate ranker instance."""
    global _ranker
    if _ranker is None:
        _ranker = CandidateRanker(get_db(), get_embedder())
    return _ranker


def get_promoter() -> PromotionManager:
    """Get or create promotion manager instance."""
    global _promoter
    if _promoter is None:
        _promoter = PromotionManager(get_db())
    return _promoter


def get_clusterer() -> FragmentClusterer:
    """Get or create fragment clusterer instance."""
    global _clusterer
    if _clusterer is None:
        _clusterer = FragmentClusterer(get_db(), get_embedder())
    return _clusterer


def get_mind_client_instance(user_id: str | None = None) -> MindClient:
    """Get or create Mind MCP client instance."""
    global _mind_client
    if _mind_client is None:
        _mind_client = MindClient(user_id)
    elif user_id:
        _mind_client.default_user_id = user_id
    return _mind_client


# --- Tool definitions ---

@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available MCP tools."""
    return [
        Tool(
            name="muse_health",
            description="Check Muse MCP health status and get model info.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        Tool(
            name="muse_expand_prompt",
            description="""Expand a raw prompt into a rich working object.

Converts raw prompts into structured context with:
- Goal: What we're trying to achieve
- Domains: Relevant knowledge areas
- Constraints: Limitations and requirements
- Desired outputs: What success looks like

This is typically the first step in the Muse workflow.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "UUID of the user",
                    },
                    "prompt": {
                        "type": "string",
                        "description": "The raw prompt to expand",
                    },
                    "context": {
                        "type": "object",
                        "description": "Optional additional context (domains, constraints, etc.)",
                    },
                },
                "required": ["user_id", "prompt"],
            },
        ),
        Tool(
            name="muse_retrieve_associations",
            description="""Multi-mode retrieval from Mind MCP for productive associations.

Retrieves using multiple modes:
- nearest: Semantically similar memories
- distant_analogies: Cross-domain structural matches
- past_failures: What went wrong before
- successful_workflows: What worked
- contradictory: Arguments against
- domain_patterns: Established patterns
- user_preferences: User/project style

This goes beyond standard RAG by deliberately fetching productive tension.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "UUID of the user",
                    },
                    "query": {
                        "type": "string",
                        "description": "Query for retrieval",
                    },
                    "modes": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Retrieval modes to use (default: all)",
                    },
                    "limit_per_mode": {
                        "type": "integer",
                        "description": "Max results per mode (default: 5)",
                        "default": 5,
                    },
                },
                "required": ["user_id", "query"],
            },
        ),
        Tool(
            name="muse_generate_analogies",
            description="""Find cross-domain structural mappings.

Creates analogies that connect concepts from different domains
based on structural similarity rather than surface similarity.

Example:
  Source: "KSP estimator: messy knowledge → schema → estimator → feedback"
  Target: "MCP memory: messy experience → memory → retrieval → reflection"

Good analogies have high structural similarity but low surface similarity.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "UUID of the user",
                    },
                    "source_content": {
                        "type": "string",
                        "description": "Source content to find analogies for",
                    },
                    "source_domain": {
                        "type": "string",
                        "description": "Domain of the source (e.g., 'software', 'business')",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum analogies to generate (default: 5)",
                        "default": 5,
                    },
                },
                "required": ["user_id", "source_content", "source_domain"],
            },
        ),
        Tool(
            name="muse_find_contradictions",
            description="""Surface tensions and counter-evidence for ideas.

Acts as an inner critic, asking:
- What stored memory argues against this?
- What assumption is fragile?
- What would make this fail in production?
- What would a skeptical engineer reject?
- What would make this expensive or noisy?

Contradiction types: evidence, assumption, risk, cost, scalability, alternative""",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "UUID of the user",
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to find contradictions for",
                    },
                    "fragment_id": {
                        "type": "string",
                        "description": "Optional fragment ID if content is from a fragment",
                    },
                },
                "required": ["user_id", "content"],
            },
        ),
        Tool(
            name="muse_mutate_ideas",
            description="""Apply transformation operators to generate idea variants.

Mutation types:
- invert: Flip the core assumption
- combine: Merge with another idea
- compress: Simplify to essence
- modularize: Break into components
- make_safer: Reduce risk
- make_explainable: Add clarity
- make_testable: Add verification
- make_sellable: Add appeal
- scale_up: Expand scope
- scale_down: Narrow focus""",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "UUID of the user",
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to mutate",
                    },
                    "fragment_id": {
                        "type": "string",
                        "description": "Optional source fragment ID",
                    },
                    "mutation_types": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Which mutations to apply (default: all)",
                    },
                    "create_fragments": {
                        "type": "boolean",
                        "description": "Create fragments for results (default: true)",
                        "default": True,
                    },
                },
                "required": ["user_id", "content"],
            },
        ),
        Tool(
            name="muse_rank_candidates",
            description="""Score and rank ideas using the value formula.

V = w_u*U + w_n*N + w_f*F + w_a*A - w_r*R

Where:
- U = usefulness (0-1)
- N = novelty (0-1)
- F = feasibility (0-1)
- A = alignment with goals (0-1)
- R = risk/hallucination likelihood (0-1)

Creates a candidate from content and scores it on all dimensions.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "UUID of the user",
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to score (creates a candidate)",
                    },
                    "working_object_id": {
                        "type": "string",
                        "description": "Optional working object ID for alignment scoring",
                    },
                    "weights": {
                        "type": "object",
                        "description": "Custom weights for scoring formula",
                    },
                },
                "required": ["user_id", "content"],
            },
        ),
        Tool(
            name="muse_promote_to_mind",
            description="""Promote a candidate to Mind MCP (long-term memory).

Only promotes candidates that meet criteria:
- Value score >= 0.6
- Usefulness >= 0.5
- Novelty >= 0.4
- Risk <= 0.7

Automatically determines memory type (semantic, procedural, episodic, preference)
based on content analysis.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "UUID of the user",
                    },
                    "candidate_id": {
                        "type": "string",
                        "description": "ID of candidate to promote",
                    },
                    "memory_type": {
                        "type": "string",
                        "description": "Memory type (auto, semantic, procedural, episodic, preference)",
                        "default": "auto",
                    },
                    "reason": {
                        "type": "string",
                        "description": "Optional reason for promotion",
                    },
                },
                "required": ["user_id", "candidate_id"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle tool calls."""
    try:
        if name == "muse_health":
            result = await handle_health()
        elif name == "muse_expand_prompt":
            result = await handle_expand_prompt(arguments)
        elif name == "muse_retrieve_associations":
            result = await handle_retrieve_associations(arguments)
        elif name == "muse_generate_analogies":
            result = await handle_generate_analogies(arguments)
        elif name == "muse_find_contradictions":
            result = await handle_find_contradictions(arguments)
        elif name == "muse_mutate_ideas":
            result = await handle_mutate_ideas(arguments)
        elif name == "muse_rank_candidates":
            result = await handle_rank_candidates(arguments)
        elif name == "muse_promote_to_mind":
            result = await handle_promote_to_mind(arguments)
        else:
            result = {"error": f"Unknown tool: {name}"}

        import json
        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    except Exception as e:
        import json
        import traceback
        return [TextContent(
            type="text",
            text=json.dumps({
                "error": str(e),
                "traceback": traceback.format_exc(),
            }, indent=2),
        )]


async def handle_health() -> dict[str, Any]:
    """Handle muse_health tool."""
    db = get_db()
    embedder = get_embedder()

    stats = db.get_stats()
    model_info = embedder.get_info()

    return {
        "status": "healthy",
        "version": "0.1.0",
        "model": model_info,
        "database": stats,
        "theory": "MIND remembers. Muse recombines. The agent reasons. MIND learns from what survives.",
    }


async def handle_expand_prompt(args: dict[str, Any]) -> dict[str, Any]:
    """Handle muse_expand_prompt tool."""
    user_id = args["user_id"]
    prompt = args["prompt"]
    context = args.get("context")

    expander = get_expander()
    wo = expander.expand(user_id, prompt, context)

    return expander.to_response(wo)


async def handle_retrieve_associations(args: dict[str, Any]) -> dict[str, Any]:
    """Handle muse_retrieve_associations tool."""
    user_id = args["user_id"]
    query = args["query"]
    mode_names = args.get("modes")
    limit_per_mode = args.get("limit_per_mode", 5)

    # Convert mode names to enum
    modes = None
    if mode_names:
        modes = []
        for name in mode_names:
            try:
                modes.append(RetrievalMode(name))
            except ValueError:
                pass

    retriever = get_retriever()

    # Note: In production, you'd pass a Mind MCP client here
    associations = retriever.retrieve_associations(
        user_id=user_id,
        query=query,
        modes=modes,
        limit_per_mode=limit_per_mode,
        mind_client=None,  # TODO: Integrate with Mind MCP client
    )

    return retriever.to_response(associations)


async def handle_generate_analogies(args: dict[str, Any]) -> dict[str, Any]:
    """Handle muse_generate_analogies tool."""
    user_id = args["user_id"]
    source_content = args["source_content"]
    source_domain = args["source_domain"]
    limit = args.get("limit", 5)

    generator = get_analogy_generator()

    # Note: In production, you'd retrieve target memories from Mind MCP
    analogies = generator.generate_analogies(
        user_id=user_id,
        source_content=source_content,
        source_domain=source_domain,
        target_memories=[],  # TODO: Retrieve from Mind MCP
        limit=limit,
    )

    return generator.to_response(analogies)


async def handle_find_contradictions(args: dict[str, Any]) -> dict[str, Any]:
    """Handle muse_find_contradictions tool."""
    user_id = args["user_id"]
    content = args["content"]
    fragment_id = args.get("fragment_id")

    finder = get_contradiction_finder()
    contradictions = finder.find_contradictions(
        user_id=user_id,
        target_content=content,
        target_id=fragment_id,
        target_type="fragment" if fragment_id else "content",
        memories=None,  # TODO: Retrieve from Mind MCP
    )

    return finder.to_response(contradictions)


async def handle_mutate_ideas(args: dict[str, Any]) -> dict[str, Any]:
    """Handle muse_mutate_ideas tool."""
    user_id = args["user_id"]
    content = args["content"]
    fragment_id = args.get("fragment_id")
    mutation_type_names = args.get("mutation_types")
    create_fragments = args.get("create_fragments", True)

    # Convert mutation type names to enum
    mutation_types = None
    if mutation_type_names:
        mutation_types = []
        for name in mutation_type_names:
            try:
                mutation_types.append(MutationType(name))
            except ValueError:
                pass

    mutator = get_mutator()
    mutations = mutator.mutate(
        user_id=user_id,
        source_content=content,
        source_fragment_id=fragment_id,
        mutation_types=mutation_types,
        create_fragments=create_fragments,
    )

    return mutator.to_response(mutations)


async def handle_rank_candidates(args: dict[str, Any]) -> dict[str, Any]:
    """Handle muse_rank_candidates tool."""
    user_id = args["user_id"]
    content = args["content"]
    working_object_id = args.get("working_object_id")
    weights = args.get("weights")

    ranker = get_ranker()

    # Create candidate
    candidate = ranker.create_candidate(
        user_id=user_id,
        content=content,
        source_working_object_id=working_object_id,
    )

    # Get working object if provided
    working_object = None
    if working_object_id:
        working_object = get_db().get_working_object(working_object_id)

    # Score candidate
    candidate = ranker.score_candidate(
        candidate=candidate,
        working_object=working_object,
        existing_memories=None,  # TODO: Retrieve from Mind MCP
        weights=weights,
    )

    return {
        "candidate": candidate.to_dict(),
        "formula": "V = w_u*U + w_n*N + w_f*F + w_a*A - w_r*R",
    }


async def handle_promote_to_mind(args: dict[str, Any]) -> dict[str, Any]:
    """Handle muse_promote_to_mind tool."""
    user_id = args["user_id"]
    candidate_id = args["candidate_id"]
    memory_type = args.get("memory_type", "auto")
    reason = args.get("reason")

    # Get candidate
    candidate = get_db().get_candidate(candidate_id)
    if candidate is None:
        return {"error": f"Candidate not found: {candidate_id}"}

    if candidate.user_id != user_id:
        return {"error": "Candidate does not belong to user"}

    promoter = get_promoter()
    result = promoter.promote_to_mind(
        candidate=candidate,
        mind_client=None,  # TODO: Integrate with Mind MCP client
        memory_type=memory_type,
        reason=reason,
    )

    return promoter.to_response(result)


async def run_server():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )
