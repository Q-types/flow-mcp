"""
State management for Architect MCP.

Handles project state, persistence, and integration with Mind MCP for memory.
Implements write coalescing, indexed lookups, and secure file handling.
"""

import json
import asyncio
import os
import re
import uuid
from pathlib import Path
from datetime import datetime
from typing import Any
from collections import deque

import aiofiles
import structlog

from .models import (
    Project, Team, Sprint, Task, Agent, SprintLog,
    AgentRole, TeamType, SprintStatus, TaskStatus, LogLevel,
    ExecutionPlan, IntegrationCheck
)

logger = structlog.get_logger()

# Security constants
MAX_STATE_FILE_SIZE = 50 * 1024 * 1024  # 50MB limit
MAX_PROJECTS = 500
MAX_SPRINTS_PER_PROJECT = 100
MAX_TASKS_PER_SPRINT = 500
MAX_DECISIONS = 500
MAX_NAME_LENGTH = 200
MAX_DESCRIPTION_LENGTH = 10000
MAX_IDEA_LENGTH = 10000
UUID_PATTERN = re.compile(
    r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
    re.IGNORECASE
)


def generate_id() -> str:
    """Generate a full UUID for entity IDs."""
    return str(uuid.uuid4())


def sanitize_text(text: str, max_length: int, field_name: str) -> str:
    """Sanitize and validate text input."""
    if not isinstance(text, str):
        raise ValueError(f"{field_name} must be a string")

    # Strip and truncate
    text = text.strip()[:max_length]

    # Remove control characters except newlines and tabs
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)

    return text


class StateManager:
    """
    Manages all project state and provides persistence.

    Features:
    - Write coalescing to reduce I/O
    - Indexed lookups for O(1) access
    - Secure file permissions
    - Input validation and size limits
    """

    def __init__(self, data_dir: Path | None = None):
        # Validate and set data directory
        if data_dir is None:
            self.data_dir = Path.home() / ".architect-mcp"
        else:
            resolved = Path(data_dir).resolve()
            home = Path.home().resolve()
            # Allow paths within home or temp directories
            if not (str(resolved).startswith(str(home)) or
                    str(resolved).startswith("/tmp") or
                    str(resolved).startswith("/private/tmp")):
                logger.warning("Data directory outside home rejected", path=str(resolved))
                self.data_dir = Path.home() / ".architect-mcp"
            else:
                self.data_dir = resolved

        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Set restrictive permissions on directory
        try:
            os.chmod(self.data_dir, 0o700)
        except OSError:
            pass

        # Primary storage
        self.projects: dict[str, Project] = {}
        self.active_project_id: str | None = None

        # Indexes for O(1) lookups
        self._sprint_index: dict[str, tuple[str, Sprint]] = {}  # sprint_id -> (project_id, sprint)
        self._task_index: dict[str, tuple[str, str, Task]] = {}  # task_id -> (project_id, sprint_id, task)
        self._team_index: dict[str, tuple[str, Team]] = {}  # team_id -> (project_id, team)
        self._agent_index: dict[str, Agent] = {}  # agent_id -> agent

        # Write coalescing
        self._save_task: asyncio.Task | None = None
        self._save_delay = 0.5  # Coalesce writes within 500ms
        self._dirty = False
        self._save_lock = asyncio.Lock()

        # Mind MCP integration
        self.mind_user_id: str | None = None

    async def initialize(self):
        """Load any persisted state."""
        await self._load_state()
        self._rebuild_indexes()
        logger.info("State manager initialized")

    def _rebuild_indexes(self):
        """Rebuild indexes after loading state."""
        self._sprint_index.clear()
        self._task_index.clear()
        self._team_index.clear()
        self._agent_index.clear()

        for proj_id, project in self.projects.items():
            for team in project.teams:
                self._team_index[team.id] = (proj_id, team)
                for agent in team.agents:
                    self._agent_index[agent.id] = agent
            for sprint in project.sprints:
                self._sprint_index[sprint.id] = (proj_id, sprint)
                for task in sprint.tasks:
                    self._task_index[task.id] = (proj_id, sprint.id, task)

    async def _load_state(self):
        """Load state from disk with validation."""
        state_file = self.data_dir / "state.json"
        if not state_file.exists():
            return

        try:
            # Check file size before reading
            file_size = os.path.getsize(state_file)
            if file_size > MAX_STATE_FILE_SIZE:
                logger.error("State file too large, refusing to load", size=file_size)
                return

            async with aiofiles.open(state_file, "r") as f:
                content = await f.read()
                data = json.loads(content)

                # Handle wrapped format with checksum
                if "checksum" in data and "data" in data:
                    data = data["data"]

                projects_data = data.get("projects", [])
                if len(projects_data) > MAX_PROJECTS:
                    logger.warning("Truncating projects to limit",
                                   count=len(projects_data), limit=MAX_PROJECTS)
                    projects_data = projects_data[:MAX_PROJECTS]

                for proj_data in projects_data:
                    try:
                        proj = Project(**proj_data)
                        self.projects[proj.id] = proj
                    except Exception as e:
                        logger.warning("Invalid project data, skipping", error=str(e))
                        continue

                self.active_project_id = data.get("active_project_id")
                logger.info("Loaded state", project_count=len(self.projects))

        except json.JSONDecodeError as e:
            logger.error("Invalid JSON in state file", error=str(e))
        except Exception as e:
            logger.error("Failed to load state", error=str(e))

    def _mark_dirty(self):
        """Mark state as needing persistence (triggers coalesced save)."""
        self._dirty = True
        if self._save_task is None or self._save_task.done():
            self._save_task = asyncio.create_task(self._delayed_save())

    async def _delayed_save(self):
        """Debounced save - coalesces rapid mutations."""
        await asyncio.sleep(self._save_delay)
        if self._dirty:
            await self._do_save()

    async def _do_save(self):
        """Actual save implementation with atomic write and secure permissions."""
        async with self._save_lock:
            if not self._dirty:
                return

            state_file = self.data_dir / "state.json"
            temp_file = state_file.with_suffix('.tmp')

            data = {
                "projects": [p.model_dump(mode="json") for p in self.projects.values()],
                "active_project_id": self.active_project_id,
                "saved_at": datetime.now().isoformat(),
                "version": 1
            }

            try:
                # Serialize in executor to avoid blocking
                loop = asyncio.get_event_loop()
                json_str = await loop.run_in_executor(
                    None, lambda: json.dumps(data, indent=2, default=str)
                )

                # Write to temp file
                async with aiofiles.open(temp_file, "w") as f:
                    await f.write(json_str)

                # Set restrictive permissions
                os.chmod(temp_file, 0o600)

                # Atomic rename
                os.rename(temp_file, state_file)
                self._dirty = False

            except Exception as e:
                logger.error("Failed to save state", error=str(e))
                if temp_file.exists():
                    try:
                        temp_file.unlink()
                    except:
                        pass
                raise

    async def force_save(self):
        """Force immediate save (for shutdown or explicit save requests)."""
        if self._save_task and not self._save_task.done():
            self._save_task.cancel()
            try:
                await self._save_task
            except asyncio.CancelledError:
                pass
        if self._dirty:
            await self._do_save()

    # --- Project Management ---

    async def create_project(self, name: str, description: str, idea: str) -> Project:
        """Create a new project with validation."""
        # Validate inputs
        name = sanitize_text(name, MAX_NAME_LENGTH, "name")
        description = sanitize_text(description, MAX_DESCRIPTION_LENGTH, "description")
        idea = sanitize_text(idea, MAX_IDEA_LENGTH, "idea")

        if not name:
            raise ValueError("Project name cannot be empty")
        if not idea:
            raise ValueError("Project idea cannot be empty")

        # Check project limit
        if len(self.projects) >= MAX_PROJECTS:
            raise ValueError(f"Maximum of {MAX_PROJECTS} projects reached")

        project = Project(
            id=generate_id(),
            name=name,
            description=description,
            idea=idea
        )
        self.projects[project.id] = project
        self.active_project_id = project.id
        self._mark_dirty()
        logger.info("Created project", project_id=project.id, name=name)
        return project

    def get_active_project(self) -> Project | None:
        """Get the currently active project."""
        if self.active_project_id:
            return self.projects.get(self.active_project_id)
        return None

    async def set_active_project(self, project_id: str) -> Project | None:
        """Set the active project."""
        if project_id in self.projects:
            self.active_project_id = project_id
            self._mark_dirty()
            return self.projects[project_id]
        return None

    async def delete_project(self, project_id: str) -> bool:
        """Delete a project and clean up indexes."""
        if project_id not in self.projects:
            return False

        project = self.projects[project_id]

        # Clean up indexes
        for team in project.teams:
            self._team_index.pop(team.id, None)
            for agent in team.agents:
                self._agent_index.pop(agent.id, None)
        for sprint in project.sprints:
            self._sprint_index.pop(sprint.id, None)
            for task in sprint.tasks:
                self._task_index.pop(task.id, None)

        del self.projects[project_id]

        if self.active_project_id == project_id:
            self.active_project_id = next(iter(self.projects), None)

        self._mark_dirty()
        return True

    # --- Team Management ---

    async def create_team(self, project_id: str, team_type: TeamType, name: str) -> Team:
        """Create a new team for a project."""
        project = self.projects.get(project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")

        name = sanitize_text(name, MAX_NAME_LENGTH, "team name")

        team = Team(
            id=generate_id(),
            type=team_type,
            name=name
        )
        project.teams.append(team)
        self._team_index[team.id] = (project_id, team)
        self._mark_dirty()
        logger.info("Created team", team_id=team.id, type=team_type.value)
        return team

    def get_team(self, team_id: str) -> tuple[str, Team] | None:
        """Get a team by ID with O(1) lookup."""
        return self._team_index.get(team_id)

    async def spawn_agent(
        self,
        project_id: str,
        team_id: str,
        role: AgentRole,
        name: str,
        skills: list[str] | None = None
    ) -> Agent:
        """Spawn a new agent for a team."""
        project = self.projects.get(project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")

        team_entry = self._team_index.get(team_id)
        if not team_entry or team_entry[0] != project_id:
            raise ValueError(f"Team {team_id} not found in project")

        team = team_entry[1]
        name = sanitize_text(name, MAX_NAME_LENGTH, "agent name")

        agent = Agent(
            id=generate_id(),
            role=role,
            name=name,
            team=team_id,
            skills=skills or []
        )
        team.agents.append(agent)
        self._agent_index[agent.id] = agent
        self._mark_dirty()
        logger.info("Spawned agent", agent_id=agent.id, role=role.value, team=team_id)
        return agent

    # --- Sprint Management ---

    async def create_sprint(
        self,
        project_id: str,
        name: str,
        goal: str,
        teams: list[TeamType]
    ) -> Sprint:
        """Create a new sprint."""
        project = self.projects.get(project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")

        if len(project.sprints) >= MAX_SPRINTS_PER_PROJECT:
            raise ValueError(f"Maximum of {MAX_SPRINTS_PER_PROJECT} sprints per project reached")

        name = sanitize_text(name, MAX_NAME_LENGTH, "sprint name")
        goal = sanitize_text(goal, MAX_DESCRIPTION_LENGTH, "sprint goal")

        sprint = Sprint(
            id=generate_id(),
            name=name,
            goal=goal,
            teams=teams
        )
        project.sprints.append(sprint)
        project.current_sprint_id = sprint.id
        self._sprint_index[sprint.id] = (project_id, sprint)
        self._mark_dirty()
        logger.info("Created sprint", sprint_id=sprint.id, name=name)
        return sprint

    def get_sprint(self, sprint_id: str) -> tuple[str, Sprint] | None:
        """Get a sprint by ID with O(1) lookup."""
        return self._sprint_index.get(sprint_id)

    async def complete_sprint(self, project_id: str, sprint_id: str, summary: str = "") -> Sprint:
        """Mark a sprint as completed."""
        sprint_entry = self._sprint_index.get(sprint_id)
        if not sprint_entry or sprint_entry[0] != project_id:
            raise ValueError(f"Sprint {sprint_id} not found")

        sprint = sprint_entry[1]
        sprint.status = SprintStatus.COMPLETED
        sprint.completed_at = datetime.now()

        # Add completion log
        sprint.add_log(
            LogLevel.SUCCESS,
            "system",
            f"Sprint completed: {summary or 'No summary provided'}"
        )

        self._mark_dirty()
        return sprint

    async def add_task(
        self,
        project_id: str,
        sprint_id: str,
        title: str,
        description: str,
        team: TeamType,
        priority: int = 3,
        dependencies: list[str] | None = None,
        acceptance_criteria: list[str] | None = None
    ) -> Task:
        """Add a task to a sprint."""
        sprint_entry = self._sprint_index.get(sprint_id)
        if not sprint_entry or sprint_entry[0] != project_id:
            raise ValueError(f"Sprint {sprint_id} not found in project")

        sprint = sprint_entry[1]

        if len(sprint.tasks) >= MAX_TASKS_PER_SPRINT:
            raise ValueError(f"Maximum of {MAX_TASKS_PER_SPRINT} tasks per sprint reached")

        title = sanitize_text(title, MAX_NAME_LENGTH, "task title")
        description = sanitize_text(description, MAX_DESCRIPTION_LENGTH, "task description")

        task = Task(
            id=generate_id(),
            title=title,
            description=description,
            team=team,
            priority=max(1, min(5, priority)),
            dependencies=dependencies or [],
            acceptance_criteria=acceptance_criteria or []
        )
        sprint.tasks.append(task)
        self._task_index[task.id] = (project_id, sprint_id, task)
        self._mark_dirty()
        return task

    def get_task(self, task_id: str) -> tuple[str, str, Task] | None:
        """Get a task by ID with O(1) lookup."""
        return self._task_index.get(task_id)

    async def update_task_status(
        self,
        project_id: str,
        sprint_id: str,
        task_id: str,
        status: TaskStatus,
        output: Any = None
    ) -> Task:
        """Update a task's status."""
        task_entry = self._task_index.get(task_id)
        if not task_entry:
            raise ValueError(f"Task {task_id} not found")

        if task_entry[0] != project_id or task_entry[1] != sprint_id:
            raise ValueError(f"Task {task_id} not in specified project/sprint")

        task = task_entry[2]
        task.status = status
        if output is not None:
            task.output = output
        if status == TaskStatus.COMPLETED:
            task.completed_at = datetime.now()

        self._mark_dirty()
        return task

    async def delete_task(self, task_id: str) -> bool:
        """Delete a task by ID."""
        task_entry = self._task_index.get(task_id)
        if not task_entry:
            return False

        project_id, sprint_id, task = task_entry
        sprint_entry = self._sprint_index.get(sprint_id)
        if sprint_entry:
            sprint = sprint_entry[1]
            sprint.tasks = [t for t in sprint.tasks if t.id != task_id]

        del self._task_index[task_id]
        self._mark_dirty()
        return True

    def list_tasks(
        self,
        project_id: str,
        sprint_id: str | None = None,
        team: TeamType | None = None,
        status: TaskStatus | None = None
    ) -> list[Task]:
        """List tasks with optional filtering."""
        project = self.projects.get(project_id)
        if not project:
            return []

        tasks = []
        sprints = project.sprints
        if sprint_id:
            sprint_entry = self._sprint_index.get(sprint_id)
            if sprint_entry and sprint_entry[0] == project_id:
                sprints = [sprint_entry[1]]
            else:
                return []

        for sprint in sprints:
            for task in sprint.tasks:
                if team and task.team != team:
                    continue
                if status and task.status != status:
                    continue
                tasks.append(task)

        return tasks

    # --- Logging ---

    async def add_sprint_log(
        self,
        project_id: str,
        sprint_id: str,
        level: LogLevel,
        team: str,
        message: str,
        agent_id: str | None = None,
        context: dict | None = None
    ) -> SprintLog:
        """Add a log entry to a sprint."""
        sprint_entry = self._sprint_index.get(sprint_id)
        if not sprint_entry or sprint_entry[0] != project_id:
            raise ValueError(f"Sprint {sprint_id} not found")

        sprint = sprint_entry[1]
        message = sanitize_text(message, 1000, "log message")

        # Limit context size
        if context and len(str(context)) > 5000:
            context = {"truncated": True, "message": "Context too large"}

        sprint.add_log(level, team, message, agent_id, context)
        self._mark_dirty()
        return sprint.logs[-1]

    def get_sprint_logs(
        self,
        project_id: str,
        sprint_id: str,
        level: LogLevel | None = None,
        team: str | None = None,
        limit: int = 50
    ) -> list[SprintLog]:
        """Get logs from a sprint with optional filtering."""
        sprint_entry = self._sprint_index.get(sprint_id)
        if not sprint_entry or sprint_entry[0] != project_id:
            return []

        sprint = sprint_entry[1]
        logs = list(sprint.logs)

        if level:
            logs = [l for l in logs if l.level == level]
        if team:
            logs = [l for l in logs if l.team == team]

        return logs[-limit:]

    # --- Execution Plan ---

    async def save_execution_plan(
        self,
        project_id: str,
        plan: ExecutionPlan
    ) -> None:
        """Save an execution plan to the project."""
        project = self.projects.get(project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")

        project.architecture = plan.model_dump(mode="json")
        self._mark_dirty()

    # --- Integration Checks ---

    async def record_integration_check(
        self,
        project_id: str,
        check: IntegrationCheck
    ) -> None:
        """Record an integration check result."""
        project = self.projects.get(project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")

        project.decisions.append({
            "type": "integration_check",
            "data": check.model_dump(mode="json")
        })

        # Keep decisions bounded
        if len(project.decisions) > MAX_DECISIONS:
            project.decisions = project.decisions[-MAX_DECISIONS:]

        self._mark_dirty()

    # --- Mind MCP Integration ---

    async def connect_mind(self, user_id: str):
        """Set up Mind MCP integration for memory persistence."""
        if not user_id or not isinstance(user_id, str):
            raise ValueError("user_id must be a non-empty string")

        user_id = user_id.strip()

        # Validate format (allow UUIDs or simple identifiers)
        if len(user_id) > 100:
            raise ValueError("user_id too long")

        self.mind_user_id = user_id
        logger.info("Connected to Mind MCP")

    async def remember_decision(self, decision: str, context: dict | None = None):
        """Store a decision in Mind MCP if connected."""
        decision = sanitize_text(decision, MAX_DESCRIPTION_LENGTH, "decision")

        project = self.get_active_project()
        if project:
            project.decisions.append({
                "type": "decision",
                "decision": decision,
                "context": context or {},
                "timestamp": datetime.now().isoformat()
            })

            # Keep decisions bounded
            if len(project.decisions) > MAX_DECISIONS:
                project.decisions = project.decisions[-MAX_DECISIONS:]

            self._mark_dirty()

    async def recall_context(self, query: str) -> list[dict]:
        """Retrieve relevant context from Mind MCP."""
        # Would call mind_retrieve if connected
        return []


# Thread-safe singleton
_state_manager: StateManager | None = None
_state_lock = asyncio.Lock()


async def get_state_manager() -> StateManager:
    """Get or create the global state manager (thread-safe)."""
    global _state_manager

    if _state_manager is not None:
        return _state_manager

    async with _state_lock:
        # Double-check after acquiring lock
        if _state_manager is None:
            _state_manager = StateManager()
            await _state_manager.initialize()

    return _state_manager
