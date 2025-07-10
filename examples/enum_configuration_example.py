#!/usr/bin/env python3
"""
Example demonstrating NexaMem Redis configuration using enums.
This shows how to use the new StorageType and RedisAuthMethod enums
for cleaner, more type-safe configuration.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from nexamem import initialize, ChatHistory, StorageType, RedisAuthMethod

def demo_enum_configurations():
    """Demonstrate various configuration options using enums."""
    
    print("🎯 NexaMem Enum Configuration Examples")
    print("=" * 50)
    
    # 1. Memory storage with enum
    print("\n1. Memory Storage Configuration:")
    memory_config = {
        "history_storage": StorageType.MEMORY,
        "debug": True
    }
    print(f"   Config: {memory_config}")
    initialize(memory_config)
    
    memory_history = ChatHistory()
    memory_history.add_message("user", "Testing memory storage with enum!")
    print(f"   Messages: {len(memory_history.get_history())}")
    
    # 2. Redis with access key authentication using enum
    print("\n2. Redis Access Key Authentication:")
    redis_access_config = {
        "history_storage": StorageType.REDIS,
        "redis_host": "your-cache.redis.cache.windows.net",
        "redis_port": 6380,
        "redis_password": "your-access-key",
        "redis_ssl": True,
        "redis_auth_method": RedisAuthMethod.ACCESS_KEY,  # Using enum!
        "redis_key_prefix": "enum_demo:",
        "debug": True
    }
    print(f"   Config: {redis_access_config}")
    print("   ✅ Enum value:", RedisAuthMethod.ACCESS_KEY.value)
    
    # 3. Redis with Entra ID authentication using enum
    print("\n3. Redis Entra ID Authentication:")
    redis_entra_config = {
        "history_storage": StorageType.REDIS,
        "redis_host": "your-cache.redis.cache.windows.net",
        "redis_port": 6380,
        "redis_ssl": True,
        "redis_auth_method": RedisAuthMethod.ENTRA_ID,  # Using enum!
        "redis_entra_scope": "https://redis.azure.com/.default",
        "redis_key_prefix": "entra_demo:",
        "debug": True
    }
    print(f"   Config: {redis_entra_config}")
    print("   ✅ Enum value:", RedisAuthMethod.ENTRA_ID.value)
    
    # 4. File storage with enum
    print("\n4. File Storage Configuration:")
    file_config = {
        "history_storage": StorageType.FILE,
        "file_path": "./enum_demo_history.json",
        "debug": True
    }
    print(f"   Config: {file_config}")
    print("   ✅ Enum value:", StorageType.FILE.value)
    
    # 5. SQLite storage with enum
    print("\n5. SQLite Storage Configuration:")
    sqlite_config = {
        "history_storage": StorageType.SQLITE,
        "sqlite_path": "./enum_demo.db",
        "debug": True
    }
    print(f"   Config: {sqlite_config}")
    print("   ✅ Enum value:", StorageType.SQLITE.value)
    
    print("\n🎉 Benefits of Using Enums:")
    print("   • IDE auto-completion and IntelliSense")
    print("   • Type safety and validation")
    print("   • Reduced risk of typos")
    print("   • Better code documentation")
    print("   • Easier refactoring")
    
    print("\n📋 Available Enum Values:")
    print("   StorageType:")
    for storage_type in StorageType:
        print(f"     • {storage_type.name} = '{storage_type.value}'")
    
    print("   RedisAuthMethod:")
    for auth_method in RedisAuthMethod:
        print(f"     • {auth_method.name} = '{auth_method.value}'")

def demo_backward_compatibility():
    """Demonstrate that string values still work for backward compatibility."""
    
    print("\n🔄 Backward Compatibility Test")
    print("=" * 35)
    
    # Old way (still works)
    old_config = {
        "history_storage": "memory",  # String value
        "debug": False
    }
    print("   Old style config (strings):", old_config)
    initialize(old_config)
    
    # New way (recommended)
    new_config = {
        "history_storage": StorageType.MEMORY,  # Enum value
        "debug": False
    }
    print("   New style config (enums):", new_config)
    initialize(new_config)
    
    print("   ✅ Both configurations work identically!")

if __name__ == "__main__":
    try:
        demo_enum_configurations()
        demo_backward_compatibility()
        
        print("\n✅ All enum configuration examples completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("   Note: Some Redis configurations may fail without valid credentials.")
