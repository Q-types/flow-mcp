"""
Smart Skill Discovery using the full MCP stack.

Coordinates Mind, Muse, Spawner, and Architect for intelligent skill selection:

1. Mind: Retrieve past successful skill combinations
2. Muse: Expand search with analogies and associations
3. Spawner: Multi-query search across skill library
4. Architect: Context-aware filtering and selection
5. Mind: Store decision for future learning

This creates a learning loop where skill selections improve over time.
"""

from dataclasses import dataclass, field
from typing import Any
import structlog

from .spawner import SpawnerIntegration, Skill
from .mind import MindIntegration

logger = structlog.get_logger()


@dataclass
class SkillDiscoveryResult:
    """Result from smart skill discovery."""
    query: str
    skills: list[Skill] = field(default_factory=list)
    expanded_queries: list[str] = field(default_factory=list)
    mind_suggestions: list[str] = field(default_factory=list)
    muse_analogies: list[str] = field(default_factory=list)
    search_sources: dict[str, int] = field(default_factory=dict)
    confidence: float = 0.0


@dataclass
class DiscoveryContext:
    """Context for skill discovery."""
    project_name: str | None = None
    project_idea: str | None = None
    tech_stack: list[str] = field(default_factory=list)
    team_type: str | None = None
    task_description: str | None = None
    phase: str | None = None


class SmartSkillDiscovery:
    """
    Intelligent skill discovery using the full MCP stack.

    Pipeline:
    1. Mind retrieval: "What worked before for similar tasks?"
    2. Muse expansion: Generate analogies and related concepts
    3. Spawner search: Multi-query search with expanded terms
    4. Ranking: Score skills by frequency, relevance, past success
    5. Learning: Store selection for future improvement
    """

    def __init__(self):
        self.spawner = SpawnerIntegration()
        self.mind = MindIntegration()
        self.muse_caller = None  # Set via set_muse_caller

        # Domain expansion mappings for common concepts
        self._domain_expansions = {
            "database": [
                "database", "sql", "postgres", "schema", "migration",
                "orm", "query", "index", "rls", "supabase", "drizzle",
                "data modeling", "persistence", "storage"
            ],
            "auth": [
                "auth", "authentication", "authorization", "login",
                "session", "jwt", "oauth", "rbac", "permissions",
                "security", "identity", "sso"
            ],
            "frontend": [
                "frontend", "react", "ui", "component", "tailwind",
                "nextjs", "svelte", "state management", "forms",
                "accessibility", "responsive"
            ],
            "backend": [
                "backend", "api", "server", "endpoint", "rest",
                "graphql", "middleware", "validation", "error handling"
            ],
            "api": [
                "api", "rest", "graphql", "openapi", "endpoint",
                "versioning", "rate limiting", "documentation"
            ],
            "testing": [
                "testing", "test", "unit test", "integration test",
                "e2e", "playwright", "vitest", "jest", "coverage"
            ],
            "ai": [
                "ai", "llm", "gpt", "embeddings", "rag", "prompt",
                "vector", "semantic search", "langchain", "agents"
            ],
            "devops": [
                "devops", "ci", "cd", "docker", "kubernetes",
                "deployment", "monitoring", "logging", "infrastructure"
            ]
        }

    def set_muse_caller(self, caller) -> None:
        """Set the Muse MCP caller for analogy generation."""
        self.muse_caller = caller

    async def discover_skills(
        self,
        query: str,
        context: DiscoveryContext | None = None,
        use_mind: bool = True,
        use_muse: bool = True,
        limit: int = 10
    ) -> SkillDiscoveryResult:
        """
        Discover relevant skills using the full MCP stack.

        Args:
            query: The skill search query (e.g., "database", "auth")
            context: Optional project/task context for better matching
            use_mind: Whether to consult Mind for past successes
            use_muse: Whether to use Muse for analogy expansion
            limit: Maximum skills to return

        Returns:
            SkillDiscoveryResult with ranked skills and metadata
        """
        result = SkillDiscoveryResult(query=query)
        skill_scores: dict[str, tuple[Skill, float]] = {}

        # Step 1: Expand query with domain knowledge
        expanded = self._expand_query(query)
        result.expanded_queries = expanded

        # Step 2: Consult Mind for past successful skills
        if use_mind:
            mind_skills = await self._query_mind_for_skills(query, context)
            result.mind_suggestions = mind_skills

            # Boost scores for Mind-suggested skills
            for skill_id in mind_skills:
                if skill_id not in skill_scores:
                    skill_scores[skill_id] = (Skill(id=skill_id, name=skill_id), 0.0)
                skill, score = skill_scores[skill_id]
                skill_scores[skill_id] = (skill, score + 2.0)  # Mind boost

        # Step 3: Use Muse for analogies (if available)
        if use_muse and self.muse_caller:
            analogies = await self._get_muse_analogies(query, context)
            result.muse_analogies = analogies
            expanded.extend(analogies)

        # Step 4: Multi-query search in Spawner
        search_counts: dict[str, int] = {}
        for search_term in expanded:
            skills = await self.spawner.search_skills(search_term, limit=20)
            search_counts[search_term] = len(skills)

            for skill in skills:
                if skill.id not in skill_scores:
                    skill_scores[skill.id] = (skill, 0.0)
                existing_skill, score = skill_scores[skill.id]
                # Score based on: frequency of appearance + tag relevance
                tag_match = 1.0 if query.lower() in [t.lower() for t in skill.tags] else 0.5
                skill_scores[skill.id] = (skill, score + 1.0 + tag_match)

        result.search_sources = search_counts

        # Step 5: Context-aware filtering
        if context:
            skill_scores = self._apply_context_filter(skill_scores, context)

        # Step 6: Rank and select top skills
        ranked = sorted(
            skill_scores.values(),
            key=lambda x: x[1],
            reverse=True
        )[:limit]

        result.skills = [skill for skill, score in ranked]
        result.confidence = self._calculate_confidence(ranked, query)

        logger.info(
            "Smart skill discovery completed",
            query=query,
            expanded_terms=len(expanded),
            skills_found=len(result.skills),
            confidence=result.confidence
        )

        return result

    def _expand_query(self, query: str) -> list[str]:
        """Expand query using domain knowledge."""
        query_lower = query.lower()
        expanded = [query]

        # Check for known domain expansions
        for domain, terms in self._domain_expansions.items():
            if domain in query_lower or query_lower in domain:
                expanded.extend(terms)
                break

        # Add common variations
        if "_" in query:
            expanded.append(query.replace("_", " "))
            expanded.append(query.replace("_", "-"))

        return list(set(expanded))

    async def _query_mind_for_skills(
        self,
        query: str,
        context: DiscoveryContext | None
    ) -> list[str]:
        """Query Mind for past successful skill combinations."""
        try:
            # Build retrieval query
            retrieval_query = f"skills for {query}"
            if context:
                if context.project_idea:
                    retrieval_query += f" in project: {context.project_idea[:100]}"
                if context.tech_stack:
                    retrieval_query += f" with stack: {', '.join(context.tech_stack)}"

            memories = await self.mind.retrieve(
                query=retrieval_query,
                memory_types=["procedural", "episodic"],
                limit=5
            )

            # Extract skill IDs from memories
            skill_suggestions = []
            for memory in memories.memories:
                content = memory.content.lower()
                # Look for skill patterns in memory content
                if "skill" in content or "loaded" in content:
                    # Extract skill-like identifiers (kebab-case words)
                    import re
                    skill_patterns = re.findall(r'\b[a-z]+-[a-z]+(?:-[a-z]+)*\b', content)
                    skill_suggestions.extend(skill_patterns)

            return list(set(skill_suggestions))[:10]

        except Exception as e:
            logger.warning("Mind retrieval failed", error=str(e))
            return []

    async def _get_muse_analogies(
        self,
        query: str,
        context: DiscoveryContext | None
    ) -> list[str]:
        """Use Muse to generate analogies and related concepts."""
        if not self.muse_caller:
            return []

        try:
            # Call Muse to expand with analogies
            result = await self.muse_caller("muse_generate_analogies", {
                "source_content": f"Finding skills for: {query}",
                "source_domain": "software development",
                "limit": 5
            })

            # Extract useful search terms from analogies
            analogies = []
            for analogy in result.get("analogies", []):
                target = analogy.get("target_domain", "")
                if target and target not in analogies:
                    analogies.append(target)

            return analogies[:5]

        except Exception as e:
            logger.warning("Muse analogy generation failed", error=str(e))
            return []

    def _apply_context_filter(
        self,
        skill_scores: dict[str, tuple[Skill, float]],
        context: DiscoveryContext
    ) -> dict[str, tuple[Skill, float]]:
        """Apply context-aware filtering to skill scores."""
        filtered = {}

        for skill_id, (skill, score) in skill_scores.items():
            adjusted_score = score

            # Boost if skill tags match tech stack
            if context.tech_stack:
                for tech in context.tech_stack:
                    if tech.lower() in [t.lower() for t in skill.tags]:
                        adjusted_score += 1.5

            # Boost if skill name contains task-relevant keywords
            if context.task_description:
                task_words = context.task_description.lower().split()
                for word in task_words:
                    if len(word) > 3 and word in skill.name.lower():
                        adjusted_score += 0.5

            filtered[skill_id] = (skill, adjusted_score)

        return filtered

    def _calculate_confidence(
        self,
        ranked_skills: list[tuple[Skill, float]],
        query: str
    ) -> float:
        """Calculate confidence score for the discovery result."""
        if not ranked_skills:
            return 0.0

        # Factors: number of skills, score distribution, query match
        num_skills = len(ranked_skills)
        top_score = ranked_skills[0][1] if ranked_skills else 0

        # More skills with high scores = higher confidence
        confidence = min(1.0, (num_skills / 10) * 0.3 + (top_score / 10) * 0.7)

        return round(confidence, 2)

    async def record_skill_selection(
        self,
        query: str,
        selected_skills: list[str],
        context: DiscoveryContext | None,
        outcome: str = "selected"
    ) -> None:
        """Record skill selection in Mind for future learning."""
        try:
            content = f"Skill selection for '{query}': {', '.join(selected_skills)}"
            if context:
                if context.project_name:
                    content += f" | Project: {context.project_name}"
                if context.tech_stack:
                    content += f" | Stack: {', '.join(context.tech_stack)}"
            content += f" | Outcome: {outcome}"

            await self.mind.remember(
                content=content,
                memory_type="procedural",
                temporal_level=3  # Months-level persistence
            )

            logger.info(
                "Recorded skill selection",
                query=query,
                skills=selected_skills
            )

        except Exception as e:
            logger.warning("Failed to record skill selection", error=str(e))

    async def learn_from_outcome(
        self,
        skill_ids: list[str],
        outcome_quality: float,
        context: DiscoveryContext | None
    ) -> None:
        """
        Learn from task outcome to improve future skill selection.

        Args:
            skill_ids: Skills that were used
            outcome_quality: -1.0 (bad) to 1.0 (good)
            context: Task context
        """
        try:
            summary = f"Skills {', '.join(skill_ids)} used"
            if context and context.task_description:
                summary += f" for: {context.task_description[:50]}"

            await self.mind.record_decision(
                memory_ids=[],  # Would need to track retrieval IDs
                decision_summary=summary,
                outcome_quality=outcome_quality,
                outcome_signal="task_completed" if outcome_quality > 0 else "agent_feedback"
            )

        except Exception as e:
            logger.warning("Failed to record learning", error=str(e))
