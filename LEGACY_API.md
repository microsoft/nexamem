# Legacy ChatHistory API (Deprecated)

> ⚠️ **Deprecation Notice**: The legacy ChatHistory API is deprecated and will be removed in a future version. Please migrate to the new [AIMemory API](README.md#quick-start---aimemory-recommended) for all new projects.

## Migration Guide

### Quick Migration Example

**Before (Legacy API):**
```python
from nexamem import initialize, ChatHistory

# Old initialization pattern
initialize({
    "history_storage": "redis",
    "redis_config": {
        "azure_hostname": "your-cache.redis.cache.windows.net",
        "azure_access_key": "your_primary_access_key",
        "ssl": True
    }
})

history = ChatHistory()
history.add_message('user', 'Hello!')
history.add_message('assistant', 'Hi! How can I help you?')
messages = history.get_history()
```

**After (New AIMemory API):**
```python
from nexamem import AIMemory, AIMemoryConfig, StorageConfig, MemoryScope

# New configuration pattern
config = AIMemoryConfig(
    default_scope="chat_session",
    storage=StorageConfig.azure_redis(
        hostname="your-cache.redis.cache.windows.net",
        access_key="your_primary_access_key",
        ssl=True
    ),
    channels_yaml="channels.yaml"  # Optional: YAML channel configuration
)

memory = AIMemory(config)

scope = MemoryScope(
    agent_id="chat_agent",
    user_id="user_123",
    session_id="session_abc"
)

# Write messages
memory.write(scope=scope, channel="conversation", content="Hello!")
memory.write(scope=scope, channel="conversation", content="Hi! How can I help you?")

# Read messages
messages, metadata = memory.read(scope=scope, channel="conversation")
```

## Key Differences

| Feature | Legacy API | New API |
|---------|------------|---------|
| **Configuration** | `initialize()` function | `AIMemoryConfig` class |
| **Storage Setup** | Dict-based config | Type-safe Pydantic models |
| **Message Storage** | `add_message()` | `write()` with channels |
| **Message Retrieval** | `get_history()` | `read()` with metadata |
| **Session Management** | Built-in session context | Explicit `MemoryScope` |
| **Async Support** | Limited | Full async/await support |
| **Channel Management** | Single conversation | Multiple channels with YAML config |
| **Policy Enforcement** | Basic | Advanced (TTL, PII, quotas) |

## Migration Benefits

The new AIMemory API provides:

- **Better Performance**: Async-first design with connection pooling
- **Enhanced Security**: PII detection, encryption, and policy enforcement
- **Flexible Channels**: YAML-configured channels with TTL and quota management
- **Better Testing**: Dependency injection and configurable storage backends
- **Enterprise Features**: Audit logging, metrics, and compliance-ready design

## Legacy API Documentation

For applications that cannot migrate immediately, the legacy API remains available:

### Enhanced Message Properties

All messages support these additional properties:

- **`agent_id`** - String identifier for the agent (default: empty string)
- **`user_id`** - String identifier for the user (default: empty string)  
- **`session_id`** - Auto-generated UUID for the session (automatically created if not provided)
- **`env`** - Environment identifier (default: "prod")
- **`timestamp`** - ISO datetime string of when the message was recorded (auto-generated)
- **`tokens`** - Number of tokens used by the LLM (default: 0)
- **`data`** - JSON string for additional custom data (default: empty string)

### Basic Usage

```python
from nexamem import initialize, ChatHistory

# Initialize with your preferred storage
initialize({
    "history_storage": "memory",  # or "file", "sqlite", "redis"
    "debug": True
})

history = ChatHistory()

# Simple usage (backward compatible)
history.add_message('user', 'Hello!')
history.add_message('assistant', 'Hi! How can I help you?')

# Enhanced usage with new properties
history.add_message(
    'assistant', 
    'Your portfolio is performing well.',
    agent_id="portfolio_agent",
    user_id="customer_123",
    tokens=15,
    data='{"confidence": 0.92, "risk_level": "moderate"}'
)

# View all messages with enhanced properties
messages = history.get_history()
for msg in messages:
    print(f"Role: {msg['role']}")
    print(f"Content: {msg['content']}")
    print(f"Agent: {msg['agent_id']}")
    print(f"Tokens: {msg['tokens']}")
    print(f"Timestamp: {msg['timestamp']}")
```

### Azure Redis with Legacy API

```python
from nexamem import initialize, ChatHistory

# Azure Redis with access key
initialize({
    "history_storage": "redis",
    "redis_config": {
        "azure_hostname": "your-cache.redis.cache.windows.net",
        "azure_access_key": "your_primary_access_key",
        "ssl": True
    }
})

history = ChatHistory()

# Set session context for organized conversation tracking
history.set_session_context(
    agent_id="customer_support",
    user_id="customer_12345",
    env="prod"
)

# Add messages with automatic token counting and metadata
history.add_user_message("I need help with my account", tokens=8)
history.add_assistant_message(
    "I'd be happy to help! What specific issue are you experiencing?", 
    tokens=15,
    data='{"intent": "support_request", "confidence": 0.95}'
)

# Retrieve conversation history with all enhanced properties
messages = history.get_history()
print(f"Retrieved {len(messages)} messages from Azure Redis")

# Advanced querying: find all messages for this user across sessions
user_messages = history.query_redis("*customer_12345*", limit=100)
print(f"Found {len(user_messages)} total messages for this customer")
```

## Support

- **New Projects**: Use the [AIMemory API](README.md#quick-start---aimemory-recommended)
- **Migration Questions**: See the [New Architecture Guide](NEW_ARCHITECTURE.md)
- **Legacy API Issues**: The legacy API will receive critical bug fixes only
- **Timeline**: Legacy API deprecation timeline will be announced in future releases
