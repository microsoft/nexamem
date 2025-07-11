"""Tests for new AIMemory implementation with dependency injection."""

import pytest

from nexamem import (
    AIMemory,
    AIMemoryConfig,
    AsyncAIMemory,
    StorageConfig,
)
from nexamem.di import DIContainer
from nexamem.storage.base import BaseAsyncStorage, BaseStorage


class TestAIMemory:
    """Test AIMemory synchronous implementation."""

    def test_init_with_memory_config(self):
        """Test initialization with memory storage config."""
        config = AIMemoryConfig(
            default_scope="test", storage=StorageConfig.memory()
        )
        ai_memory = AIMemory(config)
        assert ai_memory.config == config
        assert ai_memory._storage is not None

    def test_init_with_custom_container(self):
        """Test initialization with custom DI container."""
        config = AIMemoryConfig(
            default_scope="test", storage=StorageConfig.memory()
        )
        container = DIContainer()
        ai_memory = AIMemory(config, container)
        assert ai_memory.container == container

    def test_store_memory(self):
        """Test storing memories."""
        config = AIMemoryConfig(
            default_scope="test", storage=StorageConfig.memory()
        )
        ai_memory = AIMemory(config)

        # Store without explicit ID
        memory_id = ai_memory.store("Hello world", metadata={"type": "greeting"})
        assert memory_id is not None
        assert isinstance(memory_id, str)

        # Store with explicit ID
        custom_id = "custom-123"
        result_id = ai_memory.store("Custom content", memory_id=custom_id)
        assert result_id == custom_id

    def test_retrieve_memory(self):
        """Test retrieving memories."""
        config = AIMemoryConfig(
            default_scope="test", storage=StorageConfig.memory()
        )
        ai_memory = AIMemory(config)

        # Store a memory
        memory_id = ai_memory.store(
            "Test content", metadata={"author": "test"}, scope="custom_scope"
        )

        # Retrieve it
        memory = ai_memory.retrieve(memory_id)
        assert memory is not None
        assert memory["content"] == "Test content"
        assert memory["metadata"]["author"] == "test"
        assert memory["scope"] == "custom_scope"

        # Retrieve non-existent memory
        memory = ai_memory.retrieve("nonexistent")
        assert memory is None

    def test_delete_memory(self):
        """Test deleting memories."""
        config = AIMemoryConfig(
            default_scope="test", storage=StorageConfig.memory()
        )
        ai_memory = AIMemory(config)

        # Store a memory
        memory_id = ai_memory.store("To be deleted")

        # Delete it
        result = ai_memory.delete(memory_id)
        assert result is True

        # Should not be retrievable
        memory = ai_memory.retrieve(memory_id)
        assert memory is None

        # Delete non-existent memory
        result = ai_memory.delete("nonexistent")
        assert result is False

    def test_list_memories(self):
        """Test listing memories."""
        config = AIMemoryConfig(
            default_scope="test", storage=StorageConfig.memory()
        )
        ai_memory = AIMemory(config)

        # Store multiple memories
        id1 = ai_memory.store("Content 1", scope="scope1")
        id2 = ai_memory.store("Content 2", scope="scope2")
        id3 = ai_memory.store("Content 3", scope="scope1")

        # List all memories requires specifying None to get all
        # Since list() uses default scope if none specified
        scope1_memories = ai_memory.list("scope1")
        assert len(scope1_memories) == 2
        assert id1 in scope1_memories
        assert id3 in scope1_memories

        scope2_memories = ai_memory.list("scope2")
        assert len(scope2_memories) == 1
        assert id2 in scope2_memories

    def test_search_memories(self):
        """Test searching memories."""
        config = AIMemoryConfig(
            default_scope="test", storage=StorageConfig.memory()
        )
        ai_memory = AIMemory(config)

        # Store memories
        python_id = ai_memory.store("Python programming tutorial", scope="coding")
        java_id = ai_memory.store("Java development guide", scope="coding")
        ai_memory.store("Cooking recipes collection", scope="food")

        # Search for Python within the coding scope
        results = ai_memory.search("Python", "coding")
        assert len(results) == 1
        assert python_id in results

        # Search within scope
        results = ai_memory.search("development", "coding")
        assert len(results) == 1
        assert java_id in results

    def test_get_statistics(self):
        """Test getting statistics."""
        config = AIMemoryConfig(
            default_scope="test", storage=StorageConfig.memory()
        )
        ai_memory = AIMemory(config)

        # Store some memories
        ai_memory.store("Content 1", scope="scope1")
        ai_memory.store("Content 2", scope="scope2")

        stats = ai_memory.get_stats()
        assert "total_memories" in stats
        assert "total_scopes" in stats

    def test_clear_scope(self):
        """Test clearing a scope."""
        config = AIMemoryConfig(
            default_scope="test", storage=StorageConfig.memory()
        )
        ai_memory = AIMemory(config)

        # Store memories in different scopes
        ai_memory.store("Content 1", scope="scope1")
        ai_memory.store("Content 2", scope="scope2")
        ai_memory.store("Content 3", scope="scope1")

        # Clear scope1
        cleared = ai_memory.clear_scope("scope1")
        assert cleared == 2

        # Only scope2 memory should remain
        scope1_memories = ai_memory.list("scope1")
        assert len(scope1_memories) == 0

        scope2_memories = ai_memory.list("scope2")
        assert len(scope2_memories) == 1


@pytest.mark.asyncio
class TestAsyncAIMemory:
    """Test AsyncAIMemory asynchronous implementation."""

    async def test_init_with_memory_config(self):
        """Test initialization with memory storage config."""
        config = AIMemoryConfig(
            default_scope="test", storage=StorageConfig.memory()
        )
        ai_memory = AsyncAIMemory(config)
        assert ai_memory.config == config
        assert ai_memory._storage is not None

    async def test_store_memory(self):
        """Test storing memories asynchronously."""
        config = AIMemoryConfig(
            default_scope="test", storage=StorageConfig.memory()
        )
        ai_memory = AsyncAIMemory(config)

        # Store without explicit ID
        memory_id = await ai_memory.store(
            "Hello world", metadata={"type": "greeting"}
        )
        assert memory_id is not None
        assert isinstance(memory_id, str)

        # Store with explicit ID
        custom_id = "custom-123"
        result_id = await ai_memory.store("Custom content", memory_id=custom_id)
        assert result_id == custom_id

    async def test_retrieve_memory(self):
        """Test retrieving memories asynchronously."""
        config = AIMemoryConfig(
            default_scope="test", storage=StorageConfig.memory()
        )
        ai_memory = AsyncAIMemory(config)

        # Store a memory
        memory_id = await ai_memory.store(
            "Test content", metadata={"author": "test"}, scope="custom_scope"
        )

        # Retrieve it
        memory = await ai_memory.retrieve(memory_id)
        assert memory is not None
        assert memory["content"] == "Test content"
        assert memory["metadata"]["author"] == "test"
        assert memory["scope"] == "custom_scope"

    async def test_delete_memory(self):
        """Test deleting memories asynchronously."""
        config = AIMemoryConfig(
            default_scope="test", storage=StorageConfig.memory()
        )
        ai_memory = AsyncAIMemory(config)

        # Store a memory
        memory_id = await ai_memory.store("To be deleted")

        # Delete it
        result = await ai_memory.delete(memory_id)
        assert result is True

        # Should not be retrievable
        memory = await ai_memory.retrieve(memory_id)
        assert memory is None

    async def test_list_memories(self):
        """Test listing memories asynchronously."""
        config = AIMemoryConfig(
            default_scope="test", storage=StorageConfig.memory()
        )
        ai_memory = AsyncAIMemory(config)

        # Store multiple memories
        id1 = await ai_memory.store("Content 1", scope="scope1")
        await ai_memory.store("Content 2", scope="scope2")
        await ai_memory.store("Content 3", scope="scope1")

        # List by scope
        scope1_memories = await ai_memory.list("scope1")
        assert len(scope1_memories) == 2
        assert id1 in scope1_memories

    async def test_search_memories(self):
        """Test searching memories asynchronously."""
        config = AIMemoryConfig(
            default_scope="test", storage=StorageConfig.memory()
        )
        ai_memory = AsyncAIMemory(config)

        # Store memories
        python_id = await ai_memory.store("Python programming tutorial", scope="coding")
        await ai_memory.store("Java development guide", scope="coding")

        # Search for Python within the coding scope
        results = await ai_memory.search("Python", "coding")
        assert len(results) == 1
        assert python_id in results

    async def test_get_statistics(self):
        """Test getting statistics asynchronously."""
        config = AIMemoryConfig(
            default_scope="test", storage=StorageConfig.memory()
        )
        ai_memory = AsyncAIMemory(config)

        # Store some memories
        await ai_memory.store("Content 1", scope="scope1")
        await ai_memory.store("Content 2", scope="scope2")

        stats = await ai_memory.get_stats()
        assert "total_memories" in stats
        assert "total_scopes" in stats

    async def test_clear_scope(self):
        """Test clearing a scope asynchronously."""
        config = AIMemoryConfig(
            default_scope="test", storage=StorageConfig.memory()
        )
        ai_memory = AsyncAIMemory(config)

        # Store memories in different scopes
        await ai_memory.store("Content 1", scope="scope1")
        await ai_memory.store("Content 2", scope="scope2")
        await ai_memory.store("Content 3", scope="scope1")

        # Clear scope1
        cleared = await ai_memory.clear_scope("scope1")
        assert cleared == 2

        # Only scope2 memory should remain
        scope1_memories = await ai_memory.list("scope1")
        assert len(scope1_memories) == 0

        scope2_memories = await ai_memory.list("scope2")
        assert len(scope2_memories) == 1


def test_di_container_registration():
    """Test that DI container properly registers services."""
    config = AIMemoryConfig(default_scope="test", storage=StorageConfig.memory())
    container = DIContainer()

    # Create AIMemory with custom container
    AIMemory(config, container)

    # Container should have storage registered
    assert container.is_registered(BaseStorage)

    # Should be able to resolve storage
    storage = container.resolve(BaseStorage)
    assert storage is not None


@pytest.mark.asyncio
async def test_async_di_container_registration():
    """Test that async DI container properly registers services."""
    config = AIMemoryConfig(default_scope="test", storage=StorageConfig.memory())
    container = DIContainer()

    # Create AsyncAIMemory with custom container
    AsyncAIMemory(config, container)

    # Container should have async storage registered
    assert container.is_registered(BaseAsyncStorage)

    # Should be able to resolve async storage
    storage = container.resolve(BaseAsyncStorage)
    assert storage is not None
