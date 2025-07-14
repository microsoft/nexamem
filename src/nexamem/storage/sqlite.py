"""SQLite-based storage implementation for NexaMem."""

import asyncio
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import BaseAsyncStorage, BaseStorage


class SQLiteStorage(BaseStorage):
    """Synchronous SQLite-based storage implementation."""

    def __init__(self, database_path: str):
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()

    def _init_database(self) -> None:
        """Initialize the SQLite database with required tables."""
        with sqlite3.connect(self.database_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    memory_id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    metadata TEXT NOT NULL DEFAULT '{}',
                    scope TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    memory_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    scope TEXT
                )
            """)

            # Create indexes for better performance
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_memories_scope
                ON memories(scope)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_memories_created_at
                ON memories(created_at DESC)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_log_memory_id
                ON audit_log(memory_id)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_log_timestamp
                ON audit_log(timestamp DESC)
            """)

            conn.commit()

    def store_memory(
        self,
        memory_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        scope: Optional[str] = None
    ) -> bool:
        """Store memory in SQLite database."""
        try:
            metadata_json = json.dumps(metadata or {})
            timestamp = datetime.now(timezone.utc).isoformat()

            with sqlite3.connect(self.database_path) as conn:
                # Store or update memory
                conn.execute("""
                    INSERT OR REPLACE INTO memories 
                    (memory_id, content, metadata, scope, created_at, updated_at)
                    VALUES (?, ?, ?, ?, 
                        COALESCE((SELECT created_at FROM memories WHERE memory_id = ?), ?),
                        ?)
                """, (memory_id, content, metadata_json, scope, memory_id, timestamp, timestamp))

                # Add audit log entry
                conn.execute("""
                    INSERT INTO audit_log (memory_id, action, timestamp, scope)
                    VALUES (?, 'store', ?, ?)
                """, (memory_id, timestamp, scope))

                conn.commit()
            return True
        except (sqlite3.Error, json.JSONEncodeError):
            return False

    def retrieve_memory(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve memory from SQLite database."""
        try:
            with sqlite3.connect(self.database_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT memory_id, content, metadata, scope, created_at, updated_at
                    FROM memories WHERE memory_id = ?
                """, (memory_id,))

                row = cursor.fetchone()
                if row:
                    return {
                        'content': row['content'],
                        'metadata': json.loads(row['metadata']),
                        'scope': row['scope'],
                        'created_at': row['created_at'],
                        'updated_at': row['updated_at']
                    }
        except (sqlite3.Error, json.JSONDecodeError):
            pass
        return None

    def delete_memory(self, memory_id: str) -> bool:
        """Delete memory from SQLite database."""
        try:
            with sqlite3.connect(self.database_path) as conn:
                # Get scope before deletion for audit log
                cursor = conn.execute("""
                    SELECT scope FROM memories WHERE memory_id = ?
                """, (memory_id,))
                row = cursor.fetchone()
                if not row:
                    return False

                scope = row[0]

                # Delete the memory
                conn.execute("DELETE FROM memories WHERE memory_id = ?", (memory_id,))

                # Add audit log entry
                timestamp = datetime.utcnow().isoformat()
                conn.execute("""
                    INSERT INTO audit_log (memory_id, action, timestamp, scope)
                    VALUES (?, 'delete', ?, ?)
                """, (memory_id, timestamp, scope))

                conn.commit()
            return True
        except sqlite3.Error:
            return False

    def list_memories(
        self,
        scope: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[str]:
        """List memory IDs, optionally filtered by scope."""
        try:
            with sqlite3.connect(self.database_path) as conn:
                if scope:
                    query = """
                        SELECT memory_id FROM memories 
                        WHERE scope = ? 
                        ORDER BY created_at DESC
                    """
                    params = (scope,)
                else:
                    query = """
                        SELECT memory_id FROM memories 
                        ORDER BY created_at DESC
                    """
                    params = ()

                if limit:
                    query += " LIMIT ?"
                    params = params + (limit,)

                cursor = conn.execute(query, params)
                return [row[0] for row in cursor.fetchall()]
        except sqlite3.Error:
            pass
        return []

    def search_memories(
        self,
        query: str,
        scope: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[str]:
        """Search memories by content using SQLite FTS or LIKE."""
        try:
            with sqlite3.connect(self.database_path) as conn:
                search_pattern = f"%{query}%"

                if scope:
                    sql_query = """
                        SELECT memory_id FROM memories 
                        WHERE scope = ? AND content LIKE ?
                        ORDER BY created_at DESC
                    """
                    params = (scope, search_pattern)
                else:
                    sql_query = """
                        SELECT memory_id FROM memories 
                        WHERE content LIKE ?
                        ORDER BY created_at DESC
                    """
                    params = (search_pattern,)

                if limit:
                    sql_query += " LIMIT ?"
                    params = params + (limit,)

                cursor = conn.execute(sql_query, params)
                return [row[0] for row in cursor.fetchall()]
        except sqlite3.Error:
            pass
        return []

    def get_audit_log(
        self,
        memory_id: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get audit log entries."""
        try:
            with sqlite3.connect(self.database_path) as conn:
                conn.row_factory = sqlite3.Row

                if memory_id:
                    query = """
                        SELECT memory_id, action, timestamp, scope
                        FROM audit_log 
                        WHERE memory_id = ?
                        ORDER BY timestamp DESC
                    """
                    params = (memory_id,)
                else:
                    query = """
                        SELECT memory_id, action, timestamp, scope
                        FROM audit_log 
                        ORDER BY timestamp DESC
                    """
                    params = ()

                if limit:
                    query += " LIMIT ?"
                    params = params + (limit,)

                cursor = conn.execute(query, params)
                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error:
            pass
        return []

    def get_stats(self) -> Dict[str, Any]:
        """Get storage statistics."""
        try:
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.execute("SELECT COUNT(*) FROM memories")
                total_memories = cursor.fetchone()[0]

                cursor = conn.execute("SELECT COUNT(DISTINCT scope) FROM memories WHERE scope IS NOT NULL")
                total_scopes = cursor.fetchone()[0]

                cursor = conn.execute("SELECT COUNT(*) FROM audit_log")
                audit_entries = cursor.fetchone()[0]

                return {
                    'total_memories': total_memories,
                    'total_scopes': total_scopes,
                    'audit_entries': audit_entries,
                    'storage_type': 'sqlite',
                    'database_path': str(self.database_path)
                }
        except sqlite3.Error:
            pass
        return {
            'total_memories': 0,
            'total_scopes': 0,
            'audit_entries': 0,
            'storage_type': 'sqlite',
            'database_path': str(self.database_path)
        }


class AsyncSQLiteStorage(BaseAsyncStorage):
    """Asynchronous SQLite-based storage implementation."""

    def __init__(self, database_path: str):
        self._sync_storage = SQLiteStorage(database_path)
        self._lock = asyncio.Lock()

    async def store_memory(
        self,
        memory_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        scope: Optional[str] = None
    ) -> bool:
        """Store memory in SQLite database (async)."""
        async with self._lock:
            return self._sync_storage.store_memory(memory_id, content, metadata, scope)

    async def retrieve_memory(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve memory from SQLite database (async)."""
        async with self._lock:
            return self._sync_storage.retrieve_memory(memory_id)

    async def delete_memory(self, memory_id: str) -> bool:
        """Delete memory from SQLite database (async)."""
        async with self._lock:
            return self._sync_storage.delete_memory(memory_id)

    async def list_memories(
        self,
        scope: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[str]:
        """List memory IDs (async)."""
        async with self._lock:
            return self._sync_storage.list_memories(scope, limit)

    async def search_memories(
        self,
        query: str,
        scope: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[str]:
        """Search memories (async)."""
        async with self._lock:
            return self._sync_storage.search_memories(query, scope, limit)

    async def get_audit_log(
        self,
        memory_id: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get audit log (async)."""
        async with self._lock:
            return self._sync_storage.get_audit_log(memory_id, limit)

    async def get_stats(self) -> Dict[str, Any]:
        """Get statistics (async)."""
        async with self._lock:
            return self._sync_storage.get_stats()
