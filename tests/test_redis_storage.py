"""Redis storage unit tests using fakeredis and mocked identity services."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import fakeredis
import pytest

from nexamem.config.storage import AzureAuthMethod, AzureRedisConfig
from nexamem.memory_scope import MemoryScope
from nexamem.storage.azure_redis import (
    AsyncAzureRedisStorage,
    AzureRedisConnectionError,
    AzureRedisStorage,
)


def test_explicit_redis_auth_configuration() -> None:
    config = AzureRedisConfig(
        hostname="unit.redis.cache.windows.net",
        auth_method=AzureAuthMethod.ACCESS_KEY,
        access_key="unit-test-only",
    )
    assert config.access_key == "unit-test-only"


def test_redis_connect_verifies_tls() -> None:
    config = AzureRedisConfig(hostname="unit.redis.cache.windows.net", access_key="unit-test-only")
    client = fakeredis.FakeRedis(decode_responses=True)
    with patch("nexamem.storage.azure_redis.redis.Redis", return_value=client) as factory:
        storage = AzureRedisStorage(config)
        storage.connect()
        assert factory.call_args.kwargs.get("ssl_cert_reqs", "required") == "required"
    client.close()


def test_redis_memory_lifecycle() -> None:
    config = AzureRedisConfig(hostname="unit.redis.cache.windows.net", access_key="unit-test-only")
    client = fakeredis.FakeRedis(decode_responses=True)
    with patch("nexamem.storage.azure_redis.redis.Redis", return_value=client):
        storage = AzureRedisStorage(config)
        assert storage.ping()
        assert storage.get_stats()["total_memories"] == 0
        assert storage.retrieve_memory("missing") is None
        assert storage.delete_memory("missing") is False
        assert storage.store_memory("one", "Python", {"kind": "test"}, "old")
        original = storage.retrieve_memory("one")
        assert original["metadata"] == {"kind": "test"}
        assert storage.store_memory("one", "Python updated", scope="new")
        assert storage.list_memories("old") == []
        assert storage.retrieve_memory("one")["created_at"] == original["created_at"]
        assert storage.list_memories("new", 1) == ["one"]
        assert storage.search_memories("PYTHON", "new", 1) == ["one"]
        assert storage.search_memories("python", limit=1) == ["one"]
        assert storage.get_audit_log("one")[0]["memory_id"] == "one"
        assert storage.get_audit_log("missing") == []
        assert storage.get_stats()["total_scopes"] == 1
        assert storage.delete_memory("one")
        assert storage.list_memories() == []
        assert storage.store_memory("unscoped", "content")
    client.close()


async def test_async_redis_memory_lifecycle() -> None:
    config = AzureRedisConfig(hostname="unit.redis.cache.windows.net", access_key="unit-test-only")
    client = fakeredis.FakeAsyncRedis(decode_responses=True)
    with patch("nexamem.storage.azure_redis.redis_async.Redis", return_value=client) as factory:
        storage = AsyncAzureRedisStorage(config)
        assert await storage.ping()
        assert factory.call_args.kwargs["ssl_cert_reqs"] == "required"
        assert (await storage.get_stats())["total_memories"] == 0
        assert await storage.retrieve_memory("missing") is None
        assert await storage.delete_memory("missing") is False
        assert await storage.store_memory("one", "Python", {"kind": "test"}, "old")
        original = await storage.retrieve_memory("one")
        assert await storage.store_memory("one", "Python updated", scope="new")
        assert await storage.list_memories("old") == []
        assert (await storage.retrieve_memory("one"))["created_at"] == original["created_at"]
        assert await storage.list_memories("new", 1) == ["one"]
        assert await storage.search_memories("PYTHON", "new", 1) == ["one"]
        assert await storage.search_memories("python", limit=1) == ["one"]
        assert (await storage.get_audit_log("one"))[0]["memory_id"] == "one"
        assert await storage.get_audit_log("missing") == []
        assert (await storage.get_stats())["total_scopes"] == 1
        assert await storage.delete_memory("one")
        assert await storage.list_memories() == []
        assert await storage.store_memory("unscoped", "content")
    await client.aclose()


@pytest.mark.parametrize("layout", ["resp2", "resp3", "resp3_nested"])
@pytest.mark.parametrize("decoded", [False, True])
async def test_audit_stream_response_shapes(layout: str, decoded: bool) -> None:
    config = AzureRedisConfig(hostname="unit.redis.cache.windows.net", access_key="unit-test-only")
    fields = {"memory_id": "one", "action": "store"}
    stream_id = "1-0"
    if not decoded:
        fields = {key.encode(): value.encode() for key, value in fields.items()}
        stream_id = stream_id.encode()
    messages = [(stream_id, fields), ("2-0", None), (None, fields)]
    if layout == "resp2":
        response = [["audit", messages]]
    elif layout == "resp3":
        response = {"audit": messages}
    else:
        response = {"audit": [messages]}

    expected = [{"memory_id": "one", "action": "store", "id": "1-0"}]
    storage = AzureRedisStorage(config)
    storage._client = Mock(xread=Mock(return_value=response))
    assert storage.get_audit_log("one") == expected
    assert storage.get_audit_log("missing") == []

    async_storage = AsyncAzureRedisStorage(config)
    async_storage._client = Mock(xread=AsyncMock(return_value=response))
    assert await async_storage.get_audit_log("one") == expected
    assert await async_storage.get_audit_log("missing") == []


@pytest.mark.parametrize("storage_type", [AzureRedisStorage, AsyncAzureRedisStorage])
def test_unconnected_redis_access(storage_type: type) -> None:
    config = AzureRedisConfig(hostname="unit.redis.cache.windows.net", access_key="unit-test-only")
    storage = storage_type(config)
    storage._client = None
    storage._collections = None
    with pytest.raises(AzureRedisConnectionError, match="connection"):
        assert storage._client is not None
    with pytest.raises(AzureRedisConnectionError, match="collections"):
        assert storage._collections is not None


async def test_keyvault_missing_configuration_and_value() -> None:
    config = AzureRedisConfig(
        hostname="unit.redis.cache.windows.net",
        auth_method=AzureAuthMethod.KEYVAULT,
        keyvault_url="https://unit.vault.azure.net",
        secret_name="redis-key",
    )
    for missing_config in (False, True):
        current = config.model_copy(update={"secret_name": None}) if missing_config else config
        storage = AzureRedisStorage(current)
        client = Mock(get_secret=Mock(return_value=SimpleNamespace(value=None)))
        with (
            patch("nexamem.storage.azure_redis.DefaultAzureCredential"),
            patch("nexamem.storage.azure_redis.SecretClient", return_value=client),
            pytest.raises(AzureRedisConnectionError),
        ):
            storage._get_auth_token()

        async_storage = AsyncAzureRedisStorage(current)
        async_client = Mock(get_secret=AsyncMock(return_value=SimpleNamespace(value=None)))
        with (
            patch("nexamem.storage.azure_redis.AsyncDefaultAzureCredential"),
            patch("nexamem.storage.azure_redis.AsyncSecretClient", return_value=async_client),
            pytest.raises(AzureRedisConnectionError),
        ):
            await async_storage._get_auth_token()


@pytest.mark.parametrize("collections", [True, False])
def test_redis_message_operations(collections: bool) -> None:
    config = AzureRedisConfig(
        hostname="unit.redis.cache.windows.net",
        access_key="unit-test-only",
        use_collections=collections,
    )
    client = fakeredis.FakeRedis(decode_responses=True)
    scope = MemoryScope(agent_id="agent", user_id="user", session_id="session", env="test")
    other_scope = scope.model_copy(update={"user_id": "other"})
    with patch("nexamem.storage.azure_redis.redis.Redis", return_value=client):
        storage = AzureRedisStorage(config)
        assert storage.read_messages(scope, "working")[0] == []
        assert storage.count_bytes(scope, "working") == 0
        storage.write_message(scope, "working", b"hello", 120, {"label": "test"})
        storage.write_message(scope, "working", "world", 120)
        storage.write_message(other_scope, "working", "private", 120)
        messages, metadata = storage.read_messages(scope, "working", since_sec=60)
        assert sorted(messages) == ["hello", "world"]
        assert metadata["total_bytes"] == 10
        assert storage.count_bytes(scope, "working") == 10
        assert len(storage.read_messages(scope, "working", max_msgs=1)[0]) == 1
        assert len(storage.read_messages(scope, "working", max_bytes=5)[0]) == 1
        assert storage.checkpoint_get(scope, "checkpoint") is None
        storage.checkpoint_set(scope, "checkpoint", {"state": "saved"})
        assert storage.checkpoint_get(scope, "checkpoint") == {"state": "saved"}
        client.set("test:agent:checkpoint:checkpoint", "invalid")
        assert storage.checkpoint_get(scope, "checkpoint") is None
        assert storage.bulk_erase(scope) > 0
        assert storage.count_bytes(scope, "working") == 0
        assert storage.read_messages(scope, "working")[0] == []
        assert storage.read_messages(other_scope, "working")[0] == ["private"]
        assert storage.bulk_erase(scope) == 0
        storage.close()


@pytest.mark.parametrize("collections", [True, False])
async def test_async_redis_message_operations(collections: bool) -> None:
    config = AzureRedisConfig(
        hostname="unit.redis.cache.windows.net",
        access_key="unit-test-only",
        use_collections=collections,
    )
    client = fakeredis.FakeAsyncRedis(decode_responses=True)
    scope = MemoryScope(agent_id="agent", user_id="user", session_id="session", env="test")
    other_scope = scope.model_copy(update={"user_id": "other"})
    with patch("nexamem.storage.azure_redis.redis_async.Redis", return_value=client):
        storage = AsyncAzureRedisStorage(config)
        assert (await storage.read_messages(scope, "working"))[0] == []
        assert await storage.count_bytes(scope, "working") == 0
        await storage.write_message(scope, "working", b"hello", 120, {"label": "test"})
        await storage.write_message(scope, "working", "world", 120)
        await storage.write_message(other_scope, "working", "private", 120)
        messages, metadata = await storage.read_messages(scope, "working", since_sec=60)
        assert sorted(messages) == ["hello", "world"]
        assert metadata["total_bytes"] == 10
        assert await storage.count_bytes(scope, "working") == 10
        assert len((await storage.read_messages(scope, "working", max_msgs=1))[0]) == 1
        assert len((await storage.read_messages(scope, "working", max_bytes=5))[0]) == 1
        assert await storage.checkpoint_get(scope, "checkpoint") is None
        await storage.checkpoint_set(scope, "checkpoint", {"state": "saved"})
        assert await storage.checkpoint_get(scope, "checkpoint") == {"state": "saved"}
        await client.set("test:agent:checkpoint:checkpoint", "invalid")
        assert await storage.checkpoint_get(scope, "checkpoint") is None
        assert await storage.bulk_erase(scope) > 0
        assert await storage.count_bytes(scope, "working") == 0
        assert (await storage.read_messages(scope, "working"))[0] == []
        assert (await storage.read_messages(other_scope, "working"))[0] == ["private"]
        assert await storage.bulk_erase(scope) == 0
    await client.aclose()
