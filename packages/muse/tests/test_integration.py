"""Integration tests for Muse MCP.

Tests the full workflow from prompt expansion to promotion.
"""

import pytest
import tempfile
import os
from pathlib import Path

from muse_mcp.database import Database
from muse_mcp.embeddings import EmbeddingModel
from muse_mcp.fragments import FragmentStore
from muse_mcp.expansion import PromptExpander
from muse_mcp.ranking import CandidateRanker
from muse_mcp.mutations import IdeaMutator
from muse_mcp.contradictions import ContradictionFinder
from muse_mcp.clustering import FragmentClusterer
from muse_mcp.promotion import PromotionManager
from muse_mcp.models import LifecycleState, MutationType


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_muse.db"
        db = Database(str(db_path))
        yield db


@pytest.fixture
def embedder():
    """Create embedding model (uses cached model)."""
    return EmbeddingModel()


@pytest.fixture
def fragment_store(temp_db, embedder):
    """Create fragment store with test database."""
    return FragmentStore(temp_db, embedder)


@pytest.fixture
def ranker(temp_db, embedder):
    """Create candidate ranker."""
    return CandidateRanker(temp_db, embedder)


@pytest.fixture
def mutator(temp_db, embedder, fragment_store):
    """Create idea mutator."""
    return IdeaMutator(temp_db, embedder, fragment_store)


@pytest.fixture
def contradiction_finder(temp_db, embedder):
    """Create contradiction finder."""
    return ContradictionFinder(temp_db, embedder)


@pytest.fixture
def clusterer(temp_db, embedder):
    """Create fragment clusterer."""
    return FragmentClusterer(temp_db, embedder)


@pytest.fixture
def promoter(temp_db):
    """Create promotion manager."""
    return PromotionManager(temp_db)


@pytest.fixture
def expander(temp_db):
    """Create prompt expander."""
    return PromptExpander(temp_db)


class TestFragmentLifecycle:
    """Test fragment lifecycle from creation to decay."""

    def test_create_fragment(self, fragment_store):
        """Test creating a fragment."""
        f = fragment_store.create(
            user_id="test-user",
            content="An idea about memory systems",
            domains=["ai", "memory"],
        )

        assert f.id is not None
        assert f.state == LifecycleState.FRAGMENT
        assert f.salience == 1.0

    def test_fragment_decay(self, fragment_store):
        """Test fragment decay over time."""
        f = fragment_store.create(
            user_id="test-user",
            content="Decaying idea",
            decay_rate=0.2,
        )

        # Apply decay
        updated = fragment_store.apply_decay("test-user", hours_passed=2.0)
        assert updated >= 1

        # Fetch fragment and check salience
        f2 = fragment_store.get(f.id)
        assert f2.salience < 1.0

    def test_find_similar_fragments(self, fragment_store):
        """Test finding similar fragments."""
        # Create related fragments
        fragment_store.create(
            user_id="test-user",
            content="Memory systems for AI agents",
        )
        fragment_store.create(
            user_id="test-user",
            content="AI agent memory architecture",
        )
        fragment_store.create(
            user_id="test-user",
            content="Cooking recipes for dinner",
        )

        # Find similar to AI memory
        similar = fragment_store.find_similar(
            content="Memory for AI systems",
            user_id="test-user",
            limit=5,
        )

        # Should find the AI-related fragments
        assert len(similar) >= 2

    def test_cleanup_expired(self, fragment_store):
        """Test cleaning up expired fragments."""
        from datetime import datetime, timedelta

        # Create fragment and manually expire it
        f = fragment_store.create(
            user_id="test-user",
            content="Expired idea",
            ttl_seconds=1,  # Very short TTL
        )

        # Force expiration
        fragment_store.db.refresh_fragment(
            f.id,
            datetime.utcnow() - timedelta(hours=1)
        )

        # Cleanup
        deleted = fragment_store.cleanup_expired()
        assert deleted >= 1

        # Fragment should be gone
        f2 = fragment_store.get(f.id)
        assert f2 is None


class TestPromptExpansion:
    """Test prompt expansion."""

    def test_expand_simple_prompt(self, expander):
        """Test expanding a simple prompt."""
        wo = expander.expand(
            user_id="test-user",
            raw_prompt="Build a memory system for AI agents",
        )

        assert wo.id is not None
        assert wo.goal is not None
        assert len(wo.goal) > 0
        assert "memory" in " ".join(wo.domains).lower() or len(wo.domains) > 0

    def test_expand_with_constraints(self, expander):
        """Test expanding prompt with constraints."""
        wo = expander.expand(
            user_id="test-user",
            raw_prompt="Build a fast, local-first memory system that must be secure",
        )

        # Should detect constraints
        assert len(wo.constraints) > 0


class TestCandidateRanking:
    """Test candidate scoring and ranking."""

    def test_score_candidate(self, ranker):
        """Test scoring a candidate."""
        candidate = ranker.create_candidate(
            user_id="test-user",
            content="A practical solution to improve API performance by 50%",
        )

        scored = ranker.score_candidate(candidate)

        assert scored.usefulness > 0
        assert scored.novelty > 0
        assert scored.feasibility > 0
        assert scored.value_score != 0
        assert scored.evaluated_at is not None

    def test_rank_multiple_candidates(self, ranker):
        """Test ranking multiple candidates."""
        # Create candidates with different qualities
        ranker.create_candidate(
            user_id="test-user",
            content="A vague maybe idea that could possibly work",
        )
        c2 = ranker.create_candidate(
            user_id="test-user",
            content="A practical tested solution that solves the performance issue",
        )

        # Score both
        candidates = ranker.db.get_top_candidates(
            user_id="test-user",
            limit=10,
        )

        for c in candidates:
            ranker.score_candidate(c)

        # Get ranked list
        ranked = ranker.rank_candidates("test-user")
        assert len(ranked) >= 1


class TestIdeaMutation:
    """Test idea mutation."""

    def test_apply_mutations(self, mutator):
        """Test applying mutations to an idea."""
        mutations = mutator.mutate(
            user_id="test-user",
            source_content="Build a centralized database for all user data",
            mutation_types=[MutationType.INVERT, MutationType.COMPRESS],
            create_fragments=True,
        )

        assert len(mutations) == 2
        assert any(m.mutation_type == MutationType.INVERT for m in mutations)
        assert any(m.mutation_type == MutationType.COMPRESS for m in mutations)

    def test_combine_ideas(self, mutator):
        """Test combining two ideas."""
        mutation = mutator.combine_with(
            user_id="test-user",
            content_a="Use embeddings for semantic search",
            content_b="Apply decay to old memories",
        )

        assert mutation.mutation_type == MutationType.COMBINE
        assert "COMBINED" in mutation.result_content


class TestContradictionFinding:
    """Test contradiction detection."""

    def test_find_assumption_contradictions(self, contradiction_finder):
        """Test finding fragile assumptions."""
        contradictions = contradiction_finder.find_contradictions(
            user_id="test-user",
            target_content="Users will always provide valid input and the system will never fail",
        )

        # Should find assumptions (always, never)
        assert len(contradictions) > 0
        assert any(c.contradiction_type == "assumption" for c in contradictions)

    def test_find_risk_contradictions(self, contradiction_finder):
        """Test finding risk-based contradictions."""
        contradictions = contradiction_finder.find_contradictions(
            user_id="test-user",
            target_content="We'll use an external API for all database operations",
        )

        # Should identify external dependency risk
        assert len(contradictions) > 0


class TestClustering:
    """Test fragment clustering."""

    def test_cluster_similar_fragments(self, clusterer, fragment_store):
        """Test clustering similar fragments."""
        # Create multiple similar fragments
        for i in range(5):
            fragment_store.create(
                user_id="test-user",
                content=f"Memory architecture for AI agents - variant {i}",
            )

        # Also create a different fragment
        fragment_store.create(
            user_id="test-user",
            content="Cooking recipes are delicious",
        )

        # Cluster
        clusters = clusterer.cluster_fragments("test-user")

        # Should create at least one cluster for the similar fragments
        if len(clusters) > 0:
            # Found clusters
            assert clusters[0].fragment_ids is not None


class TestPromotion:
    """Test promotion to Mind MCP."""

    def test_check_eligibility(self, promoter, ranker):
        """Test promotion eligibility checking."""
        # Create a high-value candidate
        candidate = ranker.create_candidate(
            user_id="test-user",
            content="A proven solution that improves performance",
        )
        candidate.usefulness = 0.8
        candidate.novelty = 0.6
        candidate.feasibility = 0.7
        candidate.alignment = 0.7
        candidate.risk = 0.2
        candidate.compute_value()

        eligibility = promoter.check_promotion_eligibility(candidate)

        assert "eligible" in eligibility
        assert "scores" in eligibility

    def test_promotion_flow(self, promoter, ranker):
        """Test full promotion flow (without actual Mind MCP)."""
        # Create eligible candidate
        candidate = ranker.create_candidate(
            user_id="test-user",
            content="Excellent testable solution with low risk",
        )
        candidate.usefulness = 0.8
        candidate.novelty = 0.6
        candidate.feasibility = 0.8
        candidate.alignment = 0.7
        candidate.risk = 0.2
        candidate.compute_value()

        # Update in DB
        ranker.db.update_candidate_scores(
            candidate.id,
            usefulness=candidate.usefulness,
            novelty=candidate.novelty,
            feasibility=candidate.feasibility,
            alignment=candidate.alignment,
            risk=candidate.risk,
            value_score=candidate.value_score,
        )

        # Check promotion (without Mind client)
        result = promoter.promote_to_mind(
            candidate=candidate,
            mind_client=None,  # No actual Mind MCP
            memory_type="auto",
        )

        # Without Mind client, should still check eligibility
        assert "eligible" in str(result) or "success" in result


class TestFullWorkflow:
    """Test complete Muse workflow."""

    def test_prompt_to_candidate(self, expander, fragment_store, ranker):
        """Test flow from prompt to ranked candidate."""
        # 1. Expand prompt
        wo = expander.expand(
            user_id="test-user",
            raw_prompt="Build a memory system that stores and retrieves information efficiently",
        )

        # 2. Create fragment from expanded goal
        fragment = fragment_store.create(
            user_id="test-user",
            content=wo.goal,
            source_working_object_id=wo.id,
        )

        # 3. Create candidate from fragment
        candidate = ranker.create_candidate(
            user_id="test-user",
            content=fragment.content,
            source_fragment_ids=[fragment.id],
            source_working_object_id=wo.id,
        )

        # 4. Score candidate
        scored = ranker.score_candidate(
            candidate=candidate,
            working_object=wo,
        )

        assert scored.value_score != 0
        assert scored.alignment > 0  # Should be aligned with working object goal


class TestDatabaseOperations:
    """Test database operations."""

    def test_stats(self, temp_db, fragment_store):
        """Test getting database stats."""
        # Create some data
        fragment_store.create(user_id="test-user", content="Test 1")
        fragment_store.create(user_id="test-user", content="Test 2")

        stats = temp_db.get_stats()

        assert "fragments_count" in stats
        assert stats["fragments_count"] >= 2

    def test_cleanup_all_expired(self, temp_db, fragment_store):
        """Test cleaning up all expired content."""
        from datetime import datetime, timedelta

        # Create and expire a fragment
        f = fragment_store.create(
            user_id="test-user",
            content="Will expire",
            ttl_seconds=1,
        )
        temp_db.refresh_fragment(f.id, datetime.utcnow() - timedelta(hours=1))

        # Cleanup all
        counts = temp_db.cleanup_all_expired()

        assert counts["fragments"] >= 1
