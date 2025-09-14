"""Service factory for external project integration.

This module provides factory patterns and interfaces for integrating NexaMem
into external projects with minimal coupling and maximum flexibility.
"""

import os
from typing import Dict, Any, Protocol, Optional, Union, List
from .config.aimemory import AIMemoryConfig
from .config.storage import StorageConfig, AzureRedisConfig
from .new_aimemory import AIMemory, AsyncAIMemory
from .memory_scope import MemoryScope


class IConversationMemory(Protocol):
    """Standard interface for conversation memory services.
    
    This protocol defines the contract that conversation memory services
    should implement for external integration.
    """
    
    async def store_turn(
        self, 
        conversation_id: str, 
        content: str, 
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Store a conversation turn.
        
        Args:
            conversation_id: Unique identifier for the conversation
            content: The conversation content to store
            metadata: Optional metadata (user_id, timestamp, etc.)
            
        Returns:
            Unique identifier for the stored turn
        """
        ...
    
    async def get_history(
        self, 
        conversation_id: str, 
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get conversation history.
        
        Args:
            conversation_id: Unique identifier for the conversation
            limit: Maximum number of turns to retrieve
            
        Returns:
            List of conversation turns with metadata
        """
        ...
    
    async def search_conversations(
        self, 
        query: str, 
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search across conversations.
        
        Args:
            query: Search query string
            limit: Maximum number of results
            
        Returns:
            List of matching conversation turns
        """
        ...


class ConversationMemoryAdapter:
    """Adapter that implements IConversationMemory using NexaMem."""
    
    def __init__(self, ai_memory: Union[AIMemory, AsyncAIMemory]):
        self.ai_memory = ai_memory
        self._is_async = isinstance(ai_memory, AsyncAIMemory)
    
    async def store_turn(
        self, 
        conversation_id: str, 
        content: str, 
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Store a conversation turn using NexaMem."""
        # Create enriched metadata
        enriched_metadata = {
            "conversation_id": conversation_id,
            "type": "conversation_turn",
            **(metadata or {})
        }
        
        if self._is_async:
            return await self.ai_memory.store(
                content=content,
                metadata=enriched_metadata,
                scope=conversation_id
            )
        else:
            return self.ai_memory.store(
                content=content,
                metadata=enriched_metadata,
                scope=conversation_id
            )
    
    async def get_history(
        self, 
        conversation_id: str, 
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get conversation history using NexaMem."""
        if self._is_async:
            memory_ids = await self.ai_memory.list(
                scope=conversation_id,
                limit=limit
            )
            
            history = []
            for memory_id in memory_ids:
                memory = await self.ai_memory.retrieve(memory_id)
                if memory:
                    history.append({
                        "id": memory_id,
                        "content": memory["content"],
                        "metadata": memory.get("metadata", {}),
                        "timestamp": memory.get("created_at")
                    })
            return history
        else:
            memory_ids = self.ai_memory.list(
                scope=conversation_id,
                limit=limit
            )
            
            history = []
            for memory_id in memory_ids:
                memory = self.ai_memory.retrieve(memory_id)
                if memory:
                    history.append({
                        "id": memory_id,
                        "content": memory["content"],
                        "metadata": memory.get("metadata", {}),
                        "timestamp": memory.get("created_at")
                    })
            return history
    
    async def search_conversations(
        self, 
        query: str, 
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search across conversations using NexaMem."""
        if self._is_async:
            memory_ids = await self.ai_memory.search(
                query=query,
                limit=limit
            )
            
            results = []
            for memory_id in memory_ids:
                memory = await self.ai_memory.retrieve(memory_id)
                if memory:
                    results.append({
                        "id": memory_id,
                        "content": memory["content"],
                        "metadata": memory.get("metadata", {}),
                        "conversation_id": memory.get("scope"),
                        "timestamp": memory.get("created_at")
                    })
            return results
        else:
            memory_ids = self.ai_memory.search(
                query=query,
                limit=limit
            )
            
            results = []
            for memory_id in memory_ids:
                memory = self.ai_memory.retrieve(memory_id)
                if memory:
                    results.append({
                        "id": memory_id,
                        "content": memory["content"],
                        "metadata": memory.get("metadata", {}),
                        "conversation_id": memory.get("scope"),
                        "timestamp": memory.get("created_at")
                    })
            return results


class MemoryServiceFactory:
    """Factory for creating memory services for external integration.
    
    This factory provides multiple patterns for integrating NexaMem into
    external projects with different architectural preferences.
    """
    
    @staticmethod
    def create_conversation_memory(
        service_type: str = "azure_redis",
        config: Optional[Dict[str, Any]] = None,
        async_preferred: bool = True
    ) -> ConversationMemoryAdapter:
        """Create a conversation memory service.
        
        Args:
            service_type: Type of storage backend ("azure_redis", "memory", "file", "sqlite")
            config: Configuration dictionary
            async_preferred: Whether to create async or sync implementation
            
        Returns:
            ConversationMemoryAdapter implementing IConversationMemory
        """
        config = config or {}
        
        # Build storage configuration
        storage_config = MemoryServiceFactory._build_storage_config(service_type, config)
        
        # Build AI Memory configuration
        ai_config = AIMemoryConfig(
            default_scope=config.get("default_scope", "conversation"),
            storage=storage_config,
            channels_yaml=config.get("channels_yaml"),
            strict_yaml_validation=config.get("strict_validation", True),
            enable_audit=config.get("enable_audit", True),
            enable_metrics=config.get("enable_metrics", True)
        )
        
        # Create appropriate AI Memory implementation
        if async_preferred:
            ai_memory = AsyncAIMemory(ai_config)
        else:
            ai_memory = AIMemory(ai_config)
        
        return ConversationMemoryAdapter(ai_memory)
    
    @staticmethod
    def create_from_env(async_preferred: bool = True) -> ConversationMemoryAdapter:
        """Create service from environment variables.
        
        Environment variables:
        - NEXAMEM_SERVICE_TYPE: Storage type (azure_redis, memory, file, sqlite)
        - NEXAMEM_DEFAULT_SCOPE: Default scope for conversations
        - NEXAMEM_CHANNELS_YAML: Path to channels YAML configuration
        - AZURE_REDIS_HOSTNAME: Azure Redis hostname
        - AZURE_REDIS_ACCESS_KEY: Azure Redis access key
        
        Args:
            async_preferred: Whether to create async or sync implementation
            
        Returns:
            ConversationMemoryAdapter implementing IConversationMemory
        """
        service_type = os.getenv("NEXAMEM_SERVICE_TYPE", "memory")
        
        config = {
            "default_scope": os.getenv("NEXAMEM_DEFAULT_SCOPE", "conversation"),
            "channels_yaml": os.getenv("NEXAMEM_CHANNELS_YAML"),
            "strict_validation": os.getenv("NEXAMEM_STRICT_VALIDATION", "true").lower() == "true",
            "enable_audit": os.getenv("NEXAMEM_ENABLE_AUDIT", "true").lower() == "true",
            "enable_metrics": os.getenv("NEXAMEM_ENABLE_METRICS", "true").lower() == "true"
        }
        
        # Add service-specific config from environment
        if service_type == "azure_redis":
            config.update({
                "redis_hostname": os.getenv("AZURE_REDIS_HOSTNAME"),
                "redis_access_key": os.getenv("AZURE_REDIS_ACCESS_KEY"),
                "redis_port": int(os.getenv("AZURE_REDIS_PORT", "6380")),
                "redis_ssl": os.getenv("AZURE_REDIS_SSL", "true").lower() == "true"
            })
        elif service_type == "file":
            config["file_path"] = os.getenv("NEXAMEM_FILE_PATH", "./nexamem_data")
        elif service_type == "sqlite":
            config["sqlite_path"] = os.getenv("NEXAMEM_SQLITE_PATH", "./nexamem.db")
        
        return MemoryServiceFactory.create_conversation_memory(
            service_type=service_type,
            config=config,
            async_preferred=async_preferred
        )
    
    @staticmethod
    def create_ai_memory(
        service_type: str = "azure_redis",
        config: Optional[Dict[str, Any]] = None,
        async_preferred: bool = True
    ) -> Union[AIMemory, AsyncAIMemory]:
        """Create raw AIMemory instance for advanced usage.
        
        Args:
            service_type: Type of storage backend
            config: Configuration dictionary  
            async_preferred: Whether to create async or sync implementation
            
        Returns:
            AIMemory or AsyncAIMemory instance
        """
        config = config or {}
        
        storage_config = MemoryServiceFactory._build_storage_config(service_type, config)
        ai_config = AIMemoryConfig(
            default_scope=config.get("default_scope", "default"),
            storage=storage_config,
            channels_yaml=config.get("channels_yaml"),
            strict_yaml_validation=config.get("strict_validation", True)
        )
        
        if async_preferred:
            return AsyncAIMemory(ai_config)
        else:
            return AIMemory(ai_config)
    
    @staticmethod
    def _build_storage_config(service_type: str, config: Dict[str, Any]) -> StorageConfig:
        """Build storage configuration based on service type."""
        if service_type == "azure_redis":
            if not config.get("redis_hostname"):
                raise ValueError("redis_hostname required for azure_redis service type")
            if not config.get("redis_access_key"):
                raise ValueError("redis_access_key required for azure_redis service type")
            
            redis_config = AzureRedisConfig(
                hostname=config["redis_hostname"],
                access_key=config["redis_access_key"],
                port=config.get("redis_port", 6380),
                ssl=config.get("redis_ssl", True),
                collection_prefix=config.get("redis_prefix", "nexamem")
            )
            return StorageConfig.azure_redis(redis_config)
        
        elif service_type == "memory":
            return StorageConfig.memory()
        
        elif service_type == "file":
            return StorageConfig.file(config.get("file_path", "./nexamem_data"))
        
        elif service_type == "sqlite":
            return StorageConfig.sqlite(config.get("sqlite_path", "./nexamem.db"))
        
        else:
            raise ValueError(f"Unknown service type: {service_type}")


# Convenience aliases for common usage patterns
def create_conversation_memory(**kwargs) -> ConversationMemoryAdapter:
    """Convenience function to create conversation memory service."""
    return MemoryServiceFactory.create_conversation_memory(**kwargs)


def create_from_environment(**kwargs) -> ConversationMemoryAdapter:
    """Convenience function to create service from environment."""
    return MemoryServiceFactory.create_from_env(**kwargs)


def create_ai_memory(**kwargs) -> Union[AIMemory, AsyncAIMemory]:
    """Convenience function to create AI memory instance."""
    return MemoryServiceFactory.create_ai_memory(**kwargs)