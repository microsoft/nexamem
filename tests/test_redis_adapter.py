"""
Comprehensive unit tests for redis_adapter module.
Tests both sync and async Redis adapters with Azure support.
"""
import json
import time
import uuid
from unittest.mock import AsyncMock, Mock, patch

import pytest

from nexamem.memory_scope import MemoryScope
from nexamem.redis_adapter import (
    AsyncRedisAdapter,
    AzureRedisConnectionHelper,
    RedisAdapter,
    RedisConnectionError,
)


class TestRedisConnectionError:
    """Test RedisConnectionError exception."""
    
    def test_redis_connection_error_creation(self):
        """Test creating RedisConnectionError with message."""
        error = RedisConnectionError("Connection failed")
        assert str(error) == "Connection failed"
        assert isinstance(error, Exception)


class TestAzureRedisConnectionHelper:
    """Test Azure Redis connection helper utilities."""
    
    def test_get_azure_redis_config_with_access_key(self):
        """Test Azure Redis config with access key."""
        config = AzureRedisConnectionHelper.get_azure_redis_config(
            hostname="test.redis.cache.windows.net",
            access_key="test_key"
        )
        
        expected = {
            "host": "test.redis.cache.windows.net",
            "port": 6380,
            "password": "test_key",
            "ssl": True,
            "ssl_cert_reqs": None,
            "ssl_check_hostname": False,
            "socket_connect_timeout": 5,
            "socket_timeout": 5
        }
        
        assert config == expected
    
    @patch('nexamem.redis_adapter.DefaultAzureCredential')
    def test_get_azure_redis_config_with_entra_id(self, mock_credential):
        """Test Azure Redis config with Entra ID authentication."""
        mock_cred = Mock()
        mock_credential.return_value = mock_cred
        
        config = AzureRedisConnectionHelper.get_azure_redis_config(
            hostname="test.redis.cache.windows.net",
            use_entra_id=True,
            username="test_user"
        )
        
        assert config["host"] == "test.redis.cache.windows.net"
        assert config["port"] == 6380
        assert config["ssl"] is True
        assert config["username"] == "test_user"
        assert "password" in config  # Should get token
    
    @patch('nexamem.redis_adapter.ClientSecretCredential')
    def test_get_azure_redis_config_with_service_principal(self, mock_credential):
        """Test Azure Redis config with service principal."""
        mock_cred = Mock()
        mock_credential.return_value = mock_cred
        
        config = AzureRedisConnectionHelper.get_azure_redis_config(
            hostname="test.redis.cache.windows.net",
            use_entra_id=True,
            client_id="test_client",
            client_secret="test_secret",
            tenant_id="test_tenant"
        )
        
        assert config["host"] == "test.redis.cache.windows.net"
        assert config["ssl"] is True
        mock_credential.assert_called_once_with(
            tenant_id="test_tenant",
            client_id="test_client",
            client_secret="test_secret"
        )
    
    @patch('nexamem.redis_adapter.SecretClient')
    def test_get_azure_redis_config_with_keyvault(self, mock_secret_client):
        """Test Azure Redis config with Key Vault."""
        mock_client = Mock()
        mock_secret = Mock()
        mock_secret.value = "secret_access_key"
        mock_client.get_secret.return_value = mock_secret
        mock_secret_client.return_value = mock_client
        
        config = AzureRedisConnectionHelper.get_azure_redis_config(
            hostname="test.redis.cache.windows.net",
            keyvault_url="https://test.vault.azure.net/",
            secret_name="redis-key"
        )
        
        assert config["password"] == "secret_access_key"
        assert config["host"] == "test.redis.cache.windows.net"
    
    def test_get_azure_redis_config_no_auth_raises_error(self):
        """Test that missing authentication raises error."""
        with pytest.raises(ValueError, match="authentication method"):
            AzureRedisConnectionHelper.get_azure_redis_config(
                hostname="test.redis.cache.windows.net"
            )
    
    def test_create_connection_string_access_key(self):
        """Test creating connection string with access key."""
        conn_str = AzureRedisConnectionHelper.create_connection_string(
            hostname="test.redis.cache.windows.net",
            access_key="test_key"
        )
        
        expected = "rediss://test.redis.cache.windows.net:6380?password=test_key&ssl_cert_reqs=none&ssl_check_hostname=false"
        assert conn_str == expected
    
    def test_create_connection_string_no_key_raises_error(self):
        """Test that creating connection string without key raises error."""
        with pytest.raises(ValueError, match="Access key is required"):
            AzureRedisConnectionHelper.create_connection_string(
                hostname="test.redis.cache.windows.net"
            )


class TestRedisAdapter:
    """Test synchronous Redis adapter."""
    
    @pytest.fixture
    def mock_redis(self):
        """Mock Redis client."""
        mock = Mock()
        mock.ping.return_value = True
        mock.set.return_value = True
        mock.get.return_value = None
        mock.zadd.return_value = 1
        mock.zrange.return_value = []
        mock.zrangebyscore.return_value = []
        mock.zrem.return_value = 1
        mock.delete.return_value = 1
        mock.scan_iter.return_value = iter([])
        mock.pipeline.return_value = mock
        mock.execute.return_value = []
        return mock
    
    @pytest.fixture
    def adapter(self, mock_redis):
        """Redis adapter with mocked client."""
        with patch('nexamem.redis_adapter.redis') as mock_redis_module:
            mock_redis_module.Redis.return_value = mock_redis
            adapter = RedisAdapter(use_fakeredis=True)
            adapter.redis = mock_redis
            return adapter
    
    @pytest.fixture
    def sample_scope(self):
        """Sample memory scope for testing."""
        return MemoryScope(
            agent_id="test_agent",
            user_id="user123",
            session_id="session456",
            env="test"
        )
    
    def test_redis_adapter_initialization(self):
        """Test Redis adapter initialization."""
        with patch('nexamem.redis_adapter.redis') as mock_redis_module:
            mock_client = Mock()
            mock_redis_module.Redis.return_value = mock_client
            
            adapter = RedisAdapter(
                host="localhost",
                port=6379,
                db=0,
                use_fakeredis=True
            )
            
            assert adapter.host == "localhost"
            assert adapter.port == 6379
            assert adapter.db == 0
            assert adapter.use_fakeredis is True
    
    def test_redis_adapter_azure_initialization(self):
        """Test Redis adapter initialization with Azure config."""
        azure_config = {
            "host": "test.redis.cache.windows.net",
            "port": 6380,
            "password": "test_key",
            "ssl": True
        }
        
        with patch('nexamem.redis_adapter.redis') as mock_redis_module:
            mock_client = Mock()
            mock_redis_module.Redis.return_value = mock_client
            
            adapter = RedisAdapter(azure_config=azure_config)
            
            assert adapter.host == "test.redis.cache.windows.net"
            assert adapter.port == 6380
            assert adapter.ssl is True
            assert adapter.is_azure is True
    
    def test_write_message(self, adapter, sample_scope, mock_redis):
        """Test writing a message to Redis."""
        # Setup mock responses
        mock_redis.set.return_value = True
        mock_redis.zadd.return_value = 1
        
        message_uuid = adapter.write_message(
            scope=sample_scope,
            channel="working",
            content="Test message",
            ttl_sec=3600
        )
        
        assert isinstance(message_uuid, str)
        assert len(message_uuid) == 36  # UUID length
        
        # Verify Redis calls
        assert mock_redis.set.called
        assert mock_redis.zadd.called
    
    def test_read_messages(self, adapter, sample_scope, mock_redis):
        """Test reading messages from Redis."""
        # Setup mock data
        message_uuid = str(uuid.uuid4())
        message_data = {
            "content": "Test message",
            "timestamp": time.time(),
            "metadata": {"ttl_sec": 3600}
        }
        
        mock_redis.zrangebyscore.return_value = [message_uuid.encode()]
        mock_redis.get.return_value = json.dumps(message_data).encode()
        
        messages, metadata = adapter.read_messages(
            scope=sample_scope,
            channel="working"
        )
        
        assert len(messages) == 1
        assert messages[0] == "Test message"
        assert "total_bytes" in metadata
        assert "retrieved_count" in metadata
    
    def test_read_messages_with_filters(self, adapter, sample_scope, mock_redis):
        """Test reading messages with filters."""
        # Setup mock data
        message_uuid = str(uuid.uuid4())
        current_time = time.time()
        message_data = {
            "content": "Test message",
            "timestamp": current_time,
            "metadata": {"ttl_sec": 3600}
        }
        
        mock_redis.zrangebyscore.return_value = [message_uuid.encode()]
        mock_redis.get.return_value = json.dumps(message_data).encode()
        
        messages, metadata = adapter.read_messages(
            scope=sample_scope,
            channel="working",
            since_sec=60,  # 1 minute ago
            max_msgs=10,
            max_bytes=1000
        )
        
        # Verify zrangebyscore was called with time filter
        args, kwargs = mock_redis.zrangebyscore.call_args
        assert args[1] >= current_time - 60  # Time filter applied
    
    def test_bulk_erase(self, adapter, sample_scope, mock_redis):
        """Test bulk erase operation."""
        # Setup mock scan results
        mock_keys = [
            b"test:test_agent:user123:session456:working:msg1",
            b"test:test_agent:user123:session456:routing:msg2"
        ]
        mock_redis.scan_iter.return_value = iter(mock_keys)
        mock_redis.delete.return_value = 2
        
        deleted_count = adapter.bulk_erase(sample_scope)
        
        assert deleted_count == 2
        mock_redis.scan_iter.assert_called_once()
        mock_redis.delete.assert_called_once()
    
    def test_count_bytes(self, adapter, sample_scope, mock_redis):
        """Test counting bytes in a channel."""
        # Setup mock data
        message_uuid = str(uuid.uuid4())
        message_data = {
            "content": "Test message",
            "timestamp": time.time(),
            "metadata": {"ttl_sec": 3600}
        }
        
        mock_redis.zrange.return_value = [message_uuid.encode()]
        mock_redis.get.return_value = json.dumps(message_data).encode()
        
        byte_count = adapter.count_bytes(sample_scope, "working")
        
        assert byte_count > 0
        mock_redis.zrange.assert_called_once()
    
    def test_checkpoint_operations(self, adapter, sample_scope, mock_redis):
        """Test checkpoint set and get operations."""
        test_data = {"step": 1, "status": "active"}
        
        # Test checkpoint set
        mock_redis.set.return_value = True
        adapter.checkpoint_set(sample_scope, "workflow", test_data)
        mock_redis.set.assert_called()
        
        # Test checkpoint get
        mock_redis.get.return_value = json.dumps(test_data).encode()
        result = adapter.checkpoint_get(sample_scope, "workflow")
        
        assert result == test_data
    
    def test_checkpoint_get_nonexistent(self, adapter, sample_scope, mock_redis):
        """Test getting nonexistent checkpoint."""
        mock_redis.get.return_value = None
        result = adapter.checkpoint_get(sample_scope, "nonexistent")
        assert result is None
    
    def test_checkpoint_get_invalid_json(self, adapter, sample_scope, mock_redis):
        """Test getting checkpoint with invalid JSON."""
        mock_redis.get.return_value = b"invalid json"
        result = adapter.checkpoint_get(sample_scope, "invalid")
        assert result is None
    
    def test_ping(self, adapter, mock_redis):
        """Test Redis ping operation."""
        mock_redis.ping.return_value = True
        assert adapter.ping() is True
        
        mock_redis.ping.side_effect = Exception("Connection failed")
        assert adapter.ping() is False
    
    def test_get_info(self, adapter):
        """Test getting Redis connection info."""
        info = adapter.get_info()
        
        required_keys = ["host", "port", "ssl", "db", "connected", "use_fakeredis", "is_azure"]
        for key in required_keys:
            assert key in info
        
        assert info["host"] == adapter.host
        assert info["port"] == adapter.port
    
    def test_connection_failure(self):
        """Test Redis connection failure handling."""
        with patch('nexamem.redis_adapter.redis') as mock_redis_module:
            mock_redis_module.Redis.side_effect = Exception("Connection failed")
            
            with pytest.raises(RedisConnectionError):
                RedisAdapter(host="nonexistent", port=6379)
    
    def test_write_message_binary_content(self, adapter, sample_scope, mock_redis):
        """Test writing binary content."""
        binary_content = b"Binary data"
        mock_redis.set.return_value = True
        mock_redis.zadd.return_value = 1
        
        message_uuid = adapter.write_message(
            scope=sample_scope,
            channel="working",
            content=binary_content,
            ttl_sec=3600
        )
        
        assert isinstance(message_uuid, str)
        mock_redis.set.assert_called()
    
    def test_redis_adapter_without_redis_library(self):
        """Test adapter behavior when Redis library is not available."""
        with patch('nexamem.redis_adapter.redis', None):
            with pytest.raises(ImportError, match="redis"):
                RedisAdapter()


class TestAsyncRedisAdapter:
    """Test asynchronous Redis adapter."""
    
    @pytest.fixture
    def mock_async_redis(self):
        """Mock async Redis client."""
        mock = AsyncMock()
        mock.ping.return_value = True
        mock.set.return_value = True
        mock.get.return_value = None
        mock.zadd.return_value = 1
        mock.zrange.return_value = []
        mock.zrangebyscore.return_value = []
        mock.zrem.return_value = 1
        mock.delete.return_value = 1
        mock.scan_iter = AsyncMock(return_value=iter([]))
        return mock
    
    @pytest.fixture
    async def async_adapter(self, mock_async_redis):
        """Async Redis adapter with mocked client."""
        with patch('nexamem.redis_adapter.redis_async') as mock_redis_module:
            mock_redis_module.Redis.return_value = mock_async_redis
            adapter = AsyncRedisAdapter(use_fakeredis=True)
            adapter.client = mock_async_redis
            return adapter
    
    @pytest.fixture
    def sample_scope(self):
        """Sample memory scope for testing."""
        return MemoryScope(
            agent_id="test_agent",
            user_id="user123",
            session_id="session456",
            env="test"
        )
    
    @pytest.mark.asyncio
    async def test_async_redis_adapter_initialization(self):
        """Test async Redis adapter initialization."""
        with patch('nexamem.redis_adapter.redis_async') as mock_redis_module:
            mock_client = AsyncMock()
            mock_redis_module.Redis.return_value = mock_client
            
            adapter = AsyncRedisAdapter(
                host="localhost",
                port=6379,
                db=0,
                use_fakeredis=True
            )
            
            assert adapter.host == "localhost"
            assert adapter.port == 6379
            assert adapter.db == 0
            assert adapter.use_fakeredis is True
    
    @pytest.mark.asyncio
    async def test_async_write_message(self, async_adapter, sample_scope, mock_async_redis):
        """Test async writing a message to Redis."""
        mock_async_redis.set.return_value = True
        mock_async_redis.zadd.return_value = 1
        
        message_uuid = await async_adapter.write_message(
            scope=sample_scope,
            channel="working",
            content="Test message",
            ttl_sec=3600
        )
        
        assert isinstance(message_uuid, str)
        assert len(message_uuid) == 36  # UUID length
        
        # Verify async calls
        mock_async_redis.set.assert_called()
        mock_async_redis.zadd.assert_called()
    
    @pytest.mark.asyncio
    async def test_async_read_messages(self, async_adapter, sample_scope, mock_async_redis):
        """Test async reading messages from Redis."""
        # Setup mock data
        message_uuid = str(uuid.uuid4())
        message_data = {
            "content": "Test message",
            "timestamp": time.time(),
            "metadata": {"ttl_sec": 3600}
        }
        
        mock_async_redis.zrangebyscore.return_value = [message_uuid.encode()]
        mock_async_redis.get.return_value = json.dumps(message_data).encode()
        
        messages, metadata = await async_adapter.read_messages(
            scope=sample_scope,
            channel="working"
        )
        
        assert len(messages) == 1
        assert messages[0] == "Test message"
        assert "total_bytes" in metadata
        assert "retrieved_count" in metadata
    
    @pytest.mark.asyncio
    async def test_async_bulk_erase(self, async_adapter, sample_scope, mock_async_redis):
        """Test async bulk erase operation."""
        # Setup mock scan results
        mock_keys = [
            b"test:test_agent:user123:session456:working:msg1",
            b"test:test_agent:user123:session456:routing:msg2"
        ]
        
        async def mock_scan_iter(*args, **kwargs):
            for key in mock_keys:
                yield key
        
        mock_async_redis.scan_iter = mock_scan_iter
        mock_async_redis.delete.return_value = 2
        
        deleted_count = await async_adapter.bulk_erase(sample_scope)
        
        assert deleted_count == 2
        mock_async_redis.delete.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_async_count_bytes(self, async_adapter, sample_scope, mock_async_redis):
        """Test async counting bytes in a channel."""
        # Setup mock data
        message_uuid = str(uuid.uuid4())
        message_data = {
            "content": "Test message",
            "timestamp": time.time(),
            "metadata": {"ttl_sec": 3600}
        }
        
        mock_async_redis.zrange.return_value = [message_uuid.encode()]
        mock_async_redis.get.return_value = json.dumps(message_data).encode()
        
        byte_count = await async_adapter.count_bytes(sample_scope, "working")
        
        assert byte_count > 0
        mock_async_redis.zrange.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_async_checkpoint_operations(self, async_adapter, sample_scope, mock_async_redis):
        """Test async checkpoint operations."""
        test_data = {"step": 1, "status": "active"}
        
        # Test checkpoint set
        mock_async_redis.set.return_value = True
        await async_adapter.checkpoint_set(sample_scope, "workflow", test_data)
        mock_async_redis.set.assert_called()
        
        # Test checkpoint get
        mock_async_redis.get.return_value = json.dumps(test_data).encode()
        result = await async_adapter.checkpoint_get(sample_scope, "workflow")
        
        assert result == test_data
    
    @pytest.mark.asyncio
    async def test_async_ping(self, async_adapter, mock_async_redis):
        """Test async Redis ping operation."""
        mock_async_redis.ping.return_value = True
        assert await async_adapter.ping() is True
        
        mock_async_redis.ping.side_effect = Exception("Connection failed")
        assert await async_adapter.ping() is False
    
    @pytest.mark.asyncio
    async def test_async_close(self, async_adapter, mock_async_redis):
        """Test async close operation."""
        await async_adapter.close()
        mock_async_redis.close.assert_called_once()
    
    def test_async_get_info(self, async_adapter):
        """Test getting async Redis connection info."""
        info = async_adapter.get_info()
        
        required_keys = ["host", "port", "ssl", "db", "async", "is_azure"]
        for key in required_keys:
            assert key in info
        
        assert info["async"] is True
        assert info["host"] == async_adapter.host
    
    @pytest.mark.asyncio
    async def test_async_connection_failure(self):
        """Test async Redis connection failure handling."""
        with patch('nexamem.redis_adapter.redis_async') as mock_redis_module:
            mock_redis_module.Redis.side_effect = Exception("Connection failed")
            
            with pytest.raises(RedisConnectionError):
                AsyncRedisAdapter(host="nonexistent", port=6379)
    
    def test_async_adapter_without_redis_library(self):
        """Test async adapter behavior when Redis library is not available."""
        with patch('nexamem.redis_adapter.redis_async', None):
            with pytest.raises(ImportError, match="redis"):
                AsyncRedisAdapter()


class TestRedisAdapterIntegration:
    """Integration tests for Redis adapter with realistic scenarios."""
    
    @pytest.fixture
    def sample_scope(self):
        """Sample memory scope for testing."""
        return MemoryScope(
            agent_id="chat_bot",
            user_id="user789",
            session_id="session123",
            env="production"
        )
    
    def test_write_read_roundtrip(self, sample_scope):
        """Test complete write-read roundtrip with fakeredis."""
        with patch('nexamem.redis_adapter.fakeredis') as mock_fakeredis:
            mock_redis = Mock()
            mock_fakeredis.FakeRedis.return_value = mock_redis
            
            # Setup mock behavior for write
            mock_redis.set.return_value = True
            mock_redis.zadd.return_value = 1
            
            # Setup mock behavior for read
            message_uuid = str(uuid.uuid4())
            current_time = time.time()
            message_data = {
                "content": "Hello, world!",
                "timestamp": current_time,
                "metadata": {"ttl_sec": 3600}
            }
            
            mock_redis.zrangebyscore.return_value = [message_uuid.encode()]
            mock_redis.get.return_value = json.dumps(message_data).encode()
            
            adapter = RedisAdapter(use_fakeredis=True)
            adapter.redis = mock_redis
            
            # Write message
            adapter.write_message(
                scope=sample_scope,
                channel="working",
                content="Hello, world!",
                ttl_sec=3600
            )
            
            # Read messages
            messages, metadata = adapter.read_messages(
                scope=sample_scope,
                channel="working"
            )
            
            assert len(messages) == 1
            assert messages[0] == "Hello, world!"
            assert "total_bytes" in metadata
    
    def test_multiple_channels(self, sample_scope):
        """Test operations across multiple channels."""
        with patch('nexamem.redis_adapter.fakeredis') as mock_fakeredis:
            mock_redis = Mock()
            mock_fakeredis.FakeRedis.return_value = mock_redis
            
            mock_redis.set.return_value = True
            mock_redis.zadd.return_value = 1
            
            adapter = RedisAdapter(use_fakeredis=True)
            adapter.redis = mock_redis
            
            # Write to multiple channels
            adapter.write_message(sample_scope, "working", "Working message", 3600)
            adapter.write_message(sample_scope, "routing", "Routing message", 3600)
            
            # Verify separate calls for each channel
            assert mock_redis.set.call_count == 2
            assert mock_redis.zadd.call_count == 2
    
    def test_ttl_metadata_preservation(self, sample_scope):
        """Test that TTL metadata is preserved correctly."""
        with patch('nexamem.redis_adapter.fakeredis') as mock_fakeredis:
            mock_redis = Mock()
            mock_fakeredis.FakeRedis.return_value = mock_redis
            
            adapter = RedisAdapter(use_fakeredis=True)
            adapter.redis = mock_redis
            
            mock_redis.set.return_value = True
            mock_redis.zadd.return_value = 1
            
            # Write with custom TTL
            adapter.write_message(
                scope=sample_scope,
                channel="working",
                content="Test message",
                ttl_sec=7200,  # 2 hours
                metadata={"custom": "value"}
            )
            
            # Verify set was called with TTL
            set_call = mock_redis.set.call_args
            assert set_call[1]["ex"] == 7200  # TTL parameter
