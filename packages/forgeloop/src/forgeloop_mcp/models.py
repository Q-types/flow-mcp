"""Pydantic data models for ForgeLoop MCP."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    """Return current UTC timestamp."""
    return datetime.now(timezone.utc)


# =============================================================================
# Enums
# =============================================================================


class PhaseStatus(str, Enum):
    """Phase lifecycle statuses."""
    PLANNED = "planned"
    ACTIVE = "active"
    BLOCKED = "blocked"
    VALIDATING = "validating"
    COMPLETE = "complete"
    ABANDONED = "abandoned"
    SUPERSEDED = "superseded"


class DecisionStatus(str, Enum):
    """Decision confirmation statuses."""
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


class AssumptionStatus(str, Enum):
    """Assumption validation statuses."""
    UNCONFIRMED = "unconfirmed"
    CONFIRMED = "confirmed"
    KNOWN_SIMPLIFICATION = "known_simplification"
    RESOLVED = "resolved"
    INVALIDATED = "invalidated"


class ValidationStatus(str, Enum):
    """Validation result statuses."""
    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"
    NOT_RUN = "not_run"


class FileClassification(str, Enum):
    """Source-of-truth file classifications."""
    CANONICAL = "canonical"
    GENERATED = "generated"
    MIGRATION = "migration"
    AD_HOC = "ad_hoc"
    OBSOLETE = "obsolete"
    UNKNOWN = "unknown"
    TEST = "test"
    DOCUMENTATION = "documentation"


class ReportType(str, Enum):
    """Available report types."""
    PROJECT_STATUS = "project_status"
    PHASE_COMPLETION = "phase_completion"
    VALIDATION = "validation"
    SOURCE_OF_TRUTH = "source_of_truth"
    GAP_ANALYSIS = "gap_analysis"
    DECISION_SUMMARY = "decision_summary"
    ASSUMPTION_SUMMARY = "assumption_summary"
    NEXT_PHASE_PLAN = "next_phase_plan"


class PromptType(str, Enum):
    """Agent prompt types."""
    AUDIT = "audit"
    IMPLEMENTATION = "implementation"
    VALIDATION = "validation"
    CORRECTION = "correction"
    REFACTOR = "refactor"
    DOCUMENTATION = "documentation"
    COMMIT_SUMMARY = "commit_summary"
    NEXT_PHASE = "next_phase"
    PROGRESS = "progress"


class ContextLevel(str, Enum):
    """Prompt context detail levels."""
    BRIEF = "brief"
    STANDARD = "standard"
    FULL = "full"


class OutputCapture(str, Enum):
    """Validation output capture modes."""
    SUMMARY = "summary"
    FULL = "full"


class NextAction(str, Enum):
    """Recommended next actions."""
    PROCEED_TO_NEXT_PHASE = "proceed_to_next_phase"
    RUN_VALIDATION = "run_validation"
    WRITE_TESTS = "write_tests"
    UPDATE_DOCS = "update_docs"
    RECORD_DECISION = "record_decision"
    RESOLVE_ASSUMPTION = "resolve_assumption"
    COMMIT_CHECKPOINT = "commit_checkpoint"
    BRANCH_BEFORE_CHANGE = "branch_before_change"
    STOP_AND_ASK_USER = "stop_and_ask_user"
    PERFORM_SOURCE_AUDIT = "perform_source_audit"
    CLEAN_INSTALL_OR_REBUILD = "clean_install_or_rebuild"


class Confidence(str, Enum):
    """Recommendation confidence levels."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# =============================================================================
# Core Records
# =============================================================================


class ProjectRecord(BaseModel):
    """Project configuration and metadata."""
    project_id: str
    name: str
    root_path: str
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    default_validation_commands: list[str] = Field(default_factory=list)
    description: str | None = None


class PhaseRecord(BaseModel):
    """Implementation phase tracking."""
    id: str
    name: str
    objective: str
    scope: list[str] = Field(default_factory=list)
    success_criteria: list[str] = Field(default_factory=list)
    status: PhaseStatus = PhaseStatus.PLANNED
    blockers: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    notes: str | None = None
    files_changed: list[str] = Field(default_factory=list)
    validation_ids: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    completed_at: datetime | None = None
    commit_hash: str | None = None


class DecisionRecord(BaseModel):
    """Confirmed technical or domain decision."""
    id: str
    title: str
    decision: str
    status: DecisionStatus = DecisionStatus.PROPOSED
    rationale: str | None = None
    consequences: list[str] = Field(default_factory=list)
    source: str | None = None
    related_files: list[str] = Field(default_factory=list)
    related_phase_id: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class AssumptionRecord(BaseModel):
    """Tracked assumption with validation status."""
    id: str
    assumption: str
    status: AssumptionStatus = AssumptionStatus.UNCONFIRMED
    risk: str | None = None
    validation_status: str | None = None
    resolution_plan: str | None = None
    related_files: list[str] = Field(default_factory=list)
    related_phase_id: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class ValidationRecord(BaseModel):
    """Validation command execution result."""
    id: str
    phase_id: str | None = None
    command: str | None = None
    status: ValidationStatus = ValidationStatus.NOT_RUN
    exit_code: int | None = None
    duration_seconds: float | None = None
    # Test results
    passed: int | None = None
    failed: int | None = None
    # Lint results
    errors: int | None = None
    warnings: int | None = None
    fixed: int | None = None
    # Output
    output_summary: str | None = None
    raw_output_path: str | None = None
    created_at: datetime = Field(default_factory=utc_now)


# =============================================================================
# Scan & Audit Results
# =============================================================================


class GitState(BaseModel):
    """Git repository state."""
    branch: str | None = None
    commit: str | None = None
    dirty: bool = False
    changed_files: list[str] = Field(default_factory=list)
    staged_files: list[str] = Field(default_factory=list)


class PackageInfo(BaseModel):
    """Package/project metadata extracted from config files."""
    name: str | None = None
    version: str | None = None
    description: str | None = None
    package_type: str | None = None  # python, node, rust, go, etc.
    dependencies: list[str] = Field(default_factory=list)
    dev_dependencies: list[str] = Field(default_factory=list)
    scripts: dict[str, str] = Field(default_factory=dict)
    entry_point: str | None = None


class DetectedFiles(BaseModel):
    """Categorized detected files."""
    source: list[str] = Field(default_factory=list)
    tests: list[str] = Field(default_factory=list)
    docs: list[str] = Field(default_factory=list)
    config: list[str] = Field(default_factory=list)
    scripts: list[str] = Field(default_factory=list)
    migrations: list[str] = Field(default_factory=list)
    readme: list[str] = Field(default_factory=list)
    env_files: list[str] = Field(default_factory=list)


class ProjectStateSnapshot(BaseModel):
    """Complete project state snapshot."""
    timestamp: datetime = Field(default_factory=utc_now)
    root_path: str
    git: GitState | None = None
    detected_files: DetectedFiles = Field(default_factory=DetectedFiles)
    package_info: PackageInfo | None = None
    warnings: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    recent_files: list[str] = Field(default_factory=list)


class ClassifiedFile(BaseModel):
    """File with source-of-truth classification."""
    path: str
    classification: FileClassification
    reason: str | None = None
    warnings: list[str] = Field(default_factory=list)


class SourceOfTruthAudit(BaseModel):
    """Source-of-truth audit result."""
    timestamp: datetime = Field(default_factory=utc_now)
    root_path: str
    classified_files: list[ClassifiedFile] = Field(default_factory=list)
    flags: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


# =============================================================================
# Reports & Prompts
# =============================================================================


class ReportResult(BaseModel):
    """Generated report metadata."""
    report_id: str
    report_type: ReportType
    output_path: str
    markdown_summary: str
    created_at: datetime = Field(default_factory=utc_now)


class AgentPrompt(BaseModel):
    """Generated agent prompt."""
    prompt_id: str
    prompt_type: PromptType
    prompt_text: str
    output_path: str | None = None
    phase_id: str | None = None
    created_at: datetime = Field(default_factory=utc_now)


class NextActionRecommendation(BaseModel):
    """Recommended next action with rationale."""
    recommendation: NextAction
    confidence: Confidence
    rationale: str
    required_before_next: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)


# =============================================================================
# Phase Completion
# =============================================================================


class PhaseCompletionReport(BaseModel):
    """Phase completion summary."""
    phase_id: str
    phase_name: str
    status: PhaseStatus
    files_changed: list[str] = Field(default_factory=list)
    validation_ids: list[str] = Field(default_factory=list)
    known_limitations: list[str] = Field(default_factory=list)
    next_recommendation: str | None = None
    commit_hash: str | None = None
    completed_at: datetime = Field(default_factory=utc_now)


# =============================================================================
# Tool Input Models
# =============================================================================


class ScanProjectInput(BaseModel):
    """Input for scan_project_state tool."""
    root_path: str
    include_git: bool = True
    include_file_tree: bool = True
    include_recent_changes: bool = True
    include_package_files: bool = True
    include_test_files: bool = True
    max_depth: int = 5


class CreatePhaseInput(BaseModel):
    """Input for create_phase tool."""
    name: str
    objective: str
    scope: list[str] = Field(default_factory=list)
    success_criteria: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)


class UpdatePhaseInput(BaseModel):
    """Input for update_phase tool."""
    phase_id: str
    status: PhaseStatus | None = None
    notes: str | None = None
    files_changed: list[str] | None = None
    blockers: list[str] | None = None
    success_criteria: list[str] | None = None


class CompletePhaseInput(BaseModel):
    """Input for complete_phase tool."""
    phase_id: str
    validation_ids: list[str] = Field(default_factory=list)
    files_changed: list[str] = Field(default_factory=list)
    known_limitations: list[str] = Field(default_factory=list)
    next_recommendation: str | None = None
    commit_hash: str | None = None


class RecordDecisionInput(BaseModel):
    """Input for record_decision tool."""
    title: str
    decision: str
    rationale: str | None = None
    consequences: list[str] = Field(default_factory=list)
    source: str | None = None
    status: DecisionStatus = DecisionStatus.PROPOSED
    related_files: list[str] = Field(default_factory=list)
    related_phase_id: str | None = None


class RecordAssumptionInput(BaseModel):
    """Input for record_assumption tool."""
    assumption: str
    risk: str | None = None
    status: AssumptionStatus = AssumptionStatus.UNCONFIRMED
    validation_status: str | None = None
    resolution_plan: str | None = None
    related_files: list[str] = Field(default_factory=list)
    related_phase_id: str | None = None


class RecordValidationInput(BaseModel):
    """Input for record_validation tool."""
    phase_id: str | None = None
    command: str | None = None
    status: ValidationStatus = ValidationStatus.NOT_RUN
    exit_code: int | None = None
    duration_seconds: float | None = None
    passed: int | None = None
    failed: int | None = None
    output_summary: str | None = None
    raw_output_path: str | None = None


class RunValidationInput(BaseModel):
    """Input for run_validation_command tool."""
    command: str
    working_directory: str
    phase_id: str | None = None
    required_pass: bool = False
    timeout_seconds: int = 300
    output_capture: OutputCapture = OutputCapture.SUMMARY


class AuditSourceInput(BaseModel):
    """Input for audit_source_of_truth tool."""
    root_path: str
    canonical_patterns: list[str] = Field(default_factory=list)
    generated_patterns: list[str] = Field(default_factory=list)
    migration_patterns: list[str] = Field(default_factory=list)
    docs_patterns: list[str] = Field(default_factory=list)
    script_patterns: list[str] = Field(default_factory=list)
    test_patterns: list[str] = Field(default_factory=list)
    compare_docs_to_code: bool = False


class GenerateReportInput(BaseModel):
    """Input for generate_report tool."""
    report_type: ReportType
    output_path: str | None = None
    phase_id: str | None = None
    include_decisions: bool = True
    include_assumptions: bool = True
    include_validations: bool = True


class GeneratePromptInput(BaseModel):
    """Input for generate_agent_prompt tool."""
    prompt_type: PromptType
    phase_id: str | None = None
    context_level: ContextLevel = ContextLevel.STANDARD
    include_decisions: bool = True
    include_assumptions: bool = True
    include_validation_requirements: bool = True
    include_file_context: bool = True


class RecommendNextInput(BaseModel):
    """Input for recommend_next_action tool."""
    phase_id: str | None = None
    include_git_state: bool = True
    include_validation_state: bool = True
    include_assumptions: bool = True
