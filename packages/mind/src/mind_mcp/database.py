"""SQLite database layer for Mind MCP v2.

Enhanced with cognitive memory types, conflict tracking, and reflections.
"""

from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Generator

import numpy as np

from .models import Memory, Decision, Conflict, Reflection, MemoryType, ConflictStatus


# Default database path
DEFAULT_DB_PATH = Path.home() / ".mind" / "v2" / "memories.db"

# Schema version for migrations
SCHEMA_VERSION = 2


class Database:
    """SQLite database with vector storage for memories."""

    def __init__(self, db_path: str | Path | None = None):
        """Initialize database connection.

        Args:
            db_path: Path to SQLite database. Defaults to ~/.mind/v2/memories.db
        """
        self.db_path = Path(db_path or os.environ.get("MIND_DB_PATH", DEFAULT_DB_PATH))
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()
        self._run_migrations()

    def _init_schema(self) -> None:
        """Initialize database schema."""
        with self._connection() as conn:
            # Schema version tracking
            conn.execute("""
                CREATE TABLE IF NOT EXISTS schema_version (
                    version INTEGER PRIMARY KEY
                )
            """)

            # Memories table (enhanced with cognitive types)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    content TEXT NOT NULL,
                    content_type TEXT DEFAULT 'observation',
                    memory_type TEXT DEFAULT 'semantic',
                    temporal_level INTEGER DEFAULT 2,
                    salience REAL DEFAULT 1.0,
                    importance REAL DEFAULT 0.7,
                    last_accessed TEXT,
                    access_count INTEGER DEFAULT 0,
                    embedding BLOB,
                    created_at TEXT NOT NULL,
                    updated_at TEXT
                )
            """)

            # FTS5 for keyword search
            conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
                    content,
                    memory_id UNINDEXED,
                    user_id UNINDEXED
                )
            """)

            # Decisions table for learning
            conn.execute("""
                CREATE TABLE IF NOT EXISTS decisions (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    memory_ids TEXT,
                    decision_summary TEXT,
                    outcome_quality REAL,
                    outcome_signal TEXT,
                    salience_changes TEXT,
                    created_at TEXT NOT NULL
                )
            """)

            # Conflicts table for contradiction handling
            conn.execute("""
                CREATE TABLE IF NOT EXISTS conflicts (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    old_memory_id TEXT NOT NULL,
                    new_memory_id TEXT NOT NULL,
                    old_claim TEXT NOT NULL,
                    new_claim TEXT NOT NULL,
                    old_confidence REAL DEFAULT 0.5,
                    new_confidence REAL DEFAULT 0.5,
                    similarity_score REAL DEFAULT 0.0,
                    conflict_type TEXT DEFAULT 'semantic',
                    status TEXT DEFAULT 'pending',
                    resolution_note TEXT,
                    resolved_at TEXT,
                    detected_at TEXT NOT NULL,
                    FOREIGN KEY (old_memory_id) REFERENCES memories(id),
                    FOREIGN KEY (new_memory_id) REFERENCES memories(id)
                )
            """)

            # Reflections table for periodic insights
            conn.execute("""
                CREATE TABLE IF NOT EXISTS reflections (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    period_start TEXT NOT NULL,
                    period_end TEXT NOT NULL,
                    source_memory_ids TEXT,
                    memory_count INTEGER DEFAULT 0,
                    content TEXT NOT NULL,
                    patterns TEXT,
                    unresolved_goals TEXT,
                    key_decisions TEXT,
                    contradictions TEXT,
                    action_items TEXT,
                    trigger TEXT DEFAULT 'count',
                    created_at TEXT NOT NULL
                )
            """)

            # Core indexes (columns that always exist)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_user ON memories(user_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_salience ON memories(salience DESC)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_decisions_user ON decisions(user_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_conflicts_user ON conflicts(user_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_conflicts_status ON conflicts(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_reflections_user ON reflections(user_id)")

            conn.commit()

    def _create_v2_indexes(self, conn: sqlite3.Connection) -> None:
        """Create indexes for v2 columns (called after migration)."""
        try:
            conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_type ON memories(memory_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_importance ON memories(importance DESC)")
        except sqlite3.OperationalError:
            pass  # Columns may not exist yet

    def _run_migrations(self) -> None:
        """Run database migrations if needed."""
        with self._connection() as conn:
            # Get current schema version
            try:
                row = conn.execute("SELECT MAX(version) FROM schema_version").fetchone()
                current_version = row[0] if row and row[0] else 0
            except sqlite3.OperationalError:
                current_version = 0

            if current_version < SCHEMA_VERSION:
                self._migrate_v1_to_v2(conn)
                conn.execute("INSERT OR REPLACE INTO schema_version (version) VALUES (?)", (SCHEMA_VERSION,))
                conn.commit()

            # Create indexes for v2 columns (safe to call even if already exist)
            self._create_v2_indexes(conn)
            conn.commit()

    def _migrate_v1_to_v2(self, conn: sqlite3.Connection) -> None:
        """Migrate from v1 schema (no memory_type) to v2."""
        # Check if columns exist
        columns = {row[1] for row in conn.execute("PRAGMA table_info(memories)").fetchall()}

        # Add new columns if they don't exist
        if "memory_type" not in columns:
            conn.execute("ALTER TABLE memories ADD COLUMN memory_type TEXT DEFAULT 'semantic'")

        if "importance" not in columns:
            conn.execute("ALTER TABLE memories ADD COLUMN importance REAL DEFAULT 0.7")

        if "last_accessed" not in columns:
            conn.execute("ALTER TABLE memories ADD COLUMN last_accessed TEXT")

        if "access_count" not in columns:
            conn.execute("ALTER TABLE memories ADD COLUMN access_count INTEGER DEFAULT 0")

        # Migrate existing content_type to memory_type
        type_mapping = {
            "fact": "semantic",
            "preference": "preference",
            "event": "episodic",
            "goal": "episodic",
            "observation": "semantic",
            "decision": "episodic",
        }

        for old_type, new_type in type_mapping.items():
            conn.execute(
                "UPDATE memories SET memory_type = ? WHERE content_type = ? AND memory_type = 'semantic'",
                (new_type, old_type)
            )

        # Set default importance based on type
        importance_mapping = {
            "episodic": 0.5,
            "semantic": 0.7,
            "procedural": 0.8,
            "preference": 0.9,
            "reflection": 0.95,
        }

        for mem_type, importance in importance_mapping.items():
            conn.execute(
                "UPDATE memories SET importance = ? WHERE memory_type = ? AND importance = 0.7",
                (importance, mem_type)
            )

    @contextmanager
    def _connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Context manager for database connections."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    # --- Memory operations ---

    def insert_memory(
        self,
        memory: Memory,
        embedding: np.ndarray | None = None,
    ) -> str:
        """Insert a new memory with optional embedding.

        Args:
            memory: Memory object to insert
            embedding: Numpy array of embedding vector

        Returns:
            Memory ID
        """
        embedding_blob = embedding.tobytes() if embedding is not None else None

        with self._connection() as conn:
            conn.execute(
                """
                INSERT INTO memories (
                    id, user_id, content, content_type, memory_type,
                    temporal_level, salience, importance, last_accessed,
                    access_count, embedding, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    memory.id,
                    memory.user_id,
                    memory.content,
                    memory.content_type,
                    memory.memory_type.value if hasattr(memory.memory_type, 'value') else memory.memory_type,
                    memory.temporal_level,
                    memory.salience,
                    memory.importance,
                    memory.last_accessed.isoformat() if memory.last_accessed else None,
                    memory.access_count,
                    embedding_blob,
                    memory.created_at.isoformat(),
                ),
            )

            # Insert into FTS index
            conn.execute(
                "INSERT INTO memories_fts (content, memory_id, user_id) VALUES (?, ?, ?)",
                (memory.content, memory.id, memory.user_id),
            )

            conn.commit()

        return memory.id

    def get_memory(self, memory_id: str) -> Memory | None:
        """Get a memory by ID."""
        with self._connection() as conn:
            row = conn.execute(
                "SELECT * FROM memories WHERE id = ?", (memory_id,)
            ).fetchone()

            if row is None:
                return None

            return self._row_to_memory(row)

    def get_memories_by_user(
        self,
        user_id: str,
        limit: int = 100,
        min_salience: float = 0.0,
    ) -> list[tuple[Memory, np.ndarray | None]]:
        """Get all memories for a user with their embeddings.

        Args:
            user_id: User ID to filter by
            limit: Maximum number of memories to return
            min_salience: Minimum salience threshold

        Returns:
            List of (Memory, embedding) tuples
        """
        with self._connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM memories
                WHERE user_id = ? AND salience >= ?
                ORDER BY salience DESC, created_at DESC
                LIMIT ?
                """,
                (user_id, min_salience, limit),
            ).fetchall()

            results = []
            for row in rows:
                memory = self._row_to_memory(row)
                embedding = None
                if row["embedding"]:
                    embedding = np.frombuffer(row["embedding"], dtype=np.float32)
                results.append((memory, embedding))

            return results

    def update_salience(self, memory_id: str, new_salience: float) -> bool:
        """Update the salience of a memory.

        Args:
            memory_id: Memory ID to update
            new_salience: New salience value (0.0-1.0)

        Returns:
            True if updated, False if memory not found
        """
        new_salience = max(0.0, min(1.0, new_salience))

        with self._connection() as conn:
            cursor = conn.execute(
                """
                UPDATE memories
                SET salience = ?, updated_at = ?
                WHERE id = ?
                """,
                (new_salience, datetime.utcnow().isoformat(), memory_id),
            )
            conn.commit()
            return cursor.rowcount > 0

    def delete_memory(self, memory_id: str) -> bool:
        """Delete a memory.

        Args:
            memory_id: Memory ID to delete

        Returns:
            True if deleted, False if memory not found
        """
        with self._connection() as conn:
            # Delete from FTS
            conn.execute("DELETE FROM memories_fts WHERE memory_id = ?", (memory_id,))
            # Delete from main table
            cursor = conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
            conn.commit()
            return cursor.rowcount > 0

    def _row_to_memory(self, row: sqlite3.Row) -> Memory:
        """Convert a database row to a Memory object."""
        # Convert sqlite3.Row to dict for safer access
        row_dict = dict(row)

        # Handle memory_type - may not exist in old rows
        memory_type_str = row_dict.get("memory_type", "semantic")
        try:
            memory_type = MemoryType(memory_type_str)
        except (ValueError, KeyError):
            memory_type = MemoryType.SEMANTIC

        # Parse last_accessed if present and not None
        last_accessed = None
        if row_dict.get("last_accessed"):
            last_accessed = datetime.fromisoformat(row_dict["last_accessed"])

        # Parse updated_at if present and not None
        updated_at = None
        if row_dict.get("updated_at"):
            updated_at = datetime.fromisoformat(row_dict["updated_at"])

        return Memory(
            id=row_dict["id"],
            user_id=row_dict["user_id"],
            content=row_dict["content"],
            content_type=row_dict["content_type"],
            memory_type=memory_type,
            temporal_level=row_dict["temporal_level"],
            salience=row_dict["salience"],
            importance=row_dict.get("importance", 0.7),
            last_accessed=last_accessed,
            access_count=row_dict.get("access_count", 0),
            created_at=datetime.fromisoformat(row_dict["created_at"]),
            updated_at=updated_at,
        )

    def update_last_accessed(self, memory_id: str) -> bool:
        """Update last_accessed timestamp and increment access_count.

        Args:
            memory_id: Memory ID to update

        Returns:
            True if updated, False if memory not found
        """
        with self._connection() as conn:
            cursor = conn.execute(
                """
                UPDATE memories
                SET last_accessed = ?, access_count = access_count + 1, updated_at = ?
                WHERE id = ?
                """,
                (datetime.utcnow().isoformat(), datetime.utcnow().isoformat(), memory_id),
            )
            conn.commit()
            return cursor.rowcount > 0

    # --- FTS operations ---

    def fts_search(
        self,
        user_id: str,
        query: str,
        limit: int = 50,
    ) -> list[tuple[str, float]]:
        """Full-text search using FTS5 BM25.

        Args:
            user_id: User ID to filter by
            query: Search query
            limit: Maximum results

        Returns:
            List of (memory_id, bm25_score) tuples
        """
        # Sanitize query for FTS5
        tokens = [t for t in query.lower().split() if t.isalnum()]
        if not tokens:
            return []

        fts_query = " OR ".join(tokens)

        with self._connection() as conn:
            rows = conn.execute(
                """
                SELECT memory_id, bm25(memories_fts) as score
                FROM memories_fts
                WHERE memories_fts MATCH ? AND user_id = ?
                ORDER BY score
                LIMIT ?
                """,
                (fts_query, user_id, limit),
            ).fetchall()

            # BM25 scores are negative (lower is better), convert to positive
            return [(row["memory_id"], -row["score"]) for row in rows]

    # --- Decision operations ---

    def insert_decision(self, decision: Decision) -> str:
        """Insert a decision record.

        Args:
            decision: Decision object to insert

        Returns:
            Decision ID
        """
        with self._connection() as conn:
            conn.execute(
                """
                INSERT INTO decisions (id, user_id, memory_ids, decision_summary, outcome_quality, outcome_signal, salience_changes, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    decision.id,
                    decision.user_id,
                    json.dumps(decision.memory_ids),
                    decision.decision_summary,
                    decision.outcome_quality,
                    decision.outcome_signal,
                    json.dumps(decision.salience_changes),
                    decision.created_at.isoformat(),
                ),
            )
            conn.commit()

        return decision.id

    def get_decisions_by_user(
        self,
        user_id: str,
        limit: int = 100,
    ) -> list[Decision]:
        """Get decisions for a user."""
        with self._connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM decisions
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (user_id, limit),
            ).fetchall()

            return [self._row_to_decision(row) for row in rows]

    def _row_to_decision(self, row: sqlite3.Row) -> Decision:
        """Convert a database row to a Decision object."""
        return Decision(
            id=row["id"],
            user_id=row["user_id"],
            memory_ids=json.loads(row["memory_ids"]) if row["memory_ids"] else [],
            decision_summary=row["decision_summary"],
            outcome_quality=row["outcome_quality"],
            outcome_signal=row["outcome_signal"],
            salience_changes=json.loads(row["salience_changes"]) if row["salience_changes"] else {},
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    # --- Conflict operations ---

    def insert_conflict(self, conflict: Conflict) -> str:
        """Insert a conflict record.

        Args:
            conflict: Conflict object to insert

        Returns:
            Conflict ID
        """
        with self._connection() as conn:
            conn.execute(
                """
                INSERT INTO conflicts (
                    id, user_id, old_memory_id, new_memory_id,
                    old_claim, new_claim, old_confidence, new_confidence,
                    similarity_score, conflict_type, status,
                    resolution_note, resolved_at, detected_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    conflict.id,
                    conflict.user_id,
                    conflict.old_memory_id,
                    conflict.new_memory_id,
                    conflict.old_claim,
                    conflict.new_claim,
                    conflict.old_confidence,
                    conflict.new_confidence,
                    conflict.similarity_score,
                    conflict.conflict_type,
                    conflict.status.value,
                    conflict.resolution_note,
                    conflict.resolved_at.isoformat() if conflict.resolved_at else None,
                    conflict.detected_at.isoformat(),
                ),
            )
            conn.commit()
        return conflict.id

    def get_conflicts_by_user(
        self,
        user_id: str,
        status: ConflictStatus | None = None,
        limit: int = 100,
    ) -> list[Conflict]:
        """Get conflicts for a user.

        Args:
            user_id: User ID to filter by
            status: Optional status filter
            limit: Maximum conflicts to return
        """
        with self._connection() as conn:
            if status:
                rows = conn.execute(
                    """
                    SELECT * FROM conflicts
                    WHERE user_id = ? AND status = ?
                    ORDER BY detected_at DESC
                    LIMIT ?
                    """,
                    (user_id, status.value, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT * FROM conflicts
                    WHERE user_id = ?
                    ORDER BY detected_at DESC
                    LIMIT ?
                    """,
                    (user_id, limit),
                ).fetchall()

            return [self._row_to_conflict(row) for row in rows]

    def resolve_conflict(
        self,
        conflict_id: str,
        status: ConflictStatus,
        resolution_note: str | None = None,
    ) -> bool:
        """Resolve a conflict.

        Args:
            conflict_id: Conflict ID to resolve
            status: New status (resolved or superseded)
            resolution_note: Optional note explaining resolution
        """
        with self._connection() as conn:
            cursor = conn.execute(
                """
                UPDATE conflicts
                SET status = ?, resolution_note = ?, resolved_at = ?
                WHERE id = ?
                """,
                (status.value, resolution_note, datetime.utcnow().isoformat(), conflict_id),
            )
            conn.commit()
            return cursor.rowcount > 0

    def _row_to_conflict(self, row: sqlite3.Row) -> Conflict:
        """Convert a database row to a Conflict object."""
        return Conflict(
            id=row["id"],
            user_id=row["user_id"],
            old_memory_id=row["old_memory_id"],
            new_memory_id=row["new_memory_id"],
            old_claim=row["old_claim"],
            new_claim=row["new_claim"],
            old_confidence=row["old_confidence"],
            new_confidence=row["new_confidence"],
            similarity_score=row["similarity_score"],
            conflict_type=row["conflict_type"],
            status=ConflictStatus(row["status"]),
            resolution_note=row["resolution_note"],
            resolved_at=datetime.fromisoformat(row["resolved_at"]) if row["resolved_at"] else None,
            detected_at=datetime.fromisoformat(row["detected_at"]),
        )

    # --- Reflection operations ---

    def insert_reflection(self, reflection: Reflection) -> str:
        """Insert a reflection record.

        Args:
            reflection: Reflection object to insert

        Returns:
            Reflection ID
        """
        with self._connection() as conn:
            conn.execute(
                """
                INSERT INTO reflections (
                    id, user_id, period_start, period_end,
                    source_memory_ids, memory_count, content,
                    patterns, unresolved_goals, key_decisions,
                    contradictions, action_items, trigger, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    reflection.id,
                    reflection.user_id,
                    reflection.period_start.isoformat(),
                    reflection.period_end.isoformat(),
                    json.dumps(reflection.source_memory_ids),
                    reflection.memory_count,
                    reflection.content,
                    json.dumps(reflection.patterns),
                    json.dumps(reflection.unresolved_goals),
                    json.dumps(reflection.key_decisions),
                    json.dumps(reflection.contradictions),
                    json.dumps(reflection.action_items),
                    reflection.trigger,
                    reflection.created_at.isoformat(),
                ),
            )
            conn.commit()
        return reflection.id

    def get_reflections_by_user(
        self,
        user_id: str,
        limit: int = 10,
    ) -> list[Reflection]:
        """Get reflections for a user.

        Args:
            user_id: User ID to filter by
            limit: Maximum reflections to return
        """
        with self._connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM reflections
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (user_id, limit),
            ).fetchall()

            return [self._row_to_reflection(row) for row in rows]

    def get_memory_count_since_last_reflection(self, user_id: str) -> int:
        """Get count of memories created since last reflection.

        Args:
            user_id: User ID to check
        """
        with self._connection() as conn:
            # Get last reflection time
            last_reflection = conn.execute(
                "SELECT MAX(created_at) FROM reflections WHERE user_id = ?",
                (user_id,)
            ).fetchone()

            if last_reflection and last_reflection[0]:
                count = conn.execute(
                    "SELECT COUNT(*) FROM memories WHERE user_id = ? AND created_at > ?",
                    (user_id, last_reflection[0])
                ).fetchone()[0]
            else:
                count = conn.execute(
                    "SELECT COUNT(*) FROM memories WHERE user_id = ?",
                    (user_id,)
                ).fetchone()[0]

            return count

    def _row_to_reflection(self, row: sqlite3.Row) -> Reflection:
        """Convert a database row to a Reflection object."""
        return Reflection(
            id=row["id"],
            user_id=row["user_id"],
            period_start=datetime.fromisoformat(row["period_start"]),
            period_end=datetime.fromisoformat(row["period_end"]),
            source_memory_ids=json.loads(row["source_memory_ids"]) if row["source_memory_ids"] else [],
            memory_count=row["memory_count"],
            content=row["content"],
            patterns=json.loads(row["patterns"]) if row["patterns"] else [],
            unresolved_goals=json.loads(row["unresolved_goals"]) if row["unresolved_goals"] else [],
            key_decisions=json.loads(row["key_decisions"]) if row["key_decisions"] else [],
            contradictions=json.loads(row["contradictions"]) if row["contradictions"] else [],
            action_items=json.loads(row["action_items"]) if row["action_items"] else [],
            trigger=row["trigger"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    # --- Stats ---

    def get_stats(self, user_id: str | None = None) -> dict[str, Any]:
        """Get database statistics.

        Args:
            user_id: Optional user ID to filter stats

        Returns:
            Dictionary with stats
        """
        with self._connection() as conn:
            if user_id:
                memory_count = conn.execute(
                    "SELECT COUNT(*) FROM memories WHERE user_id = ?", (user_id,)
                ).fetchone()[0]
                decision_count = conn.execute(
                    "SELECT COUNT(*) FROM decisions WHERE user_id = ?", (user_id,)
                ).fetchone()[0]
            else:
                memory_count = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
                decision_count = conn.execute("SELECT COUNT(*) FROM decisions").fetchone()[0]
                user_count = conn.execute(
                    "SELECT COUNT(DISTINCT user_id) FROM memories"
                ).fetchone()[0]

            stats = {
                "total_memories": memory_count,
                "total_decisions": decision_count,
                "db_path": str(self.db_path),
            }

            if not user_id:
                stats["total_users"] = user_count

            return stats
