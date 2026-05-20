Yes, this can work for any coding job, provided it is framed not as a KSP/database tool, but as a general iterative engineering control system.

The general pattern is:

S_{t+1} = \operatorname{Checkpoint}\left(\operatorname{Record}\left(\operatorname{Validate}\left(\operatorname{Implement}\left(\operatorname{Plan}\left(\operatorname{Audit}(S_t, R_t)\right)\right)\right)\right)\right)

Spoken form:
“The next project state equals checkpointing after recording after validation after implementation after planning after auditing the current state and current requirements.”

That abstraction applies to:

* Python packages
* web apps
* APIs
* dashboards
* databases
* ML pipelines
* DevOps projects
* documentation systems
* agentic software builds
* data engineering pipelines
* research codebases
* automation systems

The MCP should not be “a KSP helper”. It should be a coding-project state-transition governor.

Below is a tightened PDR, PRD, and build prompt.

⸻

ForgeLoop MCP

Product Design Record + Product Requirements Document

⸻

1. PDR: Product Design Record

1.1 Product Name

ForgeLoop MCP

1.2 One-Line Definition

ForgeLoop MCP is an iterative engineering orchestration server that helps AI coding agents audit, plan, implement, validate, record, and checkpoint software changes without losing project coherence.

1.3 Core Problem

AI coding agents can produce useful code quickly, but long-running projects degrade when changes are made without continuously reconciling:

1. the intended design,
2. the current codebase,
3. source-of-truth files,
4. tests and validation evidence,
5. user-confirmed requirements,
6. assumptions,
7. implementation history,
8. next safe actions.

The failure mode is not simply “bad code”.
It is state drift.

A project can become locally functional but globally incoherent: tests are stale, documentation lies, migrations no longer match the install path, business rules live only in chat, and future agents inherit a fog machine.

1.4 Product Goal

ForgeLoop MCP should provide a repeatable engineering loop:

OBSERVE → COMPARE → PLAN → IMPLEMENT → VALIDATE → RECORD → CHECKPOINT → NEXT

The server should help agents answer:

What exists?
What is intended?
What changed?
Why did it change?
Did it work?
What evidence proves it?
What remains uncertain?
What is the safest next action?

1.5 Generalised Use Cases

ForgeLoop MCP should work across software domains.

Domain	Example Use
Python packages	Refactor modules, run tests, record design decisions
Web apps	Add features, validate routes/components/builds
APIs	Compare OpenAPI specs to implementation
Databases	Align schema, migrations, seed data and live DB
ML systems	Track data assumptions, experiment changes and validation
Data pipelines	Validate transformations, schemas, freshness and outputs
Dashboards	Track metrics definitions, UI changes and data checks
DevOps	Validate Docker, CI, deployment and environment changes
Agent systems	Generate bounded prompts and track agent decisions
Documentation	Ensure docs match current system behaviour

1.6 Core Design Principle

ForgeLoop MCP should not primarily be a code writer.

It should be a state discipline layer for coding agents.

The central equation is:

S_{t+1} = F(S_t, R_t, E_t)

Spoken form:
“The next project state equals ForgeLoop applied to the current state, current requirements, and current evidence.”

Where:

Symbol	Meaning
S_t	current project state
R_t	current requirements
E_t	evidence from tests, scans, audits, logs and user confirmations
F	ForgeLoop transition process

Expanded:

S_{t+1} =
Ckpt
\left(
Rec
\left(
Val
\left(
Impl
\left(
Plan
\left(
Audit(S_t, R_t)
\right)
\right)
\right)
\right)
\right)

Spoken form:
“The next state equals checkpointing after recording after validating after implementing after planning from an audit of the current state and requirements.”

1.7 Product Philosophy

ForgeLoop MCP should behave like:

* a technical foreman,
* a lab notebook,
* a regression-test conscience,
* a source-of-truth inspector,
* a change-control assistant.

It should prefer:

small bounded changes + explicit validation + recorded reasoning

over:

large speculative rewrites + assumed correctness

1.8 What ForgeLoop Is Not

ForgeLoop MCP is not:

* a general memory server,
* a full autonomous programmer,
* a CI/CD replacement,
* a database-only migration tool,
* a project management app,
* a code-generation engine.

It can generate prompts and reports, but its main role is to structure the engineering loop.

⸻

2. PRD: Product Requirements Document

2.1 Product Summary

ForgeLoop MCP is a local MCP server that helps AI coding agents run controlled iterative development workflows. It scans project state, records phases, stores decisions and assumptions, runs validation commands, audits source-of-truth alignment, generates reports, and recommends next actions.

2.2 Primary Users

User	Need
Technical founder	Keep AI-built software coherent over many sessions
Software engineer	Track implementation phases and validation evidence
Data scientist	Preserve experiment/code assumptions and validation results
ML engineer	Record model/data/pipeline decisions
Data engineer	Validate schemas, transformations and outputs
Consultant	Build client systems with traceable requirements
Agent orchestrator	Generate bounded prompts for coding agents

2.3 Jobs To Be Done

JTBD 1: Maintain Project Coherence

When an agent makes repeated code changes, I want each phase to have a clear objective, scope, validation result and next action, so the project does not become a pile of clever fragments.

JTBD 2: Prevent Source-of-Truth Drift

When files, docs, schemas, generated code or live systems change, I want ForgeLoop to identify what is canonical, what is temporary, what is obsolete, and what must be reconciled.

JTBD 3: Validate Before Continuing

When an implementation appears complete, I want ForgeLoop to run or record validation evidence before recommending the next phase.

JTBD 4: Preserve Decisions and Assumptions

When I confirm a rule, design choice or simplification, I want it stored separately as a decision, assumption or known limitation, so future work does not contradict it.

JTBD 5: Generate Better Coding-Agent Prompts

When I pass work to Codex, Claude Code, Cursor, Windsurf or another agent, I want a bounded prompt that includes current state, relevant decisions, constraints, validation requirements and output expectations.

JTBD 6: Recommend the Safest Next Step

When a phase finishes, I want ForgeLoop to recommend whether to proceed, test, refactor, document, ask a question, commit, branch, tag or stop.

⸻

3. MVP Scope

3.1 MVP Features

The first version should be local, file-backed, and simple.

Use:

.forgeloop/
  project.json
  phases.json
  decisions.json
  assumptions.json
  validations.json
  reports/
  snapshots/

No database is required for MVP.

3.2 MVP Tool List

Build these MCP tools first:

scan_project_state
create_phase
update_phase
complete_phase
record_decision
record_assumption
record_validation
run_validation_command
audit_source_of_truth
generate_report
generate_agent_prompt
recommend_next_action

3.3 Deferred Features

Do not build these in MVP:

* automatic code editing,
* full AST analysis,
* deep database introspection,
* symbolic unit algebra,
* CI/CD integration,
* cloud sync,
* multi-user permissions,
* autonomous migration generation.

Those are later-stage claws. The MVP needs the spine.

⸻

4. Functional Requirements

FR1: Project State Scanner

ForgeLoop shall scan a project directory and return a structured snapshot.

Tool

scan_project_state({
  root_path: string,
  include_git?: boolean,
  include_file_tree?: boolean,
  include_recent_changes?: boolean,
  include_package_files?: boolean,
  include_test_files?: boolean,
  max_depth?: number
}) -> ProjectStateSnapshot

Should Detect

* git branch,
* current commit,
* dirty files,
* staged files,
* package/config files,
* test files,
* docs,
* source directories,
* scripts,
* migrations if present,
* environment files,
* README files,
* recently modified files.

Output Object

{
  "timestamp": "2026-05-17T12:00:00Z",
  "root_path": "/path/to/project",
  "git": {
    "branch": "main",
    "commit": "abc123",
    "dirty": true,
    "changed_files": []
  },
  "detected_files": {
    "source": [],
    "tests": [],
    "docs": [],
    "config": [],
    "scripts": [],
    "migrations": []
  },
  "warnings": [],
  "open_questions": []
}

⸻

FR2: Phase Manager

ForgeLoop shall track bounded implementation phases.

Tools

create_phase({
  name: string,
  objective: string,
  scope: string[],
  success_criteria: string[],
  blockers?: string[],
  risks?: string[]
}) -> PhaseRecord
update_phase({
  phase_id: string,
  status?: "planned" | "active" | "blocked" | "validating" | "complete" | "abandoned",
  notes?: string,
  files_changed?: string[],
  blockers?: string[],
  success_criteria?: string[]
}) -> PhaseRecord
complete_phase({
  phase_id: string,
  validation_ids?: string[],
  files_changed: string[],
  known_limitations?: string[],
  next_recommendation?: string,
  commit_hash?: string
}) -> PhaseCompletionReport

Phase Statuses

planned
active
blocked
validating
complete
abandoned
superseded

⸻

FR3: Decision Ledger

ForgeLoop shall store confirmed technical or domain decisions.

Tool

record_decision({
  title: string,
  decision: string,
  rationale?: string,
  consequences?: string[],
  source?: string,
  status: "proposed" | "accepted" | "rejected" | "superseded",
  related_files?: string[],
  related_phase_id?: string
}) -> DecisionRecord

Example

{
  "id": "DEC-0001",
  "title": "Use JSON file store for MVP",
  "status": "accepted",
  "decision": "ForgeLoop MVP will use .forgeloop JSON files rather than SQLite.",
  "rationale": "Lower complexity and easier inspection during early development.",
  "consequences": [
    "Good for single-user local projects",
    "Can migrate to SQLite later"
  ],
  "source": "Initial product decision",
  "created_at": "2026-05-17T12:00:00Z"
}

⸻

FR4: Assumption Register

ForgeLoop shall track assumptions separately from confirmed decisions.

This matters because assumptions decay.

\text{Confidence}(t) = \text{Confidence}_0 e^{-\lambda t}

Spoken form:
“Confidence at time t equals initial confidence times e to the minus lambda t.”

Meaning: an untested assumption should become less trusted over time unless validated.

Tool

record_assumption({
  assumption: string,
  risk?: string,
  status: "unconfirmed" | "confirmed" | "known_simplification" | "resolved" | "invalidated",
  validation_status?: string,
  resolution_plan?: string,
  related_files?: string[],
  related_phase_id?: string
}) -> AssumptionRecord

Example

{
  "id": "ASM-0001",
  "assumption": "The current test suite covers all critical API routes.",
  "status": "unconfirmed",
  "risk": "A route may break without test failure.",
  "validation_status": "not yet audited",
  "resolution_plan": "Generate route-to-test coverage report."
}

⸻

FR5: Validation Runner

ForgeLoop shall run validation commands and capture outputs.

Tool

run_validation_command({
  command: string,
  working_directory: string,
  phase_id?: string,
  required_pass?: boolean,
  timeout_seconds?: number,
  output_capture?: "summary" | "full"
}) -> ValidationResult

Examples

pytest
npm test
npm run build
ruff check .
mypy .
python scripts/validate_outputs.py
docker compose config

Output

{
  "id": "VAL-0001",
  "command": "pytest",
  "status": "pass",
  "exit_code": 0,
  "duration_seconds": 12.4,
  "passed": 42,
  "failed": 0,
  "output_summary": "42 tests passed",
  "raw_output_path": ".forgeloop/validations/VAL-0001.log"
}

⸻

FR6: Source-of-Truth Audit

ForgeLoop shall classify project files by role and identify possible drift.

Tool

audit_source_of_truth({
  root_path: string,
  canonical_patterns?: string[],
  generated_patterns?: string[],
  migration_patterns?: string[],
  docs_patterns?: string[],
  script_patterns?: string[],
  test_patterns?: string[],
  compare_docs_to_code?: boolean
}) -> SourceOfTruthAudit

Classifications

Classification	Meaning
canonical	Expected source of truth
generated	Should not be manually edited
migration	Historical or live transition file
ad_hoc	Useful but not yet integrated
obsolete	Should not be used
unknown	Requires review
test	Validation artefact
documentation	Human-readable explanation

Audit Should Flag

* scripts that modify state but are not documented,
* migrations not included in install process,
* tests not run recently,
* docs that mention missing files,
* generated files being edited manually,
* duplicated logic,
* config files with conflicting settings,
* dirty git state before major change.

⸻

FR7: Report Generator

ForgeLoop shall generate Markdown reports.

Tool

generate_report({
  report_type:
    | "project_status"
    | "phase_completion"
    | "validation"
    | "source_of_truth"
    | "gap_analysis"
    | "decision_summary"
    | "assumption_summary"
    | "next_phase_plan",
  output_path?: string,
  phase_id?: string,
  include_decisions?: boolean,
  include_assumptions?: boolean,
  include_validations?: boolean
}) -> ReportResult

Example Reports

docs/FORGELOOP_PROJECT_STATUS.md
docs/PHASE_03_COMPLETION_REPORT.md
docs/SOURCE_OF_TRUTH_AUDIT.md
docs/VALIDATION_REPORT.md
docs/NEXT_PHASE_PLAN.md

⸻

FR8: Agent Prompt Generator

ForgeLoop shall generate bounded prompts for coding agents.

Tool

generate_agent_prompt({
  prompt_type:
    | "audit"
    | "implementation"
    | "validation"
    | "correction"
    | "refactor"
    | "documentation"
    | "commit_summary"
    | "next_phase",
  phase_id?: string,
  context_level?: "brief" | "standard" | "full",
  include_decisions?: boolean,
  include_assumptions?: boolean,
  include_validation_requirements?: boolean,
  include_file_context?: boolean
}) -> string

Prompt Should Include

* project name,
* current phase,
* objective,
* scope,
* exclusions,
* relevant decisions,
* relevant assumptions,
* files likely involved,
* validation commands,
* required output files,
* instruction to avoid unbounded rewrites,
* instruction to report what changed.

⸻

FR9: Next Action Recommender

ForgeLoop shall recommend a next action based on current state.

Tool

recommend_next_action({
  phase_id?: string,
  include_git_state?: boolean,
  include_validation_state?: boolean,
  include_assumptions?: boolean
}) -> NextActionRecommendation

Possible Recommendations

proceed_to_next_phase
run_validation
write_tests
update_docs
record_decision
resolve_assumption
commit_checkpoint
branch_before_change
stop_and_ask_user
perform_source_audit
clean_install_or_rebuild

Output

{
  "recommendation": "commit_checkpoint",
  "confidence": "high",
  "rationale": "Phase complete, validation passed, docs generated, no dirty unknown files.",
  "required_before_next": [
    "Commit current changes",
    "Tag stable checkpoint"
  ]
}

⸻

5. Non-Functional Requirements

NFR1: Local-First

MVP should work entirely locally.

NFR2: Transparent Storage

All records should be human-readable JSON or Markdown.

NFR3: Conservative Change Control

ForgeLoop should favour small, reversible, bounded changes.

NFR4: Evidence-Based Recommendations

The server should avoid claiming success without validation records.

NFR5: Separation of Fact Types

ForgeLoop must distinguish:

Type	Example
confirmed decision	“Use FastAPI for API layer.”
assumption	“Existing tests cover main flows.”
known simplification	“Authentication is mocked in MVP.”
unresolved blocker	“Production database credentials unavailable.”
obsolete belief	“Old CLI command still exists.”

NFR6: Agent-Agnostic

ForgeLoop should work with:

* Claude Code,
* Codex,
* Cursor,
* Windsurf,
* Continue,
* custom agents,
* terminal-based workflows.

NFR7: Language-Agnostic

ForgeLoop should support any coding project by default.

Optional detection can support:

* Python,
* JavaScript/TypeScript,
* SQL,
* Docker,
* Rust,
* Go,
* Java,
* R,
* notebooks.

⸻

6. Data Model

6.1 Project Record

{
  "project_id": "proj_001",
  "name": "Example Project",
  "root_path": "/path/to/project",
  "created_at": "2026-05-17T12:00:00Z",
  "updated_at": "2026-05-17T12:00:00Z",
  "default_validation_commands": [
    "pytest",
    "npm test"
  ]
}

6.2 Phase Record

{
  "id": "PHASE-0001",
  "name": "Add authentication middleware",
  "status": "active",
  "objective": "Add token-based auth middleware to the API.",
  "scope": [
    "middleware",
    "tests",
    "docs"
  ],
  "success_criteria": [
    "Unauthenticated requests return 401",
    "Authenticated requests pass through",
    "Tests pass"
  ],
  "files_changed": [],
  "created_at": "2026-05-17T12:00:00Z",
  "completed_at": null
}

6.3 Decision Record

{
  "id": "DEC-0001",
  "title": "Use JWT middleware",
  "status": "accepted",
  "decision": "Use JWT validation middleware at the API boundary.",
  "rationale": "Keeps route handlers simple and centralises auth checks.",
  "consequences": [
    "Tests need mock tokens",
    "Middleware must be documented"
  ],
  "source": "User confirmed",
  "related_phase_id": "PHASE-0001",
  "created_at": "2026-05-17T12:00:00Z"
}

6.4 Assumption Record

{
  "id": "ASM-0001",
  "assumption": "The application will only need one auth provider in MVP.",
  "status": "unconfirmed",
  "risk": "Multi-provider auth may require design changes.",
  "validation_status": "not tested",
  "resolution_plan": "Confirm before production release.",
  "related_phase_id": "PHASE-0001"
}

6.5 Validation Record

{
  "id": "VAL-0001",
  "phase_id": "PHASE-0001",
  "command": "pytest",
  "status": "pass",
  "exit_code": 0,
  "duration_seconds": 8.2,
  "output_summary": "18 passed",
  "raw_output_path": ".forgeloop/validations/VAL-0001.log",
  "created_at": "2026-05-17T12:00:00Z"
}

⸻

7. Workflow Templates

7.1 General Coding Workflow

1. scan_project_state
2. create_phase
3. record relevant decisions/assumptions
4. generate_agent_prompt(type="implementation")
5. coding agent modifies files
6. run_validation_command
7. generate_report(type="phase_completion")
8. recommend_next_action
9. commit checkpoint if safe

7.2 Audit Workflow

1. scan_project_state
2. audit_source_of_truth
3. list unknown/ad-hoc/obsolete files
4. generate source-of-truth report
5. recommend reconcile/test/document/commit

7.3 Correction Workflow

1. read failed validation
2. classify failure: code, test, config, data, environment, assumption
3. generate correction prompt
4. apply minimal fix
5. rerun failed validation
6. rerun surrounding regression tests
7. record validation
8. update phase

7.4 Refactor Workflow

1. create refactor phase
2. define non-behaviour-changing success criteria
3. snapshot current validation state
4. generate bounded refactor prompt
5. run tests before and after
6. compare validation results
7. report changed files and risk

7.5 ML/Data Workflow

1. scan project
2. record data assumptions
3. create experiment or pipeline phase
4. run validation command
5. record metrics
6. generate report
7. recommend whether model/data/pipeline is stable enough to proceed

⸻

8. Acceptance Criteria

ForgeLoop MVP is successful when it can:

Criterion	Required
Initialise .forgeloop/ project state	Yes
Scan git and project files	Yes
Create and complete phases	Yes
Record decisions	Yes
Record assumptions	Yes
Run validation commands	Yes
Store validation logs	Yes
Generate Markdown reports	Yes
Generate coding-agent prompts	Yes
Recommend next safe action	Yes
Work on non-KSP projects	Yes
Work without a database	Yes
Automatically edit source code	No
Perform deep semantic code analysis	No
Replace CI/CD	No

⸻

9. Recommended Implementation Architecture

9.1 Tech Stack

Recommended MVP:

Language: TypeScript or Python
Storage: JSON files
Reports: Markdown
Runtime: local MCP server
Execution: subprocess for validation commands

Given your broader tooling, I would choose Python if you want fast iteration and easy integration with data/scientific workflows.

Choose TypeScript if your agent/MCP ecosystem is already more Node-oriented.

9.2 Suggested Folder Structure

forgeloop-mcp/
  README.md
  pyproject.toml
  src/
    forgeloop_mcp/
      __init__.py
      server.py
      models.py
      storage.py
      project_scan.py
      git_utils.py
      validation.py
      reports.py
      prompts.py
      recommender.py
      source_audit.py
  tests/
    test_storage.py
    test_phase_manager.py
    test_validation.py
    test_reports.py
  examples/
    example_project/
  docs/
    PRD.md
    PDR.md

9.3 Storage Structure Created in Target Projects

.forgeloop/
  project.json
  phases.json
  decisions.json
  assumptions.json
  validations.json
  snapshots/
  reports/
  prompts/
  logs/

⸻

10. Prompt to Build ForgeLoop MCP

Copy this into your coding agent.

You are an expert MCP server engineer, senior software architect, and disciplined software delivery lead.
Your task is to build a new MCP server called ForgeLoop MCP.
ForgeLoop MCP is a local-first iterative engineering orchestration server. Its purpose is to help AI coding agents manage long-running software projects through a repeatable loop:
OBSERVE → COMPARE → PLAN → IMPLEMENT → VALIDATE → RECORD → CHECKPOINT → NEXT
The server should not primarily be a code generator. It should be a project-state discipline layer that helps agents preserve decisions, assumptions, validation evidence, source-of-truth alignment, and safe next actions.
Core equation:
S_{t+1} = Checkpoint(Record(Validate(Implement(Plan(Audit(S_t, R_t))))))
Spoken meaning: the next project state equals checkpointing after recording after validating after implementing after planning from an audit of the current state and current requirements.
Build this as a general-purpose coding-project MCP, not as a KSP-specific tool. It must work for Python, JavaScript/TypeScript, SQL, data science, ML, dashboard, API, database, and documentation-heavy projects.
MVP SCOPE
Build only the MVP. Do not over-engineer.
The MVP must provide the following MCP tools:
1. scan_project_state
2. create_phase
3. update_phase
4. complete_phase
5. record_decision
6. record_assumption
7. record_validation
8. run_validation_command
9. audit_source_of_truth
10. generate_report
11. generate_agent_prompt
12. recommend_next_action
Do not implement automatic code editing in the MVP.
Do not implement deep AST analysis in the MVP.
Do not require a database in the MVP.
Do not require cloud services.
Use local human-readable JSON and Markdown files.
STORAGE MODEL
When used inside a target project, ForgeLoop should create and maintain:
.forgeloop/
  project.json
  phases.json
  decisions.json
  assumptions.json
  validations.json
  snapshots/
  reports/
  prompts/
  logs/
All JSON files should be human-readable and stable.
Use IDs such as:
PHASE-0001
DEC-0001
ASM-0001
VAL-0001
REP-0001
FUNCTIONAL REQUIREMENTS
1. scan_project_state
Input:
- root_path: string
- include_git?: boolean
- include_file_tree?: boolean
- include_recent_changes?: boolean
- include_package_files?: boolean
- include_test_files?: boolean
- max_depth?: number
Output:
A structured project snapshot containing:
- timestamp
- root_path
- git branch
- git commit
- dirty state
- changed files
- detected source files
- detected test files
- detected docs
- detected config files
- detected scripts
- detected migrations
- warnings
- open questions
It should not invent files. It must inspect the filesystem.
2. create_phase
Input:
- name
- objective
- scope
- success_criteria
- blockers?
- risks?
Output:
A PhaseRecord stored in .forgeloop/phases.json.
Allowed statuses:
- planned
- active
- blocked
- validating
- complete
- abandoned
- superseded
3. update_phase
Input:
- phase_id
- optional status
- notes
- files_changed
- blockers
- success_criteria
Output:
Updated PhaseRecord.
4. complete_phase
Input:
- phase_id
- validation_ids?
- files_changed
- known_limitations?
- next_recommendation?
- commit_hash?
Output:
PhaseCompletionReport.
The phase should only be marked complete if either:
- validation evidence exists, or
- the completion explicitly states that validation was not run and why.
5. record_decision
Input:
- title
- decision
- rationale?
- consequences?
- source?
- status: proposed | accepted | rejected | superseded
- related_files?
- related_phase_id?
Output:
DecisionRecord stored in .forgeloop/decisions.json.
Decisions are confirmed or proposed design/domain choices.
6. record_assumption
Input:
- assumption
- risk?
- status: unconfirmed | confirmed | known_simplification | resolved | invalidated
- validation_status?
- resolution_plan?
- related_files?
- related_phase_id?
Output:
AssumptionRecord stored in .forgeloop/assumptions.json.
Assumptions must be kept separate from decisions.
7. record_validation
Input:
- phase_id?
- command?
- status: pass | fail | warning | not_run
- exit_code?
- duration_seconds?
- passed?
- failed?
- output_summary?
- raw_output_path?
Output:
ValidationRecord stored in .forgeloop/validations.json.
8. run_validation_command
Input:
- command
- working_directory
- phase_id?
- required_pass?
- timeout_seconds?
- output_capture: summary | full
Behaviour:
- Run the command using subprocess.
- Capture stdout and stderr.
- Store raw output in .forgeloop/logs/.
- Create a validation record.
- Return status, exit code, duration, summary, and path to log.
This must be implemented carefully to avoid shell injection risks.
Prefer argument-list execution where possible.
If shell execution is used, make that explicit and documented.
9. audit_source_of_truth
Input:
- root_path
- canonical_patterns?
- generated_patterns?
- migration_patterns?
- docs_patterns?
- script_patterns?
- test_patterns?
- compare_docs_to_code?
Output:
SourceOfTruthAudit.
The audit should classify files as:
- canonical
- generated
- migration
- ad_hoc
- obsolete
- unknown
- test
- documentation
It should flag:
- ad-hoc scripts
- migrations not clearly included in install path
- docs that appear stale
- generated files that may have been manually edited
- duplicated likely source-of-truth files
- dirty git state
- unknown files requiring review
Keep this heuristic-based for MVP.
10. generate_report
Input:
- report_type:
  - project_status
  - phase_completion
  - validation
  - source_of_truth
  - gap_analysis
  - decision_summary
  - assumption_summary
  - next_phase_plan
- output_path?
- phase_id?
- include_decisions?
- include_assumptions?
- include_validations?
Output:
ReportResult containing:
- report_id
- output_path
- markdown_summary
- created_at
Reports should be written as Markdown under .forgeloop/reports/ unless an output path is provided.
11. generate_agent_prompt
Input:
- prompt_type:
  - audit
  - implementation
  - validation
  - correction
  - refactor
  - documentation
  - commit_summary
  - next_phase
- phase_id?
- context_level: brief | standard | full
- include_decisions?
- include_assumptions?
- include_validation_requirements?
- include_file_context?
Output:
A structured prompt string and optionally a saved prompt file under .forgeloop/prompts/.
The prompt should include:
- project name
- current phase
- objective
- scope
- exclusions
- relevant decisions
- relevant assumptions
- likely files involved
- validation requirements
- required output/reporting format
- instruction to avoid unbounded rewrites
- instruction to explain changed files and validation result
12. recommend_next_action
Input:
- phase_id?
- include_git_state?
- include_validation_state?
- include_assumptions?
Output:
NextActionRecommendation containing:
- recommendation
- confidence
- rationale
- required_before_next
- risks
Possible recommendations:
- proceed_to_next_phase
- run_validation
- write_tests
- update_docs
- record_decision
- resolve_assumption
- commit_checkpoint
- branch_before_change
- stop_and_ask_user
- perform_source_audit
- clean_install_or_rebuild
NON-FUNCTIONAL REQUIREMENTS
1. Local-first.
2. Human-readable storage.
3. Conservative change control.
4. Evidence-based recommendations.
5. Separation of decisions, assumptions, validations and phases.
6. Agent-agnostic.
7. Language-agnostic.
8. No hallucinated implementation status.
9. Clear error messages.
10. Tests for core storage and tool behaviour.
IMPLEMENTATION EXPECTATIONS
Use a clean modular architecture.
Suggested modules:
src/forgeloop_mcp/
  server.py
  models.py
  storage.py
  project_scan.py
  git_utils.py
  validation.py
  reports.py
  prompts.py
  recommender.py
  source_audit.py
Include tests:
tests/
  test_storage.py
  test_phase_manager.py
  test_decisions.py
  test_assumptions.py
  test_validation.py
  test_reports.py
  test_recommender.py
Use typed models. Prefer Pydantic if appropriate.
Use pathlib for filesystem operations.
Use datetime with timezone-aware UTC timestamps.
Use safe JSON read/write with atomic writes where practical.
Make the server robust if .forgeloop/ does not yet exist.
README REQUIREMENTS
Create a README.md explaining:
1. What ForgeLoop MCP is.
2. What problem it solves.
3. How to install it.
4. How to configure it with an MCP client.
5. Tool list.
6. Example workflow.
7. Example prompts generated.
8. MVP limitations.
9. Roadmap.
EXAMPLE WORKFLOW TO SUPPORT
A user wants to add a new feature to a Python project.
The agent should be able to:
1. scan_project_state
2. create_phase with objective and success criteria
3. record assumptions if needed
4. generate_agent_prompt for implementation
5. run_validation_command with pytest
6. generate_report for phase completion
7. recommend_next_action, likely commit_checkpoint or proceed_to_next_phase
QUALITY BAR
The implementation should be simple but real.
Avoid decorative architecture.
Do not create placeholder tools that return fake success.
Every tool should perform useful work.
Where a feature is heuristic, say so in the output.
Where validation was not run, say so explicitly.
Where source-of-truth cannot be determined, classify as unknown rather than guessing.
Deliver the complete MCP server implementation, tests, README, and example usage.

⸻

11. Shorter Orchestration Prompt

For everyday use with a coding agent:

Use ForgeLoop-style development.
For this task, follow this loop:
1. Audit current project state before changing files.
2. Identify the intended target state.
3. Produce a bounded implementation plan.
4. Modify only the necessary files.
5. Run relevant validation commands.
6. Report:
   - files changed,
   - why they changed,
   - validation run,
   - validation result,
   - assumptions made,
   - known limitations,
   - recommended next step.
7. Do not claim success unless validation has passed or you clearly state validation was not run.
8. Prefer updating canonical source files over making one-off patches.
9. Keep decisions and assumptions separate.
10. Ask a blocking question only if implementation cannot safely proceed without it.
Task:
[INSERT TASK HERE]

⸻

12. Best Final Positioning

I would describe ForgeLoop MCP as:

A local-first MCP server for disciplined agentic software engineering. It gives coding agents a repeatable audit-plan-implement-validate-record-checkpoint loop, so long-running projects stay coherent, testable, and traceable.

Or more sharply:

ForgeLoop MCP keeps AI-assisted coding projects from turning into archaeology.

For your ecosystem, it becomes a very useful cross-project primitive:

mind MCP       → remembers concepts and history
architect MCP  → designs systems
executor MCP   → performs tasks
forgeloop MCP  → governs engineering iteration and proof

The key is to keep it general, boring in the right places, and strict about evidence. That is how it becomes useful beyond KSP.