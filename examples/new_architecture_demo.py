"""
Example usage of the new NexaMem architecture with dependency injection.

This example demonstrates:
1. Azure Redis configuration (primary backend)
2. Channel-based memory management with YAML configuration
3. Async-first design pattern
4. Dependency injection for storage
5. Clean configuration with Pydantic
"""

import asyncio

from nexamem import (
    AIMemory,
    AIMemoryConfig,
    AsyncAIMemory,
    AzureRedisConfig,
    StorageConfig,
    MemoryScope,
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
        )),
        channels_yaml=None,  # Could specify YAML file for channel configuration
        strict_yaml_validation=True
    )


def create_memory_config() -> AIMemoryConfig:
    """Create configuration for in-memory storage."""
    return AIMemoryConfig(
        default_scope="test_session",
        storage=StorageConfig.memory(),
        channels_yaml=None,
        strict_yaml_validation=True
    )


def create_file_config() -> AIMemoryConfig:
    """Create configuration for file storage."""
    return AIMemoryConfig(
        default_scope="file_session",
        storage=StorageConfig.file("./nexamem_data"),
        channels_yaml=None,
        strict_yaml_validation=True
    )


def create_sqlite_config() -> AIMemoryConfig:
    """Create configuration for SQLite storage."""
    return AIMemoryConfig(
        default_scope="sqlite_session",
        storage=StorageConfig.sqlite("./nexamem.db"),
        channels_yaml=None,
        strict_yaml_validation=True
    )


async def async_example():
    """Demonstrate async AIMemory usage with channel-based API."""
    print("=== Async AIMemory Example ===")
    
    # Use in-memory storage for this example
    config = create_memory_config()
    
    # Create async AI memory instance
    ai_memory = AsyncAIMemory(config)
    
    # Create a memory scope for session management
    scope = MemoryScope(
        agent_id="async_agent",
        user_id="user_123",
        session_id="session_abc",
        env="dev"
    )
    
    # First, let's demonstrate the storage-based API which is fully async
    print("--- Storage-based API ---")
    memory1_id = await ai_memory.store(
        "User asked about Python best practices",
        metadata={"topic": "programming", "language": "python"}
    )
    print(f"Stored memory using storage API: {memory1_id}")
    
    memory2_id = await ai_memory.store(
        "Discussed async/await patterns in Python",
        metadata={"topic": "programming", "language": "python", "subtopic": "async"}
    )
    print(f"Stored memory: {memory2_id}")
    
    # Retrieve using storage API
    retrieved = await ai_memory.retrieve(memory1_id)
    print(f"Retrieved memory: {retrieved['content'][:50]}...")
    
    # Search memories
    search_results = await ai_memory.search("Python", limit=10)
    print(f"Found {len(search_results)} Python-related memories")
    
    # List all memories
    all_memories = await ai_memory.list()
    print(f"Total memories: {len(all_memories)}")
    
    # Get statistics
    stats = await ai_memory.get_stats()
    print(f"Storage stats: {stats}")
    
    print("\n--- Channel-based API (limited async support) ---")
    # Note: Channel-based write/read work, but channel management is sync-only
    try:
        # Try to write to a channel that might exist
        message1_uuid = await ai_memory.write(
            scope=scope,
            channel="general",  # Try a common channel name
            content="Testing channel-based write",
            auto_pii=True
        )
        print(f"Stored message to general channel: {message1_uuid}")
        
        # Read it back
        messages, metadata = await ai_memory.read(
            scope=scope,
            channel="general",
            max_msgs=10
        )
        print(f"Retrieved {len(messages)} messages from general channel")
        
    except Exception as e:
        print(f"Channel-based API note: {e}")
        print("Use the sync AIMemory for full channel management features")


def sync_example():
    """Demonstrate sync AIMemory usage with channel-based API."""
    print("\n=== Sync AIMemory Example ===")
    
    # Use SQLite storage for this example
    config = create_sqlite_config()
    
    # Create sync AI memory instance
    ai_memory = AIMemory(config)
    
    # Create a memory scope
    scope = MemoryScope(
        agent_id="sync_agent",
        user_id="user_456",
        session_id="session_def",
        env="prod"
    )
    
    # Register channels
    ai_memory.register_channel(
        name="support_chat",
        ttl_sec=86400,  # 24 hours
        encrypt=True,   # Encrypt for sensitive data
        quota_bytes=500000  # 500KB
    )
    
    ai_memory.register_channel(
        name="debug_logs",
        ttl_sec=3600,   # 1 hour
        encrypt=False,
        quota_bytes=100000  # 100KB
    )
    
    # Write to different channels
    support_msg = ai_memory.write(
        scope=scope,
        channel="support_chat",
        content="Customer reported login issues",
        auto_pii=True
    )
    print(f"Support message stored: {support_msg}")
    
    debug_msg = ai_memory.write(
        scope=scope,
        channel="debug_logs",
        content="Authentication service response time: 250ms",
        auto_pii=False
    )
    print(f"Debug message stored: {debug_msg}")
    
    # Read from specific channel
    support_messages, _ = ai_memory.read(
        scope=scope,
        channel="support_chat",
        max_msgs=5
    )
    print(f"Support chat has {len(support_messages)} messages")
    
    # Check if channel exists
    if ai_memory.channel_exists("support_chat"):
        print("Support chat channel is available")
    
    # List all channels
    all_channels = ai_memory.list_channels()
    for name, config in all_channels.items():
        print(f"Channel '{name}': TTL={config.ttl_sec}s, Encrypt={config.encrypt}")


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
    print(f"YAML validation: {azure_config.strict_yaml_validation}")
    
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