"""
Mind MCP Integration for persistent memory.

Enables Architect to:
- Store project decisions and learnings
- Retrieve relevant context from past sessions
- Track decision outcomes for learning
- Build institutional memory across projects

Mind provides a feedback loop that helps Architect learn which
decisions led to good outcomes, improving future recommendations.
"""

from typing import Any, Callable, Awaitable
from dataclasses import dataclass, field
from datetime import datetime
import uuid
import structlog

logger = structlog.get_logger()


# Type alias for MCP tool caller
MCPCaller = Callable[[str, Any], Awaitable[dict[str, Any]]]


@dataclass
class Memory:
    """A memory stored in Mind."""
    id: str
    content: str
    content_type: str
    temporal_level: int
    salience: float
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "content_type": self.content_type,
            "temporal_level": self.temporal_level,
            "salience": self.salience,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class RetrievalResult:
    """Result from Mind retrieval."""
    retrieval_id: str
    memories: list[Memory]
    scores: dict[str, float] = field(default_factory=dict)

    @property
    def memory_ids(self) -> list[str]:
        """Get list of memory IDs for decision tracking."""
        return [m.id for m in self.memories]


@dataclass
class DecisionOutcome:
    """Tracked decision with outcome."""
    decision_id: str
    memory_ids: list[str]
    decision_summary: str
    outcome_quality: float
    outcome_signal: str
    salience_changes: dict[str, float] = field(default_factory=dict)


class MindIntegration:
    """
    Integration with Mind MCP for persistent memory.

    Mind MCP provides:
    - mind_remember: Store memories with temporal levels
    - mind_retrieve: Semantic search for relevant memories
    - mind_decide: Track decisions and outcomes for learning

    Temporal Levels:
    - 1 = immediate (hours) - current session context
    - 2 = situational (days-weeks) - recent patterns
    - 3 = seasonal (months) - recurring patterns
    - 4 = identity (years) - core preferences/patterns

    The Architect uses Mind to:
    1. Store project decisions with context
    2. Retrieve relevant past experiences before planning
    3. Record outcomes to improve future decisions
    """

    def __init__(self, user_id: str | None = None):
        self.user_id = user_id or self._generate_user_id()
        self.connected = False
        self.mcp_caller: MCPCaller | None = None

        # Local cache for when MCP is unavailable
        self._local_memories: dict[str, Memory] = {}
        self._local_decisions: list[DecisionOutcome] = []

    def _generate_user_id(self) -> str:
        """Generate a valid UUID for user identification."""
        return str(uuid.uuid4())

    def set_user_id(self, user_id: str) -> None:
        """Set the user ID for Mind operations."""
        # Validate UUID format
        try:
            uuid.UUID(user_id)
            self.user_id = user_id
        except ValueError:
            # Generate a new UUID if invalid format provided
            logger.warning("Invalid user_id format, generating new UUID", provided=user_id)
            self.user_id = self._generate_user_id()

    def set_mcp_caller(self, caller: MCPCaller) -> None:
        """Set the MCP tool caller for real integrations."""
        self.mcp_caller = caller
        self.connected = True
        logger.info("Mind MCP caller configured", user_id=self.user_id)

    async def connect(self) -> bool:
        """
        Connect to Mind MCP.

        Verifies the Mind MCP is available and user_id is valid.
        """
        if self.mcp_caller:
            try:
                # Test connection with health check
                result = await self.mcp_caller("mind_health", {})
                if result.get("status") == "healthy":
                    self.connected = True
                    logger.info("Connected to Mind MCP", user_id=self.user_id)
                    return True
            except Exception as e:
                logger.warning("Mind MCP connection failed", error=str(e))

        # Fallback to local mode
        self.connected = True  # Local mode always works
        logger.info("Mind operating in local mode", user_id=self.user_id)
        return True

    async def remember(
        self,
        content: str,
        content_type: str = "decision",
        temporal_level: int = 2,
        salience: float = 1.0
    ) -> dict[str, Any]:
        """
        Store a memory in Mind MCP.

        Content Types:
        - fact: Objective information
        - preference: User/project preferences
        - event: Something that happened
        - goal: Objectives and targets
        - observation: Learned patterns
        - decision: Choices made and why

        Args:
            content: The content to remember
            content_type: Type of memory
            temporal_level: How long to persist (1-4)
            salience: Importance 0.0-1.0

        Returns:
            Response with memory ID and confirmation
        """
        logger.info(
            "Remembering in Mind",
            content_preview=content[:50] if len(content) > 50 else content,
            type=content_type,
            level=temporal_level,
            salience=salience
        )

        # Try MCP call first
        if self.mcp_caller:
            try:
                result = await self.mcp_caller("mind_remember", {
                    "user_id": self.user_id,
                    "content": content,
                    "content_type": content_type,
                    "temporal_level": temporal_level,
                    "salience": salience
                })

                if isinstance(result, dict):
                    memory_id = result.get("id") or result.get("memory_id")
                    if memory_id:
                        # Cache locally too
                        self._local_memories[memory_id] = Memory(
                            id=memory_id,
                            content=content,
                            content_type=content_type,
                            temporal_level=temporal_level,
                            salience=salience
                        )
                        return {
                            "success": True,
                            "memory_id": memory_id,
                            "message": f"Stored in Mind: {content[:50]}..."
                        }
            except Exception as e:
                logger.warning("Mind remember MCP call failed", error=str(e))

        # Fallback: Store locally
        memory_id = str(uuid.uuid4())
        self._local_memories[memory_id] = Memory(
            id=memory_id,
            content=content,
            content_type=content_type,
            temporal_level=temporal_level,
            salience=salience
        )

        return {
            "success": True,
            "memory_id": memory_id,
            "message": f"Stored locally: {content[:50]}...",
            "local_only": True
        }

    async def retrieve(
        self,
        query: str,
        limit: int = 10,
        min_salience: float = 0.0
    ) -> RetrievalResult:
        """
        Retrieve relevant memories from Mind MCP.

        Uses multi-source fusion (vector similarity, keywords, salience, recency)
        to find the most relevant memories.

        Args:
            query: Natural language query
            limit: Maximum memories to return
            min_salience: Minimum importance threshold

        Returns:
            RetrievalResult with memories and scores
        """
        logger.info("Retrieving from Mind", query=query[:50], limit=limit)

        # Try MCP call first
        if self.mcp_caller:
            try:
                result = await self.mcp_caller("mind_retrieve", {
                    "user_id": self.user_id,
                    "query": query,
                    "limit": limit,
                    "min_salience": min_salience
                })

                if isinstance(result, dict):
                    memories = []
                    scores = {}
                    retrieval_id = result.get("retrieval_id", str(uuid.uuid4()))

                    for mem_data in result.get("memories", []):
                        memory = Memory(
                            id=mem_data.get("id", str(uuid.uuid4())),
                            content=mem_data.get("content", ""),
                            content_type=mem_data.get("content_type", "observation"),
                            temporal_level=mem_data.get("temporal_level", 2),
                            salience=mem_data.get("salience", 0.5)
                        )
                        memories.append(memory)
                        scores[memory.id] = mem_data.get("score", 0.5)

                    return RetrievalResult(
                        retrieval_id=retrieval_id,
                        memories=memories,
                        scores=scores
                    )
            except Exception as e:
                logger.warning("Mind retrieve MCP call failed", error=str(e))

        # Fallback: Search local memories
        query_lower = query.lower()
        matching_memories = []

        for memory in self._local_memories.values():
            if memory.salience >= min_salience:
                # Simple keyword matching
                if any(word in memory.content.lower() for word in query_lower.split()):
                    matching_memories.append(memory)

        # Sort by salience and limit
        matching_memories.sort(key=lambda m: m.salience, reverse=True)
        matching_memories = matching_memories[:limit]

        return RetrievalResult(
            retrieval_id=str(uuid.uuid4()),
            memories=matching_memories,
            scores={m.id: m.salience for m in matching_memories}
        )

    async def record_decision(
        self,
        memory_ids: list[str],
        decision_summary: str,
        outcome_quality: float,
        outcome_signal: str = "agent_feedback",
        memory_scores: dict[str, float] | None = None
    ) -> DecisionOutcome:
        """
        Record a decision outcome for learning.

        This creates a feedback loop that helps Mind learn
        which memories are useful for good decisions.

        Good outcomes (+quality) increase memory salience.
        Bad outcomes (-quality) decrease salience.

        Outcome Signals:
        - "user_accepted": User explicitly approved
        - "user_rejected": User explicitly rejected
        - "task_completed": Task finished successfully
        - "agent_feedback": Agent's own assessment

        Args:
            memory_ids: Memories that influenced this decision
            decision_summary: What was decided (no PII)
            outcome_quality: How well it worked (-1.0 to 1.0)
            outcome_signal: How outcome was detected
            memory_scores: Optional retrieval scores for attribution

        Returns:
            DecisionOutcome with salience changes
        """
        logger.info(
            "Recording decision in Mind",
            decision=decision_summary[:50],
            outcome=outcome_quality,
            memory_count=len(memory_ids)
        )

        # Try MCP call first
        if self.mcp_caller:
            try:
                params: dict[str, Any] = {
                    "user_id": self.user_id,
                    "memory_ids": memory_ids,
                    "decision_summary": decision_summary,
                    "outcome_quality": outcome_quality,
                    "outcome_signal": outcome_signal
                }
                if memory_scores:
                    params["memory_scores"] = memory_scores

                result = await self.mcp_caller("mind_decide", params)

                if isinstance(result, dict):
                    outcome = DecisionOutcome(
                        decision_id=result.get("decision_id", str(uuid.uuid4())),
                        memory_ids=memory_ids,
                        decision_summary=decision_summary,
                        outcome_quality=outcome_quality,
                        outcome_signal=outcome_signal,
                        salience_changes=result.get("salience_changes", {})
                    )
                    self._local_decisions.append(outcome)
                    return outcome
            except Exception as e:
                logger.warning("Mind decide MCP call failed", error=str(e))

        # Fallback: Track locally
        outcome = DecisionOutcome(
            decision_id=str(uuid.uuid4()),
            memory_ids=memory_ids,
            decision_summary=decision_summary,
            outcome_quality=outcome_quality,
            outcome_signal=outcome_signal,
            salience_changes={}
        )

        # Update local memory salience based on outcome
        for memory_id in memory_ids:
            if memory_id in self._local_memories:
                memory = self._local_memories[memory_id]
                # Adjust salience: positive outcomes increase, negative decrease
                adjustment = outcome_quality * 0.1
                new_salience = max(0.0, min(1.0, memory.salience + adjustment))
                outcome.salience_changes[memory_id] = new_salience - memory.salience
                memory.salience = new_salience

        self._local_decisions.append(outcome)
        return outcome

    # --- Architect-specific convenience methods ---

    async def remember_project_decision(
        self,
        project_name: str,
        decision: str,
        reason: str
    ) -> dict[str, Any]:
        """Store a project decision with context."""
        content = f"Project '{project_name}': Decided to {decision} because {reason}"
        return await self.remember(
            content=content,
            content_type="decision",
            temporal_level=3,  # months - project decisions are long-term
            salience=0.8
        )

    async def remember_team_structure(
        self,
        project_type: str,
        structure: str
    ) -> dict[str, Any]:
        """Store effective team structure patterns."""
        content = f"For {project_type} projects, effective team structure: {structure}"
        return await self.remember(
            content=content,
            content_type="fact",
            temporal_level=4,  # years - architecture patterns persist
            salience=0.9
        )

    async def remember_integration_lesson(
        self,
        issue: str,
        solution: str
    ) -> dict[str, Any]:
        """Store integration lessons learned."""
        content = f"Integration issue: {issue}. Solution: {solution}"
        return await self.remember(
            content=content,
            content_type="observation",
            temporal_level=3,
            salience=0.7
        )

    async def remember_user_preference(
        self,
        preference: str,
        context: str
    ) -> dict[str, Any]:
        """Store user preferences."""
        content = f"User prefers {preference} for {context}"
        return await self.remember(
            content=content,
            content_type="preference",
            temporal_level=4,  # years - preferences persist
            salience=0.9
        )

    async def remember_sprint_outcome(
        self,
        project_name: str,
        sprint_name: str,
        outcome: str
    ) -> dict[str, Any]:
        """Store sprint outcomes for pattern learning."""
        content = f"Sprint '{sprint_name}' in '{project_name}': {outcome}"
        return await self.remember(
            content=content,
            content_type="event",
            temporal_level=2,  # weeks - recent history
            salience=0.6
        )

    async def get_relevant_context(
        self,
        project_idea: str,
        project_type: str | None = None
    ) -> RetrievalResult:
        """Retrieve context relevant to a new project."""
        query_parts = [project_idea]
        if project_type:
            query_parts.append(f"type:{project_type}")
        query_parts.append("decisions patterns lessons")

        query = " ".join(query_parts)
        return await self.retrieve(query, limit=10, min_salience=0.3)

    async def learn_from_outcome(
        self,
        retrieval_result: RetrievalResult,
        decision_summary: str,
        success: bool
    ) -> DecisionOutcome:
        """Simple learning interface for Architect."""
        outcome_quality = 0.8 if success else -0.5
        return await self.record_decision(
            memory_ids=retrieval_result.memory_ids,
            decision_summary=decision_summary,
            outcome_quality=outcome_quality,
            outcome_signal="task_completed" if success else "agent_feedback",
            memory_scores=retrieval_result.scores
        )


# Suggested memories to store for Architect:

ARCHITECT_MEMORY_TEMPLATES = {
    "project_decision": {
        "content_type": "decision",
        "temporal_level": 3,  # Months - project decisions are long-term
        "template": "Project '{project}': Decided to {decision} because {reason}"
    },
    "team_structure": {
        "content_type": "fact",
        "temporal_level": 4,  # Years - architecture patterns are persistent
        "template": "For {project_type} projects, effective team structure: {structure}"
    },
    "integration_lesson": {
        "content_type": "observation",
        "temporal_level": 3,
        "template": "Integration issue: {issue}. Solution: {solution}"
    },
    "user_preference": {
        "content_type": "preference",
        "temporal_level": 4,
        "template": "User prefers {preference} for {context}"
    },
    "sprint_outcome": {
        "content_type": "event",
        "temporal_level": 2,  # Days/weeks - sprint outcomes are medium-term
        "template": "Sprint '{sprint}' in '{project}': {outcome}"
    }
}


# Mind integration workflow for Architect:

MIND_WORKFLOW = """
## Mind Integration Workflow

### At Project Start
```python
# 1. Retrieve relevant context before planning
context = await mind.get_relevant_context(
    project_idea=idea,
    project_type="saas"  # or detected type
)

# 2. Use context to inform planning
if context.memories:
    for memory in context.memories:
        # Consider past lessons in planning
        pass
```

### During Execution
```python
# 3. Store important decisions
await mind.remember_project_decision(
    project_name="MyProject",
    decision="use Supabase for auth",
    reason="team has prior experience"
)

# 4. Store lessons learned
await mind.remember_integration_lesson(
    issue="Frontend-API type mismatch",
    solution="Generate types from API schema"
)
```

### At Sprint Completion
```python
# 5. Record outcomes for learning
await mind.remember_sprint_outcome(
    project_name="MyProject",
    sprint_name="Sprint 1",
    outcome="Foundation complete, all tests passing"
)

# 6. Feed back to Mind for learning
await mind.learn_from_outcome(
    retrieval_result=context,  # From step 1
    decision_summary="Used past patterns for team structure",
    success=True
)
```

### Memory Best Practices
- Store decisions WITH reasoning
- Record both successes and failures
- Use appropriate temporal levels
- Higher salience for critical decisions
- Retrieve before planning new work
"""
