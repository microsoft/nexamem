"""Storage factory for dependency injection."""

from ..config.storage import AzureRedisConfig, FileConfig, SQLiteConfig, StorageConfig
from .azure_redis import AsyncAzureRedisStorage, AzureRedisStorage
from .base import BaseAsyncStorage, BaseStorage
from .file import AsyncFileStorage, FileStorage
from .memory import AsyncMemoryStorage, MemoryStorage
from .sqlite import AsyncSQLiteStorage, SQLiteStorage


class StorageFactory:
    """Factory for creating storage instances based on configuration."""

    @staticmethod
    def create_sync_storage(config: StorageConfig) -> BaseStorage:
        """Create a synchronous storage instance based on configuration."""
        if config.type.value == "azure_redis" and isinstance(config.config, AzureRedisConfig):
            return AzureRedisStorage(config.config)
        elif config.type.value == "memory":
            return MemoryStorage()
        elif config.type.value == "file" and isinstance(config.config, FileConfig):
            return FileStorage(config.config.path)
        elif config.type.value == "sqlite" and isinstance(config.config, SQLiteConfig):
            return SQLiteStorage(config.config.path)
        else:
            raise ValueError(f"Unsupported storage type: {config.type}")

    @staticmethod
    def create_async_storage(config: StorageConfig) -> BaseAsyncStorage:
        """Create an asynchronous storage instance based on configuration."""
        if config.type.value == "azure_redis" and isinstance(config.config, AzureRedisConfig):
            return AsyncAzureRedisStorage(config.config)
        elif config.type.value == "memory":
            return AsyncMemoryStorage()
        elif config.type.value == "file" and isinstance(config.config, FileConfig):
            return AsyncFileStorage(config.config.path)
        elif config.type.value == "sqlite" and isinstance(config.config, SQLiteConfig):
            return AsyncSQLiteStorage(config.config.path)
        else:
            raise ValueError(f"Unsupported storage type: {config.type}")

    @staticmethod
    def create_storage(
        config: StorageConfig, async_preferred: bool = True
    ) -> BaseStorage | BaseAsyncStorage:
        """Create a storage instance, preferring async if specified."""
        if async_preferred:
            return StorageFactory.create_async_storage(config)
        else:
            return StorageFactory.create_sync_storage(config)


def create_storage_from_config(
    config: StorageConfig, async_preferred: bool = True
) -> BaseStorage | BaseAsyncStorage:
    """Convenience function to create storage from config."""
    return StorageFactory.create_storage(config, async_preferred)
