"""Tests for memory storage implementation."""

import pytest

from nexamem.storage.memory import AsyncMemoryStorage, MemoryStorage


class TestMemoryStorage:
    """Test memory storage implementation."""

    def test_store_and_retrieve(self):
        """Test storing and retrieving memories."""
        storage = MemoryStorage()

        # Store a memory
        result = storage.store_memory(
            "test1", "Hello world", {"author": "test"}, "test_scope"
        )
        assert result is True

        # Retrieve the memory
        memory = storage.retrieve_memory("test1")
        assert memory is not None
        assert memory["content"] == "Hello world"
        assert memory["metadata"]["author"] == "test"
        assert memory["scope"] == "test_scope"

    def test_delete_memory(self):
        """Test deleting memories."""
        storage = MemoryStorage()

        # Store a memory
        storage.store_memory("test1", "Hello world")

        # Delete it
        result = storage.delete_memory("test1")
        assert result is True

        # Should not be retrievable
        memory = storage.retrieve_memory("test1")
        assert memory is None

        # Deleting non-existent memory should return False
        result = storage.delete_memory("nonexistent")
        assert result is False

    def test_list_memories(self):
        """Test listing memories."""
        storage = MemoryStorage()

        # Store multiple memories
        storage.store_memory("test1", "Content 1", scope="scope1")
        storage.store_memory("test2", "Content 2", scope="scope2")
        storage.store_memory("test3", "Content 3", scope="scope1")

        # List all memories
        all_memories = storage.list_memories()
        assert len(all_memories) == 3
        assert "test1" in all_memories
        assert "test2" in all_memories
        assert "test3" in all_memories

        # List memories by scope
        scope1_memories = storage.list_memories("scope1")
        assert len(scope1_memories) == 2
        assert "test1" in scope1_memories
        assert "test3" in scope1_memories

        scope2_memories = storage.list_memories("scope2")
        assert len(scope2_memories) == 1
        assert "test2" in scope2_memories

    def test_search_memories(self):
        """Test searching memories."""
        storage = MemoryStorage()

        # Store memories with different content
        storage.store_memory("test1", "Python programming", scope="coding")
        storage.store_memory("test2", "Java development", scope="coding")
        storage.store_memory("test3", "Cooking recipes", scope="food")

        # Search for Python
        results = storage.search_memories("Python")
        assert len(results) == 1
        assert "test1" in results

        # Search within scope
        results = storage.search_memories("development", "coding")
        assert len(results) == 1
        assert "test2" in results

        # Search with no matches
        results = storage.search_memories("nonexistent")
        assert len(results) == 0

    def test_get_statistics(self):
        """Test getting storage statistics."""
        storage = MemoryStorage()

        # Initially empty
        stats = storage.get_stats()
        assert stats["total_memories"] == 0
        assert stats["total_scopes"] == 0

        # Add some memories
        storage.store_memory("test1", "Content 1", scope="scope1")
        storage.store_memory("test2", "Content 2", scope="scope2")
        storage.store_memory("test3", "Content 3", scope="scope1")

        stats = storage.get_stats()
        assert stats["total_memories"] == 3
        assert stats["total_scopes"] == 2
        assert stats["audit_entries"] == 3

    def test_clear_scope_via_individual_deletes(self):
        """Test clearing all memories in a scope via individual deletes."""
        storage = MemoryStorage()

        # Store memories in different scopes
        storage.store_memory("test1", "Content 1", scope="scope1")
        storage.store_memory("test2", "Content 2", scope="scope2")
        storage.store_memory("test3", "Content 3", scope="scope1")

        # Get scope1 memories and delete them
        scope1_memories = storage.list_memories("scope1")
        deleted_count = 0
        for memory_id in scope1_memories:
            if storage.delete_memory(memory_id):
                deleted_count += 1

        assert deleted_count == 2

        # Only scope2 memory should remain
        remaining_scope2 = storage.list_memories("scope2")
        assert len(remaining_scope2) == 1


@pytest.mark.asyncio
class TestAsyncMemoryStorage:
    """Test async memory storage implementation."""

    async def test_store_and_retrieve(self):
        """Test storing and retrieving memories asynchronously."""
        storage = AsyncMemoryStorage()

        # Store a memory
        result = await storage.store_memory(
            "test1", "Hello world", {"author": "test"}, "test_scope"
        )
        assert result is True

        # Retrieve the memory
        memory = await storage.retrieve_memory("test1")
        assert memory is not None
        assert memory["content"] == "Hello world"
        assert memory["metadata"]["author"] == "test"
        assert memory["scope"] == "test_scope"

    async def test_delete_memory(self):
        """Test deleting memories asynchronously."""
        storage = AsyncMemoryStorage()

        # Store a memory
        await storage.store_memory("test1", "Hello world")

        # Delete it
        result = await storage.delete_memory("test1")
        assert result is True

        # Should not be retrievable
        memory = await storage.retrieve_memory("test1")
        assert memory is None

    async def test_list_memories(self):
        """Test listing memories asynchronously."""
        storage = AsyncMemoryStorage()

        # Store multiple memories
        await storage.store_memory("test1", "Content 1", scope="scope1")
        await storage.store_memory("test2", "Content 2", scope="scope2")
        await storage.store_memory("test3", "Content 3", scope="scope1")

        # List all memories
        all_memories = await storage.list_memories()
        assert len(all_memories) == 3

        # List memories by scope
        scope1_memories = await storage.list_memories("scope1")
        assert len(scope1_memories) == 2

    async def test_search_memories(self):
        """Test searching memories asynchronously."""
        storage = AsyncMemoryStorage()

        # Store memories with different content
        await storage.store_memory("test1", "Python programming", scope="coding")
        await storage.store_memory("test2", "Java development", scope="coding")

        # Search for Python
        results = await storage.search_memories("Python")
        assert len(results) == 1
        assert "test1" in results

    async def test_get_statistics(self):
        """Test getting storage statistics asynchronously."""
        storage = AsyncMemoryStorage()

        # Add some memories
        await storage.store_memory("test1", "Content 1", scope="scope1")
        await storage.store_memory("test2", "Content 2", scope="scope2")

        stats = await storage.get_stats()
        assert stats["total_memories"] == 2
        assert stats["total_scopes"] == 2

    async def test_clear_scope_via_individual_deletes(self):
        """Test clearing all memories in a scope via individual deletes asynchronously."""
        storage = AsyncMemoryStorage()

        # Store memories in different scopes
        await storage.store_memory("test1", "Content 1", scope="scope1")
        await storage.store_memory("test2", "Content 2", scope="scope2")
        await storage.store_memory("test3", "Content 3", scope="scope1")

        # Get scope1 memories and delete them
        scope1_memories = await storage.list_memories("scope1")
        deleted_count = 0
        for memory_id in scope1_memories:
            if await storage.delete_memory(memory_id):
                deleted_count += 1

        assert deleted_count == 2

        # Only scope2 memory should remain
        remaining_scope2 = await storage.list_memories("scope2")
        assert len(remaining_scope2) == 1
