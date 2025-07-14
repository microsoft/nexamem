"""Storage abstraction module for NexaMem.

This module provides a unified interface for different storage backends
including Azure Redis, in-memory, file-based, and SQLite storage.
"""

from .azure_redis import AsyncAzureRedisStorage, AzureRedisStorage
from .base import BaseAsyncStorage, BaseStorage
from .factory import StorageFactory, create_storage_from_config
from .file import AsyncFileStorage, FileStorage
from .memory import AsyncMemoryStorage, MemoryStorage
from .sqlite import AsyncSQLiteStorage, SQLiteStorage

__all__ = [
    # Base interfaces
    "BaseStorage",
    "BaseAsyncStorage",
    # Storage implementations
    "AzureRedisStorage",
    "AsyncAzureRedisStorage",
    "MemoryStorage",
    "AsyncMemoryStorage",
    "FileStorage",
    "AsyncFileStorage",
    "SQLiteStorage",
    "AsyncSQLiteStorage",
    # Factory
    "StorageFactory",
    "create_storage_from_config",
]
