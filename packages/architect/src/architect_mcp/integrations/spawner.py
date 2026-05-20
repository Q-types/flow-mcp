"""
Spawner MCP Integration for intelligent agent generation.

Enables Architect to:
- Dynamically discover and load relevant skills for teams
- Generate agents with appropriate expertise
- Get gotchas and sharp edges for the tech stack
- Validate code against best practices

Spawner acts as the "hiring/talent" arm of the Architect system,
providing the right specialist skills for each team and task.
"""

from typing import Any, Callable, Awaitable
from dataclasses import dataclass, field
import structlog

from ..models import TeamType, AgentRole

logger = structlog.get_logger()


# Type alias for MCP tool caller
MCPCaller = Callable[[str, Any], Awaitable[dict[str, Any]]]


@dataclass
class Skill:
    """A Spawner skill with metadata."""
    id: str
    name: str
    description: str = ""
    tags: list[str] = field(default_factory=list)
    layer: int = 1
    loaded: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "tags": self.tags,
            "layer": self.layer,
            "loaded": self.loaded
        }


@dataclass
class SkillLoadResult:
    """Result from loading a skill."""
    skill_id: str
    success: bool
    content: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


@dataclass
class ValidationResult:
    """Result from code validation."""
    valid: bool
    issues: list[dict[str, Any]] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)


@dataclass
class GotchaResult:
    """Sharp edges and gotchas for a tech stack."""
    stack: list[str]
    gotchas: list[dict[str, Any]] = field(default_factory=list)


class SpawnerIntegration:
    """
    Integration with Spawner MCP for intelligent agent generation.

    Spawner provides:
    - spawner_skills: Search/list/load specialist skills
    - spawner_load: Load project context and skills
    - spawner_watch_out: Get gotchas for tech stack
    - spawner_validate: Run code quality checks
    - spawner_orchestrate: Project initialization

    The Architect uses Spawner to:
    1. Discover skills needed for each team type
    2. Load skills before assigning tasks
    3. Get warnings about common pitfalls
    4. Validate code output quality
    """

    def __init__(self):
        self.loaded_skills: dict[str, Skill] = {}
        self.project_context: dict[str, Any] = {}
        self.mcp_caller: MCPCaller | None = None
        self._skill_cache: dict[str, list[Skill]] = {}

    def set_mcp_caller(self, caller: MCPCaller) -> None:
        """Set the MCP tool caller for real integrations."""
        self.mcp_caller = caller
        logger.info("Spawner MCP caller configured")

    async def search_skills(
        self,
        query: str,
        tag: str | None = None,
        limit: int = 10
    ) -> list[Skill]:
        """
        Search for skills matching a query.

        This dynamically discovers skills from Spawner's skill library
        instead of using hardcoded mappings.

        Args:
            query: Search query
            tag: Optional tag filter
            limit: Maximum results

        Returns:
            List of matching skills
        """
        logger.info("Searching Spawner skills", query=query, tag=tag)

        if self.mcp_caller:
            try:
                params: dict[str, Any] = {
                    "action": "search",
                    "query": query
                }
                if tag:
                    params["tag"] = tag

                result = await self.mcp_caller("spawner_skills", params)

                skills = []
                for skill_data in result.get("skills", [])[:limit]:
                    skill = Skill(
                        id=skill_data.get("id", ""),
                        name=skill_data.get("name", ""),
                        description=skill_data.get("description", ""),
                        tags=skill_data.get("tags", []),
                        layer=skill_data.get("layer", 1)
                    )
                    skills.append(skill)

                return skills
            except Exception as e:
                logger.warning("Spawner skills search failed", error=str(e))

        # Fallback: Return empty (will use static mapping)
        return []

    async def get_skills_for_team(self, team_type: TeamType) -> list[Skill]:
        """
        Get appropriate skills for a team type.

        First tries dynamic discovery via Spawner, then falls back
        to static mappings if MCP is unavailable.

        Args:
            team_type: The type of team

        Returns:
            List of relevant skills
        """
        # Check cache first
        cache_key = team_type.value
        if cache_key in self._skill_cache:
            return self._skill_cache[cache_key]

        # Try dynamic discovery
        if self.mcp_caller:
            # Search by team type as query and tag
            skills = await self.search_skills(
                query=team_type.value,
                tag=team_type.value
            )
            if skills:
                self._skill_cache[cache_key] = skills
                logger.info(
                    "Discovered skills for team",
                    team=team_type.value,
                    skills=[s.id for s in skills]
                )
                return skills

        # Fallback: Static mapping
        skill_mapping = {
            TeamType.BACKEND: [
                Skill("backend", "Backend Engineering", tags=["api", "server"]),
                Skill("supabase-backend", "Supabase Backend", tags=["supabase", "database"]),
                Skill("typescript-strict", "TypeScript Strict Mode", tags=["typescript"]),
                Skill("api-design", "API Design", tags=["api", "rest"])
            ],
            TeamType.FRONTEND: [
                Skill("frontend", "Frontend Engineering", tags=["ui", "react"]),
                Skill("react-patterns", "React Patterns", tags=["react"]),
                Skill("tailwind-ui", "Tailwind UI", tags=["css", "tailwind"]),
                Skill("nextjs-app-router", "Next.js App Router", tags=["nextjs"])
            ],
            TeamType.DATABASE: [
                Skill("supabase-backend", "Supabase Backend", tags=["supabase"]),
                Skill("postgres-wizard", "PostgreSQL Wizard", tags=["postgres", "sql"]),
                Skill("database-architect", "Database Architect", tags=["schema"])
            ],
            TeamType.API: [
                Skill("api-design", "API Design", tags=["api"]),
                Skill("api-designer", "API Designer", tags=["openapi"]),
                Skill("typescript-strict", "TypeScript Strict Mode", tags=["typescript"])
            ],
            TeamType.AUTH: [
                Skill("nextjs-supabase-auth", "Next.js Supabase Auth", tags=["auth"]),
                Skill("auth-specialist", "Auth Specialist", tags=["auth", "security"]),
                Skill("security-audit", "Security Audit", tags=["security"])
            ],
            TeamType.TESTING: [
                Skill("test-architect", "Test Architect", tags=["testing"]),
                Skill("qa-engineering", "QA Engineering", tags=["qa"]),
                Skill("testing-automation", "Testing Automation", tags=["automation"])
            ],
            TeamType.DEVOPS: [
                Skill("devops", "DevOps Engineering", tags=["devops"]),
                Skill("ci-cd", "CI/CD Pipeline", tags=["ci", "cd"]),
                Skill("docker-specialist", "Docker Specialist", tags=["docker"])
            ],
            TeamType.DESIGN: [
                Skill("ui-design", "UI Design", tags=["ui"]),
                Skill("ux-design", "UX Design", tags=["ux"]),
                Skill("tailwind-ui", "Tailwind UI", tags=["css"])
            ],
            TeamType.DOCUMENTATION: [
                Skill("documentation-engineer", "Documentation Engineer", tags=["docs"]),
                Skill("technical-writer", "Technical Writer", tags=["writing"]),
                Skill("developer-communications", "Developer Communications", tags=["devrel"])
            ]
        }

        skills = skill_mapping.get(team_type, [])
        self._skill_cache[cache_key] = skills

        logger.info(
            "Using static skills for team",
            team=team_type.value,
            skills=[s.id for s in skills]
        )
        return skills

    async def load_skill(
        self,
        skill_id: str,
        context: str | None = None
    ) -> SkillLoadResult:
        """
        Load a specific skill via Spawner.

        This actually loads the skill content so it can be used
        to inform agent behavior.

        Args:
            skill_id: The skill ID to load
            context: Optional context about what's being built

        Returns:
            SkillLoadResult with skill content or error
        """
        logger.info("Loading skill", skill_id=skill_id)

        if self.mcp_caller:
            try:
                params: dict[str, Any] = {"skill_id": skill_id}
                if context:
                    params["context"] = context

                result = await self.mcp_caller("spawner_load", params)

                if result.get("success") or result.get("skill"):
                    skill = Skill(
                        id=skill_id,
                        name=result.get("skill", {}).get("name", skill_id),
                        loaded=True
                    )
                    self.loaded_skills[skill_id] = skill

                    return SkillLoadResult(
                        skill_id=skill_id,
                        success=True,
                        content=result.get("skill", {})
                    )
            except Exception as e:
                logger.warning("Spawner load skill failed", skill_id=skill_id, error=str(e))

        # Fallback: Mark as "loaded" locally
        skill = Skill(id=skill_id, name=skill_id, loaded=True)
        self.loaded_skills[skill_id] = skill

        return SkillLoadResult(
            skill_id=skill_id,
            success=True,
            content={"id": skill_id, "local_only": True}
        )

    async def load_skills_for_team(self, team_type: TeamType) -> list[SkillLoadResult]:
        """
        Load all relevant skills for a team type.

        Args:
            team_type: The team type to load skills for

        Returns:
            List of load results
        """
        skills = await self.get_skills_for_team(team_type)
        results = []

        for skill in skills:
            result = await self.load_skill(
                skill.id,
                context=f"Loading for {team_type.value} team"
            )
            results.append(result)

        logger.info(
            "Loaded skills for team",
            team=team_type.value,
            loaded=len([r for r in results if r.success]),
            failed=len([r for r in results if not r.success])
        )

        return results

    async def get_agent_skills(
        self,
        role: AgentRole,
        team_type: TeamType
    ) -> list[str]:
        """
        Determine appropriate skill IDs for an agent based on role and team.

        Args:
            role: The agent's role
            team_type: The team the agent belongs to

        Returns:
            List of skill IDs
        """
        # Base skills by role
        role_skills = {
            AgentRole.ARCHITECT: ["system-design", "architecture", "product-strategy"],
            AgentRole.SUPERVISOR: ["code-review", "project-management", "monitoring"],
            AgentRole.EXECUTOR: [],  # Will be filled from team skills
            AgentRole.INTEGRATOR: ["system-design", "testing-automation", "code-review"],
            AgentRole.REVIEWER: ["code-review", "security-hardening", "test-architect"]
        }

        skills = role_skills.get(role, []).copy()

        # Add team-specific skills for executors
        if role == AgentRole.EXECUTOR:
            team_skills = await self.get_skills_for_team(team_type)
            skills.extend([s.id for s in team_skills[:3]])  # Top 3 skills

        return skills

    async def get_gotchas(
        self,
        stack: list[str] | None = None,
        situation: str | None = None,
        code_context: str | None = None
    ) -> GotchaResult:
        """
        Get gotchas and pitfalls from Spawner for the current situation.

        This proactively warns about common mistakes before they happen.

        Args:
            stack: Technology stack (e.g., ["nextjs", "supabase"])
            situation: Description of current situation
            code_context: Code snippet to check

        Returns:
            GotchaResult with warnings
        """
        stack = stack or ["nextjs", "react", "typescript", "supabase"]
        logger.info("Getting gotchas from Spawner", stack=stack)

        if self.mcp_caller:
            try:
                params: dict[str, Any] = {"stack": stack}
                if situation:
                    params["situation"] = situation
                if code_context:
                    params["code_context"] = code_context

                result = await self.mcp_caller("spawner_watch_out", params)

                gotchas = []
                for edge in result.get("sharp_edges", []):
                    gotchas.append({
                        "tech": edge.get("tech", ""),
                        "issue": edge.get("gotcha") or edge.get("issue", ""),
                        "solution": edge.get("solution", ""),
                        "severity": edge.get("severity", "medium")
                    })

                return GotchaResult(stack=stack, gotchas=gotchas)
            except Exception as e:
                logger.warning("Spawner watch_out failed", error=str(e))

        # Fallback: Common gotchas
        gotchas = []

        if "nextjs" in stack:
            gotchas.append({
                "tech": "nextjs",
                "issue": "Using 'use client' unnecessarily",
                "solution": "Default to Server Components, only use client for interactivity",
                "severity": "medium"
            })
            gotchas.append({
                "tech": "nextjs",
                "issue": "Not using App Router conventions",
                "solution": "Use layout.tsx, page.tsx, and route groups properly",
                "severity": "low"
            })

        if "supabase" in stack:
            gotchas.append({
                "tech": "supabase",
                "issue": "Missing RLS policies",
                "solution": "Always enable RLS and add policies for all tables",
                "severity": "high"
            })
            gotchas.append({
                "tech": "supabase",
                "issue": "Exposing service_role key",
                "solution": "Only use anon key on client, service_role on server only",
                "severity": "critical"
            })

        if "typescript" in stack:
            gotchas.append({
                "tech": "typescript",
                "issue": "Using 'any' type",
                "solution": "Define proper types or use 'unknown' with type guards",
                "severity": "medium"
            })

        if "react" in stack:
            gotchas.append({
                "tech": "react",
                "issue": "Missing dependency arrays in useEffect",
                "solution": "Include all dependencies or document why they're excluded",
                "severity": "medium"
            })

        return GotchaResult(stack=stack, gotchas=gotchas)

    async def validate_code(
        self,
        code: str,
        file_path: str,
        check_types: list[str] | None = None
    ) -> ValidationResult:
        """
        Run Spawner validation checks on code.

        Check Types:
        - security: Security vulnerabilities
        - patterns: Anti-patterns and code smells
        - production: Production readiness

        Args:
            code: The code to validate
            file_path: Path for context (determines which checks apply)
            check_types: Types of checks to run (default: all)

        Returns:
            ValidationResult with issues and suggestions
        """
        check_types = check_types or ["security", "patterns", "production"]
        logger.info("Validating code", file_path=file_path, checks=check_types)

        if self.mcp_caller:
            try:
                result = await self.mcp_caller("spawner_validate", {
                    "code": code,
                    "file_path": file_path,
                    "check_types": check_types
                })

                return ValidationResult(
                    valid=result.get("valid", True),
                    issues=result.get("issues", []),
                    suggestions=result.get("suggestions", [])
                )
            except Exception as e:
                logger.warning("Spawner validate failed", error=str(e))

        # Fallback: Basic validation
        issues = []
        suggestions = []

        # Simple pattern checks
        if "any" in code and ".ts" in file_path:
            issues.append({
                "type": "patterns",
                "severity": "medium",
                "message": "Found 'any' type - consider using proper types",
                "line": None
            })

        if "console.log" in code:
            suggestions.append("Remove or replace console.log with proper logging")

        if "TODO" in code or "FIXME" in code:
            suggestions.append("Address TODO/FIXME comments before production")

        return ValidationResult(
            valid=len([i for i in issues if i.get("severity") == "critical"]) == 0,
            issues=issues,
            suggestions=suggestions
        )

    async def get_squad_for_feature(self, feature: str) -> list[str]:
        """
        Get a recommended squad of skills for implementing a feature.

        Spawner has pre-defined squads for common features.

        Args:
            feature: Feature name (e.g., "auth", "payments")

        Returns:
            List of skill IDs for the squad
        """
        logger.info("Getting squad for feature", feature=feature)

        if self.mcp_caller:
            try:
                result = await self.mcp_caller("spawner_skills", {
                    "action": "squad",
                    "squad": f"{feature.lower()}-complete"
                })

                skills = result.get("skills", [])
                return [s.get("id", "") for s in skills if s.get("id")]
            except Exception as e:
                logger.warning("Spawner squad lookup failed", error=str(e))

        # Fallback: Static squad mapping
        squad_mapping = {
            "auth": ["nextjs-supabase-auth", "auth-specialist", "security-audit"],
            "payments": ["stripe-billing", "backend", "security-hardening"],
            "crud": ["backend", "api-design", "supabase-backend"],
            "api": ["api-design", "typescript-strict", "backend"],
            "realtime": ["websockets-realtime", "supabase-backend"],
            "ai": ["llm-architect", "rag-engineer", "prompt-engineer"],
            "dashboard": ["frontend", "tailwind-ui", "data-visualization"]
        }

        feature_lower = feature.lower()
        for key, squad in squad_mapping.items():
            if key in feature_lower:
                return squad

        return []

    async def initialize_project(
        self,
        cwd: str,
        user_message: str | None = None,
        files: list[str] | None = None
    ) -> dict[str, Any]:
        """
        Initialize Spawner for a project using spawner_orchestrate.

        This should be called first in every session.

        Args:
            cwd: Current working directory
            user_message: Optional user request
            files: Optional list of project files

        Returns:
            Orchestration result with detected context
        """
        logger.info("Initializing Spawner for project", cwd=cwd)

        if self.mcp_caller:
            try:
                params: dict[str, Any] = {"cwd": cwd}
                if user_message:
                    params["user_message"] = user_message
                if files:
                    params["files"] = files

                result = await self.mcp_caller("spawner_orchestrate", params)
                self.project_context = result
                return result
            except Exception as e:
                logger.warning("Spawner orchestrate failed", error=str(e))

        return {
            "mode": "new_project",
            "skills_setup": {"status": "unknown"},
            "note": "MCP integration required for full orchestration"
        }

    async def remember_decision(
        self,
        project_id: str | None,
        decision: str,
        reason: str
    ) -> dict[str, Any]:
        """
        Save a project decision via Spawner.

        Args:
            project_id: Optional project ID
            decision: What was decided
            reason: Why it was decided

        Returns:
            Result from Spawner
        """
        if self.mcp_caller:
            try:
                params: dict[str, Any] = {
                    "update": {
                        "decision": {
                            "what": decision,
                            "why": reason
                        }
                    }
                }
                if project_id:
                    params["project_id"] = project_id

                return await self.mcp_caller("spawner_remember", params)
            except Exception as e:
                logger.warning("Spawner remember failed", error=str(e))

        return {"success": True, "local_only": True}


# Recommended Spawner workflow for Architect:

SPAWNER_WORKFLOW = """
## Spawner Integration Workflow

### 1. Project Initialization (CALL FIRST)
```python
# Initialize Spawner for the project
await spawner.initialize_project(
    cwd="/path/to/project",
    user_message="Building a SaaS app"
)
```

### 2. Skill Discovery
```python
# Get skills for each team dynamically
backend_skills = await spawner.get_skills_for_team(TeamType.BACKEND)
frontend_skills = await spawner.get_skills_for_team(TeamType.FRONTEND)

# Or search for specific skills
auth_skills = await spawner.search_skills("authentication", tag="auth")
```

### 3. Skill Loading
```python
# Load skills before team starts work
results = await spawner.load_skills_for_team(TeamType.BACKEND)

# Or load specific skill
result = await spawner.load_skill("supabase-backend", context="Building auth")
```

### 4. Gotcha Checking (Before Each Sprint)
```python
# Get warnings for the stack
gotchas = await spawner.get_gotchas(
    stack=["nextjs", "supabase", "typescript"],
    situation="Setting up authentication"
)

for gotcha in gotchas.gotchas:
    print(f"⚠️  {gotcha['tech']}: {gotcha['issue']}")
    print(f"   Fix: {gotcha['solution']}")
```

### 5. Code Validation (After Tasks)
```python
# Validate code output
validation = await spawner.validate_code(
    code=generated_code,
    file_path="src/lib/auth.ts",
    check_types=["security", "patterns"]
)

if not validation.valid:
    for issue in validation.issues:
        print(f"Issue: {issue['message']}")
```

### 6. Feature Squads
```python
# Get recommended skills for a feature
auth_squad = await spawner.get_squad_for_feature("auth")
# Returns: ["nextjs-supabase-auth", "auth-specialist", "security-audit"]
```

### 7. Remember Decisions
```python
# Store decisions for future projects
await spawner.remember_decision(
    project_id=project.id,
    decision="Use Supabase for auth",
    reason="Team experience and fast setup"
)
```
"""
