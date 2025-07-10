"""
Example: Using NexaMem with Azure Redis Cache

This example demonstrates how to configure and use NexaMem with Azure Redis Cache
for persistent chat history storage across application instances.
"""
import os
from nexamem import initialize, ChatHistory

def main():
    # Azure Redis Cache configuration
    # You would get these values from your Azure Redis Cache instance
    redis_config = {
        "history_storage": "redis",
        "redis_host": "your-cache-name.redis.cache.windows.net",  # Replace with your cache name
        "redis_port": 6380,  # Azure Redis default SSL port
        "redis_password": os.getenv("AZURE_REDIS_KEY"),  # Set this environment variable
        "redis_ssl": True,   # Azure Redis requires SSL
        "redis_db": 0,       # Use database 0
        "redis_key_prefix": "my_app:",  # Optional: namespace your keys
        "debug": True        # Enable debug output
    }
    
    # Alternative: Local Redis configuration for development
    # redis_config = {
    #     "history_storage": "redis", 
    #     "redis_host": "localhost",
    #     "redis_port": 6379,
    #     "redis_ssl": False,
    #     "redis_key_prefix": "dev_nexamem:",
    #     "debug": True
    # }
    
    try:
        # Initialize NexaMem with Redis configuration
        initialize(redis_config)
        print("✅ NexaMem initialized with Azure Redis Cache!")
        
        # Create ChatHistory instance
        history = ChatHistory()
        
        # Get Redis connection info for verification
        try:
            info = history.get_redis_info()
            print("\n📊 Redis Connection Info:")
            print(f"   Host: {info.get('host', 'unknown')}")
            print(f"   Port: {info.get('port', 'unknown')}")
            print(f"   SSL: {info.get('ssl_enabled', 'unknown')}")
            print(f"   Messages in history: {info.get('history_length', '0')}")
            print(f"   Redis version: {info.get('redis_version', 'unknown')}")
        except Exception as e:
            print(f"⚠️  Could not get Redis info: {e}")
        
        # Demo: Add some messages
        print("\n💬 Adding messages to chat history...")
        history.add_message("user", "Hello! Can you help me with Azure Redis?")
        history.add_message("assistant", "Of course! Azure Redis Cache is a fully managed, in-memory cache service.")
        history.add_message("user", "How do I scale it?")
        history.add_message("assistant", "You can scale Azure Redis Cache through the Azure portal or using ARM templates.")
        
        # Retrieve and display history
        print("\n📜 Current chat history:")
        messages = history.get_history()
        for i, msg in enumerate(messages):
            print(f"   {i+1}. [{msg['role']}]: {msg['content']}")
        
        # Demo: Query functionality
        print("\n🔍 Searching for messages containing 'Azure'...")
        azure_messages = history.query_redis(pattern="Azure")
        for msg in azure_messages:
            print(f"   [{msg['role']}]: {msg['content']}")
        
        # Demo: Get specific message
        print(f"\n📋 First message: {history.get_message_at(0)}")
        
        print(f"\n✅ Successfully stored {len(messages)} messages in Azure Redis Cache!")
        print("💡 Messages will persist across application restarts.")
        
        # Uncomment to clear history
        # history.clear()
        # print("\n🧹 Chat history cleared.")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\n💡 Make sure you have:")
        print("   1. Set AZURE_REDIS_KEY environment variable")
        print("   2. Updated redis_host with your cache name")
        print("   3. Installed redis package: pip install redis")

if __name__ == "__main__":
    main()
