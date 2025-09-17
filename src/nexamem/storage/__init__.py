"""Storage abstraction module for NexaMem.

This module provides a unified interface for different storage backends
including Azure Redis, Azure Cosmos DB, Azure Blob Storage, Azure AI Search,
in-memory, file-based, and SQLite storage.
"""

from .azure_ai_search import (
    AsyncAzureAISearchStorage,
    AsyncAzureOpenAIEmbeddingProvider,
    AsyncCustomEmbeddingProvider,
    AsyncEmbeddingProvider,
    AsyncOpenAIEmbeddingProvider,
    AzureAISearchConnectionError,
    AzureAISearchHealthCheck,
    AzureAISearchStorage,
    AzureOpenAIEmbeddingProvider,
    CustomEmbeddingProvider,
    EmbeddingProvider,
    OpenAIEmbeddingProvider,
)
from .azure_blob import (
    AsyncAzureBlobStorage,
    AzureBlobConnectionError,
    AzureBlobHealthCheck,
    AzureBlobStorage,
)
from .azure_cosmos import (
    AsyncAzureCosmosStorage,
    AzureCosmosConnectionError,
    AzureCosmosHealthCheck,
    AzureCosmosStorage,
)
from .azure_redis import (
    AsyncAzureRedisStorage,
    AzureRedisConnectionError,
    AzureRedisHealthCheck,
    AzureRedisStorage,
)
from .azure_redis_factory import (
    AccessKeyAuthProvider,
    AsyncAccessKeyAuthProvider,
    AsyncAuthenticationProvider,
    AsyncEntraIdAuthProvider,
    AsyncKeyVaultAuthProvider,
    AuthenticationProvider,
    AzureRedisStorageFactory,
    EntraIdAuthProvider,
    KeyVaultAuthProvider,
    create_azure_redis_storage,
    create_from_env,
)
from .base import BaseAsyncStorage, BaseStorage
from .factory import StorageFactory, create_storage_from_config
from .file import AsyncFileStorage, FileStorage
from .interfaces import (
    AsyncConversationMemoryAdapter,
    ConversationMemoryAdapter,
    IAsyncConversationMemory,
    IConversationMemory,
    MemoryServiceFactory,
    create_from_environment,
    create_memory_service,
)
from .memory import AsyncMemoryStorage, MemoryStorage
from .sqlite import AsyncSQLiteStorage, SQLiteStorage

# Legacy aliases for backward compatibility
StorageAdapter = BaseStorage
AsyncStorageAdapter = BaseAsyncStorage

__all__ = [
    # Base interfaces
    "BaseStorage",
    "BaseAsyncStorage",
    "StorageAdapter",  # Legacy alias
    "AsyncStorageAdapter",  # Legacy alias

    # Storage factory
    "StorageFactory",
    "create_storage_from_config",

    # Azure Redis implementations
    "AzureRedisStorage",
    "AsyncAzureRedisStorage",
    "AzureRedisConnectionError",
    "AzureRedisHealthCheck",

    # Azure Cosmos DB implementations
    "AzureCosmosStorage",
    "AsyncAzureCosmosStorage",
    "AzureCosmosConnectionError",
    "AzureCosmosHealthCheck",

    # Azure Blob Storage implementations
    "AzureBlobStorage",
    "AsyncAzureBlobStorage",
    "AzureBlobConnectionError",
    "AzureBlobHealthCheck",

    # Azure AI Search implementations
    "AsyncAzureAISearchStorage",
    "AzureAISearchStorage",
    "AzureAISearchConnectionError",
    "AzureAISearchHealthCheck",

    # Embedding providers for AI Search
    "EmbeddingProvider",
    "AsyncEmbeddingProvider",
    "OpenAIEmbeddingProvider",
    "AsyncOpenAIEmbeddingProvider",
    "AzureOpenAIEmbeddingProvider",
    "AsyncAzureOpenAIEmbeddingProvider",
    "CustomEmbeddingProvider",
    "AsyncCustomEmbeddingProvider",

    # Azure Redis factory and auth providers
    "AzureRedisStorageFactory",
    "create_azure_redis_storage",
    "create_from_env",
    "AuthenticationProvider",
    "AsyncAuthenticationProvider",
    "AccessKeyAuthProvider",
    "AsyncAccessKeyAuthProvider",
    "EntraIdAuthProvider",
    "AsyncEntraIdAuthProvider",
    "KeyVaultAuthProvider",
    "AsyncKeyVaultAuthProvider",

    # High-level interfaces for external projects
    "IConversationMemory",
    "IAsyncConversationMemory",
    "ConversationMemoryAdapter",
    "AsyncConversationMemoryAdapter",
    "MemoryServiceFactory",
    "create_memory_service",  # 3-line integration
    "create_from_environment",

    # Other storage implementations
    "MemoryStorage",
    "AsyncMemoryStorage",
    "FileStorage",
    "AsyncFileStorage",
    "SQLiteStorage",
    "AsyncSQLiteStorage",
]
