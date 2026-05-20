# Flow MCP Stack

> An intelligent, self-improving orchestration layer for AI-assisted software development

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     FLOW MCP STACK                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                 │
│  │   SPAWNER   │◄──►│  ARCHITECT  │◄──►│    MIND     │                 │
│  │   Skills    │    │ Orchestrate │    │   Memory    │                 │
│  └──────┬──────┘    └──────┬──────┘    └──────┬──────┘                 │
│         │                  │                  │                         │
│         │           ┌──────┴──────┐           │                         │
│         └──────────►│    MUSE     │◄──────────┘                         │
│                     │  Creativity │                                     │
│                     └──────┬──────┘                                     │
│                            │                                            │
│                     ┌──────┴──────┐                                     │
│                     │  FORGELOOP  │                                     │
│                     │  Execution  │                                     │
│                     └─────────────┘                                     │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## Overview

The Flow MCP Stack is a suite of interconnected Model Context Protocol (MCP) servers that work together to provide intelligent, context-aware software development assistance. Each component handles a specific aspect of the development lifecycle, and together they form a self-improving system that learns from every interaction.

## Components

| Component | Purpose | Key Capabilities |
|-----------|---------|------------------|
| **[Architect](docs/ARCHITECT.md)** | Project orchestration & team management | Sprint planning, task assignment, quality gates, multi-team coordination |
| **[Mind](docs/MIND.md)** | Persistent semantic memory | Long-term learning, pattern recognition, decision tracking, conflict detection |
| **[Muse](docs/MUSE.md)** | Creative ideation & mutation | Analogy generation, idea expansion, contradiction finding, ranked candidates |
| **[Spawner](docs/SPAWNER.md)** | Skill library & validation | 470+ skills, sharp edge detection, guardrail checks, stack analysis |
| **[ForgeLoop](docs/FORGELOOP.md)** | Bounded execution & tracking | Phase management, validation commands, assumption tracking, agent prompts |

## Key Features

### Learning Loop
The system improves over time by tracking outcomes:
```
Decision Made → Outcome Observed → Memory Updated → Future Decisions Improved
```

### Smart Skill Discovery
Multi-source skill search that learns what works:
```
Query → Mind (past successes) → Muse (analogies) → Spawner (search) → Ranked Results
```

### Plan Evaluation
Five-dimensional plan scoring:
- **Complexity**: Team count, structural depth, integration points
- **Feasibility**: Resource availability, timeline realism
- **Clarity**: Specification completeness, success criteria
- **Cohesion**: Dependency alignment, phase flow
- **Risk**: Technical uncertainty, external dependencies

### Quality Gates
Automated verification with recursive review:
- Test pass rate (100% threshold)
- Lint critical errors (0 threshold)
- Scope coverage (90% threshold)

## Repository Structure

```
flow-mcp/
├── README.md                 # This file
├── pyproject.toml            # Monorepo configuration
├── docs/                     # Stack documentation
│   ├── ARCHITECTURE.md       # System design
│   ├── BENCHMARKS.md         # Performance testing
│   ├── ARCHITECT.md          # Architect component
│   ├── MIND.md               # Mind component
│   ├── MUSE.md               # Muse component
│   ├── SPAWNER.md            # Spawner integration
│   └── FORGELOOP.md          # ForgeLoop component
└── packages/                 # MCP components
    ├── architect/            # Project orchestration
    ├── mind/                 # Semantic memory
    ├── muse/                 # Creative ideation
    └── forgeloop/            # Bounded execution
```

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/Q-types/flow-mcp.git
cd flow-mcp

# Install all packages (recommended)
pip install -e packages/mind
pip install -e packages/muse
pip install -e packages/architect
pip install -e packages/forgeloop

# Or install individually
pip install -e packages/architect  # Just Architect
```

### Configuration

Add to your Claude Code MCP settings (`~/.claude/settings.local.json`):

```json
{
  "mcpServers": {
    "architect": {
      "command": "python",
      "args": ["-m", "architect_mcp"]
    },
    "mind": {
      "command": "python",
      "args": ["-m", "mind_mcp"]
    },
    "muse": {
      "command": "python",
      "args": ["-m", "muse_mcp"]
    },
    "spawner": {
      "command": "node",
      "args": ["path/to/spawner-mcp/dist/index.js"]
    },
    "forgeloop": {
      "command": "python",
      "args": ["-m", "forgeloop_mcp"]
    }
  }
}
```

### Basic Usage

```python
# 1. Start a project with validated idea
architect_full_pipeline(
    name="MyProject",
    idea="A task management app with real-time collaboration",
    auto_refine=True,
    prd_level="science-fair"
)

# 2. Create a sprint
architect_create_sprint(
    name="Sprint 1: Foundation",
    goal="Set up core database and authentication",
    teams=["database", "auth", "backend"]
)

# 3. Smart skill discovery for tasks
architect_smart_discover(
    query="database",
    project_context=True
)

# 4. Add tasks with automatic skill loading
architect_smart_assign(
    title="Design database schema",
    description="Create tables for users, tasks, and projects",
    team="database",
    feature="database"
)

# 5. Track decisions for learning
mind_remember(
    content="Chose PostgreSQL with Drizzle ORM for type safety",
    memory_type="episodic",
    temporal_level=3
)

# 6. Record outcome for future improvement
mind_decide(
    memory_ids=["mem_123"],
    decision_summary="PostgreSQL + Drizzle worked well for real-time sync",
    outcome_quality=0.9
)
```

## Integration Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         PROJECT LIFECYCLE                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  IDEATION          PLANNING           EXECUTION         LEARNING       │
│  ────────          ────────           ─────────         ────────       │
│                                                                         │
│  ┌─────────┐      ┌─────────┐        ┌─────────┐       ┌─────────┐    │
│  │ IdeaRalph│ ───►│Architect│ ──────►│ForgeLoop│ ─────►│  Mind   │    │
│  │ Validate│      │  Plan   │        │ Execute │       │  Learn  │    │
│  └─────────┘      └────┬────┘        └────┬────┘       └────┬────┘    │
│       │                │                  │                  │         │
│       │           ┌────┴────┐        ┌────┴────┐            │         │
│       │           │ Spawner │        │  Muse   │            │         │
│       │           │ Skills  │        │ Mutate  │            │         │
│       └───────────┴─────────┴────────┴─────────┴────────────┘         │
│                              ▲                                         │
│                              │                                         │
│                    ┌─────────┴─────────┐                              │
│                    │  Mind Retrieval   │                              │
│                    │  (Past Patterns)  │                              │
│                    └───────────────────┘                              │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## Architecture

See [ARCHITECTURE.md](docs/ARCHITECTURE.md) for detailed system design and [BENCHMARKS.md](docs/BENCHMARKS.md) for performance testing results.

### Core Principles

1. **Separation of Concerns**: Each MCP handles one aspect well
2. **Learning by Default**: Every decision feeds back into memory
3. **Graceful Degradation**: System works even if individual MCPs are unavailable
4. **Explicit Context**: All context is traceable and auditable

### Data Flow

```
User Request
    │
    ▼
┌─────────────┐     ┌─────────────┐
│  Architect  │────►│    Mind     │  "What worked before?"
│  (Router)   │◄────│  (Memory)   │
└──────┬──────┘     └─────────────┘
       │
       ▼
┌─────────────┐     ┌─────────────┐
│   Spawner   │────►│    Muse     │  "What's similar?"
│  (Skills)   │◄────│ (Expansion) │
└──────┬──────┘     └─────────────┘
       │
       ▼
┌─────────────┐
│  ForgeLoop  │  Bounded Execution
│ (Executor)  │
└──────┬──────┘
       │
       ▼
   Validation
       │
       ▼
┌─────────────┐
│    Mind     │  Store Outcome
│  (Learn)    │
└─────────────┘
```

## Component Deep Dives

### Architect MCP
The orchestration layer that coordinates teams, sprints, and tasks:
- **Multi-team coordination**: Backend, Frontend, Database, Auth, Testing, DevOps, Design, Documentation
- **Sprint management**: Goals, tasks, dependencies, quality gates
- **Smart assignment**: Automatic skill loading based on task type
- **Scope enforcement**: Prevents drift during long-running tasks
- **Integration checks**: Cross-team compatibility validation

### Mind MCP
Persistent semantic memory with learning capabilities:
- **Memory types**: Episodic (events), Semantic (facts), Procedural (workflows), Preference (style)
- **Retrieval**: Hybrid semantic + keyword search with RRF fusion
- **Learning loop**: Outcome tracking adjusts memory salience
- **Reflection**: Automatic synthesis of patterns and insights
- **Conflict detection**: Identifies contradictory information

### Muse MCP
Creative ideation and idea mutation:
- **Prompt expansion**: Rich working objects from raw prompts
- **Multi-mode retrieval**: Nearest, analogies, failures, successes, contradictions
- **Mutation operators**: Invert, combine, compress, scale up/down, make safer
- **Candidate ranking**: Value formula balancing usefulness, novelty, feasibility, risk
- **Promotion pipeline**: Quality-gated path to long-term memory

### Spawner MCP
Skill library and validation guardrails:
- **470+ skills**: Covering development, frameworks, patterns, design, marketing, strategy
- **Skill packs**: Curated bundles (essentials, agents, enterprise, finance)
- **Sharp edges**: Proactive gotcha detection per stack
- **Validation**: Security, anti-pattern, and production-readiness checks
- **Stack analysis**: Auto-detection of project technologies

### ForgeLoop MCP
Bounded execution and tracking:
- **Phase management**: Scope, objectives, success criteria
- **Validation commands**: Configurable test/lint/type-check requirements
- **Assumption tracking**: Document and verify assumptions
- **Decision log**: Record and retrieve past decisions
- **Agent prompts**: Generate bounded, context-aware prompts

## Metrics & Evaluation

### Plan Complexity Formula
```
Overall = Team(25%) + Structural(35%) + Integration(40%)

Team Complexity = min(10, team_count * 1.5)
Structural = min(10, (phases * 1.2) + (avg_tasks * 0.3))
Integration = min(10, (dependency_depth * 1.5) + (integration_points * 0.8))
```

### Overall Plan Score
```
Score = (10 - Complexity) * 0.15
      + Feasibility * 0.25
      + Clarity * 0.20
      + Cohesion * 0.20
      + (10 - Risk) * 0.20
```

## API Reference

### Architect Tools
| Tool | Description |
|------|-------------|
| `architect_init` | Initialize a new project |
| `architect_plan` | Create execution plan |
| `architect_spawn_teams` | Create team structure with skills |
| `architect_create_sprint` | Create a new sprint |
| `architect_add_task` | Add task to sprint |
| `architect_smart_assign` | Add task with auto skill loading |
| `architect_smart_discover` | Multi-source skill discovery |
| `architect_evaluate_plan` | Score plan on 5 dimensions |
| `architect_enforce_scope` | Prevent scope drift |
| `architect_review_loop` | Recursive quality review |
| `architect_check_quality_gates` | Verify quality thresholds |
| `architect_full_pipeline` | End-to-end idea to plan |

### Mind Tools
| Tool | Description |
|------|-------------|
| `mind_remember` | Store a memory |
| `mind_retrieve` | Retrieve relevant memories |
| `mind_decide` | Track decision outcomes |
| `mind_reflect` | Generate meta-insights |
| `mind_conflicts` | Get memory conflicts |
| `mind_health` | Check system status |

### Muse Tools
| Tool | Description |
|------|-------------|
| `muse_expand_prompt` | Expand raw prompt to working object |
| `muse_retrieve_associations` | Multi-mode memory retrieval |
| `muse_generate_analogies` | Cross-domain structural mappings |
| `muse_find_contradictions` | Surface tensions and counter-evidence |
| `muse_mutate_ideas` | Apply transformation operators |
| `muse_rank_candidates` | Score ideas on value formula |
| `muse_promote_to_mind` | Promote quality candidates to memory |

### Spawner Tools
| Tool | Description |
|------|-------------|
| `spawner_orchestrate` | Session initialization |
| `spawner_skills` | Search/list/get skills |
| `spawner_load` | Load skills for context |
| `spawner_validate` | Run guardrail checks |
| `spawner_watch_out` | Get stack-specific gotchas |
| `spawner_analyze` | Analyze existing codebase |

### ForgeLoop Tools
| Tool | Description |
|------|-------------|
| `forgeloop_init` | Initialize project tracking |
| `forgeloop_create_phase` | Create execution phase |
| `forgeloop_record_validation` | Record validation results |
| `forgeloop_add_assumption` | Track assumptions |
| `forgeloop_add_decision` | Record decisions |
| `forgeloop_generate_prompt` | Generate bounded agent prompts |

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Type check
mypy src

# Lint
ruff check src
```

## Philosophy

The Flow Stack follows these principles:

1. **Start Simple**: Begin with minimal viable structure, add complexity only when needed
2. **Learn Always**: Every interaction is an opportunity to improve
3. **Clear Boundaries**: Each component owns a specific domain
4. **Fail Gracefully**: Partial results beat total failures
5. **Integrate Early**: Continuous checks catch issues before they compound

## Testing & Benchmarks

We conducted extensive testing across individual MCPs and their combined workflows. See [BENCHMARKS.md](docs/BENCHMARKS.md) for complete results.

### Summary: Individual MCP Performance

| MCP | Key Operation | p50 Latency | p99 Latency |
|-----|---------------|-------------|-------------|
| Mind | retrieve (10 results) | 45ms | 120ms |
| Muse | expand_prompt | 180ms | 450ms |
| Spawner | skills search | 25ms | 80ms |
| Architect | plan | 350ms | 900ms |
| ForgeLoop | generate_prompt | 35ms | 95ms |

### Summary: Combined Stack Performance

| Workflow | p50 | p99 | Quality Improvement |
|----------|-----|-----|---------------------|
| Smart skill discovery | 280ms | 680ms | +22% vs single-source |
| Full pipeline (idea→plan) | 800ms | 2.1s | +30% plan quality |
| Learning loop | 90ms | 180ms | Enables improvement over time |

### Key Finding

The 2-3x latency increase from using the full stack is justified by the **20-30% improvement in output quality** across tested scenarios. The learning loop ensures this quality gap widens over time as the system accumulates experience.

## Contributing

See [CONTRIBUTING.md](docs/CONTRIBUTING.md) for guidelines.

## License

MIT License - see [LICENSE](LICENSE) for details.

---

Built with intelligence by the Flow Team
