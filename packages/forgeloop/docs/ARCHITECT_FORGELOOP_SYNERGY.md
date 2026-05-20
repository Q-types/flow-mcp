# Architect MCP + ForgeLoop MCP Synergy Analysis

## Executive Summary

**Architect MCP** and **ForgeLoop MCP** are complementary systems designed to work together:

| Aspect | Architect MCP | ForgeLoop MCP |
|--------|---------------|---------------|
| **Level** | Strategic/Planning | Tactical/Execution |
| **Scope** | Project-wide | Phase/file-level |
| **Focus** | What to build | How to build it safely |
| **State** | Tasks, sprints, teams | Phases, validations, decisions |
| **Integration** | IdeaRalph, Mind, Spawner | Git, filesystem, test runners |

---

## Responsibility Matrix

### Architect MCP Owns

| Domain | Tools | Purpose |
|--------|-------|---------|
| **Project Lifecycle** | `architect_init`, `architect_plan`, `architect_full_pipeline` | Create and plan projects |
| **Team Management** | `architect_spawn_teams`, `architect_get_team`, `architect_assign_supervisor` | Agent team structure |
| **Sprint Planning** | `architect_create_sprint`, `architect_complete_sprint` | Time-boxed iterations |
| **Task Tracking** | `architect_add_task`, `architect_update_task`, `architect_list_tasks`, `architect_smart_assign` | Work item management |
| **Quality Gates** | `architect_check_integration`, `architect_review_loop`, `architect_check_quality_gates` | Cross-team validation |
| **Supervision** | `architect_supervisor_review`, `architect_enforce_scope`, `architect_project_manager_review` | Drift detection |
| **Idea Validation** | `architect_validate_idea`, `architect_generate_prd` | PMF scoring via IdeaRalph |
| **Context Loading** | `architect_load_context`, `architect_get_gotchas`, `architect_connect_mind` | Memory and skills |

### ForgeLoop MCP Owns

| Domain | Tools | Purpose |
|--------|-------|---------|
| **Project State** | `init_project`, `get_project`, `scan_project_state` | Local project inspection |
| **Implementation Phases** | `create_phase`, `update_phase`, `complete_phase`, `list_phases` | Bounded work tracking |
| **Technical Decisions** | `record_decision`, `list_decisions` | Design choice tracking |
| **Assumptions** | `record_assumption`, `list_assumptions` | Risk tracking |
| **Validation Execution** | `run_validation_command`, `record_validation`, `list_validations` | Test/lint execution |
| **Source Auditing** | `audit_source_of_truth` | File classification |
| **Agent Prompts** | `generate_agent_prompt` | Bounded prompts |
| **Reports** | `generate_report` | Status documentation |
| **Recommendations** | `recommend_next_action` | Next step guidance |

---

## Conceptual Mapping

### Hierarchy

```
Architect Project
    └── Architect Sprint (time-boxed)
            └── Architect Task (assignable work item)
                    └── ForgeLoop Phase (implementation unit)
                            ├── ForgeLoop Decisions (design choices)
                            ├── ForgeLoop Assumptions (risks)
                            └── ForgeLoop Validations (evidence)
```

### State Equations

**Architect** (project planning):
```
Project_{t+1} = Plan(Validate_idea(Requirements_t))
Sprint_{t+1} = PM_Review(Quality_Gates(Sprint_t))
```

**ForgeLoop** (implementation discipline):
```
S_{t+1} = Checkpoint(Record(Validate(Implement(Plan(Audit(S_t, R_t))))))
```

### Combined:
```
Delivery = Architect(WHAT) × ForgeLoop(HOW)
```

---

## Integration Points

### 1. Task → Phase Mapping

When an Architect task is assigned, create a corresponding ForgeLoop phase:

```
Architect Task                  ForgeLoop Phase
─────────────────────────────────────────────────────
task.title            →         phase.name
task.description      →         phase.objective
task.acceptance_criteria →      phase.success_criteria
task.team             →         (context for prompts)
```

### 2. Validation → Task Status

ForgeLoop validation results can update Architect task status:

```
ForgeLoop Validation            Architect Task Update
─────────────────────────────────────────────────────
validation.status = "pass"  →   task.status = "review"
validation.status = "fail"  →   task.status = "in_progress" + blocker
phase.status = "complete"   →   task.status = "completed"
```

### 3. Supervision Integration

Architect's scope enforcement can use ForgeLoop's phase data:

```python
# Architect supervisor checks ForgeLoop phase
forgeloop_phase = forgeloop.get_active_phase(root_path)
if forgeloop_phase.files_changed != expected_files:
    architect.enforce_scope(task_id, drift_detected=True)
```

### 4. Quality Gates

Architect quality gates can incorporate ForgeLoop validations:

```python
# Architect quality gate checks ForgeLoop validation records
validations = forgeloop.list_validations(phase_id=current_phase)
test_pass_rate = sum(v.passed for v in validations) / sum(v.passed + v.failed)
architect.check_quality_gates(test_pass_rate=test_pass_rate)
```

---

## Orchestration Workflows

### Workflow 1: New Feature Development

```
1. ARCHITECT: architect_init(name="MyApp", idea="...")
2. ARCHITECT: architect_validate_idea(idea="...")  → PMF score
3. ARCHITECT: architect_generate_prd(idea="...")   → Requirements
4. ARCHITECT: architect_plan()                     → Teams, sprints
5. ARCHITECT: architect_spawn_teams()              → Agent structure
6. ARCHITECT: architect_create_sprint(name="Sprint 1", ...)
7. ARCHITECT: architect_add_task(title="Implement auth", ...)

--- Task execution begins ---

8. FORGELOOP: init_project(root_path="/project")
9. FORGELOOP: scan_project_state(root_path="/project")
10. FORGELOOP: create_phase(
        name="Implement auth",
        objective="Add JWT authentication",
        success_criteria=["Tests pass", "Docs updated"]
    )
11. FORGELOOP: record_decision(
        title="Use JWT",
        decision="JWT for stateless auth"
    )
12. FORGELOOP: generate_agent_prompt(prompt_type="implementation")

--- Agent implements code ---

13. FORGELOOP: run_validation_command(command="pytest")
14. FORGELOOP: complete_phase(files_changed=["src/auth.py"])
15. FORGELOOP: recommend_next_action()  → "commit_checkpoint"

--- Back to Architect ---

16. ARCHITECT: architect_update_task(task_id, status="completed")
17. ARCHITECT: architect_supervisor_review(team="backend")
18. ARCHITECT: architect_check_quality_gates(...)
```

### Workflow 2: Bug Fix

```
1. ARCHITECT: architect_add_task(title="Fix login bug", priority=1)

2. FORGELOOP: scan_project_state()
3. FORGELOOP: create_phase(name="Fix login bug", objective="...")
4. FORGELOOP: record_assumption(
        assumption="Bug is in auth middleware",
        risk="May be in frontend instead"
    )
5. FORGELOOP: generate_agent_prompt(prompt_type="correction")

--- Agent fixes bug ---

6. FORGELOOP: run_validation_command(command="pytest tests/test_auth.py")
7. FORGELOOP: complete_phase(validation_ids=["VAL-0001"])

8. ARCHITECT: architect_update_task(status="completed")
```

### Workflow 3: Refactoring

```
1. ARCHITECT: architect_add_task(title="Refactor database layer")

2. FORGELOOP: scan_project_state()
3. FORGELOOP: audit_source_of_truth()  → Identify canonical files
4. FORGELOOP: create_phase(
        name="Refactor DB layer",
        success_criteria=["No behavior change", "Tests pass before/after"]
    )
5. FORGELOOP: run_validation_command(command="pytest")  → Baseline
6. FORGELOOP: generate_agent_prompt(prompt_type="refactor")

--- Agent refactors ---

7. FORGELOOP: run_validation_command(command="pytest")  → Compare
8. FORGELOOP: generate_report(report_type="validation")  → Before/after

9. ARCHITECT: architect_review_loop(task_id, verification_result={...})
```

---

## When to Use Which MCP

| Scenario | Use Architect | Use ForgeLoop |
|----------|---------------|---------------|
| Starting a new project | ✅ `architect_init` | |
| Validating an idea | ✅ `architect_validate_idea` | |
| Planning sprints | ✅ `architect_create_sprint` | |
| Creating tasks | ✅ `architect_add_task` | |
| Starting implementation | | ✅ `create_phase` |
| Running tests | | ✅ `run_validation_command` |
| Recording design decisions | | ✅ `record_decision` |
| Checking team progress | ✅ `architect_supervisor_review` | |
| Checking implementation state | | ✅ `scan_project_state` |
| Quality gate validation | ✅ `architect_check_quality_gates` | ✅ `list_validations` (data source) |
| Sprint completion | ✅ `architect_complete_sprint` | |
| Phase completion | | ✅ `complete_phase` |
| Generating agent prompts | | ✅ `generate_agent_prompt` |
| Cross-team integration | ✅ `architect_check_integration` | |
| Source-of-truth auditing | | ✅ `audit_source_of_truth` |

---

## CLAUDE.md Integration Snippet

```markdown
## MCP Orchestration Pattern

### Project Planning (Architect MCP)
Use Architect MCP for high-level project management:
- `architect_init` → Start new projects
- `architect_plan` → Generate execution plan
- `architect_create_sprint` → Time-boxed iterations
- `architect_add_task` → Work item tracking
- `architect_supervisor_review` → Team progress checks

### Implementation Discipline (ForgeLoop MCP)
Use ForgeLoop MCP for execution-level tracking:
- `init_project` → Initialize .forgeloop/ in project
- `create_phase` → Bounded implementation units
- `record_decision` / `record_assumption` → Track choices and risks
- `run_validation_command` → Execute and capture test results
- `generate_agent_prompt` → Get bounded prompts for work
- `recommend_next_action` → Safe next step guidance

### Typical Flow
1. Architect creates task
2. ForgeLoop creates phase for task
3. Agent implements with ForgeLoop tracking
4. ForgeLoop captures validation evidence
5. Architect updates task status based on ForgeLoop results
```

---

## Anti-Patterns to Avoid

### ❌ Don't: Use ForgeLoop for project planning
ForgeLoop phases are not sprints. Use Architect for sprint/task planning.

### ❌ Don't: Use Architect for test execution
Architect tracks outcomes, not execution. Use ForgeLoop's `run_validation_command`.

### ❌ Don't: Duplicate state
Don't store the same decision in both systems. ForgeLoop owns technical decisions.

### ❌ Don't: Skip ForgeLoop for quick fixes
Even small changes benefit from `create_phase` → `run_validation` → `complete_phase`.

---

## Future Integration Opportunities

1. **Automatic Task-Phase Sync**: Bridge module that creates ForgeLoop phases when Architect tasks are assigned
2. **Validation Rollup**: Aggregate ForgeLoop validation stats into Architect sprint reports
3. **Unified Reporting**: Combined report showing Architect progress + ForgeLoop evidence
4. **Shared Mind Context**: Both MCPs use Mind MCP for memory, enabling cross-system learning

---

*Generated during Sprint 5: Architect-ForgeLoop Synergy Evaluation*
