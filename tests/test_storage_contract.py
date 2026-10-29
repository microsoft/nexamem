"""Shared storage behavior, using only local temporary data."""

import asyncio
import sqlite3
import threading
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import fakeredis
import pytest

from nexamem import AIMemory, AIMemoryConfig, AsyncAIMemory, MemoryScope, StorageConfig
from nexamem.config.storage import AzureRedisConfig
from nexamem.di import DIContainer
from nexamem.retention import EXPIRY_FIELD, expired
from nexamem.storage.base import BaseStorage
from nexamem.storage.file import AsyncFileStorage, FileStorage
from nexamem.storage.memory import AsyncMemoryStorage, MemoryStorage
from nexamem.storage.sqlite import AsyncSQLiteStorage, SQLiteStorage


def configured_backend(backend, tmp_path):
    if backend == "file":
        return StorageConfig.file(str(tmp_path / "files"))
    if backend == "sqlite":
        return StorageConfig.sqlite(str(tmp_path / "memory.db"))
    if backend == "redis":
        return StorageConfig.azure_redis(
            AzureRedisConfig(hostname="unit.redis.cache.windows.net", access_key="test")
        )
    return StorageConfig.memory()


@pytest.mark.parametrize("backend", ["memory", "file", "sqlite", "redis"])
def test_facade_retention_boundaries(backend, tmp_path):
    config = AIMemoryConfig(storage=configured_backend(backend, tmp_path), default_ttl_sec=10)
    client = fakeredis.FakeRedis(decode_responses=True)
    with (
        patch("nexamem.storage.azure_redis.redis.Redis", return_value=client),
        patch("nexamem.retention.time.time", return_value=100) as clock,
    ):
        with AIMemory(config) as memory:
            metadata = {"kind": "note"}
            memory.store("same content", "old", metadata, "session")
            memory.store("same content", "renewed", scope="session", ttl_sec=20)
            assert EXPIRY_FIELD not in metadata
            clock.return_value = 110
            assert memory.retrieve("old") is None
            assert memory.list("session", limit=1) == ["renewed"]
            assert memory.search("same", "session", limit=1) == ["renewed"]
            assert memory.list("session", limit=0) == []
            with pytest.raises(ValueError):
                memory.list(limit=-1)
            with pytest.raises(ValueError):
                memory.store("invalid", ttl_sec=0)
            with pytest.raises(ValueError, match="reserved"):
                memory.store("invalid", metadata={EXPIRY_FIELD: 1})
            memory.store("updated", "renewed", scope="session", ttl_sec=5)
            clock.return_value = 115
            assert memory.purge_expired("other-session") == 0
            assert memory.purge_expired("session") == 1
            assert memory.purge_expired() == 0
            assert memory.get_stats()["total_memories"] == 0
            memory.store("expires", "stats", scope="session")
            clock.return_value = 125
            assert memory.get_stats()["total_memories"] == 0


@pytest.mark.parametrize("backend", ["memory", "file", "sqlite", "redis"])
async def test_async_facade_retention_boundaries(backend, tmp_path):
    config = AIMemoryConfig(storage=configured_backend(backend, tmp_path))
    client = fakeredis.FakeAsyncRedis(decode_responses=True)
    scope = MemoryScope(agent_id="agent", user_id="user", session_id="session", env="test")
    with (
        patch("nexamem.storage.azure_redis.redis_async.Redis", return_value=client),
        patch("nexamem.retention.time.time", return_value=100) as clock,
    ):
        async with AsyncAIMemory(config) as memory:
            memory.register_channel("short", ttl_sec=60)
            first = await memory.write(scope, "short", "first")
            await memory.write(scope, "short", "second", ttl_override=120)
            await memory.store("persistent", "forever", scope="persistent")
            clock.return_value = 160
            assert await memory.retrieve(first) is None
            assert (await memory.read(scope, "short"))[0] == ["second"]
            assert len(await memory.search("second", scope.get_key_prefix("short"), 1)) == 1
            assert await memory.list(scope.get_key_prefix("short"), 0) == []
            with pytest.raises(ValueError):
                await memory.list(limit=-1)
            clock.return_value = 220
            assert await memory.purge_expired() == 1
            assert await memory.purge_expired() == 0
            assert (await memory.get_stats())["total_memories"] == 1
            assert (await memory.retrieve("forever"))["content"] == "persistent"
            await memory.store("expires", "stats", ttl_sec=1)
            clock.return_value = 221
            assert (await memory.get_stats())["total_memories"] == 1


def test_sync_channel_retention_and_invalid_expiry():
    scope = MemoryScope(agent_id="agent", user_id="user", session_id="session", env="test")
    with patch("nexamem.retention.time.time", return_value=100) as clock:
        memory = AIMemory(AIMemoryConfig(storage=StorageConfig.memory()))
        memory.register_channel("short", ttl_sec=60)
        memory.write(scope, "short", "first", ttl_override=1)
        memory.write(scope, "short", "second")
        clock.return_value = 101
        assert memory.read(scope, "short")[0] == ["second"]
        clock.return_value = 160
        assert memory.read(scope, "short")[0] == []
    assert expired({"metadata": {EXPIRY_FIELD: "invalid"}})
    assert expired({"metadata": {EXPIRY_FIELD: float("nan")}})
    assert not expired({"metadata": {}})


async def test_facade_lifecycle_ownership():
    config = AIMemoryConfig(storage=StorageConfig.memory())
    memory = AIMemory(config)
    memory._storage.close = Mock()
    with memory:
        pass
    memory._storage.close.assert_called_once()
    container = DIContainer()
    container.register(
        BaseStorage,
        Mock(can_provide=Mock(return_value=True), provide=Mock(return_value=memory._storage)),
    )
    with AIMemory(config, container):
        pass
    memory._storage.close.assert_called_once()

    async_memory = AsyncAIMemory(config)
    async_memory._storage.close = AsyncMock()
    async with async_memory:
        pass
    async_memory._storage.close.assert_awaited_once()
    from nexamem.storage.base import BaseAsyncStorage

    container = DIContainer()
    container.register(
        BaseAsyncStorage,
        Mock(can_provide=Mock(return_value=True), provide=Mock(return_value=async_memory._storage)),
    )
    async with AsyncAIMemory(config, container):
        pass
    async_memory._storage.close.assert_awaited_once()
    await async_memory.close()
    assert async_memory._storage.close.await_count == 2
    with MemoryStorage():
        pass
    async with AsyncMemoryStorage() as backend:
        await backend.aclose()


@pytest.mark.parametrize("backend", [AsyncFileStorage, AsyncSQLiteStorage])
async def test_local_async_io_runs_in_worker_and_serializes_cancellation(backend, tmp_path):
    storage = backend(str(tmp_path / "data"))
    started, release = threading.Event(), threading.Event()
    thread_ids = []

    def operation(*args):
        thread_ids.append(threading.get_ident())
        started.set()
        assert release.wait(5)
        return True

    storage._sync_storage.store_memory = operation
    first = asyncio.create_task(storage.store_memory("one", "content"))
    try:
        assert await asyncio.to_thread(started.wait, 2)
        assert thread_ids == [thread_ids[0]] and thread_ids[0] != threading.get_ident()
        first.cancel()
        second = asyncio.create_task(storage.store_memory("two", "content"))
        await asyncio.get_running_loop().run_in_executor(None, lambda: None)
        first.cancel()
        await asyncio.get_running_loop().run_in_executor(None, lambda: None)
        assert not first.done() and len(thread_ids) == 1
    finally:
        release.set()
    with pytest.raises(asyncio.CancelledError):
        await first
    assert await second
    assert len(thread_ids) == 2


@pytest.fixture(params=["memory", "file", "sqlite"])
def storage(request: pytest.FixtureRequest, tmp_path: Path) -> BaseStorage:
    """Create an isolated backend for each contract test."""
    if request.param == "memory":
        return MemoryStorage()
    if request.param == "file":
        return FileStorage(str(tmp_path / "files"))
    return SQLiteStorage(str(tmp_path / "memories.db"))


@pytest.mark.parametrize("new_scope", ["second", None])
def test_overwrite_removes_old_scope(storage: BaseStorage, new_scope: str | None) -> None:
    assert storage.store_memory("shared", "original", scope="first")
    assert storage.store_memory("shared", "replacement", scope=new_scope)
    assert storage.list_memories("first") == []
    assert storage.search_memories("replacement", "first") == []
    assert storage.list_memories(new_scope) == ["shared"]
    assert storage.get_stats()["total_scopes"] == int(new_scope is not None)


def test_overwrite_preserves_creation_time(storage: BaseStorage) -> None:
    assert storage.store_memory("same", "original")
    original = storage.retrieve_memory("same")
    assert original is not None
    assert storage.store_memory("same", "replacement")
    updated = storage.retrieve_memory("same")
    assert updated is not None
    assert updated["created_at"] == original["created_at"]
    assert updated["content"] == "replacement"


def test_sqlite_rejects_unserializable_metadata(tmp_path: Path) -> None:
    storage = SQLiteStorage(str(tmp_path / "memories.db"))
    assert storage.store_memory("bad", "content", {"value": object()}) is False
    assert storage.retrieve_memory("bad") is None
    assert storage.get_audit_log() == []


@pytest.mark.parametrize("memory_id", ["../escaped", "agent:user:session", "CON", "percent%id"])
def test_file_identifiers_are_contained(tmp_path: Path, memory_id: str) -> None:
    storage = FileStorage(str(tmp_path / "files"))
    assert storage.store_memory(memory_id, "content", scope="agent:user:session:channel")
    assert storage.list_memories() == [memory_id]
    assert storage.list_memories("agent:user:session:channel") == [memory_id]
    assert storage.retrieve_memory(memory_id)["content"] == "content"
    assert not (tmp_path / "files" / "escaped.json").exists()
    assert storage.delete_memory(memory_id)
    assert storage.list_memories() == []


def test_failed_file_serialization_preserves_previous_value(tmp_path: Path) -> None:
    storage = FileStorage(str(tmp_path / "files"))
    assert storage.store_memory("same", "original", scope="first")
    assert storage.store_memory("same", "replacement", {"bad": object()}, "second") is False
    assert storage.retrieve_memory("same")["content"] == "original"
    assert storage.list_memories("first") == ["same"]
    assert storage.list_memories("second") == []


def test_storage_lifecycle(storage: BaseStorage) -> None:
    assert storage.retrieve_memory("missing") is None
    assert storage.delete_memory("missing") is False
    assert storage.get_audit_log() == []
    assert storage.list_memories() == []
    for sequence, (memory_id, content, scope) in enumerate(
        [
            ("first", "Python tutorial", "coding"),
            ("second", "Python reference", "coding"),
            ("third", "Recipe", "cooking"),
        ]
    ):
        with patch(f"{type(storage).__module__}.datetime", wraps=datetime) as clock:
            clock.now.return_value = datetime(2026, 1, 1, second=sequence, tzinfo=UTC)
            assert storage.store_memory(memory_id, content, {"id": memory_id}, scope)
    assert storage.list_memories() == ["third", "second", "first"]
    assert storage.list_memories("coding", 1) == ["second"]
    assert storage.search_memories("PYTHON") == ["second", "first"]
    assert storage.search_memories("python", "coding", 1) == ["second"]
    assert storage.search_memories("Python", "cooking") == []
    assert storage.search_memories("missing") == []
    assert storage.get_audit_log("first", 1)[0]["memory_id"] == "first"
    assert len(storage.get_audit_log(limit=2)) == 2
    assert storage.delete_memory("second")
    assert storage.list_memories("coding") == ["first"]
    assert storage.delete_memory("first")
    assert storage.get_stats()["total_scopes"] == 1
    assert storage.get_audit_log("first")[0]["action"] == "delete"
    assert (
        datetime.fromisoformat(storage.get_audit_log("first")[0]["timestamp"]).utcoffset()
        is not None
    )


@pytest.mark.parametrize("backend", [AsyncMemoryStorage, AsyncFileStorage, AsyncSQLiteStorage])
async def test_async_storage_lifecycle(backend: type, tmp_path: Path) -> None:
    storage = backend() if backend is AsyncMemoryStorage else backend(str(tmp_path / "data"))
    assert await storage.retrieve_memory("missing") is None
    assert await storage.delete_memory("missing") is False
    assert await storage.store_memory("one", "Python", {"kind": "test"}, "old")
    assert await storage.store_memory("one", "Python updated", scope="new")
    assert await storage.list_memories("old") == []
    assert await storage.list_memories("new", 1) == ["one"]
    assert await storage.search_memories("python", "new", 1) == ["one"]
    assert (await storage.retrieve_memory("one"))["content"] == "Python updated"
    assert (await storage.get_audit_log("one", 1))[0]["action"] == "store"
    assert (await storage.get_stats())["total_memories"] == 1
    assert await storage.delete_memory("one")
    assert (await storage.get_stats())["total_memories"] == 0


@pytest.mark.parametrize("backend", ["file", "sqlite"])
def test_persistent_storage_reopens(backend: str, tmp_path: Path) -> None:
    factory = FileStorage if backend == "file" else SQLiteStorage
    path = str(tmp_path / "data")
    assert factory(path).store_memory("one", "persistent", {"label": "saved"}, "scope")
    reopened = factory(path)
    assert reopened.retrieve_memory("one")["metadata"] == {"label": "saved"}
    assert reopened.list_memories("scope") == ["one"]
    assert reopened.get_audit_log("one")[0]["action"] == "store"


def test_sqlite_errors_are_contained(tmp_path: Path) -> None:
    storage = SQLiteStorage(str(tmp_path / "data.db"))
    with patch(
        "nexamem.storage.sqlite.sqlite3.connect",
        side_effect=sqlite3.OperationalError("unavailable"),
    ):
        assert storage.store_memory("one", "content") is False
        assert storage.retrieve_memory("one") is None
        assert storage.delete_memory("one") is False
        assert storage.list_memories() == []
        assert storage.search_memories("content") == []
        assert storage.get_audit_log() == []
        assert storage.get_stats()["total_memories"] == 0


def test_sqlite_closes_connections(tmp_path: Path) -> None:
    connections = []
    connect = sqlite3.connect

    def tracked_connect(*args: object, **kwargs: object) -> sqlite3.Connection:
        connection = connect(*args, **kwargs)
        connections.append(connection)
        return connection

    with patch("nexamem.storage.sqlite.sqlite3.connect", side_effect=tracked_connect):
        storage = SQLiteStorage(str(tmp_path / "data.db"))
        assert storage.store_memory("one", "content")
        assert storage.retrieve_memory("one") is not None
        storage.list_memories()
        storage.search_memories("content")
        storage.get_stats()
        storage.get_audit_log()
        assert storage.delete_memory("one")
    for connection in connections:
        with pytest.raises(sqlite3.ProgrammingError, match="closed"):
            connection.execute("SELECT 1")


def test_file_corruption_and_io_errors(tmp_path: Path) -> None:
    storage = FileStorage(str(tmp_path / "files"))
    with patch.object(Path, "open", side_effect=OSError("unavailable")):
        assert storage.retrieve_memory("missing") is None
    storage._get_memory_file("bad").write_text("not json", encoding="utf-8")
    assert storage.retrieve_memory("bad") is None
    assert storage.search_memories("anything") == []
    assert storage.delete_memory("bad")
    storage.audit_file.write_text(
        '\ninvalid\n{"memory_id":"one","timestamp":"now"}\n', encoding="utf-8"
    )
    assert len(storage.get_audit_log("one")) == 1
    assert storage.get_audit_log("other") == []
    with patch("builtins.open", side_effect=OSError("unavailable")):
        assert storage.get_audit_log() == []
        assert storage.get_stats()["audit_entries"] == 0
        storage._append_audit_entry({"action": "test"})
    with patch.object(Path, "replace", side_effect=OSError("unavailable")):
        assert storage.store_memory("failed", "content") is False
    assert list(storage.memories_dir.iterdir()) == []


def test_facade_channel_environment_isolation() -> None:
    from nexamem import AIMemory, AIMemoryConfig, MemoryScope, StorageConfig

    memory = AIMemory(AIMemoryConfig(default_scope="test", storage=StorageConfig.memory()))
    memory.register_channel("working", ttl_sec=120)
    development = MemoryScope(agent_id="agent", user_id="user", session_id="session", env="dev")
    production = development.model_copy(update={"env": "prod"})
    memory.write(development, "working", b"development")
    memory.write(production, "working", "production")
    assert memory.read(development, "working")[0] == ["development"]
    assert memory.read(production, "working")[0] == ["production"]


async def test_async_facade_channel_environment_isolation() -> None:
    from nexamem import AIMemoryConfig, AsyncAIMemory, MemoryScope, StorageConfig

    memory = AsyncAIMemory(AIMemoryConfig(default_scope="test", storage=StorageConfig.memory()))
    memory.register_channel("working", ttl_sec=120)
    development = MemoryScope(agent_id="agent", user_id="user", session_id="session", env="dev")
    production = development.model_copy(update={"env": "prod"})
    await memory.write(development, "working", b"development")
    await memory.write(production, "working", "production")
    assert (await memory.read(development, "working"))[0] == ["development"]
    assert (await memory.read(production, "working"))[0] == ["production"]
