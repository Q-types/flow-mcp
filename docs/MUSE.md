# Muse MCP

> Creative ideation and idea mutation engine

## Overview

Muse MCP is the creative layer of the Flow stack. It expands prompts into rich working objects, generates analogies across domains, finds contradictions, mutates ideas through various operators, and ranks candidates for quality. When integrated with VMind, it creates a complete ideation-to-memory pipeline.

## Why This Matters

### As a Standalone MCP

Even without the rest of the Flow stack, Muse provides:

1. **Prompt expansion**: Turn vague ideas into structured working objects
2. **Analogy generation**: Find solutions from unrelated domains
3. **Contradiction detection**: Surface tensions and counter-evidence early
4. **Idea mutation**: Systematically explore variations (invert, compress, scale)
5. **Quality ranking**: Score ideas before investing time building them

### With the Full Flow Stack

When integrated with VMind, Architect, Spawner, and ForgeLoop:

| Integration | Benefit |
|-------------|---------|
| **+ VMind** | Retrieve past failures and successes to inform mutations |
| **+ Architect** | Expand skill searches with cross-domain analogies |
| **+ Spawner** | Find skills via structural similarity, not just keywords |
| **+ ForgeLoop** | Generate bounded prompts that incorporate contradictions |

**The compound effect**: When exploring "how to implement caching", Muse doesn't just find caching skills — it retrieves past caching failures from VMind, generates analogies ("similar to memoization in functional programming"), finds contradictions ("previous Redis deployment had connection issues"), and ranks approaches before Architect assigns the task.

## Key Features

### Prompt Expansion

Transform raw prompts into structured working objects:

```python
result = muse_expand_prompt(
    prompt="Build a task management app",
    user_id="user_123"
)

# Returns:
{
    "working_object": {
        "goal": "Create an application for organizing and tracking tasks",
        "domains": ["productivity", "project management", "collaboration"],
        "constraints": ["User-friendly interface", "Data persistence", "Multi-user support"],
        "desired_outputs": ["Task CRUD", "Due dates", "Assignments", "Progress tracking"]
    },
    "working_object_id": "wo_456"
}
```

### Multi-Mode Retrieval

Retrieve associations using multiple cognitive modes:

```python
result = muse_retrieve_associations(
    query="task management system",
    modes=["nearest", "distant_analogies", "past_failures", "successful_workflows"],
    user_id="user_123"
)

# Returns:
{
    "nearest": [...],              # Semantically similar memories
    "distant_analogies": [...],    # Cross-domain structural matches
    "past_failures": [...],        # What went wrong before
    "successful_workflows": [...]  # What worked
}
```

### Analogy Generation

Find structural similarities across domains:

```python
result = muse_generate_analogies(
    source_content="Kanban board with swimlanes and WIP limits",
    source_domain="project management",
    limit=5,
    user_id="user_123"
)

# Returns:
{
    "analogies": [
        {
            "target_domain": "manufacturing",
            "target_content": "Assembly line with stations and capacity limits",
            "structural_similarity": 0.85,
            "surface_similarity": 0.2,
            "mapping": {
                "swimlanes": "stations",
                "WIP limits": "capacity constraints",
                "cards": "work units"
            }
        },
        ...
    ]
}
```

### Contradiction Finding

Surface tensions and counter-evidence:

```python
result = muse_find_contradictions(
    content="We should use a monolithic architecture for faster development",
    user_id="user_123"
)

# Returns:
{
    "contradictions": [
        {
            "type": "evidence",
            "content": "Previous monolith became unmaintainable at 50k LOC",
            "source_memory_id": "mem_789"
        },
        {
            "type": "assumption",
            "content": "Assumes team won't grow; microservices scale better with team size"
        },
        {
            "type": "risk",
            "content": "Deployment coupling could cause cascading failures"
        }
    ]
}
```

### Idea Mutation

Apply transformation operators:

```python
result = muse_mutate_ideas(
    content="A todo app with AI task prioritization",
    mutation_types=["invert", "combine", "scale_up"],
    user_id="user_123"
)

# Returns:
{
    "mutations": [
        {
            "type": "invert",
            "content": "An app that deliberately randomizes task order to break prioritization bias",
            "fragment_id": "frag_001"
        },
        {
            "type": "combine",
            "content": "A todo app with AI prioritization + calendar blocking + energy tracking",
            "fragment_id": "frag_002"
        },
        {
            "type": "scale_up",
            "content": "An enterprise task management platform with AI prioritization across teams and projects",
            "fragment_id": "frag_003"
        }
    ]
}
```

### Candidate Ranking

Score ideas on multiple dimensions:

```python
result = muse_rank_candidates(
    content="AI-powered code review assistant integrated into GitHub PRs",
    user_id="user_123"
)

# Returns:
{
    "candidate_id": "cand_001",
    "scores": {
        "usefulness": 0.85,
        "novelty": 0.4,
        "feasibility": 0.75,
        "alignment": 0.9,
        "risk": 0.3
    },
    "value_score": 7.2,
    "formula": "V = 0.3*U + 0.2*N + 0.2*F + 0.2*A - 0.1*R"
}
```

## Retrieval Modes

| Mode | Description | Use Case |
|------|-------------|----------|
| `nearest` | Semantically similar memories | Direct relevance |
| `distant_analogies` | Cross-domain structural matches | Creative solutions |
| `past_failures` | What went wrong before | Risk avoidance |
| `successful_workflows` | What worked | Proven patterns |
| `contradictory` | Arguments against | Devil's advocate |
| `domain_patterns` | Established patterns | Best practices |
| `user_preferences` | User/project style | Alignment |

## Mutation Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `invert` | Flip core assumption | "Fast delivery" → "Intentionally slow, mindful delivery" |
| `combine` | Merge with another idea | "Todo + Calendar" → "Time-blocked tasks" |
| `compress` | Simplify to essence | "Full CRM" → "Contact list with notes" |
| `modularize` | Break into components | "Monolith" → "Auth service + Task service + ..." |
| `make_safer` | Reduce risk | "AI auto-commit" → "AI suggests, human approves" |
| `make_explainable` | Add clarity | "ML ranking" → "ML ranking with reason display" |
| `make_testable` | Add verification | "Feature X" → "Feature X with A/B test framework" |
| `make_sellable` | Add appeal | "Task tracker" → "AI productivity coach" |
| `scale_up` | Expand scope | "Personal" → "Team" → "Enterprise" |
| `scale_down` | Narrow focus | "All tasks" → "Just today's tasks" |

## Value Formula

Candidates are scored using:

```
V = w_u*U + w_n*N + w_f*F + w_a*A - w_r*R

Where:
  U = Usefulness (0-1): Does it solve a real problem?
  N = Novelty (0-1): Is it different from existing solutions?
  F = Feasibility (0-1): Can it be built with available resources?
  A = Alignment (0-1): Does it match project goals?
  R = Risk (0-1): What's the hallucination/failure likelihood?

Default weights: w_u=0.3, w_n=0.2, w_f=0.2, w_a=0.2, w_r=0.1
```

### Custom Weights

```python
muse_rank_candidates(
    content="My idea",
    weights={
        "usefulness": 0.4,    # Prioritize practical value
        "novelty": 0.1,       # Don't need to be novel
        "feasibility": 0.3,   # Must be buildable
        "alignment": 0.15,
        "risk": 0.05
    },
    user_id="user_123"
)
```

## Promotion Pipeline

Quality-gated path from Muse to VMind:

```python
# Only candidates meeting criteria are promoted
result = muse_promote_to_mind(
    candidate_id="cand_001",
    user_id="user_123"
)

# Criteria:
# - Value score >= 0.6
# - Usefulness >= 0.5
# - Novelty >= 0.4
# - Risk <= 0.7

# If promoted:
{
    "promoted": True,
    "memory_id": "mem_new_123",
    "memory_type": "semantic"  # Auto-determined
}
```

## API Reference

| Tool | Description |
|------|-------------|
| `muse_expand_prompt` | Expand raw prompt to working object |
| `muse_retrieve_associations` | Multi-mode memory retrieval |
| `muse_generate_analogies` | Cross-domain structural mappings |
| `muse_find_contradictions` | Surface tensions and counter-evidence |
| `muse_mutate_ideas` | Apply transformation operators |
| `muse_rank_candidates` | Score ideas on value formula |
| `muse_promote_to_vmind` | Promote quality candidates to memory |
| `muse_health` | Check system status |

## Integration with VMind

Muse and VMind work together in a creative pipeline:

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ Raw Prompt  │────►│    MUSE     │────►│   VMIND     │
│             │     │  (Expand)   │     │  (Store)    │
└─────────────┘     └──────┬──────┘     └──────┬──────┘
                           │                   │
                    ┌──────▼──────┐           │
                    │  Mutations  │           │
                    │  Analogies  │           │
                    │ Contradicts │           │
                    └──────┬──────┘           │
                           │                   │
                    ┌──────▼──────┐           │
                    │   Ranking   │           │
                    │  (Quality)  │           │
                    └──────┬──────┘           │
                           │                   │
                    ┌──────▼──────┐           │
                    │  Promotion  │───────────┘
                    │ (If quality)│
                    └─────────────┘
```

### Workflow Example

```python
# 1. Start with a prompt
working = muse_expand_prompt(
    prompt="Build a better email client",
    user_id="user_123"
)

# 2. Retrieve relevant context from VMind
associations = muse_retrieve_associations(
    query=working["working_object"]["goal"],
    modes=["successful_workflows", "past_failures"],
    user_id="user_123"
)

# 3. Generate variations
mutations = muse_mutate_ideas(
    content=working["working_object"]["goal"],
    mutation_types=["invert", "scale_down", "make_safer"],
    user_id="user_123"
)

# 4. Find potential issues
contradictions = muse_find_contradictions(
    content=mutations["mutations"][0]["content"],
    user_id="user_123"
)

# 5. Score the best candidates
for mutation in mutations["mutations"]:
    ranked = muse_rank_candidates(
        content=mutation["content"],
        working_object_id=working["working_object_id"],
        user_id="user_123"
    )

    # 6. Promote high-quality ideas to VMind
    if ranked["value_score"] >= 0.7:
        muse_promote_to_mind(
            candidate_id=ranked["candidate_id"],
            user_id="user_123"
        )
```

## Best Practices

### 1. Use Multiple Retrieval Modes

```python
# Cast a wide net for creative input
muse_retrieve_associations(
    query="...",
    modes=["nearest", "distant_analogies", "contradictory"],
    ...
)
```

### 2. Apply Selective Mutations

```python
# Choose mutations based on goal
# For risk reduction:
mutation_types=["make_safer", "make_testable", "compress"]

# For expansion:
mutation_types=["scale_up", "combine", "modularize"]

# For creativity:
mutation_types=["invert", "distant_analogies"]
```

### 3. Find Contradictions Early

```python
# Before committing to an idea
contradictions = muse_find_contradictions(content=idea)

if len(contradictions["contradictions"]) > 3:
    # Reconsider or address issues first
    ...
```

### 4. Custom Weights for Context

```python
# Startup MVP - prioritize feasibility
weights={"feasibility": 0.4, "usefulness": 0.3, ...}

# Research project - prioritize novelty
weights={"novelty": 0.4, "usefulness": 0.3, ...}

# Enterprise - prioritize safety
weights={"risk": 0.3, "feasibility": 0.3, ...}
```

### 5. Promote Selectively

```python
# Only promote ideas that meet quality threshold
# The promotion criteria exist for a reason
# Low-quality memories pollute future retrieval
```

## Performance

| Operation | p50 | p99 |
|-----------|-----|-----|
| expand_prompt | 180ms | 450ms |
| retrieve_associations (all) | 250ms | 650ms |
| retrieve_associations (single) | 55ms | 140ms |
| generate_analogies | 220ms | 550ms |
| find_contradictions | 180ms | 480ms |
| mutate_ideas (all) | 450ms | 1.1s |
| mutate_ideas (single) | 85ms | 210ms |
| rank_candidates | 35ms | 95ms |
| promote_to_mind | 55ms | 150ms |

## Contradiction Types

| Type | Description | Example |
|------|-------------|---------|
| `evidence` | Stored memory contradicts | "Last time X failed" |
| `assumption` | Fragile assumption | "Assumes users want..." |
| `risk` | Production failure mode | "Could cause data loss" |
| `cost` | Resource concern | "Requires expensive GPU" |
| `scalability` | Growth limitation | "Won't work past 10k users" |
| `alternative` | Better option exists | "Y solves this better" |
