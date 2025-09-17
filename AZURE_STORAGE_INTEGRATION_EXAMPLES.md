# Azure Storage Services Integration Examples

This document provides comprehensive examples for integrating all Azure storage services (Redis, Cosmos DB, Blob Storage, and AI Search) into external projects using NexaMem.

## Quick 3-Line Integration Examples

### Azure Cosmos DB Integration

```python
# Line 1: Import
from nexamem.storage.interfaces import create_memory_service

# Line 2: Create service
memory = create_memory_service(
    "azure_cosmos",
    endpoint="https://your-account.documents.azure.com:443/",
    account_key="your-account-key",
    database_name="conversations"
)

# Line 3: Use service
turn_id = memory.store_conversation_turn("conv1", {
    "user": "What are the benefits of Azure Cosmos DB?",
    "assistant": "Azure Cosmos DB offers global distribution, elastic scale, and multiple API models..."
})
```

### Azure Blob Storage Integration

```python
# Line 1: Import
from nexamem.storage.interfaces import create_memory_service

# Line 2: Create service
memory = create_memory_service(
    "azure_blob",
    account_name="yourstorageaccount",
    account_key="your-storage-key",
    container_name="conversations"
)

# Line 3: Use service
turn_id = memory.store_conversation_turn("conv1", {
    "user": "How does blob storage handle large conversations?",
    "assistant": "Blob storage is perfect for large conversations with support for tiered storage..."
})
```

### Azure AI Search Vector Database Integration

```python
# Line 1: Import
from nexamem.storage.interfaces import create_memory_service

# Line 2: Create service
memory = create_memory_service(
    "azure_ai_search",
    endpoint="https://your-search-service.search.windows.net",
    api_key="your-search-key",
    openai_api_key="your-openai-key",
    embedding_provider="openai"
)

# Line 3: Use service with semantic search
turn_id = memory.store_conversation_turn("conv1", {
    "user": "Explain vector search capabilities",
    "assistant": "Vector search enables semantic similarity matching using embeddings..."
})
```

## Framework Integration Examples

### FastAPI with Multiple Storage Backends

```python
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import asyncio
from nexamem.storage.interfaces import create_memory_service

app = FastAPI(title="Multi-Storage Chat API")

# Storage service instances
storage_services = {
    "redis": create_memory_service(
        "azure_redis",
        hostname="your-cache.redis.cache.windows.net",
        access_key="your-redis-key",
        async_preferred=True
    ),
    "cosmos": create_memory_service(
        "azure_cosmos", 
        endpoint="https://your-account.documents.azure.com:443/",
        account_key="your-cosmos-key",
        database_name="conversations",
        async_preferred=True
    ),
    "blob": create_memory_service(
        "azure_blob",
        account_name="yourstorageaccount", 
        account_key="your-storage-key",
        async_preferred=True
    ),
    "search": create_memory_service(
        "azure_ai_search",
        endpoint="https://your-search.search.windows.net",
        api_key="your-search-key",
        openai_api_key="your-openai-key",
        async_preferred=True
    )
}

class ChatRequest(BaseModel):
    conversation_id: str
    message: str
    user_id: Optional[str] = None
    storage_backend: str = "redis"  # Default to Redis
    
class VectorSearchRequest(BaseModel):
    query: str
    top_k: Optional[int] = 5
    similarity_threshold: Optional[float] = 0.7

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    """Chat endpoint with configurable storage backend."""
    try:
        # Select storage service
        if request.storage_backend not in storage_services:
            raise HTTPException(status_code=400, detail=f"Unsupported storage backend: {request.storage_backend}")
        
        memory = storage_services[request.storage_backend]
        
        # Store user message
        user_turn_id = await memory.store_conversation_turn(
            request.conversation_id,
            {
                "role": "user",
                "content": request.message,
                "timestamp": time.time()
            },
            {"user_id": request.user_id} if request.user_id else None
        )
        
        # Get conversation history for context
        history = await memory.get_conversation_history(request.conversation_id, limit=10)
        
        # Generate AI response (mock)
        ai_response = f"Response using {request.storage_backend} storage: {request.message}"
        
        # Store AI response
        ai_turn_id = await memory.store_conversation_turn(
            request.conversation_id,
            {
                "role": "assistant", 
                "content": ai_response,
                "timestamp": time.time()
            }
        )
        
        return {
            "response": ai_response,
            "conversation_id": request.conversation_id,
            "user_turn_id": user_turn_id,
            "ai_turn_id": ai_turn_id,
            "storage_backend": request.storage_backend,
            "context_length": len(history)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/search/semantic")
async def semantic_search(request: VectorSearchRequest):
    """Semantic search using AI Search vector capabilities."""
    try:
        # Only AI Search supports vector search
        search_service = storage_services["search"]
        
        # Perform vector search (if the backend supports it)
        if hasattr(search_service.storage, 'vector_search'):
            results = await search_service.storage.vector_search(
                query=request.query,
                top_k=request.top_k,
                similarity_threshold=request.similarity_threshold
            )
            return {
                "query": request.query,
                "results": results,
                "backend": "azure_ai_search"
            }
        else:
            # Fallback to regular search
            matching_conversations = await search_service.search_conversations(
                request.query,
                limit=request.top_k
            )
            return {
                "query": request.query,
                "matching_conversations": matching_conversations,
                "backend": "fallback_search"
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/storage/{storage_type}/health")
async def storage_health_check(storage_type: str):
    """Get health status for specific storage backend."""
    try:
        if storage_type not in storage_services:
            raise HTTPException(status_code=400, detail=f"Unknown storage type: {storage_type}")
        
        memory = storage_services[storage_type]
        
        # Get health status if available
        if hasattr(memory.storage, 'get_health_status'):
            health = await memory.storage.get_health_status()
        else:
            # Fallback to ping
            ping_result = await memory.storage.ping() if hasattr(memory.storage, 'ping') else True
            health = {"status": "healthy" if ping_result else "unhealthy"}
        
        return {
            "storage_type": storage_type,
            "health": health
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/storage/stats")
async def get_all_storage_stats():
    """Get statistics from all storage backends."""
    try:
        stats = {}
        
        for backend_name, service in storage_services.items():
            try:
                backend_stats = await service.get_stats()
                stats[backend_name] = backend_stats
            except Exception as e:
                stats[backend_name] = {"error": str(e)}
        
        return {"storage_stats": stats}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

## Advanced Configuration Examples

### Environment-Based Multi-Storage Setup

```python
import os
from nexamem.storage.interfaces import create_from_environment

# Set environment variables for different storage types
configurations = {
    "redis": {
        "NEXAMEM_STORAGE_TYPE": "azure_redis",
        "AZURE_REDIS_HOSTNAME": "your-cache.redis.cache.windows.net",
        "AZURE_REDIS_ACCESS_KEY": "your-redis-key"
    },
    "cosmos": {
        "NEXAMEM_STORAGE_TYPE": "azure_cosmos",
        "AZURE_COSMOS_ENDPOINT": "https://your-account.documents.azure.com:443/",
        "AZURE_COSMOS_KEY": "your-cosmos-key",
        "AZURE_COSMOS_DATABASE": "conversations"
    },
    "blob": {
        "NEXAMEM_STORAGE_TYPE": "azure_blob",
        "AZURE_STORAGE_ACCOUNT": "yourstorageaccount",
        "AZURE_STORAGE_KEY": "your-storage-key"
    },
    "search": {
        "NEXAMEM_STORAGE_TYPE": "azure_ai_search",
        "AZURE_SEARCH_ENDPOINT": "https://your-search.search.windows.net",
        "AZURE_SEARCH_KEY": "your-search-key",
        "OPENAI_API_KEY": "your-openai-key"
    }
}

async def create_storage_from_config(config_name: str):
    """Create storage service from environment configuration."""
    # Set environment variables
    for key, value in configurations[config_name].items():
        os.environ[key] = value
    
    # Create service from environment
    return create_from_environment(async_preferred=True)

# Usage
async def main():
    # Create different storage services
    redis_memory = await create_storage_from_config("redis")
    cosmos_memory = await create_storage_from_config("cosmos")
    blob_memory = await create_storage_from_config("blob")
    search_memory = await create_storage_from_config("search")
    
    # Use them interchangeably
    conversation_id = "multi_storage_test"
    
    # Store in Redis (fast access)
    await redis_memory.store_conversation_turn(conversation_id, {
        "type": "quick_access",
        "content": "Fast Redis storage for real-time chat"
    })
    
    # Store in Cosmos (global distribution)
    await cosmos_memory.store_conversation_turn(conversation_id, {
        "type": "global_access", 
        "content": "Globally distributed conversation data"
    })
    
    # Store in Blob (large content)
    await blob_memory.store_conversation_turn(conversation_id, {
        "type": "large_content",
        "content": "Large conversation data with detailed context and attachments"
    })
    
    # Store in AI Search (semantic search)
    await search_memory.store_conversation_turn(conversation_id, {
        "type": "searchable_content",
        "content": "Semantically searchable conversation content with embeddings"
    })

if __name__ == "__main__":
    asyncio.run(main())
```

### Custom Embedding Provider for AI Search

```python
import numpy as np
from nexamem.storage.azure_ai_search import AsyncCustomEmbeddingProvider
from nexamem.storage.interfaces import create_memory_service

class CustomSentenceTransformerProvider(AsyncCustomEmbeddingProvider):
    """Custom embedding provider using Sentence Transformers."""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(model_name)
            dimension = self.model.get_sentence_embedding_dimension()
        except ImportError:
            raise ImportError("sentence-transformers package required")
        
        # Create async wrapper function
        async def async_embedding_function(text: str):
            # Run in thread pool for CPU-bound operation
            import asyncio
            loop = asyncio.get_event_loop()
            embedding = await loop.run_in_executor(None, self.model.encode, text)
            return embedding.tolist()
        
        super().__init__(async_embedding_function, dimension)

# Usage with custom embedding provider
async def setup_custom_ai_search():
    """Setup AI Search with custom embedding provider."""
    
    # Create custom embedding provider
    custom_embeddings = CustomSentenceTransformerProvider("all-MiniLM-L6-v2")
    
    # Create AI Search storage with custom embeddings
    from nexamem.config.storage import AzureAISearchConfig, AzureAuthMethod, StorageConfig
    from nexamem.storage.azure_ai_search import AsyncAzureAISearchStorage
    from nexamem.storage.interfaces import AsyncConversationMemoryAdapter
    
    search_config = AzureAISearchConfig(
        endpoint="https://your-search.search.windows.net",
        api_key="your-search-key",
        auth_method=AzureAuthMethod.ACCESS_KEY,
        embedding_provider="custom",  # Use custom provider
        vector_dimension=384  # MiniLM embedding dimension
    )
    
    # Create storage with custom embedding provider
    storage = AsyncAzureAISearchStorage(search_config, custom_embeddings)
    
    # Wrap in conversation adapter
    storage_config = StorageConfig.azure_ai_search(search_config)
    adapter = AsyncConversationMemoryAdapter(storage_config)
    adapter.storage = storage  # Override with custom storage
    
    return adapter

# Usage
async def test_custom_embeddings():
    memory = await setup_custom_ai_search()
    
    # Store conversations with custom embeddings
    await memory.store_conversation_turn("conv1", {
        "user": "What is machine learning?",
        "assistant": "Machine learning is a subset of AI that learns from data..."
    })
    
    # Perform semantic search with custom embeddings
    results = await memory.storage.vector_search(
        "artificial intelligence concepts",
        top_k=5
    )
    
    print("Semantic search results:", results)

if __name__ == "__main__":
    asyncio.run(test_custom_embeddings())
```

## Production Deployment Examples

### Kubernetes Deployment with Multiple Storage Backends

```yaml
# kubernetes-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nexamem-chat-service
spec:
  replicas: 3
  selector:
    matchLabels:
      app: nexamem-chat
  template:
    metadata:
      labels:
        app: nexamem-chat
    spec:
      containers:
      - name: chat-service
        image: your-registry/nexamem-chat:latest
        ports:
        - containerPort: 8000
        env:
        # Redis for real-time chat
        - name: REDIS_HOSTNAME
          value: "your-cache.redis.cache.windows.net"
        - name: REDIS_ACCESS_KEY
          valueFrom:
            secretKeyRef:
              name: azure-secrets
              key: redis-key
        
        # Cosmos DB for global data
        - name: COSMOS_ENDPOINT
          value: "https://your-account.documents.azure.com:443/"
        - name: COSMOS_KEY
          valueFrom:
            secretKeyRef:
              name: azure-secrets
              key: cosmos-key
        
        # Blob Storage for large content
        - name: BLOB_ACCOUNT
          value: "yourstorageaccount"
        - name: BLOB_KEY
          valueFrom:
            secretKeyRef:
              name: azure-secrets
              key: blob-key
        
        # AI Search for semantic search
        - name: SEARCH_ENDPOINT
          value: "https://your-search.search.windows.net"
        - name: SEARCH_KEY
          valueFrom:
            secretKeyRef:
              name: azure-secrets
              key: search-key
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: azure-secrets
              key: openai-key
        
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5

---
apiVersion: v1
kind: Secret
metadata:
  name: azure-secrets
type: Opaque
data:
  redis-key: <base64-encoded-redis-key>
  cosmos-key: <base64-encoded-cosmos-key>
  blob-key: <base64-encoded-blob-key>
  search-key: <base64-encoded-search-key>
  openai-key: <base64-encoded-openai-key>
```

### Docker Compose for Development

```yaml
# docker-compose.yml
version: '3.8'

services:
  nexamem-chat:
    build: .
    ports:
      - "8000:8000"
    environment:
      # Use local Redis for development
      - NEXAMEM_STORAGE_TYPE=memory
      
      # Or use Azure services for staging
      # - NEXAMEM_STORAGE_TYPE=azure_redis
      # - AZURE_REDIS_HOSTNAME=your-cache.redis.cache.windows.net
      # - AZURE_REDIS_ACCESS_KEY=your-redis-key
      
    volumes:
      - ./app:/app
    depends_on:
      - redis
      - mongodb  # Local alternatives for development

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data

  mongodb:
    image: mongo:6
    ports:
      - "27017:27017"
    environment:
      - MONGO_INITDB_ROOT_USERNAME=admin
      - MONGO_INITDB_ROOT_PASSWORD=password
    volumes:
      - mongo_data:/data/db

  # Local vector search alternative
  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
    volumes:
      - qdrant_data:/qdrant/storage

volumes:
  redis_data:
  mongo_data:
  qdrant_data:
```

### Health Monitoring and Metrics

```python
import asyncio
import time
from typing import Dict, Any
from nexamem.storage.interfaces import create_memory_service

class StorageMonitor:
    """Monitor health and performance of all storage backends."""
    
    def __init__(self):
        self.storage_services = {
            "redis": create_memory_service("azure_redis", **redis_config),
            "cosmos": create_memory_service("azure_cosmos", **cosmos_config),
            "blob": create_memory_service("azure_blob", **blob_config),
            "search": create_memory_service("azure_ai_search", **search_config)
        }
        self.metrics = {}
    
    async def health_check_all(self) -> Dict[str, Any]:
        """Perform health check on all storage backends."""
        health_status = {}
        
        for name, service in self.storage_services.items():
            try:
                start_time = time.time()
                
                if hasattr(service.storage, 'get_health_status'):
                    health = await service.storage.get_health_status()
                else:
                    ping_result = await service.storage.ping()
                    health = {"status": "healthy" if ping_result else "unhealthy"}
                
                health['response_time_ms'] = round((time.time() - start_time) * 1000, 2)
                health_status[name] = health
                
            except Exception as e:
                health_status[name] = {
                    "status": "unhealthy",
                    "error": str(e),
                    "response_time_ms": round((time.time() - start_time) * 1000, 2)
                }
        
        return health_status
    
    async def performance_test(self, iterations: int = 100) -> Dict[str, Any]:
        """Run performance tests on all storage backends."""
        results = {}
        
        for name, service in self.storage_services.items():
            print(f"Testing {name} performance...")
            
            # Test write performance
            write_times = []
            for i in range(iterations):
                start_time = time.time()
                await service.store_conversation_turn(
                    f"perf_test_{i}",
                    {"test": f"performance test {i}", "data": "x" * 100}
                )
                write_times.append((time.time() - start_time) * 1000)
            
            # Test read performance
            read_times = []
            for i in range(min(iterations, 10)):  # Test fewer reads
                start_time = time.time()
                await service.get_conversation_history(f"perf_test_{i}")
                read_times.append((time.time() - start_time) * 1000)
            
            results[name] = {
                "write_avg_ms": round(sum(write_times) / len(write_times), 2),
                "write_max_ms": round(max(write_times), 2),
                "write_min_ms": round(min(write_times), 2),
                "read_avg_ms": round(sum(read_times) / len(read_times), 2),
                "read_max_ms": round(max(read_times), 2),
                "read_min_ms": round(min(read_times), 2),
            }
        
        return results

# Usage
async def monitor_storage_health():
    monitor = StorageMonitor()
    
    # Continuous health monitoring
    while True:
        health = await monitor.health_check_all()
        print("Storage Health Status:", health)
        
        # Alert if any service is unhealthy
        unhealthy_services = [name for name, status in health.items() 
                            if status.get("status") != "healthy"]
        
        if unhealthy_services:
            print(f"ALERT: Unhealthy services: {unhealthy_services}")
        
        await asyncio.sleep(60)  # Check every minute

if __name__ == "__main__":
    asyncio.run(monitor_storage_health())
```

This comprehensive set of examples demonstrates:

1. **3-line integration** for all storage backends
2. **Framework integration** with FastAPI supporting multiple backends
3. **Environment-based configuration** for production deployments
4. **Custom embedding providers** for AI Search
5. **Kubernetes and Docker deployment** patterns
6. **Health monitoring and performance testing** across all services

External projects can choose the most appropriate storage backend(s) for their needs while maintaining consistent APIs and integration patterns across all options.