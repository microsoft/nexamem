#!/usr/bin/env python3
"""
Simple Azure Redis verification script that can be run when Python environment is working.
"""
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_azure_redis_imports():
    """Test that Azure Redis components can be imported."""
    try:
        from nexamem.redis_adapter import AzureRedisConnectionHelper, RedisAdapter, AsyncRedisAdapter
        from nexamem.config import initialize
        from nexamem.history import ChatHistory
        print("✅ All Azure Redis imports successful")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def test_azure_redis_config_helper():
    """Test Azure Redis configuration helper."""
    try:
        from nexamem.redis_adapter import AzureRedisConnectionHelper
        
        # Test basic configuration
        config = AzureRedisConnectionHelper.get_azure_redis_config(
            hostname="test.redis.cache.windows.net",
            access_key="test_key"
        )
        
        expected_keys = ['host', 'port', 'ssl', 'password', 'decode_responses']
        for key in expected_keys:
            assert key in config, f"Missing key: {key}"
        
        assert config['host'] == "test.redis.cache.windows.net"
        assert config['port'] == 6380
        assert config['ssl'] is True
        assert config['password'] == "test_key"
        
        print("✅ Azure Redis configuration helper works correctly")
        return True
    except Exception as e:
        print(f"❌ Azure Redis config helper error: {e}")
        return False

def test_redis_storage_config():
    """Test Redis storage configuration."""
    try:
        from nexamem.config import initialize, ConfigError
        
        # Test valid Redis config
        config = {
            "history_storage": "redis",
            "redis_config": {
                "host": "localhost",
                "use_fakeredis": True
            }
        }
        initialize(config)
        print("✅ Redis storage configuration validation works")
        return True
    except Exception as e:
        print(f"❌ Redis storage config error: {e}")
        return False

def test_azure_redis_config_validation():
    """Test Azure Redis configuration validation."""
    try:
        from nexamem.config import initialize, ConfigError
        
        # Test invalid Azure config (missing auth)
        try:
            config = {
                "history_storage": "redis",
                "redis_config": {
                    "azure_hostname": "test.redis.cache.windows.net"
                }
            }
            initialize(config)
            print("❌ Should have failed with missing auth")
            return False
        except ConfigError:
            print("✅ Azure Redis auth validation works correctly")
        
        # Test valid Azure config with access key
        config = {
            "history_storage": "redis",
            "redis_config": {
                "azure_hostname": "test.redis.cache.windows.net",
                "azure_access_key": "test_key"
            }
        }
        initialize(config)
        print("✅ Azure Redis access key validation works")
        
        return True
    except Exception as e:
        print(f"❌ Azure Redis config validation error: {e}")
        return False

def test_chat_history_redis():
    """Test ChatHistory with Redis backend."""
    try:
        from nexamem.config import initialize
        from nexamem.history import ChatHistory
        
        # Configure with fakeredis for testing
        config = {
            "history_storage": "redis",
            "redis_config": {
                "host": "localhost",
                "use_fakeredis": True
            }
        }
        initialize(config)
        
        # Test basic functionality
        history = ChatHistory()
        history.set_session_context(
            agent_id="test_agent",
            user_id="test_user",
            env="test"
        )
        
        # Add messages
        history.add_user_message("Test message", tokens=3)
        history.add_assistant_message("Test response", tokens=5)
        
        # Get messages
        messages = history.get_history()
        assert len(messages) == 2
        assert messages[0]['content'] == "Test message"
        assert messages[1]['content'] == "Test response"
        
        print("✅ ChatHistory with Redis backend works correctly")
        return True
    except Exception as e:
        print(f"❌ ChatHistory Redis error: {e}")
        return False

def main():
    """Run all verification tests."""
    print("Azure Cache for Redis Integration Verification")
    print("=" * 50)
    
    tests = [
        ("Imports", test_azure_redis_imports),
        ("Config Helper", test_azure_redis_config_helper),
        ("Redis Storage Config", test_redis_storage_config),
        ("Azure Config Validation", test_azure_redis_config_validation),
        ("ChatHistory Redis", test_chat_history_redis),
    ]
    
    results = []
    for name, test_func in tests:
        print(f"\nTesting {name}...")
        try:
            success = test_func()
            results.append((name, success))
        except Exception as e:
            print(f"❌ Unexpected error in {name}: {e}")
            results.append((name, False))
    
    print("\n" + "=" * 50)
    print("Verification Summary:")
    all_passed = True
    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {name}: {status}")
        if not success:
            all_passed = False
    
    if all_passed:
        print("\n🎉 All tests passed! Azure Redis integration is working correctly.")
    else:
        print("\n⚠️ Some tests failed. Check the output above for details.")
    
    return all_passed

if __name__ == "__main__":
    main()
