# ForgeLoop MCP

A local-first MCP server for disciplined agentic software engineering. It gives coding agents a repeatable audit-plan-implement-validate-record-checkpoint loop, so long-running projects stay coherent, testable, and traceable.

> ForgeLoop MCP keeps AI-assisted coding projects from turning into archaeology.

## What It Does

ForgeLoop MCP is an iterative engineering orchestration server that helps AI coding agents:

- **Audit** current project state (files, git, structure)
- **Plan** bounded implementation phases
- **Implement** changes with tracked scope
- **Validate** with test/lint/build commands
- **Record** decisions, assumptions, and validation evidence
- **Checkpoint** progress with clear next actions

## Core Equation

```
S_{t+1} = Checkpoint(Record(Validate(Implement(Plan(Audit(S_t, R_t))))))
```

The next project state equals checkpointing after recording after validating after implementing after planning from an audit of the current state and requirements.

## Installation

```bash
pip install forgeloop-mcp
```

Or for development:

```bash
git clone https://github.com/yourusername/forgeloop-mcp
cd forgeloop-mcp
pip install -e ".[dev]"
```

## Configuration

Add to your MCP client configuration (e.g., Claude Code `~/.claude/settings.json`):

```json
{
  "mcpServers": {
    "forgeloop": {
      "command": "forgeloop-mcp",
      "args": []
    }
  }
}
```

## Tools

### Project State

| Tool | Description |
|------|-------------|
| `scan_project_state` | Scan project directory for git state, files, and structure |
| `audit_source_of_truth` | Classify files as canonical, generated, migration, etc. |

### Phase Management

| Tool | Description |
|------|-------------|
| `create_phase` | Create a new implementation phase with objective and success criteria |
| `update_phase` | Update phase status, notes, files changed |
| `complete_phase` | Mark phase complete with validation evidence |

### Decision & Assumption Tracking

| Tool | Description |
|------|-------------|
| `record_decision` | Store confirmed technical/domain decisions |
| `record_assumption` | Track assumptions that need validation |

### Validation

| Tool | Description |
|------|-------------|
| `run_validation_command` | Execute pytest, npm test, etc. and capture results |
| `record_validation` | Manually record validation results |

### Reports & Prompts

| Tool | Description |
|------|-------------|
| `generate_report` | Create Markdown reports (project status, phase completion, etc.) |
| `generate_agent_prompt` | Generate bounded prompts for coding agents |
| `recommend_next_action` | Analyze state and suggest next safe action |

## Storage Structure

ForgeLoop creates a `.forgeloop/` directory in your project:

```
.forgeloop/
├── project.json      # Project metadata
├── phases.json       # Implementation phases
├── decisions.json    # Technical decisions
├── assumptions.json  # Tracked assumptions
├── validations.json  # Validation results
├── reports/          # Generated Markdown reports
├── prompts/          # Generated agent prompts
├── logs/             # Validation command output
└── snapshots/        # Project state snapshots
```

## Example Workflow

```
1. scan_project_state(root_path="/path/to/project")
   → Understand current state

2. create_phase(name="Add auth", objective="Add JWT authentication")
   → Define bounded work

3. record_decision(title="Use JWT", decision="JWT for stateless auth")
   → Track design choices

4. generate_agent_prompt(prompt_type="implementation")
   → Get bounded prompt for coding agent

5. [Agent implements changes]

6. run_validation_command(command="pytest", working_directory="/path/to/project")
   → Capture test results

7. complete_phase(files_changed=["src/auth.py", "tests/test_auth.py"])
   → Record completion with evidence

8. recommend_next_action()
   → Get suggested next step
```

## MVP Limitations

This is an MVP focused on the engineering loop. Not included:

- Automatic code editing
- Deep AST analysis
- CI/CD integration
- Cloud sync
- Multi-user support

## Philosophy

ForgeLoop prefers:

```
small bounded changes + explicit validation + recorded reasoning
```

over:

```
large speculative rewrites + assumed correctness
```

## License

MIT
