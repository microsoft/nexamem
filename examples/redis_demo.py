"""
Demo script: NexaMem with Azure Redis Cache Support

This demo shows the new Redis functionality without requiring a real Redis server.
It uses fakeredis to simulate Redis operations.
"""
import sys
import os

# Add src to path for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from nexamem import initialize, ChatHistory
import fakeredis

def demo_redis_features():
    print("🎯 NexaMem Redis Demo")
    print("=" * 50)
    
    # Monkey patch redis for demo
    import nexamem.history
    
    # Create a mock Redis class that uses FakeRedis
    class MockRedis:
        @staticmethod
        def Redis(**kwargs):
            return fakeredis.FakeRedis()
    
    nexamem.history.redis = MockRedis()
    
    # Azure Redis Cache configuration
    azure_config = {
        "history_storage": "redis",
        "redis_host": "demo-cache.redis.cache.windows.net",
        "redis_port": 6380,
        "redis_password": "demo-key",
        "redis_ssl": True,
        "redis_db": 0,
        "redis_key_prefix": "myapp:",
        "debug": True
    }
    
    print("🔧 Initializing with Azure Redis Cache configuration...")
    initialize(azure_config)
    
    print("\n💾 Creating ChatHistory instance...")
    history = ChatHistory()
    
    print("\n📝 Adding conversation messages...")
    messages = [
        ("user", "Hello! I need help with Azure Redis Cache."),
        ("assistant", "I'd be happy to help! Azure Redis Cache is a fully managed, in-memory cache service."),
        ("user", "What are the main benefits?"),
        ("assistant", "Key benefits include: high performance, scalability, security, and global distribution."),
        ("user", "How do I monitor Redis performance?"),
        ("assistant", "You can use Azure Monitor, Redis CLI, or the Azure portal metrics.")
    ]
    
    for role, content in messages:
        history.add_message(role, content)
        print(f"   ✅ Added [{role}]: {content[:50]}...")
    
    print(f"\n📊 Total messages stored: {len(history.get_history())}")
    
    print("\n🔍 Demonstrating Redis query features...")
    
    # Search for Azure-related messages
    azure_messages = history.query_redis(pattern="Azure")
    print(f"   🔎 Found {len(azure_messages)} messages mentioning 'Azure':")
    for msg in azure_messages:
        print(f"      [{msg['role']}]: {msg['content'][:60]}...")
    
    # Get specific message
    print(f"\n📋 First message: {history.get_message_at(0)}")
    
    # Show Redis connection info
    print("\n📈 Redis Connection Info:")
    try:
        info = history.get_redis_info()
        for key, value in info.items():
            print(f"   {key}: {value}")
    except Exception as e:
        print(f"   Info not available in demo mode: {e}")
    
    print("\n🧹 Demonstrating clear functionality...")
    history.clear()
    print(f"   Messages after clear: {len(history.get_history())}")
    
    print("\n✅ Demo completed successfully!")
    print("💡 This shows how NexaMem integrates with Azure Redis Cache")
    print("🔗 Use the same patterns with a real Redis instance in production")

if __name__ == "__main__":
    demo_redis_features()
