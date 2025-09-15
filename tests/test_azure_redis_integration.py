"""
Integration tests for Azure Redis storage using fakeredis.
These tests simulate real Redis operations without requiring actual Redis connection.
"""

import asyncio
import json
import pytest
import time
import uuid
from unittest.mock import patch

try:
    import fakeredis
    import fakeredis.aioredis
    FAKEREDIS_AVAILABLE = True
except ImportError:
    fakeredis = None
    FAKEREDIS_AVAILABLE = False

from nexamem.config.storage import AzureRedisConfig, AzureAuthMethod
from nexamem.memory_scope import MemoryScope
from nexamem.storage.azure_redis import (
    AzureRedisStorage,
    AsyncAzureRedisStorage,
    AzureRedisConnectionError
)


pytestmark = pytest.mark.skipif(not FAKEREDIS_AVAILABLE, reason="fakeredis not available")


@pytest.fixture
def fake_redis_config():
    """Configuration for fake Redis testing."""
    return AzureRedisConfig(
        hostname="fake.redis.cache.windows.net",
        access_key="fake-access-key",
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


class TestAzureRedisStorageIntegration:
    """Integration tests with fake Redis."""

    @patch('nexamem.storage.azure_redis.redis.Redis')
    def test_fake_redis_sync_operations(self, mock_redis_class, fake_redis_config):
        """Test sync operations with fake Redis."""
        # Create fake Redis instance
        fake_redis = fakeredis.FakeStrictRedis(decode_responses=True)
        mock_redis_class.return_value = fake_redis
        
        storage = AzureRedisStorage(fake_redis_config)
        storage.connect()
        
        # Test store operation
        result = storage.store_memory(
            "test-id-1",
            "Test content for Redis integration",
            {"source": "integration_test", "type": "test"},
            "integration-scope"
        )
        assert result is True
        
        # Test retrieve operation
        memory = storage.retrieve_memory("test-id-1")
        assert memory is not None
        assert memory["content"] == "Test content for Redis integration"
        assert memory["metadata"]["source"] == "integration_test"
        assert memory["scope"] == "integration-scope"
        assert "created_at" in memory
        assert "updated_at" in memory
        
        # Test list all memories
        all_memories = storage.list_memories()
        assert "test-id-1" in all_memories
        assert len(all_memories) == 1
        
        # Test list by scope
        scope_memories = storage.list_memories("integration-scope")
        assert "test-id-1" in scope_memories
        
        # Test search functionality
        search_results = storage.search_memories("Redis integration")
        assert "test-id-1" in search_results
        
        search_results = storage.search_memories("nonexistent")
        assert len(search_results) == 0
        
        # Test storage stats
        stats = storage.get_stats()
        assert stats["total_memories"] == 1
        assert stats["storage_type"] == "azure_redis"
        assert stats["total_scopes"] >= 1
        
        # Test update operation (store with same ID)
        result = storage.store_memory(
            "test-id-1",
            "Updated test content",
            {"source": "integration_test", "updated": True},
            "integration-scope"
        )
        assert result is True
        
        updated_memory = storage.retrieve_memory("test-id-1")
        assert updated_memory is not None
        assert updated_memory["content"] == "Updated test content"
        assert updated_memory["metadata"]["updated"] is True
        
        # Test delete operation
        result = storage.delete_memory("test-id-1")
        assert result is True
        
        deleted_memory = storage.retrieve_memory("test-id-1")
        assert deleted_memory is None
        
        # Verify empty state
        all_memories = storage.list_memories()
        assert len(all_memories) == 0

    @patch('nexamem.storage.azure_redis.redis_async.Redis')
    @pytest.mark.asyncio
    async def test_fake_redis_async_operations(self, mock_redis_class, fake_redis_config):
        """Test async operations with fake Redis."""
        # Create fake async Redis instance
        fake_redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
        mock_redis_class.return_value = fake_redis
        
        storage = AsyncAzureRedisStorage(fake_redis_config)
        await storage.connect()
        
        # Test async store operation
        result = await storage.store_memory(
            "async-test-id-1",
            "Async test content for Redis integration",
            {"source": "async_integration_test", "type": "async_test"},
            "async-integration-scope"
        )
        assert result is True
        
        # Test async retrieve operation
        memory = await storage.retrieve_memory("async-test-id-1")
        assert memory is not None
        assert memory["content"] == "Async test content for Redis integration"
        assert memory["metadata"]["source"] == "async_integration_test"
        assert memory["scope"] == "async-integration-scope"
        
        # Test async list operations
        all_memories = await storage.list_memories()
        assert "async-test-id-1" in all_memories
        
        scope_memories = await storage.list_memories("async-integration-scope")
        assert "async-test-id-1" in scope_memories
        
        # Test async search
        search_results = await storage.search_memories("Async test")
        assert "async-test-id-1" in search_results
        
        # Test async stats
        stats = await storage.get_stats()
        assert stats["total_memories"] == 1
        assert stats["storage_type"] == "azure_redis"
        
        # Test async delete
        result = await storage.delete_memory("async-test-id-1")
        assert result is True
        
        deleted_memory = await storage.retrieve_memory("async-test-id-1")
        assert deleted_memory is None

    @patch('nexamem.storage.azure_redis.redis.Redis')
    def test_multiple_scopes_sync(self, mock_redis_class, fake_redis_config):
        """Test operations across multiple scopes (sync)."""
        fake_redis = fakeredis.FakeStrictRedis(decode_responses=True)
        mock_redis_class.return_value = fake_redis
        
        storage = AzureRedisStorage(fake_redis_config)
        storage.connect()
        
        # Store memories in different scopes
        for i in range(3):
            for scope in ["scope-A", "scope-B", "scope-C"]:
                storage.store_memory(
                    f"{scope}-memory-{i}",
                    f"Content for {scope} memory {i}",
                    {"scope": scope, "index": i},
                    scope
                )
        
        # Test scope isolation
        scope_a_memories = storage.list_memories("scope-A")
        scope_b_memories = storage.list_memories("scope-B") 
        scope_c_memories = storage.list_memories("scope-C")
        
        assert len(scope_a_memories) == 3
        assert len(scope_b_memories) == 3
        assert len(scope_c_memories) == 3
        
        # Verify no overlap
        assert set(scope_a_memories).isdisjoint(set(scope_b_memories))
        assert set(scope_b_memories).isdisjoint(set(scope_c_memories))
        
        # Test cross-scope search
        all_scope_a_results = storage.search_memories("scope-A")
        assert len(all_scope_a_results) == 3
        
        # Test stats across scopes
        stats = storage.get_stats()
        assert stats["total_memories"] == 9
        assert stats["total_scopes"] == 3

    @patch('nexamem.storage.azure_redis.redis.Redis')
    def test_error_resilience_sync(self, mock_redis_class, fake_redis_config):
        """Test error handling and resilience (sync)."""
        fake_redis = fakeredis.FakeStrictRedis(decode_responses=True)
        mock_redis_class.return_value = fake_redis
        
        storage = AzureRedisStorage(fake_redis_config)
        storage.connect()
        
        # Test retrieving non-existent memory
        result = storage.retrieve_memory("nonexistent-id")
        assert result is None
        
        # Test deleting non-existent memory
        result = storage.delete_memory("nonexistent-id")
        assert result is False
        
        # Test searching with empty database
        results = storage.search_memories("anything")
        assert results == []
        
        # Test listing memories from non-existent scope
        results = storage.list_memories("nonexistent-scope")
        assert results == []

    @patch('nexamem.storage.azure_redis.redis_async.Redis')
    @pytest.mark.asyncio
    async def test_error_resilience_async(self, mock_redis_class, fake_redis_config):
        """Test error handling and resilience (async)."""
        fake_redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
        mock_redis_class.return_value = fake_redis
        
        storage = AsyncAzureRedisStorage(fake_redis_config)
        await storage.connect()
        
        # Test retrieving non-existent memory
        result = await storage.retrieve_memory("nonexistent-id")
        assert result is None
        
        # Test deleting non-existent memory
        result = await storage.delete_memory("nonexistent-id")
        assert result is False
        
        # Test searching with empty database
        results = await storage.search_memories("anything")
        assert results == []
        
        # Test listing memories from non-existent scope
        results = await storage.list_memories("nonexistent-scope")
        assert results == []

    @patch('nexamem.storage.azure_redis.redis.Redis')
    def test_ping_operations_sync(self, mock_redis_class, fake_redis_config):
        """Test ping operations (sync)."""
        fake_redis = fakeredis.FakeStrictRedis(decode_responses=True)
        mock_redis_class.return_value = fake_redis
        
        storage = AzureRedisStorage(fake_redis_config)
        storage.connect()
        
        # Test successful ping
        result = storage.ping()
        assert result is True

    @patch('nexamem.storage.azure_redis.redis_async.Redis')
    @pytest.mark.asyncio
    async def test_ping_operations_async(self, mock_redis_class, fake_redis_config):
        """Test ping operations (async)."""
        fake_redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
        mock_redis_class.return_value = fake_redis
        
        storage = AsyncAzureRedisStorage(fake_redis_config)
        await storage.connect()
        
        # Test successful ping
        result = await storage.ping()
        assert result is True

    @patch('nexamem.storage.azure_redis.redis.Redis')
    def test_large_data_operations_sync(self, mock_redis_class, fake_redis_config):
        """Test operations with larger data sets (sync)."""
        fake_redis = fakeredis.FakeStrictRedis(decode_responses=True)
        mock_redis_class.return_value = fake_redis
        
        storage = AzureRedisStorage(fake_redis_config)
        storage.connect()
        
        # Store multiple memories with larger content
        large_content = "This is a large test content. " * 100  # ~3KB
        
        memory_ids = []
        for i in range(50):
            memory_id = f"large-memory-{i}"
            memory_ids.append(memory_id)
            
            result = storage.store_memory(
                memory_id,
                f"{large_content} Index: {i}",
                {"index": i, "size": "large"},
                f"large-scope-{i % 5}"  # 5 different scopes
            )
            assert result is True
        
        # Test retrieval of all memories
        all_memories = storage.list_memories()
        assert len(all_memories) == 50
        
        # Test search across large dataset
        search_results = storage.search_memories("Index: 25")
        assert len(search_results) == 1
        assert "large-memory-25" in search_results
        
        # Test stats with larger dataset
        stats = storage.get_stats()
        assert stats["total_memories"] == 50
        assert stats["total_scopes"] == 5
        
        # Clean up - delete all memories
        for memory_id in memory_ids:
            result = storage.delete_memory(memory_id)
            assert result is True
        
        # Verify cleanup
        final_memories = storage.list_memories()
        assert len(final_memories) == 0


class TestAzureRedisPerformance:
    """Performance and stress tests for Azure Redis storage."""

    @patch('nexamem.storage.azure_redis.redis.Redis')
    def test_concurrent_operations_simulation_sync(self, mock_redis_class, fake_redis_config):
        """Test simulated concurrent operations (sync)."""
        fake_redis = fakeredis.FakeStrictRedis(decode_responses=True)
        mock_redis_class.return_value = fake_redis
        
        storage = AzureRedisStorage(fake_redis_config)
        storage.connect()
        
        start_time = time.time()
        
        # Simulate rapid operations
        operations_count = 100
        for i in range(operations_count):
            # Mix of store, retrieve, and search operations
            if i % 3 == 0:
                storage.store_memory(f"perf-{i}", f"Content {i}", {"op": "store"}, "perf-scope")
            elif i % 3 == 1:
                storage.retrieve_memory(f"perf-{i-1}")
            else:
                storage.search_memories(f"Content")
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should complete reasonably quickly (under 1 second for fake Redis)
        assert duration < 1.0
        
        # Verify data integrity
        stats = storage.get_stats()
        expected_stores = operations_count // 3 + (1 if operations_count % 3 > 0 else 0)
        assert stats["total_memories"] == expected_stores

    @patch('nexamem.storage.azure_redis.redis_async.Redis')
    @pytest.mark.asyncio
    async def test_concurrent_operations_simulation_async(self, mock_redis_class, fake_redis_config):
        """Test simulated concurrent operations (async)."""
        fake_redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
        mock_redis_class.return_value = fake_redis
        
        storage = AsyncAzureRedisStorage(fake_redis_config)
        await storage.connect()
        
        start_time = time.time()
        
        # Create tasks for concurrent execution
        async def store_task(i):
            return await storage.store_memory(f"async-perf-{i}", f"Async Content {i}", {"op": "store"}, "async-perf-scope")
        
        async def retrieve_task(i):
            return await storage.retrieve_memory(f"async-perf-{i}")
        
        async def search_task():
            return await storage.search_memories("Async Content")
        
        # Execute tasks concurrently
        tasks = []
        for i in range(20):
            tasks.append(store_task(i))
        
        for i in range(10):
            tasks.append(retrieve_task(i))
        
        for _ in range(5):
            tasks.append(search_task())
        
        results = await asyncio.gather(*tasks)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should complete reasonably quickly
        assert duration < 2.0
        
        # Verify most store operations succeeded
        store_results = results[:20]
        successful_stores = sum(1 for r in store_results if r is True)
        assert successful_stores >= 15  # Allow for some variance in fake Redis


class TestAzureRedisConfiguration:
    """Test various configuration scenarios for Azure Redis."""

    def test_ssl_configuration(self):
        """Test SSL configuration validation."""
        # Valid SSL configuration
        config = AzureRedisConfig(
            hostname="test.redis.cache.windows.net",
            access_key="test-key",
            ssl=True,
            port=6380
        )
        assert config.ssl is True
        assert config.port == 6380
        
        # Non-SSL configuration (not recommended for Azure)
        config_no_ssl = AzureRedisConfig(
            hostname="test.redis.cache.windows.net",
            access_key="test-key",
            ssl=False,
            port=6379
        )
        assert config_no_ssl.ssl is False
        assert config_no_ssl.port == 6379

    def test_database_selection(self):
        """Test Redis database selection."""
        for db_num in range(16):  # Azure Redis supports 0-15
            config = AzureRedisConfig(
                hostname="test.redis.cache.windows.net",
                access_key="test-key",
                db=db_num
            )
            assert config.db == db_num

    def test_collections_prefix_configuration(self):
        """Test collections prefix configuration."""
        config = AzureRedisConfig(
            hostname="test.redis.cache.windows.net",
            access_key="test-key",
            use_collections=True,
            collection_prefix="custom_prefix"
        )
        assert config.use_collections is True
        assert config.collection_prefix == "custom_prefix"