import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

print("Testing basic imports...")
try:
    from nexamem import initialize, ChatHistory
    print("✅ Basic imports work")
except Exception as e:
    print(f"❌ Import failed: {e}")
    sys.exit(1)

print("Testing Redis config support...")
try:
    initialize({
        "history_storage": "redis",
        "redis_config": {
            "azure_hostname": "test.redis.cache.windows.net",
            "azure_access_key": "test_key"
        }
    })
    print("✅ Azure Redis config works")
except Exception as e:
    print(f"❌ Azure Redis config failed: {e}")
    sys.exit(1)

print("Testing basic functionality...")
try:
    initialize({"history_storage": "memory"})
    history = ChatHistory()
    history.add_message('user', 'Test')
    messages = history.get_history()
    assert len(messages) == 1
    assert 'agent_id' in messages[0]
    assert 'timestamp' in messages[0]
    print("✅ Basic functionality works")
except Exception as e:
    print(f"❌ Basic functionality failed: {e}")
    sys.exit(1)

print("🎉 All basic tests passed!")
