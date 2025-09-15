"""
Tests for Azure Redis storage implementation.
Tests both sync and async variants with comprehensive coverage.
"""

import asyncio
import json
import pytest
import time
import uuid
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from nexamem.config.storage import AzureRedisConfig, AzureAuthMethod
from nexamem.memory_scope import MemoryScope
from nexamem.storage.azure_redis import (
    AzureRedisStorage,
    AsyncAzureRedisStorage,
    AzureRedisConnectionError,
    AzureRedisCollections
)


@pytest.fixture
def azure_redis_config():
    """Basic Azure Redis configuration for testing."""
    return AzureRedisConfig(
        hostname="test-cache.redis.cache.windows.net",
        access_key="test-access-key",
        auth_method=AzureAuthMethod.ACCESS_KEY,
        use_collections=True,
        collection_prefix="test_nexamem"
    )


@pytest.fixture
def memory_scope():
    """Test memory scope."""
    return MemoryScope(
        agent_id="test_agent",
        user_id="test_user",
        session_id="test_session",
        env="test"
    )


@pytest.fixture
def mock_redis_client():
    """Mock Redis client for testing."""
    mock_client = Mock()
    mock_client.ping.return_value = True
    mock_client.hset.return_value = 1
    mock_client.hget.return_value = None
    mock_client.hlen.return_value = 0
    mock_client.hkeys.return_value = []
    mock_client.hdel.return_value = 0
    mock_client.sadd.return_value = 1
    mock_client.srem.return_value = 1
    mock_client.smembers.return_value = set()
    mock_client.xadd.return_value = b"test-id"
    mock_client.xread.return_value = []
    mock_client.xinfo_stream.return_value = {"length": 0}
    mock_client.keys.return_value = []
    mock_client.delete.return_value = 0
    mock_client.pipeline.return_value = mock_client
    mock_client.execute.return_value = [True, True, True]
    mock_client.expire.return_value = True
    mock_client.zadd.return_value = 1
    mock_client.zrevrangebyscore.return_value = []
    mock_client.hmget.return_value = []
    mock_client.zrem.return_value = 1
    mock_client.setex.return_value = True
    mock_client.get.return_value = None
    mock_client.zrange.return_value = []
    mock_client.set.return_value = True
    mock_client.close.return_value = None
    return mock_client


@pytest.fixture
def mock_async_redis_client():
    """Mock async Redis client for testing."""
    mock_client = AsyncMock()
    mock_client.ping.return_value = True
    mock_client.hset.return_value = 1
    mock_client.hget.return_value = None
    mock_client.hlen.return_value = 0
    mock_client.hkeys.return_value = []
    mock_client.hdel.return_value = 0
    mock_client.sadd.return_value = 1
    mock_client.srem.return_value = 1
    mock_client.smembers.return_value = set()
    mock_client.xadd.return_value = b"test-id"
    mock_client.xread.return_value = []
    mock_client.xinfo_stream.return_value = {"length": 0}
    mock_client.keys.return_value = []
    mock_client.delete.return_value = 0
    mock_client.pipeline.return_value = mock_client
    mock_client.execute.return_value = [True, True, True]
    mock_client.expire.return_value = True
    mock_client.zadd.return_value = 1
    mock_client.zrevrangebyscore.return_value = []
    mock_client.hmget.return_value = []
    mock_client.zrem.return_value = 1
    mock_client.setex.return_value = True
    mock_client.get.return_value = None
    mock_client.zrange.return_value = []
    mock_client.set.return_value = True
    
    # Mock context manager for pipeline
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    
    return mock_client


class TestAzureRedisConfig:
    """Test Azure Redis configuration."""

    def test_valid_config(self):
        """Test valid configuration creation."""
        config = AzureRedisConfig(
            hostname="test.redis.cache.windows.net",
            access_key="test-key"
        )
        assert config.hostname == "test.redis.cache.windows.net"
        assert config.access_key == "test-key"
        assert config.port == 6380
        assert config.ssl is True

    def test_invalid_hostname(self):
        """Test invalid hostname validation."""
        with pytest.raises(ValueError, match="Azure Redis hostname must end with"):
            AzureRedisConfig(
                hostname="invalid-hostname.com",
                access_key="test-key"
            )

    def test_from_env_access_key(self):
        """Test configuration from environment variables."""
        with patch.dict('os.environ', {
            'AZURE_REDIS_HOSTNAME': 'env.redis.cache.windows.net',
            'AZURE_REDIS_ACCESS_KEY': 'env-key'
        }):
            config = AzureRedisConfig.from_env()
            assert config.hostname == 'env.redis.cache.windows.net'
            assert config.access_key == 'env-key'
            assert config.auth_method == AzureAuthMethod.ACCESS_KEY

    def test_from_env_missing_hostname(self):
        """Test environment configuration with missing hostname."""
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(ValueError, match="AZURE_REDIS_HOSTNAME environment variable required"):
                AzureRedisConfig.from_env()


class TestAzureRedisStorage:
    """Test synchronous Azure Redis storage."""

    def test_init(self, azure_redis_config):
        """Test storage initialization."""
        storage = AzureRedisStorage(azure_redis_config)
        assert storage.config == azure_redis_config
        assert storage._client is None

    @patch('nexamem.storage.azure_redis.redis')
    def test_connect_success(self, mock_redis, azure_redis_config, mock_redis_client):
        """Test successful connection."""
        mock_redis.Redis.return_value = mock_redis_client
        
        storage = AzureRedisStorage(azure_redis_config)
        storage.connect()
        
        assert storage._client == mock_redis_client
        mock_redis_client.ping.assert_called_once()

    @patch('nexamem.storage.azure_redis.redis')
    def test_connect_failure(self, mock_redis, azure_redis_config):
        """Test connection failure."""
        mock_redis.Redis.side_effect = Exception("Connection failed")
        
        storage = AzureRedisStorage(azure_redis_config)
        
        with pytest.raises(AzureRedisConnectionError, match="Failed to connect to Azure Redis"):
            storage.connect()

    @patch('nexamem.storage.azure_redis.redis')
    def test_store_memory_success(self, mock_redis, azure_redis_config, mock_redis_client):
        """Test successful memory storage."""
        mock_redis.Redis.return_value = mock_redis_client
        
        storage = AzureRedisStorage(azure_redis_config)
        
        result = storage.store_memory(
            "test-id",
            "Test content",
            {"key": "value"},
            "test-scope"
        )
        
        assert result is True
        mock_redis_client.hset.assert_called()
        mock_redis_client.sadd.assert_called()
        mock_redis_client.xadd.assert_called()

    @patch('nexamem.storage.azure_redis.redis')
    def test_retrieve_memory_success(self, mock_redis, azure_redis_config, mock_redis_client):
        """Test successful memory retrieval."""
        memory_data = {
            'content': 'Test content',
            'metadata': {'key': 'value'},
            'scope': 'test-scope',
            'created_at': time.time(),
            'updated_at': time.time()
        }
        mock_redis_client.hget.return_value = json.dumps(memory_data)
        mock_redis.Redis.return_value = mock_redis_client
        
        storage = AzureRedisStorage(azure_redis_config)
        
        result = storage.retrieve_memory("test-id")
        
        assert result == memory_data
        mock_redis_client.hget.assert_called_with("test_nexamem:memories", "test-id")

    @patch('nexamem.storage.azure_redis.redis')
    def test_retrieve_memory_not_found(self, mock_redis, azure_redis_config, mock_redis_client):
        """Test memory retrieval when not found."""
        mock_redis_client.hget.return_value = None
        mock_redis.Redis.return_value = mock_redis_client
        
        storage = AzureRedisStorage(azure_redis_config)
        
        result = storage.retrieve_memory("nonexistent")
        
        assert result is None

    @patch('nexamem.storage.azure_redis.redis')
    def test_delete_memory_success(self, mock_redis, azure_redis_config, mock_redis_client):
        """Test successful memory deletion."""
        memory_data = {
            'content': 'Test content',
            'scope': 'test-scope',
            'created_at': time.time(),
            'updated_at': time.time()
        }
        mock_redis_client.hget.return_value = json.dumps(memory_data)
        mock_redis_client.hdel.return_value = 1
        mock_redis.Redis.return_value = mock_redis_client
        
        storage = AzureRedisStorage(azure_redis_config)
        
        result = storage.delete_memory("test-id")
        
        assert result is True
        mock_redis_client.hdel.assert_called()
        mock_redis_client.srem.assert_called()
        mock_redis_client.xadd.assert_called()

    @patch('nexamem.storage.azure_redis.redis')
    def test_list_memories_all(self, mock_redis, azure_redis_config, mock_redis_client):
        """Test listing all memories."""
        mock_redis_client.hkeys.return_value = ["id1", "id2", "id3"]
        mock_redis.Redis.return_value = mock_redis_client
        
        storage = AzureRedisStorage(azure_redis_config)
        
        result = storage.list_memories()
        
        assert result == ["id1", "id2", "id3"]
        mock_redis_client.hkeys.assert_called_with("test_nexamem:memories")

    @patch('nexamem.storage.azure_redis.redis')
    def test_list_memories_by_scope(self, mock_redis, azure_redis_config, mock_redis_client):
        """Test listing memories by scope."""
        mock_redis_client.smembers.return_value = {"id1", "id2"}
        mock_redis.Redis.return_value = mock_redis_client
        
        storage = AzureRedisStorage(azure_redis_config)
        
        result = storage.list_memories("test-scope")
        
        assert set(result) == {"id1", "id2"}
        mock_redis_client.smembers.assert_called_with("test_nexamem:scope:test-scope")

    @patch('nexamem.storage.azure_redis.redis')
    def test_search_memories(self, mock_redis, azure_redis_config, mock_redis_client):
        """Test searching memories."""
        mock_redis_client.hkeys.return_value = ["id1", "id2"]
        
        # Mock retrieve_memory to return different content
        def mock_retrieve(memory_id):
            if memory_id == "id1":
                return {"content": "Python programming"}
            elif memory_id == "id2":
                return {"content": "Java development"}
            return None
        
        mock_redis.Redis.return_value = mock_redis_client
        
        storage = AzureRedisStorage(azure_redis_config)
        storage.retrieve_memory = Mock(side_effect=mock_retrieve)
        
        result = storage.search_memories("python")
        
        assert result == ["id1"]

    @patch('nexamem.storage.azure_redis.redis')
    def test_get_stats(self, mock_redis, azure_redis_config, mock_redis_client):
        """Test getting storage statistics."""
        mock_redis_client.hlen.return_value = 5
        mock_redis_client.keys.return_value = ["scope1", "scope2"]
        mock_redis_client.xinfo_stream.return_value = {"length": 10}
        mock_redis.Redis.return_value = mock_redis_client
        
        storage = AzureRedisStorage(azure_redis_config)
        
        stats = storage.get_stats()
        
        assert stats["total_memories"] == 5
        assert stats["total_scopes"] == 2
        assert stats["audit_entries"] == 10
        assert stats["storage_type"] == "azure_redis"

    @patch('nexamem.storage.azure_redis.redis')
    def test_ping_success(self, mock_redis, azure_redis_config, mock_redis_client):
        """Test successful ping."""
        mock_redis_client.ping.return_value = True
        mock_redis.Redis.return_value = mock_redis_client
        
        storage = AzureRedisStorage(azure_redis_config)
        
        result = storage.ping()
        
        assert result is True

    @patch('nexamem.storage.azure_redis.redis')
    def test_ping_failure(self, mock_redis, azure_redis_config, mock_redis_client):
        """Test ping failure."""
        mock_redis_client.ping.side_effect = Exception("Connection failed")
        mock_redis.Redis.return_value = mock_redis_client
        
        storage = AzureRedisStorage(azure_redis_config)
        
        result = storage.ping()
        
        assert result is False

    def test_auth_access_key(self, azure_redis_config):
        """Test access key authentication."""
        storage = AzureRedisStorage(azure_redis_config)
        
        token = storage._get_auth_token()
        
        assert token == "test-access-key"

    def test_auth_missing_access_key(self):
        """Test access key authentication with missing key."""
        config = AzureRedisConfig(
            hostname="test.redis.cache.windows.net",
            auth_method=AzureAuthMethod.ACCESS_KEY
        )
        storage = AzureRedisStorage(config)
        
        with pytest.raises(AzureRedisConnectionError, match="Access key required"):
            storage._get_auth_token()

    @patch('nexamem.storage.azure_redis.DefaultAzureCredential')
    def test_auth_entra_id(self, mock_credential):
        """Test Entra ID authentication."""
        mock_token = Mock()
        mock_token.token = "entra-token"
        mock_cred_instance = Mock()
        mock_cred_instance.get_token.return_value = mock_token
        mock_credential.return_value = mock_cred_instance
        
        config = AzureRedisConfig(
            hostname="test.redis.cache.windows.net",
            auth_method=AzureAuthMethod.ENTRA_ID,
            use_entra_id=True
        )
        storage = AzureRedisStorage(config)
        
        token = storage._get_auth_token()
        
        assert token == "entra-token"
        mock_cred_instance.get_token.assert_called_with("https://redis.azure.com/.default")


class TestAsyncAzureRedisStorage:
    """Test asynchronous Azure Redis storage."""

    def test_init(self, azure_redis_config):
        """Test async storage initialization."""
        storage = AsyncAzureRedisStorage(azure_redis_config)
        assert storage.config == azure_redis_config
        assert storage._client is None

    @patch('nexamem.storage.azure_redis.redis_async')
    @pytest.mark.asyncio
    async def test_connect_success(self, mock_redis_async, azure_redis_config, mock_async_redis_client):
        """Test successful async connection."""
        mock_redis_async.Redis.return_value = mock_async_redis_client
        
        storage = AsyncAzureRedisStorage(azure_redis_config)
        await storage.connect()
        
        assert storage._client == mock_async_redis_client
        mock_async_redis_client.ping.assert_called_once()

    @patch('nexamem.storage.azure_redis.redis_async')
    @pytest.mark.asyncio
    async def test_store_memory_success(self, mock_redis_async, azure_redis_config, mock_async_redis_client):
        """Test successful async memory storage."""
        mock_redis_async.Redis.return_value = mock_async_redis_client
        
        storage = AsyncAzureRedisStorage(azure_redis_config)
        
        result = await storage.store_memory(
            "test-id",
            "Test content",
            {"key": "value"},
            "test-scope"
        )
        
        assert result is True
        mock_async_redis_client.hset.assert_called()
        mock_async_redis_client.sadd.assert_called()
        mock_async_redis_client.xadd.assert_called()

    @patch('nexamem.storage.azure_redis.redis_async')
    @pytest.mark.asyncio
    async def test_retrieve_memory_success(self, mock_redis_async, azure_redis_config, mock_async_redis_client):
        """Test successful async memory retrieval."""
        memory_data = {
            'content': 'Test content',
            'metadata': {'key': 'value'},
            'scope': 'test-scope',
            'created_at': time.time(),
            'updated_at': time.time()
        }
        mock_async_redis_client.hget.return_value = json.dumps(memory_data)
        mock_redis_async.Redis.return_value = mock_async_redis_client
        
        storage = AsyncAzureRedisStorage(azure_redis_config)
        
        result = await storage.retrieve_memory("test-id")
        
        assert result == memory_data

    @patch('nexamem.storage.azure_redis.redis_async')
    @pytest.mark.asyncio
    async def test_delete_memory_success(self, mock_redis_async, azure_redis_config, mock_async_redis_client):
        """Test successful async memory deletion."""
        memory_data = {
            'content': 'Test content',
            'scope': 'test-scope'
        }
        mock_async_redis_client.hget.return_value = json.dumps(memory_data)
        mock_async_redis_client.hdel.return_value = 1
        mock_redis_async.Redis.return_value = mock_async_redis_client
        
        storage = AsyncAzureRedisStorage(azure_redis_config)
        
        result = await storage.delete_memory("test-id")
        
        assert result is True

    @patch('nexamem.storage.azure_redis.redis_async')
    @pytest.mark.asyncio
    async def test_list_memories_async(self, mock_redis_async, azure_redis_config, mock_async_redis_client):
        """Test async memory listing."""
        mock_async_redis_client.hkeys.return_value = ["id1", "id2", "id3"]
        mock_redis_async.Redis.return_value = mock_async_redis_client
        
        storage = AsyncAzureRedisStorage(azure_redis_config)
        
        result = await storage.list_memories()
        
        assert result == ["id1", "id2", "id3"]

    @patch('nexamem.storage.azure_redis.redis_async')
    @pytest.mark.asyncio
    async def test_search_memories_async(self, mock_redis_async, azure_redis_config, mock_async_redis_client):
        """Test async memory search."""
        mock_async_redis_client.hkeys.return_value = ["id1", "id2"]
        mock_redis_async.Redis.return_value = mock_async_redis_client
        
        # Mock retrieve_memory to return different content
        async def mock_retrieve(memory_id):
            if memory_id == "id1":
                return {"content": "Python programming"}
            elif memory_id == "id2":
                return {"content": "Java development"}
            return None
        
        storage = AsyncAzureRedisStorage(azure_redis_config)
        storage.retrieve_memory = mock_retrieve
        
        result = await storage.search_memories("python")
        
        assert result == ["id1"]

    @patch('nexamem.storage.azure_redis.AsyncDefaultAzureCredential')
    @pytest.mark.asyncio
    async def test_auth_entra_id_async(self, mock_credential):
        """Test async Entra ID authentication."""
        mock_token = Mock()
        mock_token.token = "async-entra-token"
        mock_cred_instance = AsyncMock()
        mock_cred_instance.get_token.return_value = mock_token
        mock_credential.return_value = mock_cred_instance
        
        config = AzureRedisConfig(
            hostname="test.redis.cache.windows.net",
            auth_method=AzureAuthMethod.ENTRA_ID,
            use_entra_id=True
        )
        storage = AsyncAzureRedisStorage(config)
        
        token = await storage._get_auth_token()
        
        assert token == "async-entra-token"


class TestAzureRedisCollections:
    """Test Azure Redis collections functionality."""

    @patch('nexamem.storage.azure_redis.redis')
    def test_collections_sync_add_message(self, mock_redis, mock_redis_client, memory_scope):
        """Test adding message using collections (sync)."""
        collections = AzureRedisCollections(mock_redis_client, "test")
        
        message_id = collections.add_message_to_channel_sync(
            memory_scope,
            "test_channel",
            {"content": "Test message"},
            3600
        )
        
        assert isinstance(message_id, str)
        mock_redis_client.hset.assert_called()
        mock_redis_client.zadd.assert_called()
        mock_redis_client.expire.assert_called()

    @pytest.mark.asyncio
    async def test_collections_async_add_message(self, mock_async_redis_client, memory_scope):
        """Test adding message using collections (async)."""
        collections = AzureRedisCollections(mock_async_redis_client, "test")
        
        message_id = await collections.add_message_to_channel_async(
            memory_scope,
            "test_channel",
            {"content": "Test message"},
            3600
        )
        
        assert isinstance(message_id, str)
        mock_async_redis_client.hset.assert_called()
        mock_async_redis_client.zadd.assert_called()
        mock_async_redis_client.expire.assert_called()

    def test_collections_sync_get_messages_empty(self, mock_redis_client, memory_scope):
        """Test getting messages when none exist (sync)."""
        mock_redis_client.zrevrangebyscore.return_value = []
        collections = AzureRedisCollections(mock_redis_client, "test")
        
        messages, metadata = collections.get_messages_from_channel_sync(
            memory_scope,
            "test_channel"
        )
        
        assert messages == []
        assert metadata["total_messages"] == 0
        assert metadata["total_bytes"] == 0
        assert metadata["truncated"] is False

    @pytest.mark.asyncio
    async def test_collections_async_get_messages_empty(self, mock_async_redis_client, memory_scope):
        """Test getting messages when none exist (async)."""
        mock_async_redis_client.zrevrangebyscore.return_value = []
        collections = AzureRedisCollections(mock_async_redis_client, "test")
        
        messages, metadata = await collections.get_messages_from_channel_async(
            memory_scope,
            "test_channel"
        )
        
        assert messages == []
        assert metadata["total_messages"] == 0

    def test_collections_sync_get_messages_with_data(self, mock_redis_client, memory_scope):
        """Test getting messages with data (sync)."""
        # Mock sorted set returning UUIDs
        mock_redis_client.zrevrangebyscore.return_value = ["uuid1", "uuid2"]
        
        # Mock hash returning message data
        message_data = [
            json.dumps({"content": "Message 1", "uuid": "uuid1", "timestamp": 1234567890}),
            json.dumps({"content": "Message 2", "uuid": "uuid2", "timestamp": 1234567891})
        ]
        mock_redis_client.hmget.return_value = message_data
        
        collections = AzureRedisCollections(mock_redis_client, "test")
        
        messages, metadata = collections.get_messages_from_channel_sync(
            memory_scope,
            "test_channel"
        )
        
        assert len(messages) == 2
        assert messages[0] == "Message 1"
        assert messages[1] == "Message 2"
        assert metadata["total_messages"] == 2
        assert metadata["total_bytes"] > 0


class TestAzureRedisIntegration:
    """Integration tests for Azure Redis storage."""

    @patch('nexamem.storage.azure_redis.redis')
    def test_full_memory_lifecycle_sync(self, mock_redis, azure_redis_config, mock_redis_client):
        """Test complete memory lifecycle (sync)."""
        # Setup mock responses for a full lifecycle
        mock_redis.Redis.return_value = mock_redis_client
        
        # Mock storage operations
        mock_redis_client.hget.side_effect = [
            None,  # Initial retrieve (not found)
            json.dumps({  # After store, retrieve success
                'content': 'Test content',
                'metadata': {'key': 'value'},
                'scope': 'test-scope',
                'created_at': time.time(),
                'updated_at': time.time()
            }),
            json.dumps({  # For delete operation
                'content': 'Test content',
                'scope': 'test-scope'
            })
        ]
        mock_redis_client.hdel.return_value = 1
        
        storage = AzureRedisStorage(azure_redis_config)
        
        # Memory should not exist initially
        memory = storage.retrieve_memory("test-id")
        assert memory is None
        
        # Store memory
        result = storage.store_memory(
            "test-id",
            "Test content",
            {"key": "value"},
            "test-scope"
        )
        assert result is True
        
        # Retrieve memory
        memory = storage.retrieve_memory("test-id")
        assert memory is not None
        assert memory["content"] == "Test content"
        
        # Delete memory
        result = storage.delete_memory("test-id")
        assert result is True

    @pytest.mark.asyncio
    @patch('nexamem.storage.azure_redis.redis_async')
    async def test_full_memory_lifecycle_async(self, mock_redis_async, azure_redis_config, mock_async_redis_client):
        """Test complete memory lifecycle (async)."""
        mock_redis_async.Redis.return_value = mock_async_redis_client
        
        # Mock storage operations
        mock_async_redis_client.hget.side_effect = [
            None,  # Initial retrieve (not found)
            json.dumps({  # After store, retrieve success
                'content': 'Test content',
                'metadata': {'key': 'value'},
                'scope': 'test-scope',
                'created_at': time.time(),
                'updated_at': time.time()
            }),
            json.dumps({  # For delete operation
                'content': 'Test content',
                'scope': 'test-scope'
            })
        ]
        mock_async_redis_client.hdel.return_value = 1
        
        storage = AsyncAzureRedisStorage(azure_redis_config)
        
        # Memory should not exist initially
        memory = await storage.retrieve_memory("test-id")
        assert memory is None
        
        # Store memory
        result = await storage.store_memory(
            "test-id",
            "Test content",
            {"key": "value"},
            "test-scope"
        )
        assert result is True
        
        # Retrieve memory
        memory = await storage.retrieve_memory("test-id")
        assert memory is not None
        assert memory["content"] == "Test content"
        
        # Delete memory
        result = await storage.delete_memory("test-id")
        assert result is True

    @patch('nexamem.storage.azure_redis.redis')
    def test_error_handling_sync(self, mock_redis, azure_redis_config, mock_redis_client):
        """Test error handling in sync operations."""
        mock_redis.Redis.return_value = mock_redis_client
        mock_redis_client.hset.side_effect = Exception("Redis error")
        
        storage = AzureRedisStorage(azure_redis_config)
        
        # Store should handle exception gracefully
        result = storage.store_memory("test-id", "content")
        assert result is False

    @pytest.mark.asyncio
    @patch('nexamem.storage.azure_redis.redis_async')
    async def test_error_handling_async(self, mock_redis_async, azure_redis_config, mock_async_redis_client):
        """Test error handling in async operations."""
        mock_redis_async.Redis.return_value = mock_async_redis_client
        mock_async_redis_client.hset.side_effect = Exception("Redis error")
        
        storage = AsyncAzureRedisStorage(azure_redis_config)
        
        # Store should handle exception gracefully
        result = await storage.store_memory("test-id", "content")
        assert result is False