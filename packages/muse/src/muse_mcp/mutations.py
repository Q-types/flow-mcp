"""Idea mutation engine for Muse MCP.

Systematically transforms ideas through operations like:
- invert: Flip the core assumption
- combine: Merge with another idea
- compress: Simplify to essence
- modularize: Break into components
- make_safer: Reduce risk
- make_explainable: Add clarity
- make_testable: Add verification
- make_sellable: Add appeal
- scale_up: Expand scope
- scale_down: Narrow focus
"""

from __future__ import annotations

from typing import Any

from .database import Database
from .embeddings import EmbeddingModel
from .fragments import FragmentStore
from .models import Fragment, Mutation, MutationType


class IdeaMutator:
    """Applies transformations to generate idea variants."""

    def __init__(
        self,
        db: Database,
        embedder: EmbeddingModel,
        fragment_store: FragmentStore,
    ):
        """Initialize idea mutator.

        Args:
            db: Database instance
            embedder: Embedding model instance
            fragment_store: Fragment store for creating new fragments
        """
        self.db = db
        self.embedder = embedder
        self.fragment_store = fragment_store

    def mutate(
        self,
        user_id: str,
        source_content: str,
        source_fragment_id: str | None = None,
        mutation_types: list[MutationType] | None = None,
        create_fragments: bool = True,
    ) -> list[Mutation]:
        """Apply mutations to generate idea variants.

        Args:
            user_id: User ID
            source_content: Content to mutate
            source_fragment_id: Optional source fragment ID
            mutation_types: Which mutations to apply (default: all)
            create_fragments: Whether to create fragments for results

        Returns:
            List of mutations with results
        """
        if mutation_types is None:
            mutation_types = list(MutationType)

        mutations = []

        for mtype in mutation_types:
            result = self._apply_mutation(source_content, mtype)

            if result:
                # Create fragment if requested
                fragment_id = None
                if create_fragments:
                    fragment = self.fragment_store.create(
                        user_id=user_id,
                        content=result,
                        source_prompt=f"Mutation ({mtype.value}) of: {source_content[:100]}",
                        parent_id=source_fragment_id,
                        tags=[f"mutation:{mtype.value}"],
                    )
                    fragment_id = fragment.id

                mutation = Mutation(
                    user_id=user_id,
                    source_content=source_content,
                    source_fragment_id=source_fragment_id,
                    mutation_type=mtype,
                    result_content=result,
                    result_fragment_id=fragment_id,
                )

                self.db.insert_mutation(mutation)
                mutations.append(mutation)

        return mutations

    def _apply_mutation(self, content: str, mtype: MutationType) -> str | None:
        """Apply a specific mutation type."""
        mutators = {
            MutationType.INVERT: self._invert,
            MutationType.COMBINE: self._combine_placeholder,
            MutationType.COMPRESS: self._compress,
            MutationType.MODULARIZE: self._modularize,
            MutationType.MAKE_SAFER: self._make_safer,
            MutationType.MAKE_EXPLAINABLE: self._make_explainable,
            MutationType.MAKE_TESTABLE: self._make_testable,
            MutationType.MAKE_SELLABLE: self._make_sellable,
            MutationType.SCALE_UP: self._scale_up,
            MutationType.SCALE_DOWN: self._scale_down,
        }

        mutator = mutators.get(mtype)
        if mutator:
            return mutator(content)
        return None

    def _invert(self, content: str) -> str:
        """Invert the core assumption or approach."""
        # Simple inversion patterns
        inversions = [
            ("add", "remove"),
            ("create", "destroy"),
            ("build", "unbundle"),
            ("centralize", "decentralize"),
            ("automate", "manual"),
            ("sync", "async"),
            ("real-time", "batch"),
            ("push", "pull"),
            ("store", "compute on demand"),
            ("cache", "always fetch"),
            ("complex", "simple"),
            ("all", "selective"),
            ("global", "local"),
            ("cloud", "edge"),
        ]

        result = content
        for original, inverted in inversions:
            if original in content.lower():
                result = f"INVERTED: Instead of '{original}', what if we '{inverted}'? " + content
                break
        else:
            result = f"INVERTED: What if we did the opposite? " + content

        return result

    def _combine_placeholder(self, content: str) -> str:
        """Placeholder for combine - needs another idea to combine with."""
        return f"COMBINE: This idea could be combined with [another concept] to create synergy. Base idea: {content}"

    def combine_with(
        self,
        user_id: str,
        content_a: str,
        content_b: str,
        fragment_id_a: str | None = None,
        create_fragment: bool = True,
    ) -> Mutation:
        """Combine two ideas into a new one.

        Args:
            user_id: User ID
            content_a: First idea
            content_b: Second idea
            fragment_id_a: Optional fragment ID for first idea
            create_fragment: Whether to create fragment for result

        Returns:
            Combined mutation
        """
        # Extract key elements from both
        result = f"COMBINED: Merging concepts:\n1. {content_a[:200]}\n2. {content_b[:200]}\n\nSynthesis: Take the core approach from (1) and apply the mechanism from (2)."

        fragment_id = None
        if create_fragment:
            fragment = self.fragment_store.create(
                user_id=user_id,
                content=result,
                source_prompt=f"Combination of two ideas",
                parent_id=fragment_id_a,
                tags=["mutation:combine"],
            )
            fragment_id = fragment.id

        mutation = Mutation(
            user_id=user_id,
            source_content=content_a,
            source_fragment_id=fragment_id_a,
            mutation_type=MutationType.COMBINE,
            result_content=result,
            result_fragment_id=fragment_id,
        )

        self.db.insert_mutation(mutation)
        return mutation

    def _compress(self, content: str) -> str:
        """Compress to essence - what's the core insight?"""
        # Extract first sentence as the likely core
        sentences = content.split('.')
        core = sentences[0].strip() if sentences else content[:100]

        return f"COMPRESSED: Core essence: {core}. Everything else is implementation detail."

    def _modularize(self, content: str) -> str:
        """Break into independent components."""
        return f"""MODULARIZED: Breaking into components:

1. INPUT MODULE: What data/trigger starts this?
2. PROCESS MODULE: What transformation happens?
3. OUTPUT MODULE: What result is produced?
4. STATE MODULE: What needs to be remembered?

Original: {content[:300]}"""

    def _make_safer(self, content: str) -> str:
        """Reduce risk and add safety margins."""
        return f"""SAFER VERSION: Adding safety margins:

- Add validation at input boundaries
- Implement graceful degradation
- Add circuit breakers for external dependencies
- Include audit logging
- Add rollback capability

Original: {content[:300]}"""

    def _make_explainable(self, content: str) -> str:
        """Add clarity and explainability."""
        return f"""EXPLAINABLE VERSION: Making transparent:

- WHY: What problem does this solve?
- HOW: What mechanism achieves this?
- TRADE-OFFS: What are we giving up?
- ALTERNATIVES: What else could we do?

Original: {content[:300]}"""

    def _make_testable(self, content: str) -> str:
        """Add verification and testability."""
        return f"""TESTABLE VERSION: Adding verification:

- Unit test: Does each component work in isolation?
- Integration test: Do components work together?
- Property test: Does it hold for edge cases?
- Load test: Does it work under stress?
- Acceptance criteria: What proves it's done?

Original: {content[:300]}"""

    def _make_sellable(self, content: str) -> str:
        """Add appeal and marketability."""
        return f"""SELLABLE VERSION: Emphasizing value:

- HEADLINE: What's the one-line pitch?
- BENEFIT: What does the user gain?
- PROOF: What evidence supports this?
- URGENCY: Why now?

Original: {content[:300]}"""

    def _scale_up(self, content: str) -> str:
        """Expand scope and ambition."""
        return f"""SCALED UP: Expanding scope:

- What if this worked for 10x more users?
- What if this handled 100x more data?
- What if this expanded to adjacent domains?
- What if this became a platform others build on?

Original: {content[:300]}"""

    def _scale_down(self, content: str) -> str:
        """Narrow focus for faster validation."""
        return f"""SCALED DOWN: Minimum viable version:

- What's the simplest version that provides value?
- What can we defer to later?
- Who is the single most important user?
- What's the one metric that matters?

Original: {content[:300]}"""

    def to_response(self, mutations: list[Mutation]) -> dict[str, Any]:
        """Convert mutations to API response format."""
        by_type = {}
        for m in mutations:
            mtype = m.mutation_type.value
            if mtype not in by_type:
                by_type[mtype] = []
            by_type[mtype].append(m.to_dict())

        return {
            "mutations": [m.to_dict() for m in mutations],
            "by_type": by_type,
            "count": len(mutations),
            "types_applied": list(by_type.keys()),
        }
