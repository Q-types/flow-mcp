# Flow MCP Stack Overview

> Start here. This guide will help you understand what the Flow stack does, why it matters, and how to explore further.

## The Problem We're Solving

AI coding assistants are powerful, but they have a critical limitation: **they don't learn from experience**.

Every session starts from zero. The assistant doesn't remember that you prefer Drizzle over Prisma, that your team had issues with Redis last quarter, or that the authentication pattern you used three projects ago worked beautifully. You end up re-explaining context, re-discovering solutions, and repeating mistakes.

## What Flow Does Differently

Flow is a coordinated system of five MCP servers that gives AI assistants:

1. **True semantic memory** (VMind) — Not file-based notes, but 768-dimensional vector embeddings that retrieve by *meaning*
2. **Orchestrated planning** (Architect) — Multi-team coordination with quality gates and scope enforcement
3. **Creative expansion** (Muse) — Analogy generation, idea mutation, contradiction detection
4. **Domain expertise** (Spawner) — 470+ specialist skills with gotcha detection
5. **Bounded execution** (ForgeLoop) — Phase tracking, validation commands, assumption logging

Together, they form a **learning loop**: decisions are tracked, outcomes are recorded, and future retrieval improves automatically.

## The Core Insight: Vector Memory

Most "memory" systems for AI are glorified markdown files or JSON logs. Flow's VMind is fundamentally different.

**Traditional approach:**
```
Store: "We chose PostgreSQL for the user service"
Query: "database decisions" → Keyword search → Maybe finds it
Query: "data persistence choices" → No match (different words)
```

**VMind approach:**
```
Store: "We chose PostgreSQL for the user service"
       ↓
Embed: [0.023, -0.156, 0.089, ..., 0.042]  (768 dimensions)
       ↓
Query: "data persistence choices"
       ↓
Embed query → Cosine similarity → FINDS IT (semantically related)
```

This isn't magic — it's math. Text is converted to high-dimensional vectors where semantically similar content clusters together. "Database decisions" and "data persistence choices" end up near each other in vector space.

**Key specs:**
- **Model**: nomic-ai/nomic-embed-text-v1.5
- **Dimensions**: 768
- **Search**: Hybrid (cosine similarity + BM25 keyword + RRF fusion)
- **Storage**: SQLite with FTS5 at `~/.mind/v2/memories.db`
- **Latency**: 45ms p50 for 10-result retrieval

## How the Components Work Together

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         FLOW ARCHITECTURE                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   ORCHESTRATION                INTELLIGENCE              CAPABILITY    │
│   ─────────────                ────────────              ──────────    │
│                                                                         │
│   ┌───────────┐               ┌───────────┐            ┌───────────┐  │
│   │ ARCHITECT │◄─────────────►│   VMIND   │◄──────────►│  SPAWNER  │  │
│   │  (Plan)   │               │ (Memory)  │            │  (Skills) │  │
│   └─────┬─────┘               └─────┬─────┘            └───────────┘  │
│         │                           │                                  │
│         │                     ┌─────┴─────┐                           │
│         │                     │   MUSE    │                           │
│         │                     │(Creative) │                           │
│         │                     └───────────┘                           │
│         │                                                              │
│   ┌─────┴─────┐                                                       │
│   │ FORGELOOP │                                                       │
│   │ (Execute) │                                                       │
│   └───────────┘                                                       │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Information Flow Example

Let's trace a real request: "Add user authentication to this Next.js app"

```
1. ARCHITECT receives request
   └─► Creates sprint with auth task for auth team

2. ARCHITECT queries VMIND
   └─► "What authentication patterns worked before?"
   └─► Returns: "JWT with refresh rotation (0.85 quality)",
               "Supabase RLS policies (0.92 quality)"

3. ARCHITECT queries SPAWNER
   └─► Smart skill discovery for "auth"
   └─► Returns: nextjs-supabase-auth, jwt-patterns, security-audit
   └─► Also returns gotchas: "RLS must be enabled AFTER policies created"

4. MUSE expands the task
   └─► Finds analogies: "Similar to session management patterns"
   └─► Finds contradictions: "Previous session-based auth had scaling issues"

5. FORGELOOP creates bounded execution phase
   └─► Scope: ["src/auth/*", "src/middleware.ts"]
   └─► Exclusions: ["src/api/*"] (don't touch unrelated code)
   └─► Validation: "npm test && npm run lint"

6. Work proceeds with scope enforcement
   └─► ARCHITECT checks for drift every 2 minutes
   └─► If agent modifies src/api/users.ts → Drift detected, pause

7. On completion, outcome recorded
   └─► VMIND stores: "JWT + Supabase auth, quality: 0.9"
   └─► Memory salience increases for patterns used
   └─► Next auth task will surface these patterns first
```

## Why Each Component Matters

### VMind — The Memory That Learns

Without VMind, every session starts from zero. With VMind:

- **Semantic search**: Find relevant memories even with different wording
- **Learning loop**: Good outcomes boost memory salience, bad outcomes decrease it
- **Memory types**: Episodic (events), Semantic (facts), Procedural (patterns), Preference (style)
- **Conflict detection**: Automatically flags contradictory information
- **Reflection**: Synthesizes patterns across memories periodically

**Read more**: [VMIND.md](VMIND.md)

### Architect — Coordinated Execution

Without Architect, complex tasks become chaotic. With Architect:

- **Multi-team coordination**: Backend, Frontend, Database, Auth, Testing, DevOps, Design, Documentation
- **Sprint management**: Goals, tasks, dependencies, acceptance criteria
- **Quality gates**: Test pass rate (100%), lint errors (0), scope coverage (90%)
- **Scope enforcement**: Detects drift during long-running tasks
- **Integration checks**: Ensures teams work together coherently

**Read more**: [ARCHITECT.md](ARCHITECT.md)

### Muse — Creative Expansion

Without Muse, you get literal solutions. With Muse:

- **Prompt expansion**: Raw ideas become structured working objects
- **Analogy generation**: Find cross-domain solutions ("This is like...")
- **Contradiction detection**: Surface tensions and counter-evidence early
- **Idea mutation**: Invert, combine, compress, scale up/down, make safer
- **Quality ranking**: Score ideas on usefulness, novelty, feasibility, risk

**Read more**: [MUSE.md](MUSE.md)

### Spawner — Domain Expertise

Without Spawner, you rely on generic knowledge. With Spawner:

- **470+ specialist skills**: From TypeScript patterns to YC playbook
- **Skill squads**: Pre-bundled skills for features (auth-complete, payments-complete)
- **Sharp edges**: Proactive warnings ("RLS must be enabled AFTER policies")
- **Validation**: Catches SQL injection, XSS, hardcoded secrets
- **Stack analysis**: Auto-detects project technologies

**Read more**: [SPAWNER.md](SPAWNER.md)

### ForgeLoop — Bounded Execution

Without ForgeLoop, agents can drift. With ForgeLoop:

- **Phase management**: Bounded scope with clear deliverables
- **Validation commands**: Configurable test/lint/type-check
- **Assumption tracking**: Document what you're assuming
- **Decision logging**: Record why choices were made
- **Agent prompts**: Generate context-aware, bounded prompts

**Read more**: [FORGELOOP.md](FORGELOOP.md)

## The Learning Loop in Detail

This is what makes Flow fundamentally different from static systems:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         THE LEARNING LOOP                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   1. RETRIEVE                           2. DECIDE                       │
│   ──────────                            ────────                        │
│   Query VMind for relevant              Use retrieved context           │
│   past experiences                      to inform decision              │
│                                                                         │
│   vmind_retrieve(                       "Based on past success with     │
│     query="auth patterns",              JWT refresh rotation, let's     │
│     memory_types=["procedural"]         use that pattern here"          │
│   )                                                                     │
│                                                                         │
│   Returns memories with                                                 │
│   salience scores                                                       │
│                                                                         │
│         ▲                                      │                        │
│         │                                      │                        │
│         │                                      ▼                        │
│                                                                         │
│   4. LEARN                              3. OBSERVE                      │
│   ────────                              ──────────                      │
│   Adjust salience based                 Track the outcome               │
│   on outcome quality                    of the decision                 │
│                                                                         │
│   Good outcome (+0.9):                  vmind_decide(                   │
│   └─► Salience ↑ by 0.15               memory_ids=[...],               │
│   └─► Ranks higher next time            decision_summary="...",         │
│                                         outcome_quality=0.9             │
│   Bad outcome (-0.5):                   )                               │
│   └─► Salience ↓ by 0.10                                               │
│   └─► Less likely retrieved                                            │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

Over time, this creates emergent behavior:
- Successful patterns rise to the top
- Failed approaches fade away
- The system gets better at *your* specific domain and preferences

## Reading Order

For the best understanding, read the docs in this order:

| Order | Document | What You'll Learn |
|-------|----------|-------------------|
| 1 | **You are here** | Overview and philosophy |
| 2 | [VMIND.md](VMIND.md) | How semantic memory works |
| 3 | [ARCHITECT.md](ARCHITECT.md) | Project orchestration |
| 4 | [MUSE.md](MUSE.md) | Creative ideation |
| 5 | [SPAWNER.md](SPAWNER.md) | Skill library |
| 6 | [FORGELOOP.md](FORGELOOP.md) | Bounded execution |
| 7 | [ARCHITECTURE.md](ARCHITECTURE.md) | System design deep dive |
| 8 | [BENCHMARKS.md](BENCHMARKS.md) | Performance data |

## Quick Comparison

| Aspect | Without Flow | With Flow |
|--------|--------------|-----------|
| Memory | None / markdown files | 768-dim semantic vectors |
| Search | Keyword matching | Meaning-based retrieval |
| Learning | None | Outcome-adjusted salience |
| Planning | Ad-hoc | Structured sprints with gates |
| Creativity | Literal solutions | Analogies, mutations, contradictions |
| Skills | Generic knowledge | 470+ domain specialists |
| Execution | Unbounded | Scoped phases with validation |

## Getting Started

### 1. Install the Stack

```bash
git clone https://github.com/Q-types/flow-mcp.git
cd flow-mcp
pip install -e packages/vmind packages/muse packages/architect packages/forgeloop
```

### 2. Configure Claude Code

Add to `~/.claude/settings.local.json`:

```json
{
  "mcpServers": {
    "vmind": { "command": "python", "args": ["-m", "vmind_mcp"] },
    "muse": { "command": "python", "args": ["-m", "muse_mcp"] },
    "architect": { "command": "python", "args": ["-m", "architect_mcp"] },
    "forgeloop": { "command": "python", "args": ["-m", "forgeloop_mcp"] }
  }
}
```

### 3. First Session

```python
# Store something to memory
vmind_remember(
    content="This project uses PostgreSQL with Drizzle ORM for type safety",
    memory_type="semantic",
    temporal_level=4
)

# Later, retrieve it semantically
vmind_retrieve(query="database choices and ORMs")
# Finds it even though words don't match exactly
```

## Performance at a Glance

| Operation | p50 | p99 |
|-----------|-----|-----|
| VMind retrieve (10 results) | 45ms | 120ms |
| Muse expand_prompt | 180ms | 450ms |
| Spawner skills search | 25ms | 80ms |
| Architect plan | 350ms | 900ms |
| Full pipeline | 800ms | 2.1s |

The 2-3x latency vs. raw Claude is offset by **20-30% quality improvement** that compounds over time.

## Next Steps

Now that you understand the philosophy, dive into the components:

- **[VMIND.md](VMIND.md)** — Start here to understand the memory system
- **[ARCHITECT.md](ARCHITECT.md)** — Learn how to orchestrate complex projects
- **[ARCHITECTURE.md](ARCHITECTURE.md)** — See the full system design

---

*Flow MCP Stack — AI that remembers, learns, and improves*
