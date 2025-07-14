# 🚀 NexaMem/AIMemory v0.3 Installation Guide

## � Standard Installation

### Option 1: Install with pip (standard)
```bash
pip install nexamem
```

### Option 2: Install with uv (faster)
```bash
uv add nexamem
```

## 🔧 Development Installation

### With pip:
```bash
pip install -e .[dev]
```

### With uv:
```bash
uv add --dev nexamem[dev]
```

## ☁️ Azure Integration

### With pip:
```bash
pip install nexamem[azure]
```

### With uv:
```bash
uv add nexamem[azure]
```

## 📚 Full Installation (all features)

### With pip:
```bash
pip install nexamem[all]
```

### With uv:
```bash
uv add nexamem[all]
```

## 🔍 Available Extras

- **`azure`**: Azure identity and KeyVault integration
- **`dev`**: Development and testing tools
- **`docs`**: Documentation generation tools  
- **`perf`**: Performance testing and profiling
- **`all`**: All optional dependencies

## ⚡ UV Benefits

- **~10x faster** dependency resolution
- **Better lock file** management
- **Built-in virtual environment** management
- **Excellent for CI/CD** pipelines
- **Modern Python** package management

## 📋 Verify Installation

```python
import nexamem
print(f"✅ NexaMem {nexamem.__version__} installed successfully!")

# Test basic functionality
from nexamem import AIMemory, MemoryScope, AIMemoryConfig, StorageConfig
print("🎯 Core components available!")
```

## 🏗️ Development Setup

### Using UV (recommended)
```bash
# Clone repository
git clone https://github.com/microsoft/nexamem.git
cd nexamem

# Create virtual environment and install dependencies
uv venv
uv add --dev nexamem[dev]

# Activate environment
source .venv/bin/activate  # Linux/macOS
# or
.venv\Scripts\activate     # Windows

# Run tests
pytest
```

### Using pip
```bash
# Clone repository
git clone https://github.com/microsoft/nexamem.git
cd nexamem

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# or
.venv\Scripts\activate     # Windows

# Install in development mode
pip install -e .[dev]

# Run tests
pytest
```

## 🚀 Quick Start

```python
from nexamem import AIMemory, MemoryScope

# Create memory scope
scope = MemoryScope(
    agent_id="my_agent",
    user_id="user123",
    env="prod"
)

# Initialize AIMemory (requires Redis)
memory = AIMemory(redis_url="redis://localhost:6379")

# Write to conversation memory
message_id = memory.write(scope, "working", "Hello from NexaMem!")

# Read conversation history
messages, metadata = memory.read(scope, "working", max_msgs=10)
print(f"Retrieved {len(messages)} messages")
```

## 🐳 Docker Installation

```dockerfile
FROM python:3.11-slim

# Install with UV for faster builds
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Install NexaMem
RUN uv pip install nexamem[azure]

# Your application code
COPY . /app
WORKDIR /app

CMD ["python", "app.py"]
```

## 🔧 Troubleshooting

### Redis Connection Issues
```python
# Use fakeredis for testing without Redis server
from nexamem import AIMemory
memory = AIMemory(redis_url="fakeredis://")
```

### Import Errors
```bash
# Ensure you have the correct Python version
python --version  # Should be 3.8+

# Reinstall with dependencies
pip install --force-reinstall nexamem[all]
```

### Performance Issues
```bash
# Use UV for faster dependency resolution
uv add nexamem
```

## 📖 Next Steps

1. **Read the Documentation**: Check out the [README.md](README.md)
2. **Try the Examples**: Explore the [examples/](examples/) directory
3. **Run the Notebook**: Open [NexaMem_Test.ipynb](NexaMem_Test.ipynb)
4. **Configure Channels**: Create your [channels.yaml](channels.yaml)
5. **Deploy to Production**: Use Azure Redis Cache for enterprise deployments
