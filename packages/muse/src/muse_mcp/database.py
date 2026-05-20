"""Database layer for Muse MCP - Transient storage with TTL support.

Schema designed for fast decay queries and efficient cleanup of expired content.
Uses SQLite with schema versioning like Mind MCP.
"""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np

from .models import (
    Fragment,
    WorkingObject,
    Cluster,
    Candidate,
    Analogy,
    Contradiction,
    Mutation,
    LifecycleState,
    MutationType,
)


SCHEMA_VERSION = 1

# Default database location
DEFAULT_DB_PATH = Path.home() / ".muse" / "muse.db"


class Database:
    """SQLite database for transient Muse MCP storage."""

    def __init__(self, db_path: str | Path | None = None):
        """Initialize database connection.

        Args:
            db_path: Path to SQLite database. If None, uses default location.
        """
        if db_path is None:
            db_path = os.environ.get("MUSE_DB_PATH", str(DEFAULT_DB_PATH))

        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._init_schema()

    def _get_connection(self) -> sqlite3.Connection:
        """Get a database connection."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        return conn

    def _init_schema(self) -> None:
        """Initialize database schema with versioning."""
        with self._get_connection() as conn:
            # Check schema version
            conn.execute("""
                CREATE TABLE IF NOT EXISTS schema_version (
                    version INTEGER PRIMARY KEY
                )
            """)

            result = conn.execute("SELECT version FROM schema_version").fetchone()
            current_version = result[0] if result else 0

            if current_version < SCHEMA_VERSION:
                self._create_tables(conn)
                conn.execute("DELETE FROM schema_version")
                conn.execute("INSERT INTO schema_version (version) VALUES (?)", (SCHEMA_VERSION,))

            conn.commit()

    def _create_tables(self, conn: sqlite3.Connection) -> None:
        """Create all tables for Muse MCP."""

        # Fragments table - atomic transient ideas
        conn.execute("""
            CREATE TABLE IF NOT EXISTS fragments (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                content TEXT NOT NULL,
                state TEXT DEFAULT 'fragment',
                source_prompt TEXT,
                source_working_object_id TEXT,
                salience REAL DEFAULT 1.0,
                decay_rate REAL DEFAULT 0.1,
                ttl_seconds INTEGER DEFAULT 3600,
                created_at TEXT NOT NULL,
                last_accessed TEXT,
                expires_at TEXT,
                parent_id TEXT,
                cluster_id TEXT,
                domains TEXT,  -- JSON array
                tags TEXT,     -- JSON array
                metadata TEXT, -- JSON object
                embedding BLOB
            )
        """)

        # Working objects table - expanded prompts
        conn.execute("""
            CREATE TABLE IF NOT EXISTS working_objects (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                raw_prompt TEXT NOT NULL,
                goal TEXT,
                domains TEXT,           -- JSON array
                constraints TEXT,       -- JSON array
                desired_outputs TEXT,   -- JSON array
                relevant_memories TEXT, -- JSON array
                relevant_patterns TEXT, -- JSON array
                relevant_failures TEXT, -- JSON array
                fragment_ids TEXT,      -- JSON array
                created_at TEXT NOT NULL,
                expires_at TEXT
            )
        """)

        # Clusters table - grouped fragments
        conn.execute("""
            CREATE TABLE IF NOT EXISTS clusters (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                label TEXT,
                summary TEXT,
                fragment_ids TEXT,      -- JSON array
                centroid_embedding BLOB,
                state TEXT DEFAULT 'clustered',
                salience REAL DEFAULT 1.0,
                created_at TEXT NOT NULL,
                expires_at TEXT
            )
        """)

        # Candidates table - evaluated ideas
        conn.execute("""
            CREATE TABLE IF NOT EXISTS candidates (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                content TEXT NOT NULL,
                summary TEXT,
                source_fragment_ids TEXT,     -- JSON array
                source_cluster_id TEXT,
                source_working_object_id TEXT,
                usefulness REAL DEFAULT 0.5,
                novelty REAL DEFAULT 0.5,
                feasibility REAL DEFAULT 0.5,
                alignment REAL DEFAULT 0.5,
                risk REAL DEFAULT 0.5,
                value_score REAL DEFAULT 0.0,
                state TEXT DEFAULT 'candidate',
                promoted INTEGER DEFAULT 0,
                promoted_memory_id TEXT,
                promotion_reason TEXT,
                created_at TEXT NOT NULL,
                evaluated_at TEXT,
                promoted_at TEXT,
                expires_at TEXT,
                embedding BLOB
            )
        """)

        # Analogies table - cross-domain mappings
        conn.execute("""
            CREATE TABLE IF NOT EXISTS analogies (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                source_domain TEXT,
                source_concept TEXT,
                source_structure TEXT,
                target_domain TEXT,
                target_concept TEXT,
                target_structure TEXT,
                structural_similarity REAL DEFAULT 0.0,
                surface_distance REAL DEFAULT 0.0,
                usefulness REAL DEFAULT 0.0,
                insights TEXT,          -- JSON array
                created_at TEXT NOT NULL,
                expires_at TEXT
            )
        """)

        # Contradictions table - tensions and counter-evidence
        conn.execute("""
            CREATE TABLE IF NOT EXISTS contradictions (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                target_content TEXT,
                target_fragment_id TEXT,
                target_candidate_id TEXT,
                contradiction_type TEXT,
                contradiction_content TEXT,
                source TEXT,
                severity REAL DEFAULT 0.5,
                confidence REAL DEFAULT 0.5,
                resolved INTEGER DEFAULT 0,
                resolution TEXT,
                created_at TEXT NOT NULL
            )
        """)

        # Mutations table - idea transformations
        conn.execute("""
            CREATE TABLE IF NOT EXISTS mutations (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                source_content TEXT,
                source_fragment_id TEXT,
                mutation_type TEXT,
                result_content TEXT,
                result_fragment_id TEXT,
                improvement_score REAL DEFAULT 0.0,
                created_at TEXT NOT NULL
            )
        """)

        # Create indexes for efficient queries
        self._create_indexes(conn)

    def _create_indexes(self, conn: sqlite3.Connection) -> None:
        """Create indexes for efficient TTL and retrieval queries."""

        # Fragment indexes
        conn.execute("CREATE INDEX IF NOT EXISTS idx_fragments_user ON fragments(user_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_fragments_expires ON fragments(expires_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_fragments_state ON fragments(state)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_fragments_cluster ON fragments(cluster_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_fragments_salience ON fragments(salience)")

        # Working object indexes
        conn.execute("CREATE INDEX IF NOT EXISTS idx_working_objects_user ON working_objects(user_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_working_objects_expires ON working_objects(expires_at)")

        # Cluster indexes
        conn.execute("CREATE INDEX IF NOT EXISTS idx_clusters_user ON clusters(user_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_clusters_expires ON clusters(expires_at)")

        # Candidate indexes
        conn.execute("CREATE INDEX IF NOT EXISTS idx_candidates_user ON candidates(user_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_candidates_expires ON candidates(expires_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_candidates_value ON candidates(value_score DESC)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_candidates_promoted ON candidates(promoted)")

        # Analogy indexes
        conn.execute("CREATE INDEX IF NOT EXISTS idx_analogies_user ON analogies(user_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_analogies_expires ON analogies(expires_at)")

        # Contradiction indexes
        conn.execute("CREATE INDEX IF NOT EXISTS idx_contradictions_user ON contradictions(user_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_contradictions_target ON contradictions(target_fragment_id)")

    # --- Fragment operations ---

    def insert_fragment(self, fragment: Fragment, embedding: np.ndarray | None = None) -> None:
        """Insert a fragment into the database."""
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO fragments (
                    id, user_id, content, state, source_prompt, source_working_object_id,
                    salience, decay_rate, ttl_seconds, created_at, last_accessed, expires_at,
                    parent_id, cluster_id, domains, tags, metadata, embedding
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                fragment.id,
                fragment.user_id,
                fragment.content,
                fragment.state.value,
                fragment.source_prompt,
                fragment.source_working_object_id,
                fragment.salience,
                fragment.decay_rate,
                fragment.ttl_seconds,
                fragment.created_at.isoformat(),
                fragment.last_accessed.isoformat() if fragment.last_accessed else None,
                fragment.expires_at.isoformat() if fragment.expires_at else None,
                fragment.parent_id,
                fragment.cluster_id,
                json.dumps(fragment.domains),
                json.dumps(fragment.tags),
                json.dumps(fragment.metadata),
                embedding.tobytes() if embedding is not None else None,
            ))
            conn.commit()

    def get_fragment(self, fragment_id: str) -> Fragment | None:
        """Get a fragment by ID."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM fragments WHERE id = ?",
                (fragment_id,)
            ).fetchone()

            if row is None:
                return None

            return self._row_to_fragment(row)

    def get_fragments_by_user(
        self,
        user_id: str,
        state: LifecycleState | None = None,
        include_expired: bool = False,
        limit: int = 100,
    ) -> list[tuple[Fragment, np.ndarray | None]]:
        """Get fragments for a user with optional filtering."""
        with self._get_connection() as conn:
            query = "SELECT * FROM fragments WHERE user_id = ?"
            params: list[Any] = [user_id]

            if state:
                query += " AND state = ?"
                params.append(state.value)

            if not include_expired:
                query += " AND (expires_at IS NULL OR expires_at > ?)"
                params.append(datetime.utcnow().isoformat())

            query += " ORDER BY salience DESC, created_at DESC LIMIT ?"
            params.append(limit)

            rows = conn.execute(query, params).fetchall()

            results = []
            for row in rows:
                fragment = self._row_to_fragment(row)
                embedding = np.frombuffer(row["embedding"], dtype=np.float32) if row["embedding"] else None
                results.append((fragment, embedding))

            return results

    def update_fragment_salience(self, fragment_id: str, new_salience: float) -> None:
        """Update a fragment's salience."""
        with self._get_connection() as conn:
            conn.execute(
                "UPDATE fragments SET salience = ? WHERE id = ?",
                (new_salience, fragment_id)
            )
            conn.commit()

    def update_fragment_state(self, fragment_id: str, new_state: LifecycleState) -> None:
        """Update a fragment's lifecycle state."""
        with self._get_connection() as conn:
            conn.execute(
                "UPDATE fragments SET state = ? WHERE id = ?",
                (new_state.value, fragment_id)
            )
            conn.commit()

    def refresh_fragment(self, fragment_id: str, new_expires_at: datetime | None = None) -> None:
        """Refresh fragment's last_accessed and optionally extend expiry."""
        with self._get_connection() as conn:
            now = datetime.utcnow().isoformat()
            if new_expires_at:
                conn.execute(
                    "UPDATE fragments SET last_accessed = ?, expires_at = ? WHERE id = ?",
                    (now, new_expires_at.isoformat(), fragment_id)
                )
            else:
                conn.execute(
                    "UPDATE fragments SET last_accessed = ? WHERE id = ?",
                    (now, fragment_id)
                )
            conn.commit()

    def delete_fragment(self, fragment_id: str) -> bool:
        """Delete a fragment."""
        with self._get_connection() as conn:
            cursor = conn.execute("DELETE FROM fragments WHERE id = ?", (fragment_id,))
            conn.commit()
            return cursor.rowcount > 0

    def cleanup_expired_fragments(self) -> int:
        """Delete expired fragments. Returns count of deleted rows."""
        with self._get_connection() as conn:
            now = datetime.utcnow().isoformat()
            cursor = conn.execute(
                "DELETE FROM fragments WHERE expires_at IS NOT NULL AND expires_at < ?",
                (now,)
            )
            conn.commit()
            return cursor.rowcount

    def _row_to_fragment(self, row: sqlite3.Row) -> Fragment:
        """Convert a database row to a Fragment object."""
        return Fragment(
            id=row["id"],
            user_id=row["user_id"],
            content=row["content"],
            state=LifecycleState(row["state"]),
            source_prompt=row["source_prompt"] or "",
            source_working_object_id=row["source_working_object_id"],
            salience=row["salience"],
            decay_rate=row["decay_rate"],
            ttl_seconds=row["ttl_seconds"],
            created_at=datetime.fromisoformat(row["created_at"]),
            last_accessed=datetime.fromisoformat(row["last_accessed"]) if row["last_accessed"] else None,
            expires_at=datetime.fromisoformat(row["expires_at"]) if row["expires_at"] else None,
            parent_id=row["parent_id"],
            cluster_id=row["cluster_id"],
            domains=json.loads(row["domains"]) if row["domains"] else [],
            tags=json.loads(row["tags"]) if row["tags"] else [],
            metadata=json.loads(row["metadata"]) if row["metadata"] else {},
        )

    # --- Working Object operations ---

    def insert_working_object(self, wo: WorkingObject) -> None:
        """Insert a working object."""
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO working_objects (
                    id, user_id, raw_prompt, goal, domains, constraints,
                    desired_outputs, relevant_memories, relevant_patterns,
                    relevant_failures, fragment_ids, created_at, expires_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                wo.id,
                wo.user_id,
                wo.raw_prompt,
                wo.goal,
                json.dumps(wo.domains),
                json.dumps(wo.constraints),
                json.dumps(wo.desired_outputs),
                json.dumps(wo.relevant_memories),
                json.dumps(wo.relevant_patterns),
                json.dumps(wo.relevant_failures),
                json.dumps(wo.fragment_ids),
                wo.created_at.isoformat(),
                wo.expires_at.isoformat() if wo.expires_at else None,
            ))
            conn.commit()

    def get_working_object(self, wo_id: str) -> WorkingObject | None:
        """Get a working object by ID."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM working_objects WHERE id = ?",
                (wo_id,)
            ).fetchone()

            if row is None:
                return None

            return WorkingObject(
                id=row["id"],
                user_id=row["user_id"],
                raw_prompt=row["raw_prompt"],
                goal=row["goal"] or "",
                domains=json.loads(row["domains"]) if row["domains"] else [],
                constraints=json.loads(row["constraints"]) if row["constraints"] else [],
                desired_outputs=json.loads(row["desired_outputs"]) if row["desired_outputs"] else [],
                relevant_memories=json.loads(row["relevant_memories"]) if row["relevant_memories"] else [],
                relevant_patterns=json.loads(row["relevant_patterns"]) if row["relevant_patterns"] else [],
                relevant_failures=json.loads(row["relevant_failures"]) if row["relevant_failures"] else [],
                fragment_ids=json.loads(row["fragment_ids"]) if row["fragment_ids"] else [],
                created_at=datetime.fromisoformat(row["created_at"]),
                expires_at=datetime.fromisoformat(row["expires_at"]) if row["expires_at"] else None,
            )

    # --- Candidate operations ---

    def insert_candidate(self, candidate: Candidate, embedding: np.ndarray | None = None) -> None:
        """Insert a candidate."""
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO candidates (
                    id, user_id, content, summary, source_fragment_ids, source_cluster_id,
                    source_working_object_id, usefulness, novelty, feasibility, alignment,
                    risk, value_score, state, promoted, promoted_memory_id, promotion_reason,
                    created_at, evaluated_at, promoted_at, expires_at, embedding
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                candidate.id,
                candidate.user_id,
                candidate.content,
                candidate.summary,
                json.dumps(candidate.source_fragment_ids),
                candidate.source_cluster_id,
                candidate.source_working_object_id,
                candidate.usefulness,
                candidate.novelty,
                candidate.feasibility,
                candidate.alignment,
                candidate.risk,
                candidate.value_score,
                candidate.state.value,
                1 if candidate.promoted else 0,
                candidate.promoted_memory_id,
                candidate.promotion_reason,
                candidate.created_at.isoformat(),
                candidate.evaluated_at.isoformat() if candidate.evaluated_at else None,
                candidate.promoted_at.isoformat() if candidate.promoted_at else None,
                candidate.expires_at.isoformat() if candidate.expires_at else None,
                embedding.tobytes() if embedding is not None else None,
            ))
            conn.commit()

    def get_candidate(self, candidate_id: str) -> Candidate | None:
        """Get a candidate by ID."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM candidates WHERE id = ?",
                (candidate_id,)
            ).fetchone()

            if row is None:
                return None

            return self._row_to_candidate(row)

    def get_top_candidates(
        self,
        user_id: str,
        limit: int = 10,
        min_value_score: float = 0.0,
        exclude_promoted: bool = True,
    ) -> list[Candidate]:
        """Get top candidates by value score."""
        with self._get_connection() as conn:
            query = """
                SELECT * FROM candidates
                WHERE user_id = ? AND value_score >= ?
                AND (expires_at IS NULL OR expires_at > ?)
            """
            params: list[Any] = [user_id, min_value_score, datetime.utcnow().isoformat()]

            if exclude_promoted:
                query += " AND promoted = 0"

            query += " ORDER BY value_score DESC LIMIT ?"
            params.append(limit)

            rows = conn.execute(query, params).fetchall()
            return [self._row_to_candidate(row) for row in rows]

    def update_candidate_scores(
        self,
        candidate_id: str,
        usefulness: float | None = None,
        novelty: float | None = None,
        feasibility: float | None = None,
        alignment: float | None = None,
        risk: float | None = None,
        value_score: float | None = None,
    ) -> None:
        """Update candidate scores."""
        with self._get_connection() as conn:
            updates = []
            params = []

            if usefulness is not None:
                updates.append("usefulness = ?")
                params.append(usefulness)
            if novelty is not None:
                updates.append("novelty = ?")
                params.append(novelty)
            if feasibility is not None:
                updates.append("feasibility = ?")
                params.append(feasibility)
            if alignment is not None:
                updates.append("alignment = ?")
                params.append(alignment)
            if risk is not None:
                updates.append("risk = ?")
                params.append(risk)
            if value_score is not None:
                updates.append("value_score = ?")
                params.append(value_score)

            if updates:
                updates.append("evaluated_at = ?")
                params.append(datetime.utcnow().isoformat())
                params.append(candidate_id)

                conn.execute(
                    f"UPDATE candidates SET {', '.join(updates)} WHERE id = ?",
                    params
                )
                conn.commit()

    def mark_candidate_promoted(
        self,
        candidate_id: str,
        memory_id: str,
        reason: str,
    ) -> None:
        """Mark a candidate as promoted to Mind MCP."""
        with self._get_connection() as conn:
            conn.execute("""
                UPDATE candidates
                SET promoted = 1, promoted_memory_id = ?, promotion_reason = ?,
                    promoted_at = ?, state = ?
                WHERE id = ?
            """, (
                memory_id,
                reason,
                datetime.utcnow().isoformat(),
                LifecycleState.PROMOTED.value,
                candidate_id,
            ))
            conn.commit()

    def _row_to_candidate(self, row: sqlite3.Row) -> Candidate:
        """Convert a database row to a Candidate object."""
        return Candidate(
            id=row["id"],
            user_id=row["user_id"],
            content=row["content"],
            summary=row["summary"] or "",
            source_fragment_ids=json.loads(row["source_fragment_ids"]) if row["source_fragment_ids"] else [],
            source_cluster_id=row["source_cluster_id"],
            source_working_object_id=row["source_working_object_id"],
            usefulness=row["usefulness"],
            novelty=row["novelty"],
            feasibility=row["feasibility"],
            alignment=row["alignment"],
            risk=row["risk"],
            value_score=row["value_score"],
            state=LifecycleState(row["state"]),
            promoted=bool(row["promoted"]),
            promoted_memory_id=row["promoted_memory_id"],
            promotion_reason=row["promotion_reason"],
            created_at=datetime.fromisoformat(row["created_at"]),
            evaluated_at=datetime.fromisoformat(row["evaluated_at"]) if row["evaluated_at"] else None,
            promoted_at=datetime.fromisoformat(row["promoted_at"]) if row["promoted_at"] else None,
            expires_at=datetime.fromisoformat(row["expires_at"]) if row["expires_at"] else None,
        )

    # --- Analogy operations ---

    def insert_analogy(self, analogy: Analogy) -> None:
        """Insert an analogy."""
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO analogies (
                    id, user_id, source_domain, source_concept, source_structure,
                    target_domain, target_concept, target_structure,
                    structural_similarity, surface_distance, usefulness,
                    insights, created_at, expires_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                analogy.id,
                analogy.user_id,
                analogy.source_domain,
                analogy.source_concept,
                analogy.source_structure,
                analogy.target_domain,
                analogy.target_concept,
                analogy.target_structure,
                analogy.structural_similarity,
                analogy.surface_distance,
                analogy.usefulness,
                json.dumps(analogy.insights),
                analogy.created_at.isoformat(),
                analogy.expires_at.isoformat() if analogy.expires_at else None,
            ))
            conn.commit()

    def get_analogies_by_user(self, user_id: str, limit: int = 20) -> list[Analogy]:
        """Get analogies for a user."""
        with self._get_connection() as conn:
            rows = conn.execute("""
                SELECT * FROM analogies
                WHERE user_id = ? AND (expires_at IS NULL OR expires_at > ?)
                ORDER BY usefulness DESC, created_at DESC
                LIMIT ?
            """, (user_id, datetime.utcnow().isoformat(), limit)).fetchall()

            return [
                Analogy(
                    id=row["id"],
                    user_id=row["user_id"],
                    source_domain=row["source_domain"] or "",
                    source_concept=row["source_concept"] or "",
                    source_structure=row["source_structure"] or "",
                    target_domain=row["target_domain"] or "",
                    target_concept=row["target_concept"] or "",
                    target_structure=row["target_structure"] or "",
                    structural_similarity=row["structural_similarity"],
                    surface_distance=row["surface_distance"],
                    usefulness=row["usefulness"],
                    insights=json.loads(row["insights"]) if row["insights"] else [],
                    created_at=datetime.fromisoformat(row["created_at"]),
                    expires_at=datetime.fromisoformat(row["expires_at"]) if row["expires_at"] else None,
                )
                for row in rows
            ]

    # --- Contradiction operations ---

    def insert_contradiction(self, contradiction: Contradiction) -> None:
        """Insert a contradiction."""
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO contradictions (
                    id, user_id, target_content, target_fragment_id, target_candidate_id,
                    contradiction_type, contradiction_content, source,
                    severity, confidence, resolved, resolution, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                contradiction.id,
                contradiction.user_id,
                contradiction.target_content,
                contradiction.target_fragment_id,
                contradiction.target_candidate_id,
                contradiction.contradiction_type,
                contradiction.contradiction_content,
                contradiction.source,
                contradiction.severity,
                contradiction.confidence,
                1 if contradiction.resolved else 0,
                contradiction.resolution,
                contradiction.created_at.isoformat(),
            ))
            conn.commit()

    def get_contradictions_for_target(
        self,
        target_fragment_id: str | None = None,
        target_candidate_id: str | None = None,
    ) -> list[Contradiction]:
        """Get contradictions for a specific target."""
        with self._get_connection() as conn:
            if target_fragment_id:
                rows = conn.execute(
                    "SELECT * FROM contradictions WHERE target_fragment_id = ?",
                    (target_fragment_id,)
                ).fetchall()
            elif target_candidate_id:
                rows = conn.execute(
                    "SELECT * FROM contradictions WHERE target_candidate_id = ?",
                    (target_candidate_id,)
                ).fetchall()
            else:
                return []

            return [self._row_to_contradiction(row) for row in rows]

    def _row_to_contradiction(self, row: sqlite3.Row) -> Contradiction:
        """Convert a database row to a Contradiction object."""
        return Contradiction(
            id=row["id"],
            user_id=row["user_id"],
            target_content=row["target_content"] or "",
            target_fragment_id=row["target_fragment_id"],
            target_candidate_id=row["target_candidate_id"],
            contradiction_type=row["contradiction_type"] or "",
            contradiction_content=row["contradiction_content"] or "",
            source=row["source"] or "",
            severity=row["severity"],
            confidence=row["confidence"],
            resolved=bool(row["resolved"]),
            resolution=row["resolution"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    # --- Mutation operations ---

    def insert_mutation(self, mutation: Mutation) -> None:
        """Insert a mutation."""
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO mutations (
                    id, user_id, source_content, source_fragment_id,
                    mutation_type, result_content, result_fragment_id,
                    improvement_score, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                mutation.id,
                mutation.user_id,
                mutation.source_content,
                mutation.source_fragment_id,
                mutation.mutation_type.value,
                mutation.result_content,
                mutation.result_fragment_id,
                mutation.improvement_score,
                mutation.created_at.isoformat(),
            ))
            conn.commit()

    # --- Stats and cleanup ---

    def get_stats(self) -> dict[str, Any]:
        """Get database statistics."""
        with self._get_connection() as conn:
            stats = {}

            for table in ["fragments", "working_objects", "clusters", "candidates", "analogies", "contradictions", "mutations"]:
                count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                stats[f"{table}_count"] = count

            # Count active (non-expired) items
            now = datetime.utcnow().isoformat()
            active_fragments = conn.execute(
                "SELECT COUNT(*) FROM fragments WHERE expires_at IS NULL OR expires_at > ?",
                (now,)
            ).fetchone()[0]
            stats["active_fragments"] = active_fragments

            # Count promoted candidates
            promoted = conn.execute(
                "SELECT COUNT(*) FROM candidates WHERE promoted = 1"
            ).fetchone()[0]
            stats["promoted_candidates"] = promoted

            return stats

    def cleanup_all_expired(self) -> dict[str, int]:
        """Clean up all expired content. Returns counts by table."""
        now = datetime.utcnow().isoformat()
        counts = {}

        with self._get_connection() as conn:
            for table in ["fragments", "working_objects", "clusters", "candidates", "analogies"]:
                cursor = conn.execute(
                    f"DELETE FROM {table} WHERE expires_at IS NOT NULL AND expires_at < ?",
                    (now,)
                )
                counts[table] = cursor.rowcount

            conn.commit()

        return counts
