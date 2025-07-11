"""Tests for base storage interfaces."""

from abc import ABC

import pytest

from nexamem.storage.base import BaseStorage, BaseAsyncStorage


def test_base_storage_is_abstract():
    """Test that BaseStorage is an abstract base class."""
    assert issubclass(BaseStorage, ABC)

    # Should not be able to instantiate directly
    with pytest.raises(TypeError):
        BaseStorage()


def test_base_async_storage_is_abstract():
    """Test that BaseAsyncStorage is an abstract base class."""
    assert issubclass(BaseAsyncStorage, ABC)

    # Should not be able to instantiate directly
    with pytest.raises(TypeError):
        BaseAsyncStorage()


def test_base_storage_methods_are_abstract():
    """Test that all required methods are abstract."""

    class IncompleteStorage(BaseStorage):
        pass

    # Should not be able to instantiate without implementing all methods
    with pytest.raises(TypeError):
        IncompleteStorage()


def test_base_async_storage_methods_are_abstract():
    """Test that all required async methods are abstract."""

    class IncompleteAsyncStorage(BaseAsyncStorage):
        pass

    # Should not be able to instantiate without implementing all methods
    with pytest.raises(TypeError):
        IncompleteAsyncStorage()


class MockStorage(BaseStorage):
    """Mock storage implementation for testing."""

    def __init__(self):
        self.data = {}
        self.audit_log = []

    def store_memory(self, memory_id, content, metadata=None, scope=None):
        self.data[memory_id] = {"content": content, "metadata": metadata or {}, "scope": scope}
        self.audit_log.append(("store", memory_id))
        return True

    def retrieve_memory(self, memory_id):
        return self.data.get(memory_id)

    def delete_memory(self, memory_id):
        if memory_id in self.data:
            del self.data[memory_id]
            self.audit_log.append(("delete", memory_id))
            return True
        return False

    def list_memories(self, scope=None):
        if scope is None:
            return list(self.data.keys())
        return [k for k, v in self.data.items() if v.get("scope") == scope]

    def search_memories(self, query, scope=None):
        results = []
        for memory_id, data in self.data.items():
            if scope and data.get("scope") != scope:
                continue
            if query.lower() in data["content"].lower():
                results.append(
                    {
                        "memory_id": memory_id,
                        "content": data["content"],
                        "metadata": data["metadata"],
                        "scope": data["scope"],
                    }
                )
        return results

    def get_stats(self):
        scopes = {v.get("scope") for v in self.data.values() if v.get("scope")}
        return {
            "total_memories": len(self.data),
            "total_scopes": len(scopes),
            "audit_entries": len(self.audit_log),
        }

    def get_audit_log(self, memory_id=None, limit=None):
        logs = self.audit_log
        if memory_id:
            logs = [log for log in logs if log[1] == memory_id]
        if limit:
            logs = logs[-limit:]
        return [{"action": log[0], "memory_id": log[1]} for log in logs]

    def clear_scope(self, scope):
        keys_to_delete = [k for k, v in self.data.items() if v.get("scope") == scope]
        for key in keys_to_delete:
            del self.data[key]
        return len(keys_to_delete)


def test_mock_storage_implementation():
    """Test that the mock storage implementation works."""
    storage = MockStorage()

    # Test store
    assert storage.store_memory("test1", "content1", {"key": "value"}, "scope1")

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
    assert len(results) == 1
    assert results[0]["memory_id"] == "test1"

    # Test statistics
    stats = storage.get_stats()
    assert stats["total_memories"] == 1
    assert stats["total_scopes"] == 1

    # Test delete
    assert storage.delete_memory("test1")
    assert storage.retrieve_memory("test1") is None

    # Test clear scope
    storage.store_memory("test2", "content2", scope="scope2")
    storage.store_memory("test3", "content3", scope="scope2")
    cleared = storage.clear_scope("scope2")
    assert cleared == 2
    assert len(storage.list_memories()) == 0
