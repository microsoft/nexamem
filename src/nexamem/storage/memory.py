"""In-memory storage implementation for NexaMem."""

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from .base import BaseAsyncStorage, BaseStorage


@dataclass
class MemoryData:
    """In-memory data structure."""

    memories: dict[str, dict[str, Any]] = field(default_factory=dict)
    indexes: dict[str, set[str]] = field(default_factory=dict)
    audit_log: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class MemoryStorage(BaseStorage):
    """Synchronous in-memory storage implementation."""

    def __init__(self) -> None:
        self._data = MemoryData()

    def store_memory(
        self,
        memory_id: str,
        content: str,
        metadata: dict[str, Any] | None = None,
        scope: str | None = None,
    ) -> bool:
        """Store memory in memory."""
        try:
            previous = self._data.memories.get(memory_id)
            timestamp = datetime.now(UTC).isoformat()
            memory_data = {
                "content": content,
                "metadata": metadata or {},
                "scope": scope,
                "created_at": previous["created_at"] if previous else timestamp,
                "updated_at": timestamp,
            }

            self._data.memories[memory_id] = memory_data
            previous_scope = previous.get("scope") if previous else None
            if previous_scope and previous_scope != scope:
                previous_index = self._data.indexes.get(previous_scope, set())
                previous_index.discard(memory_id)
                if not previous_index:
                    self._data.indexes.pop(previous_scope, None)

            # Update indexes
            if scope:
                if scope not in self._data.indexes:
                    self._data.indexes[scope] = set()
                self._data.indexes[scope].add(memory_id)

            # Add to audit log
            self._data.audit_log.append(
                {
                    "memory_id": memory_id,
                    "action": "store",
                    "timestamp": datetime.now(UTC).isoformat(),
                    "scope": scope,
                }
            )

            return True
        except Exception:
            return False

    def retrieve_memory(self, memory_id: str) -> dict[str, Any] | None:
        """Retrieve memory from memory."""
        return self._data.memories.get(memory_id)

    def delete_memory(self, memory_id: str) -> bool:
        """Delete memory from memory."""
        try:
            if memory_id not in self._data.memories:
                return False

            memory_data = self._data.memories[memory_id]
            scope = memory_data.get("scope")

            # Remove from main storage
            del self._data.memories[memory_id]

            # Remove from indexes
            if scope and scope in self._data.indexes:
                self._data.indexes[scope].discard(memory_id)
                if not self._data.indexes[scope]:
                    del self._data.indexes[scope]

            # Add to audit log
            self._data.audit_log.append(
                {
                    "memory_id": memory_id,
                    "action": "delete",
                    "timestamp": datetime.now(UTC).isoformat(),
                    "scope": scope,
                }
            )

            return True
        except Exception:
            return False

    def list_memories(self, scope: str | None = None, limit: int | None = None) -> list[str]:
        """List memory IDs, optionally filtered by scope."""
        if scope:
            memory_ids = list(self._data.indexes.get(scope, set()))
        else:
            memory_ids = list(self._data.memories.keys())

        # Sort by creation time (newest first)
        memory_ids.sort(
            key=lambda mid: self._data.memories.get(mid, {}).get("created_at", ""), reverse=True
        )

        if limit:
            memory_ids = memory_ids[:limit]

        return memory_ids

    def search_memories(
        self, query: str, scope: str | None = None, limit: int | None = None
    ) -> list[str]:
        """Search memories by content (simple text search)."""
        query_lower = query.lower()
        matching_ids = []

        search_pool = self._data.indexes.get(scope, set()) if scope else self._data.memories.keys()

        for memory_id in search_pool:
            memory_data = self._data.memories.get(memory_id)
            if memory_data:
                content = memory_data.get("content", "").lower()
                if query_lower in content:
                    matching_ids.append(memory_id)

        # Sort by creation time (newest first)
        matching_ids.sort(
            key=lambda mid: self._data.memories.get(mid, {}).get("created_at", ""), reverse=True
        )

        if limit:
            matching_ids = matching_ids[:limit]

        return matching_ids

    def get_audit_log(
        self, memory_id: str | None = None, limit: int | None = None
    ) -> list[dict[str, Any]]:
        """Get audit log entries."""
        if memory_id:
            entries = [
                entry for entry in self._data.audit_log if entry.get("memory_id") == memory_id
            ]
        else:
            entries = self._data.audit_log.copy()

        # Sort by timestamp (newest first)
        entries.sort(key=lambda e: e.get("timestamp", ""), reverse=True)

        if limit:
            entries = entries[:limit]

        return entries

    def get_stats(self) -> dict[str, Any]:
        """Get storage statistics."""
        return {
            "total_memories": len(self._data.memories),
            "total_scopes": len(self._data.indexes),
            "audit_entries": len(self._data.audit_log),
            "storage_type": "memory",
        }


class AsyncMemoryStorage(BaseAsyncStorage):
    """Asynchronous in-memory storage implementation."""

    def __init__(self) -> None:
        self._sync_storage = MemoryStorage()
        self._lock = asyncio.Lock()

    async def store_memory(
        self,
        memory_id: str,
        content: str,
        metadata: dict[str, Any] | None = None,
        scope: str | None = None,
    ) -> bool:
        """Store memory in memory (async)."""
        async with self._lock:
            return self._sync_storage.store_memory(memory_id, content, metadata, scope)

    async def retrieve_memory(self, memory_id: str) -> dict[str, Any] | None:
        """Retrieve memory from memory (async)."""
        async with self._lock:
            return self._sync_storage.retrieve_memory(memory_id)

    async def delete_memory(self, memory_id: str) -> bool:
        """Delete memory from memory (async)."""
        async with self._lock:
            return self._sync_storage.delete_memory(memory_id)

    async def list_memories(self, scope: str | None = None, limit: int | None = None) -> list[str]:
        """List memory IDs (async)."""
        async with self._lock:
            return self._sync_storage.list_memories(scope, limit)

    async def search_memories(
        self, query: str, scope: str | None = None, limit: int | None = None
    ) -> list[str]:
        """Search memories (async)."""
        async with self._lock:
            return self._sync_storage.search_memories(query, scope, limit)

    async def get_audit_log(
        self, memory_id: str | None = None, limit: int | None = None
    ) -> list[dict[str, Any]]:
        """Get audit log (async)."""
        async with self._lock:
            return self._sync_storage.get_audit_log(memory_id, limit)

    async def get_stats(self) -> dict[str, Any]:
        """Get statistics (async)."""
        async with self._lock:
            return self._sync_storage.get_stats()
