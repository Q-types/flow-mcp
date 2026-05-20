"""
Architect MCP Server - Main entry point.

Provides MCP tools for orchestrating vibe coding projects with
multi-agent collaboration, supervisor monitoring, and continuous planning.
"""

import asyncio
import json
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
import structlog

from .state import get_state_manager, StateManager
from .orchestrator import AgentOrchestrator
from .models import TeamType, TaskStatus, LogLevel, SprintStatus

# Configure logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
)

logger = structlog.get_logger()

# Initialize MCP server
server = Server("architect-mcp")

# Valid team types for validation
VALID_TEAM_TYPES = [t.value for t in TeamType]
VALID_TASK_STATUSES = [s.value for s in TaskStatus]
VALID_LOG_LEVELS = [l.value for l in LogLevel]


# --- Error Response Helpers ---

def error_response(code: str, message: str, details: dict | None = None,
                   help_text: str | None = None) -> str:
    """Create a structured error response."""
    response = {
        "success": False,
        "error": {
            "code": code,
            "message": message
        }
    }
    if details:
        response["error"]["details"] = details
    if help_text:
        response["error"]["help"] = help_text
    return json.dumps(response, indent=2)


def success_response(data: dict, next_step: str | None = None) -> str:
    """Create a structured success response."""
    response = {
        "success": True,
        **data
    }
    if next_step:
        response["next_step"] = next_step
    return json.dumps(response, indent=2)


def validate_team_type(team: str) -> TeamType | None:
    """Validate and convert a team string to TeamType."""
    if team in VALID_TEAM_TYPES:
        return TeamType(team)
    return None


def validate_team_types(teams: list[str]) -> tuple[list[TeamType], list[str]]:
    """Validate a list of team strings. Returns (valid, invalid)."""
    valid = []
    invalid = []
    for t in teams:
        if t in VALID_TEAM_TYPES:
            valid.append(TeamType(t))
        else:
            invalid.append(t)
    return valid, invalid


# --- Tool Definitions ---

TOOLS = [
    Tool(
        name="architect_init",
        description="""Initialize a new project from an idea.

Creates a new project and analyzes the idea to understand scope.
This is typically the first tool to call when starting a new vibe coding project.

Example: architect_init(name="MyApp", idea="A task management app with team collaboration")
        """,
        inputSchema={
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Project name (max 200 characters)",
                    "maxLength": 200
                },
                "idea": {
                    "type": "string",
                    "description": "The idea/description of what to build",
                    "maxLength": 10000
                },
                "description": {
                    "type": "string",
                    "description": "Optional longer description",
                    "maxLength": 10000
                }
            },
            "required": ["name", "idea"]
        }
    ),
    Tool(
        name="architect_plan",
        description="""Create an execution plan for the active project.

The Architect analyzes the project idea and creates a comprehensive plan including:
- Required teams and their responsibilities
- Execution phases with tasks
- Dependencies between teams
- Critical path through the project
- Risk assessment

Call this after architect_init to get the project plan.
        """,
        inputSchema={
            "type": "object",
            "properties": {},
            "required": []
        }
    ),
    Tool(
        name="architect_spawn_teams",
        description="""Spawn the complete agent team structure for the project.

Creates all teams with their agents:
- Supervisors: One per team to monitor progress
- Executors: 2-3 developers per team
- Integrator: One for the whole project

Call this after architect_plan to set up the team structure.
        """,
        inputSchema={
            "type": "object",
            "properties": {},
            "required": []
        }
    ),
    Tool(
        name="architect_create_sprint",
        description="""Create a new sprint with specific goals.

Sprints organize work into focused iterations with clear goals.
Each sprint targets specific teams and contains tasks.
        """,
        inputSchema={
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Sprint name (e.g., 'Sprint 1: Foundation')",
                    "maxLength": 200
                },
                "goal": {
                    "type": "string",
                    "description": "What this sprint aims to achieve",
                    "maxLength": 10000
                },
                "teams": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": VALID_TEAM_TYPES
                    },
                    "description": "Teams involved in this sprint"
                }
            },
            "required": ["name", "goal", "teams"]
        }
    ),
    Tool(
        name="architect_add_task",
        description="""Add a task to the current sprint.

Tasks are assigned to teams and can have dependencies on other tasks.
        """,
        inputSchema={
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Task title",
                    "maxLength": 200
                },
                "description": {
                    "type": "string",
                    "description": "What needs to be done",
                    "maxLength": 10000
                },
                "team": {
                    "type": "string",
                    "enum": VALID_TEAM_TYPES,
                    "description": "Team to assign the task to"
                },
                "priority": {
                    "type": "integer",
                    "description": "Priority 1-5 (1=highest). Default: 3",
                    "minimum": 1,
                    "maximum": 5,
                    "default": 3
                },
                "dependencies": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "IDs of tasks this depends on"
                },
                "acceptance_criteria": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Criteria for task completion"
                }
            },
            "required": ["title", "description", "team"]
        }
    ),
    Tool(
        name="architect_update_task",
        description="""Update a task's status.

Track progress by updating task status:
- pending: Not started
- assigned: Assigned to an agent
- in_progress: Being worked on
- review: Awaiting review
- completed: Done
- blocked: Blocked by something
- failed: Failed to complete
        """,
        inputSchema={
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "string",
                    "description": "Task ID to update"
                },
                "status": {
                    "type": "string",
                    "enum": VALID_TASK_STATUSES,
                    "description": "New status"
                },
                "output": {
                    "type": "string",
                    "description": "Optional output/result from the task"
                }
            },
            "required": ["task_id", "status"]
        }
    ),
    Tool(
        name="architect_get_task",
        description="""Get details of a specific task by ID.

Returns full task information including status, team, priority, and acceptance criteria.
        """,
        inputSchema={
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "string",
                    "description": "Task ID to retrieve"
                }
            },
            "required": ["task_id"]
        }
    ),
    Tool(
        name="architect_list_tasks",
        description="""List tasks with optional filtering.

Filter by sprint, team, or status to find specific tasks.
        """,
        inputSchema={
            "type": "object",
            "properties": {
                "sprint_id": {
                    "type": "string",
                    "description": "Filter by sprint ID (default: current sprint)"
                },
                "team": {
                    "type": "string",
                    "enum": VALID_TEAM_TYPES,
                    "description": "Filter by team"
                },
                "status": {
                    "type": "string",
                    "enum": VALID_TASK_STATUSES,
                    "description": "Filter by status"
                }
            },
            "required": []
        }
    ),
    Tool(
        name="architect_delete_task",
        description="""Delete a task by ID.

Removes a task from the sprint. Use with caution.
        """,
        inputSchema={
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "string",
                    "description": "Task ID to delete"
                }
            },
            "required": ["task_id"]
        }
    ),
    Tool(
        name="architect_complete_sprint",
        description="""Mark the current sprint as completed.

Finalizes the sprint with a summary. Creates a completion log entry.
        """,
        inputSchema={
            "type": "object",
            "properties": {
                "summary": {
                    "type": "string",
                    "description": "Sprint completion summary"
                }
            },
            "required": []
        }
    ),
    Tool(
        name="architect_log",
        description="""Add a log entry to the current sprint.

Logs track what's happening during execution. Keep logs concise but informative.
        """,
        inputSchema={
            "type": "object",
            "properties": {
                "level": {
                    "type": "string",
                    "enum": VALID_LOG_LEVELS,
                    "description": "Log level"
                },
                "team": {
                    "type": "string",
                    "description": "Team this log is for"
                },
                "message": {
                    "type": "string",
                    "description": "Log message (keep concise, max 1000 chars)",
                    "maxLength": 1000
                },
                "context": {
                    "type": "object",
                    "description": "Optional additional context"
                }
            },
            "required": ["level", "team", "message"]
        }
    ),
    Tool(
        name="architect_check_integration",
        description="""Run an integration check across all teams.

The Integrator checks for compatibility issues:
- API contract mismatches
- Data model inconsistencies
- Blocked tasks
- Dependency problems

Returns issues found and suggestions for fixes.
        """,
        inputSchema={
            "type": "object",
            "properties": {},
            "required": []
        }
    ),
    Tool(
        name="architect_supervisor_review",
        description="""Get a supervisor's review of their team.

Each supervisor monitors their team's progress:
- Task completion rate
- Blockers
- Recommendations

Use this to check how a specific team is doing.
        """,
        inputSchema={
            "type": "object",
            "properties": {
                "team": {
                    "type": "string",
                    "enum": VALID_TEAM_TYPES,
                    "description": "Team type to review"
                }
            },
            "required": ["team"]
        }
    ),
    Tool(
        name="architect_status",
        description="""Get comprehensive project status.

Returns an overview of:
- Project info
- All teams and their agents
- Current sprint progress
- Recent activity log
        """,
        inputSchema={
            "type": "object",
            "properties": {},
            "required": []
        }
    ),
    Tool(
        name="architect_get_logs",
        description="""Get sprint logs with optional filtering.

Retrieve logs to understand what's been happening.
        """,
        inputSchema={
            "type": "object",
            "properties": {
                "level": {
                    "type": "string",
                    "enum": VALID_LOG_LEVELS,
                    "description": "Filter by log level"
                },
                "team": {
                    "type": "string",
                    "description": "Filter by team"
                },
                "limit": {
                    "type": "integer",
                    "description": "Max logs to return (default 50, max 100)",
                    "minimum": 1,
                    "maximum": 100,
                    "default": 50
                }
            },
            "required": []
        }
    ),
    Tool(
        name="architect_connect_mind",
        description="""Connect to Mind MCP for persistent memory.

When connected, decisions and learnings are stored in Mind MCP
for retrieval across sessions.
        """,
        inputSchema={
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "string",
                    "description": "Mind MCP user ID"
                }
            },
            "required": ["user_id"]
        }
    ),
    Tool(
        name="architect_remember",
        description="""Store a decision or learning for future reference.

Works with Mind MCP if connected, also stores locally.
        """,
        inputSchema={
            "type": "object",
            "properties": {
                "decision": {
                    "type": "string",
                    "description": "The decision or learning to remember"
                },
                "context": {
                    "type": "object",
                    "description": "Additional context"
                }
            },
            "required": ["decision"]
        }
    ),
    Tool(
        name="architect_list_projects",
        description="""List all available projects.

Shows all projects with their status and metadata.
        """,
        inputSchema={
            "type": "object",
            "properties": {},
            "required": []
        }
    ),
    Tool(
        name="architect_set_active_project",
        description="""Switch to a different project by ID.

Changes the active project for subsequent operations.
        """,
        inputSchema={
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "string",
                    "description": "Project ID to activate"
                }
            },
            "required": ["project_id"]
        }
    ),
    Tool(
        name="architect_delete_project",
        description="""Delete a project by ID.

Permanently removes a project and all its data. Use with caution.
        """,
        inputSchema={
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "string",
                    "description": "Project ID to delete"
                }
            },
            "required": ["project_id"]
        }
    ),
    Tool(
        name="architect_get_team",
        description="""Get details of a specific team.

Returns team information including agents and current tasks.
        """,
        inputSchema={
            "type": "object",
            "properties": {
                "team": {
                    "type": "string",
                    "enum": VALID_TEAM_TYPES,
                    "description": "Team type to retrieve"
                }
            },
            "required": ["team"]
        }
    ),
    # --- NEW ORCHESTRATION TOOLS ---
    Tool(
        name="architect_validate_idea",
        description="""Validate an idea using IdeaRalph's PMF scoring.

Scores the idea on 10 Product-Market Fit dimensions:
- Problem Clarity, Market Size, Uniqueness
- Feasibility, Monetization, Timing
- Virality, Defensibility, Team Fit, Ralph Factor

Returns scores, strengths, weaknesses, and suggestions.
If score < 7.0, the idea needs significant refinement.
If score >= 8.5, ready for PRD generation.

This is typically the FIRST step before architect_init.
        """,
        inputSchema={
            "type": "object",
            "properties": {
                "idea": {
                    "type": "string",
                    "description": "The startup/product idea to validate"
                },
                "refine_if_needed": {
                    "type": "boolean",
                    "description": "Auto-refine if score < 8.0 (default: false)",
                    "default": False
                }
            },
            "required": ["idea"]
        }
    ),
    Tool(
        name="architect_generate_prd",
        description="""Generate a Product Requirements Document using IdeaRalph.

PRD Levels:
- napkin: Quick 1-page sketch (problem, solution, features)
- science-fair: Detailed with personas, user stories, tech requirements
- genius: Comprehensive investor-ready doc with TAM/SAM/SOM, GTM

Call this after architect_validate_idea confirms idea viability.
        """,
        inputSchema={
            "type": "object",
            "properties": {
                "idea": {
                    "type": "string",
                    "description": "The validated idea"
                },
                "level": {
                    "type": "string",
                    "enum": ["napkin", "science-fair", "genius"],
                    "description": "PRD detail level (default: science-fair)",
                    "default": "science-fair"
                }
            },
            "required": ["idea"]
        }
    ),
    Tool(
        name="architect_load_context",
        description="""Load relevant context from Mind before planning.

Retrieves past decisions, lessons learned, and patterns
relevant to the current project idea.

This helps the Architect make better decisions based on
accumulated experience.
        """,
        inputSchema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "What context to retrieve (e.g., project type, tech stack)"
                },
                "project_type": {
                    "type": "string",
                    "description": "Optional project type filter (saas, marketplace, ai-app, etc.)"
                }
            },
            "required": ["query"]
        }
    ),
    Tool(
        name="architect_get_gotchas",
        description="""Get gotchas and sharp edges for a tech stack.

Proactively warns about common pitfalls BEFORE they happen.
Call this before starting a sprint or major feature work.

Returns issues with severity (critical, high, medium, low)
and solutions for each.
        """,
        inputSchema={
            "type": "object",
            "properties": {
                "stack": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Tech stack (e.g., ['nextjs', 'supabase', 'typescript'])"
                },
                "situation": {
                    "type": "string",
                    "description": "What you're about to do (e.g., 'setting up auth')"
                }
            },
            "required": []
        }
    ),
    Tool(
        name="architect_full_pipeline",
        description="""Run the complete Architect pipeline from idea to plan.

This orchestrates:
1. IdeaRalph validation (with optional refinement)
2. PRD generation
3. Context retrieval from Mind
4. Project creation and planning
5. Team structure spawning

Use this for a streamlined end-to-end experience.
        """,
        inputSchema={
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Project name"
                },
                "idea": {
                    "type": "string",
                    "description": "The idea to build"
                },
                "auto_refine": {
                    "type": "boolean",
                    "description": "Auto-refine idea if score < 8.0 (default: true)",
                    "default": True
                },
                "prd_level": {
                    "type": "string",
                    "enum": ["napkin", "science-fair", "genius"],
                    "description": "PRD detail level (default: science-fair)",
                    "default": "science-fair"
                },
                "skip_validation": {
                    "type": "boolean",
                    "description": "Skip idea validation (default: false)",
                    "default": False
                }
            },
            "required": ["name", "idea"]
        }
    ),
    Tool(
        name="architect_smart_assign",
        description="""Smart task assignment with automatic skill loading.

Assigns a task to a team AND loads relevant Spawner skills
for the assigned agents. Also retrieves gotchas for the task.

Use this instead of architect_add_task for better skill matching.
        """,
        inputSchema={
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Task title"
                },
                "description": {
                    "type": "string",
                    "description": "What needs to be done"
                },
                "team": {
                    "type": "string",
                    "enum": VALID_TEAM_TYPES,
                    "description": "Team to assign to"
                },
                "feature": {
                    "type": "string",
                    "description": "Feature type for skill squad (e.g., 'auth', 'payments')"
                },
                "priority": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 5,
                    "default": 3
                }
            },
            "required": ["title", "description", "team"]
        }
    ),
    # --- SPAWNER SKILL TOOLS ---
    Tool(
        name="architect_load_skill_pack",
        description="""Load a Spawner skill pack for specialized knowledge.

Available skill packs:
- essentials: Core development skills (SvelteKit, Supabase, TypeScript)
- data-science: Statistics, ML, NLP, time series analysis
- ai: LLM integration, RAG, prompt engineering
- startup: YC playbook, growth strategy, product strategy
- enterprise: Security, compliance, enterprise patterns
- marketing-ai: Content, SEO, social media automation
- finance: Payments, fintech, crypto/web3

Call this before architect_create_sprint to equip teams with domain knowledge.
        """,
        inputSchema={
            "type": "object",
            "properties": {
                "pack": {
                    "type": "string",
                    "description": "Skill pack name (e.g., 'data-science', 'ai', 'startup')"
                },
                "feature": {
                    "type": "string",
                    "description": "Optional: specific feature squad (e.g., 'auth-complete', 'payments-complete')"
                }
            },
            "required": ["pack"]
        }
    ),
    Tool(
        name="architect_search_skills",
        description="""Search Spawner's skill library for relevant expertise.

Search across 470+ skills by:
- Query text (matches names, descriptions, triggers)
- Tag filter (e.g., 'auth', 'supabase', 'react')
- Layer (1=Core, 2=Integration, 3=Polish)

Returns matching skills with descriptions and tags.
        """,
        inputSchema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query for skills"
                },
                "tag": {
                    "type": "string",
                    "description": "Filter by tag"
                },
                "limit": {
                    "type": "integer",
                    "description": "Max results (default: 10)",
                    "default": 10,
                    "maximum": 50
                }
            },
            "required": ["query"]
        }
    ),
    Tool(
        name="architect_smart_discover",
        description="""Smart skill discovery using the full MCP stack.

Uses Mind + Muse + Spawner for intelligent skill selection:
1. Mind: Retrieves past successful skill combinations
2. Muse: Expands search with analogies and associations
3. Spawner: Multi-query search across 470+ skills
4. Architect: Context-aware filtering by project/task
5. Mind: Records selection for future learning

Example: For "database" with Supabase project, might find:
- supabase-backend (direct match + stack match)
- PostgreSQL Wizard (Mind suggested from past success)
- Migration Specialist (Muse analogy: "data evolution")
- Drizzle ORM (context: TypeScript stack)

Use this instead of architect_search_skills for better results.
        """,
        inputSchema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "What you're looking for (e.g., 'database', 'auth', 'ai')"
                },
                "tech_stack": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Project tech stack for context (e.g., ['supabase', 'nextjs'])"
                },
                "task_description": {
                    "type": "string",
                    "description": "What you're trying to accomplish"
                },
                "use_mind": {
                    "type": "boolean",
                    "description": "Consult Mind for past successes (default: true)",
                    "default": True
                },
                "use_muse": {
                    "type": "boolean",
                    "description": "Use Muse for analogies (default: true)",
                    "default": True
                },
                "limit": {
                    "type": "integer",
                    "description": "Max skills to return (default: 10)",
                    "default": 10
                }
            },
            "required": ["query"]
        }
    ),
    # --- SCOPE & QUALITY TOOLS ---
    Tool(
        name="architect_enforce_scope",
        description="""Supervisor scope enforcement for a task.

Enforces scope adherence during long-running tasks:
- Re-injects original scope context after time thresholds (2 min default)
- Detects drift from planned deliverables
- Returns pause recommendation for critical drift

Use this periodically during task execution to keep teams on track.
        """,
        inputSchema={
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "string",
                    "description": "Task ID being supervised"
                },
                "elapsed_ms": {
                    "type": "integer",
                    "description": "Time elapsed since task start in milliseconds"
                },
                "original_scope": {
                    "type": "object",
                    "description": "Original scope boundaries",
                    "properties": {
                        "deliverables": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Planned file deliverables"
                        },
                        "exclusions": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Files that must NOT be modified"
                        },
                        "acceptance_criteria": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Criteria for task completion"
                        }
                    }
                },
                "current_output": {
                    "type": "object",
                    "description": "Current task output with 'modified_files' list",
                    "properties": {
                        "modified_files": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of files modified so far"
                        }
                    }
                }
            },
            "required": ["task_id", "elapsed_ms", "original_scope"]
        }
    ),
    Tool(
        name="architect_review_loop",
        description="""Run a recursive review cycle on a task.

Implements iterative verify-correct-reverify cycles:
- Checks quality gates (tests, lint, scope coverage)
- Returns action: 'complete', 'continue', or 'correct'
- Tracks iteration count vs max iterations

Use after task execution to ensure quality before marking complete.
        """,
        inputSchema={
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "string",
                    "description": "Task ID to review"
                },
                "verification_result": {
                    "type": "object",
                    "description": "Verification data (tests, lint, scope)",
                    "properties": {
                        "tests": {
                            "type": "object",
                            "properties": {
                                "passed": {"type": "integer"},
                                "failed": {"type": "integer"},
                                "total": {"type": "integer"}
                            }
                        },
                        "lint": {
                            "type": "object",
                            "properties": {
                                "critical_errors": {"type": "integer"},
                                "warnings": {"type": "integer"}
                            }
                        },
                        "scope": {
                            "type": "object",
                            "properties": {
                                "adherence_percentage": {"type": "number"}
                            }
                        }
                    }
                },
                "max_iterations": {
                    "type": "integer",
                    "description": "Maximum review cycles (default: 3)",
                    "default": 3
                },
                "execution_result": {
                    "type": "object",
                    "description": "Result from task execution"
                }
            },
            "required": ["task_id", "verification_result"]
        }
    ),
    Tool(
        name="architect_check_quality_gates",
        description="""Check quality gates for a task.

Evaluates task against configured quality gates:
- test_pass_rate: 100% threshold (blocking)
- lint_critical_errors: 0 threshold (blocking)
- scope_coverage: 90% threshold (non-blocking)

Returns pass/fail for each gate with evidence.
        """,
        inputSchema={
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "string",
                    "description": "Task ID to check"
                },
                "verification_result": {
                    "type": "object",
                    "description": "Verification data to check against gates",
                    "properties": {
                        "tests": {
                            "type": "object",
                            "properties": {
                                "passed": {"type": "integer"},
                                "total": {"type": "integer"}
                            }
                        },
                        "lint": {
                            "type": "object",
                            "properties": {
                                "critical_errors": {"type": "integer"}
                            }
                        },
                        "scope": {
                            "type": "object",
                            "properties": {
                                "adherence_percentage": {"type": "number"}
                            }
                        }
                    }
                }
            },
            "required": ["task_id", "verification_result"]
        }
    ),
    Tool(
        name="architect_evaluate_plan",
        description="""Evaluate an implementation plan on multiple dimensions.

Metrics evaluated:
- Complexity: Team count, phases, tasks, dependency depth, integration points
- Feasibility: Resource availability, skill coverage, external dependencies
- Clarity: Objectives, acceptance criteria, success metrics defined
- Cohesion: Orphan tasks, circular dependencies, handoff clarity
- Risk: Identified risks, mitigations, single points of failure

Returns:
- Scores (0-10) for each dimension
- Overall score with recommendation
- Specific improvements needed
- Similar past plans from Mind (for comparison)

Use after architect_plan to assess plan quality before execution.
Stores evaluation in Mind for learning which plans succeed.
        """,
        inputSchema={
            "type": "object",
            "properties": {
                "tech_stack": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Tech stack for context (e.g., ['nextjs', 'supabase'])"
                }
            },
            "required": []
        }
    ),
    Tool(
        name="architect_record_plan_outcome",
        description="""Record the actual outcome of a completed plan.

Creates a feedback loop for learning:
- Successful plans' characteristics are reinforced
- Future similar plans will benefit from past lessons
- Complexity patterns that work/fail are tracked

Call this after project/sprint completion to improve future planning.
        """,
        inputSchema={
            "type": "object",
            "properties": {
                "success": {
                    "type": "boolean",
                    "description": "Whether the plan succeeded overall"
                },
                "completion_rate": {
                    "type": "number",
                    "description": "Percentage of tasks completed (0.0-1.0)",
                    "minimum": 0,
                    "maximum": 1
                },
                "actual_sprints": {
                    "type": "integer",
                    "description": "Actual number of sprints taken"
                },
                "lessons": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Lessons learned from execution"
                }
            },
            "required": ["success", "completion_rate", "actual_sprints"]
        }
    ),
    Tool(
        name="architect_project_manager_review",
        description="""Project Manager's final review of a sprint.

Provides comprehensive sprint review from PM perspective:
- Checks scope adherence across ALL teams
- Gets status of each team
- Makes go/no-go decision for next sprint
- Generates recommendations

Use at sprint end before moving to next sprint.
        """,
        inputSchema={
            "type": "object",
            "properties": {
                "sprint_id": {
                    "type": "string",
                    "description": "Sprint ID to review (default: current sprint)"
                }
            },
            "required": []
        }
    )
]


# --- Tool Handlers ---

async def handle_architect_init(args: dict[str, Any], state: StateManager) -> str:
    """Initialize a new project."""
    try:
        project = await state.create_project(
            args["name"],
            args.get("description", args["idea"]),
            args["idea"]
        )
        return success_response(
            {
                "project": {
                    "id": project.id,
                    "name": project.name,
                    "idea": project.idea[:200] + "..." if len(project.idea) > 200 else project.idea
                }
            },
            next_step="Call architect_plan to create the execution plan"
        )
    except ValueError as e:
        return error_response("VALIDATION_ERROR", str(e))


async def handle_architect_plan(args: dict[str, Any], state: StateManager) -> str:
    """Create execution plan."""
    project = state.get_active_project()
    if not project:
        return error_response(
            "NO_ACTIVE_PROJECT",
            "No active project found",
            help_text="Run architect_init(name='YourProject', idea='Your idea') first"
        )

    orchestrator = AgentOrchestrator(state)
    plan = await orchestrator.plan_project(project.idea)

    return success_response(
        {
            "plan": {
                "phases": len(plan.phases),
                "teams_needed": plan.team_structure.get("teams", []),
                "estimated_sprints": plan.estimated_sprints,
                "critical_path": plan.critical_path,
                "risks": plan.risks
            },
            "phases_detail": plan.phases
        },
        next_step="Call architect_spawn_teams to create the agent team structure"
    )


async def handle_architect_spawn_teams(args: dict[str, Any], state: StateManager) -> str:
    """Spawn team structure with Spawner skills integration."""
    project = state.get_active_project()
    if not project:
        return error_response(
            "NO_ACTIVE_PROJECT",
            "No active project found",
            help_text="Run architect_init first"
        )

    if not project.architecture:
        return error_response(
            "NO_PLAN",
            "No execution plan found",
            help_text="Run architect_plan before spawning teams"
        )

    orchestrator = AgentOrchestrator(state)
    # Use enhanced spawning with Spawner skills
    result = await orchestrator.spawn_teams_with_skills(project.id)

    response_data = {
        "structure": result["structure"],
        "teams": [{"name": t["name"], "type": t["type"]} for t in result["teams"]]
    }

    # Include skills loaded per team
    if "skills_loaded" in result:
        response_data["skills_loaded"] = result["skills_loaded"]

    # Include gotchas/warnings
    if "gotchas" in result:
        response_data["gotchas"] = {
            "stack": result["gotchas"]["stack"],
            "warning_count": result["gotchas"]["total"],
            "top_warnings": [g.get("issue", "") for g in result["gotchas"]["warnings"][:3]]
        }

    return success_response(
        response_data,
        next_step="Call architect_create_sprint to start the first sprint"
    )


async def handle_architect_create_sprint(args: dict[str, Any], state: StateManager) -> str:
    """Create a new sprint."""
    project = state.get_active_project()
    if not project:
        return error_response("NO_ACTIVE_PROJECT", "No active project found")

    # Validate team types
    valid_teams, invalid_teams = validate_team_types(args["teams"])
    if invalid_teams:
        return error_response(
            "INVALID_TEAM_TYPE",
            f"Invalid team types: {invalid_teams}",
            details={"valid_teams": VALID_TEAM_TYPES}
        )

    if not valid_teams:
        return error_response("VALIDATION_ERROR", "At least one team is required")

    try:
        sprint = await state.create_sprint(
            project.id,
            args["name"],
            args["goal"],
            valid_teams
        )
        return success_response(
            {
                "sprint": {
                    "id": sprint.id,
                    "name": sprint.name,
                    "goal": sprint.goal,
                    "teams": [t.value for t in sprint.teams]
                }
            },
            next_step="Call architect_add_task to add tasks to the sprint"
        )
    except ValueError as e:
        return error_response("VALIDATION_ERROR", str(e))


async def handle_architect_add_task(args: dict[str, Any], state: StateManager) -> str:
    """Add a task to the current sprint."""
    project = state.get_active_project()
    if not project or not project.current_sprint_id:
        return error_response(
            "NO_ACTIVE_SPRINT",
            "No active project or sprint",
            help_text="Create a sprint with architect_create_sprint first"
        )

    team_type = validate_team_type(args["team"])
    if not team_type:
        return error_response(
            "INVALID_TEAM_TYPE",
            f"Invalid team type: {args['team']}",
            details={"valid_teams": VALID_TEAM_TYPES}
        )

    try:
        task = await state.add_task(
            project.id,
            project.current_sprint_id,
            args["title"],
            args["description"],
            team_type,
            args.get("priority", 3),
            args.get("dependencies", []),
            args.get("acceptance_criteria", [])
        )
        return success_response({
            "task": {
                "id": task.id,
                "title": task.title,
                "team": task.team.value,
                "priority": task.priority,
                "status": task.status.value
            }
        })
    except ValueError as e:
        return error_response("VALIDATION_ERROR", str(e))


async def handle_architect_update_task(args: dict[str, Any], state: StateManager) -> str:
    """Update task status."""
    project = state.get_active_project()
    if not project or not project.current_sprint_id:
        return error_response("NO_ACTIVE_SPRINT", "No active project or sprint")

    if args["status"] not in VALID_TASK_STATUSES:
        return error_response(
            "INVALID_STATUS",
            f"Invalid status: {args['status']}",
            details={"valid_statuses": VALID_TASK_STATUSES}
        )

    try:
        task = await state.update_task_status(
            project.id,
            project.current_sprint_id,
            args["task_id"],
            TaskStatus(args["status"]),
            args.get("output")
        )
        return success_response({
            "task": {
                "id": task.id,
                "title": task.title,
                "status": task.status.value
            }
        })
    except ValueError as e:
        return error_response("NOT_FOUND", str(e))


async def handle_architect_get_task(args: dict[str, Any], state: StateManager) -> str:
    """Get task details."""
    task_entry = state.get_task(args["task_id"])
    if not task_entry:
        return error_response("NOT_FOUND", f"Task {args['task_id']} not found")

    project_id, sprint_id, task = task_entry
    return success_response({
        "task": {
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "team": task.team.value,
            "status": task.status.value,
            "priority": task.priority,
            "dependencies": task.dependencies,
            "acceptance_criteria": task.acceptance_criteria,
            "assigned_to": task.assigned_to,
            "created_at": task.created_at.isoformat(),
            "completed_at": task.completed_at.isoformat() if task.completed_at else None
        }
    })


async def handle_architect_list_tasks(args: dict[str, Any], state: StateManager) -> str:
    """List tasks with filtering."""
    project = state.get_active_project()
    if not project:
        return error_response("NO_ACTIVE_PROJECT", "No active project found")

    team = validate_team_type(args["team"]) if args.get("team") else None
    status = TaskStatus(args["status"]) if args.get("status") in VALID_TASK_STATUSES else None
    sprint_id = args.get("sprint_id", project.current_sprint_id)

    tasks = state.list_tasks(project.id, sprint_id, team, status)

    return success_response({
        "tasks": [
            {
                "id": t.id,
                "title": t.title,
                "team": t.team.value,
                "status": t.status.value,
                "priority": t.priority
            }
            for t in tasks
        ],
        "count": len(tasks)
    })


async def handle_architect_delete_task(args: dict[str, Any], state: StateManager) -> str:
    """Delete a task."""
    deleted = await state.delete_task(args["task_id"])
    if not deleted:
        return error_response("NOT_FOUND", f"Task {args['task_id']} not found")
    return success_response({"deleted": True, "task_id": args["task_id"]})


async def handle_architect_complete_sprint(args: dict[str, Any], state: StateManager) -> str:
    """Complete the current sprint."""
    project = state.get_active_project()
    if not project or not project.current_sprint_id:
        return error_response("NO_ACTIVE_SPRINT", "No active sprint")

    try:
        sprint = await state.complete_sprint(
            project.id,
            project.current_sprint_id,
            args.get("summary", "")
        )
        return success_response({
            "sprint": {
                "id": sprint.id,
                "name": sprint.name,
                "status": sprint.status.value,
                "completed_at": sprint.completed_at.isoformat() if sprint.completed_at else None
            }
        })
    except ValueError as e:
        return error_response("ERROR", str(e))


async def handle_architect_log(args: dict[str, Any], state: StateManager) -> str:
    """Add a sprint log."""
    project = state.get_active_project()
    if not project or not project.current_sprint_id:
        return error_response("NO_ACTIVE_SPRINT", "No active project or sprint")

    if args["level"] not in VALID_LOG_LEVELS:
        return error_response(
            "INVALID_LOG_LEVEL",
            f"Invalid log level: {args['level']}",
            details={"valid_levels": VALID_LOG_LEVELS}
        )

    try:
        log = await state.add_sprint_log(
            project.id,
            project.current_sprint_id,
            LogLevel(args["level"]),
            args["team"],
            args["message"],
            context=args.get("context")
        )
        return success_response({
            "log": {
                "timestamp": log.timestamp.isoformat(),
                "level": log.level.value,
                "message": log.message
            }
        })
    except ValueError as e:
        return error_response("ERROR", str(e))


async def handle_architect_check_integration(args: dict[str, Any], state: StateManager) -> str:
    """Run integration check."""
    project = state.get_active_project()
    if not project:
        return error_response("NO_ACTIVE_PROJECT", "No active project found")

    orchestrator = AgentOrchestrator(state)
    check = await orchestrator.check_integration(project.id)

    return success_response({
        "integration_check": {
            "compatible": check.compatible,
            "teams_checked": check.teams_checked,
            "issues": check.issues,
            "suggestions": check.suggestions,
            "checked_at": check.checked_at.isoformat()
        }
    })


async def handle_architect_supervisor_review(args: dict[str, Any], state: StateManager) -> str:
    """Get supervisor review."""
    project = state.get_active_project()
    if not project:
        return error_response("NO_ACTIVE_PROJECT", "No active project found")

    team_type = validate_team_type(args["team"])
    if not team_type:
        return error_response(
            "INVALID_TEAM_TYPE",
            f"Invalid team type: {args['team']}",
            details={"valid_teams": VALID_TEAM_TYPES}
        )

    # Find the team
    team = next((t for t in project.teams if t.type == team_type), None)
    if not team:
        return error_response("NOT_FOUND", f"Team {args['team']} not found in project")

    orchestrator = AgentOrchestrator(state)
    review = await orchestrator.supervisor_review(project.id, team.id)

    return success_response({"review": review})


async def handle_architect_status(args: dict[str, Any], state: StateManager) -> str:
    """Get project status."""
    project = state.get_active_project()
    if not project:
        return error_response(
            "NO_ACTIVE_PROJECT",
            "No active project found",
            help_text="Run architect_init to create a project or architect_list_projects to see existing ones"
        )

    orchestrator = AgentOrchestrator(state)
    status = await orchestrator.get_project_status(project.id)

    return success_response({"status": status})


async def handle_architect_get_logs(args: dict[str, Any], state: StateManager) -> str:
    """Get sprint logs."""
    project = state.get_active_project()
    if not project or not project.current_sprint_id:
        return error_response("NO_ACTIVE_SPRINT", "No active project or sprint")

    level = LogLevel(args["level"]) if args.get("level") in VALID_LOG_LEVELS else None
    logs = state.get_sprint_logs(
        project.id,
        project.current_sprint_id,
        level=level,
        team=args.get("team"),
        limit=min(args.get("limit", 50), 100)
    )

    return success_response({
        "logs": [
            {
                "timestamp": log.timestamp.isoformat(),
                "level": log.level.value,
                "team": log.team,
                "message": log.message
            }
            for log in logs
        ],
        "count": len(logs)
    })


async def handle_architect_connect_mind(args: dict[str, Any], state: StateManager) -> str:
    """Connect to Mind MCP."""
    try:
        await state.connect_mind(args["user_id"])
        return success_response({
            "connected": True,
            "message": "Connected to Mind MCP"
        })
    except ValueError as e:
        return error_response("VALIDATION_ERROR", str(e))


async def handle_architect_remember(args: dict[str, Any], state: StateManager) -> str:
    """Store a decision."""
    try:
        await state.remember_decision(args["decision"], args.get("context"))
        return success_response({
            "remembered": True,
            "message": "Decision recorded"
        })
    except ValueError as e:
        return error_response("VALIDATION_ERROR", str(e))


async def handle_architect_list_projects(args: dict[str, Any], state: StateManager) -> str:
    """List projects."""
    projects = [
        {
            "id": p.id,
            "name": p.name,
            "active": p.id == state.active_project_id,
            "teams": len(p.teams),
            "sprints": len(p.sprints),
            "created_at": p.created_at.isoformat()
        }
        for p in state.projects.values()
    ]

    return success_response({
        "projects": projects,
        "count": len(projects),
        "active_project_id": state.active_project_id
    })


async def handle_architect_set_active_project(args: dict[str, Any], state: StateManager) -> str:
    """Set active project."""
    project = await state.set_active_project(args["project_id"])
    if not project:
        return error_response(
            "NOT_FOUND",
            f"Project {args['project_id']} not found",
            help_text="Use architect_list_projects to see available projects"
        )

    return success_response({
        "active_project": {
            "id": project.id,
            "name": project.name
        }
    })


async def handle_architect_delete_project(args: dict[str, Any], state: StateManager) -> str:
    """Delete a project."""
    deleted = await state.delete_project(args["project_id"])
    if not deleted:
        return error_response("NOT_FOUND", f"Project {args['project_id']} not found")

    return success_response({
        "deleted": True,
        "project_id": args["project_id"],
        "new_active_project": state.active_project_id
    })


async def handle_architect_get_team(args: dict[str, Any], state: StateManager) -> str:
    """Get team details."""
    project = state.get_active_project()
    if not project:
        return error_response("NO_ACTIVE_PROJECT", "No active project found")

    team_type = validate_team_type(args["team"])
    if not team_type:
        return error_response(
            "INVALID_TEAM_TYPE",
            f"Invalid team type: {args['team']}",
            details={"valid_teams": VALID_TEAM_TYPES}
        )

    team = next((t for t in project.teams if t.type == team_type), None)
    if not team:
        return error_response("NOT_FOUND", f"Team {args['team']} not found")

    # Get team's tasks from current sprint
    tasks = []
    if project.current_sprint_id:
        sprint_entry = state.get_sprint(project.current_sprint_id)
        if sprint_entry:
            tasks = [
                {"id": t.id, "title": t.title, "status": t.status.value}
                for t in sprint_entry[1].tasks
                if t.team == team_type
            ]

    return success_response({
        "team": {
            "id": team.id,
            "name": team.name,
            "type": team.type.value,
            "supervisor_id": team.supervisor_id,
            "agents": [
                {"id": a.id, "name": a.name, "role": a.role.value}
                for a in team.agents
            ],
            "current_tasks": tasks
        }
    })


# --- NEW ORCHESTRATION HANDLERS ---

async def handle_architect_validate_idea(args: dict[str, Any], state: StateManager) -> str:
    """Validate idea using IdeaRalph."""
    from .integrations import IdeaRalphIntegration

    idearalph = IdeaRalphIntegration()
    validation = await idearalph.validate_idea(args["idea"])

    result = {
        "validation": {
            "idea": validation.idea[:200] + "..." if len(validation.idea) > 200 else validation.idea,
            "scores": validation.scores.to_dict(),
            "is_viable": validation.is_viable,
            "needs_refinement": validation.needs_refinement,
            "strengths": validation.strengths,
            "weaknesses": validation.weaknesses,
            "suggestions": validation.suggestions
        }
    }

    # Determine next step based on score
    avg_score = validation.scores.average
    if avg_score >= 8.5:
        next_step = "Idea is strong! Call architect_generate_prd to create requirements"
    elif avg_score >= 7.0:
        next_step = "Idea is viable. Consider refinement or proceed to architect_generate_prd"
    else:
        next_step = "Idea needs work. Address weaknesses and re-validate"

    return success_response(result, next_step=next_step)


async def handle_architect_generate_prd(args: dict[str, Any], state: StateManager) -> str:
    """Generate PRD using IdeaRalph."""
    from .integrations import IdeaRalphIntegration

    idearalph = IdeaRalphIntegration()
    prd = await idearalph.generate_prd(
        idea=args["idea"],
        level=args.get("level", "science-fair")
    )

    return success_response(
        {
            "prd": {
                "idea": prd.idea[:200] + "..." if len(prd.idea) > 200 else prd.idea,
                "level": prd.level,
                "content": prd.content
            }
        },
        next_step="Call architect_init with the idea to create the project"
    )


async def handle_architect_load_context(args: dict[str, Any], state: StateManager) -> str:
    """Load context from Mind."""
    from .integrations import MindIntegration

    mind = MindIntegration()
    if state.mind_user_id:
        mind.set_user_id(state.mind_user_id)

    result = await mind.get_relevant_context(
        project_idea=args["query"],
        project_type=args.get("project_type")
    )

    return success_response({
        "context": {
            "retrieval_id": result.retrieval_id,
            "memories": [
                {
                    "id": m.id,
                    "content": m.content,
                    "type": m.content_type,
                    "salience": m.salience
                }
                for m in result.memories
            ],
            "count": len(result.memories)
        }
    })


async def handle_architect_get_gotchas(args: dict[str, Any], state: StateManager) -> str:
    """Get gotchas from Spawner."""
    from .integrations import SpawnerIntegration

    spawner = SpawnerIntegration()
    result = await spawner.get_gotchas(
        stack=args.get("stack"),
        situation=args.get("situation")
    )

    return success_response({
        "gotchas": {
            "stack": result.stack,
            "warnings": result.gotchas,
            "count": len(result.gotchas)
        }
    })


async def handle_architect_full_pipeline(args: dict[str, Any], state: StateManager) -> str:
    """Run full pipeline: validate -> PRD -> plan -> spawn."""
    from .integrations import IdeaRalphIntegration, MindIntegration, SpawnerIntegration

    steps_completed = []
    pipeline_data: dict[str, Any] = {}

    # Step 1: Validate idea (unless skipped)
    if not args.get("skip_validation", False):
        idearalph = IdeaRalphIntegration()
        validation = await idearalph.validate_idea(args["idea"])
        pipeline_data["validation"] = {
            "average_score": validation.scores.average,
            "is_viable": validation.is_viable,
            "strengths": validation.strengths[:3],
            "weaknesses": validation.weaknesses[:3]
        }
        steps_completed.append("idea_validation")

        # Auto-refine if needed
        if args.get("auto_refine", True) and validation.scores.average < 8.0:
            refined = await idearalph.refine_idea(
                args["idea"],
                target_score=8.0,
                mode="target"
            )
            pipeline_data["refinement"] = {
                "original_score": refined.get("starting_score"),
                "final_score": refined.get("final_score"),
                "iterations": refined.get("iterations", 0)
            }
            steps_completed.append("idea_refinement")

    # Step 2: Generate PRD
    idearalph = IdeaRalphIntegration()
    prd = await idearalph.generate_prd(
        idea=args["idea"],
        level=args.get("prd_level", "science-fair")
    )
    pipeline_data["prd"] = {
        "level": prd.level,
        "sections": list(prd.content.keys()) if isinstance(prd.content, dict) else []
    }
    steps_completed.append("prd_generation")

    # Step 3: Load context from Mind
    mind = MindIntegration()
    if state.mind_user_id:
        mind.set_user_id(state.mind_user_id)
    context = await mind.get_relevant_context(args["idea"])
    pipeline_data["context"] = {
        "memories_found": len(context.memories)
    }
    steps_completed.append("context_retrieval")

    # Step 4: Create project
    try:
        project = await state.create_project(
            args["name"],
            prd.content.get("summary", {}).get("idea", args["idea"]) if isinstance(prd.content, dict) else args["idea"],
            args["idea"]
        )
        pipeline_data["project"] = {
            "id": project.id,
            "name": project.name
        }
        steps_completed.append("project_creation")

        # Step 5: Create plan
        orchestrator = AgentOrchestrator(state)
        plan = await orchestrator.plan_project(project.idea)
        pipeline_data["plan"] = {
            "phases": len(plan.phases),
            "teams": plan.team_structure.get("teams", []),
            "estimated_sprints": plan.estimated_sprints
        }
        steps_completed.append("planning")

        # Step 6: Spawn teams
        team_result = await orchestrator.spawn_team_structure(project.id)
        pipeline_data["teams"] = {
            "total_teams": team_result["structure"]["total_teams"],
            "total_agents": team_result["structure"]["total_agents"]
        }
        steps_completed.append("team_spawning")

        # Step 7: Get gotchas for the stack
        spawner = SpawnerIntegration()
        detected_stack = ["nextjs", "supabase", "typescript"]  # Default stack
        gotchas = await spawner.get_gotchas(stack=detected_stack)
        pipeline_data["gotchas"] = {
            "count": len(gotchas.gotchas),
            "critical": len([g for g in gotchas.gotchas if g.get("severity") == "critical"])
        }
        steps_completed.append("gotcha_check")

    except Exception as e:
        logger.error("Pipeline error", error=str(e))
        return error_response(
            "PIPELINE_ERROR",
            f"Pipeline failed at step: {steps_completed[-1] if steps_completed else 'start'}",
            details={"error": str(e), "completed_steps": steps_completed}
        )

    return success_response(
        {
            "pipeline": {
                "steps_completed": steps_completed,
                **pipeline_data
            }
        },
        next_step="Call architect_create_sprint to start the first sprint"
    )


async def handle_architect_smart_assign(args: dict[str, Any], state: StateManager) -> str:
    """Smart task assignment with skill loading."""
    from .integrations import SpawnerIntegration

    project = state.get_active_project()
    if not project or not project.current_sprint_id:
        return error_response(
            "NO_ACTIVE_SPRINT",
            "No active project or sprint",
            help_text="Create a sprint with architect_create_sprint first"
        )

    team_type = validate_team_type(args["team"])
    if not team_type:
        return error_response(
            "INVALID_TEAM_TYPE",
            f"Invalid team type: {args['team']}",
            details={"valid_teams": VALID_TEAM_TYPES}
        )

    # Load skills for the team
    spawner = SpawnerIntegration()
    skill_results = await spawner.load_skills_for_team(team_type)
    loaded_skills = [r.skill_id for r in skill_results if r.success]

    # If feature specified, also load feature squad
    feature_skills = []
    if args.get("feature"):
        feature_skills = await spawner.get_squad_for_feature(args["feature"])

    # Get gotchas for the task
    gotchas = await spawner.get_gotchas(
        situation=args["description"]
    )

    # Create the task
    try:
        task = await state.add_task(
            project.id,
            project.current_sprint_id,
            args["title"],
            args["description"],
            team_type,
            args.get("priority", 3),
            [],  # dependencies
            []   # acceptance criteria
        )

        return success_response({
            "task": {
                "id": task.id,
                "title": task.title,
                "team": task.team.value,
                "status": task.status.value
            },
            "skills_loaded": {
                "team_skills": loaded_skills,
                "feature_skills": feature_skills
            },
            "gotchas": {
                "count": len(gotchas.gotchas),
                "warnings": gotchas.gotchas[:3]  # Top 3 warnings
            }
        })
    except ValueError as e:
        return error_response("VALIDATION_ERROR", str(e))


async def handle_architect_load_skill_pack(args: dict[str, Any], state: StateManager) -> str:
    """Load a Spawner skill pack for specialized knowledge."""
    from .integrations import SpawnerIntegration

    spawner = SpawnerIntegration()
    pack_name = args["pack"]
    feature = args.get("feature")

    skills_loaded = []
    squad_skills = []

    # Load skill pack via Spawner
    if spawner.mcp_caller:
        try:
            result = await spawner.mcp_caller("spawner_skills", {
                "action": "pack",
                "pack": pack_name
            })
            for skill in result.get("skills", []):
                skills_loaded.append({
                    "id": skill.get("id", ""),
                    "name": skill.get("name", ""),
                    "description": skill.get("description", "")[:100]
                })
        except Exception as e:
            logger.warning("Spawner skill pack load failed", pack=pack_name, error=str(e))

    # If feature squad requested, load that too
    if feature:
        squad_skills = await spawner.get_squad_for_feature(feature)

    # Fallback skill pack definitions
    if not skills_loaded:
        skill_packs = {
            "data-science": [
                {"id": "statistics-fundamentals", "name": "Statistics Fundamentals", "description": "Statistical analysis and inference"},
                {"id": "ml-supervised", "name": "Supervised Learning", "description": "Classification, regression, ensemble methods"},
                {"id": "ml-unsupervised", "name": "Unsupervised Learning", "description": "Clustering, dimensionality reduction"},
                {"id": "nlp-patterns", "name": "NLP Patterns", "description": "Text processing and language models"},
                {"id": "time-series", "name": "Time Series Analysis", "description": "Forecasting and temporal patterns"},
                {"id": "data-visualization", "name": "Data Visualization", "description": "Charts, dashboards, storytelling"},
                {"id": "feature-engineering", "name": "Feature Engineering", "description": "Data transformation and feature creation"}
            ],
            "ai": [
                {"id": "llm-architect", "name": "LLM Architect", "description": "Large language model integration"},
                {"id": "rag-engineer", "name": "RAG Engineer", "description": "Retrieval-augmented generation"},
                {"id": "prompt-engineer", "name": "Prompt Engineer", "description": "Prompt design and optimization"},
                {"id": "ai-safety", "name": "AI Safety", "description": "Guardrails and safety patterns"}
            ],
            "startup": [
                {"id": "yc-playbook", "name": "YC Playbook", "description": "Startup launch patterns"},
                {"id": "growth-strategy", "name": "Growth Strategy", "description": "User acquisition and retention"},
                {"id": "product-strategy", "name": "Product Strategy", "description": "Roadmap and prioritization"},
                {"id": "mvp-patterns", "name": "MVP Patterns", "description": "Minimum viable product design"}
            ],
            "essentials": [
                {"id": "sveltekit", "name": "SvelteKit", "description": "SvelteKit framework patterns"},
                {"id": "supabase-backend", "name": "Supabase Backend", "description": "Supabase database and auth"},
                {"id": "typescript-strict", "name": "TypeScript Strict", "description": "Type-safe development"},
                {"id": "tailwind-ui", "name": "Tailwind UI", "description": "Utility-first CSS"}
            ]
        }
        skills_loaded = skill_packs.get(pack_name, [])

    return success_response({
        "skill_pack": {
            "name": pack_name,
            "skills_loaded": len(skills_loaded),
            "skills": skills_loaded
        },
        "feature_squad": squad_skills if squad_skills else None
    })


async def handle_architect_search_skills(args: dict[str, Any], state: StateManager) -> str:
    """Search Spawner's skill library."""
    from .integrations import SpawnerIntegration

    spawner = SpawnerIntegration()
    query = args["query"]
    tag = args.get("tag")
    limit = args.get("limit", 10)

    skills = await spawner.search_skills(query, tag, limit)

    return success_response({
        "search": {
            "query": query,
            "tag": tag,
            "results": len(skills),
            "skills": [s.to_dict() for s in skills]
        }
    })


async def handle_architect_smart_discover(args: dict[str, Any], state: StateManager) -> str:
    """Smart skill discovery using full MCP stack."""
    from .integrations import SmartSkillDiscovery, DiscoveryContext

    discovery = SmartSkillDiscovery()

    # Set Mind user ID if connected
    if state.mind_user_id:
        discovery.mind.set_user_id(state.mind_user_id)

    # Build context from args and active project
    project = state.get_active_project()
    context = DiscoveryContext(
        project_name=project.name if project else None,
        project_idea=project.idea if project else None,
        tech_stack=args.get("tech_stack", []),
        task_description=args.get("task_description")
    )

    # If no tech stack provided, try to detect from project
    if not context.tech_stack and project and project.idea:
        # Simple detection from idea
        idea_lower = project.idea.lower()
        detected = []
        if "supabase" in idea_lower:
            detected.append("supabase")
        if "next" in idea_lower:
            detected.append("nextjs")
        if "svelte" in idea_lower:
            detected.append("sveltekit")
        if "typescript" in idea_lower or "ts" in idea_lower:
            detected.append("typescript")
        context.tech_stack = detected

    # Run smart discovery
    result = await discovery.discover_skills(
        query=args["query"],
        context=context,
        use_mind=args.get("use_mind", True),
        use_muse=args.get("use_muse", True),
        limit=args.get("limit", 10)
    )

    # Record the selection for learning
    if result.skills:
        await discovery.record_skill_selection(
            query=args["query"],
            selected_skills=[s.id for s in result.skills],
            context=context
        )

    return success_response({
        "smart_discovery": {
            "query": args["query"],
            "confidence": result.confidence,
            "skills": [
                {
                    "id": s.id,
                    "name": s.name,
                    "description": s.description[:100] if s.description else "",
                    "tags": s.tags
                }
                for s in result.skills
            ],
            "discovery_info": {
                "expanded_queries": result.expanded_queries[:10],
                "mind_suggestions": result.mind_suggestions,
                "muse_analogies": result.muse_analogies,
                "sources_searched": len(result.search_sources)
            },
            "context_used": {
                "project": context.project_name,
                "tech_stack": context.tech_stack,
                "task": context.task_description[:50] if context.task_description else None
            }
        }
    })


async def handle_architect_enforce_scope(args: dict[str, Any], state: StateManager) -> str:
    """Enforce scope boundaries during task execution."""
    task_id = args["task_id"]
    elapsed_ms = args["elapsed_ms"]
    original_scope = args["original_scope"]
    current_output = args.get("current_output", {})

    # Check for scope drift
    planned_deliverables = set(original_scope.get("deliverables", []))
    exclusions = set(original_scope.get("exclusions", []))
    modified_files = set(current_output.get("modified_files", []))

    # Calculate drift
    unexpected_modifications = modified_files - planned_deliverables
    exclusion_violations = modified_files & exclusions

    drift_detected = len(unexpected_modifications) > 0 or len(exclusion_violations) > 0
    critical_drift = len(exclusion_violations) > 0

    # Time-based scope reminder (every 2 minutes)
    should_remind = elapsed_ms > 120000 and (elapsed_ms // 120000) != ((elapsed_ms - 1000) // 120000)

    response = {
        "task_id": task_id,
        "elapsed_ms": elapsed_ms,
        "scope_status": "critical_drift" if critical_drift else "drift" if drift_detected else "on_track",
        "analysis": {
            "planned_deliverables": list(planned_deliverables),
            "modified_files": list(modified_files),
            "unexpected": list(unexpected_modifications),
            "exclusion_violations": list(exclusion_violations)
        }
    }

    if critical_drift:
        response["action"] = "pause"
        response["reason"] = f"Modified excluded files: {', '.join(exclusion_violations)}"
    elif drift_detected and len(unexpected_modifications) > 3:
        response["action"] = "review"
        response["reason"] = f"Significant scope drift: {len(unexpected_modifications)} unexpected files"
    elif should_remind:
        response["action"] = "remind"
        response["scope_reminder"] = original_scope.get("acceptance_criteria", [])
    else:
        response["action"] = "continue"

    return success_response(response)


async def handle_architect_review_loop(args: dict[str, Any], state: StateManager) -> str:
    """Run a recursive review cycle on a task."""
    task_id = args["task_id"]
    verification = args["verification_result"]
    max_iterations = args.get("max_iterations", 3)

    # Get current iteration from task metadata (or default to 1)
    task_entry = state.get_task(task_id)
    if not task_entry:
        return error_response("NOT_FOUND", f"Task {task_id} not found")

    _, _, task = task_entry
    current_iteration = task.metadata.get("review_iteration", 1) if hasattr(task, 'metadata') else 1

    # Check quality gates
    tests = verification.get("tests", {})
    lint = verification.get("lint", {})
    scope = verification.get("scope", {})

    test_pass_rate = tests.get("passed", 0) / max(tests.get("total", 1), 1)
    lint_errors = lint.get("critical_errors", 0)
    scope_adherence = scope.get("adherence_percentage", 100)

    # Determine action
    all_gates_pass = test_pass_rate == 1.0 and lint_errors == 0 and scope_adherence >= 90

    if all_gates_pass:
        action = "complete"
        recommendation = "All quality gates passed. Task is ready for completion."
    elif current_iteration >= max_iterations:
        action = "complete"
        recommendation = f"Max iterations ({max_iterations}) reached. Review manually before completing."
    else:
        action = "correct"
        issues = []
        if test_pass_rate < 1.0:
            issues.append(f"Tests: {tests.get('failed', 0)} failures")
        if lint_errors > 0:
            issues.append(f"Lint: {lint_errors} critical errors")
        if scope_adherence < 90:
            issues.append(f"Scope: {scope_adherence:.0f}% adherence")
        recommendation = f"Fix issues: {', '.join(issues)}"

    return success_response({
        "review": {
            "task_id": task_id,
            "iteration": current_iteration,
            "max_iterations": max_iterations,
            "action": action,
            "recommendation": recommendation,
            "gates": {
                "test_pass_rate": f"{test_pass_rate * 100:.0f}%",
                "lint_errors": lint_errors,
                "scope_adherence": f"{scope_adherence:.0f}%"
            }
        }
    })


async def handle_architect_check_quality_gates(args: dict[str, Any], state: StateManager) -> str:
    """Check quality gates for a task."""
    task_id = args["task_id"]
    verification = args["verification_result"]

    tests = verification.get("tests", {})
    lint = verification.get("lint", {})
    scope = verification.get("scope", {})

    gates = []

    # Test pass rate gate (blocking)
    test_total = tests.get("total", 0)
    test_passed = tests.get("passed", 0)
    test_pass_rate = test_passed / max(test_total, 1)
    gates.append({
        "name": "test_pass_rate",
        "threshold": "100%",
        "actual": f"{test_pass_rate * 100:.0f}%",
        "passed": test_pass_rate == 1.0,
        "blocking": True
    })

    # Lint errors gate (blocking)
    lint_errors = lint.get("critical_errors", 0)
    gates.append({
        "name": "lint_critical_errors",
        "threshold": "0",
        "actual": str(lint_errors),
        "passed": lint_errors == 0,
        "blocking": True
    })

    # Scope coverage gate (non-blocking)
    scope_adherence = scope.get("adherence_percentage", 100)
    gates.append({
        "name": "scope_coverage",
        "threshold": "90%",
        "actual": f"{scope_adherence:.0f}%",
        "passed": scope_adherence >= 90,
        "blocking": False
    })

    all_blocking_pass = all(g["passed"] for g in gates if g["blocking"])
    all_pass = all(g["passed"] for g in gates)

    return success_response({
        "quality_gates": {
            "task_id": task_id,
            "overall": "pass" if all_blocking_pass else "fail",
            "all_gates_pass": all_pass,
            "gates": gates
        }
    })


async def handle_architect_evaluate_plan(args: dict[str, Any], state: StateManager) -> str:
    """Evaluate the current plan on multiple dimensions."""
    from .integrations import PlanEvaluator, MindIntegration

    project = state.get_active_project()
    if not project:
        return error_response("NO_ACTIVE_PROJECT", "No active project found")

    if not project.architecture:
        return error_response(
            "NO_PLAN",
            "No execution plan found",
            help_text="Run architect_plan first to create a plan"
        )

    evaluator = PlanEvaluator()

    # Connect Mind for learning
    mind = MindIntegration()
    if state.mind_user_id:
        mind.set_user_id(state.mind_user_id)
    evaluator.set_mind(mind)

    # Get tech stack from args or detect from project
    tech_stack = args.get("tech_stack", [])
    if not tech_stack and project.idea:
        idea_lower = project.idea.lower()
        if "supabase" in idea_lower:
            tech_stack.append("supabase")
        if "next" in idea_lower:
            tech_stack.append("nextjs")
        if "typescript" in idea_lower:
            tech_stack.append("typescript")

    # Evaluate the plan
    evaluation = await evaluator.evaluate_plan(
        plan=project.architecture,
        project_name=project.name,
        tech_stack=tech_stack
    )

    return success_response({
        "evaluation": evaluation.to_dict()
    })


async def handle_architect_record_plan_outcome(args: dict[str, Any], state: StateManager) -> str:
    """Record the actual outcome of a plan for learning."""
    from .integrations import PlanEvaluator, MindIntegration

    project = state.get_active_project()
    if not project:
        return error_response("NO_ACTIVE_PROJECT", "No active project found")

    evaluator = PlanEvaluator()

    # Connect Mind for learning
    mind = MindIntegration()
    if state.mind_user_id:
        mind.set_user_id(state.mind_user_id)
    evaluator.set_mind(mind)

    # Record the outcome
    await evaluator.record_plan_outcome(
        plan_id=project.id,
        success=args["success"],
        completion_rate=args["completion_rate"],
        actual_sprints=args["actual_sprints"],
        lessons=args.get("lessons")
    )

    return success_response({
        "recorded": True,
        "project": project.name,
        "outcome": {
            "success": args["success"],
            "completion_rate": f"{args['completion_rate'] * 100:.0f}%",
            "actual_sprints": args["actual_sprints"],
            "lessons_count": len(args.get("lessons", []))
        },
        "message": "Outcome recorded in Mind for future learning"
    })


async def handle_architect_project_manager_review(args: dict[str, Any], state: StateManager) -> str:
    """Project Manager's final review of a sprint."""
    project = state.get_active_project()
    if not project:
        return error_response("NO_ACTIVE_PROJECT", "No active project found")

    sprint_id = args.get("sprint_id", project.current_sprint_id)
    if not sprint_id:
        return error_response("NO_ACTIVE_SPRINT", "No active sprint found")

    sprint_entry = state.get_sprint(sprint_id)
    if not sprint_entry:
        return error_response("NOT_FOUND", f"Sprint {sprint_id} not found")

    _, sprint = sprint_entry

    # Gather team statuses
    team_statuses = []
    for team in project.teams:
        team_tasks = [t for t in sprint.tasks if t.team == team.type]
        completed = len([t for t in team_tasks if t.status == TaskStatus.COMPLETED])
        total = len(team_tasks)
        team_statuses.append({
            "team": team.name,
            "type": team.type.value,
            "tasks_completed": completed,
            "tasks_total": total,
            "completion_rate": f"{(completed / max(total, 1)) * 100:.0f}%"
        })

    # Overall sprint metrics
    total_tasks = len(sprint.tasks)
    completed_tasks = len([t for t in sprint.tasks if t.status == TaskStatus.COMPLETED])
    blocked_tasks = len([t for t in sprint.tasks if t.status == TaskStatus.BLOCKED])
    in_progress = len([t for t in sprint.tasks if t.status == TaskStatus.IN_PROGRESS])

    completion_rate = completed_tasks / max(total_tasks, 1)

    # Make go/no-go decision
    if completion_rate >= 0.9 and blocked_tasks == 0:
        decision = "GO"
        recommendation = "Sprint completed successfully. Ready for next sprint."
    elif completion_rate >= 0.7:
        decision = "CONDITIONAL_GO"
        recommendation = f"Sprint mostly complete ({completion_rate * 100:.0f}%). Consider carrying over {total_tasks - completed_tasks} incomplete tasks."
    else:
        decision = "NO_GO"
        recommendation = f"Sprint not ready ({completion_rate * 100:.0f}% complete, {blocked_tasks} blocked). Address blockers before proceeding."

    return success_response({
        "pm_review": {
            "sprint": sprint.name,
            "sprint_id": sprint.id,
            "status": sprint.status.value,
            "decision": decision,
            "recommendation": recommendation,
            "metrics": {
                "total_tasks": total_tasks,
                "completed": completed_tasks,
                "blocked": blocked_tasks,
                "in_progress": in_progress,
                "completion_rate": f"{completion_rate * 100:.0f}%"
            },
            "team_statuses": team_statuses
        }
    })


# Tool handler dispatch
TOOL_HANDLERS = {
    "architect_init": handle_architect_init,
    "architect_plan": handle_architect_plan,
    "architect_spawn_teams": handle_architect_spawn_teams,
    "architect_create_sprint": handle_architect_create_sprint,
    "architect_add_task": handle_architect_add_task,
    "architect_update_task": handle_architect_update_task,
    "architect_get_task": handle_architect_get_task,
    "architect_list_tasks": handle_architect_list_tasks,
    "architect_delete_task": handle_architect_delete_task,
    "architect_complete_sprint": handle_architect_complete_sprint,
    "architect_log": handle_architect_log,
    "architect_check_integration": handle_architect_check_integration,
    "architect_supervisor_review": handle_architect_supervisor_review,
    "architect_status": handle_architect_status,
    "architect_get_logs": handle_architect_get_logs,
    "architect_connect_mind": handle_architect_connect_mind,
    "architect_remember": handle_architect_remember,
    "architect_list_projects": handle_architect_list_projects,
    "architect_set_active_project": handle_architect_set_active_project,
    "architect_delete_project": handle_architect_delete_project,
    "architect_get_team": handle_architect_get_team,
    # New orchestration tools
    "architect_validate_idea": handle_architect_validate_idea,
    "architect_generate_prd": handle_architect_generate_prd,
    "architect_load_context": handle_architect_load_context,
    "architect_get_gotchas": handle_architect_get_gotchas,
    "architect_full_pipeline": handle_architect_full_pipeline,
    "architect_smart_assign": handle_architect_smart_assign,
    # Spawner skill tools
    "architect_load_skill_pack": handle_architect_load_skill_pack,
    "architect_search_skills": handle_architect_search_skills,
    "architect_smart_discover": handle_architect_smart_discover,
    # Scope & quality tools
    "architect_enforce_scope": handle_architect_enforce_scope,
    "architect_review_loop": handle_architect_review_loop,
    "architect_check_quality_gates": handle_architect_check_quality_gates,
    "architect_project_manager_review": handle_architect_project_manager_review,
    # Plan evaluation tools
    "architect_evaluate_plan": handle_architect_evaluate_plan,
    "architect_record_plan_outcome": handle_architect_record_plan_outcome,
}


# --- MCP Server Setup ---

@server.list_tools()
async def list_tools() -> list[Tool]:
    """Return the list of available tools."""
    return TOOLS


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle tool calls with structured error handling."""
    state = await get_state_manager()

    handler = TOOL_HANDLERS.get(name)
    if not handler:
        result = error_response("UNKNOWN_TOOL", f"Unknown tool: {name}")
        return [TextContent(type="text", text=result)]

    try:
        result = await handler(arguments, state)
        return [TextContent(type="text", text=result)]
    except ValueError as e:
        logger.warning("Validation error", tool=name, error=str(e))
        result = error_response("VALIDATION_ERROR", str(e))
        return [TextContent(type="text", text=result)]
    except Exception as e:
        logger.error("Tool error", tool=name, error=str(e))
        result = error_response(
            "INTERNAL_ERROR",
            "An unexpected error occurred",
            details={"error_type": type(e).__name__}
        )
        return [TextContent(type="text", text=result)]


async def run_server():
    """Run the MCP server."""
    logger.info("Starting Architect MCP Server")
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


def main():
    """Entry point."""
    asyncio.run(run_server())


if __name__ == "__main__":
    main()
