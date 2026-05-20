"""
Plan Evaluation System for measuring implementation plan quality.

Evaluates plans on multiple dimensions:
- Complexity: How complex is the plan to execute?
- Feasibility: Is it achievable with available resources?
- Clarity: Are requirements and success criteria well-defined?
- Cohesion: Do the pieces fit together logically?
- Risk: What's the risk profile?

Stores evaluations in Mind for learning which plan characteristics
lead to successful outcomes.
"""

from dataclasses import dataclass, field
from typing import Any
from datetime import datetime
import math
import structlog

logger = structlog.get_logger()


@dataclass
class ComplexityMetrics:
    """Complexity breakdown for a plan."""
    team_count: int = 0
    phase_count: int = 0
    task_count: int = 0
    dependency_depth: int = 0  # Longest dependency chain
    integration_points: int = 0  # Cross-team handoffs
    tech_stack_size: int = 0

    # Derived scores (0-10 scale, higher = more complex)
    team_complexity: float = 0.0
    structural_complexity: float = 0.0
    integration_complexity: float = 0.0
    overall_complexity: float = 0.0

    def calculate_scores(self) -> None:
        """Calculate complexity scores from raw metrics."""
        # Team complexity: 1-3 teams = low, 4-6 = medium, 7+ = high
        self.team_complexity = min(10, self.team_count * 1.5)

        # Structural: phases * average_tasks_per_phase
        avg_tasks = self.task_count / max(self.phase_count, 1)
        self.structural_complexity = min(10, (self.phase_count * 1.2) + (avg_tasks * 0.3))

        # Integration: dependency depth + cross-team points
        self.integration_complexity = min(10, (self.dependency_depth * 1.5) + (self.integration_points * 0.8))

        # Overall: weighted average
        self.overall_complexity = (
            self.team_complexity * 0.25 +
            self.structural_complexity * 0.35 +
            self.integration_complexity * 0.40
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "raw": {
                "team_count": self.team_count,
                "phase_count": self.phase_count,
                "task_count": self.task_count,
                "dependency_depth": self.dependency_depth,
                "integration_points": self.integration_points,
                "tech_stack_size": self.tech_stack_size
            },
            "scores": {
                "team_complexity": round(self.team_complexity, 2),
                "structural_complexity": round(self.structural_complexity, 2),
                "integration_complexity": round(self.integration_complexity, 2),
                "overall": round(self.overall_complexity, 2)
            },
            "level": self._complexity_level()
        }

    def _complexity_level(self) -> str:
        if self.overall_complexity < 3:
            return "low"
        elif self.overall_complexity < 6:
            return "medium"
        elif self.overall_complexity < 8:
            return "high"
        else:
            return "very_high"


@dataclass
class FeasibilityMetrics:
    """Feasibility assessment for a plan."""
    estimated_sprints: int = 0
    resource_availability: float = 1.0  # 0-1, how much of needed resources exist
    skill_coverage: float = 1.0  # 0-1, how well skills match requirements
    external_dependencies: int = 0  # Third-party/external blockers

    # Derived score (0-10, higher = more feasible)
    feasibility_score: float = 0.0

    def calculate_score(self) -> None:
        """Calculate feasibility from metrics."""
        # Base score from resource and skill availability
        base = (self.resource_availability * 5) + (self.skill_coverage * 5)

        # Penalize for long timelines and external deps
        timeline_penalty = min(3, self.estimated_sprints * 0.3)
        external_penalty = min(3, self.external_dependencies * 0.5)

        self.feasibility_score = max(0, base - timeline_penalty - external_penalty)

    def to_dict(self) -> dict[str, Any]:
        return {
            "estimated_sprints": self.estimated_sprints,
            "resource_availability": round(self.resource_availability, 2),
            "skill_coverage": round(self.skill_coverage, 2),
            "external_dependencies": self.external_dependencies,
            "score": round(self.feasibility_score, 2),
            "level": "high" if self.feasibility_score >= 7 else "medium" if self.feasibility_score >= 4 else "low"
        }


@dataclass
class ClarityMetrics:
    """Clarity assessment for plan definition."""
    phases_with_objectives: int = 0
    total_phases: int = 0
    tasks_with_acceptance_criteria: int = 0
    total_tasks: int = 0
    success_metrics_defined: int = 0
    scope_items_defined: int = 0

    # Derived score (0-10, higher = more clear)
    clarity_score: float = 0.0

    def calculate_score(self) -> None:
        """Calculate clarity from metrics."""
        objective_ratio = self.phases_with_objectives / max(self.total_phases, 1)
        criteria_ratio = self.tasks_with_acceptance_criteria / max(self.total_tasks, 1)

        # Weighted score
        self.clarity_score = (
            objective_ratio * 4 +
            criteria_ratio * 4 +
            min(2, self.success_metrics_defined * 0.5)
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "objective_coverage": f"{self.phases_with_objectives}/{self.total_phases}",
            "acceptance_criteria_coverage": f"{self.tasks_with_acceptance_criteria}/{self.total_tasks}",
            "success_metrics_defined": self.success_metrics_defined,
            "scope_items": self.scope_items_defined,
            "score": round(self.clarity_score, 2),
            "level": "high" if self.clarity_score >= 7 else "medium" if self.clarity_score >= 4 else "low"
        }


@dataclass
class CohesionMetrics:
    """Cohesion assessment for plan structure."""
    orphan_tasks: int = 0  # Tasks with no team or unclear ownership
    circular_dependencies: int = 0
    phase_gaps: int = 0  # Phases with no connection to others
    team_handoff_clarity: float = 1.0  # 0-1, how clear are handoffs

    # Derived score (0-10, higher = more cohesive)
    cohesion_score: float = 0.0

    def calculate_score(self) -> None:
        """Calculate cohesion from metrics."""
        # Start at 10, penalize for issues
        self.cohesion_score = 10.0
        self.cohesion_score -= min(3, self.orphan_tasks * 0.5)
        self.cohesion_score -= min(4, self.circular_dependencies * 2.0)
        self.cohesion_score -= min(2, self.phase_gaps * 0.5)
        self.cohesion_score -= (1 - self.team_handoff_clarity) * 3
        self.cohesion_score = max(0, self.cohesion_score)

    def to_dict(self) -> dict[str, Any]:
        return {
            "orphan_tasks": self.orphan_tasks,
            "circular_dependencies": self.circular_dependencies,
            "phase_gaps": self.phase_gaps,
            "team_handoff_clarity": round(self.team_handoff_clarity, 2),
            "score": round(self.cohesion_score, 2),
            "level": "high" if self.cohesion_score >= 7 else "medium" if self.cohesion_score >= 4 else "low"
        }


@dataclass
class RiskMetrics:
    """Risk assessment for a plan."""
    identified_risks: int = 0
    high_severity_risks: int = 0
    mitigations_defined: int = 0
    single_points_of_failure: int = 0
    untested_technologies: int = 0

    # Derived score (0-10, higher = lower risk / better managed)
    risk_score: float = 0.0

    def calculate_score(self) -> None:
        """Calculate risk management score."""
        # More identified risks with mitigations = better
        mitigation_ratio = self.mitigations_defined / max(self.identified_risks, 1)

        # Start at baseline, adjust for factors
        self.risk_score = 5.0 + (mitigation_ratio * 3)
        self.risk_score -= min(3, self.high_severity_risks * 1.0)
        self.risk_score -= min(2, self.single_points_of_failure * 0.5)
        self.risk_score -= min(2, self.untested_technologies * 0.5)
        self.risk_score = max(0, min(10, self.risk_score))

    def to_dict(self) -> dict[str, Any]:
        return {
            "identified_risks": self.identified_risks,
            "high_severity": self.high_severity_risks,
            "mitigations_defined": self.mitigations_defined,
            "single_points_of_failure": self.single_points_of_failure,
            "untested_tech": self.untested_technologies,
            "score": round(self.risk_score, 2),
            "level": "low" if self.risk_score >= 7 else "medium" if self.risk_score >= 4 else "high"
        }


@dataclass
class PlanEvaluation:
    """Complete evaluation of an implementation plan."""
    plan_id: str
    project_name: str
    evaluated_at: datetime = field(default_factory=datetime.now)

    complexity: ComplexityMetrics = field(default_factory=ComplexityMetrics)
    feasibility: FeasibilityMetrics = field(default_factory=FeasibilityMetrics)
    clarity: ClarityMetrics = field(default_factory=ClarityMetrics)
    cohesion: CohesionMetrics = field(default_factory=CohesionMetrics)
    risk: RiskMetrics = field(default_factory=RiskMetrics)

    # Overall assessment
    overall_score: float = 0.0
    recommendation: str = ""
    improvements: list[str] = field(default_factory=list)
    similar_past_plans: list[dict] = field(default_factory=list)

    def calculate_overall(self) -> None:
        """Calculate overall score and generate recommendations."""
        # Calculate component scores
        self.complexity.calculate_scores()
        self.feasibility.calculate_score()
        self.clarity.calculate_score()
        self.cohesion.calculate_score()
        self.risk.calculate_score()

        # Overall is weighted average (complexity is inverted - lower is better)
        complexity_inverted = 10 - self.complexity.overall_complexity
        self.overall_score = (
            complexity_inverted * 0.15 +
            self.feasibility.feasibility_score * 0.25 +
            self.clarity.clarity_score * 0.20 +
            self.cohesion.cohesion_score * 0.20 +
            self.risk.risk_score * 0.20
        )

        # Generate recommendation
        if self.overall_score >= 8:
            self.recommendation = "Excellent plan. Ready for execution."
        elif self.overall_score >= 6:
            self.recommendation = "Good plan with minor improvements possible."
        elif self.overall_score >= 4:
            self.recommendation = "Plan needs refinement before execution."
        else:
            self.recommendation = "Plan requires significant rework."

        # Identify improvements
        self._identify_improvements()

    def _identify_improvements(self) -> None:
        """Identify specific improvements needed."""
        self.improvements = []

        if self.complexity.overall_complexity > 7:
            self.improvements.append(
                f"High complexity ({self.complexity.overall_complexity:.1f}/10). "
                "Consider breaking into smaller phases or reducing team count."
            )

        if self.feasibility.feasibility_score < 5:
            self.improvements.append(
                f"Low feasibility ({self.feasibility.feasibility_score:.1f}/10). "
                "Review resource availability and skill gaps."
            )

        if self.clarity.clarity_score < 5:
            self.improvements.append(
                f"Low clarity ({self.clarity.clarity_score:.1f}/10). "
                "Add acceptance criteria to tasks and define success metrics."
            )

        if self.cohesion.cohesion_score < 6:
            self.improvements.append(
                f"Cohesion issues ({self.cohesion.cohesion_score:.1f}/10). "
                f"Address {self.cohesion.orphan_tasks} orphan tasks and clarify handoffs."
            )

        if self.risk.risk_score < 5:
            self.improvements.append(
                f"Risk concerns ({self.risk.risk_score:.1f}/10). "
                f"Define mitigations for {self.risk.high_severity_risks} high-severity risks."
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "project_name": self.project_name,
            "evaluated_at": self.evaluated_at.isoformat(),
            "metrics": {
                "complexity": self.complexity.to_dict(),
                "feasibility": self.feasibility.to_dict(),
                "clarity": self.clarity.to_dict(),
                "cohesion": self.cohesion.to_dict(),
                "risk": self.risk.to_dict()
            },
            "overall": {
                "score": round(self.overall_score, 2),
                "level": self._overall_level(),
                "recommendation": self.recommendation
            },
            "improvements": self.improvements,
            "similar_past_plans": self.similar_past_plans
        }

    def _overall_level(self) -> str:
        if self.overall_score >= 8:
            return "excellent"
        elif self.overall_score >= 6:
            return "good"
        elif self.overall_score >= 4:
            return "needs_work"
        else:
            return "poor"

    def to_mind_content(self) -> str:
        """Generate content for Mind storage."""
        return (
            f"Plan evaluation for '{self.project_name}': "
            f"Overall={self.overall_score:.1f}/10, "
            f"Complexity={self.complexity.overall_complexity:.1f} ({self.complexity._complexity_level()}), "
            f"Feasibility={self.feasibility.feasibility_score:.1f}, "
            f"Clarity={self.clarity.clarity_score:.1f}, "
            f"Cohesion={self.cohesion.cohesion_score:.1f}, "
            f"Risk={self.risk.risk_score:.1f}. "
            f"Teams={self.complexity.team_count}, Phases={self.complexity.phase_count}, "
            f"Tasks={self.complexity.task_count}. "
            f"Recommendation: {self.recommendation}"
        )


class PlanEvaluator:
    """
    Evaluates implementation plans and learns from outcomes.

    Uses Mind to:
    - Store plan evaluations
    - Retrieve similar past plans for comparison
    - Learn which plan characteristics lead to success
    """

    def __init__(self):
        self.mind = None  # Set via set_mind

    def set_mind(self, mind) -> None:
        """Set Mind integration for learning."""
        self.mind = mind

    async def evaluate_plan(
        self,
        plan: dict[str, Any],
        project_name: str,
        tech_stack: list[str] | None = None
    ) -> PlanEvaluation:
        """
        Evaluate an implementation plan on all dimensions.

        Args:
            plan: The execution plan dictionary
            project_name: Name of the project
            tech_stack: Optional tech stack for context

        Returns:
            PlanEvaluation with all metrics and recommendations
        """
        plan_id = plan.get("project_id", "unknown")
        evaluation = PlanEvaluation(
            plan_id=plan_id,
            project_name=project_name
        )

        # Extract plan components
        phases = plan.get("phases", [])
        teams = plan.get("team_structure", {}).get("teams", [])
        dependencies = plan.get("dependencies", {})
        risks = plan.get("risks", [])

        # Calculate complexity
        evaluation.complexity = self._calculate_complexity(
            phases, teams, dependencies, tech_stack
        )

        # Calculate feasibility
        evaluation.feasibility = self._calculate_feasibility(
            plan, phases, teams
        )

        # Calculate clarity
        evaluation.clarity = self._calculate_clarity(phases)

        # Calculate cohesion
        evaluation.cohesion = self._calculate_cohesion(phases, dependencies)

        # Calculate risk
        evaluation.risk = self._calculate_risk(risks)

        # Get similar past plans from Mind
        if self.mind:
            evaluation.similar_past_plans = await self._get_similar_plans(
                project_name, evaluation.complexity.overall_complexity
            )

        # Calculate overall and recommendations
        evaluation.calculate_overall()

        # Store in Mind for future learning
        if self.mind:
            await self._store_evaluation(evaluation)

        logger.info(
            "Plan evaluated",
            project=project_name,
            overall_score=evaluation.overall_score,
            complexity=evaluation.complexity.overall_complexity
        )

        return evaluation

    def _calculate_complexity(
        self,
        phases: list[dict],
        teams: list[str],
        dependencies: dict[str, list[str]],
        tech_stack: list[str] | None
    ) -> ComplexityMetrics:
        """Calculate complexity metrics from plan structure."""
        metrics = ComplexityMetrics()

        metrics.team_count = len(teams)
        metrics.phase_count = len(phases)

        # Count tasks across phases
        total_tasks = 0
        for phase in phases:
            total_tasks += len(phase.get("tasks", []))
        metrics.task_count = total_tasks

        # Calculate dependency depth (longest chain)
        metrics.dependency_depth = self._calculate_dependency_depth(dependencies)

        # Count integration points (cross-team dependencies)
        metrics.integration_points = self._count_integration_points(phases, teams)

        # Tech stack size
        metrics.tech_stack_size = len(tech_stack) if tech_stack else 0

        metrics.calculate_scores()
        return metrics

    def _calculate_dependency_depth(self, dependencies: dict[str, list[str]]) -> int:
        """Find the longest dependency chain."""
        if not dependencies:
            return 1

        def depth_from(node: str, visited: set) -> int:
            if node in visited:
                return 0  # Circular dependency
            visited.add(node)

            deps = dependencies.get(node, [])
            if not deps:
                return 1

            max_child_depth = 0
            for dep in deps:
                child_depth = depth_from(dep, visited.copy())
                max_child_depth = max(max_child_depth, child_depth)

            return 1 + max_child_depth

        max_depth = 0
        for node in dependencies:
            depth = depth_from(node, set())
            max_depth = max(max_depth, depth)

        return max_depth

    def _count_integration_points(
        self,
        phases: list[dict],
        teams: list[str]
    ) -> int:
        """Count cross-team integration points."""
        integration_points = 0

        for i, phase in enumerate(phases):
            phase_teams = set(phase.get("teams", []))

            # Count unique team pairs that must coordinate
            if len(phase_teams) > 1:
                # Each pair of teams = 1 integration point
                integration_points += len(phase_teams) * (len(phase_teams) - 1) // 2

            # Phase transitions also count
            if i > 0:
                prev_teams = set(phases[i-1].get("teams", []))
                handoff_teams = prev_teams - phase_teams
                integration_points += len(handoff_teams)

        return integration_points

    def _calculate_feasibility(
        self,
        plan: dict,
        phases: list[dict],
        teams: list[str]
    ) -> FeasibilityMetrics:
        """Calculate feasibility metrics."""
        metrics = FeasibilityMetrics()

        metrics.estimated_sprints = plan.get("estimated_sprints", len(phases))

        # Resource availability (placeholder - would need actual data)
        metrics.resource_availability = min(1.0, len(teams) / max(len(phases), 1))

        # Skill coverage (placeholder - would need Spawner integration)
        skills = plan.get("team_structure", {}).get("skills", {})
        if skills:
            total_skills = sum(len(s) for s in skills.values())
            metrics.skill_coverage = min(1.0, total_skills / (len(teams) * 3))
        else:
            metrics.skill_coverage = 0.7  # Default assumption

        # External dependencies
        metrics.external_dependencies = 0
        for phase in phases:
            for task in phase.get("tasks", []):
                if isinstance(task, str) and any(
                    w in task.lower() for w in ["external", "third-party", "api", "integration"]
                ):
                    metrics.external_dependencies += 1

        metrics.calculate_score()
        return metrics

    def _calculate_clarity(self, phases: list[dict]) -> ClarityMetrics:
        """Calculate clarity metrics."""
        metrics = ClarityMetrics()

        metrics.total_phases = len(phases)
        metrics.phases_with_objectives = sum(
            1 for p in phases if p.get("goal") or p.get("objective")
        )

        # Count tasks with acceptance criteria
        total_tasks = 0
        tasks_with_criteria = 0
        success_metrics = 0
        scope_items = 0

        for phase in phases:
            tasks = phase.get("tasks", [])
            total_tasks += len(tasks)

            # For dict tasks, check for acceptance_criteria
            for task in tasks:
                if isinstance(task, dict):
                    if task.get("acceptance_criteria"):
                        tasks_with_criteria += 1
                    if task.get("success_metrics"):
                        success_metrics += len(task.get("success_metrics", []))

            scope_items += len(phase.get("scope", []))

        metrics.total_tasks = total_tasks
        metrics.tasks_with_acceptance_criteria = tasks_with_criteria
        metrics.success_metrics_defined = success_metrics
        metrics.scope_items_defined = scope_items

        metrics.calculate_score()
        return metrics

    def _calculate_cohesion(
        self,
        phases: list[dict],
        dependencies: dict[str, list[str]]
    ) -> CohesionMetrics:
        """Calculate cohesion metrics."""
        metrics = CohesionMetrics()

        # Check for orphan tasks (tasks without clear phase assignment)
        for phase in phases:
            for task in phase.get("tasks", []):
                if isinstance(task, dict) and not task.get("team"):
                    metrics.orphan_tasks += 1

        # Check for circular dependencies
        metrics.circular_dependencies = self._count_circular_deps(dependencies)

        # Check for disconnected phases
        connected_phases = set()
        for node, deps in dependencies.items():
            connected_phases.add(node)
            connected_phases.update(deps)

        all_teams = set()
        for phase in phases:
            all_teams.update(phase.get("teams", []))

        metrics.phase_gaps = len(all_teams - connected_phases)

        # Team handoff clarity (heuristic based on dependency completeness)
        if dependencies:
            defined_deps = len([d for d in dependencies.values() if d])
            metrics.team_handoff_clarity = min(1.0, defined_deps / len(dependencies))
        else:
            metrics.team_handoff_clarity = 0.5

        metrics.calculate_score()
        return metrics

    def _count_circular_deps(self, dependencies: dict[str, list[str]]) -> int:
        """Count circular dependencies in the graph."""
        circular = 0

        def has_cycle(node: str, path: set) -> bool:
            if node in path:
                return True
            path.add(node)
            for dep in dependencies.get(node, []):
                if has_cycle(dep, path.copy()):
                    return True
            return False

        for node in dependencies:
            if has_cycle(node, set()):
                circular += 1

        return circular

    def _calculate_risk(self, risks: list[dict]) -> RiskMetrics:
        """Calculate risk metrics."""
        metrics = RiskMetrics()

        metrics.identified_risks = len(risks)

        for risk in risks:
            severity = risk.get("severity", "").lower()
            if severity in ["high", "critical"]:
                metrics.high_severity_risks += 1

            if risk.get("mitigation"):
                metrics.mitigations_defined += 1

        # Single points of failure (heuristic)
        for risk in risks:
            if "single" in str(risk).lower() or "critical path" in str(risk).lower():
                metrics.single_points_of_failure += 1

        metrics.calculate_score()
        return metrics

    async def _get_similar_plans(
        self,
        project_name: str,
        complexity: float
    ) -> list[dict]:
        """Retrieve similar past plans from Mind."""
        if not self.mind:
            return []

        try:
            # Query for similar plan evaluations
            result = await self.mind.retrieve(
                query=f"plan evaluation complexity {complexity:.0f} project",
                memory_types=["episodic", "semantic"],
                limit=3
            )

            similar = []
            for memory in result.memories:
                # Parse plan info from memory content
                if "Plan evaluation" in memory.content:
                    similar.append({
                        "content": memory.content[:200],
                        "salience": memory.salience
                    })

            return similar
        except Exception as e:
            logger.warning("Failed to get similar plans", error=str(e))
            return []

    async def _store_evaluation(self, evaluation: PlanEvaluation) -> None:
        """Store evaluation in Mind for future learning."""
        if not self.mind:
            return

        try:
            await self.mind.remember(
                content=evaluation.to_mind_content(),
                memory_type="episodic",
                temporal_level=3  # Months-level persistence
            )

            logger.info("Stored plan evaluation in Mind", project=evaluation.project_name)
        except Exception as e:
            logger.warning("Failed to store evaluation", error=str(e))

    async def record_plan_outcome(
        self,
        plan_id: str,
        success: bool,
        completion_rate: float,
        actual_sprints: int,
        lessons: list[str] | None = None
    ) -> None:
        """
        Record the actual outcome of a plan for learning.

        This creates a feedback loop - plans with characteristics
        that led to success will be favored in future recommendations.
        """
        if not self.mind:
            return

        try:
            outcome_quality = 0.8 if success else 0.3
            if completion_rate >= 0.9:
                outcome_quality += 0.2
            elif completion_rate < 0.5:
                outcome_quality -= 0.3

            outcome_quality = max(-1.0, min(1.0, outcome_quality))

            content = (
                f"Plan {plan_id} outcome: {'SUCCESS' if success else 'PARTIAL'}. "
                f"Completion={completion_rate*100:.0f}%, Sprints={actual_sprints}. "
            )
            if lessons:
                content += f"Lessons: {'; '.join(lessons)}"

            await self.mind.remember(
                content=content,
                memory_type="episodic",
                temporal_level=4  # Long-term lesson
            )

            logger.info(
                "Recorded plan outcome",
                plan_id=plan_id,
                success=success,
                outcome_quality=outcome_quality
            )
        except Exception as e:
            logger.warning("Failed to record outcome", error=str(e))
