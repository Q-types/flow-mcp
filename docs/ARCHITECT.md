# Architect MCP

> Orchestration layer for multi-agent project coordination

## Overview

Architect MCP is the brain of the Flow stack. It handles project planning, team coordination, sprint management, and quality assurance. When integrated with other MCPs, it provides intelligent skill loading, learning from past decisions, and continuous improvement.

## Key Features

### Multi-Team Coordination
Architect manages specialized teams, each with supervisors and executors:

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
       └─────────┘       └─────────┘       └─────────┘
```

**Available Teams**:
- `backend`: Server-side logic and services
- `frontend`: User interface and client-side
- `database`: Data models and schema
- `api`: API design and endpoints
- `auth`: Authentication and authorization
- `testing`: Tests and quality assurance
- `devops`: Deployment and infrastructure
- `design`: UI/UX design
- `documentation`: Docs and guides

### Sprint Management

Sprints organize work into focused iterations with clear goals:

```python
# Create a sprint
architect_create_sprint(
    name="Sprint 1: Foundation",
    goal="Set up database schema and core models",
    teams=["database", "backend"]
)

# Add tasks with dependencies
architect_add_task(
    title="Define user data model",
    description="Create User model with auth fields",
    team="database",
    priority=1,
    acceptance_criteria=["Has id, email, password_hash", "Timestamps included"]
)

architect_add_task(
    title="Create user service",
    description="CRUD operations for users",
    team="backend",
    dependencies=["task_001"]  # Depends on data model
)
```

### Quality Gates

Automated verification ensures quality at every step:

```python
# Define quality gates
gates = {
    "test_pass_rate": {"threshold": 1.0, "blocking": True},
    "lint_critical_errors": {"threshold": 0, "blocking": True},
    "scope_coverage": {"threshold": 0.9, "blocking": False}
}

# Check gates
architect_check_quality_gates(
    task_id="task_001",
    verification_result={
        "tests": {"passed": 15, "total": 15},
        "lint": {"critical_errors": 0},
        "scope": {"adherence_percentage": 95}
    }
)
```

### Scope Enforcement

Prevents drift during long-running tasks:

```python
architect_enforce_scope(
    task_id="task_001",
    elapsed_ms=180000,  # 3 minutes
    original_scope={
        "deliverables": ["src/models/user.py", "tests/test_user.py"],
        "exclusions": ["src/auth/*"],
        "acceptance_criteria": ["Unit tests pass", "Type hints complete"]
    },
    current_output={
        "modified_files": ["src/models/user.py", "src/auth/session.py"]  # Drift!
    }
)
# Returns: {"drift_detected": True, "out_of_scope": ["src/auth/session.py"], ...}
```

## Smart Features (with MCP Integration)

### Smart Skill Discovery

When Spawner, Mind, and Muse are available:

```python
# Find best skills for a task
result = architect_smart_discover(
    query="database",
    project_context=True
)

# Returns:
# {
#   "skills": ["supabase-backend", "drizzle-orm", "database-patterns"],
#   "confidence": 0.92,
#   "mind_suggestions": ["Used drizzle-orm successfully in last 3 projects"],
#   "muse_analogies": ["Similar to state management patterns"]
# }
```

### Smart Task Assignment

Automatically loads relevant skills when assigning tasks:

```python
architect_smart_assign(
    title="Implement user authentication",
    description="Add login/logout with JWT tokens",
    team="auth",
    feature="auth"  # Triggers auth-complete squad
)

# Automatically loads: nextjs-supabase-auth, jwt-patterns, security-audit
```

### Plan Evaluation

Score plans on multiple dimensions:

```python
evaluation = architect_evaluate_plan()

# Returns:
# {
#   "overall_score": 7.8,
#   "metrics": {
#     "complexity": 5.2,
#     "feasibility": 8.5,
#     "clarity": 7.8,
#     "cohesion": 8.0,
#     "risk": 4.2
#   },
#   "recommendations": [
#     "Consider splitting Phase 3 into smaller phases",
#     "Add more acceptance criteria to database tasks"
#   ]
# }
```

## API Reference

### Project Management

| Tool | Description |
|------|-------------|
| `architect_init` | Initialize a new project from an idea |
| `architect_plan` | Create execution plan with phases and teams |
| `architect_spawn_teams` | Spawn the complete agent team structure |
| `architect_status` | Get comprehensive project status |
| `architect_list_projects` | List all projects |
| `architect_set_active_project` | Switch active project |
| `architect_delete_project` | Delete a project |

### Sprint Management

| Tool | Description |
|------|-------------|
| `architect_create_sprint` | Create a new sprint with goals |
| `architect_complete_sprint` | Mark sprint as completed |
| `architect_get_logs` | Retrieve sprint logs |

### Task Management

| Tool | Description |
|------|-------------|
| `architect_add_task` | Add task to current sprint |
| `architect_update_task` | Update task status |
| `architect_get_task` | Get task details |
| `architect_list_tasks` | List tasks with filters |
| `architect_delete_task` | Remove a task |
| `architect_smart_assign` | Add task with auto skill loading |

### Quality & Monitoring

| Tool | Description |
|------|-------------|
| `architect_check_integration` | Run cross-team compatibility check |
| `architect_supervisor_review` | Get a team supervisor's review |
| `architect_enforce_scope` | Check for scope drift |
| `architect_review_loop` | Recursive quality review |
| `architect_check_quality_gates` | Verify quality thresholds |
| `architect_project_manager_review` | Sprint-level PM review |

### Smart Features

| Tool | Description |
|------|-------------|
| `architect_smart_discover` | Multi-source skill discovery |
| `architect_evaluate_plan` | Score plan on 5 dimensions |
| `architect_record_plan_outcome` | Record plan results for learning |
| `architect_load_skill_pack` | Load a curated skill pack |
| `architect_search_skills` | Search Spawner skills |

### Full Pipeline

| Tool | Description |
|------|-------------|
| `architect_full_pipeline` | End-to-end idea to plan |
| `architect_validate_idea` | IdeaRalph PMF validation |
| `architect_generate_prd` | Generate PRD from idea |
| `architect_load_context` | Load relevant Mind context |
| `architect_get_gotchas` | Get sharp edges for stack |

### Memory Integration

| Tool | Description |
|------|-------------|
| `architect_connect_mind` | Connect to Mind MCP |
| `architect_remember` | Store decisions |
| `architect_log` | Add log entries |

## Configuration

### Project Settings

```json
{
  "default_validation_commands": [
    "pytest",
    "ruff check .",
    "mypy src"
  ],
  "quality_gates": {
    "test_pass_rate": 1.0,
    "lint_critical_errors": 0,
    "scope_coverage": 0.9
  },
  "max_logs_per_sprint": 100
}
```

### Team Skill Mappings

```python
TEAM_SKILLS = {
    "backend": ["supabase-backend", "typescript-strict", "api-design"],
    "frontend": ["react-patterns", "tailwind-ui", "nextjs-app-router"],
    "auth": ["nextjs-supabase-auth", "auth-flow", "security-audit"],
    "database": ["database-patterns", "drizzle-orm", "supabase-rls"],
    "testing": ["test-architect", "vitest-patterns", "playwright-e2e"],
    "devops": ["docker-patterns", "ci-cd", "monitoring"],
    "api": ["api-design", "openapi", "rest-patterns"],
    "design": ["tailwind-ui", "accessibility", "responsive-design"],
    "documentation": ["technical-writing", "api-docs", "readme-guide"]
}
```

## Best Practices

### 1. Start with Validation

Always validate ideas before planning:

```python
# Validate first
result = architect_validate_idea(idea="My startup idea", refine_if_needed=True)

if result["score"] >= 8.0:
    architect_init(name="MyProject", idea=result["refined_idea"])
    architect_plan()
```

### 2. Use Smart Assignment

Let the system find the best skills:

```python
# Instead of:
architect_add_task(title="Add auth", team="auth")
spawner_load(skill_id="auth-patterns")  # Manual

# Use:
architect_smart_assign(
    title="Add auth",
    team="auth",
    feature="auth"  # Auto-loads auth-complete squad
)
```

### 3. Track Outcomes

Enable the learning loop:

```python
# After sprint completion
architect_record_plan_outcome(
    outcome_quality=0.85,
    notes="Sprint completed with minor scope adjustments"
)
```

### 4. Regular Integration Checks

Catch issues early:

```python
# After each major task completion
architect_check_integration()

# At sprint milestones
architect_project_manager_review()
```

### 5. Scope Enforcement for Long Tasks

Prevent drift in complex tasks:

```python
# Check every 2-3 minutes for long-running tasks
architect_enforce_scope(
    task_id="task_001",
    elapsed_ms=elapsed_time,
    original_scope=task.scope,
    current_output=current_state
)
```

## Error Handling

### Graceful Degradation

When integrations are unavailable:

| Missing | Fallback |
|---------|----------|
| Spawner | Basic skill mapping from config |
| Mind | No context retrieval, no learning |
| IdeaRalph | Skip validation, direct planning |

### Error Recovery

```python
try:
    result = architect_smart_discover(query="database")
except SpawnerUnavailable:
    # Fall back to basic skills
    result = {"skills": TEAM_SKILLS["database"], "confidence": 0.5}
```

## Performance

| Operation | Typical Latency |
|-----------|-----------------|
| `architect_init` | 25ms |
| `architect_plan` | 350ms |
| `architect_spawn_teams` | 280ms |
| `architect_smart_assign` | 220ms |
| `architect_full_pipeline` | 800ms |

See [BENCHMARKS.md](BENCHMARKS.md) for detailed performance data.
