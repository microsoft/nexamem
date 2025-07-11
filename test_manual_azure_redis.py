#!/usr/bin/env python3
"""
Simple manual test of Azure Redis functionality.
This script tests the implementation without relying on external test runners.
"""

def test_imports():
    """Test that all Azure Redis components can be imported."""
    try:
        import sys
        import os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
        
        from nexamem.redis_adapter import (
            AzureRedisConnectionHelper, 
            RedisAdapter, 
            AsyncRedisAdapter,
            RedisConnectionError
        )
        from nexamem.config import initialize, ConfigError
        from nexamem.history import ChatHistory
        
        print("✅ All imports successful")
        return True
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False

def test_azure_connection_helper():
    """Test Azure Redis connection helper methods."""
    try:
        import sys
        import os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
        
        from nexamem.redis_adapter import AzureRedisConnectionHelper
        
        # Test access key configuration
        config = AzureRedisConnectionHelper.get_azure_redis_config(
            hostname="test.redis.cache.windows.net",
            access_key="test_access_key"
        )
        
        assert config['host'] == "test.redis.cache.windows.net"
        assert config['port'] == 6380
        assert config['ssl'] is True
        assert config['password'] == "test_access_key"
        
        # Test connection string
        conn_str = AzureRedisConnectionHelper.create_azure_connection_string(
            hostname="test.redis.cache.windows.net",
            access_key="test_key"
        )
        expected = "rediss://:test_key@test.redis.cache.windows.net:6380"
        assert conn_str == expected
        
        print("✅ Azure connection helper working correctly")
        return True
    except Exception as e:
        print(f"❌ Azure connection helper failed: {e}")
        return False

def test_config_validation():
    """Test configuration validation for Redis storage."""
    try:
        import sys
        import os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
        
        from nexamem.config import initialize, ConfigError
        
        # Test valid configuration
        valid_config = {
            "history_storage": "redis",
            "redis_config": {
                "host": "localhost",
                "use_fakeredis": True
            }
        }
        initialize(valid_config)
        
        # Test Azure Redis config validation - should fail without auth
        try:
            invalid_config = {
                "history_storage": "redis",
                "redis_config": {
                    "azure_hostname": "test.redis.cache.windows.net"
                }
            }
            initialize(invalid_config)
            print("❌ Should have failed validation")
            return False
        except ConfigError:
            pass  # Expected
        
        # Test valid Azure config
        azure_config = {
            "history_storage": "redis",
            "redis_config": {
                "azure_hostname": "test.redis.cache.windows.net",
                "azure_access_key": "test_key"
            }
        }
        initialize(azure_config)
        
        print("✅ Configuration validation working correctly")
        return True
    except Exception as e:
        print(f"❌ Configuration validation failed: {e}")
        return False

def test_redis_storage():
    """Test Redis storage functionality with fakeredis."""
    try:
        import sys
        import os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
        
        from nexamem.config import initialize
        from nexamem.history import ChatHistory
        
        # Configure with fakeredis
        config = {
            "history_storage": "redis",
            "redis_config": {
                "host": "localhost",
                "use_fakeredis": True,
                "key_prefix": "test_nexamem"
            }
        }
        initialize(config)
        
        # Test basic operations
        history = ChatHistory()
        history.set_session_context(
            agent_id="test_agent",
            user_id="test_user",
            env="test"
        )
        
        # Add messages
        history.add_user_message("Hello Redis!", tokens=3)
        history.add_assistant_message("Redis is working!", tokens=4)
        history.add_system_message("Test completed", tokens=0)
        
        # Retrieve messages
        messages = history.get_history()
        assert len(messages) == 3
        assert messages[0]['content'] == "Hello Redis!"
        assert messages[1]['content'] == "Redis is working!"
        assert messages[2]['content'] == "Test completed"
        
        # Test all required properties
        expected_props = [
            'role', 'content', 'agent_id', 'user_id', 'session_id',
            'env', 'timestamp', 'tokens', 'data'
        ]
        for msg in messages:
            for prop in expected_props:
                assert prop in msg, f"Missing property: {prop}"
        
        # Test Redis query
        results = history.query_redis("*", limit=10)
        assert len(results) >= 3
        
        # Test clear
        history.clear()
        cleared_messages = history.get_history()
        assert len(cleared_messages) == 0
        
        print("✅ Redis storage functionality working correctly")
        return True
    except Exception as e:
        print(f"❌ Redis storage test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_azure_redis_adapter():
    """Test Azure Redis adapter creation."""
    try:
        import sys
        import os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
        
        from nexamem.redis_adapter import RedisAdapter
        
        # Test Azure Redis adapter creation with fakeredis override
        adapter = RedisAdapter(
            azure_hostname="test.redis.cache.windows.net",
            azure_access_key="test_key",
            use_fakeredis=True  # Override for testing
        )
        
        assert adapter.is_azure is True
        assert adapter.ping() is True
        
        info = adapter.get_info()
        assert info['is_azure'] is True
        assert info['use_fakeredis'] is True
        
        print("✅ Azure Redis adapter working correctly")
        return True
    except Exception as e:
        print(f"❌ Azure Redis adapter test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests."""
    print("Manual Azure Redis Integration Test")
    print("=" * 50)
    
    tests = [
        ("Component Imports", test_imports),
        ("Azure Connection Helper", test_azure_connection_helper),
        ("Configuration Validation", test_config_validation),
        ("Redis Storage Operations", test_redis_storage),
        ("Azure Redis Adapter", test_azure_redis_adapter),
    ]
    
    results = []
    for name, test_func in tests:
        print(f"\nTesting: {name}")
        try:
            success = test_func()
            results.append((name, success))
        except Exception as e:
            print(f"❌ Unexpected error in {name}: {e}")
            results.append((name, False))
    
    print("\n" + "=" * 50)
    print("Test Results:")
    
    all_passed = True
    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {name}: {status}")
        if not success:
            all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 All tests passed! Azure Redis integration is working correctly.")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
