"""New AIMemory implementation using dependency injection."""

import builtins
import uuid
from collections.abc import Callable
from types import TracebackType
from typing import Any, Self, TypeVar, cast

from .channels import ChannelConfig, ChannelManager
from .config.aimemory import AIMemoryConfig
from .di import DIContainer, ServiceProvider
from .memory_scope import MemoryScope
from .retention import expired, retained_metadata
from .storage import BaseAsyncStorage, BaseStorage, StorageFactory
from .telemetry import trace_async_operation, trace_operation

ServiceT = TypeVar("ServiceT")


class AIMemoryServiceProvider(ServiceProvider):
    """Service provider for AIMemory storage."""

    def __init__(self, config: AIMemoryConfig) -> None:
        self.config = config

    def provide(
        self, service_type: Callable[..., ServiceT], config: dict[str, Any] | None = None
    ) -> ServiceT:
        """Provide storage instance based on configuration."""
        if service_type in (BaseStorage, BaseAsyncStorage):
            return cast(
                "ServiceT",
                StorageFactory.create_storage(
                    self.config.storage, async_preferred=(service_type == BaseAsyncStorage)
                ),
            )
        raise ValueError(f"Cannot provide service of type {service_type}")

    def can_provide(self, service_type: Callable[..., object]) -> bool:
        """Check if can provide the service type."""
        return service_type in (BaseStorage, BaseAsyncStorage)


class AIMemory:
    """Synchronous AI Memory management with dependency injection."""

    def __init__(self, config: AIMemoryConfig, container: DIContainer | None = None) -> None:
        self.config = config
        self.container = container or DIContainer()
        self._owns_storage = not self.container.is_registered(BaseStorage)

        # Register storage provider if not already registered
        if not self.container.is_registered(BaseStorage):
            provider = AIMemoryServiceProvider(config)
            self.container.register(BaseStorage, provider)

        self._storage = self.container.resolve(BaseStorage)

        # Initialize channel manager with YAML configuration
        self.channels = ChannelManager(
            yaml_path=config.channels_yaml, strict_validation=config.strict_yaml_validation
        )

    def close(self) -> None:
        """Release storage created by this facade, not externally registered storage."""
        if self._owns_storage:
            self._storage.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()

    def _retrieve_live(self, memory_id: str) -> dict[str, Any] | None:
        record = self._storage.retrieve_memory(memory_id)
        if record is not None and expired(record):
            self._storage.delete_memory(memory_id)
            return None
        return record

    def _live_ids(self, ids: builtins.list[str], limit: int | None) -> builtins.list[str]:
        if limit is not None and limit < 0:
            raise ValueError("limit must be nonnegative")
        result = [memory_id for memory_id in ids if self._retrieve_live(memory_id) is not None]
        return result if limit is None else result[:limit]

    def purge_expired(self, scope: str | None = None) -> int:
        """Delete expired records in a scope, or all scopes when omitted."""
        deleted = 0
        for memory_id in self._storage.list_memories(scope=scope):
            record = self._storage.retrieve_memory(memory_id)
            if record is not None and expired(record) and self._storage.delete_memory(memory_id):
                deleted += 1
        return deleted

    @trace_operation("store")
    def store(
        self,
        content: str,
        memory_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        scope: str | None = None,
        *,
        ttl_sec: int | None = None,
    ) -> str:
        """Store a memory and return its ID."""
        if memory_id is None:
            memory_id = str(uuid.uuid4())

        success = self._storage.store_memory(
            memory_id=memory_id,
            content=content,
            metadata=retained_metadata(
                metadata, ttl_sec if ttl_sec is not None else self.config.default_ttl_sec
            ),
            scope=scope or self.config.default_scope,
        )

        if not success:
            raise RuntimeError(f"Failed to store memory {memory_id}")

        return memory_id

    @trace_operation("retrieve")
    def retrieve(self, memory_id: str) -> dict[str, Any] | None:
        """Retrieve a memory by ID."""
        return self._retrieve_live(memory_id)

    @trace_operation("delete")
    def delete(self, memory_id: str) -> bool:
        """Delete a memory by ID."""
        return self._storage.delete_memory(memory_id)

    @trace_operation("list")
    def list(self, scope: str | None = None, limit: int | None = None) -> list[str]:
        """List memory IDs, optionally filtered by scope."""
        return self._live_ids(
            self._storage.list_memories(scope=scope or self.config.default_scope), limit
        )

    @trace_operation("search")
    def search(
        self, query: str, scope: str | None = None, limit: int | None = None
    ) -> builtins.list[str]:
        """Search memories by content."""
        return self._live_ids(
            self._storage.search_memories(query=query, scope=scope or self.config.default_scope),
            limit,
        )

    @trace_operation("get_audit_log")
    def get_audit_log(
        self, memory_id: str | None = None, limit: int | None = None
    ) -> builtins.list[dict[str, Any]]:
        """Get audit log entries."""
        return self._storage.get_audit_log(memory_id=memory_id, limit=limit)

    @trace_operation("get_stats")
    def get_stats(self) -> dict[str, Any]:
        """Get storage statistics."""
        self.purge_expired()
        return self._storage.get_stats()

    @trace_operation("clear_scope")
    def clear_scope(self, scope: str | None = None) -> int:
        """Clear all memories in a scope. Returns number of deleted memories."""
        target_scope = scope or self.config.default_scope
        memory_ids = self.list(scope=target_scope)
        deleted_count = 0

        for memory_id in memory_ids:
            if self.delete(memory_id):
                deleted_count += 1

        return deleted_count

    def register_channel(
        self, name: str, *, ttl_sec: int, encrypt: bool = False, quota_bytes: int | None = None
    ) -> None:
        """Register a new channel at runtime."""
        self.channels.register_channel(
            name=name, ttl_sec=ttl_sec, encrypt=encrypt, quota_bytes=quota_bytes
        )

    def get_channel(self, name: str) -> ChannelConfig | None:
        """Get channel configuration by name."""
        return self.channels.get_channel(name)

    def list_channels(self) -> dict[str, ChannelConfig]:
        """List all registered channels."""
        return self.channels.list_channels()

    def channel_exists(self, name: str) -> bool:
        """Check if a channel exists."""
        return self.channels.channel_exists(name)

    # Legacy AIMemory API compatibility methods
    @trace_operation("write")
    def write(
        self,
        scope: MemoryScope,
        channel: str,
        content: str | bytes,
        *,
        pii: bool = False,
        ttl_override: int | None = None,
        auto_pii: bool = False,
    ) -> str:
        """
        Write content to a memory channel (legacy API compatibility).

        This method provides compatibility with the legacy AIMemory API
        while using the new storage backend.
        """
        # Verify channel exists
        if not self.channel_exists(channel):
            from .aimemory import ChannelNotFound

            raise ChannelNotFound(f"Channel '{channel}' not found")

        memory_id = str(uuid.uuid4())

        metadata = {
            "channel": channel,
            "scope_dict": scope.model_dump(),
            "pii": pii,
            "ttl_override": ttl_override,
            "auto_pii": auto_pii,
            "content_type": "legacy_write",
        }

        success = self._storage.store_memory(
            memory_id=memory_id,
            content=content if isinstance(content, str) else content.decode("utf-8"),
            metadata=retained_metadata(
                metadata,
                ttl_override if ttl_override is not None else self.list_channels()[channel].ttl_sec,
            ),
            scope=scope.get_key_prefix(channel),
        )

        if not success:
            raise RuntimeError(f"Failed to write to channel {channel}")

        return memory_id

    @trace_operation("read")
    def read(
        self,
        scope: MemoryScope,
        channel: str,
        *,
        since_sec: int | None = None,
        max_bytes: int | None = None,
        max_msgs: int | None = None,
        max_tokens: int | None = None,
    ) -> tuple[builtins.list[str], dict[str, Any]]:
        """
        Read messages from a memory channel (legacy API compatibility).

        Returns:
            Tuple of (messages, metadata)
        """
        # Verify channel exists
        if not self.channel_exists(channel):
            from .aimemory import ChannelNotFound

            raise ChannelNotFound(f"Channel '{channel}' not found")

        # Query memories for this scope and channel
        scope_key = scope.get_key_prefix(channel)
        memory_ids = self.list(scope=scope_key, limit=max_msgs)

        messages = []
        for memory_id in memory_ids:
            memory = self._retrieve_live(memory_id)
            if memory and memory.get("metadata", {}).get("channel") == channel:
                messages.append(memory["content"])

        metadata = {
            "channel": channel,
            "messages_returned": len(messages),
            "scope": scope_key,
            "max_msgs": max_msgs,
            "max_bytes": max_bytes,
            "max_tokens": max_tokens,
            "since_sec": since_sec,
        }

        return messages, metadata


class AsyncAIMemory:
    """Asynchronous AI Memory management with dependency injection."""

    def __init__(self, config: AIMemoryConfig, container: DIContainer | None = None) -> None:
        self.config = config
        self.container = container or DIContainer()
        self._owns_storage = not self.container.is_registered(BaseAsyncStorage)

        # Register storage provider if not already registered
        if not self.container.is_registered(BaseAsyncStorage):
            provider = AIMemoryServiceProvider(config)
            self.container.register(BaseAsyncStorage, provider)

        self._storage = self.container.resolve(BaseAsyncStorage)

        # Initialize channel manager with YAML configuration
        self.channels = ChannelManager(
            yaml_path=config.channels_yaml, strict_validation=config.strict_yaml_validation
        )

    async def aclose(self) -> None:
        """Release storage created by this facade, not externally registered storage."""
        if self._owns_storage:
            await self._storage.close()

    async def close(self) -> None:
        """Alias for aclose."""
        await self.aclose()

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self.aclose()

    async def _retrieve_live(self, memory_id: str) -> dict[str, Any] | None:
        record = await self._storage.retrieve_memory(memory_id)
        if record is not None and expired(record):
            await self._storage.delete_memory(memory_id)
            return None
        return record

    async def _live_ids(self, ids: builtins.list[str], limit: int | None) -> builtins.list[str]:
        if limit is not None and limit < 0:
            raise ValueError("limit must be nonnegative")
        result = [
            memory_id for memory_id in ids if await self._retrieve_live(memory_id) is not None
        ]
        return result if limit is None else result[:limit]

    async def purge_expired(self, scope: str | None = None) -> int:
        """Delete expired records in a scope, or all scopes when omitted."""
        deleted = 0
        for memory_id in await self._storage.list_memories(scope=scope):
            record = await self._storage.retrieve_memory(memory_id)
            if (
                record is not None
                and expired(record)
                and await self._storage.delete_memory(memory_id)
            ):
                deleted += 1
        return deleted

    @trace_async_operation("store")
    async def store(
        self,
        content: str,
        memory_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        scope: str | None = None,
        *,
        ttl_sec: int | None = None,
    ) -> str:
        """Store a memory and return its ID."""
        if memory_id is None:
            memory_id = str(uuid.uuid4())

        success = await self._storage.store_memory(
            memory_id=memory_id,
            content=content,
            metadata=retained_metadata(
                metadata, ttl_sec if ttl_sec is not None else self.config.default_ttl_sec
            ),
            scope=scope or self.config.default_scope,
        )

        if not success:
            raise RuntimeError(f"Failed to store memory {memory_id}")

        return memory_id

    @trace_async_operation("retrieve")
    async def retrieve(self, memory_id: str) -> dict[str, Any] | None:
        """Retrieve a memory by ID."""
        return await self._retrieve_live(memory_id)

    @trace_async_operation("delete")
    async def delete(self, memory_id: str) -> bool:
        """Delete a memory by ID."""
        return await self._storage.delete_memory(memory_id)

    @trace_async_operation("list")
    async def list(self, scope: str | None = None, limit: int | None = None) -> list[str]:
        """List memory IDs, optionally filtered by scope."""
        return await self._live_ids(
            await self._storage.list_memories(scope=scope or self.config.default_scope), limit
        )

    @trace_async_operation("search")
    async def search(
        self, query: str, scope: str | None = None, limit: int | None = None
    ) -> builtins.list[str]:
        """Search memories by content."""
        return await self._live_ids(
            await self._storage.search_memories(
                query=query, scope=scope or self.config.default_scope
            ),
            limit,
        )

    @trace_async_operation("get_audit_log")
    async def get_audit_log(
        self, memory_id: str | None = None, limit: int | None = None
    ) -> builtins.list[dict[str, Any]]:
        """Get audit log entries."""
        return await self._storage.get_audit_log(memory_id=memory_id, limit=limit)

    @trace_async_operation("get_stats")
    async def get_stats(self) -> dict[str, Any]:
        """Get storage statistics."""
        await self.purge_expired()
        return await self._storage.get_stats()

    @trace_async_operation("clear_scope")
    async def clear_scope(self, scope: str | None = None) -> int:
        """Clear all memories in a scope. Returns number of deleted memories."""
        target_scope = scope or self.config.default_scope
        memory_ids = await self.list(scope=target_scope)
        deleted_count = 0

        for memory_id in memory_ids:
            if await self.delete(memory_id):
                deleted_count += 1

        return deleted_count

    def register_channel(
        self, name: str, *, ttl_sec: int, encrypt: bool = False, quota_bytes: int | None = None
    ) -> None:
        """Register a new channel at runtime."""
        self.channels.register_channel(
            name=name, ttl_sec=ttl_sec, encrypt=encrypt, quota_bytes=quota_bytes
        )

    def get_channel(self, name: str) -> ChannelConfig | None:
        """Get channel configuration by name."""
        return self.channels.get_channel(name)

    def list_channels(self) -> dict[str, ChannelConfig]:
        """List all registered channels."""
        return self.channels.list_channels()

    def channel_exists(self, name: str) -> bool:
        """Check if a channel exists."""
        return self.channels.channel_exists(name)

    # Legacy AIMemory API compatibility methods
    @trace_async_operation("write")
    async def write(
        self,
        scope: MemoryScope,
        channel: str,
        content: str | bytes,
        *,
        pii: bool = False,
        ttl_override: int | None = None,
        auto_pii: bool = False,
    ) -> str:
        """
        Write content to a memory channel (legacy API compatibility).

        This method provides compatibility with the legacy AIMemory API
        while using the new storage backend.
        """
        # Verify channel exists
        if not self.channel_exists(channel):
            from .aimemory import ChannelNotFound

            raise ChannelNotFound(f"Channel '{channel}' not found")

        memory_id = str(uuid.uuid4())

        metadata = {
            "channel": channel,
            "scope_dict": scope.model_dump(),
            "pii": pii,
            "ttl_override": ttl_override,
            "auto_pii": auto_pii,
            "content_type": "legacy_write",
        }

        success = await self._storage.store_memory(
            memory_id=memory_id,
            content=content if isinstance(content, str) else content.decode("utf-8"),
            metadata=retained_metadata(
                metadata,
                ttl_override if ttl_override is not None else self.list_channels()[channel].ttl_sec,
            ),
            scope=scope.get_key_prefix(channel),
        )

        if not success:
            raise RuntimeError(f"Failed to write to channel {channel}")

        return memory_id

    @trace_async_operation("read")
    async def read(
        self,
        scope: MemoryScope,
        channel: str,
        *,
        since_sec: int | None = None,
        max_bytes: int | None = None,
        max_msgs: int | None = None,
        max_tokens: int | None = None,
    ) -> tuple[builtins.list[str], dict[str, Any]]:
        """
        Read messages from a memory channel (legacy API compatibility).

        Returns:
            Tuple of (messages, metadata)
        """
        # Verify channel exists
        if not self.channel_exists(channel):
            from .aimemory import ChannelNotFound

            raise ChannelNotFound(f"Channel '{channel}' not found")

        # Query memories for this scope and channel
        scope_key = scope.get_key_prefix(channel)
        memory_ids = await self.list(scope=scope_key, limit=max_msgs)

        messages = []
        for memory_id in memory_ids:
            memory = await self._retrieve_live(memory_id)
            if memory and memory.get("metadata", {}).get("channel") == channel:
                messages.append(memory["content"])

        metadata = {
            "channel": channel,
            "messages_returned": len(messages),
            "scope": scope_key,
            "max_msgs": max_msgs,
            "max_bytes": max_bytes,
            "max_tokens": max_tokens,
            "since_sec": since_sec,
        }

        return messages, metadata


def create_aimemory(
    config: AIMemoryConfig, async_preferred: bool = False, container: DIContainer | None = None
) -> AIMemory | AsyncAIMemory:
    """Factory function to create AIMemory instances."""
    if async_preferred:
        return AsyncAIMemory(config, container)
    else:
        return AIMemory(config, container)
