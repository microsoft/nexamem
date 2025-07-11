# NexaMem / AIMemory

A Python library providing governed, Redis-backed conversational memory for AI components. Designed for easy integration with AI agents, orchestrators, and chatbot systems.

[![Tests](https://github.com/microsoft/nexamem/workflows/Tests/badge.svg)](https://github.com/microsoft/nexamem/actions/workflows/tests.yml)
[![Publish](https://github.com/microsoft/nexamem/workflows/Publish%20Python%20🐍%20distribution%20📦%20to%20PyPI%20and%20TestPyPI/badge.svg)](https://github.com/microsoft/nexamem/actions/workflows/python-publish-to-test.yml)
[![Python](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

## 📖 Quick Navigation

**New to NexaMem?** → [Quick Start - AIMemory](#quick-start---aimemory-recommended)  
**Want Azure Redis?** → [Azure Redis Ready](#-azure-redis-ready) | [Production Configuration](#production-with-azure-redis)  
**YAML Channels?** → [Channel Configuration](#channel-configuration-channelsyaml) | [Schema Validation](#-yaml-schema-validation)  
**Need Help?** → [Azure Redis Integration Guide](AZURE_REDIS.md) | [Migration Guide](LEGACY_API.md)  
**Testing & Development?** → [Testing & Development](#-testing--development)

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
- **Azure Redis integration** with enterprise security and performance

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

## 🔥 Azure Redis Ready

NexaMem includes **first-class support for Azure Cache for Redis** with enterprise security features:

- **🚀 Quick Setup**: Connect with just hostname + access key  
- **🔐 Enterprise Auth**: Full Azure Entra ID (Azure AD) integration
- **⚡ High Performance**: Sub-millisecond latency, automatic scaling
- **🛡️ Security**: VNet integration, encryption at rest/transit, compliance-ready
- **📊 Advanced Querying**: Pattern-based message search and analytics

**Ready to use Azure Redis?** See our [Quick Start with Azure Redis](#quick-start-with-azure-redis) section below or check the comprehensive [Azure Redis Integration Guide](AZURE_REDIS.md) for advanced configurations.

## Quick Start - AIMemory (Recommended)

The new AIMemory API provides enterprise-grade conversational memory with Redis backing and full YAML channel configuration support:

```python
from nexamem import AIMemory, AIMemoryConfig, StorageConfig, MemoryScope

# Initialize with in-memory storage for testing (or Redis for production)
config = AIMemoryConfig(
    default_scope="test_session",
    storage=StorageConfig.memory(),  # For testing, use Redis for production
    channels_yaml="channels.yaml",  # Optional: YAML channel configuration
    strict_yaml_validation=True     # Optional: Enable strict YAML validation
)
memory = AIMemory(config)

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

### Production with Azure Redis

For production applications, use Azure Cache for Redis with the new AIMemory API:

```python
from nexamem import AIMemory, AIMemoryConfig, StorageConfig

# Production configuration with Azure Redis
config = AIMemoryConfig(
    default_scope="production_session",
    storage=StorageConfig.azure_redis(
        hostname="your-cache.redis.cache.windows.net",
        access_key="your_primary_access_key",
        port=6380,
        ssl=True
    ),
    channels_yaml="channels.yaml",
    strict_yaml_validation=True
)

memory = AIMemory(config)

# Use the same write/read operations as before
scope = MemoryScope(
    agent_id="prod_agent",
    user_id="customer_12345",
    session_id="session_abc123",
    env="prod"
)

message_uuid = memory.write(
    scope=scope,
    channel="working",
    content="Production message with Azure Redis backing",
    auto_pii=True
)

messages, metadata = memory.read(scope=scope, channel="working")
print(f"Retrieved {len(messages)} messages from Azure Redis")
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
from nexamem import AsyncAIMemory, AIMemoryConfig, StorageConfig

async def main():
    config = AIMemoryConfig(
        default_scope="async_session",
        storage=StorageConfig.memory(),  # For testing, use Redis for production
        channels_yaml="channels.yaml"   # Optional: YAML channel configuration
    )
    
    async_memory = AsyncAIMemory(config)
    
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

## 🧪 Testing & Development

### Running Tests

NexaMem includes a comprehensive test suite covering all major functionality. Tests are organized to provide both unit and integration coverage.

#### Prerequisites

Make sure you're using the project's virtual environment:

```bash
# On Windows (recommended)
.venv/Scripts/python.exe -m pytest

# Or activate the virtual environment first
.venv\Scripts\activate
python -m pytest

# On Unix/Linux/macOS
source .venv/bin/activate
python -m pytest
```

### Legacy ChatHistory API (Deprecated)

> ⚠️ **Note**: The legacy ChatHistory API is deprecated and will be removed in a future version. Please migrate to the new [AIMemory API](#quick-start---aimemory-recommended) for new projects.

For existing applications still using the legacy API, see [LEGACY_API.md](LEGACY_API.md) for documentation and migration guidance.

# On Unix/Linux/macOS
source .venv/bin/activate
python -m pytest
```

## License

This project is licensed under the MIT License.
