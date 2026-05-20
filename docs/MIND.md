# Mind MCP

> Persistent semantic memory with learning capabilities

## Overview

Mind MCP provides long-term memory for the Flow stack. It stores experiences, patterns, decisions, and preferences, then retrieves them when relevant. Most importantly, it learns from outcomes - memories that lead to good decisions become more prominent over time.

## Key Features

### Semantic Memory Storage

Store memories with automatic embedding and classification:

```python
mind_remember(
    content="Chose PostgreSQL over MongoDB for this project because of relational data requirements and strong typing needs",
    memory_type="episodic",    # Event/decision
    temporal_level=3           # Months-level persistence
)
```

### Hybrid Retrieval

Combines semantic similarity with keyword matching:

```python
result = mind_retrieve(
    query="database selection decisions",
    limit=5,
    memory_types=["episodic", "semantic"]
)

# Returns memories ranked by:
# - Semantic similarity (cosine)
# - Keyword match (BM25)
# - Importance score
# - Recency boost
# - Age decay penalty
```

### Learning Loop

Track outcomes to improve future retrieval:

```python
# After a successful task
mind_decide(
    memory_ids=["mem_123", "mem_456"],  # Memories that influenced decision
    decision_summary="Used PostgreSQL with Drizzle ORM for user service",
    outcome_quality=0.9,                 # 0.9 = very successful
    outcome_signal="task_completed"
)

# These memories now have higher salience
# They'll rank higher in future similar queries
```

### Automatic Reflection

Synthesizes patterns from accumulated memories:

```python
mind_reflect(force=True)

# Analyzes recent memories for:
# - Recurring patterns
# - Unresolved goals
# - Contradictions
# - Key decisions
# Stores insights as high-importance semantic memories
```

## Memory Types

| Type | Description | Decay Rate | Best For |
|------|-------------|------------|----------|
| `episodic` | Events, tasks, sessions | 30%/month | Task history, what happened |
| `semantic` | Facts, knowledge | 10%/month | Domain expertise, stable facts |
| `procedural` | Workflows, patterns | 5%/month | Best practices, how-to |
| `preference` | Style, preferences | 2%/month | Communication patterns |

### Choosing Memory Type

```python
# Task outcome (episodic - will decay)
mind_remember(
    content="Sprint 3 completed with all acceptance criteria met",
    memory_type="episodic",
    temporal_level=2  # Days-weeks
)

# Learned pattern (procedural - persists)
mind_remember(
    content="When setting up Supabase RLS, always create policies before enabling RLS on tables",
    memory_type="procedural",
    temporal_level=4  # Years
)

# Project preference (preference - very stable)
mind_remember(
    content="This project uses camelCase for TypeScript and snake_case for Python",
    memory_type="preference",
    temporal_level=4
)
```

## Temporal Levels

| Level | Duration | Use Case |
|-------|----------|----------|
| 1 | Hours | Current session context |
| 2 | Days-weeks | Recent patterns |
| 3 | Months | Recurring patterns |
| 4 | Years | Core preferences, permanent knowledge |

## Scoring Formula

Retrieval ranking uses a multi-factor formula:

```
S_i = α·sim(q,m_i) + β·I_i + γ·R_i - δ·A_i

Where:
  sim = Semantic + keyword similarity (RRF fusion)
  I   = Importance (static + dynamic salience)
  R   = Recency boost (last access time)
  A   = Age decay (type-specific rate)
```

### Factor Weights by Memory Type

| Type | α (Similarity) | β (Importance) | γ (Recency) | δ (Decay) |
|------|----------------|----------------|-------------|-----------|
| episodic | 0.6 | 0.2 | 0.3 | 0.3 |
| semantic | 0.5 | 0.4 | 0.1 | 0.1 |
| procedural | 0.5 | 0.3 | 0.2 | 0.05 |
| preference | 0.4 | 0.5 | 0.1 | 0.02 |

## API Reference

### Core Operations

| Tool | Description |
|------|-------------|
| `mind_remember` | Store a memory with embedding |
| `mind_retrieve` | Retrieve relevant memories |
| `mind_decide` | Track decision outcomes |
| `mind_reflect` | Generate meta-insights |
| `mind_conflicts` | Get memory conflicts |
| `mind_health` | Check system status |

### mind_remember

```python
mind_remember(
    content: str,           # The memory content (embedded)
    memory_type: str,       # episodic | semantic | procedural | preference
    temporal_level: int,    # 1-4 (hours to years)
    importance: float,      # 0.0-1.0 (optional, defaults by type)
    user_id: str           # Optional user scope
)
```

### mind_retrieve

```python
mind_retrieve(
    query: str,             # Natural language query
    limit: int = 10,        # Max results (1-100)
    min_salience: float,    # Threshold 0.0-1.0
    memory_types: list,     # Filter types
    include_reflections: bool = True,
    user_id: str
)

# Returns:
{
    "memories": [
        {
            "id": "mem_123",
            "content": "...",
            "memory_type": "semantic",
            "salience": 0.85,
            "created_at": "2024-01-15T10:30:00Z",
            "accessed_at": "2024-01-20T14:45:00Z"
        }
    ],
    "query": "database selection",
    "total_found": 12
}
```

### mind_decide

```python
mind_decide(
    memory_ids: list,       # IDs that influenced decision
    decision_summary: str,  # What was decided (no PII)
    outcome_quality: float, # -1.0 (bad) to 1.0 (good)
    outcome_signal: str,    # user_accepted | user_rejected | task_completed | agent_feedback
    memory_scores: dict     # Optional: memory_id -> retrieval score
)
```

### mind_reflect

```python
mind_reflect(
    force: bool = False,    # Run even if trigger not reached
    user_id: str
)

# Triggers automatically every 50 memories
# Or force manually at session end
```

### mind_conflicts

```python
mind_conflicts(
    limit: int = 10,
    include_resolved: bool = False,
    user_id: str
)

# Returns contradictory memories for resolution
```

## Integration Patterns

### Session Start

```python
# Retrieve relevant context before starting
context = mind_retrieve(
    query="Working on user authentication for e-commerce app",
    memory_types=["procedural", "semantic"],
    limit=10
)

# Use context to inform decisions
```

### Decision Recording

```python
# When making an architectural decision
mind_remember(
    content="Chose JWT over session cookies for auth because: stateless scaling, mobile app support, microservices compatibility",
    memory_type="episodic",
    temporal_level=3
)
```

### Learning from Outcomes

```python
# After task completion
retrieved = mind_retrieve(query="auth implementation patterns")
memory_ids = [m["id"] for m in retrieved["memories"][:3]]

mind_decide(
    memory_ids=memory_ids,
    decision_summary="JWT auth implementation successful, added refresh token rotation",
    outcome_quality=0.85,
    outcome_signal="task_completed"
)
```

### Session End

```python
# Synthesize learnings
mind_reflect(force=True)
```

## Conflict Detection

Mind automatically detects semantic conflicts:

```python
# If you store contradictory information:
mind_remember(content="Always use Redis for caching", ...)
mind_remember(content="Never use Redis in this project", ...)

# Conflicts are detected via:
# - High cosine similarity (>0.85)
# - Negation patterns
# - Temporal proximity

conflicts = mind_conflicts()
# Returns conflicting pairs for manual resolution
```

## Technical Details

### Embedding Model
- **Model**: nomic-ai/nomic-embed-text-v1.5
- **Dimensions**: 768
- **Normalization**: L2-normalized (cosine = dot product)

### Storage
- **Database**: SQLite with FTS5
- **Location**: `~/.mind/v2/memories.db`
- **Index**: Vector similarity + full-text search

### Search Pipeline
1. Generate query embedding
2. Vector similarity search (top 100)
3. BM25 keyword search (top 100)
4. RRF fusion (k=60)
5. Apply scoring formula
6. Return top N

## Performance

| Operation | p50 | p99 |
|-----------|-----|-----|
| remember (short) | 12ms | 45ms |
| remember (long) | 35ms | 120ms |
| retrieve (10 results) | 45ms | 120ms |
| retrieve (50 results) | 120ms | 350ms |
| decide | 18ms | 55ms |
| reflect | 280ms | 680ms |

### Scaling

| Memory Count | Retrieval p50 |
|--------------|---------------|
| 1,000 | 45ms |
| 10,000 | 85ms |
| 100,000 | 180ms |

## Best Practices

### 1. Be Specific in Content

```python
# Good - specific and searchable
mind_remember(
    content="PostgreSQL with Drizzle ORM chosen for project X because: type safety, migration support, good TypeScript integration",
    memory_type="episodic"
)

# Bad - too vague
mind_remember(
    content="Made a database decision",
    memory_type="episodic"
)
```

### 2. Use Appropriate Memory Types

```python
# Procedural for repeatable patterns
mind_remember(
    content="When debugging Supabase RLS issues, check: 1) Policy definitions 2) Auth context 3) Service role usage",
    memory_type="procedural"
)

# Semantic for facts/knowledge
mind_remember(
    content="Supabase RLS policies are evaluated on every query when RLS is enabled",
    memory_type="semantic"
)
```

### 3. Track Outcomes Consistently

```python
# Always close the loop
mind_decide(
    memory_ids=used_memories,
    decision_summary="Applied X pattern, result: Y",
    outcome_quality=score
)
```

### 4. Regular Reflection

```python
# At natural breakpoints (sprint end, major milestone)
mind_reflect(force=True)
```

### 5. Query Specifically

```python
# Good - specific context
mind_retrieve(query="authentication patterns for NextJS with Supabase")

# Less effective - too broad
mind_retrieve(query="auth")
```
