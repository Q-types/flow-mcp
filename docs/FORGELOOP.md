# ForgeLoop MCP

> Bounded execution and validation tracking

## Overview

ForgeLoop MCP provides structured execution tracking for AI-assisted development. It manages phases, validates outputs, tracks assumptions, records decisions, and generates bounded prompts that keep agents focused and auditable.

## Key Features

### Phase Management

Organize work into bounded phases with clear objectives:

```python
# Create a phase
forgeloop_create_phase(
    name="Database Schema Design",
    objective="Create the core data models for the application",
    scope=[
        "User model with authentication fields",
        "Project model with ownership",
        "Task model with status and assignments"
    ],
    success_criteria=[
        "All models have proper relationships",
        "Migrations run without errors",
        "Type hints complete"
    ]
)
```

### Validation Tracking

Record and track validation results:

```python
forgeloop_record_validation(
    phase_id="phase_001",
    command="pytest tests/",
    exit_code=0,
    output_summary="15 passed, 0 failed",
    status="pass"
)

forgeloop_record_validation(
    phase_id="phase_001",
    command="mypy src/",
    exit_code=1,
    output_summary="Found 3 errors in src/models.py",
    status="fail"
)
```

### Assumption Tracking

Document assumptions for later verification:

```python
forgeloop_add_assumption(
    assumption="Users will always have a valid email address",
    related_phase_id="phase_001",
    risk="Could cause issues if OAuth providers don't return email",
    validation_method="Test with Google OAuth account without public email"
)
```

### Decision Recording

Track architectural and implementation decisions:

```python
forgeloop_add_decision(
    title="ORM Selection",
    context="Need to choose between Drizzle, Prisma, and raw SQL",
    decision="Use Drizzle ORM",
    rationale="Better TypeScript inference, smaller bundle size, SQL-like syntax",
    alternatives_considered=["Prisma (too heavy)", "Raw SQL (no type safety)"],
    related_phase_id="phase_001"
)
```

### Bounded Prompts

Generate context-aware, scoped prompts:

```python
prompt = forgeloop_generate_prompt(
    prompt_type="IMPLEMENTATION",
    phase_id="phase_001",
    include_decisions=True,
    include_assumptions=True,
    include_validation_requirements=True
)

# Returns a structured prompt with:
# - Phase objective and scope
# - Success criteria as checklist
# - Relevant decisions
# - Active assumptions
# - Validation commands to run
# - Constraints to prevent scope creep
```

## Phase Lifecycle

```
┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐
│  DRAFT  │────►│ ACTIVE  │────►│ REVIEW  │────►│COMPLETE │
└─────────┘     └────┬────┘     └────┬────┘     └─────────┘
                     │               │
                     ▼               ▼
              ┌─────────────┐ ┌─────────────┐
              │ VALIDATION  │ │ CORRECTION  │
              │  (Running)  │ │  (If fail)  │
              └─────────────┘ └─────────────┘
```

### Status Transitions

| From | To | Trigger |
|------|-----|---------|
| draft | active | `update_phase(status="active")` |
| active | review | All tasks complete |
| review | complete | All validations pass |
| review | active | Validation failure (fix needed) |

## Prompt Types

| Type | Purpose | Constraints |
|------|---------|-------------|
| `AUDIT` | Codebase analysis | No modifications |
| `IMPLEMENTATION` | Feature work | Bounded scope |
| `VALIDATION` | Run tests/lint | No code changes |
| `CORRECTION` | Fix failures | Fix only the failure |
| `REFACTOR` | Code improvement | Behavior-preserving |
| `DOCUMENTATION` | Update docs | Document current state |
| `COMMIT_SUMMARY` | Git message | Conventional format |
| `NEXT_PHASE` | Planning | Based on current state |
| `PROGRESS` | Status review | Assessment only |

### Prompt Examples

**Implementation Prompt:**
```markdown
# Implementation Task: MyProject

## Phase: Database Schema Design

**Objective:** Create the core data models for the application

**Scope:**
- User model with authentication fields
- Project model with ownership
- Task model with status and assignments

**Success Criteria:**
- [ ] All models have proper relationships
- [ ] Migrations run without errors
- [ ] Type hints complete

## Relevant Decisions

- **ORM Selection:** Use Drizzle ORM

## Active Assumptions

- Users will always have a valid email address
  - Risk: Could cause issues if OAuth providers don't return email

## Validation Commands

- `pytest tests/`
- `mypy src/`

## Constraints

- Do NOT refactor unrelated code
- Do NOT add features beyond the scope
- Do NOT claim success without validation
- Keep changes minimal and reversible
```

**Correction Prompt:**
```markdown
# Correction Task: MyProject

## Failed Validations to Address

### mypy src/
- Exit code: 1
- Output: Found 3 errors in src/models.py...

## Instructions

1. Analyze the failure(s) above
2. Classify the failure: code bug, test issue, config problem, or environment
3. Apply the minimal fix required
4. Re-run the failed validation
5. Verify surrounding tests still pass

## Constraints

- Fix ONLY the identified issue
- Do NOT refactor surrounding code
- Do NOT skip or disable tests
```

## API Reference

### Project Management

| Tool | Description |
|------|-------------|
| `forgeloop_init` | Initialize project tracking |
| `forgeloop_get_project` | Get project details |

### Phase Management

| Tool | Description |
|------|-------------|
| `forgeloop_create_phase` | Create execution phase |
| `forgeloop_update_phase` | Update phase status |
| `forgeloop_get_phase` | Get phase details |
| `forgeloop_get_active_phase` | Get current active phase |
| `forgeloop_list_phases` | List all phases |

### Validation

| Tool | Description |
|------|-------------|
| `forgeloop_record_validation` | Record validation results |
| `forgeloop_get_validations` | Get validation history |

### Assumptions & Decisions

| Tool | Description |
|------|-------------|
| `forgeloop_add_assumption` | Track an assumption |
| `forgeloop_update_assumption` | Confirm/invalidate assumption |
| `forgeloop_get_assumptions` | List assumptions |
| `forgeloop_add_decision` | Record a decision |
| `forgeloop_get_decisions` | List decisions |

### Prompts

| Tool | Description |
|------|-------------|
| `forgeloop_generate_prompt` | Generate bounded prompt |
| `forgeloop_get_prompts` | List generated prompts |

## Storage Structure

```
.forgeloop/
├── project.json              # Project metadata
├── phases/
│   ├── phase_001.json       # Phase definitions
│   └── phase_002.json
├── validations/
│   ├── val_001.json         # Validation results
│   └── val_002.json
├── assumptions/
│   └── asm_001.json         # Tracked assumptions
├── decisions/
│   └── dec_001.json         # Recorded decisions
└── prompts/
    ├── PROMPT-12345.md      # Generated prompts
    └── PROMPT-12346.md
```

## Integration Patterns

### With Architect

```python
# Architect creates sprint, ForgeLoop tracks execution
architect_create_sprint(name="Sprint 1", ...)
architect_add_task(title="Design schema", ...)

# ForgeLoop provides bounded execution
forgeloop_create_phase(
    name="Schema Design",
    objective=task.description
)

prompt = forgeloop_generate_prompt(prompt_type="IMPLEMENTATION")
# Execute with prompt...

forgeloop_record_validation(command="pytest", ...)
architect_update_task(task_id=task.id, status="completed")
```

### With Mind

```python
# Record decisions in both ForgeLoop (local) and Mind (global)
forgeloop_add_decision(
    title="Database Choice",
    decision="PostgreSQL",
    rationale="Relational needs, strong typing"
)

mind_remember(
    content="Chose PostgreSQL for project X: relational needs, strong typing",
    memory_type="episodic"
)
```

## Validation Commands

Configure default validation commands per project:

```python
forgeloop_init(
    name="MyProject",
    default_validation_commands=[
        "pytest tests/",
        "ruff check .",
        "mypy src/",
        "npm run build"
    ]
)
```

### Custom Validation

```python
forgeloop_record_validation(
    phase_id="phase_001",
    command="custom_security_scan.sh",
    exit_code=0,
    output_summary="No vulnerabilities found",
    status="pass"
)
```

## Best Practices

### 1. Create Bounded Phases

```python
# Good - specific and bounded
forgeloop_create_phase(
    name="User Authentication",
    scope=["Login flow", "JWT generation", "Session management"],
    success_criteria=["Tests pass", "Security scan clean"]
)

# Bad - too broad
forgeloop_create_phase(
    name="Build the app",
    scope=["Everything"]
)
```

### 2. Track All Assumptions

```python
# Every "I assume..." should be recorded
forgeloop_add_assumption(
    assumption="API rate limits are 1000/hour",
    validation_method="Check API documentation",
    risk="Could hit limits during peak usage"
)
```

### 3. Record Decisions with Context

```python
forgeloop_add_decision(
    title="Auth Strategy",
    context="Need to choose authentication approach",
    decision="JWT with refresh tokens",
    rationale="Stateless scaling, mobile support",
    alternatives_considered=["Sessions (state issues)", "OAuth only (limited)"]
)
```

### 4. Use Appropriate Prompt Types

```python
# Investigation - use AUDIT
forgeloop_generate_prompt(prompt_type="AUDIT")

# Building - use IMPLEMENTATION
forgeloop_generate_prompt(prompt_type="IMPLEMENTATION")

# Fixing - use CORRECTION
forgeloop_generate_prompt(prompt_type="CORRECTION")
```

### 5. Validate Before Completing

```python
# Always run validations before marking complete
for cmd in project.default_validation_commands:
    result = run(cmd)
    forgeloop_record_validation(
        command=cmd,
        exit_code=result.code,
        status="pass" if result.code == 0 else "fail"
    )

# Only complete if all pass
if all_validations_pass:
    forgeloop_update_phase(phase_id, status="complete")
```

## Performance

| Operation | p50 | p99 |
|-----------|-----|-----|
| init | 18ms | 48ms |
| create_phase | 12ms | 35ms |
| record_validation | 25ms | 70ms |
| add_assumption | 8ms | 25ms |
| add_decision | 10ms | 28ms |
| generate_prompt (simple) | 35ms | 95ms |
| generate_prompt (full) | 120ms | 350ms |

## Assumption Statuses

| Status | Description |
|--------|-------------|
| `unconfirmed` | Needs verification |
| `confirmed` | Verified correct |
| `invalidated` | Proven false |
| `deferred` | Check later |

## Decision Statuses

| Status | Description |
|--------|-------------|
| `proposed` | Under consideration |
| `accepted` | Approved for implementation |
| `rejected` | Not proceeding |
| `superseded` | Replaced by newer decision |
