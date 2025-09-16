"""
Tests for Azure Redis storage implementation.
Uses fakeredis for testing without requiring actual Azure Redis instance.
"""

import pytest
import fakeredis
from unittest.mock import Mock, patch, AsyncMock

from nexamem.config.storage import AzureRedisConfig, AzureAuthMethod
from nexamem.storage.azure_redis import (
    AsyncAzureRedisStorage, 
    AzureRedisStorage, 
    AzureRedisConnectionError,
    AzureRedisCollections
)


class TestAzureRedisConfig:
    """Test Azure Redis configuration validation."""
    
    def test_valid_config_access_key(self):
        """Test valid Azure Redis config with access key."""
        config = AzureRedisConfig(
            hostname="test.redis.cache.windows.net",
            access_key="test_key",
            auth_method=AzureAuthMethod.ACCESS_KEY
        )
        assert config.hostname == "test.redis.cache.windows.net"
        assert config.port == 6380
        assert config.ssl is True
        assert config.auth_method == AzureAuthMethod.ACCESS_KEY
    
    def test_invalid_hostname(self):
        """Test that invalid hostname raises ValueError."""
        with pytest.raises(ValueError, match="Azure Redis hostname must end with"):
            AzureRedisConfig(
                hostname="invalid.hostname.com",
                access_key="test_key"
            )
    
    def test_missing_access_key(self):
        """Test that missing access key raises ValueError."""
        with pytest.raises(ValueError, match="access_key required"):
            AzureRedisConfig(
                hostname="test.redis.cache.windows.net",
                auth_method=AzureAuthMethod.ACCESS_KEY
            )
    
    def test_keyvault_config_validation(self):
        """Test Key Vault configuration validation."""
        with pytest.raises(ValueError, match="keyvault_url and secret_name required"):
            AzureRedisConfig(
                hostname="test.redis.cache.windows.net",
                auth_method=AzureAuthMethod.KEYVAULT
            )
    
    def test_entra_id_validation(self):
        """Test Entra ID configuration validation."""
        with pytest.raises(ValueError, match="use_entra_id must be True"):
            AzureRedisConfig(
                hostname="test.redis.cache.windows.net",
                auth_method=AzureAuthMethod.ENTRA_ID,
                use_entra_id=False
            )


class TestAzureRedisCollections:
    """Test Redis collections management."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Use fakeredis for testing
        self.redis_client = fakeredis.FakeRedis(decode_responses=True)
        self.collections = AzureRedisCollections(self.redis_client, "test")
        
        # Mock memory scope
        self.scope = Mock()
        self.scope.env = "test"
        self.scope.agent_id = "agent1"
        self.scope.user_id = "user1"
        self.scope.session_id = "session1"
    
    def test_add_message_sync(self):
        """Test adding message synchronously."""
        message_data = {"content": "test message", "metadata": {}}
        message_id = self.collections.add_message_to_channel_sync(
            self.scope, "channel1", message_data, 3600
        )
        
        assert message_id is not None
        assert len(message_id) > 0
        
        # Verify message was stored in hash
        messages_hash = "test:messages:test:agent1"
        assert self.redis_client.hexists(messages_hash, f"user1:session1:channel1:{message_id}")
        
        # Verify index was updated
        index_key = "test:index:test:agent1:user1:session1:channel1"
        assert self.redis_client.zcard(index_key) == 1
    
    def test_get_messages_sync(self):
        """Test retrieving messages synchronously."""
        # Add some test messages
        message_data1 = {"content": "message 1", "metadata": {}}
        message_data2 = {"content": "message 2", "metadata": {}}
        
        self.collections.add_message_to_channel_sync(
            self.scope, "channel1", message_data1, 3600
        )
        self.collections.add_message_to_channel_sync(
            self.scope, "channel1", message_data2, 3600
        )
        
        # Retrieve messages
        messages, metadata = self.collections.get_messages_from_channel_sync(
            self.scope, "channel1"
        )
        
        assert len(messages) == 2
        assert "message 1" in messages
        assert "message 2" in messages
        assert metadata["total_messages"] == 2
        assert metadata["total_bytes"] > 0
        assert metadata["truncated"] is False
    
    def test_message_limit(self):
        """Test message count limiting."""
        # Add multiple messages
        for i in range(5):
            message_data = {"content": f"message {i}", "metadata": {}}
            self.collections.add_message_to_channel_sync(
                self.scope, f"channel{i%2}", message_data, 3600
            )
        
        # Retrieve with limit
        messages, metadata = self.collections.get_messages_from_channel_sync(
            self.scope, "channel0", max_msgs=2
        )
        
        assert len(messages) <= 2
        assert metadata["total_messages"] <= 2
    
    def test_byte_limit(self):
        """Test message byte limiting."""
        # Add messages with known sizes
        large_content = "x" * 1000  # 1000 bytes
        message_data = {"content": large_content, "metadata": {}}
        
        for i in range(3):
            self.collections.add_message_to_channel_sync(
                self.scope, "channel1", message_data, 3600
            )
        
        # Retrieve with byte limit
        messages, metadata = self.collections.get_messages_from_channel_sync(
            self.scope, "channel1", max_bytes=1500
        )
        
        assert metadata["total_bytes"] <= 1500
        assert len(messages) <= 2  # Should truncate


class TestAzureRedisStorage:
    """Test synchronous Azure Redis storage."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = AzureRedisConfig(
            hostname="test.redis.cache.windows.net",
            access_key="test_key",
            auth_method=AzureAuthMethod.ACCESS_KEY,
            use_collections=True
        )
    
    @patch('nexamem.storage.azure_redis.redis.Redis')
    def test_connection_with_access_key(self, mock_redis):
        """Test connection using access key."""
        mock_client = Mock()
        mock_redis.return_value = mock_client
        mock_client.ping.return_value = True
        
        storage = AzureRedisStorage(self.config)
        storage.connect()
        
        mock_redis.assert_called_once()
        mock_client.ping.assert_called_once()
        assert storage._client is not None
    
    @patch('nexamem.storage.azure_redis.redis.Redis')
    def test_connection_failure(self, mock_redis):
        """Test connection failure handling."""
        mock_redis.side_effect = Exception("Connection failed")
        
        storage = AzureRedisStorage(self.config)
        
        with pytest.raises(AzureRedisConnectionError):
            storage.connect()
    
    @patch('nexamem.storage.azure_redis.redis.Redis')
    def test_memory_operations(self, mock_redis):
        """Test basic memory operations."""
        # Use fakeredis for actual Redis operations  
        fake_client = fakeredis.FakeRedis(decode_responses=True)
        # Mock just the connection creation to use fake client
        with patch.object(storage, '_establish_connection') as mock_establish:
            mock_establish.return_value = None
            storage._client = fake_client
            storage._collections = AzureRedisCollections(fake_client, storage.config.collection_prefix)
            
            # Test store
            success = storage.store_memory("test1", "content1", {"key": "value"}, "scope1")
            assert success is True
        
        # Test retrieve
        memory = storage.retrieve_memory("test1")
        assert memory is not None
        assert memory["content"] == "content1"
        assert memory["metadata"] == {"key": "value"}
        assert memory["scope"] == "scope1"
        
        # Test list
        memories = storage.list_memories()
        assert "test1" in memories
        
        # Test search
        results = storage.search_memories("content")
        assert "test1" in results
        
        # Test stats
        stats = storage.get_stats()
        assert stats["total_memories"] >= 1
        assert stats["storage_type"] == "azure_redis"
        
        # Test delete
        deleted = storage.delete_memory("test1")
        assert deleted is True
        assert storage.retrieve_memory("test1") is None
    
    @patch('nexamem.storage.azure_redis.redis.Redis')
    def test_ping(self, mock_redis):
        """Test ping functionality."""
        mock_client = Mock()
        mock_redis.return_value = mock_client
        mock_client.ping.return_value = True
        
        storage = AzureRedisStorage(self.config)
        result = storage.ping()
        
        assert result is True
        mock_client.ping.assert_called()


class TestAsyncAzureRedisStorage:
    """Test asynchronous Azure Redis storage."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = AzureRedisConfig(
            hostname="test.redis.cache.windows.net",
            access_key="test_key",
            auth_method=AzureAuthMethod.ACCESS_KEY,
            use_collections=True
        )
    
    @pytest.mark.asyncio
    @patch('nexamem.storage.azure_redis.redis_async.Redis')
    async def test_async_connection_with_access_key(self, mock_redis):
        """Test async connection using access key."""
        mock_client = AsyncMock()
        mock_redis.return_value = mock_client
        mock_client.ping.return_value = True
        
        storage = AsyncAzureRedisStorage(self.config)
        await storage.connect()
        
        mock_redis.assert_called_once()
        mock_client.ping.assert_called_once()
        assert storage._client is not None
    
    @pytest.mark.asyncio
    @patch('nexamem.storage.azure_redis.redis_async.Redis')
    async def test_async_connection_failure(self, mock_redis):
        """Test async connection failure handling."""
        mock_redis.side_effect = Exception("Connection failed")
        
        storage = AsyncAzureRedisStorage(self.config)
        
        with pytest.raises(AzureRedisConnectionError):
            await storage.connect()
    
    @pytest.mark.asyncio
    @patch('nexamem.storage.azure_redis.redis_async.Redis')
    async def test_async_memory_operations(self, mock_redis):
        """Test async memory operations."""
        # Use fakeredis for actual Redis operations
        fake_client = fakeredis.FakeAsyncRedis(decode_responses=True)
        # Mock just the connection creation to use fake client
        with patch.object(storage, '_establish_connection') as mock_establish:
            mock_establish.return_value = None
            storage._client = fake_client
            storage._collections = AzureRedisCollections(fake_client, storage.config.collection_prefix)
            
            # Test store
            success = await storage.store_memory("test1", "content1", {"key": "value"}, "scope1")
            assert success is True
        
        # Test retrieve
        memory = await storage.retrieve_memory("test1")
        assert memory is not None
        assert memory["content"] == "content1"
        assert memory["metadata"] == {"key": "value"}
        assert memory["scope"] == "scope1"
        
        # Test list
        memories = await storage.list_memories()
        assert "test1" in memories
        
        # Test search
        results = await storage.search_memories("content")
        assert "test1" in results
        
        # Test stats
        stats = await storage.get_stats()
        assert stats["total_memories"] >= 1
        assert stats["storage_type"] == "azure_redis_async"
        
        # Test delete
        deleted = await storage.delete_memory("test1")
        assert deleted is True
        result = await storage.retrieve_memory("test1")
        assert result is None
    
    @pytest.mark.asyncio
    @patch('nexamem.storage.azure_redis.redis_async.Redis')
    async def test_async_ping(self, mock_redis):
        """Test async ping functionality."""
        mock_client = AsyncMock()
        mock_redis.return_value = mock_client
        mock_client.ping.return_value = True
        
        storage = AsyncAzureRedisStorage(self.config)
        result = await storage.ping()
        
        assert result is True
        mock_client.ping.assert_called()


class TestAzureAuthenticationMethods:
    """Test different Azure authentication methods."""
    
    @pytest.mark.asyncio
    @patch('nexamem.storage.azure_redis.AsyncDefaultAzureCredential')
    async def test_entra_id_auth_async(self, mock_credential_class):
        """Test Entra ID authentication for async storage."""
        # Mock the credential and token
        mock_credential = AsyncMock()
        mock_credential_class.return_value = mock_credential
        mock_token = Mock()
        mock_token.token = "test_token"
        mock_credential.get_token.return_value = mock_token
        
        config = AzureRedisConfig(
            hostname="test.redis.cache.windows.net",
            auth_method=AzureAuthMethod.ENTRA_ID,
            use_entra_id=True
        )
        
        storage = AsyncAzureRedisStorage(config)
        token = await storage._get_auth_token()
        
        assert token == "test_token"
        mock_credential.get_token.assert_called_once_with("https://redis.azure.com/.default")
    
    @pytest.mark.asyncio
    @patch('nexamem.storage.azure_redis.AsyncSecretClient')
    @patch('nexamem.storage.azure_redis.AsyncDefaultAzureCredential')
    async def test_keyvault_auth_async(self, mock_credential_class, mock_secret_client_class):
        """Test Key Vault authentication for async storage."""
        # Mock credential
        mock_credential = AsyncMock()
        mock_credential_class.return_value = mock_credential
        
        # Mock secret client and secret
        mock_secret_client = AsyncMock()
        mock_secret_client_class.return_value = mock_secret_client
        mock_secret = Mock()
        mock_secret.value = "secret_value"
        mock_secret_client.get_secret.return_value = mock_secret
        
        config = AzureRedisConfig(
            hostname="test.redis.cache.windows.net",
            auth_method=AzureAuthMethod.KEYVAULT,
            keyvault_url="https://test.vault.azure.net/",
            secret_name="redis-key"
        )
        
        storage = AsyncAzureRedisStorage(config)
        token = await storage._get_auth_token()
        
        assert token == "secret_value"
        mock_secret_client.get_secret.assert_called_once_with("redis-key")
    
    @pytest.mark.asyncio
    async def test_unsupported_auth_method_async(self):
        """Test handling of unsupported auth method."""
        # Create config with manual override for testing unsupported method
        config = AzureRedisConfig(
            hostname="test.redis.cache.windows.net",
            access_key="test_key",  # Valid auth first
            auth_method=AzureAuthMethod.ACCESS_KEY
        )
        # Manually override for testing
        config.auth_method = "unsupported"
        
        storage = AsyncAzureRedisStorage(config)
        
        with pytest.raises(AzureRedisConnectionError, match="Unsupported auth method"):
            await storage._get_auth_token()


class TestProductionFeatures:
    """Test production-ready features."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = AzureRedisConfig(
            hostname="test.redis.cache.windows.net",
            access_key="test_key",
            collection_prefix="audit_test"
        )
    
    @pytest.mark.asyncio
    @patch('nexamem.storage.azure_redis.redis_async.Redis')
    async def test_audit_logging(self, mock_redis):
        """Test audit logging functionality."""
        storage = AsyncAzureRedisStorage(self.config)
        
        # Use fakeredis for actual Redis operations
        fake_client = fakeredis.FakeAsyncRedis(decode_responses=True)
        # Mock just the connection creation to use fake client
        with patch.object(storage, '_establish_connection') as mock_establish:
            mock_establish.return_value = None
            storage._client = fake_client
            storage._collections = AzureRedisCollections(fake_client, storage.config.collection_prefix)
            
            # Store and delete a memory to generate audit entries
            await storage.store_memory("test1", "content1", scope="scope1")
            await storage.delete_memory("test1")
        
        # Check audit log
        audit_entries = await storage.get_audit_log()
        assert len(audit_entries) >= 2
        
        # Check audit log for specific memory
        memory_audit = await storage.get_audit_log(memory_id="test1")
        assert len(memory_audit) >= 2
    
    @pytest.mark.asyncio
    @patch('nexamem.storage.azure_redis.redis_async.Redis')
    async def test_scope_management(self, mock_redis):
        """Test scope-based memory management."""
        storage = AsyncAzureRedisStorage(self.config)
        
        # Use fakeredis for actual Redis operations
        fake_client = fakeredis.FakeAsyncRedis(decode_responses=True)
        # Mock just the connection creation to use fake client
        with patch.object(storage, '_establish_connection') as mock_establish:
            mock_establish.return_value = None
            storage._client = fake_client
            storage._collections = AzureRedisCollections(fake_client, storage.config.collection_prefix)
            
            # Store memories in different scopes
            await storage.store_memory("mem1", "content1", scope="scope1")
            await storage.store_memory("mem2", "content2", scope="scope1")
            await storage.store_memory("mem3", "content3", scope="scope2")
        
        # List memories by scope
        scope1_memories = await storage.list_memories(scope="scope1")
        scope2_memories = await storage.list_memories(scope="scope2")
        
        assert "mem1" in scope1_memories
        assert "mem2" in scope1_memories
        assert "mem3" in scope2_memories
        assert len(scope1_memories) == 2
        assert len(scope2_memories) == 1
        
        # Search within scope
        results = await storage.search_memories("content", scope="scope1")
        assert len(results) == 2
        assert "mem1" in results
        assert "mem2" in results
    
    @pytest.mark.asyncio
    @patch('nexamem.storage.azure_redis.redis_async.Redis')
    async def test_error_handling(self, mock_redis):
        """Test comprehensive error handling."""
        storage = AsyncAzureRedisStorage(self.config)
        
        # Test with failing Redis client
        mock_client = AsyncMock()
        mock_client.hset.side_effect = Exception("Redis error")
        
        # Mock just the connection creation to use failing client
        with patch.object(storage, '_establish_connection') as mock_establish:
            mock_establish.return_value = None
            storage._client = mock_client
            
            # Operations should return False/empty on failure
            success = await storage.store_memory("test1", "content1")
            assert success is False
        
        memory = await storage.retrieve_memory("test1")
        assert memory is None
        
        memories = await storage.list_memories()
        assert memories == []
        
        results = await storage.search_memories("query")
        assert results == []
        
        audit_log = await storage.get_audit_log()
        assert audit_log == []
        
        stats = await storage.get_stats()
        assert stats["total_memories"] == 0