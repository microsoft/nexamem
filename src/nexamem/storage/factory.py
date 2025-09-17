"""Storage factory for dependency injection."""

from typing import Union

from ..config.storage import StorageConfig
from .azure_redis import AsyncAzureRedisStorage, AzureRedisStorage
from .azure_cosmos import AsyncAzureCosmosStorage, AzureCosmosStorage
from .azure_blob import AsyncAzureBlobStorage, AzureBlobStorage
from .azure_ai_search import AsyncAzureAISearchStorage, AzureAISearchStorage
from .base import BaseAsyncStorage, BaseStorage
from .file import AsyncFileStorage, FileStorage
from .memory import AsyncMemoryStorage, MemoryStorage
from .sqlite import AsyncSQLiteStorage, SQLiteStorage


class StorageFactory:
    """Factory for creating storage instances based on configuration."""

    @staticmethod
    def create_sync_storage(config: StorageConfig) -> BaseStorage:
        """Create a synchronous storage instance based on configuration."""
        if config.type.value == "azure_redis":
            return AzureRedisStorage(config.config)
        elif config.type.value == "azure_cosmos":
            return AzureCosmosStorage(config.config)
        elif config.type.value == "azure_blob":
            return AzureBlobStorage(config.config)
        elif config.type.value == "azure_ai_search":
            return AzureAISearchStorage(config.config)
        elif config.type.value == "memory":
            return MemoryStorage()
        elif config.type.value == "file":
            return FileStorage(config.config.path)
        elif config.type.value == "sqlite":
            return SQLiteStorage(config.config.path)
        else:
            raise ValueError(f"Unsupported storage type: {config.type}")

    @staticmethod
    def create_async_storage(config: StorageConfig) -> BaseAsyncStorage:
        """Create an asynchronous storage instance based on configuration."""
        if config.type.value == "azure_redis":
            return AsyncAzureRedisStorage(config.config)
        elif config.type.value == "azure_cosmos":
            return AsyncAzureCosmosStorage(config.config)
        elif config.type.value == "azure_blob":
            return AsyncAzureBlobStorage(config.config)
        elif config.type.value == "azure_ai_search":
            return AsyncAzureAISearchStorage(config.config)
        elif config.type.value == "memory":
            return AsyncMemoryStorage()
        elif config.type.value == "file":
            return AsyncFileStorage(config.config.path)
        elif config.type.value == "sqlite":
            return AsyncSQLiteStorage(config.config.path)
        else:
            raise ValueError(f"Unsupported storage type: {config.type}")

    @staticmethod
    def create_storage(
        config: StorageConfig,
        async_preferred: bool = True
    ) -> Union[BaseStorage, BaseAsyncStorage]:
        """Create a storage instance, preferring async if specified."""
        if async_preferred:
            return StorageFactory.create_async_storage(config)
        else:
            return StorageFactory.create_sync_storage(config)


def create_storage_from_config(
    config: StorageConfig,
    async_preferred: bool = True
) -> Union[BaseStorage, BaseAsyncStorage]:
    """Convenience function to create storage from config."""
    return StorageFactory.create_storage(config, async_preferred)
