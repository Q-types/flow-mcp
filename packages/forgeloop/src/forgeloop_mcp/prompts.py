"""Agent prompt generation for ForgeLoop MCP."""

from datetime import datetime, timezone

from .models import AgentPrompt, ContextLevel, PromptType
from .storage import ForgeLoopStorage


def generate_agent_prompt(
    storage: ForgeLoopStorage,
    prompt_type: PromptType,
    phase_id: str | None = None,
    context_level: ContextLevel = ContextLevel.STANDARD,
    include_decisions: bool = True,
    include_assumptions: bool = True,
    include_validation_requirements: bool = True,
    include_file_context: bool = True,
) -> AgentPrompt:
    """Generate a bounded prompt for a coding agent.

    Args:
        storage: ForgeLoop storage instance.
        prompt_type: Type of prompt to generate.
        phase_id: Phase ID for context.
        context_level: Detail level (brief, standard, full).
        include_decisions: Include relevant decisions.
        include_assumptions: Include relevant assumptions.
        include_validation_requirements: Include validation commands.
        include_file_context: Include file context hints.

    Returns:
        AgentPrompt with generated prompt text.
    """
    project = storage.get_project()
    project_name = project.name if project else "Unknown Project"

    # Get phase context
    if phase_id:
        phase = storage.get_phase(phase_id)
    else:
        phase = storage.get_active_phase()

    # Generate prompt based on type
    if prompt_type == PromptType.AUDIT:
        prompt_text = _generate_audit_prompt(storage, project_name, context_level)
    elif prompt_type == PromptType.IMPLEMENTATION:
        prompt_text = _generate_implementation_prompt(
            storage, project_name, phase, context_level,
            include_decisions, include_assumptions, include_validation_requirements
        )
    elif prompt_type == PromptType.VALIDATION:
        prompt_text = _generate_validation_prompt(storage, project_name, phase)
    elif prompt_type == PromptType.CORRECTION:
        prompt_text = _generate_correction_prompt(storage, project_name, phase)
    elif prompt_type == PromptType.REFACTOR:
        prompt_text = _generate_refactor_prompt(storage, project_name, phase)
    elif prompt_type == PromptType.DOCUMENTATION:
        prompt_text = _generate_documentation_prompt(storage, project_name, phase)
    elif prompt_type == PromptType.COMMIT_SUMMARY:
        prompt_text = _generate_commit_summary_prompt(storage, phase)
    elif prompt_type == PromptType.NEXT_PHASE:
        prompt_text = _generate_next_phase_prompt(storage, project_name)
    elif prompt_type == PromptType.PROGRESS:
        prompt_text = _generate_progress_prompt(storage, project_name, phase)
    else:
        prompt_text = f"Prompt type `{prompt_type}` is not yet implemented."

    # Generate prompt ID and save
    prompt_id = f"PROMPT-{int(datetime.now(timezone.utc).timestamp() * 1000) % 100000:05d}"
    saved_path = storage.save_prompt(prompt_id, prompt_text)

    return AgentPrompt(
        prompt_id=prompt_id,
        prompt_type=prompt_type,
        prompt_text=prompt_text,
        output_path=str(saved_path.relative_to(storage.root_path)),
        phase_id=phase.id if phase else None,
    )


def _generate_audit_prompt(
    storage: ForgeLoopStorage,
    project_name: str,
    context_level: ContextLevel,
) -> str:
    """Generate audit prompt."""
    return f"""# Audit Task: {project_name}

You are performing a codebase audit. Your goal is to understand the current state of the project.

## Instructions

1. **Scan the project structure** - Identify source files, tests, config, and docs
2. **Check git state** - Note any uncommitted changes
3. **Identify source-of-truth files** - What files are canonical vs generated?
4. **Flag concerns** - Note any stale docs, missing tests, or unclear ownership

## Output Requirements

Provide a structured report with:
- Project structure overview
- Key source files identified
- Test coverage assessment
- Documentation status
- Potential issues or risks

## Constraints

- Do NOT modify any files during audit
- Do NOT assume - investigate and report facts
- Flag uncertainties as "NEEDS CLARIFICATION"
"""


def _generate_implementation_prompt(
    storage: ForgeLoopStorage,
    project_name: str,
    phase,
    context_level: ContextLevel,
    include_decisions: bool,
    include_assumptions: bool,
    include_validation_requirements: bool,
) -> str:
    """Generate implementation prompt."""
    lines = [
        f"# Implementation Task: {project_name}",
        "",
    ]

    if phase:
        lines.extend([
            f"## Phase: {phase.name}",
            "",
            f"**Objective:** {phase.objective}",
            "",
        ])

        if phase.scope:
            lines.append("**Scope:**")
            for item in phase.scope:
                lines.append(f"- {item}")
            lines.append("")

        if phase.success_criteria:
            lines.append("**Success Criteria:**")
            for criterion in phase.success_criteria:
                lines.append(f"- [ ] {criterion}")
            lines.append("")

    lines.extend([
        "## Instructions",
        "",
        "1. Implement the changes required to meet the success criteria",
        "2. Make minimal, bounded changes - avoid scope creep",
        "3. Update only the files necessary for this phase",
        "4. Run validation commands after implementation",
        "",
    ])

    # Include relevant decisions
    if include_decisions and phase:
        decisions = storage.get_decisions()
        related = [d for d in decisions if d.related_phase_id == phase.id and d.status.value == "accepted"]
        if related:
            lines.append("## Relevant Decisions")
            lines.append("")
            for dec in related:
                lines.append(f"- **{dec.title}:** {dec.decision}")
            lines.append("")

    # Include assumptions
    if include_assumptions and phase:
        assumptions = storage.get_assumptions()
        related = [a for a in assumptions if a.related_phase_id == phase.id]
        if related:
            lines.append("## Active Assumptions")
            lines.append("")
            for asm in related:
                lines.append(f"- {asm.assumption}")
                if asm.risk:
                    lines.append(f"  - Risk: {asm.risk}")
            lines.append("")

    # Include validation requirements
    if include_validation_requirements:
        project = storage.get_project()
        if project and project.default_validation_commands:
            lines.append("## Validation Commands")
            lines.append("")
            for cmd in project.default_validation_commands:
                lines.append(f"- `{cmd}`")
            lines.append("")

    lines.extend([
        "## Output Requirements",
        "",
        "After implementation, report:",
        "- Files changed and why",
        "- Validation results",
        "- Any new assumptions made",
        "- Known limitations",
        "- Recommended next step",
        "",
        "## Constraints",
        "",
        "- Do NOT refactor unrelated code",
        "- Do NOT add features beyond the scope",
        "- Do NOT claim success without validation",
        "- Keep changes minimal and reversible",
    ])

    return "\n".join(lines)


def _generate_validation_prompt(
    storage: ForgeLoopStorage,
    project_name: str,
    phase,
) -> str:
    """Generate validation prompt."""
    lines = [
        f"# Validation Task: {project_name}",
        "",
    ]

    if phase:
        lines.extend([
            f"## Phase: {phase.name}",
            "",
        ])

    project = storage.get_project()
    commands = project.default_validation_commands if project else []

    lines.extend([
        "## Instructions",
        "",
        "Run the following validation commands and report results:",
        "",
    ])

    if commands:
        for cmd in commands:
            lines.append(f"1. `{cmd}`")
    else:
        lines.extend([
            "1. Run tests (e.g., `pytest`, `npm test`)",
            "2. Run linting (e.g., `ruff check .`, `eslint`)",
            "3. Run type checking (e.g., `mypy`, `tsc`)",
        ])

    lines.extend([
        "",
        "## Output Requirements",
        "",
        "For each command, report:",
        "- Command run",
        "- Exit code",
        "- Pass/fail count (if applicable)",
        "- Summary of any failures",
        "",
        "## Constraints",
        "",
        "- Do NOT modify code to pass tests",
        "- Report failures accurately",
        "- Note any skipped or incomplete validations",
    ])

    return "\n".join(lines)


def _generate_correction_prompt(
    storage: ForgeLoopStorage,
    project_name: str,
    phase,
) -> str:
    """Generate correction prompt."""
    lines = [
        f"# Correction Task: {project_name}",
        "",
    ]

    # Find recent failed validations
    validations = storage.get_validations()
    failed = [v for v in validations if v.status.value == "fail"][-3:]

    if failed:
        lines.extend([
            "## Failed Validations to Address",
            "",
        ])
        for val in failed:
            lines.extend([
                f"### {val.command}",
                "",
                f"- Exit code: {val.exit_code}",
                f"- Output: {val.output_summary[:200] if val.output_summary else 'See log'}...",
                "",
            ])

    lines.extend([
        "## Instructions",
        "",
        "1. Analyze the failure(s) above",
        "2. Classify the failure: code bug, test issue, config problem, or environment",
        "3. Apply the minimal fix required",
        "4. Re-run the failed validation",
        "5. Verify surrounding tests still pass",
        "",
        "## Output Requirements",
        "",
        "Report:",
        "- Root cause identified",
        "- Files changed",
        "- Fix applied",
        "- Validation result after fix",
        "",
        "## Constraints",
        "",
        "- Fix ONLY the identified issue",
        "- Do NOT refactor surrounding code",
        "- Do NOT skip or disable tests",
    ])

    return "\n".join(lines)


def _generate_refactor_prompt(
    storage: ForgeLoopStorage,
    project_name: str,
    phase,
) -> str:
    """Generate refactor prompt."""
    return f"""# Refactor Task: {project_name}

## Instructions

1. **Before refactoring:**
   - Run all tests and save results
   - Note current behavior as baseline

2. **During refactoring:**
   - Make behavior-preserving changes only
   - Keep changes small and reviewable
   - Maintain the same public API

3. **After refactoring:**
   - Re-run all tests
   - Verify behavior is unchanged
   - Document any interface changes

## Output Requirements

Report:
- Files changed
- Refactoring approach used
- Tests passed before/after
- Any unexpected behavior changes

## Constraints

- Do NOT change behavior
- Do NOT add new features
- Do NOT remove tests
- Commit incrementally if possible
"""


def _generate_documentation_prompt(
    storage: ForgeLoopStorage,
    project_name: str,
    phase,
) -> str:
    """Generate documentation prompt."""
    return f"""# Documentation Task: {project_name}

## Instructions

1. Review the current codebase state
2. Identify documentation gaps:
   - Missing README sections
   - Outdated API docs
   - Undocumented functions/modules
3. Update documentation to reflect current behavior

## Documentation Checklist

- [ ] README.md is current
- [ ] Installation instructions work
- [ ] Usage examples are correct
- [ ] API reference matches code
- [ ] CHANGELOG is updated (if applicable)

## Output Requirements

Report:
- Documentation files updated
- Gaps identified and addressed
- Any remaining documentation debt

## Constraints

- Document what IS, not what SHOULD BE
- Do NOT change code while documenting
- Flag inconsistencies rather than assuming
"""


def _generate_commit_summary_prompt(
    storage: ForgeLoopStorage,
    phase,
) -> str:
    """Generate commit summary prompt."""
    lines = [
        "# Commit Summary Task",
        "",
        "Generate a clear commit message for the current changes.",
        "",
        "## Instructions",
        "",
        "1. Review all changed files",
        "2. Identify the main purpose of the changes",
        "3. Write a commit message following this format:",
        "",
        "```",
        "<type>(<scope>): <subject>",
        "",
        "<body>",
        "",
        "<footer>",
        "```",
        "",
        "## Types",
        "",
        "- feat: New feature",
        "- fix: Bug fix",
        "- refactor: Code change that neither fixes nor adds",
        "- docs: Documentation only",
        "- test: Adding tests",
        "- chore: Maintenance",
        "",
    ]

    if phase:
        lines.extend([
            "## Context",
            "",
            f"- Phase: {phase.name}",
            f"- Objective: {phase.objective}",
            "",
        ])

    lines.extend([
        "## Output",
        "",
        "Provide the commit message ready to use.",
    ])

    return "\n".join(lines)


def _generate_next_phase_prompt(
    storage: ForgeLoopStorage,
    project_name: str,
) -> str:
    """Generate next phase planning prompt."""
    phases = storage.get_phases()
    completed = [p for p in phases if p.status.value == "complete"]
    active = storage.get_active_phase()

    lines = [
        f"# Next Phase Planning: {project_name}",
        "",
        "## Current State",
        "",
        f"- Completed phases: {len(completed)}",
        f"- Active phase: {active.name if active else 'None'}",
        "",
    ]

    if active and active.status.value == "complete":
        lines.extend([
            f"## Just Completed: {active.name}",
            "",
            f"**Objective:** {active.objective}",
            "",
        ])

    lines.extend([
        "## Instructions",
        "",
        "1. Review what was accomplished",
        "2. Identify the logical next step",
        "3. Define the next phase with:",
        "   - Clear name",
        "   - Specific objective",
        "   - Bounded scope",
        "   - Measurable success criteria",
        "",
        "## Output Requirements",
        "",
        "Provide:",
        "- Recommended next phase name",
        "- Objective",
        "- Scope (what to include)",
        "- Exclusions (what NOT to include)",
        "- Success criteria",
        "- Risks or blockers",
    ])

    return "\n".join(lines)


def _generate_progress_prompt(
    storage: ForgeLoopStorage,
    project_name: str,
    phase,
) -> str:
    """Generate progress review prompt."""
    lines = [
        f"# Progress Review: {project_name}",
        "",
    ]

    if phase:
        lines.extend([
            f"## Phase: {phase.name}",
            "",
            f"**Objective:** {phase.objective}",
            f"**Status:** {phase.status.value}",
            "",
        ])

        # Success criteria with completion status
        if phase.success_criteria:
            lines.extend([
                "## Success Criteria Checklist",
                "",
            ])
            validations = storage.get_validations_for_phase(phase.id)
            has_passing = any(v.status.value == "pass" for v in validations)

            for i, criterion in enumerate(phase.success_criteria, 1):
                # Simple heuristic: if validations pass, mark criteria as potentially met
                status = "?" if not has_passing else "~"
                lines.append(f"- [{status}] {criterion}")
            lines.append("")

        # Files changed
        if phase.files_changed:
            lines.extend([
                "## Files Changed",
                "",
            ])
            for f in phase.files_changed:
                lines.append(f"- `{f}`")
            lines.append("")

        # Related validations
        validations = storage.get_validations_for_phase(phase.id)
        if validations:
            passed = sum(1 for v in validations if v.status.value == "pass")
            failed = sum(1 for v in validations if v.status.value == "fail")
            lines.extend([
                "## Validation Status",
                "",
                f"- Passed: {passed}",
                f"- Failed: {failed}",
                "",
            ])
    else:
        lines.extend([
            "## No Active Phase",
            "",
            "No active phase found. Consider:",
            "1. Creating a new phase with `create_phase`",
            "2. Updating an existing phase to 'active' status",
            "",
        ])

    # Unresolved assumptions
    assumptions = storage.get_assumptions()
    unconfirmed = [a for a in assumptions if a.status.value == "unconfirmed"]
    if unconfirmed:
        lines.extend([
            "## Unresolved Assumptions",
            "",
        ])
        for asm in unconfirmed[:5]:
            lines.append(f"- {asm.assumption}")
            if asm.risk:
                lines.append(f"  - Risk: {asm.risk}")
        lines.append("")

    # Recent decisions
    decisions = storage.get_decisions()
    recent_accepted = [d for d in decisions if d.status.value == "accepted"][-3:]
    if recent_accepted:
        lines.extend([
            "## Recent Decisions",
            "",
        ])
        for dec in recent_accepted:
            lines.append(f"- **{dec.title}:** {dec.decision}")
        lines.append("")

    lines.extend([
        "## Instructions",
        "",
        "Review the progress above and:",
        "",
        "1. Assess which success criteria are met/not met",
        "2. Identify any blockers or risks",
        "3. Determine if the phase is ready for completion",
        "4. If not ready, specify what remains",
        "",
        "## Output Requirements",
        "",
        "Provide:",
        "- Progress assessment (% complete estimate)",
        "- Criteria met vs pending",
        "- Blockers identified",
        "- Recommended next action",
    ])

    return "\n".join(lines)
