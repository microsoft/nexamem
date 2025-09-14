# FastAPI + NexaMem Integration Example

This example demonstrates how to integrate NexaMem into a FastAPI application for high-performance conversational memory management.

## Features

- **Async-First Design**: Native async/await support for maximum performance
- **Automatic API Documentation**: Interactive Swagger UI and ReDoc
- **Type Safety**: Full Pydantic models for request/response validation
- **Dependency Injection**: Clean architecture with FastAPI's DI system
- **Production Ready**: Proper error handling, logging, and health checks
- **Analytics Endpoints**: Built-in conversation analytics
- **Multiple Storage Backends**: Support for Redis, Memory, File, SQLite

## Quick Start

### 1. Install Dependencies

```bash
# Install NexaMem from parent directory
pip install -e ../..

# Install FastAPI dependencies
pip install -r requirements.txt
```

### 2. Run with In-Memory Storage (Development)

```bash
python app.py
```

The server will start on `http://localhost:8000`

### 3. View Interactive Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### 4. Run with Azure Redis (Production)

```bash
export NEXAMEM_SERVICE_TYPE=azure_redis
export AZURE_REDIS_HOSTNAME=your-cache.redis.cache.windows.net
export AZURE_REDIS_ACCESS_KEY=your-access-key

python app.py
```

## API Endpoints

### Add Conversation Turn
```bash
POST /conversation/{conversation_id}/turn

{
  "content": "Hello, how can I help you today?",
  "user_id": "user123",
  "turn_type": "assistant",
  "metadata": {
    "intent": "greeting",
    "confidence": 0.95
  }
}
```

### Get Conversation History
```bash
GET /conversation/{conversation_id}/history?limit=10
```

### Search Conversations
```bash
GET /conversations/search?q=python&limit=5
```

### Create Conversation Summary
```bash
POST /conversation/{conversation_id}/summary

{
  "summary": "User asked about Python best practices. Provided recommendations on code style, testing, and documentation."
}
```

### Get Conversation Analytics
```bash
GET /conversation/{conversation_id}/analytics
```

### Health Check
```bash
GET /health
```

## Example Usage with Python

```python
import httpx
import asyncio

async def main():
    base_url = "http://localhost:8000"
    
    async with httpx.AsyncClient() as client:
        # Add a conversation turn
        response = await client.post(f"{base_url}/conversation/chat123/turn", json={
            "content": "What are Python best practices?",
            "user_id": "user456",
            "turn_type": "user"
        })
        print(response.json())
        
        # Get conversation history
        response = await client.get(f"{base_url}/conversation/chat123/history")
        print(response.json())
        
        # Search conversations
        response = await client.get(f"{base_url}/conversations/search?q=Python")
        print(response.json())

asyncio.run(main())
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `NEXAMEM_SERVICE_TYPE` | Storage backend type | `memory` |
| `AZURE_REDIS_HOSTNAME` | Azure Redis hostname | - |
| `AZURE_REDIS_ACCESS_KEY` | Azure Redis access key | - |
| `AZURE_REDIS_PORT` | Azure Redis port | `6380` |
| `AZURE_REDIS_SSL` | Use SSL for Redis | `true` |
| `PORT` | FastAPI server port | `8000` |
| `FASTAPI_RELOAD` | Enable auto-reload | `true` |

### Storage Backends

#### In-Memory (Development)
```bash
export NEXAMEM_SERVICE_TYPE=memory
```

#### Azure Redis (Production)
```bash
export NEXAMEM_SERVICE_TYPE=azure_redis
export AZURE_REDIS_HOSTNAME=your-cache.redis.cache.windows.net
export AZURE_REDIS_ACCESS_KEY=your-access-key
```

#### File Storage
```bash
export NEXAMEM_SERVICE_TYPE=file
export NEXAMEM_FILE_PATH=./conversation_data
```

#### SQLite
```bash
export NEXAMEM_SERVICE_TYPE=sqlite
export NEXAMEM_SQLITE_PATH=./conversations.db
```

## Production Deployment

### Using Uvicorn

```bash
# Single worker
uvicorn app:app --host 0.0.0.0 --port 8000

# Multiple workers
uvicorn app:app --host 0.0.0.0 --port 8000 --workers 4
```

### Using Gunicorn with Uvicorn Workers

```bash
gunicorn app:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### Docker Deployment

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

### Environment-specific Configuration

```bash
# .env.development
NEXAMEM_SERVICE_TYPE=memory
FASTAPI_RELOAD=true

# .env.production
NEXAMEM_SERVICE_TYPE=azure_redis
AZURE_REDIS_HOSTNAME=prod-cache.redis.cache.windows.net
AZURE_REDIS_ACCESS_KEY=${AZURE_REDIS_ACCESS_KEY}
FASTAPI_RELOAD=false
```

## Advanced Features

### Custom Dependency Injection

```python
from fastapi import Depends
from nexamem import IConversationMemory

# Custom dependency provider
async def get_memory_service_with_auth(
    user_id: str = Depends(get_current_user)
) -> IConversationMemory:
    # Return user-specific memory service
    return create_conversation_memory(
        config={"default_scope": f"user_{user_id}"}
    )

@app.post("/conversation/{conversation_id}/turn")
async def add_turn(
    conversation_id: str,
    turn: ConversationTurn,
    memory: IConversationMemory = Depends(get_memory_service_with_auth)
):
    # Use user-specific memory service
    pass
```

### Background Tasks

```python
from fastapi import BackgroundTasks

@app.post("/conversation/{conversation_id}/turn")
async def add_turn(
    conversation_id: str,
    turn: ConversationTurn,
    background_tasks: BackgroundTasks,
    memory: ConversationMemoryAdapter = Depends(get_memory_service)
):
    # Store turn immediately
    turn_id = await memory.store_turn(conversation_id, turn.content, turn.metadata)
    
    # Process analytics in background
    background_tasks.add_task(process_conversation_analytics, conversation_id)
    
    return {"turn_id": turn_id}

async def process_conversation_analytics(conversation_id: str):
    # Background processing logic
    pass
```

### Middleware Integration

```python
from fastapi import Request

@app.middleware("http")
async def add_conversation_context(request: Request, call_next):
    # Add conversation context to request
    conversation_id = request.headers.get("X-Conversation-ID")
    if conversation_id:
        request.state.conversation_id = conversation_id
    
    response = await call_next(request)
    return response
```

### WebSocket Support

```python
from fastapi import WebSocket

@app.websocket("/conversation/{conversation_id}/live")
async def conversation_websocket(
    websocket: WebSocket,
    conversation_id: str,
    memory: ConversationMemoryAdapter = Depends(get_memory_service)
):
    await websocket.accept()
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            
            # Store in memory
            turn_id = await memory.store_turn(
                conversation_id=conversation_id,
                content=data["content"],
                metadata=data.get("metadata", {})
            )
            
            # Send confirmation
            await websocket.send_json({
                "type": "turn_stored",
                "turn_id": turn_id,
                "conversation_id": conversation_id
            })
            
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        await websocket.close()
```

## Testing

### Basic Test Setup

```python
import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient
from app import app

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
async def async_client():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

@pytest.mark.asyncio
async def test_add_conversation_turn(async_client):
    response = await async_client.post("/conversation/test123/turn", json={
        "content": "Test message",
        "user_id": "test_user",
        "turn_type": "user"
    })
    assert response.status_code == 200
    assert response.json()["success"] is True
```

### Load Testing

```python
import asyncio
import aiohttp
import time

async def load_test():
    base_url = "http://localhost:8000"
    concurrent_requests = 100
    
    async with aiohttp.ClientSession() as session:
        tasks = []
        start_time = time.time()
        
        for i in range(concurrent_requests):
            task = session.post(f"{base_url}/conversation/load_test_{i}/turn", json={
                "content": f"Load test message {i}",
                "user_id": f"user_{i}",
                "turn_type": "user"
            })
            tasks.append(task)
        
        responses = await asyncio.gather(*tasks)
        end_time = time.time()
        
        print(f"Completed {concurrent_requests} requests in {end_time - start_time:.2f} seconds")
        print(f"Average: {(end_time - start_time) / concurrent_requests * 1000:.2f} ms per request")

asyncio.run(load_test())
```

## Performance Considerations

- **Async Operations**: All endpoints use async/await for maximum concurrency
- **Connection Pooling**: Redis connections are pooled automatically
- **Dependency Injection**: Memory service is initialized once and reused
- **Pydantic Validation**: Fast JSON parsing and validation
- **Background Tasks**: Heavy operations can be moved to background
- **Caching**: Consider adding Redis caching for frequently accessed data

## Next Steps

- Add authentication and authorization
- Implement rate limiting
- Add request/response logging
- Set up monitoring and metrics
- Add real-time features with WebSockets
- Implement conversation analytics dashboard
- Add support for file uploads and attachments

This FastAPI integration provides a high-performance, production-ready foundation for conversational AI applications using NexaMem.