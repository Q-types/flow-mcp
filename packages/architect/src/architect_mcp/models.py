"""
Core data models for Architect MCP.
"""

from datetime import datetime
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class AgentRole(str, Enum):
    """Roles in the agent hierarchy."""
    ARCHITECT = "architect"          # Master planner - designs overall structure
    SUPERVISOR = "supervisor"        # Monitors teams, spots issues
    EXECUTOR = "executor"            # Does the actual work
    INTEGRATOR = "integrator"        # Ensures cohesion between teams
    REVIEWER = "reviewer"            # Quality checks


class TeamType(str, Enum):
    """Types of teams that can be spawned."""
    BACKEND = "backend"
    FRONTEND = "frontend"
    DATABASE = "database"
    API = "api"
    AUTH = "auth"
    TESTING = "testing"
    DEVOPS = "devops"
    DESIGN = "design"
    DOCUMENTATION = "documentation"


class SprintStatus(str, Enum):
    """Status of a sprint."""
    PLANNING = "planning"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    COMPLETED = "completed"
    BLOCKED = "blocked"


class TaskStatus(str, Enum):
    """Status of individual tasks."""
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    FAILED = "failed"


class LogLevel(str, Enum):
    """Log levels for sprint tracking."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    SUCCESS = "success"
    DECISION = "decision"


# --- Core Models ---

class Agent(BaseModel):
    """Represents an agent in the system."""
    id: str
    role: AgentRole
    name: str
    team: str | None = None
    skills: list[str] = Field(default_factory=list)
    status: str = "idle"
    current_task: str | None = None
    created_at: datetime = Field(default_factory=datetime.now)


class Task(BaseModel):
    """A discrete unit of work."""
    id: str
    title: str
    description: str
    team: TeamType
    assigned_to: str | None = None
    status: TaskStatus = TaskStatus.PENDING
    priority: int = Field(default=3, ge=1, le=5)  # 1=highest
    dependencies: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    acceptance_criteria: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    completed_at: datetime | None = None
    output: Any = None


class SprintLog(BaseModel):
    """Compact log entry for sprint tracking."""
    timestamp: datetime = Field(default_factory=datetime.now)
    level: LogLevel
    team: str
    agent_id: str | None = None
    message: str
    context: dict[str, Any] = Field(default_factory=dict)


class Sprint(BaseModel):
    """A sprint containing tasks for teams."""
    id: str
    name: str
    goal: str
    status: SprintStatus = SprintStatus.PLANNING
    teams: list[TeamType] = Field(default_factory=list)
    tasks: list[Task] = Field(default_factory=list)
    logs: list[SprintLog] = Field(default_factory=list, max_length=100)  # Keep logs compact
    started_at: datetime | None = None
    completed_at: datetime | None = None

    def add_log(self, level: LogLevel, team: str, message: str,
                agent_id: str | None = None, context: dict | None = None):
        """Add a log entry, keeping the log compact."""
        log = SprintLog(
            level=level,
            team=team,
            agent_id=agent_id,
            message=message,
            context=context or {}
        )
        self.logs.append(log)
        # Keep only last 100 logs per sprint
        if len(self.logs) > 100:
            self.logs = self.logs[-100:]


class Team(BaseModel):
    """A team of agents working on a domain."""
    id: str
    type: TeamType
    name: str
    agents: list[Agent] = Field(default_factory=list)
    current_sprint: str | None = None
    supervisor_id: str | None = None


class Project(BaseModel):
    """The overall project being built."""
    id: str
    name: str
    description: str
    idea: str  # The original idea from the user
    teams: list[Team] = Field(default_factory=list)
    sprints: list[Sprint] = Field(default_factory=list)
    current_sprint_id: str | None = None
    architecture: dict[str, Any] = Field(default_factory=dict)
    decisions: list[dict[str, Any]] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)


class IntegrationCheck(BaseModel):
    """Result of checking integration between teams."""
    teams_checked: list[str]
    compatible: bool
    issues: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    checked_at: datetime = Field(default_factory=datetime.now)


class ExecutionPlan(BaseModel):
    """The master execution plan from the Architect."""
    project_id: str
    phases: list[dict[str, Any]]
    team_structure: dict[str, Any]
    dependencies: dict[str, list[str]]
    estimated_sprints: int
    critical_path: list[str]
    risks: list[dict[str, Any]] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
