"""
Example: Using NexaMem with Local Redis for Development

This example shows how to use NexaMem with a local Redis instance during development.
Perfect for testing before deploying to Azure Redis Cache.
"""
from nexamem import initialize, ChatHistory

def main():
    # Local Redis configuration for development
    redis_config = {
        "history_storage": "redis",
        "redis_host": "localhost",     # Local Redis instance
        "redis_port": 6379,           # Standard Redis port
        "redis_ssl": False,           # No SSL for local development
        "redis_db": 1,                # Use database 1 to avoid conflicts
        "redis_key_prefix": "dev_nexamem:",  # Development namespace
        "debug": True                 # Enable debug output
    }
    
    try:
        print("🚀 Starting local Redis development example...")
        
        # Initialize NexaMem
        initialize(redis_config)
        
        # Create ChatHistory instance
        history = ChatHistory()
        
        # Show current state
        existing_messages = history.get_history()
        if existing_messages:
            print(f"📜 Found {len(existing_messages)} existing messages in Redis")
            for i, msg in enumerate(existing_messages):
                print(f"   {i+1}. [{msg['role']}]: {msg['content'][:50]}...")
        else:
            print("📜 No existing messages found - starting fresh")
        
        # Add new messages
        print("\n💬 Adding new messages...")
        history.add_message("user", "I'm testing local Redis with NexaMem")
        history.add_message("assistant", "Great! Local Redis is perfect for development and testing.")
        history.add_message("user", "What are the advantages?")
        history.add_message("assistant", "Local Redis offers fast development cycles, easy debugging, and no cloud costs during development.")
        
        # Show updated history
        all_messages = history.get_history()
        print(f"\n📋 Total messages now: {len(all_messages)}")
        
        # Demonstrate query functionality
        print("\n🔍 Searching for messages containing 'Redis'...")
        redis_messages = history.query_redis(pattern="Redis")
        for msg in redis_messages:
            print(f"   [{msg['role']}]: {msg['content']}")
        
        # Show Redis connection info
        info = history.get_redis_info()
        print("\n📊 Redis Connection Status:")
        print(f"   Connected to: {info.get('host')}:{info.get('port')}")
        print(f"   Messages stored: {info.get('history_length')}")
        print(f"   Redis version: {info.get('redis_version')}")
        
        print("\n✅ Local Redis example completed successfully!")
        print("💡 Try running this script multiple times to see message persistence")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\n💡 To use local Redis:")
        print("   1. Install Redis: https://redis.io/download")
        print("   2. Start Redis server: redis-server")
        print("   3. Install Python Redis client: pip install redis")
        print("   4. Run this script")

if __name__ == "__main__":
    main()
