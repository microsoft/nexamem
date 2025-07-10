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

### 2. Example Scripts:
- Basic usage examples
- Azure Redis configuration
- Entra ID authentication setup
- Performance benchmarks

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

## 🎯 Success Metrics
- **Development Speed**: Complete package in <4 hours
- **Code Quality**: All tests pass, clean linting
- **User Experience**: One-line installation and setup
- **Production Ready**: Handles errors gracefully
- **Modern Tooling**: UV, type hints, enums

This blueprint enables rapid recreation of NexaMem using AI-assisted hyper velocity engineering techniques!
