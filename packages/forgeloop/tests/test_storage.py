"""Tests for ForgeLoop storage layer."""

import tempfile
from pathlib import Path

import pytest

from forgeloop_mcp.storage import ForgeLoopStorage


@pytest.fixture
def temp_project():
    """Create a temporary project directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


class TestForgeLoopStorage:
    """Tests for ForgeLoopStorage."""

    def test_init_project(self, temp_project):
        """Test project initialization."""
        storage = ForgeLoopStorage(temp_project)
        project = storage.init_project("Test Project", "A test project")

        assert project.name == "Test Project"
        assert project.description == "A test project"
        assert (temp_project / ".forgeloop" / "project.json").exists()

    def test_is_initialized(self, temp_project):
        """Test initialization check."""
        storage = ForgeLoopStorage(temp_project)
        assert not storage.is_initialized

        storage.init_project("Test")
        assert storage.is_initialized

    def test_create_phase(self, temp_project):
        """Test phase creation."""
        storage = ForgeLoopStorage(temp_project)
        storage.init_project("Test")

        phase = storage.create_phase(
            name="Phase 1",
            objective="Test objective",
            scope=["src/"],
            success_criteria=["Tests pass"],
        )

        assert phase.id == "PHASE-0001"
        assert phase.name == "Phase 1"
        assert phase.objective == "Test objective"
        assert phase.status.value == "planned"

    def test_update_phase(self, temp_project):
        """Test phase update."""
        storage = ForgeLoopStorage(temp_project)
        storage.init_project("Test")

        phase = storage.create_phase(name="Phase 1", objective="Test")
        updated = storage.update_phase(phase.id, status="active", notes="Started work")

        assert updated.status.value == "active"
        assert updated.notes == "Started work"

    def test_create_decision(self, temp_project):
        """Test decision creation."""
        storage = ForgeLoopStorage(temp_project)
        storage.init_project("Test")

        decision = storage.create_decision(
            title="Use pytest",
            decision="We will use pytest for testing",
            status="accepted",
            rationale="Industry standard",
        )

        assert decision.id == "DEC-0001"
        assert decision.title == "Use pytest"
        assert decision.status.value == "accepted"

    def test_create_assumption(self, temp_project):
        """Test assumption creation."""
        storage = ForgeLoopStorage(temp_project)
        storage.init_project("Test")

        assumption = storage.create_assumption(
            assumption="Tests cover all routes",
            risk="Untested routes may fail",
            status="unconfirmed",
        )

        assert assumption.id == "ASM-0001"
        assert assumption.assumption == "Tests cover all routes"
        assert assumption.status.value == "unconfirmed"

    def test_create_validation(self, temp_project):
        """Test validation creation."""
        storage = ForgeLoopStorage(temp_project)
        storage.init_project("Test")

        validation = storage.create_validation(
            command="pytest",
            status="pass",
            exit_code=0,
            passed=10,
            failed=0,
        )

        assert validation.id == "VAL-0001"
        assert validation.status.value == "pass"
        assert validation.passed == 10

    def test_get_active_phase(self, temp_project):
        """Test getting active phase."""
        storage = ForgeLoopStorage(temp_project)
        storage.init_project("Test")

        # No active phase initially
        assert storage.get_active_phase() is None

        phase = storage.create_phase(name="Phase 1", objective="Test")
        storage.update_phase(phase.id, status="active")

        active = storage.get_active_phase()
        assert active is not None
        assert active.id == phase.id

    def test_sequential_ids(self, temp_project):
        """Test that IDs are sequential."""
        storage = ForgeLoopStorage(temp_project)
        storage.init_project("Test")

        phase1 = storage.create_phase(name="P1", objective="O1")
        phase2 = storage.create_phase(name="P2", objective="O2")

        assert phase1.id == "PHASE-0001"
        assert phase2.id == "PHASE-0002"
