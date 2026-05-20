# VMind MCP (Vector Mind)

> Semantic vector memory that learns from outcomes

## This Is Not File-Based Memory

Many AI memory systems are glorified markdown files or JSON logs. They store text and retrieve it by keyword matching. If you search "database decisions", they grep for those exact words.

**VMind is fundamentally different.**

VMind converts every memory into a **768-dimensional vector embedding** using nomic-ai/nomic-embed-text-v1.5. These vectors capture *meaning*, not just words. Semantically similar content clusters together in vector space, so "database decisions" and "data persistence choices" end up near each other — even though they share zero words.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    HOW VECTOR MEMORY WORKS                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  INPUT: "We chose PostgreSQL for type safety and relational queries"   │
│                                                                         │
│            │                                                            │
│            ▼                                                            │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  EMBEDDING (nomic-embed-text-v1.5)                              │   │
│  │                                                                  │   │
│  │  "We chose PostgreSQL..."  →  [0.023, -0.156, 0.089, 0.012,     │   │
│  │                                -0.045, 0.178, ..., 0.042]        │   │
│  │                                                                  │   │
│  │                               768 dimensions                     │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│            │                                                            │
│            ▼                                                            │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  STORAGE (SQLite + FTS5)                                        │   │
│  │                                                                  │   │
│  │  - Vector stored L2-normalized (cosine = dot product)           │   │
│  │  - Full-text index for BM25 keyword backup                      │   │
│  │  - Metadata: type, salience, timestamps, user_id                │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│            │                                                            │
│            ▼                                                            │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  RETRIEVAL (Query: "data persistence choices")                  │   │
│  │                                                                  │   │
│  │  1. Embed query → [0.019, -0.142, 0.092, ...]                   │   │
│  │  2. Vector search: cosine similarity → top 100                  │   │
│  │  3. Keyword search: BM25 → top 100                              │   │
│  │  4. RRF fusion (k=60) → combined ranking                        │   │
│  │  5. Apply salience, recency, decay → final score                │   │
│  │                                                                  │   │
│  │  FINDS the PostgreSQL memory even though                        │   │
│  │  "data persistence choices" shares no words with it             │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## Why This Matters

| File-Based Memory | VMind Vector Memory |
|-------------------|---------------------|
| Grep for exact keywords | Find by meaning |
| No learning from outcomes | Good outcomes boost salience |
| All memories equal weight | Successful patterns emerge |
| Manual organization | Automatic clustering |
| Stale over time | Self-maintaining via decay |

**The learning loop is the key differentiator.** When you tell VMind that a decision worked well (+0.9 quality), the memories that influenced it gain salience. Next time you face a similar problem, those patterns rank higher automatically.

## Benefits

### As a Standalone MCP

Even without the rest of the Flow stack, VMind provides:

1. **Persistent context across sessions**: No more re-explaining your project
2. **Semantic search**: Find relevant memories even with different wording
3. **Outcome-based learning**: System gets better at surfacing useful patterns
4. **Conflict detection**: Automatically flags contradictory information
5. **Automatic reflection**: Synthesizes patterns from accumulated memories

### With the Full Flow Stack

When integrated with Architect, Muse, Spawner, and ForgeLoop:

1. **Architect uses VMind** to recall what worked in past projects
2. **Muse queries VMind** for contradictions and past failures
3. **Smart skill discovery** combines VMind patterns with Spawner searches
4. **Learning compounds**: Every project improves future projects

## Key Features

### Semantic Memory Storage

Store memories with automatic embedding and classification:

```python
vmind_remember(
    content="Chose PostgreSQL over MongoDB for this project because of relational data requirements and strong typing needs",
    memory_type="episodic",    # Event/decision
    temporal_level=3           # Months-level persistence
)
```

### Hybrid Retrieval

Combines semantic similarity with keyword matching:

```python
result = vmind_retrieve(
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
vmind_decide(
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
vmind_reflect(force=True)

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
vmind_remember(
    content="Sprint 3 completed with all acceptance criteria met",
    memory_type="episodic",
    temporal_level=2  # Days-weeks
)

# Learned pattern (procedural - persists)
vmind_remember(
    content="When setting up Supabase RLS, always create policies before enabling RLS on tables",
    memory_type="procedural",
    temporal_level=4  # Years
)

# Project preference (preference - very stable)
vmind_remember(
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
| `vmind_remember` | Store a memory with 768-dim embedding |
| `vmind_retrieve` | Semantic + keyword hybrid search |
| `vmind_decide` | Track decision outcomes for learning |
| `vmind_reflect` | Generate meta-insights from patterns |
| `vmind_conflicts` | Detect contradictory memories |
| `vmind_health` | Check system status |

### vmind_remember

```python
vmind_remember(
    content: str,           # The memory content (embedded)
    memory_type: str,       # episodic | semantic | procedural | preference
    temporal_level: int,    # 1-4 (hours to years)
    importance: float,      # 0.0-1.0 (optional, defaults by type)
    user_id: str           # Optional user scope
)
```

### vmind_retrieve

```python
vmind_retrieve(
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

### vmind_decide

```python
vmind_decide(
    memory_ids: list,       # IDs that influenced decision
    decision_summary: str,  # What was decided (no PII)
    outcome_quality: float, # -1.0 (bad) to 1.0 (good)
    outcome_signal: str,    # user_accepted | user_rejected | task_completed | agent_feedback
    memory_scores: dict     # Optional: memory_id -> retrieval score
)
```

### vmind_reflect

```python
vmind_reflect(
    force: bool = False,    # Run even if trigger not reached
    user_id: str
)

# Triggers automatically every 50 memories
# Or force manually at session end
```

### vmind_conflicts

```python
vmind_conflicts(
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
context = vmind_retrieve(
    query="Working on user authentication for e-commerce app",
    memory_types=["procedural", "semantic"],
    limit=10
)

# Use context to inform decisions
```

### Decision Recording

```python
# When making an architectural decision
vmind_remember(
    content="Chose JWT over session cookies for auth because: stateless scaling, mobile app support, microservices compatibility",
    memory_type="episodic",
    temporal_level=3
)
```

### Learning from Outcomes

```python
# After task completion
retrieved = vmind_retrieve(query="auth implementation patterns")
memory_ids = [m["id"] for m in retrieved["memories"][:3]]

vmind_decide(
    memory_ids=memory_ids,
    decision_summary="JWT auth implementation successful, added refresh token rotation",
    outcome_quality=0.85,
    outcome_signal="task_completed"
)
```

### Session End

```python
# Synthesize learnings
vmind_reflect(force=True)
```

## Conflict Detection

VMind automatically detects semantic conflicts:

```python
# If you store contradictory information:
vmind_remember(content="Always use Redis for caching", ...)
vmind_remember(content="Never use Redis in this project", ...)

# Conflicts are detected via:
# - High cosine similarity (>0.85)
# - Negation patterns
# - Temporal proximity

conflicts = vmind_conflicts()
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
1. Generate query embedding (768 dimensions)
2. Vector similarity search (top 100 by cosine)
3. BM25 keyword search (top 100)
4. RRF fusion (k=60) — combines rankings
5. Apply scoring formula (salience, recency, decay)
6. Return top N

### RRF Fusion Explained

Reciprocal Rank Fusion combines multiple ranked lists:

```
RRF_score(d) = Σ 1 / (k + rank_i(d))

Where k = 60 (smoothing constant)
```

This means a document ranked #1 in semantic and #5 in keyword gets:
```
RRF = 1/(60+1) + 1/(60+5) = 0.0164 + 0.0154 = 0.0318
```

Documents that rank highly in *both* lists score highest.

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
vmind_remember(
    content="PostgreSQL with Drizzle ORM chosen for project X because: type safety, migration support, good TypeScript integration",
    memory_type="episodic"
)

# Bad - too vague
vmind_remember(
    content="Made a database decision",
    memory_type="episodic"
)
```

### 2. Use Appropriate Memory Types

```python
# Procedural for repeatable patterns
vmind_remember(
    content="When debugging Supabase RLS issues, check: 1) Policy definitions 2) Auth context 3) Service role usage",
    memory_type="procedural"
)

# Semantic for facts/knowledge
vmind_remember(
    content="Supabase RLS policies are evaluated on every query when RLS is enabled",
    memory_type="semantic"
)
```

### 3. Track Outcomes Consistently

```python
# Always close the loop
vmind_decide(
    memory_ids=used_memories,
    decision_summary="Applied X pattern, result: Y",
    outcome_quality=score
)
```

### 4. Regular Reflection

```python
# At natural breakpoints (sprint end, major milestone)
vmind_reflect(force=True)
```

### 5. Query Specifically

```python
# Good - specific context
vmind_retrieve(query="authentication patterns for NextJS with Supabase")

# Less effective - too broad
vmind_retrieve(query="auth")
```

## Comparison: VMind vs Traditional Memory

| Aspect | Traditional (Files/Logs) | VMind |
|--------|-------------------------|-------|
| Storage | Markdown/JSON files | SQLite + 768-dim vectors |
| Search | Keyword grep | Semantic + keyword hybrid |
| Learning | None | Outcome-based salience |
| Organization | Manual folders/tags | Automatic semantic clustering |
| Staleness | Accumulates forever | Decay by memory type |
| Conflicts | Manual detection | Automatic flagging |
| Scale | Slow at 1000+ entries | Sub-100ms at 100k entries |

---

*VMind — Memory that understands meaning and learns from experience*
