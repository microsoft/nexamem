# Use this file to provide workspace-specific custom instructions to Copilot. For more details, visit https://code.visualstudio.com/docs/copilot/copilot-customization#_use-a-githubcopilotinstructionsmd-file

# NexaMem: Hyper Velocity Engineering Blueprint
# This serves as a complete guide for recreating NexaMem from scratch using AI-assisted development

## 🎯 Project Overview
- **Product**: NexaMem - A Python package for managing chatbot conversation history
- **Goal**: Demonstrate hyper velocity engineering by building a production-ready package with AI assistance
- **Target**: Modern Python package with Redis, Azure, SQLite support + type-safe enums

## 🏗️ Architecture Requirements

### Core Features to Implement:
1. **Multi-Storage Backend Support**:
   - In-memory storage (default)
   - File-based storage (JSON)
   - SQLite database storage
   - Redis storage (local + Azure Redis Cache)

2. **Azure Integration**:
   - Azure Redis Cache support
   - Access key authentication
   - Microsoft Entra ID (Azure AD) authentication
   - Token refresh handling

3. **Type-Safe Configuration**:
   - Pydantic models for message validation
   - Enums for storage types and auth methods
   - Configuration validation with clear error messages

4. **Developer Experience**:
   - IDE auto-completion support
   - Type hints throughout
   - Comprehensive error handling
   - Debug mode with detailed logging

5. **Enhanced Message Structure**:
   - Auto-generated chat_id for conversation grouping
   - Optional data field for JSON metadata storage
   - Multi-chat support for complex applications
   - Analytics and session management capabilities

## 📋 Technical Specifications

### Dependencies:
- `pydantic>=2.0` - Data validation and settings
- `redis>=5.0.0` - Redis client
- `azure-identity>=1.12.0` - Azure authentication
- `fakeredis>=2.21.0` - Testing and demos

### Python Compatibility:
- Support Python 3.8+ (including 3.13)
- Use modern typing features where appropriate
- Maintain backward compatibility

### Package Structure:
```
src/nexamem/
├── __init__.py          # Exports: ChatHistory, initialize, get_config, StorageType, RedisAuthMethod
├── config.py            # Configuration management with enum support
├── history.py           # Core ChatHistory class with all storage backends
└── py.typed             # Type checking marker

tests/
├── conftest.py          # Test configuration
├── test_config.py       # Configuration tests
├── test_history.py      # Core functionality tests
├── test_redis.py        # Redis-specific tests
└── test_enum_config.py  # Enum configuration tests

examples/
├── basic_usage.py       # Simple examples
├── redis_examples.py    # Redis configuration examples
└── enum_examples.py     # Type-safe configuration examples
```

## 🚀 Implementation Guidelines

### 1. Start with Core Classes:
```python
from enum import Enum
from pydantic import BaseModel

class StorageType(Enum):
    MEMORY = "memory"
    FILE = "file" 
    SQLITE = "sqlite"
    REDIS = "redis"

class RedisAuthMethod(Enum):
    ACCESS_KEY = "access_key"
    ENTRA_ID = "entra_id"
    AZURE_AD = "entra_id"  # Alias

class Message(BaseModel):
    role: str
    content: str
    chat_id: str
    data: str = ""  # Optional JSON string for metadata

class ChatHistory:
    # Implement all storage backends here
```

### 2. Configuration System:
- Global configuration with initialize() function
- Support both string and enum values
- Comprehensive validation with helpful error messages
- Debug mode for development

### 3. Redis Implementation:
- Support local Redis and Azure Redis Cache
- Handle both access key and Entra ID authentication
- Implement token refresh for Entra ID
- Include Redis info and query methods
- Use FakeRedis for testing

### 4. Testing Strategy:
- Unit tests for each storage backend
- Integration tests for Redis functionality
- Mock Azure authentication for testing
- Performance tests for large message sets
- Error handling and edge case coverage

### 5. Enhanced Message Structure Implementation:
- **chat_id field**: Auto-generated UUID or custom string for conversation grouping
- **data field**: JSON string for storing metadata (timestamps, analytics, user info)
- **API enhancement**: `add_message(role, content, chat_id=None, data="")`
- **Storage compatibility**: All backends (memory, file, SQLite, Redis) support new fields
- **Backward compatibility**: Existing code continues to work without changes
- **Migration logic**: Automatic addition of missing fields for legacy data

## 📚 Modern Python Package Best Practices

### pyproject.toml Configuration:
```toml
[build-system]
requires = ["setuptools>=68.0", "wheel", "build>=1.0.0"]
build-backend = "setuptools.build_meta"

[project]
name = "nexamem"
version = "0.3.2"
description = "NexaMem - A Python package to store and manage chatbot conversation history."
requires-python = ">=3.8"
keywords = ["chatbot", "history", "llm", "redis", "azure", "enum", "type-safe", "uv"]

[project.optional-dependencies]
dev = ["pytest>=8.0.0", "build>=1.0.0", "ruff>=0.1.0", "black>=23.0.0"]
test = ["pytest>=8.0.0", "pytest-cov>=4.0.0"]
```

### UV Support:
- Add [tool.uv] section for modern package management
- Include .uvignore for performance
- Create UV_GUIDE.md with usage examples

### Code Quality:
- Use ruff for linting and formatting
- Black for code formatting
- Type hints throughout
- Comprehensive docstrings
- Error handling with custom exceptions

## 🎪 Demo Features for Hyper Velocity

### 1. Jupyter Notebook Demo:
- Interactive examples of all features
- FakeRedis demo that works without setup
- Azure configuration examples
- Type-safe enum demonstrations
- Enhanced message structure with chat_id and data fields
- Type-safe enum demonstrations

### 2. Example Scripts:
- Basic usage examples
- Azure Redis configuration
- Entra ID authentication setup
- Performance benchmarks
- Multi-chat conversation management
- Metadata analytics and data extraction

### 3. Documentation:
- README.md with quick start
- REDIS_SUPPORT.md for Azure features
- UV_GUIDE.md for modern tooling
- API reference with examples

## 🔥 Hyper Velocity Engineering Tips

### AI-Assisted Development Process:
1. **Start with interfaces**: Define enums and models first
2. **Implement incrementally**: One storage backend at a time
3. **Test-driven**: Write tests alongside implementation
4. **Iterate rapidly**: Use AI to generate boilerplate and tests
5. **Document continuously**: Update docs as features are added

### Key AI Prompts for Recreation:
- "Create a ChatHistory class with [storage_type] support"
- "Add Redis authentication with Azure Entra ID"
- "Implement enhanced message structure with chat_id and data fields"
- "Add multi-chat support with conversation grouping"
- "Create analytics extraction from message metadata"
- "Update storage backends to support enhanced message structure"
- "Generate comprehensive tests for [feature]"
- "Create example scripts showing [functionality]"
- "Update documentation for [new_feature]"

### Validation Checkpoints:
- [ ] All storage backends work independently
- [ ] Redis supports both auth methods
- [ ] Enums provide type safety
- [ ] Tests achieve >90% coverage
- [ ] Examples run without errors
- [ ] Package builds and installs correctly
- [ ] UV support works seamlessly
- [ ] Enhanced message structure (chat_id, data) works across all backends
- [ ] Multi-chat support enables conversation grouping
- [ ] Metadata analytics work with data field
- [ ] Backward compatibility maintained for existing code

## 🎯 Success Metrics
- **Development Speed**: Complete package in <4 hours
- **Code Quality**: All tests pass, clean linting
- **User Experience**: One-line installation and setup
- **Production Ready**: Handles errors gracefully
- **Modern Tooling**: UV, type hints, enums

This blueprint enables rapid recreation of NexaMem using AI-assisted hyper velocity engineering techniques!

## 🎯 Enhanced Message Structure Usage Examples

### Basic Enhanced Usage:
```python
from nexamem import ChatHistory, initialize, StorageType

# Initialize with any storage backend
initialize({"history_storage": StorageType.MEMORY})
history = ChatHistory()

# Basic usage (auto-generated chat_id)
history.add_message(
    role="user", 
    content="Hello!",
    data='{"timestamp": "2025-01-10T10:00:00Z", "user_id": "123"}'
)

# Custom chat_id for conversation grouping
history.add_message(
    role="assistant", 
    content="Hi there!",
    chat_id="support_chat_001", 
    data='{"agent_id": "agent_007", "response_time": 150}'
)
```

### Multi-Chat Applications:
```python
# Support chat
history.add_message("user", "Help with billing", 
                   chat_id="support_001", 
                   data='{"priority": "high", "category": "billing"}')

# Sales chat  
history.add_message("user", "Tell me about products", 
                   chat_id="sales_002",
                   data='{"lead_source": "website", "interest": "high"}')

# Group messages by chat_id
messages = history.get_history()
chat_groups = {}
for msg in messages:
    chat_id = msg.get('chat_id', 'unknown')
    if chat_id not in chat_groups:
        chat_groups[chat_id] = []
    chat_groups[chat_id].append(msg)
```

### Analytics & Monitoring:
```python
# Store model performance data
history.add_message("assistant", "Here's the answer", 
                   data='{"model": "gpt-4", "tokens": 45, "confidence": 0.95}')

# Extract analytics from data fields
import json
total_tokens = 0
models_used = {}

for msg in history.get_history():
    if msg.get('data'):
        try:
            data = json.loads(msg['data'])
            if 'tokens' in data:
                total_tokens += data['tokens']
            if 'model' in data:
                model = data['model']
                models_used[model] = models_used.get(model, 0) + 1
        except json.JSONDecodeError:
            pass

print(f"Total tokens: {total_tokens}")
print(f"Models used: {models_used}")
```

### Message Structure:
```json
{
    "role": "user",
    "content": "Hello!",
    "chat_id": "auto_generated_or_custom_id", 
    "data": "{\"timestamp\": \"2025-01-10T10:00:00Z\", \"user_id\": \"123\"}"
}
```
