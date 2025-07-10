# Azure Redis Cache Support for NexaMem

This document describes the comprehensive Azure Redis Cache support added to NexaMem, including both access key and Microsoft Entra ID authentication.

## Overview

NexaMem now supports Redis as a storage backend, with specific optimizations for Azure Redis Cache and two authentication methods:

- **Access Key Authentication**: Traditional shared secret authentication
- **Microsoft Entra ID Authentication**: Modern token-based authentication (recommended)

This enables:

- **Distributed storage**: Share chat history across multiple application instances
- **High performance**: In-memory storage with sub-millisecond latency
- **Scalability**: Handle thousands of concurrent connections
- **Security**: SSL/TLS encryption and enterprise-grade authentication
- **Persistence**: Optional data persistence with Azure Redis Cache

## Features Added

### 1. Redis Storage Backend
- New `"redis"` option for `history_storage` configuration
- Optimized connection settings for Azure Redis Cache
- Automatic SSL configuration for Azure Redis
- Connection pooling and retry logic

### 2. Configuration Options
- `redis_host`: Redis server hostname (required)
- `redis_port`: Port number (defaults to 6380 for Azure)
- `redis_password`: Authentication password (required for access key auth)
- `redis_ssl`: SSL/TLS encryption (defaults to True)
- `redis_db`: Database number (defaults to 0)
- `redis_key_prefix`: Key namespace prefix (defaults to "nexamem:")
- `redis_auth_method`: "access_key" or "entra_id" (defaults to "access_key")
- `redis_entra_scope`: Entra ID scope (defaults to Azure Redis scope)

### 3. New Methods
- `query_redis(pattern, limit)`: Search messages with pattern matching
- `get_redis_info()`: Get connection and performance information

### 4. Azure Redis Cache Defaults
- Port 6380 (SSL port)
- SSL enabled by default
- Optimized connection timeouts
- Health check intervals

## Usage Examples

### Access Key Authentication
```python
from nexamem import initialize, ChatHistory

# Local Redis (development)
initialize({
    "history_storage": "redis",
    "redis_host": "localhost",
    "redis_port": 6379,
    "redis_ssl": False,
    "redis_password": "your-password"
})
```

### Microsoft Entra ID Authentication (Recommended)
```python
from nexamem import initialize, ChatHistory

# Azure Redis Cache with Entra ID (production)
initialize({
    "history_storage": "redis", 
    "redis_host": "your-cache.redis.cache.windows.net",
    "redis_auth_method": "entra_id",  # Use Entra ID
    "redis_ssl": True,
    "redis_key_prefix": "myapp:"
})

history = ChatHistory()
history.add_message("user", "Hello!")

# Redis-specific features work with both auth methods
matches = history.query_redis(pattern="hello", limit=10)
info = history.get_redis_info()
```

## Benefits for Production Applications

### Scalability
- Horizontal scaling across multiple app instances
- Shared state between load-balanced servers
- Handle thousands of concurrent users

### Performance
- Sub-millisecond response times
- In-memory data structure operations
- Efficient key-value lookups

### Reliability
- Azure Redis Cache provides 99.9% SLA
- Automatic failover and clustering
- Data persistence options

### Security
- SSL/TLS encryption in transit
- Azure Active Directory integration
- VNet integration support

### Microsoft Entra ID Benefits
- **No shared secrets**: Token-based authentication eliminates password management
- **Centralized identity**: Integrated with your Azure AD tenant
- **Role-based access control**: Fine-grained permissions with Azure RBAC
- **Automatic token refresh**: Handled by azure-identity library
- **Better auditing**: Centralized logging and compliance tracking
- **Zero trust security**: Modern authentication aligned with Zero Trust principles

## Testing

Comprehensive test suite added in `tests/test_redis.py`:
- Connection parameter validation
- Basic CRUD operations
- Persistence across instances
- Query functionality
- Error handling
- Azure-specific configuration
- Debug mode testing

Uses `fakeredis` for testing without requiring a real Redis instance.

## Examples

Four example scripts demonstrate usage:
- `examples/azure_redis_example.py`: Azure Redis Cache with access key authentication
- `examples/azure_entra_id_example.py`: Azure Redis Cache with Microsoft Entra ID authentication
- `examples/local_redis_example.py`: Local development setup
- `examples/redis_demo.py`: Interactive demo using fakeredis

## Migration Guide

Existing NexaMem applications continue to work without changes. To add Redis support:

1. **Install dependencies**: `pip install redis azure-identity` (already in requirements)
2. **Update configuration**: Change `history_storage` to `"redis"`
3. **Add Redis settings**: Provide `redis_host` and choose authentication method
4. **Choose authentication**: Use `redis_auth_method: "entra_id"` for enhanced security
5. **Test locally**: Use local Redis for development
6. **Deploy to Azure**: Use Azure Redis Cache for production

## Best Practices

### Development
- Use local Redis for development and testing
- Enable debug mode for troubleshooting
- Use different key prefixes for different environments

### Production
- Use Azure Redis Cache for reliability and scalability
- **Prefer Entra ID authentication** over access keys for better security
- Enable SSL for security
- Set appropriate connection timeouts
- Monitor performance with Azure Monitor
- Use connection pooling for high-traffic applications

### Authentication
- **Access Keys**: Use for simple setups and legacy compatibility
- **Entra ID**: Use for enterprise environments and enhanced security
- Store credentials securely (Key Vault, environment variables)
- Assign minimal required Redis roles (Redis Data Contributor)
- Rotate access keys regularly if using access key authentication

### Security
- Store Redis password in environment variables
- Use Azure Key Vault for credential management
- Enable Redis AUTH and SSL/TLS
- Configure network security groups for VNet access

## Troubleshooting

### Common Issues
1. **Connection refused**: Check Redis server is running and accessible
2. **Authentication failed**: Verify Redis password and permissions
3. **SSL errors**: Ensure SSL settings match Redis configuration
4. **Timeout errors**: Adjust connection timeout settings

### Debug Mode
Enable debug mode to see detailed Redis operations:
```python
initialize({
    "history_storage": "redis",
    "redis_host": "localhost", 
    "debug": True  # Shows Redis operations
})
```

### Connection Info
Use `get_redis_info()` to check connection status and statistics:
```python
history = ChatHistory()
info = history.get_redis_info()
print(f"Connected to: {info['host']}:{info['port']}")
print(f"Messages stored: {info['history_length']}")
```

## Type-Safe Configuration with Enums

NexaMem provides enums to make Redis configuration more type-safe and prevent common configuration errors:

```python
from nexamem import StorageType, RedisAuthMethod

# Type-safe Redis configuration using enums
config = {
    "history_storage": StorageType.REDIS,  # IDE auto-completion
    "redis_host": "your-cache.redis.cache.windows.net",
    "redis_auth_method": RedisAuthMethod.ENTRA_ID,  # No typos!
    # ... other configuration
}
```

### Available Enums

- `StorageType.REDIS` = "redis"
- `RedisAuthMethod.ACCESS_KEY` = "access_key"  
- `RedisAuthMethod.ENTRA_ID` = "entra_id"
- `RedisAuthMethod.AZURE_AD` = "entra_id" (alias for backward compatibility)

**Benefits**: IDE auto-completion, type safety, no typos, better refactoring support, while maintaining full backward compatibility with string values.
