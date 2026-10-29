"""File-based storage implementation for NexaMem."""

import asyncio
import contextlib
import json
from datetime import UTC, datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any
from urllib.parse import quote, unquote

from .base import BaseAsyncStorage, BaseStorage


class FileStorage(BaseStorage):
    """Synchronous file-based storage implementation."""

    def __init__(self, storage_path: str):
        self.storage_path = Path(storage_path)
        self.memories_dir = self.storage_path / "memories"
        self.indexes_dir = self.storage_path / "indexes"
        self.audit_file = self.storage_path / "audit.jsonl"
        self.metadata_file = self.storage_path / "metadata.json"

        # Ensure directories exist
        self.memories_dir.mkdir(parents=True, exist_ok=True)
        self.indexes_dir.mkdir(parents=True, exist_ok=True)
        self.storage_path.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _encode_identifier(identifier: str) -> str:
        """Encode a key as one portable filename component."""
        encoded = quote(identifier, safe="")
        reserved = {"CON", "PRN", "AUX", "NUL"}
        reserved.update(f"{prefix}{number}" for prefix in ("COM", "LPT") for number in range(1, 10))
        if identifier.split(".", 1)[0].upper() in reserved:
            encoded = f"%{ord(encoded[0]):02X}{encoded[1:]}"
        return encoded

    def _get_memory_file(self, memory_id: str) -> Path:
        """Get the file path for a memory."""
        return self.memories_dir / f"{self._encode_identifier(memory_id)}.json"

    def _get_index_file(self, scope: str) -> Path:
        """Get the index file path for a scope."""
        return self.indexes_dir / f"{self._encode_identifier(scope)}.json"

    def _read_json_file(self, file_path: Path) -> Any:
        """Read and parse a JSON file."""
        try:
            if file_path.exists():
                with open(file_path, encoding="utf-8") as f:
                    return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
        return None

    def _write_json_file(self, file_path: Path, data: Any) -> bool:
        """Write data to a JSON file."""
        temporary_path = None
        try:
            serialized = json.dumps(data, indent=2, ensure_ascii=False)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=file_path.parent, delete=False
            ) as temporary_file:
                temporary_path = Path(temporary_file.name)
                temporary_file.write(serialized)
            temporary_path.replace(file_path)
            return True
        except (OSError, TypeError, ValueError):
            return False
        finally:
            if temporary_path is not None:
                with contextlib.suppress(OSError):
                    temporary_path.unlink(missing_ok=True)

    def _append_audit_entry(self, entry: dict[str, Any]) -> None:
        """Append an entry to the audit log."""
        try:
            with open(self.audit_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except OSError:
            pass

    def _update_scope_index(self, scope: str | None, memory_id: str, remove: bool = False) -> None:
        """Update the scope index."""
        if not scope:
            return

        index_file = self._get_index_file(scope)
        index_data = self._read_json_file(index_file) or []

        if remove:
            if memory_id in index_data:
                index_data.remove(memory_id)
        else:
            if memory_id not in index_data:
                index_data.append(memory_id)

        if index_data:
            self._write_json_file(index_file, index_data)
        elif index_file.exists():
            index_file.unlink(missing_ok=True)

    def store_memory(
        self,
        memory_id: str,
        content: str,
        metadata: dict[str, Any] | None = None,
        scope: str | None = None,
    ) -> bool:
        """Store memory to file."""
        try:
            previous = self.retrieve_memory(memory_id)
            timestamp = datetime.now(UTC).isoformat()
            memory_data = {
                "content": content,
                "metadata": metadata or {},
                "scope": scope,
                "created_at": previous["created_at"] if previous else timestamp,
                "updated_at": timestamp,
            }

            memory_file = self._get_memory_file(memory_id)
            if not self._write_json_file(memory_file, memory_data):
                return False

            previous_scope = previous.get("scope") if previous else None
            if previous_scope and previous_scope != scope:
                self._update_scope_index(previous_scope, memory_id, remove=True)

            # Update scope index
            self._update_scope_index(scope, memory_id)

            # Add to audit log
            self._append_audit_entry(
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
        """Retrieve memory from file."""
        memory_file = self._get_memory_file(memory_id)
        data = self._read_json_file(memory_file)
        return data if isinstance(data, dict) else None

    def delete_memory(self, memory_id: str) -> bool:
        """Delete memory file."""
        try:
            memory_file = self._get_memory_file(memory_id)
            if not memory_file.exists():
                return False

            # Get scope before deletion
            memory_data = self._read_json_file(memory_file)
            scope = memory_data.get("scope") if memory_data else None

            # Delete the memory file
            memory_file.unlink()

            # Update scope index
            self._update_scope_index(scope, memory_id, remove=True)

            # Add to audit log
            self._append_audit_entry(
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
            # Use scope index
            index_file = self._get_index_file(scope)
            memory_ids = self._read_json_file(index_file) or []
        else:
            # List all memory files
            memory_ids = []
            if self.memories_dir.exists():
                for file_path in self.memories_dir.glob("*.json"):
                    memory_ids.append(unquote(file_path.stem))

        # Sort by creation time (newest first)
        def get_creation_time(memory_id: str) -> str:
            memory_file = self._get_memory_file(memory_id)
            memory_data = self._read_json_file(memory_file)
            return memory_data.get("created_at", "") if memory_data else ""

        memory_ids.sort(key=get_creation_time, reverse=True)

        if limit:
            memory_ids = memory_ids[:limit]

        return memory_ids

    def search_memories(
        self, query: str, scope: str | None = None, limit: int | None = None
    ) -> list[str]:
        """Search memories by content."""
        query_lower = query.lower()
        matching_ids = []

        search_pool = self.list_memories(scope=scope)

        for memory_id in search_pool:
            memory_data = self.retrieve_memory(memory_id)
            if memory_data:
                content = memory_data.get("content", "").lower()
                if query_lower in content:
                    matching_ids.append(memory_id)

        if limit:
            matching_ids = matching_ids[:limit]

        return matching_ids

    def get_audit_log(
        self, memory_id: str | None = None, limit: int | None = None
    ) -> list[dict[str, Any]]:
        """Get audit log entries."""
        entries: list[dict[str, Any]] = []

        if not self.audit_file.exists():
            return entries

        try:
            with open(self.audit_file, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            entry = json.loads(line)
                            if not memory_id or entry.get("memory_id") == memory_id:
                                entries.append(entry)
                        except json.JSONDecodeError:
                            continue
        except OSError:
            pass

        # Sort by timestamp (newest first)
        entries.sort(key=lambda e: e.get("timestamp", ""), reverse=True)

        if limit:
            entries = entries[:limit]

        return entries

    def get_stats(self) -> dict[str, Any]:
        """Get storage statistics."""
        total_memories = 0
        total_scopes = 0
        audit_entries = 0

        # Count memories
        if self.memories_dir.exists():
            total_memories = len(list(self.memories_dir.glob("*.json")))

        # Count scopes
        if self.indexes_dir.exists():
            total_scopes = len(list(self.indexes_dir.glob("*.json")))

        # Count audit entries
        if self.audit_file.exists():
            try:
                with open(self.audit_file, encoding="utf-8") as f:
                    audit_entries = sum(1 for _ in f)
            except OSError:
                pass

        return {
            "total_memories": total_memories,
            "total_scopes": total_scopes,
            "audit_entries": audit_entries,
            "storage_type": "file",
            "storage_path": str(self.storage_path),
        }


class AsyncFileStorage(BaseAsyncStorage):
    """Asynchronous file-based storage implementation."""

    def __init__(self, storage_path: str):
        self._sync_storage = FileStorage(storage_path)
        self._lock = asyncio.Lock()

    async def store_memory(
        self,
        memory_id: str,
        content: str,
        metadata: dict[str, Any] | None = None,
        scope: str | None = None,
    ) -> bool:
        """Store memory to file (async)."""
        async with self._lock:
            return self._sync_storage.store_memory(memory_id, content, metadata, scope)

    async def retrieve_memory(self, memory_id: str) -> dict[str, Any] | None:
        """Retrieve memory from file (async)."""
        async with self._lock:
            return self._sync_storage.retrieve_memory(memory_id)

    async def delete_memory(self, memory_id: str) -> bool:
        """Delete memory file (async)."""
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
