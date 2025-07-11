# Azure Cache for Redis Integration

This document explains how to use NexaMem with Azure Cache for Redis, supporting both access keys and Entra ID authentication.

## Overview

NexaMem now supports Azure Cache for Redis as a storage backend, providing enterprise-grade scalability, security, and performance for chatbot conversation history. The integration supports multiple authentication methods:

- **Access Keys**: Simple authentication using Redis access keys
- **Entra ID (Azure AD)**: Identity-based authentication using Azure Active Directory
- **Azure Key Vault**: Secure secret management for Redis credentials

## Prerequisites

### Required Dependencies

The following packages are automatically included with NexaMem:

```bash
pip install nexamem
```

This includes:
- `redis[asyncio]>=5.0.0` - Redis client with async support
- `azure-identity>=1.15.0` - Azure authentication
- `azure-keyvault-secrets>=4.7.0` - Key Vault integration
- `fakeredis>=2.21.0` - Testing support

### Azure Resources

You'll need:
1. **Azure Cache for Redis** instance
2. **Azure Active Directory** (for Entra ID auth)
3. **Azure Key Vault** (optional, for secure secret storage)

## Configuration

### Basic Configuration with Access Key

The simplest way to connect to Azure Redis:

```python
from nexamem import initialize, ChatHistory

config = {
    "history_storage": "redis",
    "redis_config": {
        "azure_hostname": "your-redis.redis.cache.windows.net",
        "azure_access_key": "your-primary-or-secondary-access-key",
        "db": 0,  # Optional: Redis database number
        "key_prefix": "nexamem:chat"  # Optional: Key prefix for organization
    }
}

initialize(config)
history = ChatHistory()
```

### Entra ID Authentication

For identity-based authentication:

```python
config = {
    "history_storage": "redis",
    "redis_config": {
        "azure_hostname": "your-redis.redis.cache.windows.net",
        "use_azure_entra_id": True,
        "azure_username": "your-username-or-client-id",
    }
}
```

### Service Principal Authentication

For automated/service scenarios:

```python
config = {
    "history_storage": "redis",
    "redis_config": {
        "azure_hostname": "your-redis.redis.cache.windows.net",
        "use_azure_entra_id": True,
        "azure_client_id": "your-client-id",
        "azure_client_secret": "your-client-secret",
        "azure_tenant_id": "your-tenant-id"
    }
}
```

### Azure Key Vault Integration

For secure credential management:

```python
config = {
    "history_storage": "redis",
    "redis_config": {
        "azure_hostname": "your-redis.redis.cache.windows.net",
        "azure_keyvault_url": "https://your-keyvault.vault.azure.net/",
        "azure_secret_name": "redis-access-key"
    }
}
```

### Environment-Based Configuration

For production deployments:

```python
import os

config = {
    "history_storage": "redis",
    "redis_config": {
        "azure_hostname": os.getenv("AZURE_REDIS_HOSTNAME"),
        "azure_access_key": os.getenv("AZURE_REDIS_ACCESS_KEY"),
        # Or use Entra ID
        # "use_azure_entra_id": True,
        # "azure_client_id": os.getenv("AZURE_CLIENT_ID"),
        # "azure_client_secret": os.getenv("AZURE_CLIENT_SECRET"),
        # "azure_tenant_id": os.getenv("AZURE_TENANT_ID")
    }
}
```

## Usage Examples

### Basic Chat History

```python
from nexamem import initialize, ChatHistory

# Configure Azure Redis
config = {
    "history_storage": "redis",
    "redis_config": {
        "azure_hostname": "your-redis.redis.cache.windows.net",
        "azure_access_key": "your-access-key"
    }
}

initialize(config)

# Create chat history
history = ChatHistory()
history.set_session_context(
    agent_id="financial_advisor",
    user_id="customer_123",
    env="production"
)

# Add messages
history.add_user_message("What's my account balance?", tokens=6)
history.add_assistant_message("Your current balance is $15,420.50", tokens=9)
history.add_system_message("Balance inquiry completed", tokens=0)

# Retrieve conversation
messages = history.get_history()
print(f"Retrieved {len(messages)} messages from Azure Redis")
```

### Advanced Querying

Redis storage supports advanced querying capabilities:

```python
# Query messages by pattern
results = history.query_redis("*user_123*", limit=50)

# Clear conversation history
history.clear()
```

### Async Operations with AIMemory

For high-performance applications:

```python
from nexamem import initialize
from nexamem.aimemory import AsyncAIMemory
from nexamem.memory_scope import MemoryScope

# Configure async Redis
config = {
    "history_storage": "redis",
    "redis_config": {
        "azure_hostname": "your-redis.redis.cache.windows.net",
        "use_azure_entra_id": True,
        "azure_username": "your-client-id"
    }
}

initialize(config)

# Create async memory instance
memory = AsyncAIMemory(
    azure_hostname="your-redis.redis.cache.windows.net",
    use_azure_entra_id=True,
    azure_username="your-client-id"
)

# Define memory scope
scope = MemoryScope(
    env="prod",
    agent_id="support_bot",
    user_id="user_456",
    session_id="session_789"
)

# Async operations
async def handle_conversation():
    # Write message
    message_id = await memory.write_async(
        scope=scope,
        channel="chat",
        content="User question about Azure Redis",
        ttl_sec=86400  # 24 hours
    )
    
    # Read messages
    messages, metadata = await memory.read_async(
        scope=scope,
        channel="chat",
        max_msgs=10
    )
    
    return messages
```

## Security Best Practices

### 1. Access Key Management

- **Rotate keys regularly** using Azure portal or CLI
- **Use Key Vault** for production environments
- **Limit key permissions** to minimum required
- **Monitor access** using Azure logging

### 2. Entra ID Configuration

```python
# Recommended: Use managed identity in Azure
config = {
    "redis_config": {
        "azure_hostname": "your-redis.redis.cache.windows.net",
        "use_azure_entra_id": True
        # Credentials automatically retrieved from Azure context
    }
}

# For service principals, secure the credentials
config = {
    "redis_config": {
        "azure_hostname": "your-redis.redis.cache.windows.net",
        "use_azure_entra_id": True,
        "azure_client_id": os.getenv("AZURE_CLIENT_ID"),  # From environment
        "azure_client_secret": os.getenv("AZURE_CLIENT_SECRET"),  # From environment
        "azure_tenant_id": os.getenv("AZURE_TENANT_ID")  # From environment
    }
}
```

### 3. Network Security

- **Use SSL/TLS** (automatically enabled for Azure Redis)
- **Configure firewall rules** in Azure portal
- **Use private endpoints** for enhanced security
- **Enable Azure Defender** for Redis

### 4. Data Privacy

```python
# Configure data retention
config = {
    "redis_config": {
        "azure_hostname": "your-redis.redis.cache.windows.net",
        "azure_access_key": "your-key",
        "key_prefix": "nexamem:secure",  # Organize sensitive data
    }
}

# Enable content processing for PII detection
from nexamem.aimemory import AIMemory

memory = AIMemory(
    azure_hostname="your-redis.redis.cache.windows.net",
    azure_access_key="your-key",
    enable_content_processing=True,  # Automatic PII detection
    enable_audit=True  # Audit trail for compliance
)
```

## Performance Optimization

### Connection Pooling

Redis connections are automatically pooled by the redis-py client:

```python
config = {
    "redis_config": {
        "azure_hostname": "your-redis.redis.cache.windows.net",
        "azure_access_key": "your-key",
        # Connection pool settings
        "max_connections": 20,
        "retry_on_timeout": True,
        "socket_timeout": 5.0,
        "socket_connect_timeout": 5.0
    }
}
```

### Caching Strategy

Configure TTL (Time To Live) for automatic cleanup:

```python
# Set TTL for messages (auto-cleanup)
memory.write(
    scope=scope,
    channel="chat",
    content="Message content",
    ttl_sec=7*24*60*60  # 7 days
)
```

### Monitoring

```python
# Enable metrics collection
memory = AIMemory(
    azure_hostname="your-redis.redis.cache.windows.net",
    azure_access_key="your-key",
    enable_metrics=True  # Performance monitoring
)

# Check connection status
info = memory.redis.get_info()
print(f"Connected: {info['connected']}")
print(f"Azure Redis: {info['is_azure']}")
```

## Error Handling

### Connection Errors

```python
from nexamem.redis_adapter import RedisConnectionError

try:
    initialize(config)
    history = ChatHistory()
except RedisConnectionError as e:
    print(f"Failed to connect to Azure Redis: {e}")
    # Fallback to local storage
    initialize({"history_storage": "memory"})
```

### Authentication Errors

```python
from azure.core.exceptions import ClientAuthenticationError

try:
    # Entra ID authentication
    memory = AIMemory(
        azure_hostname="your-redis.redis.cache.windows.net",
        use_azure_entra_id=True
    )
except ClientAuthenticationError:
    print("Azure authentication failed. Check your credentials.")
```

### Configuration Validation

```python
from nexamem.config import ConfigError

try:
    config = {
        "history_storage": "redis",
        "redis_config": {
            "azure_hostname": "your-redis.redis.cache.windows.net"
            # Missing authentication method
        }
    }
    initialize(config)
except ConfigError as e:
    print(f"Configuration error: {e}")
```

## Testing

### Using FakeRedis

For development and testing without Azure resources:

```python
config = {
    "history_storage": "redis",
    "redis_config": {
        "host": "localhost",
        "use_fakeredis": True  # No real Redis needed
    }
}

initialize(config)
history = ChatHistory()
# Works exactly like real Redis
```

### Integration Tests

```python
import pytest
from nexamem import initialize, ChatHistory

@pytest.fixture
def redis_config():
    return {
        "history_storage": "redis",
        "redis_config": {
            "azure_hostname": "test.redis.cache.windows.net",
            "azure_access_key": "test-key",
            "use_fakeredis": True  # For testing
        }
    }

def test_azure_redis_integration(redis_config):
    initialize(redis_config)
    history = ChatHistory()
    
    history.add_user_message("Test", tokens=1)
    messages = history.get_history()
    
    assert len(messages) == 1
    assert messages[0]['content'] == "Test"
```

## Migration

### From Memory Storage

```python
# Old configuration
old_config = {"history_storage": "memory"}

# New Azure Redis configuration
new_config = {
    "history_storage": "redis",
    "redis_config": {
        "azure_hostname": "your-redis.redis.cache.windows.net",
        "azure_access_key": "your-key"
    }
}

# Migration is automatic - just change config
initialize(new_config)
```

### From File/SQLite Storage

Existing file or SQLite data can be migrated programmatically:

```python
# Read from old storage
old_config = {"history_storage": "file", "file_path": "chat_history.json"}
initialize(old_config)
old_history = ChatHistory()
old_messages = old_history.get_history()

# Switch to Redis
new_config = {
    "history_storage": "redis",
    "redis_config": {"azure_hostname": "...", "azure_access_key": "..."}
}
initialize(new_config)
new_history = ChatHistory()

# Migrate messages
for msg in old_messages:
    new_history.add_message(**msg)
```

## Troubleshooting

### Common Issues

1. **Connection Timeout**
   ```python
   config = {
       "redis_config": {
           "azure_hostname": "your-redis.redis.cache.windows.net",
           "azure_access_key": "your-key",
           "socket_timeout": 10.0,  # Increase timeout
           "socket_connect_timeout": 10.0
       }
   }
   ```

2. **SSL Certificate Issues**
   ```python
   config = {
       "redis_config": {
           "azure_hostname": "your-redis.redis.cache.windows.net",
           "azure_access_key": "your-key",
           "ssl_cert_reqs": None,  # Skip cert validation if needed
           "ssl_check_hostname": False
       }
   }
   ```

3. **Memory Pressure**
   ```python
   # Configure shorter TTL for automatic cleanup
   memory.write(scope, "chat", content, ttl_sec=3600)  # 1 hour
   ```

### Debugging

Enable debug mode for detailed logging:

```python
config = {
    "history_storage": "redis",
    "redis_config": {
        "azure_hostname": "your-redis.redis.cache.windows.net",
        "azure_access_key": "your-key"
    },
    "debug": True  # Detailed logging
}
```

### Performance Monitoring

```python
# Check Redis performance
info = memory.redis.client.info()
print(f"Used memory: {info.get('used_memory_human')}")
print(f"Connected clients: {info.get('connected_clients')}")
print(f"Total commands processed: {info.get('total_commands_processed')}")
```

## Examples

See the `examples/azure_redis_demo.py` file for comprehensive working examples of all authentication methods and use cases.

For additional examples and testing, see `tests/test_azure_redis.py`.
