# NexaMem Azure Redis Integration Examples

This document provides complete examples for integrating NexaMem's production-ready Azure Redis implementation into external projects.

## 3-Line Integration for External Projects

### Basic Integration

```python
# Line 1: Import
from nexamem.storage.interfaces import create_memory_service

# Line 2: Create service  
memory = create_memory_service("azure_redis", 
                              hostname="your-cache.redis.cache.windows.net", 
                              access_key="your-access-key")

# Line 3: Use service
turn_id = memory.store_conversation_turn("conversation-1", {
    "user": "What's the weather like?",
    "assistant": "I'll help you check the weather. What's your location?"
})
```

### Flask Integration Example

```python
from flask import Flask, request, jsonify
from nexamem.storage.interfaces import create_memory_service

app = Flask(__name__)

# Initialize memory service (configure once)
memory = create_memory_service(
    "azure_redis",
    hostname="your-cache.redis.cache.windows.net",
    access_key="your-access-key",
    async_preferred=False  # Use sync for Flask
)

@app.route('/chat', methods=['POST'])
def chat_endpoint():
    data = request.json
    conversation_id = data.get('conversation_id')
    user_message = data.get('message')
    
    # Store user message
    memory.store_conversation_turn(conversation_id, {
        "role": "user",
        "content": user_message,
        "timestamp": time.time()
    })
    
    # Get conversation history for context
    history = memory.get_conversation_history(conversation_id, limit=10)
    
    # Generate response (your AI logic here)
    assistant_response = generate_response(user_message, history)
    
    # Store assistant response
    memory.store_conversation_turn(conversation_id, {
        "role": "assistant", 
        "content": assistant_response,
        "timestamp": time.time()
    })
    
    return jsonify({
        "response": assistant_response,
        "conversation_id": conversation_id
    })

@app.route('/conversation/<conversation_id>/history')
def get_history(conversation_id):
    history = memory.get_conversation_history(conversation_id)
    return jsonify({"history": history})

if __name__ == '__main__':
    app.run(debug=True)
```

### FastAPI Integration Example (Async)

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import asyncio
from nexamem.storage.interfaces import create_memory_service

app = FastAPI(title="AI Chat API with NexaMem")

# Initialize async memory service
memory = create_memory_service(
    "azure_redis", 
    hostname="your-cache.redis.cache.windows.net",
    access_key="your-access-key",
    async_preferred=True  # Use async for FastAPI
)

class ChatMessage(BaseModel):
    conversation_id: str
    message: str
    user_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    conversation_id: str
    turn_id: str

@app.post("/chat", response_model=ChatResponse)
async def chat(message: ChatMessage):
    try:
        # Store user message
        user_turn_id = await memory.store_conversation_turn(
            message.conversation_id,
            {
                "role": "user",
                "content": message.message,
                "user_id": message.user_id
            },
            {"user_id": message.user_id} if message.user_id else None
        )
        
        # Get conversation history for context
        history = await memory.get_conversation_history(
            message.conversation_id, 
            limit=10
        )
        
        # Generate response (your AI logic here)
        assistant_response = await generate_ai_response(message.message, history)
        
        # Store assistant response
        assistant_turn_id = await memory.store_conversation_turn(
            message.conversation_id,
            {
                "role": "assistant",
                "content": assistant_response,
                "user_id": message.user_id
            }
        )
        
        return ChatResponse(
            response=assistant_response,
            conversation_id=message.conversation_id,
            turn_id=assistant_turn_id
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/conversation/{conversation_id}/history")
async def get_conversation_history(conversation_id: str, limit: Optional[int] = 50):
    try:
        history = await memory.get_conversation_history(conversation_id, limit=limit)
        return {"conversation_id": conversation_id, "history": history}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/search")
async def search_conversations(query: str, user_id: Optional[str] = None, limit: Optional[int] = 20):
    try:
        conversations = await memory.search_conversations(query, user_id=user_id, limit=limit)
        return {"query": query, "conversations": conversations}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def generate_ai_response(user_message: str, history: List[dict]) -> str:
    # Implement your AI response generation logic here
    # This is just a placeholder
    return f"I received your message: '{user_message}'. Based on {len(history)} previous messages in our conversation, here's my response..."

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

## Advanced Configuration Examples

### Environment-Based Configuration

```python
# Set environment variables
import os
os.environ['NEXAMEM_STORAGE_TYPE'] = 'azure_redis'
os.environ['AZURE_REDIS_HOSTNAME'] = 'your-cache.redis.cache.windows.net'  
os.environ['AZURE_REDIS_ACCESS_KEY'] = 'your-access-key'

# Create from environment
from nexamem.storage.interfaces import create_from_environment
memory = create_from_environment(async_preferred=True)
```

### Multiple Authentication Methods

```python
from nexamem.storage.azure_redis_factory import create_azure_redis_storage
from nexamem.config.storage import AzureRedisConfig, AzureAuthMethod

# Access Key Authentication
config_access_key = AzureRedisConfig(
    hostname="your-cache.redis.cache.windows.net",
    access_key="your-access-key",
    auth_method=AzureAuthMethod.ACCESS_KEY
)

# Entra ID Authentication  
config_entra_id = AzureRedisConfig(
    hostname="your-cache.redis.cache.windows.net",
    auth_method=AzureAuthMethod.ENTRA_ID,
    use_entra_id=True
)

# Key Vault Authentication
config_keyvault = AzureRedisConfig(
    hostname="your-cache.redis.cache.windows.net", 
    auth_method=AzureAuthMethod.KEYVAULT,
    keyvault_url="https://your-keyvault.vault.azure.net/",
    secret_name="redis-access-key"
)

# Create storage with specific config
storage = create_azure_redis_storage(config_access_key, async_preferred=True)
```

### Custom Authentication Provider

```python
from nexamem.storage.azure_redis_factory import (
    AsyncAuthenticationProvider, 
    AzureRedisStorageFactory
)

class CustomAuthProvider(AsyncAuthenticationProvider):
    """Custom authentication provider for your system."""
    
    def __init__(self, your_auth_service):
        self.auth_service = your_auth_service
    
    async def get_auth_token(self) -> str:
        # Implement your custom auth logic
        token = await self.auth_service.get_redis_token()
        return token

# Use custom auth provider
config = AzureRedisConfig(
    hostname="your-cache.redis.cache.windows.net",
    access_key="fallback-key",  # Fallback if custom fails
    auth_method=AzureAuthMethod.ACCESS_KEY
)

custom_auth = CustomAuthProvider(your_auth_service)
storage = AzureRedisStorageFactory.create_async_storage(config, custom_auth)
```

## Health Monitoring Example

```python
from nexamem.storage.azure_redis import AsyncAzureRedisStorage
from nexamem.config.storage import AzureRedisConfig, AzureAuthMethod

async def monitor_redis_health():
    config = AzureRedisConfig(
        hostname="your-cache.redis.cache.windows.net",
        access_key="your-access-key",
        auth_method=AzureAuthMethod.ACCESS_KEY
    )
    
    storage = AsyncAzureRedisStorage(config)
    
    # Get comprehensive health status
    health = await storage.get_health_status()
    
    print(f"Redis Status: {health['status']}")
    if health['status'] == 'healthy':
        print(f"Latency: {health['latency_ms']}ms")
        print(f"Connected Clients: {health['connected_clients']}")
        print(f"Memory Used: {health['used_memory_human']}")
        print(f"Redis Version: {health['redis_version']}")
    else:
        print(f"Error: {health['error']}")
    
    # Get storage statistics
    stats = await storage.get_stats()
    print(f"Total Memories: {stats['total_memories']}")
    print(f"Total Scopes: {stats['total_scopes']}")
    print(f"Audit Entries: {stats['audit_entries']}")

# Run health check
asyncio.run(monitor_redis_health())
```

## Custom Implementation Example

```python
from nexamem.storage.interfaces import IAsyncConversationMemory
from typing import Dict, List, Optional, Any

class CustomConversationMemory:
    """
    External project can implement their own conversation memory
    that follows the IAsyncConversationMemory protocol.
    """
    
    def __init__(self, your_custom_storage):
        self.storage = your_custom_storage
        self.conversations = {}
    
    async def store_conversation_turn(
        self, 
        conversation_id: str, 
        turn_data: Dict[str, Any], 
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        # Your custom storage logic
        turn_id = await self.storage.save_turn(conversation_id, turn_data, metadata)
        return turn_id
    
    async def get_conversation_history(
        self, 
        conversation_id: str, 
        limit: Optional[int] = None, 
        since_timestamp: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        # Your custom retrieval logic
        return await self.storage.get_history(conversation_id, limit, since_timestamp)
    
    async def delete_conversation(self, conversation_id: str) -> bool:
        # Your custom deletion logic
        return await self.storage.delete_conversation(conversation_id)
    
    async def search_conversations(
        self, 
        query: str, 
        user_id: Optional[str] = None, 
        limit: Optional[int] = None
    ) -> List[str]:
        # Your custom search logic
        return await self.storage.search(query, user_id, limit)

# Use your custom implementation
custom_memory = CustomConversationMemory(your_storage_system)

# It will work with any code expecting IAsyncConversationMemory
assert isinstance(custom_memory, IAsyncConversationMemory)
```

## Production Deployment Example

```python
import logging
import os
from nexamem.storage.interfaces import create_memory_service

# Configure logging
logging.basicConfig(level=logging.INFO)

class ChatService:
    """Production chat service with proper error handling."""
    
    def __init__(self):
        # Create memory service with production configuration
        self.memory = create_memory_service(
            "azure_redis",
            hostname=os.getenv('AZURE_REDIS_HOSTNAME'),
            access_key=os.getenv('AZURE_REDIS_ACCESS_KEY'),
            async_preferred=True,
            # Production settings
            max_connections=50,
            socket_connect_timeout=5.0,
            socket_timeout=5.0,
            retry_on_timeout=True,
            use_collections=True,
            collection_prefix=os.getenv('REDIS_PREFIX', 'chatservice')
        )
        
    async def process_chat_message(self, conversation_id: str, user_message: str, user_id: str = None):
        """Process a chat message with full error handling."""
        try:
            # Store user message
            user_turn_id = await self.memory.store_conversation_turn(
                conversation_id,
                {
                    "role": "user",
                    "content": user_message,
                    "timestamp": time.time()
                },
                {"user_id": user_id} if user_id else None
            )
            
            # Get recent context
            recent_history = await self.memory.get_conversation_history(
                conversation_id, 
                limit=10
            )
            
            # Generate AI response (your implementation)
            ai_response = await self.generate_response(user_message, recent_history)
            
            # Store AI response
            ai_turn_id = await self.memory.store_conversation_turn(
                conversation_id,
                {
                    "role": "assistant", 
                    "content": ai_response,
                    "timestamp": time.time()
                }
            )
            
            return {
                "success": True,
                "response": ai_response,
                "user_turn_id": user_turn_id,
                "ai_turn_id": ai_turn_id
            }
            
        except Exception as e:
            logging.error(f"Error processing chat message: {e}")
            return {
                "success": False,
                "error": str(e),
                "fallback_response": "I'm sorry, I'm having trouble right now. Please try again."
            }
    
    async def generate_response(self, user_message: str, history: List[dict]) -> str:
        """Implement your AI response generation here."""
        # This is where you'd integrate with your AI service
        # (OpenAI, Azure OpenAI, Anthropic, etc.)
        return f"Response to: {user_message}"
    
    async def health_check(self) -> dict:
        """Health check endpoint for monitoring."""
        try:
            # Test storage connectivity
            test_conv_id = "health_check_" + str(time.time())
            test_turn_id = await self.memory.store_conversation_turn(
                test_conv_id,
                {"test": "health_check"}
            )
            
            # Clean up test data
            await self.memory.delete_conversation(test_conv_id)
            
            return {"status": "healthy", "storage": "connected"}
            
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}

# Usage in your application
chat_service = ChatService()

# Example API endpoint
async def chat_endpoint(request):
    result = await chat_service.process_chat_message(
        conversation_id=request.json['conversation_id'],
        user_message=request.json['message'],
        user_id=request.json.get('user_id')
    )
    return result
```

This implementation provides:

1. **Production-ready Azure Redis integration** with connection pooling, retry logic, and comprehensive error handling
2. **SOLID design principles** with dependency injection, factory patterns, and clear interfaces  
3. **3-line integration** for quick external project adoption
4. **Full customization capabilities** through protocols and factory patterns
5. **Enterprise authentication support** (Access Key, Entra ID, Key Vault)
6. **Health monitoring and statistics** for production deployments
7. **Comprehensive error handling** and logging for reliability

External projects can start with the simple 3-line integration and progressively add more sophisticated features as needed, all while maintaining clean architecture and testability.