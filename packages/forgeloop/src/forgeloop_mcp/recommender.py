"""Next action recommender for ForgeLoop MCP."""

from .git_utils import get_git_state
from .models import Confidence, NextAction, NextActionRecommendation
from .storage import ForgeLoopStorage


def recommend_next_action(
    storage: ForgeLoopStorage,
    phase_id: str | None = None,
    include_git_state: bool = True,
    include_validation_state: bool = True,
    include_assumptions: bool = True,
) -> NextActionRecommendation:
    """Recommend the next action based on current project state.

    Args:
        storage: ForgeLoop storage instance.
        phase_id: Specific phase to analyze.
        include_git_state: Consider git state in recommendation.
        include_validation_state: Consider validation results.
        include_assumptions: Consider unresolved assumptions.

    Returns:
        NextActionRecommendation with suggested action and rationale.
    """
    # Gather state
    if phase_id:
        phase = storage.get_phase(phase_id)
    else:
        phase = storage.get_active_phase()

    git_state = None
    if include_git_state:
        git_state = get_git_state(storage.root_path)

    validations = []
    if include_validation_state:
        if phase:
            validations = storage.get_validations_for_phase(phase.id)
        else:
            validations = storage.get_validations()

    assumptions = []
    if include_assumptions:
        assumptions = storage.get_assumptions()
        unconfirmed = [a for a in assumptions if a.status.value == "unconfirmed"]
    else:
        unconfirmed = []

    # Decision logic
    recommendation, confidence, rationale, required, risks = _analyze_state(
        phase, git_state, validations, unconfirmed
    )

    return NextActionRecommendation(
        recommendation=recommendation,
        confidence=confidence,
        rationale=rationale,
        required_before_next=required,
        risks=risks,
    )


def _analyze_state(phase, git_state, validations, unconfirmed_assumptions):
    """Analyze state and determine recommendation."""
    required_before_next = []
    risks = []

    # Check for critical blockers first
    if phase and phase.status.value == "blocked":
        blockers = phase.blockers if phase.blockers else ["Unknown blockers"]
        return (
            NextAction.STOP_AND_ASK_USER,
            Confidence.HIGH,
            f"Phase is blocked: {', '.join(blockers)}",
            ["Resolve blockers before proceeding"],
            blockers,
        )

    # Check for failed validations
    failed_validations = [v for v in validations if v.status.value == "fail"]
    if failed_validations:
        return (
            NextAction.RUN_VALIDATION,
            Confidence.HIGH,
            f"Found {len(failed_validations)} failed validation(s)",
            ["Fix failing tests", "Re-run validation"],
            [f"Failed: {v.command}" for v in failed_validations[:3]],
        )

    # Check git state
    if git_state:
        if git_state.dirty:
            # Has uncommitted changes
            if phase and phase.status.value == "complete":
                return (
                    NextAction.COMMIT_CHECKPOINT,
                    Confidence.HIGH,
                    "Phase complete with uncommitted changes",
                    ["Commit current changes", "Tag stable checkpoint"],
                    [],
                )
            elif not validations:
                # Changes but no validation
                return (
                    NextAction.RUN_VALIDATION,
                    Confidence.MEDIUM,
                    "Uncommitted changes without validation",
                    ["Run tests before committing"],
                    ["Untested changes"],
                )

    # Check for unconfirmed assumptions
    high_risk_assumptions = [a for a in unconfirmed_assumptions if a.risk]
    if len(high_risk_assumptions) > 3:
        return (
            NextAction.RESOLVE_ASSUMPTION,
            Confidence.MEDIUM,
            f"Found {len(high_risk_assumptions)} high-risk unconfirmed assumptions",
            ["Review and validate assumptions"],
            [a.assumption[:50] + "..." for a in high_risk_assumptions[:3]],
        )

    # Check phase status
    if phase:
        if phase.status.value == "planned":
            return (
                NextAction.PROCEED_TO_NEXT_PHASE,
                Confidence.HIGH,
                "Phase is planned and ready to start",
                ["Activate the phase", "Begin implementation"],
                [],
            )

        if phase.status.value == "active":
            # Check if we have recent validation
            recent_validations = [v for v in validations if v.status.value == "pass"]
            if not recent_validations:
                return (
                    NextAction.RUN_VALIDATION,
                    Confidence.MEDIUM,
                    "Active phase without recent validation",
                    ["Run validation commands"],
                    [],
                )

            # Check success criteria
            if phase.success_criteria:
                return (
                    NextAction.PROCEED_TO_NEXT_PHASE,
                    Confidence.MEDIUM,
                    "Phase active with passing validations - verify success criteria",
                    ["Review success criteria", "Complete phase if criteria met"],
                    [],
                )

        if phase.status.value == "validating":
            passed = [v for v in validations if v.status.value == "pass"]
            if passed:
                return (
                    NextAction.COMMIT_CHECKPOINT,
                    Confidence.HIGH,
                    "Validation passed - ready for checkpoint",
                    ["Commit changes", "Complete phase"],
                    [],
                )
            else:
                return (
                    NextAction.RUN_VALIDATION,
                    Confidence.HIGH,
                    "Phase in validating status but no passing validations",
                    ["Run validation commands"],
                    [],
                )

        if phase.status.value == "complete":
            # Phase done, check if we should move on
            if git_state and git_state.dirty:
                return (
                    NextAction.COMMIT_CHECKPOINT,
                    Confidence.HIGH,
                    "Phase complete with uncommitted changes",
                    ["Commit final changes"],
                    [],
                )

            planned_phases = [p for p in storage.get_phases() if p.status.value == "planned"]
            if planned_phases:
                return (
                    NextAction.PROCEED_TO_NEXT_PHASE,
                    Confidence.HIGH,
                    f"Phase complete - {len(planned_phases)} planned phase(s) waiting",
                    ["Activate next phase"],
                    [],
                )

    # No phase or general state
    phases = storage.get_phases()
    if not phases:
        return (
            NextAction.PERFORM_SOURCE_AUDIT,
            Confidence.MEDIUM,
            "No phases defined - recommend starting with audit",
            ["Scan project state", "Create first phase"],
            [],
        )

    # Default: check documentation
    return (
        NextAction.UPDATE_DOCS,
        Confidence.LOW,
        "Project in stable state - consider documentation update",
        ["Review documentation", "Update as needed"],
        [],
    )
