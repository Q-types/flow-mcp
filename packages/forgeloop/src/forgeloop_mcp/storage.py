"""JSON file storage layer for ForgeLoop MCP."""

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

from .models import (
    AssumptionRecord,
    DecisionRecord,
    PhaseRecord,
    ProjectRecord,
    ValidationRecord,
    utc_now,
)

T = TypeVar("T", bound=BaseModel)

FORGELOOP_DIR = ".forgeloop"
PROJECT_FILE = "project.json"
PHASES_FILE = "phases.json"
DECISIONS_FILE = "decisions.json"
ASSUMPTIONS_FILE = "assumptions.json"
VALIDATIONS_FILE = "validations.json"


class StorageError(Exception):
    """Storage operation error."""
    pass


class ForgeLoopStorage:
    """JSON file-based storage for ForgeLoop project data."""

    def __init__(self, root_path: str | Path):
        """Initialize storage for a project root path.

        Args:
            root_path: Path to the project root directory.
        """
        self.root_path = Path(root_path).resolve()
        self.forgeloop_dir = self.root_path / FORGELOOP_DIR
        self._counters: dict[str, int] = {}

    @property
    def is_initialized(self) -> bool:
        """Check if ForgeLoop is initialized for this project."""
        return (self.forgeloop_dir / PROJECT_FILE).exists()

    def ensure_initialized(self) -> None:
        """Ensure .forgeloop directory exists."""
        if not self.forgeloop_dir.exists():
            self.forgeloop_dir.mkdir(parents=True, exist_ok=True)
            # Create subdirectories
            (self.forgeloop_dir / "snapshots").mkdir(exist_ok=True)
            (self.forgeloop_dir / "reports").mkdir(exist_ok=True)
            (self.forgeloop_dir / "prompts").mkdir(exist_ok=True)
            (self.forgeloop_dir / "logs").mkdir(exist_ok=True)

    # =========================================================================
    # Atomic JSON Operations
    # =========================================================================

    def _read_json(self, filename: str) -> dict | list:
        """Read JSON file, returning empty structure if not exists."""
        filepath = self.forgeloop_dir / filename
        if not filepath.exists():
            return {} if filename == PROJECT_FILE else []
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise StorageError(f"Invalid JSON in {filename}: {e}")

    def _write_json(self, filename: str, data: dict | list) -> None:
        """Atomically write JSON file."""
        self.ensure_initialized()
        filepath = self.forgeloop_dir / filename

        # Write to temp file first, then rename (atomic on POSIX)
        fd, temp_path = tempfile.mkstemp(
            dir=self.forgeloop_dir,
            prefix=f".{filename}.",
            suffix=".tmp"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=self._json_serializer)
                f.write("\n")
            os.replace(temp_path, filepath)
        except Exception:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise

    def _json_serializer(self, obj):
        """Custom JSON serializer for datetime objects."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

    # =========================================================================
    # ID Generation
    # =========================================================================

    def _generate_id(self, prefix: str) -> str:
        """Generate next sequential ID with prefix."""
        if prefix not in self._counters:
            # Load existing items to find max ID
            self._counters[prefix] = self._find_max_id(prefix)
        self._counters[prefix] += 1
        return f"{prefix}-{self._counters[prefix]:04d}"

    def _find_max_id(self, prefix: str) -> int:
        """Find the maximum existing ID number for a prefix."""
        file_map = {
            "PHASE": PHASES_FILE,
            "DEC": DECISIONS_FILE,
            "ASM": ASSUMPTIONS_FILE,
            "VAL": VALIDATIONS_FILE,
            "REP": "reports.json",
            "PROMPT": "prompts.json",
        }
        filename = file_map.get(prefix)
        if not filename:
            return 0

        items = self._read_json(filename)
        if not items:
            return 0

        max_num = 0
        for item in items:
            item_id = item.get("id", "")
            if item_id.startswith(f"{prefix}-"):
                try:
                    num = int(item_id.split("-")[1])
                    max_num = max(max_num, num)
                except (ValueError, IndexError):
                    pass
        return max_num

    # =========================================================================
    # Project Operations
    # =========================================================================

    def get_project(self) -> ProjectRecord | None:
        """Get the project record."""
        data = self._read_json(PROJECT_FILE)
        if not data:
            return None
        return ProjectRecord.model_validate(data)

    def save_project(self, project: ProjectRecord) -> None:
        """Save the project record."""
        project.updated_at = utc_now()
        self._write_json(PROJECT_FILE, project.model_dump(mode="json"))

    def init_project(self, name: str, description: str | None = None) -> ProjectRecord:
        """Initialize a new project."""
        self.ensure_initialized()
        project = ProjectRecord(
            project_id=f"proj_{int(utc_now().timestamp())}",
            name=name,
            root_path=str(self.root_path),
            description=description,
        )
        self.save_project(project)

        # Initialize empty arrays for other files
        for filename in [PHASES_FILE, DECISIONS_FILE, ASSUMPTIONS_FILE, VALIDATIONS_FILE]:
            if not (self.forgeloop_dir / filename).exists():
                self._write_json(filename, [])

        return project

    # =========================================================================
    # Phase Operations
    # =========================================================================

    def get_phases(self) -> list[PhaseRecord]:
        """Get all phases."""
        data = self._read_json(PHASES_FILE)
        return [PhaseRecord.model_validate(p) for p in data]

    def get_phase(self, phase_id: str) -> PhaseRecord | None:
        """Get a phase by ID."""
        phases = self.get_phases()
        for phase in phases:
            if phase.id == phase_id:
                return phase
        return None

    def get_active_phase(self) -> PhaseRecord | None:
        """Get the currently active phase."""
        phases = self.get_phases()
        for phase in phases:
            if phase.status.value == "active":
                return phase
        return None

    def create_phase(
        self,
        name: str,
        objective: str,
        scope: list[str] | None = None,
        success_criteria: list[str] | None = None,
        blockers: list[str] | None = None,
        risks: list[str] | None = None,
    ) -> PhaseRecord:
        """Create a new phase."""
        phase = PhaseRecord(
            id=self._generate_id("PHASE"),
            name=name,
            objective=objective,
            scope=scope or [],
            success_criteria=success_criteria or [],
            blockers=blockers or [],
            risks=risks or [],
        )
        phases = self.get_phases()
        phases.append(phase)
        self._write_json(PHASES_FILE, [p.model_dump(mode="json") for p in phases])
        return phase

    def update_phase(self, phase_id: str, **updates) -> PhaseRecord | None:
        """Update a phase."""
        phases = self.get_phases()
        for i, phase in enumerate(phases):
            if phase.id == phase_id:
                phase_data = phase.model_dump()
                for key, value in updates.items():
                    if value is not None and key in phase_data:
                        phase_data[key] = value
                phase_data["updated_at"] = utc_now()
                phases[i] = PhaseRecord.model_validate(phase_data)
                self._write_json(PHASES_FILE, [p.model_dump(mode="json") for p in phases])
                return phases[i]
        return None

    # =========================================================================
    # Decision Operations
    # =========================================================================

    def get_decisions(self) -> list[DecisionRecord]:
        """Get all decisions."""
        data = self._read_json(DECISIONS_FILE)
        return [DecisionRecord.model_validate(d) for d in data]

    def get_decision(self, decision_id: str) -> DecisionRecord | None:
        """Get a decision by ID."""
        decisions = self.get_decisions()
        for dec in decisions:
            if dec.id == decision_id:
                return dec
        return None

    def create_decision(
        self,
        title: str,
        decision: str,
        status: str = "proposed",
        rationale: str | None = None,
        consequences: list[str] | None = None,
        source: str | None = None,
        related_files: list[str] | None = None,
        related_phase_id: str | None = None,
    ) -> DecisionRecord:
        """Create a new decision."""
        from .models import DecisionStatus

        dec = DecisionRecord(
            id=self._generate_id("DEC"),
            title=title,
            decision=decision,
            status=DecisionStatus(status),
            rationale=rationale,
            consequences=consequences or [],
            source=source,
            related_files=related_files or [],
            related_phase_id=related_phase_id,
        )
        decisions = self.get_decisions()
        decisions.append(dec)
        self._write_json(DECISIONS_FILE, [d.model_dump(mode="json") for d in decisions])
        return dec

    # =========================================================================
    # Assumption Operations
    # =========================================================================

    def get_assumptions(self) -> list[AssumptionRecord]:
        """Get all assumptions."""
        data = self._read_json(ASSUMPTIONS_FILE)
        return [AssumptionRecord.model_validate(a) for a in data]

    def get_assumption(self, assumption_id: str) -> AssumptionRecord | None:
        """Get an assumption by ID."""
        assumptions = self.get_assumptions()
        for asm in assumptions:
            if asm.id == assumption_id:
                return asm
        return None

    def create_assumption(
        self,
        assumption: str,
        status: str = "unconfirmed",
        risk: str | None = None,
        validation_status: str | None = None,
        resolution_plan: str | None = None,
        related_files: list[str] | None = None,
        related_phase_id: str | None = None,
    ) -> AssumptionRecord:
        """Create a new assumption."""
        from .models import AssumptionStatus

        asm = AssumptionRecord(
            id=self._generate_id("ASM"),
            assumption=assumption,
            status=AssumptionStatus(status),
            risk=risk,
            validation_status=validation_status,
            resolution_plan=resolution_plan,
            related_files=related_files or [],
            related_phase_id=related_phase_id,
        )
        assumptions = self.get_assumptions()
        assumptions.append(asm)
        self._write_json(ASSUMPTIONS_FILE, [a.model_dump(mode="json") for a in assumptions])
        return asm

    def update_assumption(self, assumption_id: str, **updates) -> AssumptionRecord | None:
        """Update an assumption."""
        assumptions = self.get_assumptions()
        for i, asm in enumerate(assumptions):
            if asm.id == assumption_id:
                asm_data = asm.model_dump()
                for key, value in updates.items():
                    if value is not None and key in asm_data:
                        asm_data[key] = value
                asm_data["updated_at"] = utc_now()
                assumptions[i] = AssumptionRecord.model_validate(asm_data)
                self._write_json(ASSUMPTIONS_FILE, [a.model_dump(mode="json") for a in assumptions])
                return assumptions[i]
        return None

    # =========================================================================
    # Validation Operations
    # =========================================================================

    def get_validations(self) -> list[ValidationRecord]:
        """Get all validations."""
        data = self._read_json(VALIDATIONS_FILE)
        return [ValidationRecord.model_validate(v) for v in data]

    def get_validation(self, validation_id: str) -> ValidationRecord | None:
        """Get a validation by ID."""
        validations = self.get_validations()
        for val in validations:
            if val.id == validation_id:
                return val
        return None

    def get_validations_for_phase(self, phase_id: str) -> list[ValidationRecord]:
        """Get all validations for a phase."""
        validations = self.get_validations()
        return [v for v in validations if v.phase_id == phase_id]

    def create_validation(
        self,
        phase_id: str | None = None,
        command: str | None = None,
        status: str = "not_run",
        exit_code: int | None = None,
        duration_seconds: float | None = None,
        passed: int | None = None,
        failed: int | None = None,
        errors: int | None = None,
        warnings: int | None = None,
        fixed: int | None = None,
        output_summary: str | None = None,
        raw_output_path: str | None = None,
    ) -> ValidationRecord:
        """Create a new validation record."""
        from .models import ValidationStatus

        val = ValidationRecord(
            id=self._generate_id("VAL"),
            phase_id=phase_id,
            command=command,
            status=ValidationStatus(status),
            exit_code=exit_code,
            duration_seconds=duration_seconds,
            passed=passed,
            failed=failed,
            errors=errors,
            warnings=warnings,
            fixed=fixed,
            output_summary=output_summary,
            raw_output_path=raw_output_path,
        )
        validations = self.get_validations()
        validations.append(val)
        self._write_json(VALIDATIONS_FILE, [v.model_dump(mode="json") for v in validations])
        return val

    # =========================================================================
    # File Utilities
    # =========================================================================

    def get_logs_dir(self) -> Path:
        """Get the logs directory path."""
        self.ensure_initialized()
        return self.forgeloop_dir / "logs"

    def get_reports_dir(self) -> Path:
        """Get the reports directory path."""
        self.ensure_initialized()
        return self.forgeloop_dir / "reports"

    def get_prompts_dir(self) -> Path:
        """Get the prompts directory path."""
        self.ensure_initialized()
        return self.forgeloop_dir / "prompts"

    def get_snapshots_dir(self) -> Path:
        """Get the snapshots directory path."""
        self.ensure_initialized()
        return self.forgeloop_dir / "snapshots"

    def save_log(self, validation_id: str, content: str) -> Path:
        """Save validation log content."""
        log_path = self.get_logs_dir() / f"{validation_id}.log"
        log_path.write_text(content, encoding="utf-8")
        return log_path

    def save_report(self, report_id: str, content: str) -> Path:
        """Save report content."""
        report_path = self.get_reports_dir() / f"{report_id}.md"
        report_path.write_text(content, encoding="utf-8")
        return report_path

    def save_prompt(self, prompt_id: str, content: str) -> Path:
        """Save prompt content."""
        prompt_path = self.get_prompts_dir() / f"{prompt_id}.md"
        prompt_path.write_text(content, encoding="utf-8")
        return prompt_path
