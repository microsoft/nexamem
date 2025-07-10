# NexaMem / AIMemory

A Python library providing governed, Redis-backed conversational memory for AI components. Designed for easy integration with AI agents, orchestrators, and chatbot systems.

## Features

### Legacy ChatHistory API
- Store, retrieve, and manage chatbot conversation history
- Multiple storage backends: Memory, File, SQLite, and Redis
- Simple API for integration with LLM-based chatbots

### New AIMemory API (Recommended)
- **Redis-backed channels** with user-defined configuration
- **Sync and async client classes** for high-performance applications
- **YAML channel configuration** with TTL, encryption, and quota settings
- **Policy enforcement** for TTL, PII detection, and quota management
- **Scope-based access control** with environment isolation
- **Dynamic channel registration** for runtime flexibility
- **Checkpoint operations** for workflow state management
- **Base metrics capturing** for monitoring and observability

## Installation

```sh
pip install nexamem

# For testing from TestPyPI
pip install -i https://test.pypi.org/simple/ nexamem
```

### OR with GitHub

```sh
pip install git+https://github.com/microsoft/nexamem.git
uv add git+https://github.com/microsoft/nexamem.git  
```

## Quick Start - AIMemory (Recommended)

The new AIMemory API provides enterprise-grade conversational memory with Redis backing:

```python
from nexamem import AIMemory, MemoryScope

# Initialize with Redis (or fakeredis for testing)
memory = AIMemory(
    redis_host="localhost",
    redis_port=6379,
    channels_yaml="channels.yaml",  # Optional: load channel config
    use_fakeredis=True  # For testing
)

# Create a memory scope (defines access control)
scope = MemoryScope(
    agent_id="investment_agent",
    user_id="user_12345",
    session_id="session_abc123",
    env="prod"  # Environment isolation
)

# Write to a channel
message_uuid = memory.write(
    scope=scope,
    channel="working",
    content="User asked about portfolio diversification",
    auto_pii=True  # Auto-detect PII
)

# Read from a channel
messages, metadata = memory.read(
    scope=scope,
    channel="working",
    max_msgs=10,
    since_sec=3600  # Last hour only
)

print(f"Retrieved {len(messages)} messages")
```

### Channel Configuration (channels.yaml)

Define your channels with specific policies:

```yaml
channels:
  working:          # Recent dialogue
    ttl_sec: 14400  # 4 hours
    encrypt: true
    quota_bytes: 1000000  # 1MB daily quota

  procedure:        # Workflow checkpoints  
    ttl_sec: 604800 # 7 days
    encrypt: true

  routing:          # Breadcrumbs, classifier hints
    ttl_sec: 86400  # 24 hours
    encrypt: false
```

### Policy Enforcement

AIMemory automatically enforces policies:

```python
# PII protection - fails if PII sent to non-encrypted channel
try:
    memory.write(
        scope=scope,
        channel="routing",  # encrypt=false
        content="Customer SSN: 123-45-6789",
        pii=True
    )
except EncryptionRequired:
    print("PII blocked from non-encrypted channel")

# Quota enforcement
try:
    large_content = "x" * 2000000  # 2MB
    memory.write(scope=scope, channel="working", content=large_content)
except QuotaExceeded:
    print("Daily quota exceeded")

# TTL validation
try:
    memory.write(
        scope=scope,
        channel="working",
        content="Test",
        ttl_override=999999  # Exceeds channel limit
    )
except TTLViolation:
    print("TTL override exceeds channel limit")
```

### Dynamic Channel Management

Register channels at runtime:

```python
# Register new channel
memory.register_channel(
    name="debug_logs",
    ttl_sec=3600,      # 1 hour
    encrypt=False,
    quota_bytes=500000  # 500KB
)

# List all channels
channels = memory.list_channels()
for name, config in channels.items():
    print(f"{name}: TTL={config.ttl_sec}s, Encrypt={config.encrypt}")
```

### Checkpoint Operations

Manage workflow state:

```python
# Set checkpoint
memory.checkpoint(scope, "workflow_state", {
    "current_step": "risk_assessment",
    "completed_steps": ["onboarding", "kyc"],
    "progress": 0.6
})

# Atomic update
def advance_step(current_state):
    if current_state is None:
        return {"step": 1}
    return {"step": current_state["step"] + 1}

updated = memory.checkpoint_atomic(scope, "counter", advance_step)
print(f"Step: {updated['step']}")
```

### Async API

For high-throughput applications:

```python
import asyncio
from nexamem import AsyncAIMemory

async def main():
    async_memory = AsyncAIMemory(
        redis_host="localhost",
        redis_port=6379
    )
    
    scope = MemoryScope(
        agent_id="async_agent",
        user_id="user_456"
    )
    
    # Async operations
    message_uuid = await async_memory.write(
        scope=scope,
        channel="working", 
        content="Async message"
    )
    
    messages, metadata = await async_memory.read(
        scope=scope,
        channel="working"
    )
    
    await async_memory.close()  # Important!

asyncio.run(main())
```

## Legacy ChatHistory API

The original simple API is still supported for backward compatibility:

```python
from nexamem import initialize, get_config, ChatHistory

# Initialize with your preferred storage
initialize({
    "history_storage": "memory",  # or "file", "sqlite", "redis"
    "debug": True
})

history = ChatHistory()
history.add_message('user', 'Hello!')
history.add_message('bot', 'Hi! How can I help you?')
print(history.get_history())
```

## Architecture

```
Caller → AIMemory Facade
         │
         ▼
 PolicyEngine  (TTL / quota / PII)
 ContentProcessor chain (redact / enrich)  [optional]
         │
         ▼
 RedisAdapter  (sync / async)
         │
         ▼
Azure Cache for Redis
```

**Key Components:**
- **MemoryScope**: Defines access control with agent_id, user_id, session_id, env
- **ChannelManager**: Loads and manages channel configurations
- **PolicyEngine**: Enforces TTL, encryption, quota, and PII policies
- **RedisAdapter**: Handles Redis operations with proper key structure
- **AuditSink**: (Future) Mirrors operations to Redis Stream for compliance

## Production Setup

### Azure Redis Cache

```python
from nexamem import AIMemory, MemoryScope

# Production configuration
memory = AIMemory(
    redis_host="your-cache.redis.cache.windows.net",
    redis_port=6380,  # Azure Redis SSL port
    redis_password="your-access-key",
    redis_ssl=True,
    channels_yaml="/app/config/channels.yaml"
)
```

### Channel Configuration Best Practices

```yaml
# Production channels.yaml
channels:
  working:
    ttl_sec: 14400    # 4 hours - active conversation
    encrypt: true     # PII protection
    quota_bytes: 5000000  # 5MB per user per day

  long_term:
    ttl_sec: 2592000  # 30 days - important context
    encrypt: true
    quota_bytes: 50000000  # 50MB per user per day

  routing:
    ttl_sec: 86400    # 24 hours - classifier hints
    encrypt: false    # No PII, faster access
    quota_bytes: 1000000  # 1MB per user per day

  audit:
    ttl_sec: 31536000  # 365 days - compliance
    encrypt: true
    quota_bytes: 100000000  # 100MB per user per day
```

## API Reference

### Core Classes

#### AIMemory
- `write(scope, channel, content, *, pii=False, ttl_override=None, auto_pii=False) -> str`
- `read(scope, channel, *, since_sec=None, max_bytes=None, max_msgs=None, max_tokens=None) -> (list, dict)`
- `checkpoint(scope, key, payload) -> None`
- `checkpoint_atomic(scope, key, update_fn) -> dict`
- `bulk_erase(scope) -> int`
- `count_bytes(scope, channel) -> int`
- `register_channel(name, *, ttl_sec, encrypt, quota_bytes=None) -> None`

#### MemoryScope
- `MemoryScope(agent_id, user_id, session_id=None, env="prod")`
- `get_key_prefix(channel) -> str`
- `get_index_key(channel) -> str`

#### AsyncAIMemory
Same API as AIMemory but with `async`/`await` for all operations.

### Policy Exceptions
- `PolicyViolation`: Base policy exception
- `QuotaExceeded`: Daily quota limit reached
- `EncryptionRequired`: PII content needs encrypted channel
- `TTLViolation`: TTL override exceeds channel limit

## Examples

See the `examples/` directory for complete usage examples:
- `aimemory_demo.py` - Comprehensive AIMemory demonstration
- `azure_redis_example.py` - Azure Redis Cache integration
- `channels_config_example.py` - Channel configuration examples

## Testing

```sh
# Run all tests
pytest

# Run specific test modules
pytest tests/test_aimemory.py
pytest tests/test_channels.py
pytest tests/test_policy.py

# Run with coverage
pytest --cov=nexamem tests/
```

## Development

1. Clone the repository:
   ```sh
   git clone https://github.com/microsoft/nexamem.git
   cd nexamem
   ```

2. Create virtual environment:
   ```sh
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. Install development dependencies:
   ```sh
   pip install -e .
   pip install -r requirements.txt
   ```

4. Run tests:
   ```sh
   pytest
   ```

## Migration Guide

### From ChatHistory to AIMemory

Old API:
```python
from nexamem import initialize, ChatHistory

initialize({"history_storage": "redis", "redis_host": "localhost"})
history = ChatHistory()
history.add_message('user', 'Hello!')
messages = history.get_history()
```

New API:
```python
from nexamem import AIMemory, MemoryScope

memory = AIMemory(redis_host="localhost", use_fakeredis=True)
scope = MemoryScope(agent_id="chatbot", user_id="user123")

memory.write(scope=scope, channel="working", content="Hello!")
messages, metadata = memory.read(scope=scope, channel="working")
```

### Benefits of Migration
- **Scalability**: Redis-backed with proper key management
- **Governance**: Policy enforcement and audit trails
- **Multi-tenancy**: Scope-based isolation 
- **Flexibility**: Channel-based organization
- **Performance**: Async support for high-throughput

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
