# NexaMem New Architecture Guide

This document describes the new dependency injection-based architecture for NexaMem, featuring Azure Cache for Redis as the primary backend with async-first design patterns.

## Overview

The new NexaMem architecture provides:

- **Dependency Injection (DI)**: Modular, testable, and flexible design
- **Azure Cache for Redis Primary**: Optimized for Azure Cache for Redis with proper collection usage
- **Async-First**: Preferred async operations with sync fallbacks
- **Multiple Storage Backends**: Memory, File, SQLite, and Azure Redis
- **Pydantic Configuration**: Type-safe configuration with validation
- **Enterprise-Ready**: Designed for production use

## Quick Start

```python
import asyncio
from nexamem import (
    AIMemory, AsyncAIMemory, 
    AIMemoryConfig, StorageConfig
)

# Simple in-memory setup
config = AIMemoryConfig(
    default_scope="my_app",
    storage=StorageConfig.memory()
)

# Async usage (recommended)
async def async_example():
    ai_memory = AsyncAIMemory(config)
    
    # Store a memory
    memory_id = await ai_memory.store(
        "User asked about Python best practices",
        metadata={"topic": "programming", "language": "python"}
    )
    
    # Retrieve it
    memory = await ai_memory.retrieve(memory_id)
    print(f"Retrieved: {memory['content']}")
    
    # Search memories
    results = await ai_memory.search("Python")
    print(f"Found {len(results)} Python-related memories")

# Sync usage
def sync_example():
    ai_memory = AIMemory(config)
    
    memory_id = ai_memory.store("Hello World")
    memory = ai_memory.retrieve(memory_id)
    print(f"Retrieved: {memory['content']}")

# Run examples
asyncio.run(async_example())
sync_example()
```

## Configuration Examples

### Azure Cache for Redis (Primary Backend)

```python
from nexamem import AIMemoryConfig, StorageConfig, AzureRedisConfig

config = AIMemoryConfig(
    default_scope="production_chatbot",
    storage=StorageConfig.azure_redis(AzureRedisConfig(
        hostname="your-cache.redis.cache.windows.net",
        port=6380,
        access_key="your-access-key",
        ssl=True,
        key_prefix="nexamem:",
        memory_collection="memories",
        index_collection="memory_indexes",
        audit_stream="memory_audit"
    ))
)
```

### File Storage

```python
config = AIMemoryConfig(
    default_scope="file_session",
    storage=StorageConfig.file("./nexamem_data")
)
```

### SQLite Storage

```python
config = AIMemoryConfig(
    default_scope="sqlite_session", 
    storage=StorageConfig.sqlite("./nexamem.db")
)
```

### In-Memory Storage

```python
config = AIMemoryConfig(
    default_scope="test_session",
    storage=StorageConfig.memory()
)
```

## Architecture Components

### Storage Layer

The storage layer provides a unified interface across different backends:

- **BaseStorage / BaseAsyncStorage**: Core storage interfaces
- **AzureRedisStorage**: Azure Cache for Redis implementation
- **MemoryStorage**: In-memory implementation  
- **FileStorage**: File-based implementation
- **SQLiteStorage**: SQLite database implementation
- **StorageFactory**: Factory for creating storage instances

### Configuration Layer

Pydantic-based configuration provides type safety and validation:

- **AIMemoryConfig**: Main configuration model
- **StorageConfig**: Unified storage configuration
- **AzureRedisConfig**: Azure Redis specific config
- **FileConfig, SQLiteConfig, MemoryConfig**: Backend-specific configs

### Dependency Injection

The DI system enables flexible, testable architecture:

- **DIContainer**: Main dependency injection container
- **ServiceProvider**: Interface for service providers
- **ServiceRegistry**: Registry for managing providers

### AIMemory Classes

New DI-aware AIMemory implementations:

- **AsyncAIMemory**: Async-first memory management
- **AIMemory**: Synchronous memory management
- **create_aimemory()**: Factory function

## Storage Interface

All storage backends implement the same interface:

```python
# Store a memory
success = await storage.store_memory(
    memory_id="unique-id",
    content="Memory content",
    metadata={"key": "value"},
    scope="optional-scope"
)

# Retrieve a memory
memory = await storage.retrieve_memory("unique-id")

# Delete a memory  
success = await storage.delete_memory("unique-id")

# List memories
memory_ids = await storage.list_memories(scope="optional", limit=10)

# Search memories
results = await storage.search_memories("query", scope="optional", limit=10)

# Audit logging
audit_entries = await storage.get_audit_log(memory_id="optional", limit=10)

# Statistics
stats = await storage.get_stats()
```

## Azure Redis Implementation Details

The Azure Redis storage is optimized for Azure Cache for Redis:

- **Collections over Keys**: Uses Redis Sets/Lists instead of top-level keys
- **Efficient Indexing**: Scope-based indexing with Redis Sets
- **Audit Streams**: Uses Redis Streams for audit logging
- **Connection Pooling**: Efficient connection management
- **Legacy Fallback**: Supports existing key structures

### Redis Data Structure

```
nexamem:memories          -> Hash of all memories
nexamem:memory_indexes    -> Hash of scope indexes  
nexamem:memory_audit      -> Stream for audit events
```

## Migration from Legacy API

The new API maintains backward compatibility while providing enhanced features:

```python
# Legacy (still works)
from nexamem import LegacyAIMemory, LegacyAsyncAIMemory

# New (recommended)  
from nexamem import AIMemory, AsyncAIMemory, AIMemoryConfig, StorageConfig

# Migration example
def migrate_to_new_api():
    # Old way
    # nexamem.initialize({"history_storage": "memory"})
    # ai_memory = LegacyAIMemory()
    
    # New way
    config = AIMemoryConfig(
        default_scope="migrated_app",
        storage=StorageConfig.memory()
    )
    ai_memory = AIMemory(config)
    
    return ai_memory
```

## Advanced Usage

### Custom DI Container

```python
from nexamem import DIContainer, AIMemory, AIMemoryConfig

# Create custom container
container = DIContainer()
container.set_config({"custom_setting": "value"})

# Use with AIMemory
config = AIMemoryConfig(...)
ai_memory = AIMemory(config, container=container)
```

### Custom Storage Provider

```python
from nexamem.di import ServiceProvider
from nexamem.storage import BaseAsyncStorage

class CustomStorageProvider(ServiceProvider):
    def provide(self, service_type, config=None):
        if service_type == BaseAsyncStorage:
            return MyCustomStorage(config)
        raise ValueError(f"Cannot provide {service_type}")
    
    def can_provide(self, service_type):
        return service_type == BaseAsyncStorage

# Register custom provider
container.register(BaseAsyncStorage, CustomStorageProvider())
```

### Environment Configuration

```python
# Set environment variables
import os
os.environ['NEXAMEM_STORAGE_TYPE'] = 'azure_redis'
os.environ['NEXAMEM_AZURE_HOSTNAME'] = 'your-cache.redis.cache.windows.net'
os.environ['NEXAMEM_AZURE_ACCESS_KEY'] = 'your-key'

# Create config from environment
config = AIMemoryConfig(
    default_scope="env_app",
    storage=StorageConfig.from_env()
)
```

## Testing

The new architecture is designed for easy testing:

```python
import pytest
from nexamem import AIMemoryConfig, StorageConfig, AsyncAIMemory

@pytest.fixture
async def ai_memory():
    config = AIMemoryConfig(
        default_scope="test",
        storage=StorageConfig.memory()  # Use in-memory for tests
    )
    return AsyncAIMemory(config)

async def test_memory_operations(ai_memory):
    # Test storage
    memory_id = await ai_memory.store("Test content")
    assert memory_id is not None
    
    # Test retrieval
    memory = await ai_memory.retrieve(memory_id)
    assert memory['content'] == "Test content"
    
    # Test search
    results = await ai_memory.search("Test")
    assert memory_id in results
```

## Performance Considerations

- **Async Preferred**: Use `AsyncAIMemory` for better concurrency
- **Connection Pooling**: Azure Redis uses connection pooling by default
- **Batch Operations**: Consider batching for high-volume scenarios
- **Scope Usage**: Use scopes to partition data and improve query performance
- **Indexing**: Azure Redis implementation uses efficient indexing

## Error Handling

```python
from nexamem import AIMemory, AIMemoryConfig

try:
    ai_memory = AIMemory(config)
    memory_id = ai_memory.store("Content")
except Exception as e:
    print(f"Storage error: {e}")
    # Handle error appropriately
```

## Best Practices

1. **Use Async**: Prefer `AsyncAIMemory` for better performance
2. **Configure Scopes**: Use meaningful scope names for organization
3. **Handle Errors**: Always handle storage operation failures
4. **Environment Config**: Use environment variables for production
5. **Test with Memory**: Use in-memory storage for unit tests
6. **Monitor Performance**: Use the stats API to monitor performance

## Examples

See `examples/new_architecture_demo.py` for comprehensive examples of all features.

The new architecture provides a solid foundation for enterprise AI memory management with Azure Cache for Redis as the primary backend while maintaining flexibility for other storage options.
