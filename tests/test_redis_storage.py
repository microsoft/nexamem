"""Redis storage unit tests using fakeredis and mocked identity services."""

import asyncio
import base64
import json
import time
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
from nexamem.storage.entra import RedisEntraCredentials


def test_explicit_redis_auth_configuration() -> None:
    config = AzureRedisConfig(
        hostname="unit.redis.cache.windows.net",
        auth_method=AzureAuthMethod.ACCESS_KEY,
        access_key="unit-test-only",
    )
    assert config.access_key == "unit-test-only"


@pytest.mark.parametrize(
    "hostname,port",
    [
        ("unit.redis.cache.windows.net", 6380),
        ("unit.eastus.redis.azure.net", 10000),
    ],
)
def test_azure_endpoint_defaults(hostname, port):
    assert AzureRedisConfig(hostname=hostname, access_key="test").port == port
    assert AzureRedisConfig(hostname=hostname, access_key="test", port=12345).port == 12345
    with pytest.raises(ValueError, match="TLS"):
        AzureRedisConfig(hostname=hostname, access_key="test", ssl=False)


def test_redis_connect_verifies_tls() -> None:
    config = AzureRedisConfig(hostname="unit.redis.cache.windows.net", access_key="unit-test-only")
    client = fakeredis.FakeRedis(decode_responses=True)
    with patch("nexamem.storage.azure_redis.redis.Redis", return_value=client) as factory:
        storage = AzureRedisStorage(config)
        storage.connect()
        assert factory.call_args.kwargs.get("ssl_cert_reqs", "required") == "required"
    client.close()


async def test_entra_streaming_connection_ownership() -> None:
    config = AzureRedisConfig(
        hostname="unit.eastus.redis.azure.net",
        auth_method="entra_id",
        use_entra_id=True,
        client_id="managed-identity-client-id",
    )
    for asynchronous in (False, True):
        module = "redis_async" if asynchronous else "redis"
        client = Mock(ping=AsyncMock() if asynchronous else Mock(), aclose=AsyncMock())
        credentials = Mock()
        with (
            patch(f"nexamem.storage.azure_redis.{module}.Redis", return_value=client) as factory,
            patch("nexamem.storage.azure_redis.RedisEntraCredentials", return_value=credentials),
        ):
            if asynchronous:
                storage = AsyncAzureRedisStorage(config)
                await asyncio.gather(storage.connect(), storage.connect())
                await storage.close()
                await storage.close()
            else:
                storage = AzureRedisStorage(config)
                storage.connect()
                storage.connect()
                storage.close()
                storage.close()
            factory.assert_called_once()
            assert factory.call_args.kwargs["credential_provider"] is credentials
            assert "password" not in factory.call_args.kwargs
            assert "username" not in factory.call_args.kwargs
            credentials.close.assert_called_once()
            assert storage._connection is None


def test_entra_object_id_renewal_and_cleanup() -> None:
    def token(value):
        payload = {
            "oid": "object-id",
            "exp": int(time.time()) + 3600,
            "iat": int(time.time()),
            "version": value,
        }
        encoded = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
        return f"eyJhbGciOiJIUzI1NiJ9.{encoded}.c2ln"

    credential = Mock(
        get_token=Mock(
            side_effect=[
                SimpleNamespace(token=token(1)),
                SimpleNamespace(token=token(2)),
                SimpleNamespace(token=token(3)),
                SimpleNamespace(token=token(4)),
            ]
        )
    )
    config = AzureRedisConfig(
        hostname="unit.redis.cache.windows.net", auth_method="entra_id", use_entra_id=True
    )
    with patch("nexamem.storage.entra.DefaultAzureCredential", return_value=credential):
        provider = RedisEntraCredentials(config)
        first = provider._token_mgr.acquire_token().get_token()
        second = provider._token_mgr.acquire_token(True).get_token()
        assert first.try_get("oid") == "object-id"
        assert first.get_value() != second.get_value()
        callback = Mock()
        provider.on_next(callback)
        provider._listener.on_next(second)
        callback.assert_called_once_with(second)
        assert provider.get_credentials()[0] == "object-id"
        thread = provider._token_mgr._thread
        assert thread is not None and thread.is_alive()
        provider.close()
        assert not thread.is_alive()
        assert provider._token_mgr._owned_loop.is_closed()
        credential.close.assert_called_once()
        assert provider._token_mgr._closed


async def test_connection_failure_cleanup_and_retry() -> None:
    config = AzureRedisConfig(
        hostname="unit.redis.cache.windows.net", access_key="test", username="user"
    )
    client = Mock(ping=Mock(side_effect=[RuntimeError("secret-must-not-leak"), True]))
    with patch("nexamem.storage.azure_redis.redis.Redis", return_value=client) as factory:
        storage = AzureRedisStorage(config)
        with pytest.raises(AzureRedisConnectionError) as error:
            storage.connect()
        assert "secret-must-not-leak" not in str(error.value)
        assert storage._connection is None
        client.close.assert_called_once()
        storage.connect()
        assert factory.call_args.kwargs["username"] == "user"
        storage.close()

    client = Mock(ping=AsyncMock(side_effect=[RuntimeError("failed"), True]), aclose=AsyncMock())
    with patch("nexamem.storage.azure_redis.redis_async.Redis", return_value=client):
        storage = AsyncAzureRedisStorage(config)
        with pytest.raises(AzureRedisConnectionError):
            await storage.connect()
        client.aclose.assert_awaited_once()
        assert storage._connection is None
        await storage.connect()
        await storage.close()


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
        async_client = Mock(
            get_secret=AsyncMock(return_value=SimpleNamespace(value=None)), close=AsyncMock()
        )
        with (
            patch(
                "nexamem.storage.azure_redis.AsyncDefaultAzureCredential",
                return_value=Mock(close=AsyncMock()),
            ),
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
