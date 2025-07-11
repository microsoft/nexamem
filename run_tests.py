#!/usr/bin/env python3
"""
Manual test runner to verify our Azure Redis implementation works.
"""
import sys
import os

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_basic_imports():
    """Test that we can import all the modules."""
    try:
        from nexamem import initialize, ChatHistory, AIMemory, MemoryScope
        from nexamem.redis_adapter import RedisAdapter, AzureRedisConnectionHelper
        from nexamem.config import get_config, ConfigError
        print("✅ All imports successful")
        return True
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False

def test_config_validation():
    """Test config validation including Redis support."""
    try:
        from nexamem import initialize
        from nexamem.config import ConfigError
        
        # Test valid Redis config
        initialize({
            "history_storage": "redis",
            "redis_config": {
                "host": "localhost",
                "port": 6379
            }
        })
        print("✅ Redis config validation passed")
        
        # Test Azure Redis config
        initialize({
            "history_storage": "redis", 
            "redis_config": {
                "azure_hostname": "test.redis.cache.windows.net",
                "azure_access_key": "test_key"
            }
        })
        print("✅ Azure Redis config validation passed")
        
        return True
    except Exception as e:
        print(f"❌ Config validation failed: {e}")
        return False

def test_azure_helper():
    """Test Azure Redis connection helper."""
    try:
        from nexamem.redis_adapter import AzureRedisConnectionHelper
        
        # Test access key config
        config = AzureRedisConnectionHelper.get_azure_redis_config(
            hostname="test.redis.cache.windows.net",
            access_key="test_key"
        )
        
        assert config['host'] == "test.redis.cache.windows.net"
        assert config['port'] == 6380
        assert config['ssl'] is True
        assert config['password'] == "test_key"
        
        print("✅ Azure Redis helper works correctly")
        return True
    except Exception as e:
        print(f"❌ Azure Redis helper failed: {e}")
        return False

def test_memory_storage():
    """Test basic memory storage functionality."""
    try:
        from nexamem import initialize, ChatHistory
        
        # Initialize with memory storage
        initialize({"history_storage": "memory"})
        
        history = ChatHistory()
        history.add_message('user', 'Test message')
        history.add_message('assistant', 'Test response', tokens=10)
        
        messages = history.get_history()
        assert len(messages) == 2
        assert messages[0]['role'] == 'user'
        assert messages[0]['content'] == 'Test message'
        assert messages[1]['tokens'] == 10
        
        print("✅ Memory storage works correctly")
        return True
    except Exception as e:
        print(f"❌ Memory storage failed: {e}")
        return False

def test_enhanced_properties():
    """Test enhanced message properties."""
    try:
        from nexamem import initialize, ChatHistory
        
        initialize({"history_storage": "memory"})
        
        history = ChatHistory()
        history.set_session_context(
            agent_id="test_agent",
            user_id="test_user",
            env="test"
        )
        
        history.add_user_message("Hello", tokens=5)
        messages = history.get_history()
        
        msg = messages[0]
        assert 'agent_id' in msg
        assert 'user_id' in msg
        assert 'session_id' in msg
        assert 'env' in msg
        assert 'timestamp' in msg
        assert 'tokens' in msg
        assert 'data' in msg
        
        assert msg['agent_id'] == "test_agent"
        assert msg['user_id'] == "test_user"
        assert msg['env'] == "test"
        assert msg['tokens'] == 5
        
        print("✅ Enhanced properties work correctly")
        return True
    except Exception as e:
        print(f"❌ Enhanced properties failed: {e}")
        return False

def main():
    """Run all tests."""
    print("🧪 Running NexaMem Test Suite")
    print("=" * 50)
    
    tests = [
        test_basic_imports,
        test_config_validation,
        test_azure_helper,
        test_memory_storage,
        test_enhanced_properties
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")
    
    print("=" * 50)
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed!")
        return 0
    else:
        print("⚠️  Some tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
