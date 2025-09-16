"""
Memory service interfaces for external project integration.
Implements SOLID principles with clear contracts and protocols.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Protocol, Union, runtime_checkable

from ..config.storage import StorageConfig


@runtime_checkable
class IConversationMemory(Protocol):
    """
    Interface for conversation memory management.
    This protocol defines the contract that external projects can implement
    to provide their own memory management logic while maintaining compatibility.
    """
    
    def store_conversation_turn(
        self,
        conversation_id: str,
        turn_data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Store a single conversation turn.
        
        Args:
            conversation_id: Unique identifier for the conversation
            turn_data: The conversation turn data (user input, assistant response, etc.)
            metadata: Optional metadata for the turn
            
        Returns:
            Turn ID for the stored turn
        """
        ...
    
    def get_conversation_history(
        self,
        conversation_id: str,
        limit: Optional[int] = None,
        since_timestamp: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """Get conversation history.
        
        Args:
            conversation_id: Unique identifier for the conversation
            limit: Maximum number of turns to return
            since_timestamp: Only return turns after this timestamp
            
        Returns:
            List of conversation turns
        """
        ...
    
    def delete_conversation(self, conversation_id: str) -> bool:
        """Delete an entire conversation.
        
        Args:
            conversation_id: Unique identifier for the conversation
            
        Returns:
            True if deleted successfully, False otherwise
        """
        ...
    
    def search_conversations(
        self,
        query: str,
        user_id: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[str]:
        """Search conversations by content.
        
        Args:
            query: Search query string
            user_id: Optional user ID to filter by
            limit: Maximum number of results
            
        Returns:
            List of conversation IDs matching the query
        """
        ...


@runtime_checkable  
class IAsyncConversationMemory(Protocol):
    """Async version of the conversation memory interface."""
    
    async def store_conversation_turn(
        self,
        conversation_id: str,
        turn_data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Store a single conversation turn (async)."""
        ...
    
    async def get_conversation_history(
        self,
        conversation_id: str,
        limit: Optional[int] = None,
        since_timestamp: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """Get conversation history (async)."""
        ...
    
    async def delete_conversation(self, conversation_id: str) -> bool:
        """Delete an entire conversation (async)."""
        ...
    
    async def search_conversations(
        self,
        query: str,
        user_id: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[str]:
        """Search conversations by content (async)."""
        ...


class ConversationMemoryAdapter:
    """
    Adapter that implements IConversationMemory using NexaMem storage backends.
    This allows external projects to use the conversation memory interface
    while leveraging any of the supported storage backends.
    """
    
    def __init__(self, storage_config: StorageConfig):
        """Initialize with storage configuration."""
        from .factory import StorageFactory
        self.storage = StorageFactory.create_sync_storage(storage_config)
        self.config = storage_config
    
    def store_conversation_turn(
        self,
        conversation_id: str,
        turn_data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Store a conversation turn using the underlying storage."""
        import time
        import uuid
        
        turn_id = str(uuid.uuid4())
        turn_data_with_id = {
            'turn_id': turn_id,
            'conversation_id': conversation_id,
            'timestamp': time.time(),
            'data': turn_data,
            'metadata': metadata or {}
        }
        
        # Use conversation_id as scope for organization
        success = self.storage.store_memory(
            turn_id,
            str(turn_data),  # Convert to string for storage
            turn_data_with_id,
            conversation_id
        )
        
        if success:
            return turn_id
        else:
            raise RuntimeError(f"Failed to store conversation turn for conversation {conversation_id}")
    
    def get_conversation_history(
        self,
        conversation_id: str,
        limit: Optional[int] = None,
        since_timestamp: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """Get conversation history from storage."""
        # Get all memories for this conversation (scope)
        memory_ids = self.storage.list_memories(scope=conversation_id, limit=limit)
        
        turns = []
        for memory_id in memory_ids:
            memory_data = self.storage.retrieve_memory(memory_id)
            if memory_data:
                # The metadata field contains our structured data
                turn_metadata = memory_data.get('metadata', {})
                # Filter by timestamp if specified
                if since_timestamp and turn_metadata.get('timestamp', 0) < since_timestamp:
                    continue
                turns.append(turn_metadata)
        
        # Sort by timestamp
        turns.sort(key=lambda x: x.get('timestamp', 0))
        
        return turns
    
    def delete_conversation(self, conversation_id: str) -> bool:
        """Delete all turns for a conversation."""
        memory_ids = self.storage.list_memories(scope=conversation_id)
        
        success_count = 0
        for memory_id in memory_ids:
            if self.storage.delete_memory(memory_id):
                success_count += 1
        
        return success_count == len(memory_ids)
    
    def search_conversations(
        self,
        query: str,
        user_id: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[str]:
        """Search conversations by content."""
        # Search across all memories
        matching_memory_ids = self.storage.search_memories(query, limit=limit)
        
        # Extract unique conversation IDs
        conversation_ids = set()
        for memory_id in matching_memory_ids:
            memory_data = self.storage.retrieve_memory(memory_id)
            if memory_data:
                # Check both content and metadata for conversation_id
                turn_metadata = memory_data.get('metadata', {})
                conv_id = turn_metadata.get('conversation_id')
                if conv_id:
                    # Filter by user_id if specified
                    if user_id:
                        metadata = turn_metadata.get('metadata', {})
                        if metadata.get('user_id') != user_id:
                            continue
                    conversation_ids.add(conv_id)
        
        return list(conversation_ids)[:limit] if limit else list(conversation_ids)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get conversation statistics."""
        base_stats = self.storage.get_stats()
        return {
            **base_stats,
            'adapter_type': 'conversation_memory',
            'total_conversations': base_stats.get('total_scopes', 0)
        }


class AsyncConversationMemoryAdapter:
    """
    Async version of the conversation memory adapter.
    """
    
    def __init__(self, storage_config: StorageConfig):
        """Initialize with storage configuration."""
        from .factory import StorageFactory
        self.storage = StorageFactory.create_async_storage(storage_config)
        self.config = storage_config
    
    async def store_conversation_turn(
        self,
        conversation_id: str,
        turn_data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Store a conversation turn using the underlying storage (async)."""
        import time
        import uuid
        
        turn_id = str(uuid.uuid4())
        turn_data_with_id = {
            'turn_id': turn_id,
            'conversation_id': conversation_id,
            'timestamp': time.time(),
            'data': turn_data,
            'metadata': metadata or {}
        }
        
        # Use conversation_id as scope for organization
        success = await self.storage.store_memory(
            turn_id,
            str(turn_data),  # Convert to string for storage
            turn_data_with_id,
            conversation_id
        )
        
        if success:
            return turn_id
        else:
            raise RuntimeError(f"Failed to store conversation turn for conversation {conversation_id}")
    
    async def get_conversation_history(
        self,
        conversation_id: str,
        limit: Optional[int] = None,
        since_timestamp: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """Get conversation history from storage (async)."""
        # Get all memories for this conversation (scope)
        memory_ids = await self.storage.list_memories(scope=conversation_id, limit=limit)
        
        turns = []
        for memory_id in memory_ids:
            memory_data = await self.storage.retrieve_memory(memory_id)
            if memory_data:
                # The metadata field contains our structured data
                turn_metadata = memory_data.get('metadata', {})
                # Filter by timestamp if specified
                if since_timestamp and turn_metadata.get('timestamp', 0) < since_timestamp:
                    continue
                turns.append(turn_metadata)
        
        # Sort by timestamp
        turns.sort(key=lambda x: x.get('timestamp', 0))
        
        return turns
    
    async def delete_conversation(self, conversation_id: str) -> bool:
        """Delete all turns for a conversation (async)."""
        memory_ids = await self.storage.list_memories(scope=conversation_id)
        
        success_count = 0
        for memory_id in memory_ids:
            if await self.storage.delete_memory(memory_id):
                success_count += 1
        
        return success_count == len(memory_ids)
    
    async def search_conversations(
        self,
        query: str,
        user_id: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[str]:
        """Search conversations by content (async)."""
        # Search across all memories
        matching_memory_ids = await self.storage.search_memories(query, limit=limit)
        
        # Extract unique conversation IDs
        conversation_ids = set()
        for memory_id in matching_memory_ids:
            memory_data = await self.storage.retrieve_memory(memory_id)
            if memory_data:
                # Check both content and metadata for conversation_id
                turn_metadata = memory_data.get('metadata', {})
                conv_id = turn_metadata.get('conversation_id')
                if conv_id:
                    # Filter by user_id if specified
                    if user_id:
                        metadata = turn_metadata.get('metadata', {})
                        if metadata.get('user_id') != user_id:
                            continue
                    conversation_ids.add(conv_id)
        
        return list(conversation_ids)[:limit] if limit else list(conversation_ids)
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get conversation statistics (async)."""
        base_stats = await self.storage.get_stats()
        return {
            **base_stats,
            'adapter_type': 'async_conversation_memory',
            'total_conversations': base_stats.get('total_scopes', 0)
        }


class MemoryServiceFactory:
    """
    Factory for creating memory service instances with different backends.
    Implements the factory pattern to support multiple storage backends
    while providing a unified interface for external projects.
    """
    
    @staticmethod
    def create_conversation_memory(
        storage_config: StorageConfig,
        async_preferred: bool = True
    ) -> Union[ConversationMemoryAdapter, AsyncConversationMemoryAdapter]:
        """Create conversation memory adapter with specified backend."""
        if async_preferred:
            return AsyncConversationMemoryAdapter(storage_config)
        else:
            return ConversationMemoryAdapter(storage_config)
    
    @staticmethod
    def create_azure_redis_conversation_memory(
        hostname: str,
        access_key: str,
        async_preferred: bool = True,
        **kwargs
    ) -> Union[ConversationMemoryAdapter, AsyncConversationMemoryAdapter]:
        """Create conversation memory with Azure Redis backend."""
        from ..config.storage import StorageConfig, AzureRedisConfig, AzureAuthMethod
        
        azure_config = AzureRedisConfig(
            hostname=hostname,
            access_key=access_key,
            auth_method=AzureAuthMethod.ACCESS_KEY,
            **kwargs
        )
        storage_config = StorageConfig.azure_redis(azure_config)
        
        return MemoryServiceFactory.create_conversation_memory(storage_config, async_preferred)
    
    @staticmethod
    def create_from_env(async_preferred: bool = True) -> Union[ConversationMemoryAdapter, AsyncConversationMemoryAdapter]:
        """Create conversation memory from environment variables."""
        from ..config.storage import StorageConfig
        
        storage_config = StorageConfig.from_env()
        return MemoryServiceFactory.create_conversation_memory(storage_config, async_preferred)


# Convenience functions for 3-line integration
def create_memory_service(
    storage_type: str = "memory",
    async_preferred: bool = True,
    **config_kwargs
) -> Union[ConversationMemoryAdapter, AsyncConversationMemoryAdapter]:
    """
    Convenience function for 3-line integration.
    
    Example usage for external projects:
    ```python
    # Line 1: Import
    from nexamem.storage.interfaces import create_memory_service
    
    # Line 2: Create service
    memory = create_memory_service("azure_redis", hostname="your-cache.redis.cache.windows.net", access_key="your-key")
    
    # Line 3: Use service
    turn_id = memory.store_conversation_turn("conv1", {"user": "Hello", "assistant": "Hi there!"})
    ```
    """
    from ..config.storage import StorageConfig
    
    if storage_type == "azure_redis":
        return MemoryServiceFactory.create_azure_redis_conversation_memory(async_preferred=async_preferred, **config_kwargs)
    elif storage_type == "memory":
        storage_config = StorageConfig.memory()
        return MemoryServiceFactory.create_conversation_memory(storage_config, async_preferred)
    elif storage_type == "file":
        path = config_kwargs.get("path", "memory_data.json")
        storage_config = StorageConfig.file(path)
        return MemoryServiceFactory.create_conversation_memory(storage_config, async_preferred)
    elif storage_type == "sqlite":
        path = config_kwargs.get("path", "memory_data.db")
        storage_config = StorageConfig.sqlite(path)
        return MemoryServiceFactory.create_conversation_memory(storage_config, async_preferred)
    else:
        raise ValueError(f"Unsupported storage type: {storage_type}")


def create_from_environment(async_preferred: bool = True) -> Union[ConversationMemoryAdapter, AsyncConversationMemoryAdapter]:
    """Create memory service from environment variables."""
    return MemoryServiceFactory.create_from_env(async_preferred)