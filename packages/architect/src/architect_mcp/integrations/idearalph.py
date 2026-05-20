"""
IdeaRalph MCP Integration for idea validation and PRD generation.

Enables Architect to:
- Validate startup ideas with PMF scoring
- Refine ideas until they reach quality thresholds
- Generate Product Requirements Documents
- Design UI/UX specifications
- Generate architecture plans

The Architect uses IdeaRalph as the first step in the pipeline to ensure
ideas are validated before planning and execution begins.
"""

from typing import Any
from dataclasses import dataclass, field
import structlog

logger = structlog.get_logger()


@dataclass
class PMFScores:
    """Product-Market Fit scores from IdeaRalph validation."""
    problem_clarity: float = 0.0
    market_size: float = 0.0
    uniqueness: float = 0.0
    feasibility: float = 0.0
    monetization: float = 0.0
    timing: float = 0.0
    virality: float = 0.0
    defensibility: float = 0.0
    team_fit: float = 0.0
    ralph_factor: float = 0.0

    @property
    def average(self) -> float:
        """Calculate average PMF score."""
        scores = [
            self.problem_clarity, self.market_size, self.uniqueness,
            self.feasibility, self.monetization, self.timing,
            self.virality, self.defensibility, self.team_fit, self.ralph_factor
        ]
        return sum(scores) / len(scores)

    def to_dict(self) -> dict[str, float]:
        """Convert to dictionary."""
        return {
            "problemClarity": self.problem_clarity,
            "marketSize": self.market_size,
            "uniqueness": self.uniqueness,
            "feasibility": self.feasibility,
            "monetization": self.monetization,
            "timing": self.timing,
            "virality": self.virality,
            "defensibility": self.defensibility,
            "teamFit": self.team_fit,
            "ralphFactor": self.ralph_factor,
            "average": self.average
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PMFScores":
        """Create from dictionary."""
        return cls(
            problem_clarity=data.get("problemClarity", 0),
            market_size=data.get("marketSize", 0),
            uniqueness=data.get("uniqueness", 0),
            feasibility=data.get("feasibility", 0),
            monetization=data.get("monetization", 0),
            timing=data.get("timing", 0),
            virality=data.get("virality", 0),
            defensibility=data.get("defensibility", 0),
            team_fit=data.get("teamFit", 0),
            ralph_factor=data.get("ralphFactor", 0)
        )


@dataclass
class ValidationResult:
    """Result from IdeaRalph validation."""
    idea: str
    scores: PMFScores
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)

    @property
    def is_viable(self) -> bool:
        """Check if idea meets minimum viability threshold (7.0)."""
        return self.scores.average >= 7.0

    @property
    def needs_refinement(self) -> bool:
        """Check if idea needs refinement (below 8.5)."""
        return self.scores.average < 8.5


@dataclass
class PRDResult:
    """Result from IdeaRalph PRD generation."""
    idea: str
    level: str  # napkin, science-fair, genius
    content: dict[str, Any] = field(default_factory=dict)


@dataclass
class DesignResult:
    """Result from IdeaRalph design generation."""
    idea: str
    vibe: str  # clean, bold, dark, playful
    color_palette: list[str] = field(default_factory=list)
    typography: dict[str, str] = field(default_factory=dict)
    components: list[dict[str, Any]] = field(default_factory=list)
    references: list[str] = field(default_factory=list)


class IdeaRalphIntegration:
    """
    Integration with IdeaRalph MCP for idea validation and PRD generation.

    IdeaRalph provides:
    - idearalph_validate: Score idea on 10 PMF dimensions
    - idearalph_refine: Iteratively improve idea until target score
    - idearalph_prd: Generate Product Requirements Document
    - idearalph_design: Generate UI/UX design specifications
    - idearalph_architecture: Generate technical architecture

    The Architect uses this as the FIRST step before planning:
    1. validate_idea() - Get PMF scores and feedback
    2. refine_idea() - Improve if score < 8.5
    3. generate_prd() - Create detailed requirements
    4. generate_design() - Create UI/UX specs (optional)
    """

    def __init__(self):
        self.last_validation: ValidationResult | None = None
        self.last_prd: PRDResult | None = None
        self.last_design: DesignResult | None = None

    async def validate_idea(
        self,
        idea: str,
        mcp_caller: Any = None
    ) -> ValidationResult:
        """
        Validate an idea using IdeaRalph's PMF scoring.

        This calls idearalph_validate which scores the idea on:
        - Problem Clarity: How well-defined is the problem?
        - Market Size: How large is the potential market?
        - Uniqueness: How differentiated from competitors?
        - Feasibility: Can it be built with available resources?
        - Monetization: Is the business model clear?
        - Timing: Is the market ready?
        - Virality: Does it have natural growth?
        - Defensibility: Can it build a moat?
        - Team Fit: Is it suited for indie/small teams?
        - Ralph Factor: The X-factor / excitement level

        Args:
            idea: The startup/product idea to validate
            mcp_caller: Optional MCP tool caller for real integration

        Returns:
            ValidationResult with scores and feedback
        """
        logger.info("Validating idea with IdeaRalph", idea_length=len(idea))

        if mcp_caller:
            # Real MCP call
            try:
                result = await mcp_caller(
                    "idearalph_validate",
                    idea=idea
                )
                # Parse the MCP response
                if isinstance(result, dict) and "scores" in result:
                    scores = PMFScores.from_dict(result["scores"])
                    validation = ValidationResult(
                        idea=idea,
                        scores=scores,
                        strengths=result.get("strengths", []),
                        weaknesses=result.get("weaknesses", []),
                        suggestions=result.get("suggestions", [])
                    )
                    self.last_validation = validation
                    return validation
            except Exception as e:
                logger.warning("IdeaRalph MCP call failed, using estimation", error=str(e))

        # Fallback: Estimate scores based on idea keywords
        scores = self._estimate_scores(idea)

        validation = ValidationResult(
            idea=idea,
            scores=scores,
            strengths=self._identify_strengths(idea, scores),
            weaknesses=self._identify_weaknesses(scores),
            suggestions=self._generate_suggestions(scores)
        )

        self.last_validation = validation
        logger.info(
            "Idea validated",
            average_score=scores.average,
            is_viable=validation.is_viable
        )

        return validation

    async def refine_idea(
        self,
        idea: str,
        target_score: float = 8.5,
        max_iterations: int = 5,
        mode: str = "target",
        mcp_caller: Any = None
    ) -> dict[str, Any]:
        """
        Refine an idea using IdeaRalph's iterative improvement.

        Modes:
        - "single": One round of feedback and improvement
        - "target": Keep refining until target score reached
        - "max": Run all iterations to maximize score

        Args:
            idea: The idea to refine
            target_score: Target PMF score (default 8.5)
            max_iterations: Maximum refinement rounds
            mode: Refinement mode (single, target, max)
            mcp_caller: Optional MCP tool caller

        Returns:
            Dict with refined idea and improvement history
        """
        logger.info(
            "Refining idea with IdeaRalph",
            mode=mode,
            target=target_score,
            max_iterations=max_iterations
        )

        if mcp_caller:
            try:
                result = await mcp_caller(
                    "idearalph_refine",
                    idea=idea,
                    mode=mode,
                    targetScore=target_score,
                    maxIterations=max_iterations
                )
                return result
            except Exception as e:
                logger.warning("IdeaRalph refine MCP call failed", error=str(e))

        # Fallback: Return the original idea with suggestions
        validation = await self.validate_idea(idea)

        return {
            "original_idea": idea,
            "refined_idea": idea,
            "iterations": 0,
            "starting_score": validation.scores.average,
            "final_score": validation.scores.average,
            "improvements": validation.suggestions,
            "note": "MCP integration required for actual refinement"
        }

    async def generate_prd(
        self,
        idea: str,
        level: str = "science-fair",
        scores: PMFScores | None = None,
        mcp_caller: Any = None
    ) -> PRDResult:
        """
        Generate a Product Requirements Document using IdeaRalph.

        PRD Levels:
        - "napkin": Quick 1-page sketch (problem, solution, features, metrics)
        - "science-fair": Detailed PRD with personas, user stories, technical considerations
        - "genius": Comprehensive investor-ready doc with TAM/SAM/SOM, business model, GTM

        Args:
            idea: The validated idea
            level: PRD detail level
            scores: Optional pre-existing PMF scores
            mcp_caller: Optional MCP tool caller

        Returns:
            PRDResult with structured requirements
        """
        logger.info("Generating PRD with IdeaRalph", level=level)

        if mcp_caller:
            try:
                params: dict[str, Any] = {"idea": idea, "level": level}
                if scores:
                    params["scores"] = scores.to_dict()

                result = await mcp_caller("idearalph_prd", **params)

                prd = PRDResult(
                    idea=idea,
                    level=level,
                    content=result if isinstance(result, dict) else {}
                )
                self.last_prd = prd
                return prd
            except Exception as e:
                logger.warning("IdeaRalph PRD MCP call failed", error=str(e))

        # Fallback: Generate basic PRD structure
        prd = PRDResult(
            idea=idea,
            level=level,
            content=self._generate_basic_prd(idea, level)
        )
        self.last_prd = prd

        return prd

    async def generate_design(
        self,
        idea: str,
        prd: dict[str, Any] | None = None,
        vibe: str = "clean",
        reference_url: str | None = None,
        mcp_caller: Any = None
    ) -> DesignResult:
        """
        Generate UI/UX design specifications using IdeaRalph.

        Design Vibes:
        - "clean": Minimal, professional
        - "bold": Colorful, striking
        - "dark": Tech/developer focused
        - "playful": Fun, engaging

        Args:
            idea: The startup idea
            prd: Optional PRD content for context
            vibe: Design aesthetic
            reference_url: Optional reference site URL
            mcp_caller: Optional MCP tool caller

        Returns:
            DesignResult with design specifications
        """
        logger.info("Generating design with IdeaRalph", vibe=vibe)

        if mcp_caller:
            try:
                params: dict[str, Any] = {"idea": idea, "vibe": vibe}
                if prd:
                    params["prd"] = prd
                if reference_url:
                    params["referenceUrl"] = reference_url

                result = await mcp_caller("idearalph_design", **params)

                design = DesignResult(
                    idea=idea,
                    vibe=vibe,
                    color_palette=result.get("colorPalette", []),
                    typography=result.get("typography", {}),
                    components=result.get("components", []),
                    references=result.get("references", [])
                )
                self.last_design = design
                return design
            except Exception as e:
                logger.warning("IdeaRalph design MCP call failed", error=str(e))

        # Fallback: Generate basic design specs
        design = DesignResult(
            idea=idea,
            vibe=vibe,
            color_palette=self._get_vibe_colors(vibe),
            typography=self._get_vibe_typography(vibe),
            components=[],
            references=[]
        )
        self.last_design = design

        return design

    async def generate_architecture(
        self,
        idea: str,
        prd: dict[str, Any] | None = None,
        design_spec: dict[str, Any] | None = None,
        tech_preferences: str | None = None,
        mcp_caller: Any = None
    ) -> dict[str, Any]:
        """
        Generate technical architecture using IdeaRalph.

        This bridges Ralph's idea validation with Spawner's skills for building.

        Args:
            idea: The validated idea
            prd: Optional PRD content
            design_spec: Optional design specifications
            tech_preferences: Optional tech stack preferences
            mcp_caller: Optional MCP tool caller

        Returns:
            Architecture plan with recommended Spawner skills
        """
        logger.info("Generating architecture with IdeaRalph")

        if mcp_caller:
            try:
                params: dict[str, Any] = {"idea": idea}
                if prd:
                    params["prd"] = prd
                if design_spec:
                    params["designSpec"] = design_spec
                if tech_preferences:
                    params["techPreferences"] = tech_preferences

                return await mcp_caller("idearalph_architecture", **params)
            except Exception as e:
                logger.warning("IdeaRalph architecture MCP call failed", error=str(e))

        # Fallback: Return basic architecture recommendations
        return {
            "idea": idea,
            "recommended_stack": ["nextjs", "supabase", "typescript", "tailwind"],
            "spawner_skills": [
                "backend", "frontend", "supabase-backend", "tailwind-ui"
            ],
            "components": [
                {"name": "Frontend", "tech": "Next.js + React"},
                {"name": "Backend", "tech": "Supabase"},
                {"name": "Database", "tech": "PostgreSQL"},
                {"name": "Auth", "tech": "Supabase Auth"}
            ],
            "note": "MCP integration required for detailed architecture"
        }

    # --- Private Helper Methods ---

    def _estimate_scores(self, idea: str) -> PMFScores:
        """Estimate PMF scores based on idea keywords (fallback method)."""
        idea_lower = idea.lower()

        # Base scores
        scores = PMFScores(
            problem_clarity=6.0,
            market_size=5.0,
            uniqueness=5.0,
            feasibility=7.0,
            monetization=5.0,
            timing=6.0,
            virality=4.0,
            defensibility=4.0,
            team_fit=7.0,
            ralph_factor=5.0
        )

        # Adjust based on keywords
        if any(w in idea_lower for w in ["ai", "llm", "machine learning", "gpt"]):
            scores.timing = 8.0
            scores.ralph_factor = 7.0

        if any(w in idea_lower for w in ["saas", "subscription", "b2b"]):
            scores.monetization = 7.0
            scores.team_fit = 8.0

        if any(w in idea_lower for w in ["marketplace", "platform", "network"]):
            scores.virality = 6.0
            scores.defensibility = 6.0
            scores.market_size = 7.0

        if any(w in idea_lower for w in ["simple", "focused", "specific"]):
            scores.feasibility = 8.0
            scores.problem_clarity = 7.0

        if any(w in idea_lower for w in ["unique", "novel", "first", "innovative"]):
            scores.uniqueness = 7.0

        return scores

    def _identify_strengths(self, idea: str, scores: PMFScores) -> list[str]:
        """Identify strengths based on scores."""
        strengths = []

        if scores.feasibility >= 7:
            strengths.append("Technically achievable with available resources")
        if scores.team_fit >= 7:
            strengths.append("Well-suited for small team/indie development")
        if scores.timing >= 7:
            strengths.append("Good market timing - favorable trends")
        if scores.monetization >= 7:
            strengths.append("Clear path to revenue")

        return strengths if strengths else ["Idea has potential with refinement"]

    def _identify_weaknesses(self, scores: PMFScores) -> list[str]:
        """Identify weaknesses based on scores."""
        weaknesses = []

        if scores.problem_clarity < 6:
            weaknesses.append("Problem definition needs more clarity")
        if scores.uniqueness < 5:
            weaknesses.append("Limited differentiation from competitors")
        if scores.virality < 5:
            weaknesses.append("No clear viral or growth mechanism")
        if scores.defensibility < 5:
            weaknesses.append("Easy to copy - needs stronger moat")
        if scores.market_size < 5:
            weaknesses.append("Market size may be limited")

        return weaknesses

    def _generate_suggestions(self, scores: PMFScores) -> list[str]:
        """Generate improvement suggestions based on lowest scores."""
        suggestions = []

        # Find lowest scores
        score_map = {
            "problem_clarity": scores.problem_clarity,
            "market_size": scores.market_size,
            "uniqueness": scores.uniqueness,
            "virality": scores.virality,
            "defensibility": scores.defensibility,
            "monetization": scores.monetization
        }

        sorted_scores = sorted(score_map.items(), key=lambda x: x[1])

        for key, score in sorted_scores[:3]:  # Top 3 lowest
            if key == "problem_clarity":
                suggestions.append("Define the specific user pain point more clearly")
            elif key == "uniqueness":
                suggestions.append("Identify what makes this 10x better than alternatives")
            elif key == "virality":
                suggestions.append("Add a sharing mechanism or network effect")
            elif key == "defensibility":
                suggestions.append("Consider data moats, switching costs, or expertise barriers")
            elif key == "market_size":
                suggestions.append("Research TAM/SAM/SOM to validate market opportunity")
            elif key == "monetization":
                suggestions.append("Define pricing model and validate willingness to pay")

        return suggestions

    def _generate_basic_prd(self, idea: str, level: str) -> dict[str, Any]:
        """Generate a basic PRD structure (fallback method)."""
        base = {
            "summary": {
                "idea": idea,
                "level": level
            },
            "problem": "Define the core problem this solves",
            "solution": "Describe how this solves the problem",
            "target_users": "Identify primary user personas",
            "key_features": [
                "Core feature 1",
                "Core feature 2",
                "Core feature 3"
            ],
            "success_metrics": [
                "User engagement metric",
                "Business metric"
            ]
        }

        if level in ["science-fair", "genius"]:
            base["user_stories"] = [
                "As a [user], I want to [action] so that [benefit]"
            ]
            base["technical_requirements"] = [
                "Authentication system",
                "Database for persistence",
                "API for data access"
            ]

        if level == "genius":
            base["market_analysis"] = {
                "tam": "Total Addressable Market",
                "sam": "Serviceable Addressable Market",
                "som": "Serviceable Obtainable Market"
            }
            base["business_model"] = "Revenue model and pricing strategy"
            base["go_to_market"] = "Launch and growth strategy"

        return base

    def _get_vibe_colors(self, vibe: str) -> list[str]:
        """Get color palette for design vibe."""
        palettes = {
            "clean": ["#FFFFFF", "#F8FAFC", "#1E293B", "#3B82F6", "#10B981"],
            "bold": ["#7C3AED", "#EC4899", "#F59E0B", "#10B981", "#1E293B"],
            "dark": ["#0F172A", "#1E293B", "#334155", "#3B82F6", "#22D3EE"],
            "playful": ["#FEF3C7", "#FECACA", "#A5F3FC", "#BBF7D0", "#1E293B"]
        }
        return palettes.get(vibe, palettes["clean"])

    def _get_vibe_typography(self, vibe: str) -> dict[str, str]:
        """Get typography for design vibe."""
        typography = {
            "clean": {
                "heading": "Inter, system-ui, sans-serif",
                "body": "Inter, system-ui, sans-serif",
                "mono": "JetBrains Mono, monospace"
            },
            "bold": {
                "heading": "Poppins, sans-serif",
                "body": "Inter, sans-serif",
                "mono": "Fira Code, monospace"
            },
            "dark": {
                "heading": "Space Grotesk, sans-serif",
                "body": "Inter, sans-serif",
                "mono": "JetBrains Mono, monospace"
            },
            "playful": {
                "heading": "Nunito, sans-serif",
                "body": "Nunito, sans-serif",
                "mono": "Fira Code, monospace"
            }
        }
        return typography.get(vibe, typography["clean"])


# Recommended IdeaRalph workflow for Architect:

IDEARALPH_WORKFLOW = """
## IdeaRalph Integration Workflow

### 1. Idea Validation (Required First Step)
```
validation = await idearalph.validate_idea(idea)
if validation.scores.average < 7.0:
    # Idea needs significant work
    refined = await idearalph.refine_idea(idea, mode="target", target_score=8.0)
```

### 2. PRD Generation
```
# After validation passes (score >= 7.0)
prd = await idearalph.generate_prd(
    idea=validated_idea,
    level="science-fair",  # or "genius" for investor-ready
    scores=validation.scores
)
```

### 3. Design Specification (Optional)
```
design = await idearalph.generate_design(
    idea=validated_idea,
    prd=prd.content,
    vibe="clean"  # clean, bold, dark, playful
)
```

### 4. Architecture Generation
```
# Bridges to Spawner for skill loading
architecture = await idearalph.generate_architecture(
    idea=validated_idea,
    prd=prd.content,
    design_spec=design.__dict__
)
# architecture.spawner_skills tells Spawner what to load
```

### 5. Handoff to Architect Planning
```
# Now Architect can plan with validated requirements
await architect.plan_project(
    idea=validated_idea,
    prd=prd.content,
    architecture=architecture
)
```
"""
