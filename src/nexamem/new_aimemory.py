"""New AIMemory implementation using dependency injection."""

import uuid
from typing import Any, Dict, List, Optional, Union

from .config.aimemory import AIMemoryConfig
from .di import DIContainer, ServiceProvider
from .storage import BaseAsyncStorage, BaseStorage, StorageFactory


class AIMemoryServiceProvider(ServiceProvider):
    """Service provider for AIMemory storage."""

    def __init__(self, config: AIMemoryConfig):
        self.config = config

    def provide(self, service_type, config: Optional[Dict[str, Any]] = None):
        """Provide storage instance based on configuration."""
        if service_type in (BaseStorage, BaseAsyncStorage):
            return StorageFactory.create_storage(
                self.config.storage,
                async_preferred=(service_type == BaseAsyncStorage)
            )
        raise ValueError(f"Cannot provide service of type {service_type}")

    def can_provide(self, service_type) -> bool:
        """Check if can provide the service type."""
        return service_type in (BaseStorage, BaseAsyncStorage)


class AIMemory:
    """Synchronous AI Memory management with dependency injection."""

    def __init__(self, config: AIMemoryConfig, container: Optional[DIContainer] = None):
        self.config = config
        self.container = container or DIContainer()

        # Register storage provider if not already registered
        if not self.container.is_registered(BaseStorage):
            provider = AIMemoryServiceProvider(config)
            self.container.register(BaseStorage, provider)

        self._storage = self.container.resolve(BaseStorage)

    def store(
        self,
        content: str,
        memory_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        scope: Optional[str] = None
    ) -> str:
        """Store a memory and return its ID."""
        if memory_id is None:
            memory_id = str(uuid.uuid4())

        success = self._storage.store_memory(
            memory_id=memory_id,
            content=content,
            metadata=metadata,
            scope=scope or self.config.default_scope
        )

        if not success:
            raise RuntimeError(f"Failed to store memory {memory_id}")

        return memory_id

    def retrieve(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a memory by ID."""
        return self._storage.retrieve_memory(memory_id)

    def delete(self, memory_id: str) -> bool:
        """Delete a memory by ID."""
        return self._storage.delete_memory(memory_id)

    def list(
        self,
        scope: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[str]:
        """List memory IDs, optionally filtered by scope."""
        return self._storage.list_memories(
            scope=scope or self.config.default_scope,
            limit=limit
        )

    def search(
        self,
        query: str,
        scope: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[str]:
        """Search memories by content."""
        return self._storage.search_memories(
            query=query,
            scope=scope or self.config.default_scope,
            limit=limit
        )

    def get_audit_log(
        self,
        memory_id: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get audit log entries."""
        return self._storage.get_audit_log(memory_id=memory_id, limit=limit)

    def get_stats(self) -> Dict[str, Any]:
        """Get storage statistics."""
        return self._storage.get_stats()

    def clear_scope(self, scope: Optional[str] = None) -> int:
        """Clear all memories in a scope. Returns number of deleted memories."""
        target_scope = scope or self.config.default_scope
        memory_ids = self.list(scope=target_scope)
        deleted_count = 0

        for memory_id in memory_ids:
            if self.delete(memory_id):
                deleted_count += 1

        return deleted_count


class AsyncAIMemory:
    """Asynchronous AI Memory management with dependency injection."""

    def __init__(self, config: AIMemoryConfig, container: Optional[DIContainer] = None):
        self.config = config
        self.container = container or DIContainer()

        # Register storage provider if not already registered
        if not self.container.is_registered(BaseAsyncStorage):
            provider = AIMemoryServiceProvider(config)
            self.container.register(BaseAsyncStorage, provider)

        self._storage = self.container.resolve(BaseAsyncStorage)

    async def store(
        self,
        content: str,
        memory_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        scope: Optional[str] = None
    ) -> str:
        """Store a memory and return its ID."""
        if memory_id is None:
            memory_id = str(uuid.uuid4())

        success = await self._storage.store_memory(
            memory_id=memory_id,
            content=content,
            metadata=metadata,
            scope=scope or self.config.default_scope
        )

        if not success:
            raise RuntimeError(f"Failed to store memory {memory_id}")

        return memory_id

    async def retrieve(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a memory by ID."""
        return await self._storage.retrieve_memory(memory_id)

    async def delete(self, memory_id: str) -> bool:
        """Delete a memory by ID."""
        return await self._storage.delete_memory(memory_id)

    async def list(
        self,
        scope: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[str]:
        """List memory IDs, optionally filtered by scope."""
        return await self._storage.list_memories(
            scope=scope or self.config.default_scope,
            limit=limit
        )

    async def search(
        self,
        query: str,
        scope: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[str]:
        """Search memories by content."""
        return await self._storage.search_memories(
            query=query,
            scope=scope or self.config.default_scope,
            limit=limit
        )

    async def get_audit_log(
        self,
        memory_id: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get audit log entries."""
        return await self._storage.get_audit_log(memory_id=memory_id, limit=limit)

    async def get_stats(self) -> Dict[str, Any]:
        """Get storage statistics."""
        return await self._storage.get_stats()

    async def clear_scope(self, scope: Optional[str] = None) -> int:
        """Clear all memories in a scope. Returns number of deleted memories."""
        target_scope = scope or self.config.default_scope
        memory_ids = await self.list(scope=target_scope)
        deleted_count = 0

        for memory_id in memory_ids:
            if await self.delete(memory_id):
                deleted_count += 1

        return deleted_count


def create_aimemory(
    config: AIMemoryConfig,
    async_preferred: bool = False,
    container: Optional[DIContainer] = None
) -> Union[AIMemory, AsyncAIMemory]:
    """Factory function to create AIMemory instances."""
    if async_preferred:
        return AsyncAIMemory(config, container)
    else:
        return AIMemory(config, container)
