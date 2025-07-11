"""
Example usage of the new NexaMem architecture with dependency injection.

This example demonstrates:
1. Azure Redis configuration (primary backend)
2. Async-first design pattern
3. Dependency injection for storage
4. Clean configuration with Pydantic
"""

import asyncio

from nexamem import (
    AIMemory,
    AIMemoryConfig,
    AsyncAIMemory,
    AzureRedisConfig,
    FileConfig,
    MemoryConfig,
    SQLiteConfig,
    StorageConfig,
    create_aimemory,
)


def create_azure_redis_config() -> AIMemoryConfig:
    """Create configuration for Azure Cache for Redis."""
    return AIMemoryConfig(
        default_scope="chatbot_session",
        storage=StorageConfig.azure_redis(AzureRedisConfig(
            hostname="your-redis-cache.redis.cache.windows.net",
            port=6380,
            access_key="your-access-key",
            db=0,
            ssl=True,
            socket_timeout=5.0,
            socket_connect_timeout=5.0,
            key_prefix="nexamem:",
            memory_collection="memories",
            index_collection="memory_indexes",
            audit_stream="memory_audit"
        ))
    )


def create_memory_config() -> AIMemoryConfig:
    """Create configuration for in-memory storage."""
    return AIMemoryConfig(
        default_scope="test_session",
        storage=StorageConfig.memory()
    )


def create_file_config() -> AIMemoryConfig:
    """Create configuration for file storage."""
    return AIMemoryConfig(
        default_scope="file_session",
        storage=StorageConfig.file("./nexamem_data")
    )


def create_sqlite_config() -> AIMemoryConfig:
    """Create configuration for SQLite storage."""
    return AIMemoryConfig(
        default_scope="sqlite_session",
        storage=StorageConfig.sqlite("./nexamem.db")
    )


async def async_example():
    """Demonstrate async AIMemory usage."""
    print("=== Async AIMemory Example ===")
    
    # Use in-memory storage for this example
    config = create_memory_config()
    
    # Create async AI memory instance
    ai_memory = AsyncAIMemory(config)
    
    # Store some memories
    memory1_id = await ai_memory.store(
        "User asked about Python best practices",
        metadata={"topic": "programming", "language": "python"}
    )
    print(f"Stored memory: {memory1_id}")
    
    memory2_id = await ai_memory.store(
        "Discussed async/await patterns in Python",
        metadata={"topic": "programming", "language": "python", "subtopic": "async"}
    )
    print(f"Stored memory: {memory2_id}")
    
    # Retrieve a memory
    retrieved = await ai_memory.retrieve(memory1_id)
    print(f"Retrieved memory: {retrieved}")
    
    # Search memories
    search_results = await ai_memory.search("Python", limit=10)
    print(f"Search results for 'Python': {search_results}")
    
    # List all memories
    all_memories = await ai_memory.list()
    print(f"All memories: {all_memories}")
    
    # Get statistics
    stats = await ai_memory.get_stats()
    print(f"Storage stats: {stats}")
    
    # Get audit log
    audit_log = await ai_memory.get_audit_log(limit=5)
    print(f"Recent audit entries: {audit_log}")


def sync_example():
    """Demonstrate sync AIMemory usage."""
    print("\n=== Sync AIMemory Example ===")
    
    # Use SQLite storage for this example
    config = create_sqlite_config()
    
    # Create sync AI memory instance
    ai_memory = AIMemory(config)
    
    # Store some memories
    memory1_id = ai_memory.store(
        "User wants to learn about machine learning",
        metadata={"topic": "AI", "difficulty": "beginner"}
    )
    print(f"Stored memory: {memory1_id}")
    
    memory2_id = ai_memory.store(
        "Explained neural networks and deep learning basics",
        metadata={"topic": "AI", "difficulty": "intermediate", "subtopic": "neural_networks"}
    )
    print(f"Stored memory: {memory2_id}")
    
    # Retrieve a memory
    retrieved = ai_memory.retrieve(memory1_id)
    print(f"Retrieved memory: {retrieved}")
    
    # Search memories
    search_results = ai_memory.search("learning", limit=10)
    print(f"Search results for 'learning': {search_results}")
    
    # List all memories
    all_memories = ai_memory.list()
    print(f"All memories: {all_memories}")
    
    # Get statistics
    stats = ai_memory.get_stats()
    print(f"Storage stats: {stats}")


def factory_example():
    """Demonstrate factory function usage."""
    print("\n=== Factory Function Example ===")
    
    # Create file storage config
    config = create_file_config()
    
    # Use factory function to create async instance
    ai_memory = create_aimemory(config, async_preferred=True)
    print(f"Created AI memory instance: {type(ai_memory)}")
    
    # Use factory function to create sync instance
    ai_memory_sync = create_aimemory(config, async_preferred=False)
    print(f"Created AI memory instance: {type(ai_memory_sync)}")


def configuration_examples():
    """Show different configuration patterns."""
    print("\n=== Configuration Examples ===")
    
    # Azure Redis configuration
    azure_config = create_azure_redis_config()
    print(f"Azure Redis config: {azure_config.storage.type.value}")
    print(f"Redis hostname: {azure_config.storage.config.hostname}")
    
    # Memory configuration
    memory_config = create_memory_config()
    print(f"Memory config: {memory_config.storage.type.value}")
    
    # File configuration
    file_config = create_file_config()
    print(f"File config: {file_config.storage.type.value}")
    print(f"Storage path: {file_config.storage.config.path}")
    
    # SQLite configuration
    sqlite_config = create_sqlite_config()
    print(f"SQLite config: {sqlite_config.storage.type.value}")
    print(f"Database path: {sqlite_config.storage.config.path}")


async def main():
    """Run all examples."""
    print("NexaMem New Architecture Examples")
    print("=" * 50)
    
    configuration_examples()
    await async_example()
    sync_example()
    factory_example()
    
    print("\n=== Examples Complete ===")


if __name__ == "__main__":
    asyncio.run(main())
