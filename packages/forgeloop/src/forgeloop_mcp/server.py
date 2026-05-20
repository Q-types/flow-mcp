"""ForgeLoop MCP Server - Iterative engineering orchestration for AI coding agents."""

import json
from pathlib import Path
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from .models import (
    AssumptionStatus,
    ContextLevel,
    DecisionStatus,
    OutputCapture,
    PhaseStatus,
    PromptType,
    ReportType,
    utc_now,
)
from .project_scan import scan_project
from .prompts import generate_agent_prompt
from .recommender import recommend_next_action
from .reports import generate_report
from .source_audit import audit_source_of_truth
from .storage import ForgeLoopStorage
from .validation import run_validation_command, ValidationError

# Global storage instance (set per-project)
_storage: ForgeLoopStorage | None = None


def get_storage(root_path: str | None = None) -> ForgeLoopStorage:
    """Get or create storage instance."""
    global _storage
    if root_path:
        _storage = ForgeLoopStorage(root_path)
    elif _storage is None:
        # Default to current directory
        _storage = ForgeLoopStorage(Path.cwd())
    return _storage


# =============================================================================
# MCP Server Setup
# =============================================================================

server = Server("forgeloop-mcp")


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List all available ForgeLoop tools."""
    return [
        Tool(
            name="init_project",
            description="Initialize ForgeLoop for a project. Creates .forgeloop/ directory with project.json and sets default validation commands based on detected stack.",
            inputSchema={
                "type": "object",
                "properties": {
                    "root_path": {"type": "string", "description": "Project root directory path"},
                    "name": {"type": "string", "description": "Project name (defaults to directory name)"},
                    "description": {"type": "string", "description": "Project description"},
                    "validation_commands": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Default validation commands (auto-detected if not provided)",
                    },
                },
                "required": ["root_path"],
            },
        ),
        Tool(
            name="scan_project_state",
            description="Scan a project directory and return a structured snapshot including git state, file categorization, and warnings.",
            inputSchema={
                "type": "object",
                "properties": {
                    "root_path": {"type": "string", "description": "Project root directory path"},
                    "include_git": {"type": "boolean", "default": True},
                    "include_file_tree": {"type": "boolean", "default": True},
                    "include_recent_changes": {"type": "boolean", "default": True},
                    "include_package_files": {"type": "boolean", "default": True},
                    "include_test_files": {"type": "boolean", "default": True},
                    "max_depth": {"type": "integer", "default": 5, "minimum": 1, "maximum": 10},
                },
                "required": ["root_path"],
            },
        ),
        Tool(
            name="create_phase",
            description="Create a new implementation phase with objective, scope, and success criteria.",
            inputSchema={
                "type": "object",
                "properties": {
                    "root_path": {"type": "string", "description": "Project root directory"},
                    "name": {"type": "string", "description": "Phase name"},
                    "objective": {"type": "string", "description": "What this phase aims to achieve"},
                    "scope": {"type": "array", "items": {"type": "string"}, "description": "What's in scope"},
                    "success_criteria": {"type": "array", "items": {"type": "string"}, "description": "Measurable success criteria"},
                    "blockers": {"type": "array", "items": {"type": "string"}, "description": "Known blockers"},
                    "risks": {"type": "array", "items": {"type": "string"}, "description": "Known risks"},
                },
                "required": ["root_path", "name", "objective"],
            },
        ),
        Tool(
            name="update_phase",
            description="Update an existing phase's status, notes, files changed, or blockers.",
            inputSchema={
                "type": "object",
                "properties": {
                    "root_path": {"type": "string", "description": "Project root directory"},
                    "phase_id": {"type": "string", "description": "Phase ID to update"},
                    "status": {
                        "type": "string",
                        "enum": ["planned", "active", "blocked", "validating", "complete", "abandoned", "superseded"],
                    },
                    "notes": {"type": "string"},
                    "files_changed": {"type": "array", "items": {"type": "string"}},
                    "blockers": {"type": "array", "items": {"type": "string"}},
                    "success_criteria": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["root_path", "phase_id"],
            },
        ),
        Tool(
            name="complete_phase",
            description="Mark a phase as complete with validation evidence and next recommendation.",
            inputSchema={
                "type": "object",
                "properties": {
                    "root_path": {"type": "string", "description": "Project root directory"},
                    "phase_id": {"type": "string", "description": "Phase ID to complete"},
                    "validation_ids": {"type": "array", "items": {"type": "string"}},
                    "files_changed": {"type": "array", "items": {"type": "string"}},
                    "known_limitations": {"type": "array", "items": {"type": "string"}},
                    "next_recommendation": {"type": "string"},
                    "commit_hash": {"type": "string"},
                },
                "required": ["root_path", "phase_id", "files_changed"],
            },
        ),
        Tool(
            name="record_decision",
            description="Record a confirmed technical or domain decision.",
            inputSchema={
                "type": "object",
                "properties": {
                    "root_path": {"type": "string", "description": "Project root directory"},
                    "title": {"type": "string", "description": "Decision title"},
                    "decision": {"type": "string", "description": "The decision made"},
                    "rationale": {"type": "string", "description": "Why this decision was made"},
                    "consequences": {"type": "array", "items": {"type": "string"}},
                    "source": {"type": "string", "description": "Who/what confirmed this decision"},
                    "status": {
                        "type": "string",
                        "enum": ["proposed", "accepted", "rejected", "superseded"],
                        "default": "proposed",
                    },
                    "related_files": {"type": "array", "items": {"type": "string"}},
                    "related_phase_id": {"type": "string"},
                },
                "required": ["root_path", "title", "decision"],
            },
        ),
        Tool(
            name="record_assumption",
            description="Record an assumption that needs validation.",
            inputSchema={
                "type": "object",
                "properties": {
                    "root_path": {"type": "string", "description": "Project root directory"},
                    "assumption": {"type": "string", "description": "The assumption being made"},
                    "risk": {"type": "string", "description": "Risk if assumption is wrong"},
                    "status": {
                        "type": "string",
                        "enum": ["unconfirmed", "confirmed", "known_simplification", "resolved", "invalidated"],
                        "default": "unconfirmed",
                    },
                    "validation_status": {"type": "string"},
                    "resolution_plan": {"type": "string"},
                    "related_files": {"type": "array", "items": {"type": "string"}},
                    "related_phase_id": {"type": "string"},
                },
                "required": ["root_path", "assumption"],
            },
        ),
        Tool(
            name="record_validation",
            description="Manually record a validation result (use run_validation_command for automatic capture).",
            inputSchema={
                "type": "object",
                "properties": {
                    "root_path": {"type": "string", "description": "Project root directory"},
                    "phase_id": {"type": "string"},
                    "command": {"type": "string"},
                    "status": {
                        "type": "string",
                        "enum": ["pass", "fail", "warning", "not_run"],
                        "default": "not_run",
                    },
                    "exit_code": {"type": "integer"},
                    "duration_seconds": {"type": "number"},
                    "passed": {"type": "integer"},
                    "failed": {"type": "integer"},
                    "output_summary": {"type": "string"},
                    "raw_output_path": {"type": "string"},
                },
                "required": ["root_path"],
            },
        ),
        Tool(
            name="run_validation_command",
            description="Run a validation command (e.g., pytest, npm test) and capture the result.",
            inputSchema={
                "type": "object",
                "properties": {
                    "root_path": {"type": "string", "description": "Project root directory for ForgeLoop storage"},
                    "command": {"type": "string", "description": "Command to run (must be in allowed list)"},
                    "working_directory": {"type": "string", "description": "Working directory for command"},
                    "phase_id": {"type": "string"},
                    "required_pass": {"type": "boolean", "default": False},
                    "timeout_seconds": {"type": "integer", "default": 300, "minimum": 1, "maximum": 3600},
                    "output_capture": {"type": "string", "enum": ["summary", "full"], "default": "summary"},
                },
                "required": ["root_path", "command", "working_directory"],
            },
        ),
        Tool(
            name="audit_source_of_truth",
            description="Audit project files to classify source-of-truth status and identify drift.",
            inputSchema={
                "type": "object",
                "properties": {
                    "root_path": {"type": "string", "description": "Project root directory"},
                    "canonical_patterns": {"type": "array", "items": {"type": "string"}},
                    "generated_patterns": {"type": "array", "items": {"type": "string"}},
                    "migration_patterns": {"type": "array", "items": {"type": "string"}},
                    "docs_patterns": {"type": "array", "items": {"type": "string"}},
                    "script_patterns": {"type": "array", "items": {"type": "string"}},
                    "test_patterns": {"type": "array", "items": {"type": "string"}},
                    "compare_docs_to_code": {"type": "boolean", "default": False},
                },
                "required": ["root_path"],
            },
        ),
        Tool(
            name="generate_report",
            description="Generate a Markdown report (project status, phase completion, validation, etc.).",
            inputSchema={
                "type": "object",
                "properties": {
                    "root_path": {"type": "string", "description": "Project root directory"},
                    "report_type": {
                        "type": "string",
                        "enum": [
                            "project_status", "phase_completion", "validation", "source_of_truth",
                            "gap_analysis", "decision_summary", "assumption_summary", "next_phase_plan",
                        ],
                    },
                    "output_path": {"type": "string"},
                    "phase_id": {"type": "string"},
                    "include_decisions": {"type": "boolean", "default": True},
                    "include_assumptions": {"type": "boolean", "default": True},
                    "include_validations": {"type": "boolean", "default": True},
                },
                "required": ["root_path", "report_type"],
            },
        ),
        Tool(
            name="generate_agent_prompt",
            description="Generate a bounded prompt for a coding agent based on current project state.",
            inputSchema={
                "type": "object",
                "properties": {
                    "root_path": {"type": "string", "description": "Project root directory"},
                    "prompt_type": {
                        "type": "string",
                        "enum": [
                            "audit", "implementation", "validation", "correction",
                            "refactor", "documentation", "commit_summary", "next_phase",
                            "progress",
                        ],
                    },
                    "phase_id": {"type": "string"},
                    "context_level": {"type": "string", "enum": ["brief", "standard", "full"], "default": "standard"},
                    "include_decisions": {"type": "boolean", "default": True},
                    "include_assumptions": {"type": "boolean", "default": True},
                    "include_validation_requirements": {"type": "boolean", "default": True},
                    "include_file_context": {"type": "boolean", "default": True},
                },
                "required": ["root_path", "prompt_type"],
            },
        ),
        Tool(
            name="recommend_next_action",
            description="Analyze current state and recommend the next safe action.",
            inputSchema={
                "type": "object",
                "properties": {
                    "root_path": {"type": "string", "description": "Project root directory"},
                    "phase_id": {"type": "string"},
                    "include_git_state": {"type": "boolean", "default": True},
                    "include_validation_state": {"type": "boolean", "default": True},
                    "include_assumptions": {"type": "boolean", "default": True},
                },
                "required": ["root_path"],
            },
        ),
        Tool(
            name="list_phases",
            description="List all phases with optional status filtering.",
            inputSchema={
                "type": "object",
                "properties": {
                    "root_path": {"type": "string", "description": "Project root directory"},
                    "status": {
                        "type": "string",
                        "enum": ["planned", "active", "blocked", "validating", "complete", "abandoned", "superseded"],
                        "description": "Filter by status",
                    },
                    "limit": {"type": "integer", "default": 50, "description": "Maximum phases to return"},
                },
                "required": ["root_path"],
            },
        ),
        Tool(
            name="list_decisions",
            description="List all decisions with optional status filtering.",
            inputSchema={
                "type": "object",
                "properties": {
                    "root_path": {"type": "string", "description": "Project root directory"},
                    "status": {
                        "type": "string",
                        "enum": ["proposed", "accepted", "rejected", "superseded"],
                        "description": "Filter by status",
                    },
                    "phase_id": {"type": "string", "description": "Filter by related phase"},
                    "limit": {"type": "integer", "default": 50, "description": "Maximum decisions to return"},
                },
                "required": ["root_path"],
            },
        ),
        Tool(
            name="list_assumptions",
            description="List all assumptions with optional status filtering.",
            inputSchema={
                "type": "object",
                "properties": {
                    "root_path": {"type": "string", "description": "Project root directory"},
                    "status": {
                        "type": "string",
                        "enum": ["unconfirmed", "confirmed", "known_simplification", "resolved", "invalidated"],
                        "description": "Filter by status",
                    },
                    "phase_id": {"type": "string", "description": "Filter by related phase"},
                    "limit": {"type": "integer", "default": 50, "description": "Maximum assumptions to return"},
                },
                "required": ["root_path"],
            },
        ),
        Tool(
            name="list_validations",
            description="List all validations with optional filtering.",
            inputSchema={
                "type": "object",
                "properties": {
                    "root_path": {"type": "string", "description": "Project root directory"},
                    "status": {
                        "type": "string",
                        "enum": ["pass", "fail", "warning", "not_run"],
                        "description": "Filter by status",
                    },
                    "phase_id": {"type": "string", "description": "Filter by phase"},
                    "limit": {"type": "integer", "default": 50, "description": "Maximum validations to return"},
                },
                "required": ["root_path"],
            },
        ),
        Tool(
            name="get_project",
            description="Get project metadata and configuration.",
            inputSchema={
                "type": "object",
                "properties": {
                    "root_path": {"type": "string", "description": "Project root directory"},
                },
                "required": ["root_path"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle tool calls."""
    try:
        result = await _handle_tool(name, arguments)
        return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]
    except Exception as e:
        error_result = {"error": str(e), "tool": name}
        return [TextContent(type="text", text=json.dumps(error_result, indent=2))]


def _detect_validation_commands(root_path: Path) -> list[str]:
    """Auto-detect appropriate validation commands based on project files."""
    commands = []

    # Python
    if (root_path / "pyproject.toml").exists() or (root_path / "setup.py").exists():
        if (root_path / "tests").exists() or list(root_path.glob("test_*.py")):
            commands.append("pytest")
        if (root_path / "pyproject.toml").exists():
            commands.append("ruff check .")

    # JavaScript/TypeScript
    if (root_path / "package.json").exists():
        import json
        try:
            pkg = json.loads((root_path / "package.json").read_text())
            scripts = pkg.get("scripts", {})
            if "test" in scripts:
                commands.append("npm test")
            if "lint" in scripts:
                commands.append("npm run lint")
            if "build" in scripts:
                commands.append("npm run build")
        except (json.JSONDecodeError, OSError):
            commands.append("npm test")

    # Rust
    if (root_path / "Cargo.toml").exists():
        commands.append("cargo test")
        commands.append("cargo clippy")

    # Go
    if (root_path / "go.mod").exists():
        commands.append("go test ./...")

    # Default fallback
    if not commands:
        commands = ["echo 'No validation commands configured'"]

    return commands


async def _handle_tool(name: str, args: dict[str, Any]) -> dict[str, Any]:
    """Route tool calls to handlers."""
    root_path = args.get("root_path")

    if name == "init_project":
        storage = get_storage(root_path)
        if storage.is_initialized:
            project = storage.get_project()
            return {
                "success": True,
                "message": "Project already initialized",
                "project": project.model_dump(mode="json") if project else None,
            }

        # Auto-detect validation commands if not provided
        validation_cmds = args.get("validation_commands")
        if not validation_cmds:
            validation_cmds = _detect_validation_commands(Path(root_path))

        project = storage.init_project(
            name=args.get("name") or Path(root_path).name,
            description=args.get("description"),
        )
        # Update with validation commands
        project.default_validation_commands = validation_cmds
        storage.save_project(project)

        return {
            "success": True,
            "message": "Project initialized",
            "project": project.model_dump(mode="json"),
            "detected_validation_commands": validation_cmds,
        }

    elif name == "scan_project_state":
        snapshot = scan_project(
            root_path=root_path,
            include_git=args.get("include_git", True),
            include_file_tree=args.get("include_file_tree", True),
            include_recent_changes=args.get("include_recent_changes", True),
            include_package_files=args.get("include_package_files", True),
            include_test_files=args.get("include_test_files", True),
            max_depth=args.get("max_depth", 5),
        )
        # Initialize storage if project has .forgeloop
        storage = get_storage(root_path)
        return snapshot.model_dump(mode="json")

    elif name == "create_phase":
        storage = get_storage(root_path)
        if not storage.is_initialized:
            # Auto-initialize project
            storage.init_project(name=Path(root_path).name)

        phase = storage.create_phase(
            name=args["name"],
            objective=args["objective"],
            scope=args.get("scope", []),
            success_criteria=args.get("success_criteria", []),
            blockers=args.get("blockers", []),
            risks=args.get("risks", []),
        )
        return {"success": True, "phase": phase.model_dump(mode="json")}

    elif name == "update_phase":
        storage = get_storage(root_path)
        updates = {}
        if "status" in args:
            updates["status"] = PhaseStatus(args["status"])
        for key in ["notes", "files_changed", "blockers", "success_criteria"]:
            if key in args:
                updates[key] = args[key]

        phase = storage.update_phase(args["phase_id"], **updates)
        if phase:
            return {"success": True, "phase": phase.model_dump(mode="json")}
        return {"success": False, "error": f"Phase not found: {args['phase_id']}"}

    elif name == "complete_phase":
        storage = get_storage(root_path)
        phase = storage.get_phase(args["phase_id"])
        if not phase:
            return {"success": False, "error": f"Phase not found: {args['phase_id']}"}

        # Update phase to complete
        updated = storage.update_phase(
            args["phase_id"],
            status=PhaseStatus.COMPLETE,
            files_changed=args.get("files_changed", []),
            validation_ids=args.get("validation_ids", []),
            completed_at=utc_now(),
            commit_hash=args.get("commit_hash"),
        )

        return {
            "success": True,
            "phase_completion_report": {
                "phase_id": phase.id,
                "phase_name": phase.name,
                "status": "complete",
                "files_changed": args.get("files_changed", []),
                "validation_ids": args.get("validation_ids", []),
                "known_limitations": args.get("known_limitations", []),
                "next_recommendation": args.get("next_recommendation"),
                "commit_hash": args.get("commit_hash"),
            },
        }

    elif name == "record_decision":
        storage = get_storage(root_path)
        if not storage.is_initialized:
            storage.init_project(name=Path(root_path).name)

        decision = storage.create_decision(
            title=args["title"],
            decision=args["decision"],
            status=args.get("status", "proposed"),
            rationale=args.get("rationale"),
            consequences=args.get("consequences", []),
            source=args.get("source"),
            related_files=args.get("related_files", []),
            related_phase_id=args.get("related_phase_id"),
        )
        return {"success": True, "decision": decision.model_dump(mode="json")}

    elif name == "record_assumption":
        storage = get_storage(root_path)
        if not storage.is_initialized:
            storage.init_project(name=Path(root_path).name)

        assumption = storage.create_assumption(
            assumption=args["assumption"],
            status=args.get("status", "unconfirmed"),
            risk=args.get("risk"),
            validation_status=args.get("validation_status"),
            resolution_plan=args.get("resolution_plan"),
            related_files=args.get("related_files", []),
            related_phase_id=args.get("related_phase_id"),
        )
        return {"success": True, "assumption": assumption.model_dump(mode="json")}

    elif name == "record_validation":
        storage = get_storage(root_path)
        if not storage.is_initialized:
            storage.init_project(name=Path(root_path).name)

        validation = storage.create_validation(
            phase_id=args.get("phase_id"),
            command=args.get("command"),
            status=args.get("status", "not_run"),
            exit_code=args.get("exit_code"),
            duration_seconds=args.get("duration_seconds"),
            passed=args.get("passed"),
            failed=args.get("failed"),
            output_summary=args.get("output_summary"),
            raw_output_path=args.get("raw_output_path"),
        )
        return {"success": True, "validation": validation.model_dump(mode="json")}

    elif name == "run_validation_command":
        storage = get_storage(root_path)
        if not storage.is_initialized:
            storage.init_project(name=Path(root_path).name)

        try:
            validation = run_validation_command(
                storage=storage,
                command=args["command"],
                working_directory=args["working_directory"],
                phase_id=args.get("phase_id"),
                required_pass=args.get("required_pass", False),
                timeout_seconds=args.get("timeout_seconds", 300),
                output_capture=OutputCapture(args.get("output_capture", "summary")),
            )
            return {"success": True, "validation": validation.model_dump(mode="json")}
        except ValidationError as e:
            return {"success": False, "error": str(e)}

    elif name == "audit_source_of_truth":
        audit = audit_source_of_truth(
            root_path=root_path,
            canonical_patterns=args.get("canonical_patterns"),
            generated_patterns=args.get("generated_patterns"),
            migration_patterns=args.get("migration_patterns"),
            docs_patterns=args.get("docs_patterns"),
            script_patterns=args.get("script_patterns"),
            test_patterns=args.get("test_patterns"),
            compare_docs_to_code=args.get("compare_docs_to_code", False),
        )
        return audit.model_dump(mode="json")

    elif name == "generate_report":
        storage = get_storage(root_path)
        if not storage.is_initialized:
            storage.init_project(name=Path(root_path).name)

        report = generate_report(
            storage=storage,
            report_type=ReportType(args["report_type"]),
            output_path=args.get("output_path"),
            phase_id=args.get("phase_id"),
            include_decisions=args.get("include_decisions", True),
            include_assumptions=args.get("include_assumptions", True),
            include_validations=args.get("include_validations", True),
        )
        return {"success": True, "report": report.model_dump(mode="json")}

    elif name == "generate_agent_prompt":
        storage = get_storage(root_path)
        if not storage.is_initialized:
            storage.init_project(name=Path(root_path).name)

        prompt = generate_agent_prompt(
            storage=storage,
            prompt_type=PromptType(args["prompt_type"]),
            phase_id=args.get("phase_id"),
            context_level=ContextLevel(args.get("context_level", "standard")),
            include_decisions=args.get("include_decisions", True),
            include_assumptions=args.get("include_assumptions", True),
            include_validation_requirements=args.get("include_validation_requirements", True),
            include_file_context=args.get("include_file_context", True),
        )
        return {"success": True, "prompt": prompt.model_dump(mode="json")}

    elif name == "recommend_next_action":
        storage = get_storage(root_path)
        if not storage.is_initialized:
            return {
                "recommendation": "perform_source_audit",
                "confidence": "high",
                "rationale": "ForgeLoop not initialized for this project",
                "required_before_next": ["Run scan_project_state", "Create first phase"],
                "risks": [],
            }

        recommendation = recommend_next_action(
            storage=storage,
            phase_id=args.get("phase_id"),
            include_git_state=args.get("include_git_state", True),
            include_validation_state=args.get("include_validation_state", True),
            include_assumptions=args.get("include_assumptions", True),
        )
        return recommendation.model_dump(mode="json")

    elif name == "list_phases":
        storage = get_storage(root_path)
        if not storage.is_initialized:
            return {"success": False, "error": "Project not initialized", "phases": []}

        phases = storage.get_phases()
        status_filter = args.get("status")
        if status_filter:
            phases = [p for p in phases if p.status.value == status_filter]

        limit = args.get("limit", 50)
        phases = phases[:limit]

        return {
            "success": True,
            "count": len(phases),
            "phases": [p.model_dump(mode="json") for p in phases],
        }

    elif name == "list_decisions":
        storage = get_storage(root_path)
        if not storage.is_initialized:
            return {"success": False, "error": "Project not initialized", "decisions": []}

        decisions = storage.get_decisions()
        status_filter = args.get("status")
        phase_filter = args.get("phase_id")

        if status_filter:
            decisions = [d for d in decisions if d.status.value == status_filter]
        if phase_filter:
            decisions = [d for d in decisions if d.related_phase_id == phase_filter]

        limit = args.get("limit", 50)
        decisions = decisions[:limit]

        return {
            "success": True,
            "count": len(decisions),
            "decisions": [d.model_dump(mode="json") for d in decisions],
        }

    elif name == "list_assumptions":
        storage = get_storage(root_path)
        if not storage.is_initialized:
            return {"success": False, "error": "Project not initialized", "assumptions": []}

        assumptions = storage.get_assumptions()
        status_filter = args.get("status")
        phase_filter = args.get("phase_id")

        if status_filter:
            assumptions = [a for a in assumptions if a.status.value == status_filter]
        if phase_filter:
            assumptions = [a for a in assumptions if a.related_phase_id == phase_filter]

        limit = args.get("limit", 50)
        assumptions = assumptions[:limit]

        return {
            "success": True,
            "count": len(assumptions),
            "assumptions": [a.model_dump(mode="json") for a in assumptions],
        }

    elif name == "list_validations":
        storage = get_storage(root_path)
        if not storage.is_initialized:
            return {"success": False, "error": "Project not initialized", "validations": []}

        validations = storage.get_validations()
        status_filter = args.get("status")
        phase_filter = args.get("phase_id")

        if status_filter:
            validations = [v for v in validations if v.status.value == status_filter]
        if phase_filter:
            validations = [v for v in validations if v.phase_id == phase_filter]

        limit = args.get("limit", 50)
        validations = validations[:limit]

        return {
            "success": True,
            "count": len(validations),
            "validations": [v.model_dump(mode="json") for v in validations],
        }

    elif name == "get_project":
        storage = get_storage(root_path)
        if not storage.is_initialized:
            return {"success": False, "error": "Project not initialized", "project": None}

        project = storage.get_project()
        if not project:
            return {"success": False, "error": "Project not found", "project": None}

        # Add summary stats
        phases = storage.get_phases()
        decisions = storage.get_decisions()
        assumptions = storage.get_assumptions()
        validations = storage.get_validations()

        return {
            "success": True,
            "project": project.model_dump(mode="json"),
            "stats": {
                "phases": len(phases),
                "active_phase": next((p.name for p in phases if p.status.value == "active"), None),
                "decisions": len(decisions),
                "accepted_decisions": len([d for d in decisions if d.status.value == "accepted"]),
                "assumptions": len(assumptions),
                "unconfirmed_assumptions": len([a for a in assumptions if a.status.value == "unconfirmed"]),
                "validations": len(validations),
                "passed_validations": len([v for v in validations if v.status.value == "pass"]),
                "failed_validations": len([v for v in validations if v.status.value == "fail"]),
            },
        }

    else:
        return {"error": f"Unknown tool: {name}"}


# =============================================================================
# Entry Point
# =============================================================================

def main():
    """Run the ForgeLoop MCP server."""
    import asyncio

    async def run():
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, server.create_initialization_options())

    asyncio.run(run())


if __name__ == "__main__":
    main()
