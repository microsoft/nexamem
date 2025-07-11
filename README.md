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
- **Enhanced message properties** aligned with AIMemory requirements
- Support for agent tracking, session management, token counting, and custom metadata
- Multiple storage backends: Memory, File, SQLite
- Advanced SQLite querying capabilities
- Session context management and convenience methods
- Full backward compatibility with existing code

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

The original simple API is still supported for backward compatibility and now includes enhanced message properties aligned with AIMemory requirements:

### Enhanced Message Properties

All messages now support these additional properties:

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
    "history_storage": "memory",  # or "file", "sqlite"
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

### Session Context Management

Set default context that applies to all future messages:

```python
# Set session context (applies to all future messages)
history.set_session_context(
    agent_id="investment_advisor",
    user_id="customer_789",
    env="prod"
)

# Convenience methods that automatically apply context
history.add_user_message("What's my portfolio performance?", tokens=8)
history.add_assistant_message("Your portfolio gained 12% this year.", tokens=14)
history.add_system_message("Analysis completed", tokens=0)
```

### Storage Backends

All storage backends support the enhanced properties:

#### Memory Storage
```python
initialize({"history_storage": "memory"})
```

#### File Storage (JSON)
```python
initialize({
    "history_storage": "file",
    "file_path": "conversation_history.json"
})
```

#### SQLite Database
```python
initialize({
    "history_storage": "sqlite", 
    "sqlite_path": "conversations.db"
})

# SQLite includes advanced querying
history = ChatHistory()
# Query by agent
agent_messages = history.query_sqlite("agent_id = ?", ("portfolio_agent",))
# Query by token count
high_token_msgs = history.query_sqlite("tokens > ?", (10,))
```

### Message Return Format

Each message returned by `get_history()` now includes:

```python
{
    "role": "assistant",                                    # Original
    "content": "Your portfolio gained 12% this year.",      # Original  
    "agent_id": "investment_advisor",                       # NEW
    "user_id": "customer_789",                              # NEW
    "session_id": "c6c191e1-2bc7-4b7b-b08e-d27c7bc210d2",  # NEW (auto-generated)
    "env": "prod",                                          # NEW
    "timestamp": "2025-07-11T08:54:07.728806",              # NEW (auto-generated)
    "tokens": 14,                                           # NEW
    "data": '{"confidence": 0.92}'                          # NEW (JSON string)
}
```

### Legacy Compatibility

Existing code continues to work unchanged:

```python
# This still works exactly as before
history.add_message('user', 'Hello!')
history.add_message('bot', 'Hi there!')
messages = history.get_history()

# But now each message also includes the new properties with defaults
assert messages[0]['agent_id'] == ""        # Default empty
assert messages[0]['env'] == "prod"         # Default environment  
assert messages[0]['tokens'] == 0           # Default no tokens
assert 'session_id' in messages[0]          # Auto-generated
assert 'timestamp' in messages[0]           # Auto-generated
```

## ChatHistory Enhancement Migration

The ChatHistory API has been enhanced with new message properties while maintaining full backward compatibility.

### Automatic Enhancement

**Existing code works unchanged** - new properties are automatically added with sensible defaults:

```python
# Your existing code
history.add_message('user', 'Hello')
history.add_message('assistant', 'Hi there!')

# Now automatically includes:
# - agent_id: "" (empty default)
# - user_id: "" (empty default)  
# - session_id: auto-generated UUID
# - env: "prod" (default environment)
# - timestamp: current ISO datetime
# - tokens: 0 (default)
# - data: "" (empty default)
```

### Database Migration

**SQLite databases are automatically migrated:**
- Existing databases get new columns added automatically
- No data loss - existing messages preserved
- New columns populated with appropriate defaults

```python
# Works with existing SQLite databases
initialize({
    "history_storage": "sqlite",
    "sqlite_path": "existing_database.db"  # Automatically migrated
})
```

### Gradual Enhancement

**Adopt new features incrementally:**

```python
# Step 1: Keep existing calls, get new properties automatically
history.add_message('user', 'Hello')

# Step 2: Add session context for consistency  
history.set_session_context(
    agent_id="customer_service",
    user_id="customer_123"
)

# Step 3: Use convenience methods
history.add_user_message("I need help", tokens=5)
history.add_assistant_message("How can I help?", tokens=7)

# Step 4: Add custom metadata as needed
history.add_assistant_message(
    "Based on your account history...",
    tokens=25,
    data='{"confidence": 0.95, "sources": ["account_db", "transaction_log"]}'
)
```

### Enhanced Analytics

**Leverage new properties for insights:**

```python
messages = history.get_history()

# Token usage analytics
total_tokens = sum(msg['tokens'] for msg in messages)
user_tokens = sum(msg['tokens'] for msg in messages if msg['role'] == 'user')
assistant_tokens = sum(msg['tokens'] for msg in messages if msg['role'] == 'assistant')

print(f"Total conversation tokens: {total_tokens}")
print(f"User tokens: {user_tokens}, Assistant tokens: {assistant_tokens}")

# Agent analytics (if using multiple agents)
agents = {msg['agent_id'] for msg in messages if msg['agent_id']}
print(f"Agents involved: {', '.join(agents)}")

# Session tracking
session_id = messages[0]['session_id'] if messages else None
print(f"Session ID: {session_id}")
```

### SQLite Querying

**Use advanced queries with new properties:**

```python
# Find messages by specific agent
agent_messages = history.query_sqlite(
    "agent_id = ? AND tokens > ?", 
    ("portfolio_advisor", 10)
)

# Find recent high-token interactions
recent_complex = history.query_sqlite(
    "timestamp > ? AND tokens > ?",
    ("2025-07-01T00:00:00", 20)  
)

# Find messages with custom data
custom_data_messages = history.query_sqlite(
    "data != ''",
    ()
)
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
