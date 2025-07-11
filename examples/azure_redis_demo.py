#!/usr/bin/env python3
"""
Azure Cache for Redis integration examples for NexaMem.

This example demonstrates how to use NexaMem with Azure Cache for Redis
supporting both access keys and Entra ID authentication.
"""
import os
import sys
from typing import Dict, Any

# Add the src directory to the Python path for local imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from nexamem import initialize, ChatHistory
from nexamem.redis_adapter import AzureRedisConnectionHelper


def example_azure_redis_with_access_key():
    """
    Example: Connect to Azure Cache for Redis using access key.
    
    This is the most straightforward method for Azure Redis.
    """
    print("=== Azure Redis with Access Key ===")
    
    # Configuration for Azure Redis with access key
    config = {
        "history_storage": "redis",
        "redis_config": {
            # Azure Redis hostname (replace with your actual hostname)
            "azure_hostname": "your-redis.redis.cache.windows.net",
            
            # Primary or secondary access key from Azure portal
            "azure_access_key": "your-redis-access-key-here",
            
            # Optional: Custom key prefix for organizing data
            "key_prefix": "nexamem:chatbot",
            
            # Optional: Database number (default: 0)
            "db": 0
        },
        "debug": True
    }
    
    try:
        # Initialize NexaMem with Azure Redis
        initialize(config)
        
        # Create chat history instance
        history = ChatHistory()
        
        # Set session context
        history.set_session_context(
            agent_id="azure_assistant",
            user_id="user_123",
            env="production"
        )
        
        # Add some messages
        history.add_user_message("Hello from Azure Redis!", tokens=5)
        history.add_assistant_message("Connected successfully to Azure Cache for Redis!", tokens=10)
        
        # Retrieve and display messages
        messages = history.get_history()
        print(f"Successfully stored and retrieved {len(messages)} messages")
        
        for msg in messages:
            print(f"  [{msg['role']}]: {msg['content']}")
        
        return True
        
    except Exception as e:
        print(f"Error with Azure Redis access key: {e}")
        return False


def example_azure_redis_with_entra_id():
    """
    Example: Connect to Azure Cache for Redis using Entra ID (Azure AD).
    
    This method uses Azure identity for authentication.
    Requires the redis-py client to support AAD authentication.
    """
    print("\n=== Azure Redis with Entra ID ===")
    
    # Configuration for Azure Redis with Entra ID
    config = {
        "history_storage": "redis",
        "redis_config": {
            # Azure Redis hostname
            "azure_hostname": "your-redis.redis.cache.windows.net",
            
            # Enable Entra ID authentication
            "use_azure_entra_id": True,
            
            # Username for Entra ID (often same as client ID)
            "azure_username": "your-client-id-or-username",
            
            # Optional: For service principal authentication
            # "azure_client_id": "your-client-id",
            # "azure_client_secret": "your-client-secret", 
            # "azure_tenant_id": "your-tenant-id",
            
            "key_prefix": "nexamem:entra_id",
            "db": 0
        },
        "debug": True
    }
    
    try:
        # Initialize NexaMem with Entra ID
        initialize(config)
        
        history = ChatHistory()
        history.set_session_context(
            agent_id="entra_id_assistant",
            user_id="user_456",
            env="production"
        )
        
        # Add messages
        history.add_user_message("Testing Entra ID authentication", tokens=6)
        history.add_assistant_message("Entra ID authentication successful!", tokens=8)
        
        # Display results
        messages = history.get_history()
        print(f"Successfully authenticated with Entra ID: {len(messages)} messages")
        
        return True
        
    except Exception as e:
        print(f"Error with Entra ID authentication: {e}")
        print("Note: Ensure your Azure identity has proper Redis permissions")
        return False


def example_azure_redis_with_keyvault():
    """
    Example: Connect to Azure Cache for Redis with Key Vault for secret management.
    
    This method retrieves the Redis access key from Azure Key Vault.
    """
    print("\n=== Azure Redis with Key Vault ===")
    
    config = {
        "history_storage": "redis",
        "redis_config": {
            # Azure Redis hostname
            "azure_hostname": "your-redis.redis.cache.windows.net",
            
            # Azure Key Vault configuration
            "azure_keyvault_url": "https://your-keyvault.vault.azure.net/",
            "azure_secret_name": "redis-access-key",
            
            "key_prefix": "nexamem:keyvault",
            "db": 0
        },
        "debug": True
    }
    
    try:
        # Initialize NexaMem with Key Vault
        initialize(config)
        
        history = ChatHistory()
        history.set_session_context(
            agent_id="keyvault_assistant", 
            user_id="user_789",
            env="production"
        )
        
        # Add messages
        history.add_user_message("Testing Key Vault integration", tokens=7)
        history.add_assistant_message("Key Vault secret retrieval successful!", tokens=9)
        
        # Display results
        messages = history.get_history()
        print(f"Successfully connected via Key Vault: {len(messages)} messages")
        
        return True
        
    except Exception as e:
        print(f"Error with Key Vault integration: {e}")
        print("Note: Ensure your identity has Key Vault access permissions")
        return False


def example_standard_redis():
    """
    Example: Connect to standard Redis (non-Azure).
    
    For comparison with Azure Redis configurations.
    """
    print("\n=== Standard Redis (Non-Azure) ===")
    
    config = {
        "history_storage": "redis", 
        "redis_config": {
            # Standard Redis configuration
            "host": "localhost",
            "port": 6379,
            "password": "your-redis-password",  # If authentication required
            "ssl": False,  # Set to True for SSL connections
            "db": 0,
            
            # For testing without a real Redis server
            "use_fakeredis": True,
            
            "key_prefix": "nexamem:standard"
        },
        "debug": True
    }
    
    try:
        # Initialize with standard Redis
        initialize(config)
        
        history = ChatHistory()
        history.set_session_context(
            agent_id="standard_assistant",
            user_id="user_std",
            env="development"
        )
        
        # Add messages
        history.add_user_message("Testing standard Redis", tokens=4)
        history.add_assistant_message("Standard Redis connection works!", tokens=7)
        
        # Test Redis-specific query functionality
        results = history.query_redis("*", limit=10)
        print(f"Redis query returned {len(results)} messages")
        
        messages = history.get_history()
        print(f"Standard Redis working: {len(messages)} messages")
        
        return True
        
    except Exception as e:
        print(f"Error with standard Redis: {e}")
        return False


def example_redis_connection_helper():
    """
    Example: Using AzureRedisConnectionHelper directly.
    
    Demonstrates low-level configuration utilities.
    """
    print("\n=== Azure Redis Connection Helper ===")
    
    try:
        # Example 1: Get Azure config with access key
        azure_config = AzureRedisConnectionHelper.get_azure_redis_config(
            hostname="your-redis.redis.cache.windows.net",
            access_key="your-access-key"
        )
        print("Azure config with access key:")
        for key, value in azure_config.items():
            print(f"  {key}: {value}")
        
        # Example 2: Create connection string
        conn_str = AzureRedisConnectionHelper.create_azure_connection_string(
            hostname="your-redis.redis.cache.windows.net",
            access_key="your-access-key"
        )
        print(f"\nAzure Redis connection string: {conn_str}")
        
        return True
        
    except Exception as e:
        print(f"Error with connection helper: {e}")
        return False


def example_environment_based_config():
    """
    Example: Environment-based configuration for different deployment scenarios.
    
    Shows how to configure Redis based on environment variables.
    """
    print("\n=== Environment-Based Configuration ===")
    
    # Read configuration from environment variables
    redis_hostname = os.getenv('AZURE_REDIS_HOSTNAME')
    redis_access_key = os.getenv('AZURE_REDIS_ACCESS_KEY')
    use_entra_id = os.getenv('AZURE_REDIS_USE_ENTRA_ID', 'false').lower() == 'true'
    keyvault_url = os.getenv('AZURE_KEYVAULT_URL')
    secret_name = os.getenv('AZURE_REDIS_SECRET_NAME')
    
    if redis_hostname:
        redis_config: Dict[str, Any] = {
            "azure_hostname": redis_hostname
        }
        
        if redis_access_key:
            redis_config["azure_access_key"] = redis_access_key
        elif use_entra_id:
            redis_config["use_azure_entra_id"] = True
            # Add additional Entra ID config from environment if needed
            if os.getenv('AZURE_CLIENT_ID'):
                redis_config["azure_client_id"] = os.getenv('AZURE_CLIENT_ID')
                redis_config["azure_client_secret"] = os.getenv('AZURE_CLIENT_SECRET')
                redis_config["azure_tenant_id"] = os.getenv('AZURE_TENANT_ID')
        elif keyvault_url and secret_name:
            redis_config["azure_keyvault_url"] = keyvault_url
            redis_config["azure_secret_name"] = secret_name
        else:
            print("No valid Azure Redis authentication method found in environment")
            return False
        
        config = {
            "history_storage": "redis",
            "redis_config": redis_config,
            "debug": True
        }
        
        try:
            initialize(config)
            print("Successfully configured Redis from environment variables")
            
            # Test basic functionality
            history = ChatHistory()
            history.add_user_message("Environment config test", tokens=4)
            messages = history.get_history()
            print(f"Environment-based config working: {len(messages)} messages")
            
            return True
            
        except Exception as e:
            print(f"Error with environment-based config: {e}")
            return False
    else:
        print("No Azure Redis hostname found in environment variables")
        print("Set AZURE_REDIS_HOSTNAME and authentication method (access key, Entra ID, or Key Vault)")
        return False


def main():
    """
    Run all Azure Redis examples.
    
    Note: Most examples will fail without proper Azure resources and credentials.
    This is expected and demonstrates the configuration patterns.
    """
    print("Azure Cache for Redis Integration Examples")
    print("=" * 50)
    
    examples = [
        ("Standard Redis (FakeRedis)", example_standard_redis),
        ("Azure Redis Connection Helper", example_redis_connection_helper),
        ("Azure Redis with Access Key", example_azure_redis_with_access_key),
        ("Azure Redis with Entra ID", example_azure_redis_with_entra_id),
        ("Azure Redis with Key Vault", example_azure_redis_with_keyvault),
        ("Environment-Based Config", example_environment_based_config),
    ]
    
    results = []
    for name, example_func in examples:
        try:
            success = example_func()
            results.append((name, success))
        except Exception as e:
            print(f"Unexpected error in {name}: {e}")
            results.append((name, False))
    
    print("\n" + "=" * 50)
    print("Summary:")
    for name, success in results:
        status = "✅ SUCCESS" if success else "❌ FAILED (expected without Azure resources)"
        print(f"  {name}: {status}")
    
    print("\nNote: Most examples require actual Azure resources and will show expected failures.")
    print("The Standard Redis example with FakeRedis should work without external dependencies.")


if __name__ == "__main__":
    main()
