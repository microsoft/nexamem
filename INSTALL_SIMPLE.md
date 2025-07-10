# 🚀 NexaMem/AIMemory v0.3 Installation Guide

## 📦 Standard Installation (Everything Included!)

NexaMem now includes all essential dependencies by default - no need for extras!

### Option 1: Install with pip
```bash
pip install nexamem
```

### Option 2: Install with uv (10x faster)
```bash
uv add nexamem
```

## ✅ What's Included by Default

When you install `nexamem`, you automatically get:

- **Core AIMemory functionality** - Redis-backed conversational memory
- **Redis & Async support** - Full Redis integration with async capabilities  
- **YAML configuration** - Channel configuration via YAML files
- **Azure integration** - Identity and KeyVault support for enterprise deployments
- **Policy enforcement** - TTL, encryption, quota management
- **Content processing** - PII detection and redaction
- **Audit logging** - Redis Stream-based operation tracking
- **Metrics collection** - Prometheus-style metrics

## 🔧 Development Installation (Optional)

Only needed if you're contributing to the project:

### With pip:
```bash
pip install nexamem[dev]
```

### With uv:
```bash
uv add --dev nexamem[dev]
```

### Development extras include:
- `pytest` - Testing framework with async support
- `black` - Code formatting
- `ruff` - Fast linting
- `mypy` - Type checking
- `pytest-cov` - Coverage reporting

## 📚 All Development Tools

For complete development environment:

```bash
# With pip
pip install nexamem[all]

# With uv  
uv add nexamem[all]
```

## ⚡ Why UV?

UV offers significant advantages:
- **~10x faster** dependency resolution
- **Better lock files** for reproducible builds
- **Built-in virtual environments**
- **Excellent CI/CD performance**

## 📋 Verify Installation

```bash
python -c "import nexamem; print(f'✅ NexaMem {nexamem.__version__} installed with all features!')"
```

## 🎯 Ready to Use

```python
from nexamem import AIMemory, MemoryScope

# All dependencies included - no extra configuration needed!
memory = AIMemory(redis_url="redis://localhost:6379")
scope = MemoryScope(agent_id="my_agent", user_id="user123")

# Start using immediately
memory.write(scope, "working", "Hello from AIMemory!")
```

## 🚀 Quick Start

1. **Install**: `pip install nexamem` or `uv add nexamem`
2. **Import**: `from nexamem import AIMemory, MemoryScope`
3. **Use**: All features ready out of the box!

No more complex installation steps or missing dependencies! 🎉
