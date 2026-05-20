"""Report generation for ForgeLoop MCP."""

from datetime import datetime, timezone

from .models import ReportResult, ReportType
from .storage import ForgeLoopStorage


def generate_report(
    storage: ForgeLoopStorage,
    report_type: ReportType,
    output_path: str | None = None,
    phase_id: str | None = None,
    include_decisions: bool = True,
    include_assumptions: bool = True,
    include_validations: bool = True,
) -> ReportResult:
    """Generate a Markdown report.

    Args:
        storage: ForgeLoop storage instance.
        report_type: Type of report to generate.
        output_path: Custom output path (default: .forgeloop/reports/).
        phase_id: Phase ID for phase-specific reports.
        include_decisions: Include decisions in report.
        include_assumptions: Include assumptions in report.
        include_validations: Include validations in report.

    Returns:
        ReportResult with report metadata and content.
    """
    project = storage.get_project()
    project_name = project.name if project else "Unknown Project"

    # Generate report content based on type
    if report_type == ReportType.PROJECT_STATUS:
        content = _generate_project_status(
            storage, project_name, include_decisions, include_assumptions, include_validations
        )
    elif report_type == ReportType.PHASE_COMPLETION:
        content = _generate_phase_completion(storage, phase_id, include_validations)
    elif report_type == ReportType.VALIDATION:
        content = _generate_validation_report(storage, phase_id)
    elif report_type == ReportType.SOURCE_OF_TRUTH:
        content = _generate_source_of_truth_report(storage)
    elif report_type == ReportType.GAP_ANALYSIS:
        content = _generate_gap_analysis(storage)
    elif report_type == ReportType.DECISION_SUMMARY:
        content = _generate_decision_summary(storage)
    elif report_type == ReportType.ASSUMPTION_SUMMARY:
        content = _generate_assumption_summary(storage)
    elif report_type == ReportType.NEXT_PHASE_PLAN:
        content = _generate_next_phase_plan(storage)
    else:
        content = f"# Report Type Not Implemented\n\nReport type `{report_type}` is not yet implemented."

    # Generate report ID and save
    report_id = f"REP-{int(datetime.now(timezone.utc).timestamp() * 1000) % 100000:05d}"

    if output_path:
        from pathlib import Path
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        saved_path = str(path)
    else:
        path = storage.save_report(report_id, content)
        saved_path = str(path.relative_to(storage.root_path))

    # Create summary (first few lines)
    lines = content.strip().split("\n")
    summary = "\n".join(lines[:10])
    if len(lines) > 10:
        summary += "\n..."

    return ReportResult(
        report_id=report_id,
        report_type=report_type,
        output_path=saved_path,
        markdown_summary=summary,
    )


def _generate_project_status(
    storage: ForgeLoopStorage,
    project_name: str,
    include_decisions: bool,
    include_assumptions: bool,
    include_validations: bool,
) -> str:
    """Generate project status report."""
    lines = [
        f"# Project Status: {project_name}",
        "",
        f"**Generated:** {datetime.now(timezone.utc).isoformat()}",
        "",
    ]

    # Phases summary
    phases = storage.get_phases()
    lines.extend([
        "## Phases",
        "",
        f"**Total:** {len(phases)}",
        "",
    ])

    if phases:
        lines.append("| Phase | Status | Objective |")
        lines.append("|-------|--------|-----------|")
        for phase in phases:
            lines.append(f"| {phase.name} | {phase.status.value} | {phase.objective[:50]}... |")
        lines.append("")

    # Active phase details
    active = storage.get_active_phase()
    if active:
        lines.extend([
            "## Active Phase",
            "",
            f"**Name:** {active.name}",
            f"**Objective:** {active.objective}",
            "",
            "**Success Criteria:**",
        ])
        for criterion in active.success_criteria:
            lines.append(f"- [ ] {criterion}")
        lines.append("")

    # Decisions
    if include_decisions:
        decisions = storage.get_decisions()
        accepted = [d for d in decisions if d.status.value == "accepted"]
        lines.extend([
            "## Decisions",
            "",
            f"**Total:** {len(decisions)} ({len(accepted)} accepted)",
            "",
        ])
        if accepted[-5:] if accepted else []:
            lines.append("**Recent Accepted:**")
            for dec in accepted[-5:]:
                lines.append(f"- **{dec.title}:** {dec.decision[:80]}...")
            lines.append("")

    # Assumptions
    if include_assumptions:
        assumptions = storage.get_assumptions()
        unconfirmed = [a for a in assumptions if a.status.value == "unconfirmed"]
        lines.extend([
            "## Assumptions",
            "",
            f"**Total:** {len(assumptions)} ({len(unconfirmed)} unconfirmed)",
            "",
        ])
        if unconfirmed:
            lines.append("**Unconfirmed (requires validation):**")
            for asm in unconfirmed[:5]:
                lines.append(f"- {asm.assumption}")
            lines.append("")

    # Validations
    if include_validations:
        validations = storage.get_validations()
        passed = [v for v in validations if v.status.value == "pass"]
        failed = [v for v in validations if v.status.value == "fail"]

        # Calculate lint stats
        total_errors = sum(v.errors or 0 for v in validations if v.errors is not None)
        total_warnings = sum(v.warnings or 0 for v in validations if v.warnings is not None)

        lines.extend([
            "## Validations",
            "",
            f"**Total:** {len(validations)} ({len(passed)} passed, {len(failed)} failed)",
        ])

        if total_errors > 0 or total_warnings > 0:
            lines.append(f"**Lint Issues:** {total_errors} errors, {total_warnings} warnings")
        lines.append("")

        if failed:
            lines.append("**Recent Failures:**")
            for val in failed[-3:]:
                lines.append(f"- `{val.command}` - {val.output_summary[:50] if val.output_summary else 'No summary'}...")
            lines.append("")

    return "\n".join(lines)


def _generate_phase_completion(
    storage: ForgeLoopStorage,
    phase_id: str | None,
    include_validations: bool,
) -> str:
    """Generate phase completion report."""
    if not phase_id:
        # Use active or most recent phase
        phase = storage.get_active_phase()
        if not phase:
            phases = storage.get_phases()
            phase = phases[-1] if phases else None
    else:
        phase = storage.get_phase(phase_id)

    if not phase:
        return "# Phase Completion Report\n\nNo phase found."

    lines = [
        f"# Phase Completion: {phase.name}",
        "",
        f"**Generated:** {datetime.now(timezone.utc).isoformat()}",
        f"**Status:** {phase.status.value}",
        "",
        "## Objective",
        "",
        phase.objective,
        "",
        "## Success Criteria",
        "",
    ]

    for criterion in phase.success_criteria:
        status = "x" if phase.status.value == "complete" else " "
        lines.append(f"- [{status}] {criterion}")
    lines.append("")

    if phase.files_changed:
        lines.extend([
            "## Files Changed",
            "",
        ])
        for f in phase.files_changed:
            lines.append(f"- `{f}`")
        lines.append("")

    if include_validations:
        validations = storage.get_validations_for_phase(phase.id)
        if validations:
            lines.extend([
                "## Validations",
                "",
            ])
            for val in validations:
                emoji = "✅" if val.status.value == "pass" else "❌"
                lines.append(f"- {emoji} `{val.command}` - {val.status.value}")
            lines.append("")

    if phase.notes:
        lines.extend([
            "## Notes",
            "",
            phase.notes,
            "",
        ])

    return "\n".join(lines)


def _generate_validation_report(storage: ForgeLoopStorage, phase_id: str | None) -> str:
    """Generate validation report."""
    if phase_id:
        validations = storage.get_validations_for_phase(phase_id)
        title = f"Validation Report: Phase {phase_id}"
    else:
        validations = storage.get_validations()
        title = "Validation Report: All Validations"

    lines = [
        f"# {title}",
        "",
        f"**Generated:** {datetime.now(timezone.utc).isoformat()}",
        f"**Total:** {len(validations)}",
        "",
    ]

    passed = [v for v in validations if v.status.value == "pass"]
    failed = [v for v in validations if v.status.value == "fail"]

    lines.extend([
        "## Summary",
        "",
        f"- Passed: {len(passed)}",
        f"- Failed: {len(failed)}",
        f"- Other: {len(validations) - len(passed) - len(failed)}",
        "",
        "## Details",
        "",
    ])

    for val in validations:
        emoji = "✅" if val.status.value == "pass" else "❌" if val.status.value == "fail" else "⚠️"
        lines.extend([
            f"### {emoji} {val.id}",
            "",
            f"- **Command:** `{val.command}`",
            f"- **Status:** {val.status.value}",
            f"- **Exit Code:** {val.exit_code}",
            f"- **Duration:** {val.duration_seconds}s",
        ])
        # Test results
        if val.passed is not None or val.failed is not None:
            lines.append(f"- **Tests:** {val.passed or 0} passed, {val.failed or 0} failed")
        # Lint results
        if val.errors is not None or val.warnings is not None:
            lint_parts = []
            if val.errors is not None:
                lint_parts.append(f"{val.errors} errors")
            if val.warnings is not None:
                lint_parts.append(f"{val.warnings} warnings")
            if val.fixed is not None:
                lint_parts.append(f"{val.fixed} fixed")
            lines.append(f"- **Lint:** {', '.join(lint_parts)}")
        if val.output_summary:
            lines.extend([
                "",
                "**Output:**",
                "```",
                val.output_summary[:500],
                "```",
            ])
        lines.append("")

    return "\n".join(lines)


def _generate_source_of_truth_report(storage: ForgeLoopStorage) -> str:
    """Generate source-of-truth report with audit data."""
    from .source_audit import audit_source_of_truth

    lines = [
        "# Source of Truth Report",
        "",
        f"**Generated:** {datetime.now(timezone.utc).isoformat()}",
        f"**Project Root:** {storage.root_path}",
        "",
    ]

    # Run audit
    try:
        audit = audit_source_of_truth(storage.root_path)
    except Exception as e:
        lines.extend([
            "## Error",
            "",
            f"Failed to run audit: {e}",
            "",
            "Run `audit_source_of_truth` manually to diagnose the issue.",
        ])
        return "\n".join(lines)

    # Classification summary
    classifications: dict[str, int] = {}
    for cf in audit.classified_files:
        key = cf.classification.value
        classifications[key] = classifications.get(key, 0) + 1

    lines.extend([
        "## File Classification Summary",
        "",
        "| Classification | Count |",
        "|----------------|-------|",
    ])
    for cls, count in sorted(classifications.items(), key=lambda x: -x[1]):
        lines.append(f"| {cls} | {count} |")
    lines.extend(["", f"**Total Files:** {len(audit.classified_files)}", ""])

    # Flags (issues detected)
    if audit.flags:
        lines.extend([
            "## Flags",
            "",
        ])
        for flag in audit.flags:
            lines.append(f"- ⚠️ {flag}")
        lines.append("")

    # Recommendations
    if audit.recommendations:
        lines.extend([
            "## Recommendations",
            "",
        ])
        for rec in audit.recommendations:
            lines.append(f"- {rec}")
        lines.append("")

    # Files with warnings
    warned_files = [cf for cf in audit.classified_files if cf.warnings]
    if warned_files:
        lines.extend([
            "## Files Requiring Attention",
            "",
        ])
        for cf in warned_files[:20]:  # Limit to 20
            lines.append(f"### `{cf.path}`")
            lines.append(f"- Classification: {cf.classification.value}")
            for warning in cf.warnings:
                lines.append(f"- ⚠️ {warning}")
            lines.append("")

    # Canonical files list (truncated)
    canonical = [cf for cf in audit.classified_files if cf.classification.value == "canonical"]
    if canonical:
        lines.extend([
            "## Canonical Source Files",
            "",
            f"*Showing first 30 of {len(canonical)} files*",
            "",
        ])
        for cf in canonical[:30]:
            lines.append(f"- `{cf.path}`")
        lines.append("")

    # Unknown files (need review)
    unknown = [cf for cf in audit.classified_files if cf.classification.value == "unknown"]
    if unknown:
        lines.extend([
            "## Files Needing Classification",
            "",
        ])
        for cf in unknown[:20]:
            lines.append(f"- `{cf.path}`")
        if len(unknown) > 20:
            lines.append(f"- ... and {len(unknown) - 20} more")
        lines.append("")

    return "\n".join(lines)


def _generate_gap_analysis(storage: ForgeLoopStorage) -> str:
    """Generate gap analysis report."""
    lines = [
        "# Gap Analysis Report",
        "",
        f"**Generated:** {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Identified Gaps",
        "",
    ]

    # Check for unconfirmed assumptions
    assumptions = storage.get_assumptions()
    unconfirmed = [a for a in assumptions if a.status.value == "unconfirmed"]
    if unconfirmed:
        lines.extend([
            "### Unvalidated Assumptions",
            "",
        ])
        for asm in unconfirmed:
            risk = f" (Risk: {asm.risk})" if asm.risk else ""
            lines.append(f"- {asm.assumption}{risk}")
        lines.append("")

    # Check for failed validations
    validations = storage.get_validations()
    failed = [v for v in validations if v.status.value == "fail"]
    if failed:
        lines.extend([
            "### Failed Validations",
            "",
        ])
        for val in failed:
            lines.append(f"- `{val.command}` - {val.output_summary[:50] if val.output_summary else 'Failed'}...")
        lines.append("")

    # Check for blocked phases
    phases = storage.get_phases()
    blocked = [p for p in phases if p.status.value == "blocked"]
    if blocked:
        lines.extend([
            "### Blocked Phases",
            "",
        ])
        for phase in blocked:
            blockers = ", ".join(phase.blockers) if phase.blockers else "Unknown blockers"
            lines.append(f"- **{phase.name}:** {blockers}")
        lines.append("")

    if not unconfirmed and not failed and not blocked:
        lines.append("No significant gaps identified.")

    return "\n".join(lines)


def _generate_decision_summary(storage: ForgeLoopStorage) -> str:
    """Generate decision summary report."""
    decisions = storage.get_decisions()

    lines = [
        "# Decision Summary",
        "",
        f"**Generated:** {datetime.now(timezone.utc).isoformat()}",
        f"**Total Decisions:** {len(decisions)}",
        "",
    ]

    # Group by status
    by_status: dict[str, list] = {}
    for dec in decisions:
        status = dec.status.value
        if status not in by_status:
            by_status[status] = []
        by_status[status].append(dec)

    for status, decs in by_status.items():
        lines.extend([
            f"## {status.title()} ({len(decs)})",
            "",
        ])
        for dec in decs:
            lines.extend([
                f"### {dec.title}",
                "",
                dec.decision,
                "",
            ])
            if dec.rationale:
                lines.append(f"**Rationale:** {dec.rationale}")
                lines.append("")
            if dec.consequences:
                lines.append("**Consequences:**")
                for cons in dec.consequences:
                    lines.append(f"- {cons}")
                lines.append("")

    return "\n".join(lines)


def _generate_assumption_summary(storage: ForgeLoopStorage) -> str:
    """Generate assumption summary report."""
    assumptions = storage.get_assumptions()

    lines = [
        "# Assumption Summary",
        "",
        f"**Generated:** {datetime.now(timezone.utc).isoformat()}",
        f"**Total Assumptions:** {len(assumptions)}",
        "",
    ]

    # Group by status
    by_status: dict[str, list] = {}
    for asm in assumptions:
        status = asm.status.value
        if status not in by_status:
            by_status[status] = []
        by_status[status].append(asm)

    for status, asms in by_status.items():
        lines.extend([
            f"## {status.replace('_', ' ').title()} ({len(asms)})",
            "",
        ])
        for asm in asms:
            lines.append(f"- **{asm.id}:** {asm.assumption}")
            if asm.risk:
                lines.append(f"  - Risk: {asm.risk}")
            if asm.resolution_plan:
                lines.append(f"  - Resolution: {asm.resolution_plan}")
        lines.append("")

    return "\n".join(lines)


def _generate_next_phase_plan(storage: ForgeLoopStorage) -> str:
    """Generate next phase plan report."""
    phases = storage.get_phases()

    lines = [
        "# Next Phase Plan",
        "",
        f"**Generated:** {datetime.now(timezone.utc).isoformat()}",
        "",
    ]

    # Find current state
    active = storage.get_active_phase()
    completed = [p for p in phases if p.status.value == "complete"]
    planned = [p for p in phases if p.status.value == "planned"]

    lines.extend([
        "## Current State",
        "",
        f"- Completed phases: {len(completed)}",
        f"- Active phase: {active.name if active else 'None'}",
        f"- Planned phases: {len(planned)}",
        "",
    ])

    if active:
        lines.extend([
            "## Active Phase Requirements",
            "",
            f"**{active.name}**",
            "",
            "Remaining success criteria:",
        ])
        for criterion in active.success_criteria:
            lines.append(f"- [ ] {criterion}")
        lines.append("")

    if planned:
        lines.extend([
            "## Next Planned Phases",
            "",
        ])
        for phase in planned[:3]:
            lines.extend([
                f"### {phase.name}",
                "",
                f"**Objective:** {phase.objective}",
                "",
            ])
            if phase.blockers:
                lines.append("**Blockers:**")
                for blocker in phase.blockers:
                    lines.append(f"- {blocker}")
                lines.append("")

    return "\n".join(lines)
