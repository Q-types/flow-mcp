# Muse MCP

Associative working-memory MCP server for creative recombination and selective promotion.

## Core Theory

```
MIND MCP = stores what has mattered (long-term semantic memory)
Muse MCP = explores what might matter (temporary generative workspace)
```

**The MIND ↔ Muse relationship:**

```
User prompt
   ↓
Muse expands the problem
   ↓
Muse queries MIND
   ↓
MIND returns relevant memories, patterns, failures, preferences
   ↓
Muse creates combinations, analogies, contradictions, mutations
   ↓
LLM evaluates ideas
   ↓
Only useful distilled outputs are promoted back into MIND
```

## Value Scoring Formula

```
V = w_u × U + w_n × N + w_f × F + w_a × A - w_r × R
```

Where:
- **U** = usefulness (0-1)
- **N** = novelty (0-1)
- **F** = feasibility (0-1)
- **A** = alignment with goals (0-1)
- **R** = risk/hallucination likelihood (0-1)

## Memory Lifecycle

```
fragment → cluster → candidate → evaluated insight → promoted memory
```

Most fragments should expire. Promotion criteria:
- Useful more than once
- Connected to an active project
- High novelty AND feasibility
- Captures a decision or mistake
- Captures a reusable pattern

## MCP Tools

| Tool | Description |
|------|-------------|
| `muse_health` | Check server status |
| `muse_expand_prompt` | Expand raw prompt into rich working object |
| `muse_retrieve_associations` | Multi-mode retrieval from Mind MCP |
| `muse_generate_analogies` | Find cross-domain structural mappings |
| `muse_find_contradictions` | Surface tensions and counter-evidence |
| `muse_mutate_ideas` | Apply transformation operators |
| `muse_rank_candidates` | Score ideas using V formula |
| `muse_promote_to_mind` | Selective consolidation to long-term memory |

## Key Mechanisms

### 1. Prompt Expansion

Converts raw prompts into rich working objects:

```json
{
  "goal": "improve an MCP memory architecture",
  "domains": ["agent memory", "RAG", "creativity"],
  "constraints": ["local-first", "MCP-compatible"],
  "desired_outputs": ["architecture", "tools", "ranking system"]
}
```

### 2. Multi-Mode Retrieval

Not just semantic similarity, but productive tension:

- **nearest**: Semantically similar memories
- **distant_analogies**: Cross-domain structural matches
- **past_failures**: What went wrong before
- **successful_workflows**: What worked
- **contradictory**: Arguments against
- **domain_patterns**: Established patterns
- **user_preferences**: User/project style

### 3. Analogy Mapping

Cross-domain structural mappings:

```
KSP estimator:
messy human knowledge → structured schema → estimator → actuals feedback

MCP memory:
messy agent experience → structured memory → retrieval → reflection feedback
```

### 4. Contradiction Search

Inner critic asking:
- What stored memory argues against this?
- What assumption is fragile?
- What would make this fail in production?
- What would a skeptical engineer reject?

### 5. Idea Mutation

Systematic transformations:
- `invert` - Flip the core assumption
- `combine` - Merge with another idea
- `compress` - Simplify to essence
- `modularize` - Break into components
- `make_safer` - Reduce risk
- `make_explainable` - Add clarity
- `make_testable` - Add verification
- `make_sellable` - Add appeal
- `scale_up` - Expand scope
- `scale_down` - Narrow focus

## Installation

```bash
pip install -e .
```

## Usage

```bash
# Run the MCP server
python -m muse_mcp

# Or with environment variables
MUSE_DB_PATH=/path/to/muse.db MUSE_MODEL=all-MiniLM-L6-v2 python -m muse_mcp
```

## Integration with Mind MCP

Muse MCP is designed to work alongside Mind MCP:

```
MIND remembers.
Muse recombines.
The agent reasons.
MIND learns from what survives.
```

## Architecture

```
src/muse_mcp/
├── __init__.py          # Package exports
├── __main__.py          # Entry point
├── server.py            # MCP server and tools
├── models.py            # Data models (Fragment, Candidate, etc.)
├── database.py          # SQLite with TTL support
├── embeddings.py        # Sentence transformers
├── fragments.py         # Fragment storage and decay
├── expansion.py         # Prompt expansion
├── associations.py      # Multi-mode retrieval
├── analogies.py         # Cross-domain mapping
├── contradictions.py    # Inner critic
├── mutations.py         # Idea transformation
├── ranking.py           # Value scoring
└── promotion.py         # Mind MCP promotion
```

## License

MIT
