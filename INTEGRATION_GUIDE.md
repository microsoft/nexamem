# NexaMem Integration Guide

**Complete guide for integrating NexaMem into external projects**

---

## 🎯 Quick Integration Overview

NexaMem provides multiple integration patterns to fit different architectural preferences:

### **Zero-Configuration Integration** (Simplest)
```python
from nexamem import create_conversation_memory

# One-line setup
memory = create_conversation_memory(service_type="memory")

# Store and retrieve conversations
turn_id = await memory.store_turn("conversation_123", "Hello world!")
history = await memory.get_history("conversation_123")
```

### **Environment-Based Configuration** (Production)
```python
from nexamem import create_from_environment

# Configure via environment variables
memory = create_from_environment()
```

### **Advanced Dependency Injection** (Enterprise)
```python
from nexamem import MemoryServiceFactory, IConversationMemory

# Full control over service creation
memory = MemoryServiceFactory.create_conversation_memory(
    service_type="azure_redis",
    config={"redis_hostname": "...", "redis_access_key": "..."}
)
```

---

## 🏗️ Architecture Patterns

### **Pattern 1: Service Factory** ✅ **Recommended**

**Use when**: You want simple, standardized conversation memory

```python
from nexamem import create_conversation_memory

class ConversationService:
    def __init__(self):
        self.memory = create_conversation_memory(
            service_type="azure_redis",
            config={
                "redis_hostname": "cache.redis.cache.windows.net",
                "redis_access_key": "your-key",
                "default_scope": "my_app"
            }
        )
    
    async def add_message(self, conversation_id: str, content: str, user_id: str):
        return await self.memory.store_turn(
            conversation_id=conversation_id,
            content=content,
            metadata={"user_id": user_id, "timestamp": time.time()}
        )
    
    async def get_chat_history(self, conversation_id: str, limit: int = 10):
        return await self.memory.get_history(conversation_id, limit)
```

### **Pattern 2: Direct AIMemory** 

**Use when**: You need advanced features like scopes, channels, and policies

```python
from nexamem import AsyncAIMemory, AIMemoryConfig, StorageConfig, AzureRedisConfig

class AdvancedConversationService:
    def __init__(self):
        redis_config = AzureRedisConfig(
            hostname="cache.redis.cache.windows.net",
            access_key="your-key"
        )
        
        ai_config = AIMemoryConfig(
            default_scope="advanced_app",
            storage=StorageConfig.azure_redis(redis_config),
            channels_yaml="channels.yaml",  # Use YAML channel configuration
            strict_yaml_validation=True
        )
        
        self.memory = AsyncAIMemory(ai_config)
    
    async def store_with_scope(self, content: str, scope: str, metadata: dict):
        return await self.memory.store(content, metadata, scope)
    
    async def search_memories(self, query: str, scope: str = None):
        return await self.memory.search(query, scope)
```

### **Pattern 3: Interface-Based** 

**Use when**: You want to swap implementations or support multiple backends

```python
from nexamem import IConversationMemory, create_conversation_memory
from typing import Protocol

class MyConversationMemory(Protocol):
    async def save_message(self, chat_id: str, message: str) -> str: ...
    async def load_messages(self, chat_id: str) -> list: ...

class NexaMemAdapter:
    def __init__(self, memory: IConversationMemory):
        self._memory = memory
    
    async def save_message(self, chat_id: str, message: str) -> str:
        return await self._memory.store_turn(chat_id, message)
    
    async def load_messages(self, chat_id: str) -> list:
        history = await self._memory.get_history(chat_id)
        return [turn["content"] for turn in history]

# Usage
memory_service = create_conversation_memory(service_type="azure_redis")
adapter = NexaMemAdapter(memory_service)
```

---

## 🚀 Framework Integrations

### **Flask Integration**

```python
from flask import Flask, request, jsonify
from nexamem import create_conversation_memory

app = Flask(__name__)
app.memory = create_conversation_memory(service_type="memory")

@app.route("/chat/<chat_id>/message", methods=["POST"])
def add_message(chat_id):
    data = request.get_json()
    
    import asyncio
    turn_id = asyncio.run(app.memory.store_turn(
        conversation_id=chat_id,
        content=data["message"],
        metadata={"user_id": data.get("user_id")}
    ))
    
    return jsonify({"turn_id": turn_id})

@app.route("/chat/<chat_id>/history")
def get_history(chat_id):
    import asyncio
    history = asyncio.run(app.memory.get_history(chat_id))
    return jsonify({"history": history})
```

### **FastAPI Integration**

```python
from fastapi import FastAPI, Depends
from nexamem import create_conversation_memory, ConversationMemoryAdapter

app = FastAPI()

# Dependency injection
async def get_memory() -> ConversationMemoryAdapter:
    return create_conversation_memory(service_type="memory")

@app.post("/chat/{chat_id}/message")
async def add_message(
    chat_id: str, 
    message: dict,
    memory: ConversationMemoryAdapter = Depends(get_memory)
):
    turn_id = await memory.store_turn(
        conversation_id=chat_id,
        content=message["content"],
        metadata=message.get("metadata", {})
    )
    return {"turn_id": turn_id}

@app.get("/chat/{chat_id}/history")
async def get_history(
    chat_id: str,
    memory: ConversationMemoryAdapter = Depends(get_memory)
):
    history = await memory.get_history(chat_id)
    return {"history": history}
```

### **Django Integration**

```python
# settings.py
NEXAMEM_CONFIG = {
    "service_type": "azure_redis",
    "config": {
        "redis_hostname": "cache.redis.cache.windows.net",
        "redis_access_key": "your-key"
    }
}

# services.py
from django.conf import settings
from nexamem import create_conversation_memory

class ConversationMemoryService:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.memory = create_conversation_memory(**settings.NEXAMEM_CONFIG)
        return cls._instance
    
    async def store_message(self, conversation_id: str, content: str, metadata: dict):
        return await self.memory.store_turn(conversation_id, content, metadata)

# views.py
from django.http import JsonResponse
from .services import ConversationMemoryService
import asyncio

def add_message(request, conversation_id):
    service = ConversationMemoryService()
    data = json.loads(request.body)
    
    turn_id = asyncio.run(service.store_message(
        conversation_id=conversation_id,
        content=data["content"],
        metadata=data.get("metadata", {})
    ))
    
    return JsonResponse({"turn_id": turn_id})
```

### **Quart Integration** (Async Flask)

```python
from quart import Quart, request, jsonify
from nexamem import create_conversation_memory

app = Quart(__name__)

@app.before_serving
async def setup_memory():
    app.memory = create_conversation_memory(service_type="memory")

@app.route("/chat/<chat_id>/message", methods=["POST"])
async def add_message(chat_id):
    data = await request.get_json()
    
    turn_id = await app.memory.store_turn(
        conversation_id=chat_id,
        content=data["message"],
        metadata={"user_id": data.get("user_id")}
    )
    
    return jsonify({"turn_id": turn_id})

@app.route("/chat/<chat_id>/history")
async def get_history(chat_id):
    history = await app.memory.get_history(chat_id)
    return jsonify({"history": history})
```

---

## 💾 Storage Configuration

### **In-Memory Storage** (Development)
```python
memory = create_conversation_memory(service_type="memory")
```

### **Azure Redis** (Production)
```python
memory = create_conversation_memory(
    service_type="azure_redis",
    config={
        "redis_hostname": "cache.redis.cache.windows.net",
        "redis_access_key": "your-primary-key",
        "redis_port": 6380,
        "redis_ssl": True
    }
)
```

### **File Storage** (Persistence without Redis)
```python
memory = create_conversation_memory(
    service_type="file",
    config={"file_path": "./conversation_data"}
)
```

### **SQLite** (Local database)
```python
memory = create_conversation_memory(
    service_type="sqlite",
    config={"sqlite_path": "./conversations.db"}
)
```

### **Environment Configuration**
```bash
# Set environment variables
export NEXAMEM_SERVICE_TYPE=azure_redis
export AZURE_REDIS_HOSTNAME=cache.redis.cache.windows.net
export AZURE_REDIS_ACCESS_KEY=your-key

# Then use in code
memory = create_from_environment()
```

---

## 🔧 Advanced Configuration

### **Custom Service Provider**

```python
from nexamem import MemoryServiceFactory, DIContainer, ServiceProvider
from nexamem.storage import BaseAsyncStorage

class CustomMemoryProvider(ServiceProvider):
    def provide(self, service_type, config=None):
        if service_type == BaseAsyncStorage:
            return MyCustomStorage(config)
        raise ValueError(f"Cannot provide {service_type}")
    
    def can_provide(self, service_type):
        return service_type == BaseAsyncStorage

# Register custom provider
container = DIContainer()
container.register(BaseAsyncStorage, CustomMemoryProvider())

# Use with factory
memory = MemoryServiceFactory.create_ai_memory(
    service_type="custom",
    config={"custom_param": "value"}
)
```

### **Multi-Tenant Support**

```python
class MultiTenantMemoryService:
    def __init__(self):
        self._tenant_memories = {}
    
    def get_memory_for_tenant(self, tenant_id: str):
        if tenant_id not in self._tenant_memories:
            self._tenant_memories[tenant_id] = create_conversation_memory(
                service_type="azure_redis",
                config={
                    "default_scope": f"tenant_{tenant_id}",
                    "redis_hostname": "cache.redis.cache.windows.net",
                    "redis_access_key": "your-key"
                }
            )
        return self._tenant_memories[tenant_id]
    
    async def store_for_tenant(self, tenant_id: str, conversation_id: str, content: str):
        memory = self.get_memory_for_tenant(tenant_id)
        return await memory.store_turn(conversation_id, content)
```

### **Custom Metadata Enrichment**

```python
class EnrichedConversationMemory:
    def __init__(self, base_memory):
        self.base_memory = base_memory
    
    async def store_turn_with_enrichment(self, conversation_id: str, content: str, user_id: str):
        # Add custom enrichment
        enriched_metadata = {
            "user_id": user_id,
            "timestamp": time.time(),
            "content_length": len(content),
            "language": detect_language(content),  # Custom function
            "sentiment": analyze_sentiment(content),  # Custom function
            "entities": extract_entities(content)  # Custom function
        }
        
        return await self.base_memory.store_turn(
            conversation_id=conversation_id,
            content=content,
            metadata=enriched_metadata
        )

# Usage
base_memory = create_conversation_memory(service_type="azure_redis")
enriched_memory = EnrichedConversationMemory(base_memory)
```

---

## 🏥 Health Checks and Monitoring

### **Basic Health Check**

```python
async def check_memory_service_health(memory_service):
    try:
        # Test basic operations
        test_id = await memory_service.store_turn(
            "health_check", 
            "test", 
            {"type": "health_check"}
        )
        
        history = await memory_service.get_history("health_check")
        
        return {
            "status": "healthy",
            "operations": ["store", "retrieve"],
            "timestamp": time.time()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": time.time()
        }
```

### **Metrics Collection**

```python
import time
from collections import defaultdict

class MetricsCollector:
    def __init__(self, base_memory):
        self.base_memory = base_memory
        self.metrics = defaultdict(int)
        self.response_times = []
    
    async def store_turn(self, *args, **kwargs):
        start_time = time.time()
        try:
            result = await self.base_memory.store_turn(*args, **kwargs)
            self.metrics["store_success"] += 1
            return result
        except Exception as e:
            self.metrics["store_error"] += 1
            raise
        finally:
            elapsed = time.time() - start_time
            self.response_times.append(elapsed)
            self.metrics["total_operations"] += 1
    
    def get_metrics(self):
        return {
            "operations": dict(self.metrics),
            "avg_response_time": sum(self.response_times) / len(self.response_times) if self.response_times else 0,
            "p95_response_time": sorted(self.response_times)[int(len(self.response_times) * 0.95)] if self.response_times else 0
        }
```

---

## 🧪 Testing Patterns

### **Mock Memory Service**

```python
import pytest
from unittest.mock import AsyncMock

@pytest.fixture
def mock_memory():
    mock = AsyncMock()
    mock.store_turn.return_value = "test_turn_id"
    mock.get_history.return_value = [
        {"id": "test_turn_id", "content": "test message", "metadata": {}}
    ]
    mock.search_conversations.return_value = []
    return mock

async def test_conversation_service(mock_memory):
    service = ConversationService(memory=mock_memory)
    
    turn_id = await service.add_message("conv123", "test", "user123")
    assert turn_id == "test_turn_id"
    
    mock_memory.store_turn.assert_called_once_with(
        conversation_id="conv123",
        content="test",
        metadata={"user_id": "user123", "timestamp": pytest.approx(time.time(), abs=1)}
    )
```

### **Integration Testing**

```python
@pytest.fixture
async def test_memory():
    # Use in-memory storage for tests
    memory = create_conversation_memory(service_type="memory")
    yield memory
    # Cleanup not needed for in-memory storage

async def test_full_conversation_flow(test_memory):
    conversation_id = "test_conversation"
    
    # Store multiple turns
    turn1 = await test_memory.store_turn(conversation_id, "Hello", {"user": "test"})
    turn2 = await test_memory.store_turn(conversation_id, "Hi there!", {"user": "bot"})
    
    # Get history
    history = await test_memory.get_history(conversation_id)
    
    assert len(history) == 2
    assert any(turn["content"] == "Hello" for turn in history)
    assert any(turn["content"] == "Hi there!" for turn in history)
```

---

## 🚀 Production Deployment

### **Environment Configuration**

```bash
# Production environment variables
export NEXAMEM_SERVICE_TYPE=azure_redis
export AZURE_REDIS_HOSTNAME=prod-cache.redis.cache.windows.net
export AZURE_REDIS_ACCESS_KEY=${AZURE_REDIS_ACCESS_KEY}
export NEXAMEM_DEFAULT_SCOPE=production_app
export NEXAMEM_ENABLE_AUDIT=true
export NEXAMEM_ENABLE_METRICS=true
```

### **Docker Configuration**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy application
COPY . .

# Environment defaults
ENV NEXAMEM_SERVICE_TYPE=azure_redis
ENV PORT=8000

EXPOSE 8000

CMD ["python", "app.py"]
```

### **Kubernetes Deployment**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: conversation-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: conversation-app
  template:
    metadata:
      labels:
        app: conversation-app
    spec:
      containers:
      - name: app
        image: your-registry/conversation-app:latest
        ports:
        - containerPort: 8000
        env:
        - name: NEXAMEM_SERVICE_TYPE
          value: "azure_redis"
        - name: AZURE_REDIS_HOSTNAME
          value: "your-cache.redis.cache.windows.net"
        - name: AZURE_REDIS_ACCESS_KEY
          valueFrom:
            secretKeyRef:
              name: redis-secret
              key: access-key
```

---

## ✅ Best Practices

### **1. Use Async Patterns**
```python
# ✅ Good - Use async/await
memory = create_conversation_memory(async_preferred=True)
turn_id = await memory.store_turn(...)

# ❌ Avoid - Blocking synchronous calls in async context
turn_id = memory.store_turn(...)  # Don't do this in async functions
```

### **2. Handle Errors Gracefully**
```python
async def safe_store_turn(memory, conversation_id, content):
    try:
        return await memory.store_turn(conversation_id, content)
    except Exception as e:
        logger.error(f"Failed to store turn: {e}")
        # Implement fallback or retry logic
        return None
```

### **3. Use Appropriate Scoping**
```python
# ✅ Good - Use meaningful scopes
memory = create_conversation_memory(
    config={"default_scope": f"user_{user_id}_session_{session_id}"}
)

# ✅ Good - Or use conversation-level scoping
turn_id = await memory.store_turn(
    conversation_id=f"user_{user_id}_chat_{chat_id}",
    content=content
)
```

### **4. Implement Health Checks**
```python
@app.route("/health")
async def health():
    memory_health = await check_memory_service_health(app.memory)
    return {
        "status": "healthy" if memory_health["status"] == "healthy" else "unhealthy",
        "checks": {
            "memory_service": memory_health
        }
    }
```

### **5. Use Environment Configuration**
```python
# ✅ Good - Environment-based configuration
memory = create_from_environment()

# ❌ Avoid - Hardcoded credentials
memory = create_conversation_memory(
    service_type="azure_redis",
    config={"redis_access_key": "hardcoded-key"}  # Don't do this
)
```

---

This integration guide provides everything needed to successfully integrate NexaMem into any Python application, from simple scripts to enterprise-scale systems.