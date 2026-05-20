"""
Tests for the Architect orchestrator.
"""

import pytest
import pytest_asyncio
from pathlib import Path
import tempfile
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from architect_mcp.state import StateManager
from architect_mcp.orchestrator import AgentOrchestrator
from architect_mcp.models import TeamType, AgentRole, TaskStatus, LogLevel


@pytest_asyncio.fixture
async def state_manager():
    """Create a state manager with a temp directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = StateManager(data_dir=Path(tmpdir))
        await manager.initialize()
        yield manager


@pytest_asyncio.fixture
async def project(state_manager):
    """Create a test project."""
    return await state_manager.create_project(
        name="TestApp",
        description="A test application",
        idea="A task management app with team collaboration and real-time updates"
    )


@pytest.fixture
def orchestrator(state_manager):
    """Create an orchestrator."""
    return AgentOrchestrator(state_manager)


class TestAgentOrchestrator:
    """Tests for AgentOrchestrator."""

    @pytest.mark.asyncio
    async def test_plan_project(self, state_manager, project, orchestrator):
        """Test creating an execution plan."""
        plan = await orchestrator.plan_project(project.idea)

        assert plan.project_id == project.id
        assert len(plan.phases) > 0
        assert len(plan.team_structure.get("teams", [])) > 0
        assert plan.estimated_sprints > 0

    @pytest.mark.asyncio
    async def test_analyze_required_teams(self, state_manager, orchestrator):
        """Test team analysis from idea."""
        # Web app should need frontend
        idea = "A web application with user dashboard"
        teams = orchestrator._analyze_required_teams(idea)
        assert TeamType.FRONTEND in teams
        assert TeamType.BACKEND in teams

        # API should need API team
        idea = "An API service for data processing"
        teams = orchestrator._analyze_required_teams(idea)
        assert TeamType.API in teams

        # Auth mention should need auth team
        idea = "An app with user authentication and login"
        teams = orchestrator._analyze_required_teams(idea)
        assert TeamType.AUTH in teams

    @pytest.mark.asyncio
    async def test_spawn_team_structure(self, state_manager, project, orchestrator):
        """Test spawning team structure."""
        # First create the plan
        await orchestrator.plan_project(project.idea)

        # Then spawn teams
        result = await orchestrator.spawn_team_structure(project.id)

        assert result["structure"]["total_teams"] > 0
        assert result["structure"]["total_agents"] > 0
        assert result["structure"]["supervisors"] > 0
        assert result["structure"]["integrators"] == 1

    @pytest.mark.asyncio
    async def test_check_integration_no_issues(self, state_manager, project, orchestrator):
        """Test integration check with no issues."""
        check = await orchestrator.check_integration(project.id)

        assert check.compatible == True
        assert len(check.teams_checked) == 0  # No teams yet

    @pytest.mark.asyncio
    async def test_supervisor_review(self, state_manager, project, orchestrator):
        """Test supervisor review."""
        # Create plan and teams
        await orchestrator.plan_project(project.idea)
        await orchestrator.spawn_team_structure(project.id)

        # Create a sprint
        sprint = await state_manager.create_sprint(
            project.id,
            "Sprint 1",
            "Test sprint",
            [TeamType.BACKEND]
        )

        # Add a task
        await state_manager.add_task(
            project.id,
            sprint.id,
            "Test task",
            "A test task",
            TeamType.BACKEND
        )

        # Get the backend team
        updated_project = state_manager.projects[project.id]
        backend_team = next(
            (t for t in updated_project.teams if t.type == TeamType.BACKEND),
            None
        )

        if backend_team:
            review = await orchestrator.supervisor_review(project.id, backend_team.id)
            assert "stats" in review
            assert "status" in review


class TestStateManager:
    """Tests for StateManager."""

    @pytest.mark.asyncio
    async def test_create_project(self, state_manager):
        """Test project creation."""
        project = await state_manager.create_project(
            "Test",
            "Description",
            "An idea"
        )

        assert project.id is not None
        assert project.name == "Test"
        assert state_manager.active_project_id == project.id

    @pytest.mark.asyncio
    async def test_create_team(self, state_manager, project):
        """Test team creation."""
        team = await state_manager.create_team(
            project.id,
            TeamType.BACKEND,
            "Backend Team"
        )

        assert team.id is not None
        assert team.type == TeamType.BACKEND

    @pytest.mark.asyncio
    async def test_spawn_agent(self, state_manager, project):
        """Test agent spawning."""
        team = await state_manager.create_team(
            project.id,
            TeamType.BACKEND,
            "Backend Team"
        )

        agent = await state_manager.spawn_agent(
            project.id,
            team.id,
            AgentRole.SUPERVISOR,
            "Backend Supervisor",
            skills=["monitoring", "review"]
        )

        assert agent.id is not None
        assert agent.role == AgentRole.SUPERVISOR
        assert "monitoring" in agent.skills

    @pytest.mark.asyncio
    async def test_create_sprint(self, state_manager, project):
        """Test sprint creation."""
        sprint = await state_manager.create_sprint(
            project.id,
            "Sprint 1",
            "Foundation",
            [TeamType.BACKEND, TeamType.DATABASE]
        )

        assert sprint.id is not None
        assert TeamType.BACKEND in sprint.teams

    @pytest.mark.asyncio
    async def test_add_task(self, state_manager, project):
        """Test task addition."""
        sprint = await state_manager.create_sprint(
            project.id,
            "Sprint 1",
            "Foundation",
            [TeamType.BACKEND]
        )

        task = await state_manager.add_task(
            project.id,
            sprint.id,
            "Implement user model",
            "Create the User model with auth fields",
            TeamType.BACKEND,
            priority=1
        )

        assert task.id is not None
        assert task.priority == 1
        assert task.status == TaskStatus.PENDING

    @pytest.mark.asyncio
    async def test_update_task_status(self, state_manager, project):
        """Test task status update."""
        sprint = await state_manager.create_sprint(
            project.id,
            "Sprint 1",
            "Foundation",
            [TeamType.BACKEND]
        )

        task = await state_manager.add_task(
            project.id,
            sprint.id,
            "Test task",
            "Description",
            TeamType.BACKEND
        )

        updated = await state_manager.update_task_status(
            project.id,
            sprint.id,
            task.id,
            TaskStatus.COMPLETED,
            output="Done!"
        )

        assert updated.status == TaskStatus.COMPLETED
        assert updated.output == "Done!"
        assert updated.completed_at is not None

    @pytest.mark.asyncio
    async def test_sprint_log_compaction(self, state_manager, project):
        """Test that sprint logs are kept compact."""
        sprint = await state_manager.create_sprint(
            project.id,
            "Sprint 1",
            "Foundation",
            [TeamType.BACKEND]
        )

        # Add more than 100 logs
        for i in range(150):
            await state_manager.add_sprint_log(
                project.id,
                sprint.id,
                LogLevel.INFO,
                "backend",
                f"Log entry {i}"
            )

        # Check that only 100 are kept
        updated_project = state_manager.projects[project.id]
        updated_sprint = next(s for s in updated_project.sprints if s.id == sprint.id)

        assert len(updated_sprint.logs) <= 100
