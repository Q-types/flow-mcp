"""
Agent Orchestrator for Architect MCP.

Implements the hierarchical agent system:
- Architect: Master planner, designs overall structure
- Supervisors: Monitor teams, spot issues early
- Executors: Do the actual work
- Integrators: Ensure cohesion between teams

Coordinates with:
- IdeaRalph: Idea validation, PRD, design
- Spawner: Skill discovery and loading
- Mind: Memory and learning
"""

from datetime import datetime
from typing import Any

import structlog

from .models import (
    Agent, AgentRole, Team, TeamType, Sprint, Task,
    SprintStatus, TaskStatus, LogLevel, ExecutionPlan, IntegrationCheck
)
from .state import StateManager

logger = structlog.get_logger()


# Integration instances (lazy loaded)
_idearalph = None
_spawner = None
_mind = None


def get_idearalph():
    """Get or create IdeaRalph integration."""
    global _idearalph
    if _idearalph is None:
        from .integrations import IdeaRalphIntegration
        _idearalph = IdeaRalphIntegration()
    return _idearalph


def get_spawner():
    """Get or create Spawner integration."""
    global _spawner
    if _spawner is None:
        from .integrations import SpawnerIntegration
        _spawner = SpawnerIntegration()
    return _spawner


def get_mind():
    """Get or create Mind integration."""
    global _mind
    if _mind is None:
        from .integrations import MindIntegration
        _mind = MindIntegration()
    return _mind


class AgentOrchestrator:
    """
    Orchestrates the multi-agent system for project execution.

    Architecture:

        ┌─────────────────────────────────────────────────────────────────┐
        │                       THE ARCHITECT                              │
        │   (Master Planner - Designs structure, plans phases, monitors)   │
        └─────────────────────────────────────────────────────────────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    │                 │                 │
               ┌────▼────┐       ┌────▼────┐       ┌────▼────┐
               │SUPERVISOR│       │SUPERVISOR│       │SUPERVISOR│
               │ Backend  │       │ Frontend │       │   API    │
               └────┬─────┘       └────┬─────┘       └────┬─────┘
                    │                  │                  │
               ┌────▼────┐       ┌────▼────┐       ┌────▼────┐
               │EXECUTORS│       │EXECUTORS│       │EXECUTORS│
               │  Team   │       │  Team   │       │  Team   │
               └─────────┘       └─────────┘       └─────────┘
                    │                  │                  │
                    └──────────────────┼──────────────────┘
                                       │
                              ┌────────▼────────┐
                              │   INTEGRATOR    │
                              │ (Ensures teams  │
                              │  work together) │
                              └─────────────────┘
    """

    def __init__(self, state: StateManager):
        self.state = state

    async def plan_project(self, idea: str) -> ExecutionPlan:
        """
        The Architect analyzes the idea and creates an execution plan.

        This is the core planning function that:
        1. Analyzes the idea to understand scope
        2. Identifies required teams and their responsibilities
        3. Defines phases and dependencies
        4. Creates the critical path
        5. Identifies risks
        """
        project = self.state.get_active_project()
        if not project:
            raise ValueError("No active project")

        # Analyze idea to determine required teams
        teams_needed = self._analyze_required_teams(idea)

        # Define phases based on complexity
        phases = self._define_phases(idea, teams_needed)

        # Calculate dependencies between teams
        dependencies = self._calculate_dependencies(teams_needed, phases)

        # Identify critical path
        critical_path = self._identify_critical_path(phases, dependencies)

        # Assess risks
        risks = self._assess_risks(idea, teams_needed, phases)

        plan = ExecutionPlan(
            project_id=project.id,
            phases=phases,
            team_structure={
                "teams": [t.value for t in teams_needed],
                "hierarchy": "architect -> supervisors -> executors + integrator"
            },
            dependencies=dependencies,
            estimated_sprints=len(phases),
            critical_path=critical_path,
            risks=risks
        )

        await self.state.save_execution_plan(project.id, plan)
        logger.info("Created execution plan",
                   phases=len(phases),
                   teams=len(teams_needed))
        return plan

    def _analyze_required_teams(self, idea: str) -> list[TeamType]:
        """Analyze idea to determine which teams are needed."""
        idea_lower = idea.lower()
        teams = []

        # Always need these for any software project
        teams.append(TeamType.BACKEND)
        teams.append(TeamType.DATABASE)

        # Frontend if it's a user-facing app
        if any(w in idea_lower for w in ["app", "web", "ui", "frontend", "user", "dashboard"]):
            teams.append(TeamType.FRONTEND)
            teams.append(TeamType.DESIGN)

        # API if there's integration
        if any(w in idea_lower for w in ["api", "integration", "service", "endpoint"]):
            teams.append(TeamType.API)

        # Auth if there's user management
        if any(w in idea_lower for w in ["auth", "login", "user", "account", "permission"]):
            teams.append(TeamType.AUTH)

        # Always include testing and docs
        teams.append(TeamType.TESTING)
        teams.append(TeamType.DOCUMENTATION)

        return list(set(teams))

    def _define_phases(self, idea: str, teams: list[TeamType]) -> list[dict]:
        """Define execution phases based on idea and teams."""
        phases = [
            {
                "id": "phase-1",
                "name": "Foundation",
                "goal": "Set up project structure, database schema, core models",
                "teams": [TeamType.DATABASE.value, TeamType.BACKEND.value],
                "tasks": [
                    "Define data models",
                    "Create database schema",
                    "Set up project structure",
                    "Configure development environment"
                ]
            },
            {
                "id": "phase-2",
                "name": "Core Backend",
                "goal": "Implement core business logic and API",
                "teams": [TeamType.BACKEND.value, TeamType.API.value],
                "tasks": [
                    "Implement core services",
                    "Create API endpoints",
                    "Add validation and error handling",
                    "Write unit tests"
                ]
            }
        ]

        if TeamType.AUTH in teams:
            phases.append({
                "id": "phase-3",
                "name": "Authentication",
                "goal": "Implement authentication and authorization",
                "teams": [TeamType.AUTH.value],
                "tasks": [
                    "Set up auth provider",
                    "Implement login/signup flows",
                    "Add role-based access control",
                    "Secure endpoints"
                ]
            })

        if TeamType.FRONTEND in teams:
            phases.append({
                "id": "phase-4",
                "name": "Frontend",
                "goal": "Build user interface",
                "teams": [TeamType.FRONTEND.value, TeamType.DESIGN.value],
                "tasks": [
                    "Set up frontend framework",
                    "Create component library",
                    "Implement pages and flows",
                    "Connect to API"
                ]
            })

        phases.append({
            "id": "phase-final",
            "name": "Integration & Polish",
            "goal": "Integrate all components, test, and polish",
            "teams": [t.value for t in teams],
            "tasks": [
                "Integration testing",
                "Performance optimization",
                "Documentation",
                "Deployment preparation"
            ]
        })

        return phases

    def _calculate_dependencies(
        self,
        teams: list[TeamType],
        phases: list[dict]
    ) -> dict[str, list[str]]:
        """Calculate dependencies between teams and phases."""
        deps: dict[str, list[str]] = {}

        # Database must come first
        deps[TeamType.DATABASE.value] = []

        # Backend depends on database
        deps[TeamType.BACKEND.value] = [TeamType.DATABASE.value]

        # API depends on backend
        if TeamType.API in teams:
            deps[TeamType.API.value] = [TeamType.BACKEND.value]

        # Auth depends on backend
        if TeamType.AUTH in teams:
            deps[TeamType.AUTH.value] = [TeamType.BACKEND.value]

        # Frontend depends on API and Auth
        if TeamType.FRONTEND in teams:
            frontend_deps = [TeamType.API.value] if TeamType.API in teams else [TeamType.BACKEND.value]
            if TeamType.AUTH in teams:
                frontend_deps.append(TeamType.AUTH.value)
            deps[TeamType.FRONTEND.value] = frontend_deps

        # Testing depends on everything
        if TeamType.TESTING in teams:
            deps[TeamType.TESTING.value] = [t.value for t in teams if t != TeamType.TESTING]

        return deps

    def _identify_critical_path(
        self,
        phases: list[dict],
        dependencies: dict[str, list[str]]
    ) -> list[str]:
        """Identify the critical path through the project."""
        # Simple critical path: database -> backend -> api -> frontend -> testing
        path = ["database", "backend"]
        if "api" in dependencies:
            path.append("api")
        if "frontend" in dependencies:
            path.append("frontend")
        path.append("testing")
        return path

    def _assess_risks(
        self,
        idea: str,
        teams: list[TeamType],
        phases: list[dict]
    ) -> list[dict]:
        """Assess risks for the project."""
        risks = []

        # Complexity risk
        if len(teams) > 5:
            risks.append({
                "type": "complexity",
                "severity": "medium",
                "description": "Many teams increases coordination overhead",
                "mitigation": "Regular integration checks, clear interfaces"
            })

        # Integration risk
        if TeamType.FRONTEND in teams and TeamType.API in teams:
            risks.append({
                "type": "integration",
                "severity": "medium",
                "description": "Frontend-API contract must be maintained",
                "mitigation": "Define API contracts early, use TypeScript types"
            })

        # Auth risk
        if TeamType.AUTH in teams:
            risks.append({
                "type": "security",
                "severity": "high",
                "description": "Authentication must be implemented securely",
                "mitigation": "Use established auth providers, security review"
            })

        return risks

    async def spawn_team_structure(self, project_id: str) -> dict[str, Any]:
        """
        Spawn the complete agent team structure for a project.

        Creates:
        - One Architect (already implicit)
        - One Supervisor per team
        - 2-3 Executors per team
        - One Integrator for the project
        """
        project = self.state.projects.get(project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")

        plan = project.architecture
        if not plan:
            raise ValueError("No execution plan found. Run plan_project first.")

        teams_created = []
        agents_spawned = []

        team_types = [TeamType(t) for t in plan.get("team_structure", {}).get("teams", [])]

        for team_type in team_types:
            # Create the team
            team = await self.state.create_team(
                project_id,
                team_type,
                f"{team_type.value.title()} Team"
            )
            teams_created.append(team)

            # Spawn supervisor
            supervisor = await self.state.spawn_agent(
                project_id,
                team.id,
                AgentRole.SUPERVISOR,
                f"{team_type.value.title()} Supervisor",
                skills=["monitoring", "review", "coordination", team_type.value]
            )
            team.supervisor_id = supervisor.id
            agents_spawned.append(supervisor)

            # Spawn executors (2-3 per team)
            num_executors = 2 if team_type in [TeamType.DOCUMENTATION, TeamType.TESTING] else 3
            for i in range(num_executors):
                executor = await self.state.spawn_agent(
                    project_id,
                    team.id,
                    AgentRole.EXECUTOR,
                    f"{team_type.value.title()} Dev {i+1}",
                    skills=[team_type.value, "implementation", "coding"]
                )
                agents_spawned.append(executor)

        # Spawn the integrator (project-level)
        # Create a special "integration" team
        integration_team = await self.state.create_team(
            project_id,
            TeamType.TESTING,  # Closest type
            "Integration Team"
        )

        integrator = await self.state.spawn_agent(
            project_id,
            integration_team.id,
            AgentRole.INTEGRATOR,
            "Project Integrator",
            skills=["integration", "compatibility", "architecture", "review"]
        )
        agents_spawned.append(integrator)

        logger.info(
            "Spawned team structure",
            teams=len(teams_created),
            agents=len(agents_spawned)
        )

        return {
            "teams": [t.model_dump() for t in teams_created],
            "agents": [a.model_dump() for a in agents_spawned],
            "structure": {
                "total_teams": len(teams_created),
                "total_agents": len(agents_spawned),
                "supervisors": len(team_types),
                "executors": sum(2 if t in [TeamType.DOCUMENTATION, TeamType.TESTING] else 3 for t in team_types),
                "integrators": 1
            }
        }

    async def check_integration(self, project_id: str) -> IntegrationCheck:
        """
        The Integrator checks for compatibility issues between teams.

        This runs periodically to:
        1. Check API contracts match
        2. Verify data model consistency
        3. Spot potential conflicts
        4. Suggest solutions
        """
        project = self.state.projects.get(project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")

        teams_checked = [t.name for t in project.teams]
        issues = []
        suggestions = []

        # Check for common integration issues
        current_sprint = next(
            (s for s in project.sprints if s.id == project.current_sprint_id),
            None
        )

        if current_sprint:
            # Check for blocked tasks
            blocked_tasks = [t for t in current_sprint.tasks if t.status == TaskStatus.BLOCKED]
            if blocked_tasks:
                for task in blocked_tasks:
                    issues.append(f"Task '{task.title}' is blocked: {', '.join(task.blockers)}")

            # Check for dependency issues
            completed_tasks = {t.id for t in current_sprint.tasks if t.status == TaskStatus.COMPLETED}
            for task in current_sprint.tasks:
                if task.status == TaskStatus.PENDING:
                    unmet_deps = [d for d in task.dependencies if d not in completed_tasks]
                    if unmet_deps:
                        suggestions.append(
                            f"Task '{task.title}' waiting on: {', '.join(unmet_deps)}"
                        )

        # Check team coordination
        if len(project.teams) > 1:
            # Ensure each team has a supervisor
            teams_without_supervisor = [t for t in project.teams if not t.supervisor_id]
            if teams_without_supervisor:
                issues.append(
                    f"Teams without supervisor: {', '.join(t.name for t in teams_without_supervisor)}"
                )
                suggestions.append("Assign supervisors to all teams for proper monitoring")

        compatible = len(issues) == 0

        check = IntegrationCheck(
            teams_checked=teams_checked,
            compatible=compatible,
            issues=issues,
            suggestions=suggestions
        )

        await self.state.record_integration_check(project_id, check)

        # Log the check
        if current_sprint:
            await self.state.add_sprint_log(
                project_id,
                current_sprint.id,
                LogLevel.INFO if compatible else LogLevel.WARNING,
                "integrator",
                f"Integration check: {'PASS' if compatible else 'ISSUES FOUND'}",
                context={"issues": issues, "suggestions": suggestions}
            )

        return check

    async def supervisor_review(
        self,
        project_id: str,
        team_id: str
    ) -> dict[str, Any]:
        """
        Supervisor reviews their team's progress.

        Checks:
        - Task completion rate
        - Blockers
        - Quality issues
        - Team velocity
        """
        project = self.state.projects.get(project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")

        team = next((t for t in project.teams if t.id == team_id), None)
        if not team:
            raise ValueError(f"Team {team_id} not found")

        current_sprint = next(
            (s for s in project.sprints if s.id == project.current_sprint_id),
            None
        )

        if not current_sprint:
            return {"status": "no_active_sprint", "team": team.name}

        # Get team's tasks
        team_tasks = [t for t in current_sprint.tasks if t.team == team.type]

        completed = len([t for t in team_tasks if t.status == TaskStatus.COMPLETED])
        in_progress = len([t for t in team_tasks if t.status == TaskStatus.IN_PROGRESS])
        blocked = len([t for t in team_tasks if t.status == TaskStatus.BLOCKED])
        pending = len([t for t in team_tasks if t.status == TaskStatus.PENDING])

        total = len(team_tasks)
        completion_rate = (completed / total * 100) if total > 0 else 0

        # Identify issues
        issues = []
        if blocked > 0:
            blocked_tasks = [t for t in team_tasks if t.status == TaskStatus.BLOCKED]
            issues.extend([f"Blocked: {t.title}" for t in blocked_tasks])

        # Generate recommendations
        recommendations = []
        if completion_rate < 50 and in_progress == 0:
            recommendations.append("Team may be stuck - consider unblocking or reassigning")
        if blocked > completed:
            recommendations.append("Many blocked tasks - prioritize unblocking")

        review = {
            "team": team.name,
            "team_type": team.type.value,
            "sprint": current_sprint.name,
            "stats": {
                "total_tasks": total,
                "completed": completed,
                "in_progress": in_progress,
                "blocked": blocked,
                "pending": pending,
                "completion_rate": f"{completion_rate:.1f}%"
            },
            "issues": issues,
            "recommendations": recommendations,
            "status": "healthy" if completion_rate >= 50 and blocked == 0 else "needs_attention"
        }

        # Log the review
        await self.state.add_sprint_log(
            project_id,
            current_sprint.id,
            LogLevel.INFO if review["status"] == "healthy" else LogLevel.WARNING,
            team.type.value,
            f"Supervisor review: {review['status']} ({completion_rate:.0f}% complete)",
            agent_id=team.supervisor_id,
            context={"stats": review["stats"]}
        )

        return review

    async def get_project_status(self, project_id: str) -> dict[str, Any]:
        """Get comprehensive project status for the Architect's overview."""
        project = self.state.projects.get(project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")

        current_sprint = next(
            (s for s in project.sprints if s.id == project.current_sprint_id),
            None
        )

        # Team summaries
        team_summaries = []
        for team in project.teams:
            agent_count = len(team.agents)
            has_supervisor = team.supervisor_id is not None
            team_summaries.append({
                "name": team.name,
                "type": team.type.value,
                "agents": agent_count,
                "supervised": has_supervisor
            })

        # Sprint progress
        sprint_progress = None
        if current_sprint:
            total_tasks = len(current_sprint.tasks)
            completed = len([t for t in current_sprint.tasks if t.status == TaskStatus.COMPLETED])
            sprint_progress = {
                "name": current_sprint.name,
                "goal": current_sprint.goal,
                "status": current_sprint.status.value,
                "progress": f"{completed}/{total_tasks} tasks",
                "percentage": (completed / total_tasks * 100) if total_tasks > 0 else 0
            }

        # Recent logs (last 10)
        recent_logs = []
        if current_sprint:
            for log in current_sprint.logs[-10:]:
                recent_logs.append({
                    "time": log.timestamp.strftime("%H:%M"),
                    "level": log.level.value,
                    "team": log.team,
                    "message": log.message
                })

        return {
            "project": {
                "id": project.id,
                "name": project.name,
                "description": project.description
            },
            "teams": team_summaries,
            "current_sprint": sprint_progress,
            "recent_activity": recent_logs,
            "total_sprints": len(project.sprints),
            "decisions_made": len(project.decisions)
        }

    # --- ENHANCED ORCHESTRATION WITH INTEGRATIONS ---

    async def plan_with_context(
        self,
        idea: str,
        prd_content: dict[str, Any] | None = None
    ) -> ExecutionPlan:
        """
        Enhanced planning that uses Mind context and Spawner skills.

        This improves on plan_project by:
        1. Retrieving relevant past context from Mind
        2. Using PRD content to inform team selection
        3. Loading appropriate Spawner skills
        4. Storing the planning decision in Mind
        """
        project = self.state.get_active_project()
        if not project:
            raise ValueError("No active project")

        # Get Mind context
        mind = get_mind()
        if self.state.mind_user_id:
            mind.set_user_id(self.state.mind_user_id)

        context = await mind.get_relevant_context(
            project_idea=idea,
            project_type=self._detect_project_type(idea)
        )

        logger.info(
            "Retrieved context for planning",
            memories=len(context.memories)
        )

        # Analyze idea with PRD context
        teams_needed = self._analyze_required_teams(idea)

        # Enhance team selection based on PRD
        if prd_content:
            if prd_content.get("technical_requirements"):
                # Add teams based on technical requirements
                tech_reqs = str(prd_content.get("technical_requirements", "")).lower()
                if "realtime" in tech_reqs or "websocket" in tech_reqs:
                    if TeamType.BACKEND not in teams_needed:
                        teams_needed.append(TeamType.BACKEND)
                if "ai" in tech_reqs or "llm" in tech_reqs or "ml" in tech_reqs:
                    # AI projects need strong backend
                    if TeamType.API not in teams_needed:
                        teams_needed.append(TeamType.API)

        # Load Spawner skills for each team
        spawner = get_spawner()
        loaded_skills: dict[str, list[str]] = {}

        for team_type in teams_needed:
            skills = await spawner.get_skills_for_team(team_type)
            loaded_skills[team_type.value] = [s.id for s in skills]

        # Create the plan
        phases = self._define_phases(idea, teams_needed)
        dependencies = self._calculate_dependencies(teams_needed, phases)
        critical_path = self._identify_critical_path(phases, dependencies)
        risks = self._assess_risks(idea, teams_needed, phases)

        plan = ExecutionPlan(
            project_id=project.id,
            phases=phases,
            team_structure={
                "teams": [t.value for t in teams_needed],
                "skills": loaded_skills,
                "hierarchy": "architect -> supervisors -> executors + integrator"
            },
            dependencies=dependencies,
            estimated_sprints=len(phases),
            critical_path=critical_path,
            risks=risks
        )

        await self.state.save_execution_plan(project.id, plan)

        # Store planning decision in Mind
        await mind.remember_project_decision(
            project_name=project.name,
            decision=f"Selected teams: {', '.join(t.value for t in teams_needed)}",
            reason=f"Based on idea analysis and {len(context.memories)} past lessons"
        )

        logger.info(
            "Created enhanced execution plan",
            phases=len(phases),
            teams=len(teams_needed),
            skills_loaded=sum(len(s) for s in loaded_skills.values())
        )

        return plan

    async def spawn_teams_with_skills(self, project_id: str) -> dict[str, Any]:
        """
        Spawn teams AND load relevant skills from Spawner.

        Enhances spawn_team_structure by:
        1. Loading Spawner skills for each team
        2. Assigning skill-based attributes to agents
        3. Getting gotchas before teams start
        """
        project = self.state.projects.get(project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")

        plan = project.architecture
        if not plan:
            raise ValueError("No execution plan found. Run plan_project first.")

        # First spawn the basic structure
        result = await self.spawn_team_structure(project_id)

        # Now enhance with Spawner skills
        spawner = get_spawner()

        team_types = [TeamType(t) for t in plan.get("team_structure", {}).get("teams", [])]
        skills_loaded: dict[str, list[str]] = {}

        for team_type in team_types:
            skill_results = await spawner.load_skills_for_team(team_type)
            skills_loaded[team_type.value] = [
                r.skill_id for r in skill_results if r.success
            ]

        # Get gotchas for the detected stack
        detected_stack = self._detect_tech_stack(project.idea)
        gotchas = await spawner.get_gotchas(
            stack=detected_stack,
            situation=f"Starting project: {project.name}"
        )

        result["skills_loaded"] = skills_loaded
        result["gotchas"] = {
            "stack": detected_stack,
            "warnings": gotchas.gotchas[:5],  # Top 5 warnings
            "total": len(gotchas.gotchas)
        }

        logger.info(
            "Spawned teams with skills",
            teams=len(team_types),
            total_skills=sum(len(s) for s in skills_loaded.values()),
            gotchas=len(gotchas.gotchas)
        )

        return result

    async def complete_sprint_with_learning(
        self,
        project_id: str,
        sprint_id: str,
        summary: str,
        success: bool = True
    ) -> dict[str, Any]:
        """
        Complete a sprint AND record the outcome in Mind for learning.

        This creates a feedback loop that helps the Architect
        make better decisions in future projects.
        """
        project = self.state.projects.get(project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")

        sprint_entry = self.state.get_sprint(sprint_id)
        if not sprint_entry:
            raise ValueError(f"Sprint {sprint_id} not found")

        _, sprint = sprint_entry

        # Complete the sprint in state
        completed_sprint = await self.state.complete_sprint(
            project_id, sprint_id, summary
        )

        # Calculate sprint metrics
        total_tasks = len(sprint.tasks)
        completed_tasks = len([t for t in sprint.tasks if t.status == TaskStatus.COMPLETED])
        blocked_tasks = len([t for t in sprint.tasks if t.status == TaskStatus.BLOCKED])

        # Record in Mind
        mind = get_mind()
        if self.state.mind_user_id:
            mind.set_user_id(self.state.mind_user_id)

        # Store sprint outcome
        await mind.remember_sprint_outcome(
            project_name=project.name,
            sprint_name=sprint.name,
            outcome=f"{'Success' if success else 'Partial'}: {completed_tasks}/{total_tasks} tasks, {blocked_tasks} blocked. {summary}"
        )

        # If we have a retrieval context from planning, learn from it
        outcome_quality = 0.8 if success and blocked_tasks == 0 else 0.3 if success else -0.3

        await mind.record_decision(
            memory_ids=[],  # Would need to track retrieval IDs
            decision_summary=f"Sprint {sprint.name} planning decisions",
            outcome_quality=outcome_quality,
            outcome_signal="task_completed" if success else "agent_feedback"
        )

        logger.info(
            "Completed sprint with learning",
            sprint=sprint.name,
            success=success,
            completion_rate=completed_tasks / total_tasks if total_tasks > 0 else 0
        )

        return {
            "sprint": {
                "id": completed_sprint.id,
                "name": completed_sprint.name,
                "status": completed_sprint.status.value
            },
            "metrics": {
                "total_tasks": total_tasks,
                "completed": completed_tasks,
                "blocked": blocked_tasks,
                "completion_rate": f"{(completed_tasks/total_tasks*100):.1f}%" if total_tasks > 0 else "N/A"
            },
            "learning_recorded": True
        }

    def _detect_project_type(self, idea: str) -> str | None:
        """Detect project type from idea text."""
        idea_lower = idea.lower()

        if any(w in idea_lower for w in ["saas", "subscription", "b2b"]):
            return "saas"
        if any(w in idea_lower for w in ["marketplace", "buy", "sell", "listing"]):
            return "marketplace"
        if any(w in idea_lower for w in ["ai", "llm", "gpt", "chatbot", "ml"]):
            return "ai-app"
        if any(w in idea_lower for w in ["web3", "blockchain", "nft", "crypto"]):
            return "web3"
        if any(w in idea_lower for w in ["cli", "tool", "utility"]):
            return "tool"

        return None

    def _detect_tech_stack(self, idea: str) -> list[str]:
        """Detect likely tech stack from idea."""
        idea_lower = idea.lower()
        stack = []

        # Framework detection
        if any(w in idea_lower for w in ["next", "nextjs", "vercel", "web app"]):
            stack.extend(["nextjs", "react"])
        elif any(w in idea_lower for w in ["svelte", "sveltekit"]):
            stack.extend(["sveltekit", "svelte"])
        else:
            stack.extend(["nextjs", "react"])  # Default

        # Database detection
        if any(w in idea_lower for w in ["supabase"]):
            stack.append("supabase")
        elif any(w in idea_lower for w in ["firebase"]):
            stack.append("firebase")
        else:
            stack.append("supabase")  # Default

        # Always include TypeScript
        stack.append("typescript")

        # Auth detection
        if any(w in idea_lower for w in ["auth", "login", "user"]):
            stack.append("auth")

        # AI detection
        if any(w in idea_lower for w in ["ai", "llm", "gpt", "openai"]):
            stack.append("openai")

        return list(set(stack))
