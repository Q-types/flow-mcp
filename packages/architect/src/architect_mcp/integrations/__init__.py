"""
Integrations with external MCP servers.

The Architect orchestrates these integrations:
- IdeaRalph: Idea validation, PRD generation, design specs
- Spawner: Skill discovery, loading, and code validation
- Mind: Persistent memory and learning from outcomes
- SmartDiscovery: Multi-MCP skill discovery pipeline
"""

from .idearalph import IdeaRalphIntegration, PMFScores, ValidationResult as IdeaValidationResult
from .mind import MindIntegration, Memory, RetrievalResult, DecisionOutcome
from .spawner import SpawnerIntegration, Skill, SkillLoadResult, GotchaResult
from .smart_discovery import SmartSkillDiscovery, SkillDiscoveryResult, DiscoveryContext
from .plan_evaluation import PlanEvaluator, PlanEvaluation, ComplexityMetrics

__all__ = [
    # IdeaRalph
    "IdeaRalphIntegration",
    "PMFScores",
    "IdeaValidationResult",
    # Mind
    "MindIntegration",
    "Memory",
    "RetrievalResult",
    "DecisionOutcome",
    # Spawner
    "SpawnerIntegration",
    "Skill",
    "SkillLoadResult",
    "GotchaResult",
    # Smart Discovery
    "SmartSkillDiscovery",
    "SkillDiscoveryResult",
    "DiscoveryContext",
    # Plan Evaluation
    "PlanEvaluator",
    "PlanEvaluation",
    "ComplexityMetrics",
]
