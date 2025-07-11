# NexaMem / AIMemory

A Python library providing governed, Redis-backed conversational memory for AI components. Designed for easy integration with AI agents, orchestrators, and chatbot systems.

## Features

### AIMemory API (Recommended) - v0.3
- **Redis-backed channels** with user-defined configuration
- **Sync and async client classes** for high-performance applications  
- **YAML channel configuration** with TTL, encryption, and quota settings
- **Policy enforcement** for TTL, PII detection, and quota management
- **Scope-based access control** with environment isolation
- **Dynamic channel registration** for runtime flexibility
- **Checkpoint operations** for workflow state management
- **Content processing chain** with PII detection/redaction
- **Audit logging** to Redis Stream for compliance
- **Base metrics capturing** for monitoring and observability

### Legacy ChatHistory API
- Store, retrieve, and manage chatbot conversation history
- Multiple storage backends: Memory, File, SQLite, and Redis
- Simple API for integration with LLM-based chatbots

## Installation

```sh
pip install nexamem

# Development/testing
pip install -i https://test.pypi.org/simple/ nexamem
```

### Or from GitHub

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

# Validate configuration (optional but recommended)
from nexamem.channels import validate_yaml_schema

try:
    validate_yaml_schema("channels.yaml")
    print("✅ Channel configuration is valid!")
except Exception as e:
    print(f"❌ Configuration error: {e}")
```

> **💡 Pro Tip**: AIMemory includes strict YAML schema validation by default to catch configuration errors early. See the [Schema Validation](#-yaml-schema-validation) section for details.

### Channel Configuration (channels.yaml)

AIMemory uses **strict YAML schema validation** to ensure configuration integrity and security. Each channel must follow specific rules and constraints.

#### Schema Requirements

**Channel Names:**
- Must be `snake_case`: start with lowercase letter, followed by letters/numbers/underscores
- Maximum 50 characters
- Cannot use reserved names: `admin`, `system`, `internal`, `redis`, `audit`
- Pattern: `^[a-z][a-z0-9_]*$`

**Required Fields:**
- `ttl_sec`: Time-to-live in seconds (60 to 604,800 = 1 minute to 7 days)

**Optional Fields:**
- `encrypt`: Boolean (default: `false`) - enables client-side encryption
- `quota_bytes`: Integer (1 to 1,000,000,000) - daily quota per (agent, user, channel)

#### Valid Configuration Example

```yaml
channels:
  working:              # ✅ Valid: snake_case name
    ttl_sec: 14400      # ✅ Valid: 4 hours (within 1 min - 7 days range)
    encrypt: true       # ✅ Valid: boolean value
    quota_bytes: 1000000 # ✅ Valid: 1MB daily quota

  procedure:            # ✅ Valid: workflow checkpoints
    ttl_sec: 604800     # ✅ Valid: 7 days (maximum allowed)
    encrypt: true       # ✅ Valid: encryption for sensitive workflows

  routing:              # ✅ Valid: classification hints
    ttl_sec: 86400      # ✅ Valid: 24 hours
    encrypt: false      # ✅ Valid: no encryption needed for routing
```

#### Schema Validation Control

```python
# Strict validation (default - recommended)
memory = AIMemory(
    channels_yaml="channels.yaml",
    strict_yaml_validation=True  # Default
)

# Backward compatibility mode (legacy configurations)
memory = AIMemory(
    channels_yaml="legacy_channels.yaml",
    strict_yaml_validation=False
)

# Standalone validation
from nexamem.channels import validate_yaml_schema, YamlSchemaError

try:
    validate_yaml_schema("channels.yaml")
    print("✅ Configuration is valid!")
except YamlSchemaError as e:
    print(f"❌ Validation failed: {e}")
```

## 🔐 YAML Schema Validation

AIMemory enforces **strict schema validation** to prevent configuration errors and ensure security compliance.

### Validation Features

- **Channel Name Validation**: Enforces `snake_case` naming conventions
- **Field Type Checking**: Validates data types for all configuration fields  
- **Range Validation**: Ensures TTL and quota values are within safe limits
- **Security Enforcement**: Blocks reserved names and unknown fields
- **Clear Error Messages**: Provides specific, actionable error descriptions

### Validation Modes

```python
# Strict validation (recommended for production)
memory = AIMemory(
    channels_yaml="channels.yaml",
    strict_yaml_validation=True  # Default
)

# Legacy mode (for backward compatibility)
memory = AIMemory(
    channels_yaml="legacy_channels.yaml", 
    strict_yaml_validation=False
)
```

### Schema Validation Tools

```python
from nexamem.channels import validate_yaml_schema, generate_yaml_schema_docs

# Validate configuration file
try:
    validate_yaml_schema("channels.yaml")
    print("✅ Configuration is valid")
except YamlSchemaError as e:
    print(f"❌ Validation failed: {e}")

# Generate schema documentation
print(generate_yaml_schema_docs())
```

### Common Validation Errors

| Error Type | Example | Fix |
|------------|---------|-----|
| Invalid Name | `Invalid-Channel` | Use `invalid_channel` |
| TTL Range | `ttl_sec: 999999` | Use value ≤ 604800 (7 days) |
| Reserved Name | `admin:` | Use `admin_channel` or similar |
| Unknown Field | `custom_field: value` | Remove or use allowed fields |
| Wrong Type | `encrypt: "yes"` | Use `encrypt: true` |

#### Common Validation Errors

```yaml
# ❌ INVALID Examples:
channels:
  Invalid-Name:         # ❌ Hyphens not allowed
  user_123:            # ❌ Cannot start with number
  admin:               # ❌ Reserved name
  working:
    ttl_sec: 999999    # ❌ Exceeds 7 days (604,800 seconds)
    encrypt: "yes"     # ❌ Must be boolean (true/false)
    quota_bytes: -100  # ❌ Must be positive
    unknown_field: 1   # ❌ Unknown field not allowed
```

For detailed schema documentation, see [YAML_SCHEMA_VALIDATION.md](YAML_SCHEMA_VALIDATION.md).

### Enhanced Features

```python
# Dynamic channel registration
memory.register_channel(
    name="debug_logs",
    ttl_sec=3600,      # 1 hour
    encrypt=False,
    quota_bytes=500000  # 500KB
)

# Checkpoint operations for workflow state
memory.checkpoint(scope, "workflow_state", {
    "current_step": "risk_assessment",
    "completed_steps": ["onboarding", "kyc"],
    "progress": 0.6
})

# Atomic updates
def advance_step(current_state):
    return {"step": current_state["step"] + 1}

updated = memory.checkpoint_atomic(scope, "counter", advance_step)

# Metrics and audit
metrics_data = memory.metrics.get_all_metrics()
audit_records = memory.audit.get_audit_records(count=10)
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

### From Legacy Configurations

If you have existing `channels.yaml` files that don't pass strict validation:

#### Step 1: Identify Issues

Run validation to see what needs fixing:

```python
from nexamem.channels import validate_yaml_schema, YamlSchemaError

try:
    validate_yaml_schema("legacy_channels.yaml")
except YamlSchemaError as e:
    print("Issues to fix:")
    print(e)
```

#### Step 2: Common Fixes

| Issue | Before | After |
|-------|--------|-------|
| **Invalid Names** | `user-context` | `user_context` |
| **Case Issues** | `Working` | `working` |
| **TTL Range** | `ttl_sec: 999999` | `ttl_sec: 604800` |
| **Type Issues** | `encrypt: "true"` | `encrypt: true` |
| **Reserved Names** | `admin:` | `admin_channel:` |
| **Unknown Fields** | `timeout: 30` | *(remove field)* |

#### Step 3: Gradual Migration

```python
# Phase 1: Disable strict validation temporarily
memory = AIMemory(
    channels_yaml="legacy_channels.yaml",
    strict_yaml_validation=False  # Temporary
)

# Phase 2: Fix issues and test with validation
validate_yaml_schema("fixed_channels.yaml")

# Phase 3: Enable strict validation
memory = AIMemory(
    channels_yaml="fixed_channels.yaml",
    strict_yaml_validation=True   # Production ready
)
```

### Configuration Examples

See example configurations:
- [`channels.yaml`](channels.yaml) - Default configuration with full documentation
- [`examples/valid_channels.yaml`](examples/valid_channels.yaml) - Extended valid example
- [`examples/invalid_channels.yaml`](examples/invalid_channels.yaml) - Common mistakes to avoid

## License

This project is licensed under the MIT License.
