"""Tests for Muse MCP data models."""

import pytest
from datetime import datetime, timedelta

from muse_mcp.models import (
    Fragment,
    WorkingObject,
    Cluster,
    Candidate,
    Analogy,
    Contradiction,
    Mutation,
    LifecycleState,
    MutationType,
    DEFAULT_TTL,
    DEFAULT_VALUE_WEIGHTS,
)


class TestFragment:
    """Tests for Fragment model."""

    def test_create_fragment(self):
        """Test basic fragment creation."""
        f = Fragment(
            user_id="test-user",
            content="Test idea content",
        )

        assert f.id is not None
        assert f.user_id == "test-user"
        assert f.content == "Test idea content"
        assert f.state == LifecycleState.FRAGMENT
        assert f.salience == 1.0
        assert f.expires_at is not None

    def test_fragment_decay(self):
        """Test fragment decay mechanics."""
        f = Fragment(
            user_id="test-user",
            content="Test",
            salience=1.0,
            decay_rate=0.1,
        )

        # Apply 1 hour of decay
        new_salience = f.decay(hours_passed=1.0)
        assert new_salience == 0.9
        assert f.salience == 0.9

        # Apply 5 more hours
        f.decay(hours_passed=5.0)
        assert f.salience == 0.4

    def test_fragment_expiry(self):
        """Test fragment expiration."""
        f = Fragment(
            user_id="test-user",
            content="Test",
            ttl_seconds=3600,  # 1 hour
        )

        # Should not be expired initially
        assert not f.is_expired()

        # Manually set expiry in the past
        f.expires_at = datetime.utcnow() - timedelta(hours=1)
        assert f.is_expired()

    def test_fragment_refresh(self):
        """Test fragment refresh extends TTL."""
        f = Fragment(
            user_id="test-user",
            content="Test",
            ttl_seconds=3600,
        )

        original_expires = f.expires_at
        f.refresh(extend_ttl=True)

        assert f.last_accessed is not None
        assert f.expires_at > original_expires

    def test_fragment_to_dict(self):
        """Test fragment serialization."""
        f = Fragment(
            user_id="test-user",
            content="Test",
            domains=["ai", "memory"],
            tags=["test"],
        )

        d = f.to_dict()
        assert d["user_id"] == "test-user"
        assert d["content"] == "Test"
        assert d["domains"] == ["ai", "memory"]
        assert d["state"] == "fragment"


class TestCandidate:
    """Tests for Candidate model."""

    def test_create_candidate(self):
        """Test basic candidate creation."""
        c = Candidate(
            user_id="test-user",
            content="A good idea",
        )

        assert c.id is not None
        assert c.usefulness == 0.5
        assert c.novelty == 0.5
        assert c.feasibility == 0.5
        assert c.alignment == 0.5
        assert c.risk == 0.5
        assert not c.promoted

    def test_compute_value_default_weights(self):
        """Test value computation with default weights."""
        c = Candidate(
            user_id="test-user",
            content="Test",
            usefulness=0.8,
            novelty=0.7,
            feasibility=0.6,
            alignment=0.9,
            risk=0.2,
        )

        value = c.compute_value()

        # V = 0.25*0.8 + 0.20*0.7 + 0.25*0.6 + 0.20*0.9 - 0.10*0.2
        # V = 0.2 + 0.14 + 0.15 + 0.18 - 0.02 = 0.65
        assert abs(value - 0.65) < 0.01
        assert c.value_score == value

    def test_compute_value_custom_weights(self):
        """Test value computation with custom weights."""
        c = Candidate(
            user_id="test-user",
            content="Test",
            usefulness=1.0,
            novelty=0.0,
            feasibility=0.0,
            alignment=0.0,
            risk=0.0,
        )

        # Weight usefulness at 100%
        weights = {
            "usefulness": 1.0,
            "novelty": 0.0,
            "feasibility": 0.0,
            "alignment": 0.0,
            "risk": 0.0,
        }

        value = c.compute_value(weights)
        assert value == 1.0

    def test_candidate_to_dict(self):
        """Test candidate serialization."""
        c = Candidate(
            user_id="test-user",
            content="Test idea",
            usefulness=0.8,
        )
        c.compute_value()

        d = c.to_dict()
        assert d["user_id"] == "test-user"
        assert d["content"] == "Test idea"
        assert d["scores"]["usefulness"] == 0.8
        assert "value" in d["scores"]


class TestWorkingObject:
    """Tests for WorkingObject model."""

    def test_create_working_object(self):
        """Test working object creation."""
        wo = WorkingObject(
            user_id="test-user",
            raw_prompt="Build a memory system",
            goal="Create efficient memory storage",
            domains=["ai", "databases"],
            constraints=["local-first", "fast"],
            desired_outputs=["architecture", "code"],
        )

        assert wo.id is not None
        assert wo.raw_prompt == "Build a memory system"
        assert len(wo.domains) == 2
        assert wo.expires_at is not None

    def test_working_object_to_dict(self):
        """Test working object serialization."""
        wo = WorkingObject(
            user_id="test-user",
            raw_prompt="Test",
            goal="Test goal",
        )

        d = wo.to_dict()
        assert d["raw_prompt"] == "Test"
        assert d["goal"] == "Test goal"


class TestAnalogy:
    """Tests for Analogy model."""

    def test_create_analogy(self):
        """Test analogy creation."""
        a = Analogy(
            user_id="test-user",
            source_domain="software",
            source_concept="MVC pattern",
            source_structure="X → Y → Z",
            target_domain="cooking",
            target_concept="Recipe execution",
            target_structure="X → Y → Z",
            structural_similarity=0.85,
            surface_distance=0.7,
            insights=["Both follow separation of concerns"],
        )

        assert a.id is not None
        assert a.structural_similarity == 0.85
        assert len(a.insights) == 1


class TestContradiction:
    """Tests for Contradiction model."""

    def test_create_contradiction(self):
        """Test contradiction creation."""
        c = Contradiction(
            user_id="test-user",
            target_content="We should use microservices",
            contradiction_type="risk",
            contradiction_content="Microservices add operational complexity",
            severity=0.7,
            confidence=0.8,
        )

        assert c.id is not None
        assert not c.resolved
        assert c.severity == 0.7


class TestMutation:
    """Tests for Mutation model."""

    def test_create_mutation(self):
        """Test mutation creation."""
        m = Mutation(
            user_id="test-user",
            source_content="Original idea",
            mutation_type=MutationType.INVERT,
            result_content="Inverted idea",
        )

        assert m.id is not None
        assert m.mutation_type == MutationType.INVERT

    def test_all_mutation_types(self):
        """Test all mutation types exist."""
        types = [
            MutationType.INVERT,
            MutationType.COMBINE,
            MutationType.COMPRESS,
            MutationType.MODULARIZE,
            MutationType.MAKE_SAFER,
            MutationType.MAKE_EXPLAINABLE,
            MutationType.MAKE_TESTABLE,
            MutationType.MAKE_SELLABLE,
            MutationType.SCALE_UP,
            MutationType.SCALE_DOWN,
        ]
        assert len(types) == 10
