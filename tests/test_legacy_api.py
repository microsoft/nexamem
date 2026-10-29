"""Retained legacy public APIs must remain functional for the stability release."""

import sqlite3
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import fakeredis
import pytest

from nexamem import ChatHistory, get_config, initialize
from nexamem.aimemory import AIMemory, AsyncAIMemory, ChannelNotFound
from nexamem.config import ConfigError
from nexamem.content_processor import ContentEnricher, PIIRedactor
from nexamem.memory_scope import MemoryScope
from nexamem.redis_adapter import (
    AsyncRedisAdapter,
    AzureRedisConnectionHelper,
    RedisAdapter,
    RedisConnectionError,
)


@pytest.fixture(autouse=True)
def reset_legacy_config(monkeypatch: pytest.MonkeyPatch) -> None:
    from nexamem.config import legacy_config

    monkeypatch.setattr(legacy_config, "_config", None)


def test_legacy_initialization_is_not_a_noop() -> None:
    initialize({"history_storage": "memory"})
    assert get_config()["history_storage"] == "memory"
    history = ChatHistory()
    history.add_user_message("hello")
    assert history.get_history()[0]["content"] == "hello"


@pytest.mark.parametrize(
    "config",
    [
        {},
        {"history_storage": "unknown"},
        {"history_storage": "file"},
        {"history_storage": "sqlite"},
        {"history_storage": "redis"},
        {"history_storage": "redis", "redis_config": "invalid"},
        {"history_storage": "redis", "redis_config": {"port": 6379}},
        {
            "history_storage": "redis",
            "redis_config": {"azure_hostname": "unit.redis.cache.windows.net"},
        },
    ],
)
def test_invalid_legacy_config_is_rejected(config: dict) -> None:
    with pytest.raises(ConfigError):
        initialize(config)


@pytest.mark.parametrize("storage", ["memory", "file", "sqlite", "redis"])
def test_chat_history_lifecycle(storage: str, tmp_path: Path) -> None:
    initialize(
        {
            "history_storage": storage,
            "debug": True,
            "file_path": str(tmp_path / "history.json"),
            "sqlite_path": str(tmp_path / "history.db"),
            "redis_config": {"host": "unit", "use_fakeredis": True},
        }
    )
    history = ChatHistory()
    history.set_session_context("agent", "user", "session", "test")
    history.add_user_message("question", tokens=2, timestamp="2026-01-01T00:00:00")
    history.add_assistant_message("answer", tokens=3, timestamp="2026-01-01T00:00:01")
    history.add_system_message(
        "system", tokens=1, user_id="override", timestamp="2026-01-01T00:00:02"
    )
    records = history.get_history()
    assert [record["role"] for record in records] == ["user", "assistant", "system"]
    assert records[0]["session_id"] == "session"
    assert records[2]["user_id"] == "override"
    assert history.get_message_at(1)["content"] == "answer"
    with pytest.raises(IndexError):
        history.get_message_at(-1)
    with pytest.raises(IndexError):
        history.get_message_at(99)
    if storage == "sqlite":
        assert history.query_sqlite("tokens >= ?", (2,))[0]["content"] == "question"
        assert len(history.query_sqlite()) == 3
    else:
        with pytest.raises(ConfigError):
            history.query_sqlite()
    if storage == "redis":
        assert len(history.query_redis()) == 3
    else:
        with pytest.raises(ConfigError):
            history.query_redis()
    history.clear()
    assert history.get_history() == []
    if storage == "sqlite":
        history._conn.close()
    if storage == "redis":
        history._redis.client.close()


def test_chat_history_requires_initialization() -> None:
    with pytest.raises(ConfigError, match="initialized"):
        ChatHistory()


@pytest.mark.parametrize("content", ["", "broken json", '[{"missing": "fields"}]'])
def test_chat_history_file_corruption(tmp_path: Path, content: str) -> None:
    path = tmp_path / "history.json"
    path.write_text(content, encoding="utf-8")
    initialize({"history_storage": "file", "file_path": str(path), "debug": True})
    assert ChatHistory().get_history() == []


def test_chat_history_sqlite_migration(tmp_path: Path) -> None:
    path = tmp_path / "old.db"
    connection = sqlite3.connect(path)
    connection.execute(
        "CREATE TABLE chat_history (id INTEGER PRIMARY KEY, role TEXT, content TEXT)"
    )
    connection.execute("INSERT INTO chat_history VALUES (1, 'user', 'old message')")
    connection.commit()
    connection.close()
    initialize({"history_storage": "sqlite", "sqlite_path": str(path), "debug": True})
    history = ChatHistory()
    assert history.get_message_at(0)["content"] == "old message"
    assert history.get_history()[0]["session_id"]
    history._conn.close()


def test_legacy_memory_facade() -> None:
    memory = AIMemory(use_fakeredis=True, enable_content_processing=True)
    scope = MemoryScope(agent_id="agent", user_id="user", session_id="session")
    memory.register_channel("working", ttl_sec=120, encrypt=False)
    assert "working" in memory.list_channels()
    assert memory.get_channel_config("working").ttl_sec == 120
    memory.content_processor.add_processor(PIIRedactor())
    memory.content_processor.add_processor(ContentEnricher())
    memory.write(scope, "working", "person@example.com", auto_pii=True)
    messages, metadata = memory.read(scope, "working", max_tokens=10)
    assert messages == ["[REDACTED_EMAIL]"]
    assert metadata["max_tokens_requested"] == 10
    assert memory.count_bytes(scope, "working") == len(messages[0])
    memory.checkpoint(scope, "state", {"counter": 1})
    assert memory.checkpoint_atomic(
        scope, "state", lambda current: {"counter": current["counter"] + 1}
    ) == {"counter": 2}
    for operation in (memory.read, memory.count_bytes):
        with pytest.raises(ChannelNotFound):
            operation(scope, "missing")
    with pytest.raises(ChannelNotFound):
        memory.write(scope, "missing", "content")
    assert memory.bulk_erase(scope) > 0
    memory.redis.client.close()


async def test_async_legacy_memory_facade() -> None:
    client = fakeredis.FakeAsyncRedis(decode_responses=True)
    with patch("nexamem.redis_adapter.redis_async.Redis", return_value=client):
        memory = AsyncAIMemory()
    scope = MemoryScope(agent_id="agent", user_id="user", session_id="session")
    memory.register_channel("working", ttl_sec=120, encrypt=False)
    assert "working" in memory.list_channels()
    assert memory.get_channel_config("working").ttl_sec == 120
    await memory.write(scope, "working", b"hello")
    assert (await memory.read(scope, "working", max_tokens=10))[0] == ["hello"]
    assert await memory.count_bytes(scope, "working") == 5
    await memory.checkpoint(scope, "state", {"counter": 1})
    assert await memory.checkpoint_atomic(
        scope, "state", lambda current: {"counter": current["counter"] + 1}
    ) == {"counter": 2}
    for operation in (memory.read, memory.count_bytes):
        with pytest.raises(ChannelNotFound):
            await operation(scope, "missing")
    with pytest.raises(ChannelNotFound):
        await memory.write(scope, "missing", "content")
    assert await memory.bulk_erase(scope) > 0
    assert await memory.bulk_erase(scope) == 0
    assert memory.redis.get_info()["async"]
    await memory.close()


def test_legacy_adapter_expired_and_corrupt_messages() -> None:
    adapter = RedisAdapter(use_fakeredis=True)
    scope = MemoryScope(agent_id="agent", user_id="user", session_id="session")
    for action in (adapter.read_messages, adapter.count_bytes):
        for memory_id, content in [("missing", None), ("bad", "invalid"), ("empty", "{}")]:
            adapter.client.zadd(scope.get_index_key("working"), {memory_id: 1})
            if content is not None:
                adapter.client.set(f"{scope.get_key_prefix('working')}:{memory_id}", content)
        result = action(scope, "working")
        assert (
            result == ([], {"total_messages": 0, "total_bytes": 0, "truncated": True})
            if action == adapter.read_messages
            else result == 0
        )
        assert adapter.client.zcard(scope.get_index_key("working")) == 0
    adapter.write_message(scope, "working", b"hello", 120)
    assert adapter.read_messages(scope, "working", since_sec=60, max_bytes=1)[0] == []
    assert adapter.checkpoint_get(scope, "missing") is None
    adapter.client.set("prod:agent:checkpoint:bad", "invalid")
    assert adapter.checkpoint_get(scope, "bad") is None
    assert adapter.bulk_erase(scope) > 0
    assert adapter.bulk_erase(scope) == 0
    with patch.object(adapter.client, "ping", side_effect=RuntimeError("unavailable")):
        assert adapter.ping() is False
    adapter.client.close()


async def test_async_legacy_adapter_expired_and_corrupt_messages() -> None:
    client = fakeredis.FakeAsyncRedis(decode_responses=True)
    with patch("nexamem.redis_adapter.redis_async.Redis", return_value=client):
        adapter = AsyncRedisAdapter()
    scope = MemoryScope(agent_id="agent", user_id="user", session_id="session")
    for action in (adapter.read_messages, adapter.count_bytes):
        for memory_id, content in [("missing", None), ("bad", "invalid"), ("empty", "{}")]:
            await client.zadd(scope.get_index_key("working"), {memory_id: 1})
            if content is not None:
                await client.set(f"{scope.get_key_prefix('working')}:{memory_id}", content)
        result = await action(scope, "working")
        assert result[0] == [] if action == adapter.read_messages else result == 0
        assert await client.zcard(scope.get_index_key("working")) == 0
    await adapter.write_message(scope, "working", "hello", 120)
    assert (await adapter.read_messages(scope, "working", since_sec=60, max_bytes=1))[0] == []
    assert await adapter.checkpoint_get(scope, "missing") is None
    await client.set("prod:agent:checkpoint:bad", "invalid")
    assert await adapter.checkpoint_get(scope, "bad") is None
    assert await adapter.ping()
    with patch.object(client, "ping", new=AsyncMock(side_effect=RuntimeError("unavailable"))):
        assert await adapter.ping() is False
    await adapter.close()


def test_legacy_azure_tls_verification() -> None:
    config = AzureRedisConnectionHelper.get_azure_redis_config("unit", access_key="unit-test-only")
    assert config["ssl_cert_reqs"] == "required"


def test_legacy_redis_constructors_and_authentication() -> None:
    helper = AzureRedisConnectionHelper
    assert helper.create_azure_connection_string("unit", "test").startswith("rediss://")
    assert helper.create_azure_connection_string("unit", "test", ssl=False).startswith("redis://")
    with pytest.raises(ValueError):
        helper.create_azure_connection_string("unit")
    with pytest.raises(ValueError):
        helper.get_azure_redis_config("unit")
    credential = Mock()
    credential.get_token.return_value.token = "unit-test-token"
    secret_client = Mock()
    secret_client.get_secret.return_value.value = "unit-test-key"
    with (
        patch("nexamem.redis_adapter.DefaultAzureCredential", return_value=credential),
        patch("nexamem.redis_adapter.ClientSecretCredential", return_value=credential),
        patch("nexamem.redis_adapter.SecretClient", return_value=secret_client),
    ):
        assert (
            helper.get_azure_redis_config("unit", use_entra_id=True)["password"]
            == "unit-test-token"
        )
        assert (
            helper.get_azure_redis_config(
                "unit",
                use_entra_id=True,
                client_id="client",
                client_secret="fake",
                tenant_id="tenant",
            )["username"]
            == "client"
        )
        assert (
            helper.get_azure_redis_config(
                "unit", keyvault_url="https://unit.vault.azure.net", secret_name="test"
            )["password"]
            == "unit-test-key"
        )
    for module_name, options in [
        ("DefaultAzureCredential", {"use_entra_id": True}),
        ("SecretClient", {"keyvault_url": "unit", "secret_name": "test"}),
    ]:
        with patch(f"nexamem.redis_adapter.{module_name}", None):
            with pytest.raises(ImportError):
                helper.get_azure_redis_config("unit", **options)
    client = fakeredis.FakeRedis(decode_responses=True)
    with patch("nexamem.redis_adapter.redis.Redis", return_value=client):
        assert RedisAdapter().get_info()["host"] == "localhost"
        assert RedisAdapter(azure_hostname="unit", azure_access_key="test").get_info()["is_azure"]
    with patch("nexamem.redis_adapter.redis", None):
        with pytest.raises(ImportError):
            RedisAdapter()
    with patch("nexamem.redis_adapter.fakeredis", None):
        with pytest.raises(ImportError):
            RedisAdapter(use_fakeredis=True)
    with patch("nexamem.redis_adapter.redis_async", None):
        with pytest.raises(ImportError):
            AsyncRedisAdapter()
    with patch("nexamem.redis_adapter.redis.Redis") as factory:
        factory.return_value.ping.side_effect = RuntimeError("unavailable")
        with pytest.raises(RedisConnectionError):
            RedisAdapter()
    client.close()
