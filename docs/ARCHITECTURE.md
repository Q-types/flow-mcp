# Flow Architecture

> System design and component interactions for the MCP stack

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           FLOW STACK                              │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│   ┌───────────────────────────────────────────────────────────────────────┐    │
│   │                         ORCHESTRATION LAYER                            │    │
│   │  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐               │    │
│   │  │  ARCHITECT  │◄──►│  FORGELOOP  │◄──►│  IDEARALPH  │               │    │
│   │  │   (Plan)    │    │  (Execute)  │    │ (Validate)  │               │    │
│   │  └──────┬──────┘    └──────┬──────┘    └─────────────┘               │    │
│   └─────────┼──────────────────┼─────────────────────────────────────────┘    │
│             │                  │                                               │
│   ┌─────────┼──────────────────┼─────────────────────────────────────────┐    │
│   │         │    INTELLIGENCE LAYER                                       │    │
│   │  ┌──────▼──────┐    ┌──────▼──────┐                                  │    │
│   │  │    MIND     │◄──►│    MUSE     │                                  │    │
│   │  │  (Memory)   │    │ (Creative)  │                                  │    │
│   │  └─────────────┘    └─────────────┘                                  │    │
│   └──────────────────────────────────────────────────────────────────────┘    │
│                                                                                 │
│   ┌──────────────────────────────────────────────────────────────────────┐    │
│   │                         CAPABILITY LAYER                              │    │
│   │  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐               │    │
│   │  │   SPAWNER   │    │   SKILLS    │    │   SQUADS    │               │    │
│   │  │  (Router)   │───►│  (470+)     │───►│ (Bundles)   │               │    │
│   │  └─────────────┘    └─────────────┘    └─────────────┘               │    │
│   └──────────────────────────────────────────────────────────────────────┘    │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## Component Architecture

### 1. Architect MCP

**Role**: Project orchestration and multi-agent coordination

```
┌─────────────────────────────────────────────────────────────────┐
│                       THE ARCHITECT                              │
│   (Master Planner - Designs structure, plans phases, monitors)   │
└─────────────────────────────────────────────────────────────────┘
                              │
            ┌─────────────────┼─────────────────┐
            │                 │                 │
       ┌────▼────┐       ┌────▼────┐       ┌────▼────┐
       │SUPERVISOR│       │SUPERVISOR│       │SUPERVISOR│
       │ Backend  │       │ Frontend │       │   API    │
       └────┬─────┘       └────┬─────┘       └────┬─────┘
            │                  │                  │
       ┌────▼────┐       ┌────▼────┐       ┌────▼────┐
       │EXECUTORS│       │EXECUTORS│       │EXECUTORS│
       │  Team   │       │  Team   │       │  Team   │
       └─────────┘       └─────────┘       └─────────┘
            │                  │                  │
            └──────────────────┼──────────────────┘
                               │
                      ┌────────▼────────┐
                      │   INTEGRATOR    │
                      │ (Ensures teams  │
                      │  work together) │
                      └─────────────────┘
```

**Responsibilities**:
- Project initialization and idea analysis
- Sprint and phase management
- Task assignment and dependency tracking
- Quality gate enforcement
- Cross-team integration monitoring

**Key Data Structures**:
```python
@dataclass
class Project:
    id: str
    name: str
    idea: str
    teams: list[Team]
    sprints: list[Sprint]

@dataclass
class Sprint:
    id: str
    name: str
    goal: str
    tasks: list[Task]
    logs: list[LogEntry]

@dataclass
class Task:
    id: str
    title: str
    team: TeamType
    status: TaskStatus
    dependencies: list[str]
    acceptance_criteria: list[str]
```

### 2. Mind MCP

**Role**: Persistent semantic memory with learning capabilities

```
┌─────────────────────────────────────────────────────────────────┐
│                         MIND MCP                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐         │
│  │  EMBEDDING  │───►│   VECTOR    │───►│  RETRIEVAL  │         │
│  │   Engine    │    │   Store     │    │   Engine    │         │
│  │  (nomic)    │    │  (SQLite)   │    │ (Hybrid)    │         │
│  └─────────────┘    └─────────────┘    └──────┬──────┘         │
│                                               │                 │
│  ┌─────────────┐    ┌─────────────┐    ┌──────▼──────┐         │
│  │  CONFLICT   │◄───│  LEARNING   │◄───│  SALIENCE   │         │
│  │  Detection  │    │    Loop     │    │   Scoring   │         │
│  └─────────────┘    └─────────────┘    └─────────────┘         │
│                                                                  │
│  ┌─────────────┐    ┌─────────────┐                             │
│  │ REFLECTION  │───►│  SYNTHESIS  │                             │
│  │  Trigger    │    │  (Insights) │                             │
│  └─────────────┘    └─────────────┘                             │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Memory Types**:
| Type | Description | Decay Rate | Use Case |
|------|-------------|------------|----------|
| Episodic | Events, tasks | 30%/month | Task history, sessions |
| Semantic | Facts, knowledge | 10%/month | Domain expertise |
| Procedural | Workflows, patterns | 5%/month | Best practices |
| Preference | User/project style | 2%/month | Communication style |

**Scoring Formula**:
```
S_i = α·sim(q,m_i) + β·I_i + γ·R_i - δ·A_i

Where:
  sim = Semantic similarity (cosine) + keyword (BM25) via RRF fusion
  I = Importance score (static + dynamic salience)
  R = Recency boost (last accessed)
  A = Age decay penalty (type-specific)
```

### 3. Muse MCP

**Role**: Creative ideation and idea mutation

```
┌─────────────────────────────────────────────────────────────────┐
│                         MUSE MCP                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  INPUT                    PROCESSING                OUTPUT      │
│  ─────                    ──────────                ──────      │
│                                                                  │
│  ┌─────────┐    ┌─────────────────────────┐    ┌─────────┐     │
│  │  Raw    │───►│     EXPANSION           │───►│ Working │     │
│  │ Prompt  │    │  (Goal, Constraints)    │    │ Object  │     │
│  └─────────┘    └─────────────────────────┘    └────┬────┘     │
│                                                      │          │
│                 ┌─────────────────────────┐          │          │
│                 │   MULTI-MODE RETRIEVAL  │◄─────────┘          │
│                 │ ┌───────┐ ┌───────────┐ │                     │
│                 │ │Nearest│ │ Analogies │ │                     │
│                 │ └───────┘ └───────────┘ │                     │
│                 │ ┌───────┐ ┌───────────┐ │                     │
│                 │ │Failures│ │ Successes│ │                     │
│                 │ └───────┘ └───────────┘ │                     │
│                 └───────────┬─────────────┘                     │
│                             │                                   │
│                 ┌───────────▼─────────────┐                     │
│                 │      MUTATION           │                     │
│                 │  ┌────────┐ ┌────────┐  │                     │
│                 │  │ Invert │ │Combine │  │                     │
│                 │  └────────┘ └────────┘  │                     │
│                 │  ┌────────┐ ┌────────┐  │                     │
│                 │  │Compress│ │Scale Up│  │                     │
│                 │  └────────┘ └────────┘  │                     │
│                 └───────────┬─────────────┘                     │
│                             │                                   │
│                 ┌───────────▼─────────────┐    ┌─────────┐     │
│                 │     RANKING             │───►│ Promote │     │
│                 │ V = w_u*U + w_n*N + ... │    │ to Mind │     │
│                 └─────────────────────────┘    └─────────┘     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Mutation Operators**:
- `invert`: Flip the core assumption
- `combine`: Merge with another idea
- `compress`: Simplify to essence
- `modularize`: Break into components
- `make_safer`: Reduce risk
- `make_explainable`: Add clarity
- `make_testable`: Add verification
- `scale_up/down`: Adjust scope

### 4. ForgeLoop MCP

**Role**: Bounded execution and validation tracking

```
┌─────────────────────────────────────────────────────────────────┐
│                       FORGELOOP MCP                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    PHASE MANAGEMENT                      │   │
│  │  ┌─────────┐    ┌─────────┐    ┌─────────┐              │   │
│  │  │  PLAN   │───►│ ACTIVE  │───►│COMPLETE │              │   │
│  │  └─────────┘    └────┬────┘    └─────────┘              │   │
│  │                      │                                   │   │
│  │             ┌────────▼────────┐                          │   │
│  │             │   VALIDATION    │                          │   │
│  │             │  ┌───┐ ┌────┐   │                          │   │
│  │             │  │Test│ │Lint│   │                          │   │
│  │             │  └───┘ └────┘   │                          │   │
│  │             │  ┌────┐ ┌────┐  │                          │   │
│  │             │  │Type│ │Build│  │                          │   │
│  │             │  └────┘ └────┘  │                          │   │
│  │             └─────────────────┘                          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐       │
│  │  ASSUMPTIONS  │  │   DECISIONS   │  │    PROMPTS    │       │
│  │  (Tracking)   │  │   (Log)       │  │  (Bounded)    │       │
│  └───────────────┘  └───────────────┘  └───────────────┘       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Prompt Types**:
- `AUDIT`: Codebase analysis without modification
- `IMPLEMENTATION`: Bounded feature work
- `VALIDATION`: Test/lint execution
- `CORRECTION`: Fix identified failures
- `REFACTOR`: Behavior-preserving changes
- `DOCUMENTATION`: Doc updates only

### 5. Spawner MCP

**Role**: Skill library and validation guardrails

```
┌─────────────────────────────────────────────────────────────────┐
│                       SPAWNER MCP                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    SKILL LIBRARY                         │   │
│  │  ┌───────────┐  ┌───────────┐  ┌───────────┐            │   │
│  │  │Development│  │ Frameworks│  │Integration│            │   │
│  │  │   (120)   │  │   (85)    │  │   (65)    │            │   │
│  │  └───────────┘  └───────────┘  └───────────┘            │   │
│  │  ┌───────────┐  ┌───────────┐  ┌───────────┐            │   │
│  │  │  Pattern  │  │  Design   │  │ Marketing │            │   │
│  │  │   (70)    │  │   (45)    │  │   (40)    │            │   │
│  │  └───────────┘  └───────────┘  └───────────┘            │   │
│  │  ┌───────────┐  ┌───────────┐                           │   │
│  │  │ Strategy  │  │  Startup  │                           │   │
│  │  │   (30)    │  │   (25)    │                           │   │
│  │  └───────────┘  └───────────┘                           │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐       │
│  │ SHARP EDGES   │  │  VALIDATION   │  │    SQUADS     │       │
│  │ (Gotchas)     │  │ (Guardrails)  │  │  (Bundles)    │       │
│  └───────────────┘  └───────────────┘  └───────────────┘       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Skill Packs**:
- `essentials`: Core development skills
- `agents`: AI agent patterns
- `enterprise`: Scale and compliance
- `finance`: Financial applications
- `data-science`: ML/Analytics
- `startup`: MVP and growth

## Inter-Component Communication

### Smart Skill Discovery Pipeline

```
Query: "database"
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│ 1. DOMAIN EXPANSION                                          │
│    "database" → [database, sql, postgres, schema, migration, │
│                  orm, rls, supabase, drizzle, ...]           │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. MIND RETRIEVAL                                            │
│    Query: "skills for database in project context"           │
│    Result: ["supabase-backend", "drizzle-orm"] (past wins)   │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. MUSE ANALOGIES                                            │
│    Source: "Finding skills for: database"                    │
│    Analogies: ["state management", "persistence layer"]      │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. SPAWNER MULTI-SEARCH                                      │
│    Queries: [expanded terms + mind suggestions + analogies]  │
│    Results: Deduplicated, scored by frequency + tag match    │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. CONTEXT FILTERING                                         │
│    Apply: tech_stack boost, task_description match           │
│    Rank: Sort by combined score                              │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ 6. LEARNING                                                  │
│    Store: Selection in Mind for future retrieval             │
│    Later: Record outcome for salience adjustment             │
└─────────────────────────────────────────────────────────────┘
```

### Plan Evaluation Flow

```
Plan Created
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│                    COMPLEXITY METRICS                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Team Complexity (25%)                                       │
│  └─ min(10, team_count * 1.5)                               │
│                                                              │
│  Structural Complexity (35%)                                 │
│  └─ min(10, (phases * 1.2) + (avg_tasks * 0.3))             │
│                                                              │
│  Integration Complexity (40%)                                │
│  └─ min(10, (dependency_depth * 1.5) + (integration * 0.8)) │
│                                                              │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    OTHER DIMENSIONS                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Feasibility (0-10)                                          │
│  └─ Skill availability, team count, timeline                │
│                                                              │
│  Clarity (0-10)                                              │
│  └─ Scope definition, success criteria coverage              │
│                                                              │
│  Cohesion (0-10)                                             │
│  └─ Task distribution, phase flow, dependency alignment      │
│                                                              │
│  Risk (0-10)                                                 │
│  └─ External dependencies, technical uncertainty             │
│                                                              │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    OVERALL SCORE                             │
│                                                              │
│  Score = (10 - Complexity) * 0.15                            │
│        + Feasibility * 0.25                                  │
│        + Clarity * 0.20                                      │
│        + Cohesion * 0.20                                     │
│        + (10 - Risk) * 0.20                                  │
│                                                              │
│  Result: 0-10 with recommendations                           │
└─────────────────────────────────────────────────────────────┘
```

## Data Storage

### Mind MCP
- **Database**: SQLite with FTS5 at `~/.mind/v2/memories.db`
- **Embeddings**: nomic-ai/nomic-embed-text-v1.5 (768 dimensions)
- **Index**: L2-normalized vectors, cosine = dot product

### Architect MCP
- **Storage**: JSON files in project `.architect/` directory
- **Structure**:
  ```
  .architect/
  ├── project.json
  ├── sprints/
  │   └── sprint_001.json
  └── decisions/
      └── decision_001.json
  ```

### ForgeLoop MCP
- **Storage**: JSON/YAML in `.forgeloop/` directory
- **Structure**:
  ```
  .forgeloop/
  ├── project.json
  ├── phases/
  ├── validations/
  ├── assumptions/
  ├── decisions/
  └── prompts/
  ```

## Error Handling

### Graceful Degradation

The stack operates in degraded mode when components are unavailable:

| Missing Component | Fallback Behavior |
|-------------------|-------------------|
| Mind | Skip memory retrieval, no learning loop |
| Muse | Skip analogy expansion, use domain expansion only |
| Spawner | Use basic skill matching, no sharp edges |
| ForgeLoop | Direct execution without phase tracking |

### Error Propagation

```
Component Error
    │
    ├─► Log warning with context
    │
    ├─► Return partial result with error flag
    │
    └─► Continue execution with fallback
```

## Security Considerations

1. **No PII in Memory**: Decision summaries must exclude personal data
2. **Scoped Access**: Each MCP only accesses its own storage
3. **Validation Guards**: Spawner checks for security anti-patterns
4. **Bounded Prompts**: ForgeLoop prevents unbounded agent actions

## Performance Characteristics

See [BENCHMARKS.md](BENCHMARKS.md) for detailed performance testing results.

### Summary Metrics

| Operation | Latency (p50) | Latency (p99) |
|-----------|---------------|---------------|
| Mind retrieve | 45ms | 120ms |
| Muse expand | 180ms | 450ms |
| Spawner search | 25ms | 80ms |
| Architect plan | 350ms | 900ms |
| Full pipeline | 800ms | 2.1s |
