"""MCP server for Mind v2 - Long-term memory with semantic search.

Enhanced with:
- Cognitive memory types (episodic, semantic, procedural, preference, reflection)
- Multi-factor scoring: S_i = α·sim(q,m_i) + β·I_i + γ·R_i - δ·A_i
- Reflection jobs for periodic insight generation
- Contradiction detection and handling

Environment Variables:
- MIND_DB_PATH: Path to SQLite database (default: ~/.mind/mind.db)
- MIND_MODEL: Embedding model name (default: all-MiniLM-L6-v2)
- MIND_DEFAULT_USER: Default user_id when not provided (default: qtypes)
"""

from __future__ import annotations

import os
from typing import Any


# Default user ID - used when user_id not provided or empty
DEFAULT_USER_ID = os.environ.get("MIND_DEFAULT_USER", "qtypes")

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from .database import Database
from .embeddings import EmbeddingModel
from .memory import MemoryStore
from .retrieval import HybridRetriever
from .decisions import DecisionTracker
from .contradiction import ConflictDetector
from .reflection import ReflectionJob
from .models import MemoryType


# Initialize server
server = Server("mind-mcp")

# Lazy-loaded components
_db: Database | None = None
_embedder: EmbeddingModel | None = None
_memory_store: MemoryStore | None = None
_retriever: HybridRetriever | None = None
_decision_tracker: DecisionTracker | None = None
_conflict_detector: ConflictDetector | None = None
_reflection_job: ReflectionJob | None = None


def get_db() -> Database:
    """Get or create database instance."""
    global _db
    if _db is None:
        db_path = os.environ.get("MIND_DB_PATH")
        _db = Database(db_path)
    return _db


def get_embedder() -> EmbeddingModel:
    """Get or create embedding model instance."""
    global _embedder
    if _embedder is None:
        model_name = os.environ.get("MIND_MODEL")
        _embedder = EmbeddingModel(model_name)
    return _embedder


def get_memory_store() -> MemoryStore:
    """Get or create memory store instance."""
    global _memory_store
    if _memory_store is None:
        _memory_store = MemoryStore(get_db(), get_embedder())
    return _memory_store


def get_retriever() -> HybridRetriever:
    """Get or create retriever instance."""
    global _retriever
    if _retriever is None:
        _retriever = HybridRetriever(get_db(), get_embedder())
    return _retriever


def get_decision_tracker() -> DecisionTracker:
    """Get or create decision tracker instance."""
    global _decision_tracker
    if _decision_tracker is None:
        _decision_tracker = DecisionTracker(get_db())
    return _decision_tracker


def get_conflict_detector() -> ConflictDetector:
    """Get or create conflict detector instance."""
    global _conflict_detector
    if _conflict_detector is None:
        _conflict_detector = ConflictDetector(get_db(), get_embedder())
    return _conflict_detector


def get_reflection_job() -> ReflectionJob:
    """Get or create reflection job instance."""
    global _reflection_job
    if _reflection_job is None:
        _reflection_job = ReflectionJob(get_db(), get_embedder())
    return _reflection_job


# --- Tool definitions ---

@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available MCP tools."""
    return [
        Tool(
            name="mind_health",
            description="Check Mind MCP health status and get model info.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        Tool(
            name="mind_remember",
            description="""Store a memory with semantic embedding for later retrieval.

Memory Types (cognitive classification):
- episodic: Events, tasks, what happened (timestamped, contextual)
- semantic: Distilled knowledge, facts, domain expertise
- procedural: Workflows, how-to patterns, best practices
- preference: User/project style, communication preferences
- reflection: Meta-insights, patterns across memories (auto-generated)

Content Types (legacy, auto-mapped to memory_type):
- fact → semantic
- preference → preference
- event → episodic
- goal → episodic
- observation → semantic
- decision → episodic

Temporal Levels:
- 1: immediate (hours) - current session context
- 2: situational (days-weeks) - recent patterns
- 3: seasonal (months) - recurring patterns
- 4: identity (years) - core preferences""",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "User ID for this memory (default: MIND_DEFAULT_USER env var or 'qtypes')",
                    },
                    "content": {
                        "type": "string",
                        "description": "The memory content (will be embedded for semantic search)",
                    },
                    "memory_type": {
                        "type": "string",
                        "description": "Cognitive type: episodic, semantic, procedural, preference",
                        "enum": ["episodic", "semantic", "procedural", "preference"],
                    },
                    "content_type": {
                        "type": "string",
                        "description": "Legacy type (auto-mapped): fact, preference, event, goal, observation, decision",
                        "default": "observation",
                    },
                    "temporal_level": {
                        "type": "integer",
                        "description": "Persistence level: 1=hours, 2=days, 3=months, 4=years",
                        "default": 2,
                    },
                    "salience": {
                        "type": "number",
                        "description": "Initial importance from 0.0 to 1.0",
                        "default": 1.0,
                    },
                    "importance": {
                        "type": "number",
                        "description": "Static importance score 0.0-1.0 (defaults by type)",
                    },
                },
                "required": ["content"],
            },
        ),
        Tool(
            name="mind_retrieve",
            description="""Retrieve relevant memories using hybrid semantic + keyword search.

Enhanced scoring formula: S_i = α·sim(q,m_i) + β·I_i + γ·R_i - δ·A_i
Where: sim=similarity, I=importance, R=recency boost, A=age decay.

Coefficients vary by memory type for optimal retrieval:
- episodic: Higher recency weight (events are time-sensitive)
- semantic: Higher importance weight (facts should persist)
- procedural: Balanced (workflows are stable but contextual)
- preference: High importance, low decay (preferences rarely change)
- reflection: Highest importance (meta-insights are valuable)

Uses multi-source fusion and updates access timestamps for retrieved memories.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "User ID to search (default: MIND_DEFAULT_USER env var or 'qtypes')",
                    },
                    "query": {
                        "type": "string",
                        "description": "Natural language query describing what you need",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of memories to return (1-100)",
                        "default": 10,
                    },
                    "min_salience": {
                        "type": "number",
                        "description": "Minimum salience threshold (0.0-1.0)",
                        "default": 0.0,
                    },
                    "memory_types": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Filter to specific memory types: episodic, semantic, procedural, preference",
                    },
                    "include_reflections": {
                        "type": "boolean",
                        "description": "Include reflection-type memories in results",
                        "default": True,
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="mind_decide",
            description="""Track a decision and record its outcome for learning.

This creates a feedback loop that helps Mind learn which memories are useful.
Good outcomes (+quality) increase memory salience, making those memories
more likely to be retrieved in similar future situations.
Bad outcomes (-quality) decrease salience.

Outcome Signals:
- user_accepted: User explicitly approved
- user_rejected: User explicitly rejected
- task_completed: Task finished successfully
- agent_feedback: Agent's own assessment""",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "User ID (default: MIND_DEFAULT_USER env var or 'qtypes')",
                    },
                    "memory_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of memory IDs that influenced this decision",
                    },
                    "decision_summary": {
                        "type": "string",
                        "description": "Short summary of what was decided (no PII)",
                    },
                    "outcome_quality": {
                        "type": "number",
                        "description": "How well did it work? -1.0 (bad) to 1.0 (good)",
                    },
                    "outcome_signal": {
                        "type": "string",
                        "description": "How was outcome detected?",
                        "default": "agent_feedback",
                    },
                    "memory_scores": {
                        "type": "object",
                        "description": "Optional dict mapping memory_id to retrieval score for weighted attribution",
                    },
                },
                "required": ["memory_ids", "decision_summary", "outcome_quality"],
            },
        ),
        Tool(
            name="mind_reflect",
            description="""Generate a reflection from recent memories.

Reflections analyze patterns, unresolved goals, decisions, contradictions,
and generate compressed insights. They are "compressed gradients through
experience" - distilling raw noisy memories into higher-order lessons.

Triggers automatically every 50 memories, or can be forced manually.
Reflections are stored as special 'reflection' type memories for future retrieval.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "User ID to reflect on (default: MIND_DEFAULT_USER env var or 'qtypes')",
                    },
                    "force": {
                        "type": "boolean",
                        "description": "Run reflection even if trigger count not reached",
                        "default": False,
                    },
                },
                "required": [],
            },
        ),
        Tool(
            name="mind_conflicts",
            description="""Get unresolved memory conflicts for a user.

Conflicts are detected when new memories semantically contradict existing ones.
Returns pending conflicts that may need manual resolution.

Use this to identify semantic drift and maintain memory consistency.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "User ID (default: MIND_DEFAULT_USER env var or 'qtypes')",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum conflicts to return",
                        "default": 10,
                    },
                    "include_resolved": {
                        "type": "boolean",
                        "description": "Include resolved conflicts",
                        "default": False,
                    },
                },
                "required": [],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle tool calls."""
    try:
        if name == "mind_health":
            result = await handle_health()
        elif name == "mind_remember":
            result = await handle_remember(arguments)
        elif name == "mind_retrieve":
            result = await handle_retrieve(arguments)
        elif name == "mind_decide":
            result = await handle_decide(arguments)
        elif name == "mind_reflect":
            result = await handle_reflect(arguments)
        elif name == "mind_conflicts":
            result = await handle_conflicts(arguments)
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
    """Handle mind_health tool."""
    db = get_db()
    embedder = get_embedder()

    stats = db.get_stats()
    model_info = embedder.get_info()

    return {
        "status": "healthy",
        "version": "2.0.0",
        "model": model_info,
        "database": stats,
    }


async def handle_remember(args: dict[str, Any]) -> dict[str, Any]:
    """Handle mind_remember tool."""
    user_id = args.get("user_id") or DEFAULT_USER_ID
    content = args["content"]
    content_type = args.get("content_type", "observation")
    temporal_level = args.get("temporal_level", 2)
    salience = args.get("salience", 1.0)
    importance = args.get("importance")  # None means use type default
    memory_type_str = args.get("memory_type")  # New: explicit memory type

    # Build kwargs for memory creation
    kwargs = {
        "user_id": user_id,
        "content": content,
        "content_type": content_type,
        "temporal_level": temporal_level,
        "salience": salience,
    }

    if memory_type_str:
        try:
            kwargs["memory_type"] = MemoryType(memory_type_str)
        except ValueError:
            pass  # Fall back to inference from content_type

    if importance is not None:
        kwargs["importance"] = importance

    store = get_memory_store()
    memory = store.create(**kwargs)

    # Check for conflicts with existing memories
    conflicts_detected = []
    try:
        embedder = get_embedder()
        embedding = embedder.encode_single(content)
        detector = get_conflict_detector()
        conflicts = detector.check_for_conflicts(
            new_memory=memory,
            new_embedding=embedding,
            user_id=user_id,
        )
        if conflicts:
            conflicts_detected = [
                {"id": c.id, "status": c.status.value, "old_claim": c.old_claim[:50]}
                for c in conflicts
            ]
    except Exception:
        pass  # Don't fail the remember on conflict detection errors

    # Check if reflection should be triggered
    reflection_triggered = False
    try:
        job = get_reflection_job()
        if job.should_trigger(user_id):
            reflection_triggered = True
    except Exception:
        pass

    response = {
        "success": True,
        "id": memory.id,
        "memory_id": memory.id,
        "memory_type": memory.memory_type.value,
        "importance": memory.importance,
        "message": f"Stored memory: {content[:50]}...",
    }

    if conflicts_detected:
        response["conflicts_detected"] = conflicts_detected
        response["conflict_count"] = len(conflicts_detected)

    if reflection_triggered:
        response["reflection_available"] = True
        response["message"] += " (Reflection available - call mind_reflect)"

    return response


async def handle_retrieve(args: dict[str, Any]) -> dict[str, Any]:
    """Handle mind_retrieve tool."""
    user_id = args.get("user_id") or DEFAULT_USER_ID
    query = args["query"]
    limit = min(100, max(1, args.get("limit", 10)))
    min_salience = max(0.0, min(1.0, args.get("min_salience", 0.0)))
    include_reflections = args.get("include_reflections", True)

    # Parse memory type filter
    memory_types = None
    memory_type_filter = args.get("memory_types")
    if memory_type_filter:
        if isinstance(memory_type_filter, list):
            memory_types = []
            for t in memory_type_filter:
                try:
                    memory_types.append(MemoryType(t))
                except ValueError:
                    pass

    retriever = get_retriever()
    result = retriever.retrieve(
        user_id=user_id,
        query=query,
        limit=limit,
        min_salience=min_salience,
        memory_types=memory_types,
        include_reflections=include_reflections,
    )

    return retriever.to_response(result)


async def handle_decide(args: dict[str, Any]) -> dict[str, Any]:
    """Handle mind_decide tool."""
    user_id = args.get("user_id") or DEFAULT_USER_ID
    memory_ids = args["memory_ids"]
    decision_summary = args["decision_summary"]
    outcome_quality = args["outcome_quality"]
    outcome_signal = args.get("outcome_signal", "agent_feedback")
    memory_scores = args.get("memory_scores")

    tracker = get_decision_tracker()
    decision = tracker.record(
        user_id=user_id,
        memory_ids=memory_ids,
        decision_summary=decision_summary,
        outcome_quality=outcome_quality,
        outcome_signal=outcome_signal,
        memory_scores=memory_scores,
    )

    return tracker.to_response(decision)


async def handle_reflect(args: dict[str, Any]) -> dict[str, Any]:
    """Handle mind_reflect tool."""
    user_id = args.get("user_id") or DEFAULT_USER_ID
    force = args.get("force", False)

    job = get_reflection_job()
    reflection = job.generate_reflection(
        user_id=user_id,
        trigger="manual" if force else "count",
        force=force,
    )

    return job.to_response(reflection)


async def handle_conflicts(args: dict[str, Any]) -> dict[str, Any]:
    """Handle mind_conflicts tool."""
    user_id = args.get("user_id") or DEFAULT_USER_ID
    limit = min(100, max(1, args.get("limit", 10)))
    include_resolved = args.get("include_resolved", False)

    detector = get_conflict_detector()

    if include_resolved:
        conflicts = detector.db.get_conflicts_by_user(user_id, limit=limit)
    else:
        conflicts = detector.get_unresolved_conflicts(user_id, limit=limit)

    return detector.to_response(conflicts)


async def run_server():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )
