# NexaMem 3-Day Hackathon Implementation Guide

**Implementation roadmap for completing Redis backend and creating extensible service architecture**

---

## 🎯 Day 1: Redis Implementation & Core Services

### **Task 1.1: Complete Azure Redis Storage Implementation** ⏱️ 4-6h

#### **Current State Analysis**
- ✅ Redis connection and authentication setup complete
- ✅ Configuration classes (`AzureRedisConfig`) implemented  
- ⚠️ Core storage methods need implementation in `src/nexamem/storage/azure_redis.py`

#### **Implementation Steps**

1. **Complete AzureRedisStorage.store_memory()** ⏱️ 1h
```python
async def store_memory(self, memory_id: str, content: str, metadata: Dict[str, Any], scope: Optional[str] = None) -> bool:
    """Store memory in Redis Hash with scope indexing."""
    try:
        # Create memory record
        memory_data = {
            "id": memory_id,
            "content": content,
            "metadata": json.dumps(metadata),
            "timestamp": time.time(),
            "scope": scope or "default"
        }
        
        # Use pipeline for atomic operations
        async with self.client.pipeline() as pipe:
            # Store in main memories hash
            await pipe.hset(f"{self.prefix}:memories", memory_id, json.dumps(memory_data))
            
            # Add to scope index
            if scope:
                await pipe.sadd(f"{self.prefix}:scopes:{scope}", memory_id)
            
            # Add to audit stream
            await pipe.xadd(f"{self.prefix}:audit", {
                "action": "store",
                "memory_id": memory_id,
                "scope": scope or "default",
                "timestamp": time.time()
            })
            
            await pipe.execute()
        
        return True
    except Exception as e:
        # Log error and return False
        return False
```

2. **Complete AzureRedisStorage.retrieve_memory()** ⏱️ 30min
3. **Complete AzureRedisStorage.search_memories()** ⏱️ 1h  
4. **Complete AzureRedisStorage.get_audit_log()** ⏱️ 30min
5. **Add comprehensive error handling** ⏱️ 30min
6. **Write integration tests** ⏱️ 1-2h

### **Task 1.2: Service Factory Pattern** ⏱️ 2-3h

#### **Create MemoryServiceFactory**

1. **Create `src/nexamem/service_factory.py`** ⏱️ 1h
```python
"""Service factory for external project integration."""

from typing import Dict, Any, Protocol, Optional
from .config.aimemory import AIMemoryConfig
from .config.storage import StorageConfig
from .new_aimemory import AIMemory, AsyncAIMemory


class IConversationMemory(Protocol):
    """Standard interface for conversation memory services."""
    
    async def store_turn(self, conversation_id: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Store a conversation turn."""
        ...
    
    async def get_history(self, conversation_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get conversation history."""
        ...
    
    async def search_conversations(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search across conversations."""
        ...


class MemoryServiceFactory:
    """Factory for creating memory services for external integration."""
    
    @staticmethod
    def create_conversation_memory(
        service_type: str = "azure_redis",
        config: Optional[Dict[str, Any]] = None,
        async_preferred: bool = True
    ) -> Union[AIMemory, AsyncAIMemory]:
        """Create a conversation memory service."""
        
        # Build configuration
        storage_config = MemoryServiceFactory._build_storage_config(service_type, config or {})
        ai_config = AIMemoryConfig(
            default_scope=config.get("default_scope", "conversation"),
            storage=storage_config,
            channels_yaml=config.get("channels_yaml"),
            strict_yaml_validation=config.get("strict_validation", True)
        )
        
        # Return appropriate implementation
        if async_preferred:
            return AsyncAIMemory(ai_config)
        else:
            return AIMemory(ai_config)
    
    @staticmethod
    def create_from_env(async_preferred: bool = True) -> Union[AIMemory, AsyncAIMemory]:
        """Create service from environment variables."""
        config = AIMemoryConfig.from_env()
        
        if async_preferred:
            return AsyncAIMemory(config)
        else:
            return AIMemory(config)
    
    @staticmethod
    def _build_storage_config(service_type: str, config: Dict[str, Any]) -> StorageConfig:
        """Build storage configuration based on service type."""
        if service_type == "azure_redis":
            return StorageConfig.azure_redis(
                hostname=config.get("redis_hostname"),
                access_key=config.get("redis_access_key"),
                port=config.get("redis_port", 6380),
                ssl=config.get("redis_ssl", True)
            )
        elif service_type == "memory":
            return StorageConfig.memory()
        elif service_type == "file":
            return StorageConfig.file(config.get("file_path", "./nexamem_data"))
        else:
            raise ValueError(f"Unknown service type: {service_type}")
```

2. **Create integration adapter** ⏱️ 1h
3. **Add dependency injection helpers** ⏱️ 1h

---

## 🎯 Day 2: Integration Architecture & External Project Support

### **Task 2.1: External Project Integration** ⏱️ 4-5h

#### **Create DI Integration Patterns**

1. **Flask Integration Example** ⏱️ 1.5h
```python
# examples/flask_integration.py
from flask import Flask, request, jsonify
from nexamem import MemoryServiceFactory

app = Flask(__name__)

# Initialize memory service
memory_service = MemoryServiceFactory.create_conversation_memory(
    service_type="azure_redis",
    config={
        "redis_hostname": os.getenv("REDIS_HOSTNAME"),
        "redis_access_key": os.getenv("REDIS_ACCESS_KEY"),
        "default_scope": "flask_app"
    }
)

@app.route("/conversation/<conversation_id>/turn", methods=["POST"])
async def add_turn(conversation_id: str):
    data = request.get_json()
    
    turn_id = await memory_service.store_turn(
        conversation_id=conversation_id,
        content=data["content"],
        metadata={"user_id": data.get("user_id"), "timestamp": time.time()}
    )
    
    return jsonify({"turn_id": turn_id})

@app.route("/conversation/<conversation_id>/history")
async def get_history(conversation_id: str):
    limit = request.args.get("limit", 10, type=int)
    history = await memory_service.get_history(conversation_id, limit)
    return jsonify({"history": history})
```

2. **FastAPI Integration Example** ⏱️ 1.5h
3. **Generic DI Container Integration** ⏱️ 1h
4. **Configuration Templates** ⏱️ 1h

### **Task 2.2: Interface Standardization** ⏱️ 2-3h

1. **Create standard interfaces** ⏱️ 1h
2. **Add override patterns** ⏱️ 1h
3. **Document extension points** ⏱️ 1h

---

## 🎯 Day 3: Production Readiness & Documentation

### **Task 3.1: Production Configuration** ⏱️ 2-3h

1. **Health Check Endpoints** ⏱️ 1h
```python
# src/nexamem/health.py
class MemoryServiceHealthCheck:
    """Health check for memory services."""
    
    def __init__(self, memory_service):
        self.memory_service = memory_service
    
    async def check_health(self) -> Dict[str, Any]:
        """Perform health check."""
        try:
            # Test Redis connectivity
            test_id = await self.memory_service.store("health_check", {"test": True})
            await self.memory_service.retrieve(test_id)
            await self.memory_service.delete(test_id)
            
            return {
                "status": "healthy",
                "timestamp": time.time(),
                "checks": {
                    "redis_connectivity": "pass",
                    "basic_operations": "pass"
                }
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "timestamp": time.time(),
                "error": str(e)
            }
```

2. **Production configuration templates** ⏱️ 1h
3. **Deployment documentation** ⏱️ 1h

### **Task 3.2: Integration Examples** ⏱️ 3-4h

1. **Complete Flask example with tests** ⏱️ 1.5h
2. **Complete FastAPI example with tests** ⏱️ 1.5h
3. **Documentation and README updates** ⏱️ 1h

---

## 🔧 Implementation Priorities

### **Critical Path (Must Complete)**
1. Azure Redis storage implementation → Enables production use
2. Service factory pattern → Enables external integration
3. At least one framework integration example → Proves viability

### **High Value (Should Complete)**
4. Interface standardization → Enables extensibility
5. Health checks → Production readiness
6. Documentation → Developer adoption

### **Nice to Have (If Time Permits)**
7. Performance optimization → Scale preparation
8. Advanced features → Competitive advantage

---

## 🧪 Testing Strategy

### **Day 1 Testing**
- Integration tests for Azure Redis operations
- Unit tests for service factory
- Performance benchmarks

### **Day 2 Testing**  
- Integration example tests
- DI container tests
- Configuration validation tests

### **Day 3 Testing**
- End-to-end scenario tests
- Health check tests
- Production configuration tests

---

## 📋 File Structure Changes

```
src/nexamem/
├── service_factory.py          # NEW: External integration factory
├── health.py                   # NEW: Health check utilities
├── interfaces.py               # NEW: Standard interface contracts
└── integrations/               # NEW: Framework integrations
    ├── __init__.py
    ├── flask_provider.py
    └── fastapi_provider.py

examples/
├── flask_integration/          # NEW: Complete Flask example
├── fastapi_integration/        # NEW: Complete FastAPI example
└── generic_di_example/         # NEW: Generic DI example

docs/
├── integration_guide.md       # NEW: Integration documentation
└── deployment_guide.md        # NEW: Production deployment guide
```

---

## 🎯 Success Criteria

### **Day 1 Success**
- [ ] All Azure Redis storage methods implemented and tested
- [ ] Service factory creates working memory services
- [ ] Basic integration pattern documented

### **Day 2 Success**  
- [ ] At least one framework integration working end-to-end
- [ ] Standard interfaces defined and documented
- [ ] Configuration templates available

### **Day 3 Success**
- [ ] Production deployment guide complete
- [ ] Health checks implemented
- [ ] All integration examples tested and documented

### **Overall Hackathon Success**
- [ ] External projects can integrate NexaMem in <10 lines of code
- [ ] Production-ready Redis implementation available
- [ ] Clear path for extensibility and customization
- [ ] Documentation supports adoption

---

## 💡 Key Implementation Notes

### **Redis Implementation Tips**
- Use Redis pipelines for atomic multi-operations
- Implement proper connection pooling
- Add retry logic for transient failures
- Use Redis Streams for audit trail (append-only, time-ordered)

### **Service Factory Design**
- Support both dependency injection and direct instantiation
- Provide clear configuration patterns
- Enable easy testing with mock implementations
- Follow established DI container patterns

### **Integration Patterns**
- Provide adapters for popular frameworks
- Support both singleton and scoped lifetimes
- Enable configuration through environment variables
- Document common deployment scenarios

---

*This implementation guide provides specific technical direction for completing the NexaMem Redis implementation and creating an extensible service architecture suitable for enterprise AI applications.*