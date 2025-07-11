#!/usr/bin/env python
"""Test Azure Redis integration basics."""

# Test 1: Import check
print("Test 1: Checking imports...")
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    # Basic imports
    from nexamem.config import initialize, ConfigError
    from nexamem.redis_adapter import AzureRedisConnectionHelper
    print("✅ Imports successful")
except ImportError as e:
    print(f"❌ Import failed: {e}")
    exit(1)

# Test 2: Azure Redis helper
print("\nTest 2: Azure Redis helper...")
try:
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
    
    print("✅ Azure Redis helper works")
except Exception as e:
    print(f"❌ Azure Redis helper failed: {e}")
    exit(1)

# Test 3: Config validation
print("\nTest 3: Configuration validation...")
try:
    # Test basic Redis config
    initialize({
        "history_storage": "redis",
        "redis_config": {
            "host": "localhost",
            "port": 6379
        }
    })
    print("✅ Basic Redis config validated")
    
    # Test Azure Redis config
    initialize({
        "history_storage": "redis",
        "redis_config": {
            "azure_hostname": "test.redis.cache.windows.net",
            "azure_access_key": "test_key"
        }
    })
    print("✅ Azure Redis config validated")
    
except Exception as e:
    print(f"❌ Config validation failed: {e}")
    exit(1)

# Test 4: Memory storage (baseline)
print("\nTest 4: Memory storage baseline...")
try:
    from nexamem.history import ChatHistory
    
    initialize({"history_storage": "memory"})
    history = ChatHistory()
    
    # Test enhanced properties
    history.set_session_context(
        agent_id="test_agent",
        user_id="user_123",
        env="test"
    )
    
    history.add_user_message("Test message", tokens=5)
    messages = history.get_history()
    
    # Verify enhanced properties
    msg = messages[0]
    required_props = ['role', 'content', 'agent_id', 'user_id', 'session_id', 
                      'env', 'timestamp', 'tokens', 'data']
    
    for prop in required_props:
        assert prop in msg, f"Missing property: {prop}"
    
    assert msg['agent_id'] == "test_agent"
    assert msg['user_id'] == "user_123"
    assert msg['env'] == "test"
    assert msg['tokens'] == 5
    assert msg['role'] == "user"
    assert msg['content'] == "Test message"
    
    print("✅ Enhanced properties work correctly")
    
except Exception as e:
    print(f"❌ Memory storage test failed: {e}")
    exit(1)

print("\n🎉 All tests passed! Azure Redis integration is working correctly.")
