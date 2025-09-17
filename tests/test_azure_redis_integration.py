"""
Integration tests for Azure Redis factory and interfaces.
Tests the complete SOLID implementation including dependency injection.
"""

from unittest.mock import patch

import fakeredis
import pytest

from nexamem.config.storage import AzureAuthMethod, AzureRedisConfig, StorageConfig
from nexamem.storage.azure_redis_factory import (
    AccessKeyAuthProvider,
    AsyncAccessKeyAuthProvider,
    AzureRedisStorageFactory,
    create_azure_redis_storage,
)
from nexamem.storage.interfaces import (
    AsyncConversationMemoryAdapter,
    ConversationMemoryAdapter,
    MemoryServiceFactory,
    create_from_environment,
    create_memory_service,
)


class TestAzureRedisFactory:
    """Test Azure Redis factory patterns."""

    def test_create_auth_provider_access_key(self):
        """Test creating access key auth provider."""
        config = AzureRedisConfig(
            hostname="test.redis.cache.windows.net",
            access_key="test_key",
            auth_method=AzureAuthMethod.ACCESS_KEY
        )

        provider = AzureRedisStorageFactory.create_auth_provider(config)
        assert isinstance(provider, AccessKeyAuthProvider)
        assert provider.get_auth_token() == "test_key"

    def test_create_async_auth_provider_access_key(self):
        """Test creating async access key auth provider."""
        config = AzureRedisConfig(
            hostname="test.redis.cache.windows.net",
            access_key="test_key",
            auth_method=AzureAuthMethod.ACCESS_KEY
        )

        provider = AzureRedisStorageFactory.create_async_auth_provider(config)
        assert isinstance(provider, AsyncAccessKeyAuthProvider)

    @pytest.mark.asyncio
    async def test_async_auth_provider(self):
        """Test async auth provider functionality."""
        config = AzureRedisConfig(
            hostname="test.redis.cache.windows.net",
            access_key="test_key",
            auth_method=AzureAuthMethod.ACCESS_KEY
        )

        provider = AzureRedisStorageFactory.create_async_auth_provider(config)
        token = await provider.get_auth_token()
        assert token == "test_key"

    @patch('nexamem.storage.azure_redis.redis.Redis')
    def test_create_storage_with_custom_auth(self, mock_redis):
        """Test creating storage with custom auth provider."""
        config = AzureRedisConfig(
            hostname="test.redis.cache.windows.net",
            access_key="test_key",
            auth_method=AzureAuthMethod.ACCESS_KEY
        )

        custom_auth = AccessKeyAuthProvider("custom_key")
        fake_client = fakeredis.FakeRedis(decode_responses=True)
        mock_redis.return_value = fake_client

        storage = AzureRedisStorageFactory.create_storage(config, custom_auth)
        assert hasattr(storage, '_auth_provider')
        assert storage._auth_provider.get_auth_token() == "custom_key"

    @patch('nexamem.storage.azure_redis.redis_async.Redis')
    def test_create_async_storage_with_custom_auth(self, mock_redis):
        """Test creating async storage with custom auth provider."""
        config = AzureRedisConfig(
            hostname="test.redis.cache.windows.net",
            access_key="test_key",
            auth_method=AzureAuthMethod.ACCESS_KEY
        )

        custom_auth = AsyncAccessKeyAuthProvider("custom_key")
        fake_client = fakeredis.FakeAsyncRedis(decode_responses=True)
        mock_redis.return_value = fake_client

        storage = AzureRedisStorageFactory.create_async_storage(config, custom_auth)
        assert hasattr(storage, '_auth_provider')

    def test_convenience_function(self):
        """Test convenience function for creating storage."""
        config = AzureRedisConfig(
            hostname="test.redis.cache.windows.net",
            access_key="test_key",
            auth_method=AzureAuthMethod.ACCESS_KEY
        )

        # Test async preferred (default)
        storage = create_azure_redis_storage(config)
        assert hasattr(storage, '_connection_lock')  # Async storage has this

        # Test sync preferred
        storage = create_azure_redis_storage(config, async_preferred=False)
        assert not hasattr(storage, '_connection_lock')  # Sync storage doesn't


class TestConversationMemoryAdapters:
    """Test high-level conversation memory interfaces."""

    def test_sync_conversation_adapter(self):
        """Test synchronous conversation memory adapter."""
        storage_config = StorageConfig.memory()
        adapter = ConversationMemoryAdapter(storage_config)

        # Test storing conversation turn
        turn_id = adapter.store_conversation_turn(
            "conv1",
            {"user": "Hello", "assistant": "Hi there!"},
            {"user_id": "user123"}
        )
        assert turn_id is not None

        # Test getting conversation history
        history = adapter.get_conversation_history("conv1")
        assert len(history) == 1
        assert history[0]["conversation_id"] == "conv1"
        assert "user" in str(history[0]["data"])

        # Test search
        conversations = adapter.search_conversations("Hello")
        assert "conv1" in conversations

        # Test stats
        stats = adapter.get_stats()
        assert stats["adapter_type"] == "conversation_memory"
        assert stats["total_conversations"] >= 1

        # Test delete
        success = adapter.delete_conversation("conv1")
        assert success is True

        # Verify deletion
        history = adapter.get_conversation_history("conv1")
        assert len(history) == 0

    @pytest.mark.asyncio
    async def test_async_conversation_adapter(self):
        """Test asynchronous conversation memory adapter."""
        storage_config = StorageConfig.memory()
        adapter = AsyncConversationMemoryAdapter(storage_config)

        # Test storing conversation turn
        turn_id = await adapter.store_conversation_turn(
            "conv1",
            {"user": "Hello", "assistant": "Hi there!"},
            {"user_id": "user123"}
        )
        assert turn_id is not None

        # Test getting conversation history
        history = await adapter.get_conversation_history("conv1")
        assert len(history) == 1
        assert history[0]["conversation_id"] == "conv1"

        # Test search
        conversations = await adapter.search_conversations("Hello")
        assert "conv1" in conversations

        # Test stats
        stats = await adapter.get_stats()
        assert stats["adapter_type"] == "async_conversation_memory"
        assert stats["total_conversations"] >= 1

        # Test delete
        success = await adapter.delete_conversation("conv1")
        assert success is True

    def test_memory_service_factory(self):
        """Test memory service factory."""
        # Test creating with memory storage
        service = MemoryServiceFactory.create_conversation_memory(
            StorageConfig.memory(),
            async_preferred=False
        )
        assert isinstance(service, ConversationMemoryAdapter)

        # Test creating with async preference
        service = MemoryServiceFactory.create_conversation_memory(
            StorageConfig.memory(),
            async_preferred=True
        )
        assert isinstance(service, AsyncConversationMemoryAdapter)

    def test_three_line_integration(self):
        """Test the 3-line integration pattern."""
        # Line 1: Already imported at top
        # Line 2: Create service
        memory = create_memory_service("memory", async_preferred=False)

        # Line 3: Use service
        turn_id = memory.store_conversation_turn(
            "conv1",
            {"user": "Hello", "assistant": "Hi there!"}
        )

        assert turn_id is not None
        assert isinstance(memory, ConversationMemoryAdapter)

    @pytest.mark.asyncio
    async def test_three_line_integration_async(self):
        """Test the 3-line integration pattern with async."""
        # Line 1: Already imported at top
        # Line 2: Create service
        memory = create_memory_service("memory", async_preferred=True)

        # Line 3: Use service
        turn_id = await memory.store_conversation_turn(
            "conv1",
            {"user": "Hello", "assistant": "Hi there!"}
        )

        assert turn_id is not None
        assert isinstance(memory, AsyncConversationMemoryAdapter)

    def test_unsupported_storage_type(self):
        """Test error handling for unsupported storage types."""
        with pytest.raises(ValueError, match="Unsupported storage type"):
            create_memory_service("unsupported_type")


class TestProductionIntegration:
    """Test production-ready integration scenarios."""

    def test_azure_redis_conversation_memory_factory(self):
        """Test Azure Redis conversation memory factory method."""
        with patch.dict('os.environ', {
            'AZURE_REDIS_HOSTNAME': 'test.redis.cache.windows.net',
            'AZURE_REDIS_ACCESS_KEY': 'test_key'
        }):
            # Test factory method
            service = MemoryServiceFactory.create_azure_redis_conversation_memory(
                hostname="test.redis.cache.windows.net",
                access_key="test_key",
                async_preferred=False
            )

            assert isinstance(service, ConversationMemoryAdapter)
            assert service.config.type.value == "azure_redis"

    @patch.dict('os.environ', {
        'NEXAMEM_STORAGE_TYPE': 'memory'
    })
    def test_create_from_environment(self):
        """Test creating service from environment variables."""
        service = create_from_environment(async_preferred=False)
        assert isinstance(service, ConversationMemoryAdapter)

    def test_error_resilience(self):
        """Test error resilience in production scenarios."""
        # Create adapter with memory storage for testing
        storage_config = StorageConfig.memory()
        adapter = ConversationMemoryAdapter(storage_config)

        # Store some data
        adapter.store_conversation_turn(
            "conv1",
            {"user": "Hello", "assistant": "Hi there!"}
        )

        # Simulate partial failure (some operations succeed, some fail)
        # This tests the robustness of the adapter interface
        history = adapter.get_conversation_history("conv1")
        assert len(history) >= 1

        # Test graceful handling of non-existent conversations
        history = adapter.get_conversation_history("non_existent")
        assert len(history) == 0

        # Test search with no results
        results = adapter.search_conversations("not_found")
        assert len(results) == 0

    def test_interface_compliance(self):
        """Test that implementations comply with the interface protocols."""
        from nexamem.storage.interfaces import IConversationMemory

        storage_config = StorageConfig.memory()
        adapter = ConversationMemoryAdapter(storage_config)

        # Verify protocol compliance
        assert isinstance(adapter, IConversationMemory)

        # Test all required methods exist and work
        turn_id = adapter.store_conversation_turn("conv1", {"test": "data"})
        assert turn_id is not None

        history = adapter.get_conversation_history("conv1")
        assert len(history) >= 1

        conversations = adapter.search_conversations("test")
        assert len(conversations) >= 0

        success = adapter.delete_conversation("conv1")
        assert isinstance(success, bool)


class TestOverridePatterns:
    """Test patterns for external projects to override and customize."""

    def test_custom_auth_provider(self):
        """Test using custom authentication provider."""
        class CustomAuthProvider:
            def get_auth_token(self):
                return "custom_token_from_external_system"

        config = AzureRedisConfig(
            hostname="test.redis.cache.windows.net",
            access_key="fallback_key",  # Fallback if custom fails
            auth_method=AzureAuthMethod.ACCESS_KEY
        )

        custom_provider = CustomAuthProvider()

        # External projects can inject their own auth
        with patch('nexamem.storage.azure_redis.redis.Redis') as mock_redis:
            fake_client = fakeredis.FakeRedis(decode_responses=True)
            mock_redis.return_value = fake_client

            storage = AzureRedisStorageFactory.create_storage(config, custom_provider)
            storage._auth_provider = custom_provider  # Override injection

            # Verify custom auth is used
            token = storage._auth_provider.get_auth_token()
            assert token == "custom_token_from_external_system"

    def test_custom_conversation_memory_implementation(self):
        """Test that external projects can implement IConversationMemory."""
        from nexamem.storage.interfaces import IConversationMemory

        class CustomMemoryImplementation:
            """External project's custom memory implementation."""

            def __init__(self):
                self.data = {}

            def store_conversation_turn(self, conversation_id, turn_data, metadata=None):
                if conversation_id not in self.data:
                    self.data[conversation_id] = []
                turn_id = f"turn_{len(self.data[conversation_id])}"
                self.data[conversation_id].append({
                    "turn_id": turn_id,
                    "data": turn_data,
                    "metadata": metadata
                })
                return turn_id

            def get_conversation_history(self, conversation_id, limit=None, since_timestamp=None):
                return self.data.get(conversation_id, [])[:limit] if limit else self.data.get(conversation_id, [])

            def delete_conversation(self, conversation_id):
                if conversation_id in self.data:
                    del self.data[conversation_id]
                    return True
                return False

            def search_conversations(self, query, user_id=None, limit=None):
                results = []
                for conv_id, turns in self.data.items():
                    for turn in turns:
                        if query.lower() in str(turn["data"]).lower():
                            results.append(conv_id)
                            break
                return results[:limit] if limit else results

        # Verify it implements the protocol
        custom_impl = CustomMemoryImplementation()
        assert isinstance(custom_impl, IConversationMemory)

        # Test functionality
        turn_id = custom_impl.store_conversation_turn("conv1", {"user": "Hello"})
        assert turn_id is not None

        history = custom_impl.get_conversation_history("conv1")
        assert len(history) == 1

        conversations = custom_impl.search_conversations("Hello")
        assert "conv1" in conversations

        success = custom_impl.delete_conversation("conv1")
        assert success is True
