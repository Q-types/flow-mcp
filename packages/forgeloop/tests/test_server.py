"""Tests for ForgeLoop MCP server tools."""

import tempfile
from pathlib import Path

import pytest

from forgeloop_mcp.server import _handle_tool, list_tools


@pytest.fixture
def temp_project():
    """Create a temporary project directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)

        # Create basic structure
        (root / "src").mkdir()
        (root / "tests").mkdir()
        (root / "src" / "main.py").write_text("print('hello')")
        (root / "tests" / "test_main.py").write_text("def test_main(): pass")
        (root / "README.md").write_text("# Test Project")
        (root / "pyproject.toml").write_text(
            '[project]\nname = "test-project"\nversion = "0.1.0"\n'
            'dependencies = ["requests", "pydantic"]'
        )

        yield root


class TestListTools:
    """Tests for tool listing."""

    @pytest.mark.asyncio
    async def test_list_tools_count(self):
        """Test that all tools are listed."""
        tools = await list_tools()
        assert len(tools) == 18  # Updated count with new tools

    @pytest.mark.asyncio
    async def test_list_tools_names(self):
        """Test that expected tools are present."""
        tools = await list_tools()
        tool_names = [t.name for t in tools]

        expected = [
            "init_project",
            "scan_project_state",
            "create_phase",
            "update_phase",
            "complete_phase",
            "record_decision",
            "record_assumption",
            "record_validation",
            "run_validation_command",
            "audit_source_of_truth",
            "generate_report",
            "generate_agent_prompt",
            "recommend_next_action",
            "list_phases",
            "list_decisions",
            "list_assumptions",
            "list_validations",
            "get_project",
        ]

        for name in expected:
            assert name in tool_names, f"Missing tool: {name}"


class TestInitProject:
    """Tests for init_project tool."""

    @pytest.mark.asyncio
    async def test_init_project_basic(self, temp_project):
        """Test basic project initialization."""
        result = await _handle_tool("init_project", {"root_path": str(temp_project)})

        assert result["success"] is True
        assert "project" in result
        assert result["project"]["name"] == temp_project.name
        assert (temp_project / ".forgeloop" / "project.json").exists()

    @pytest.mark.asyncio
    async def test_init_project_custom_name(self, temp_project):
        """Test initialization with custom name."""
        result = await _handle_tool("init_project", {
            "root_path": str(temp_project),
            "name": "Custom Project",
            "description": "A custom project",
        })

        assert result["success"] is True
        assert result["project"]["name"] == "Custom Project"
        assert result["project"]["description"] == "A custom project"

    @pytest.mark.asyncio
    async def test_init_project_already_initialized(self, temp_project):
        """Test initialization of already initialized project."""
        # Initialize once
        await _handle_tool("init_project", {"root_path": str(temp_project)})

        # Initialize again
        result = await _handle_tool("init_project", {"root_path": str(temp_project)})

        assert result["success"] is True
        assert "already initialized" in result["message"]

    @pytest.mark.asyncio
    async def test_init_project_detects_validation_commands(self, temp_project):
        """Test that validation commands are auto-detected."""
        result = await _handle_tool("init_project", {"root_path": str(temp_project)})

        assert "detected_validation_commands" in result
        commands = result["detected_validation_commands"]
        # Should detect pytest for Python project
        assert any("pytest" in cmd for cmd in commands)


class TestScanProjectState:
    """Tests for scan_project_state tool."""

    @pytest.mark.asyncio
    async def test_scan_basic(self, temp_project):
        """Test basic project scan."""
        result = await _handle_tool("scan_project_state", {"root_path": str(temp_project)})

        assert "root_path" in result
        assert "detected_files" in result
        assert "timestamp" in result

    @pytest.mark.asyncio
    async def test_scan_detects_source(self, temp_project):
        """Test that source files are detected."""
        result = await _handle_tool("scan_project_state", {"root_path": str(temp_project)})

        source_files = result["detected_files"]["source"]
        assert any("main.py" in f for f in source_files)

    @pytest.mark.asyncio
    async def test_scan_includes_package_info(self, temp_project):
        """Test that package info is extracted."""
        result = await _handle_tool("scan_project_state", {"root_path": str(temp_project)})

        assert "package_info" in result
        pkg = result["package_info"]
        assert pkg["package_type"] == "python"
        assert pkg["name"] == "test-project"


class TestPhaseManagement:
    """Tests for phase management tools."""

    @pytest.mark.asyncio
    async def test_create_phase(self, temp_project):
        """Test phase creation."""
        result = await _handle_tool("create_phase", {
            "root_path": str(temp_project),
            "name": "Phase 1",
            "objective": "Implement feature X",
            "scope": ["src/feature.py"],
            "success_criteria": ["Tests pass", "Docs updated"],
        })

        assert result["success"] is True
        assert result["phase"]["name"] == "Phase 1"
        assert result["phase"]["status"] == "planned"

    @pytest.mark.asyncio
    async def test_update_phase(self, temp_project):
        """Test phase update."""
        # Create phase first
        create_result = await _handle_tool("create_phase", {
            "root_path": str(temp_project),
            "name": "Phase 1",
            "objective": "Test objective",
        })
        phase_id = create_result["phase"]["id"]

        # Update phase
        result = await _handle_tool("update_phase", {
            "root_path": str(temp_project),
            "phase_id": phase_id,
            "status": "active",
            "notes": "Started work",
        })

        assert result["success"] is True
        assert result["phase"]["status"] == "active"
        assert result["phase"]["notes"] == "Started work"

    @pytest.mark.asyncio
    async def test_list_phases(self, temp_project):
        """Test phase listing."""
        # Create phases
        await _handle_tool("create_phase", {
            "root_path": str(temp_project),
            "name": "Phase 1",
            "objective": "Obj 1",
        })
        await _handle_tool("create_phase", {
            "root_path": str(temp_project),
            "name": "Phase 2",
            "objective": "Obj 2",
        })

        result = await _handle_tool("list_phases", {"root_path": str(temp_project)})

        assert result["success"] is True
        assert result["count"] == 2
        assert len(result["phases"]) == 2


class TestDecisionManagement:
    """Tests for decision management tools."""

    @pytest.mark.asyncio
    async def test_record_decision(self, temp_project):
        """Test decision recording."""
        result = await _handle_tool("record_decision", {
            "root_path": str(temp_project),
            "title": "Use pytest",
            "decision": "We will use pytest for testing",
            "rationale": "Industry standard",
            "status": "accepted",
        })

        assert result["success"] is True
        assert result["decision"]["title"] == "Use pytest"
        assert result["decision"]["status"] == "accepted"

    @pytest.mark.asyncio
    async def test_list_decisions(self, temp_project):
        """Test decision listing."""
        await _handle_tool("record_decision", {
            "root_path": str(temp_project),
            "title": "Decision 1",
            "decision": "Choice 1",
            "status": "accepted",
        })
        await _handle_tool("record_decision", {
            "root_path": str(temp_project),
            "title": "Decision 2",
            "decision": "Choice 2",
            "status": "proposed",
        })

        # List all
        result = await _handle_tool("list_decisions", {"root_path": str(temp_project)})
        assert result["count"] == 2

        # Filter by status
        result = await _handle_tool("list_decisions", {
            "root_path": str(temp_project),
            "status": "accepted",
        })
        assert result["count"] == 1


class TestAssumptionManagement:
    """Tests for assumption management tools."""

    @pytest.mark.asyncio
    async def test_record_assumption(self, temp_project):
        """Test assumption recording."""
        result = await _handle_tool("record_assumption", {
            "root_path": str(temp_project),
            "assumption": "Tests cover all routes",
            "risk": "Untested routes may fail",
            "status": "unconfirmed",
        })

        assert result["success"] is True
        assert result["assumption"]["assumption"] == "Tests cover all routes"

    @pytest.mark.asyncio
    async def test_list_assumptions(self, temp_project):
        """Test assumption listing."""
        await _handle_tool("record_assumption", {
            "root_path": str(temp_project),
            "assumption": "Assumption 1",
        })

        result = await _handle_tool("list_assumptions", {"root_path": str(temp_project)})
        assert result["count"] == 1


class TestValidation:
    """Tests for validation tools."""

    @pytest.mark.asyncio
    async def test_record_validation(self, temp_project):
        """Test validation recording."""
        result = await _handle_tool("record_validation", {
            "root_path": str(temp_project),
            "command": "pytest",
            "status": "pass",
            "exit_code": 0,
            "passed": 10,
            "failed": 0,
        })

        assert result["success"] is True
        assert result["validation"]["status"] == "pass"

    @pytest.mark.asyncio
    async def test_list_validations(self, temp_project):
        """Test validation listing."""
        await _handle_tool("record_validation", {
            "root_path": str(temp_project),
            "command": "pytest",
            "status": "pass",
        })

        result = await _handle_tool("list_validations", {"root_path": str(temp_project)})
        assert result["count"] == 1


class TestGetProject:
    """Tests for get_project tool."""

    @pytest.mark.asyncio
    async def test_get_project_not_initialized(self, temp_project):
        """Test getting project when not initialized."""
        result = await _handle_tool("get_project", {"root_path": str(temp_project)})

        assert result["success"] is False
        assert "not initialized" in result["error"]

    @pytest.mark.asyncio
    async def test_get_project_with_stats(self, temp_project):
        """Test getting project with stats."""
        # Initialize
        await _handle_tool("init_project", {"root_path": str(temp_project)})

        # Add some data
        await _handle_tool("create_phase", {
            "root_path": str(temp_project),
            "name": "Phase 1",
            "objective": "Test",
        })
        await _handle_tool("record_decision", {
            "root_path": str(temp_project),
            "title": "Dec 1",
            "decision": "Choice",
            "status": "accepted",
        })

        result = await _handle_tool("get_project", {"root_path": str(temp_project)})

        assert result["success"] is True
        assert "stats" in result
        assert result["stats"]["phases"] == 1
        assert result["stats"]["decisions"] == 1
        assert result["stats"]["accepted_decisions"] == 1


class TestRecommendNextAction:
    """Tests for recommend_next_action tool."""

    @pytest.mark.asyncio
    async def test_recommend_not_initialized(self, temp_project):
        """Test recommendation when project not initialized."""
        result = await _handle_tool("recommend_next_action", {"root_path": str(temp_project)})

        assert result["recommendation"] == "perform_source_audit"

    @pytest.mark.asyncio
    async def test_recommend_with_active_phase(self, temp_project):
        """Test recommendation with active phase."""
        await _handle_tool("init_project", {"root_path": str(temp_project)})

        create_result = await _handle_tool("create_phase", {
            "root_path": str(temp_project),
            "name": "Phase 1",
            "objective": "Test",
        })
        phase_id = create_result["phase"]["id"]

        await _handle_tool("update_phase", {
            "root_path": str(temp_project),
            "phase_id": phase_id,
            "status": "active",
        })

        result = await _handle_tool("recommend_next_action", {"root_path": str(temp_project)})

        # Should recommend running validation since active phase has no validations
        assert "recommendation" in result
        assert "rationale" in result


# =============================================================================
# Sprint 3: Validation & Source Audit Enhancement Tests
# =============================================================================


class TestEnhancedTestParsing:
    """Tests for enhanced test output parsing."""

    def test_parse_pytest_output(self):
        """Test parsing pytest output."""
        from forgeloop_mcp.validation import _parse_test_output

        output = "===== 10 passed, 2 failed in 1.23s ====="
        passed, failed = _parse_test_output(output, "pytest")
        assert passed == 10
        assert failed == 2

    def test_parse_cargo_test_output(self):
        """Test parsing Cargo test output."""
        from forgeloop_mcp.validation import _parse_test_output

        output = """
        running 5 tests
        test tests::test_one ... ok
        test tests::test_two ... ok
        test result: ok. 4 passed; 1 failed; 0 ignored
        """
        passed, failed = _parse_test_output(output, "cargo test")
        assert passed == 4
        assert failed == 1

    def test_parse_go_test_output(self):
        """Test parsing Go test output."""
        from forgeloop_mcp.validation import _parse_test_output

        output = """
        --- PASS: TestOne (0.00s)
        --- PASS: TestTwo (0.01s)
        --- FAIL: TestThree (0.00s)
        PASS
        """
        passed, failed = _parse_test_output(output, "go test")
        assert passed == 2
        assert failed == 1

    def test_parse_mocha_output(self):
        """Test parsing Mocha output."""
        from forgeloop_mcp.validation import _parse_test_output

        output = """
        15 passing (500ms)
        3 failing
        """
        passed, failed = _parse_test_output(output, "mocha")
        assert passed == 15
        assert failed == 3

    def test_parse_phpunit_output_success(self):
        """Test parsing PHPUnit success output."""
        from forgeloop_mcp.validation import _parse_test_output

        output = "OK (25 tests, 50 assertions)"
        passed, failed = _parse_test_output(output, "phpunit")
        assert passed == 25
        assert failed == 0

    def test_parse_rspec_output(self):
        """Test parsing RSpec output."""
        from forgeloop_mcp.validation import _parse_test_output

        output = "30 examples, 2 failures"
        passed, failed = _parse_test_output(output, "rspec")
        assert passed == 28
        assert failed == 2


class TestLintOutputParsing:
    """Tests for lint output parsing."""

    def test_parse_ruff_output(self):
        """Test parsing ruff output."""
        from forgeloop_mcp.validation import _parse_lint_output

        output = """
        src/main.py:10:5: E501 Line too long
        src/main.py:15:1: F401 Unused import
        Found 2 errors.
        """
        result = _parse_lint_output(output, "ruff check")
        assert result["errors"] == 2

    def test_parse_eslint_output(self):
        """Test parsing ESLint output."""
        from forgeloop_mcp.validation import _parse_lint_output

        output = """
        /src/app.js
          10:5  error  'foo' is not defined  no-undef
          15:1  warning  Unexpected console statement  no-console

        ✖ 5 problems (3 errors, 2 warnings)
        """
        result = _parse_lint_output(output, "eslint")
        assert result["errors"] == 3
        assert result["warnings"] == 2

    def test_is_lint_command(self):
        """Test lint command detection."""
        from forgeloop_mcp.validation import _is_lint_command

        assert _is_lint_command("ruff check .")
        assert _is_lint_command("eslint src/")
        assert _is_lint_command("cargo clippy")
        assert not _is_lint_command("pytest")
        assert not _is_lint_command("npm test")


class TestSourceAuditEnhancements:
    """Tests for source audit enhancements."""

    @pytest.mark.asyncio
    async def test_backup_file_detection(self, temp_project):
        """Test backup file detection."""
        # Create backup files
        (temp_project / "src" / "main.py.bak").write_text("backup")
        (temp_project / "src" / "old_file.py.old").write_text("old")

        result = await _handle_tool("audit_source_of_truth", {
            "root_path": str(temp_project),
        })

        # Should flag backup files
        assert any("backup" in flag.lower() or "obsolete" in flag.lower()
                   for flag in result.get("flags", []))

    @pytest.mark.asyncio
    async def test_docs_to_code_comparison(self, temp_project):
        """Test docs-to-code drift detection."""
        # Create a Python file with a function
        (temp_project / "src" / "utils.py").write_text("""
def calculate_total(items):
    return sum(items)

class OrderProcessor:
    pass
""")
        # Create docs that mention one but not the other
        (temp_project / "docs").mkdir(exist_ok=True)
        (temp_project / "docs" / "api.md").write_text("""
# API Documentation

## calculate_total

This function calculates totals.
""")

        result = await _handle_tool("audit_source_of_truth", {
            "root_path": str(temp_project),
            "compare_docs_to_code": True,
        })

        # Should detect undocumented symbol (OrderProcessor)
        flags = result.get("flags", [])
        assert any("undocumented" in f.lower() or "symbols" in f.lower() for f in flags)

    @pytest.mark.asyncio
    async def test_orphaned_test_detection(self, temp_project):
        """Test orphaned test file detection."""
        # Create a test file for a source that doesn't exist
        (temp_project / "tests" / "test_nonexistent.py").write_text("""
def test_something():
    pass
""")

        result = await _handle_tool("audit_source_of_truth", {
            "root_path": str(temp_project),
        })

        # Should flag orphaned test
        flags = result.get("flags", [])
        assert any("orphan" in f.lower() for f in flags)


class TestValidationRecordLintFields:
    """Tests for lint fields in validation records."""

    @pytest.mark.asyncio
    async def test_validation_record_has_lint_fields(self, temp_project):
        """Test that validation records include lint fields."""
        await _handle_tool("init_project", {"root_path": str(temp_project)})

        result = await _handle_tool("record_validation", {
            "root_path": str(temp_project),
            "command": "ruff check .",
            "status": "pass",
            "exit_code": 0,
        })

        assert result["success"] is True
        validation = result["validation"]
        # Check that lint fields exist (even if None)
        assert "errors" in validation
        assert "warnings" in validation
        assert "fixed" in validation


# =============================================================================
# Sprint 4: Reports & Prompts Tests
# =============================================================================


class TestReportGeneration:
    """Tests for report generation."""

    @pytest.mark.asyncio
    async def test_generate_project_status_report(self, temp_project):
        """Test project status report generation."""
        await _handle_tool("init_project", {"root_path": str(temp_project)})

        # Add some data
        await _handle_tool("create_phase", {
            "root_path": str(temp_project),
            "name": "Phase 1",
            "objective": "Test objective",
            "success_criteria": ["Tests pass"],
        })
        await _handle_tool("record_decision", {
            "root_path": str(temp_project),
            "title": "Test Decision",
            "decision": "We decided X",
            "status": "accepted",
        })

        result = await _handle_tool("generate_report", {
            "root_path": str(temp_project),
            "report_type": "project_status",
        })

        assert result["success"] is True
        assert "report" in result
        assert result["report"]["report_type"] == "project_status"
        assert "output_path" in result["report"]

    @pytest.mark.asyncio
    async def test_generate_validation_report(self, temp_project):
        """Test validation report generation."""
        await _handle_tool("init_project", {"root_path": str(temp_project)})

        # Add validation records
        await _handle_tool("record_validation", {
            "root_path": str(temp_project),
            "command": "pytest",
            "status": "pass",
            "exit_code": 0,
            "passed": 10,
            "failed": 0,
        })

        result = await _handle_tool("generate_report", {
            "root_path": str(temp_project),
            "report_type": "validation",
        })

        assert result["success"] is True
        assert "Validation Report" in result["report"]["markdown_summary"]

    @pytest.mark.asyncio
    async def test_generate_validation_report_with_lint(self, temp_project):
        """Test validation report includes lint fields."""
        await _handle_tool("init_project", {"root_path": str(temp_project)})

        # Add lint validation record via storage directly
        from forgeloop_mcp.storage import ForgeLoopStorage
        storage = ForgeLoopStorage(temp_project)
        storage.create_validation(
            command="ruff check .",
            status="warning",
            exit_code=1,
            errors=5,
            warnings=10,
        )

        result = await _handle_tool("generate_report", {
            "root_path": str(temp_project),
            "report_type": "validation",
        })

        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_generate_source_of_truth_report(self, temp_project):
        """Test source of truth report generation."""
        await _handle_tool("init_project", {"root_path": str(temp_project)})

        result = await _handle_tool("generate_report", {
            "root_path": str(temp_project),
            "report_type": "source_of_truth",
        })

        assert result["success"] is True
        # Should contain classification summary
        assert "report" in result

    @pytest.mark.asyncio
    async def test_generate_gap_analysis_report(self, temp_project):
        """Test gap analysis report generation."""
        await _handle_tool("init_project", {"root_path": str(temp_project)})

        # Add unconfirmed assumption
        await _handle_tool("record_assumption", {
            "root_path": str(temp_project),
            "assumption": "This is risky",
            "risk": "Could fail",
            "status": "unconfirmed",
        })

        result = await _handle_tool("generate_report", {
            "root_path": str(temp_project),
            "report_type": "gap_analysis",
        })

        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_generate_decision_summary_report(self, temp_project):
        """Test decision summary report generation."""
        await _handle_tool("init_project", {"root_path": str(temp_project)})

        await _handle_tool("record_decision", {
            "root_path": str(temp_project),
            "title": "Use pytest",
            "decision": "We will use pytest",
            "rationale": "Industry standard",
            "status": "accepted",
        })

        result = await _handle_tool("generate_report", {
            "root_path": str(temp_project),
            "report_type": "decision_summary",
        })

        assert result["success"] is True


class TestPromptGeneration:
    """Tests for agent prompt generation."""

    @pytest.mark.asyncio
    async def test_generate_audit_prompt(self, temp_project):
        """Test audit prompt generation."""
        await _handle_tool("init_project", {"root_path": str(temp_project)})

        result = await _handle_tool("generate_agent_prompt", {
            "root_path": str(temp_project),
            "prompt_type": "audit",
        })

        assert result["success"] is True
        assert "prompt" in result
        assert "Audit Task" in result["prompt"]["prompt_text"]

    @pytest.mark.asyncio
    async def test_generate_implementation_prompt(self, temp_project):
        """Test implementation prompt generation."""
        await _handle_tool("init_project", {"root_path": str(temp_project)})

        # Create active phase
        phase_result = await _handle_tool("create_phase", {
            "root_path": str(temp_project),
            "name": "Add Feature",
            "objective": "Add new feature X",
            "success_criteria": ["Tests pass", "Feature works"],
        })
        phase_id = phase_result["phase"]["id"]

        await _handle_tool("update_phase", {
            "root_path": str(temp_project),
            "phase_id": phase_id,
            "status": "active",
        })

        result = await _handle_tool("generate_agent_prompt", {
            "root_path": str(temp_project),
            "prompt_type": "implementation",
        })

        assert result["success"] is True
        assert "Implementation Task" in result["prompt"]["prompt_text"]
        assert "Add Feature" in result["prompt"]["prompt_text"]

    @pytest.mark.asyncio
    async def test_generate_validation_prompt(self, temp_project):
        """Test validation prompt generation."""
        await _handle_tool("init_project", {"root_path": str(temp_project)})

        result = await _handle_tool("generate_agent_prompt", {
            "root_path": str(temp_project),
            "prompt_type": "validation",
        })

        assert result["success"] is True
        assert "Validation Task" in result["prompt"]["prompt_text"]

    @pytest.mark.asyncio
    async def test_generate_correction_prompt(self, temp_project):
        """Test correction prompt generation."""
        await _handle_tool("init_project", {"root_path": str(temp_project)})

        # Add a failed validation
        await _handle_tool("record_validation", {
            "root_path": str(temp_project),
            "command": "pytest",
            "status": "fail",
            "exit_code": 1,
            "output_summary": "AssertionError: expected True",
        })

        result = await _handle_tool("generate_agent_prompt", {
            "root_path": str(temp_project),
            "prompt_type": "correction",
        })

        assert result["success"] is True
        assert "Correction Task" in result["prompt"]["prompt_text"]

    @pytest.mark.asyncio
    async def test_generate_progress_prompt(self, temp_project):
        """Test progress review prompt generation."""
        await _handle_tool("init_project", {"root_path": str(temp_project)})

        # Create active phase with some data
        phase_result = await _handle_tool("create_phase", {
            "root_path": str(temp_project),
            "name": "Feature Phase",
            "objective": "Implement feature",
            "success_criteria": ["Criterion 1", "Criterion 2"],
        })
        phase_id = phase_result["phase"]["id"]

        await _handle_tool("update_phase", {
            "root_path": str(temp_project),
            "phase_id": phase_id,
            "status": "active",
            "files_changed": ["src/feature.py"],
        })

        result = await _handle_tool("generate_agent_prompt", {
            "root_path": str(temp_project),
            "prompt_type": "progress",
        })

        assert result["success"] is True
        assert "Progress Review" in result["prompt"]["prompt_text"]
        assert "Success Criteria Checklist" in result["prompt"]["prompt_text"]

    @pytest.mark.asyncio
    async def test_generate_commit_summary_prompt(self, temp_project):
        """Test commit summary prompt generation."""
        await _handle_tool("init_project", {"root_path": str(temp_project)})

        result = await _handle_tool("generate_agent_prompt", {
            "root_path": str(temp_project),
            "prompt_type": "commit_summary",
        })

        assert result["success"] is True
        assert "Commit Summary" in result["prompt"]["prompt_text"]

    @pytest.mark.asyncio
    async def test_generate_next_phase_prompt(self, temp_project):
        """Test next phase planning prompt generation."""
        await _handle_tool("init_project", {"root_path": str(temp_project)})

        result = await _handle_tool("generate_agent_prompt", {
            "root_path": str(temp_project),
            "prompt_type": "next_phase",
        })

        assert result["success"] is True
        assert "Next Phase Planning" in result["prompt"]["prompt_text"]

    @pytest.mark.asyncio
    async def test_prompt_saved_to_file(self, temp_project):
        """Test that prompts are saved to files."""
        await _handle_tool("init_project", {"root_path": str(temp_project)})

        result = await _handle_tool("generate_agent_prompt", {
            "root_path": str(temp_project),
            "prompt_type": "audit",
        })

        assert result["success"] is True
        output_path = result["prompt"]["output_path"]
        full_path = temp_project / output_path
        assert full_path.exists()
