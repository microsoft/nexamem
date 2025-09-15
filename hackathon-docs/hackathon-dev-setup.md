# NexaMem Hackathon Development Setup Guide

## 🚀 Quick Setup for Hackathon Development

This guide shows how to set up NexaMem for hackathon development, especially when you want to contribute back to this repo while using it in another production project (like C42).

---

## 📋 Prerequisites

- **Python 3.8+**
- **uv** package manager (faster than pip)
- **Git** for version control
- **Azure Redis instance** (for production features)

### Install `uv` (if not already installed)

```bash
# Windows
curl -LsSf https://astral.sh/uv/install.ps1 | powershell

# macOS/Linux  
curl -LsSf https://astral.sh/uv/install.sh | sh
```

---

## 🏗️ Development Workflow Options

### Option 1: Editable Install with `uv` (Recommended for Hackathon)

Perfect when you want to develop NexaMem features and immediately test them in your production project.

```bash
# 1. Directory structure (recommended)
/projects/
├── nexamem/          # This repo - your development workspace
└── c42/              # Your production repo

# 2. In your production repo (C42), install NexaMem as editable
cd c42
uv add --editable ../nexamem

# 3. Now you get real-time updates!
# ✅ Changes in nexamem/ immediately available in C42
# ✅ Fast installs with uv
# ✅ Can test Azure Redis features instantly
```

### Option 2: Development vs Production Dependencies

Clean separation of development and production dependencies:

```bash
# In your production repo (C42)
# Add as dev dependency for hackathon
uv add --dev --editable ../nexamem

# For production, you'd later add stable version:
uv add nexamem  # stable version from PyPI
```

### Option 3: Configuration via `pyproject.toml`

Edit your production project's `pyproject.toml`:

```toml
[project.dependencies]
# Your production dependencies here

[tool.uv.dev-dependencies]  
nexamem = { path = "../nexamem", editable = true }
```

Then run:

```bash
uv sync --dev
```

---

## 📦 Installation Commands

### Installing NexaMem from GitHub

```bash
# Standard installation from GitHub
uv add git+https://github.com/microsoft/nexamem.git

# Install specific branch (like your hackathon branch)
uv add git+https://github.com/microsoft/nexamem.git@dev/barry/hackathon-memory-svc
```

### Installing Local Development Version

```bash
# Editable install from local directory
uv add --editable /path/to/local/nexamem/repo

# If repos are side by side:
uv add --editable ../nexamem

# As development dependency only:
uv add --dev --editable ../nexamem
```

---

## 🎯 Perfect Hackathon Setup

### Step 1: Clone and Setup NexaMem

```bash
# Clone this repo for development
git clone https://github.com/microsoft/nexamem.git
cd nexamem

# Create virtual environment and install dependencies
uv venv
uv sync

# Activate environment
# Windows:
.venv\Scripts\activate
# Unix/Linux/macOS:
source .venv/bin/activate
```

### Step 2: Setup Your Production Project

```bash
# Navigate to your production project
cd ../c42  # or wherever your production repo is

# Add NexaMem as editable development dependency
uv add --dev --editable ../nexamem

# Verify installation
uv run python -c "import nexamem; print('✅ NexaMem installed successfully')"
```

### Step 3: Verify Real-time Updates

```bash
# 1. Make a small change in nexamem/src/nexamem/__init__.py
# 2. In your C42 project, test the change:
cd ../c42
uv run python -c "import nexamem; print(nexamem.__version__)"
# ✅ You should see changes immediately without reinstalling!
```

---

## ⚡ Benefits of This Setup

### 🔄 **Real-time Development**

- Changes in NexaMem immediately available in your production project
- No need to reinstall after each change
- Perfect for rapid hackathon development

### 🚀 **Speed with `uv`**

- Much faster than pip for installations
- Better dependency resolution
- Faster virtual environment creation

### 🛡️ **Clean Dependencies**

- Separates development vs production dependencies
- Easy to remove development setup later
- No pollution of production dependency tree

### 🔧 **Easy Testing**

- Test Azure Redis implementations immediately
- Validate changes against real production code
- Quick iteration cycle

---

## 🧪 Testing Your Setup

### Test NexaMem Installation

```bash
# In your production project directory
uv run python -c "
from nexamem import AIMemory, AIMemoryConfig, StorageConfig, MemoryScope
print('✅ NexaMem imports successfully')
print('✅ All core classes available')
"
```

### Test Azure Redis Configuration

```bash
# Test Azure Redis configuration (without connecting)
uv run python -c "
from nexamem import StorageConfig
config = StorageConfig.azure_redis(
    hostname='test.redis.cache.windows.net',
    access_key='dummy_key',
    port=6380,
    ssl=True
)
print('✅ Azure Redis configuration works')
"
```

### Test Memory Storage (for development)

```python
# Create test_nexamem.py in your production project
from nexamem import AIMemory, AIMemoryConfig, StorageConfig, MemoryScope

# Test with in-memory storage first
config = AIMemoryConfig(
    default_scope="test_session",
    storage=StorageConfig.memory()
)
memory = AIMemory(config)

scope = MemoryScope(
    agent_id="test_agent",
    user_id="user_123",
    session_id="session_abc"
)

# Test basic operations
message_id = memory.store("Test message", scope="test")
result = memory.retrieve(message_id)
print(f"✅ Stored and retrieved: {result}")
```

```bash
# Run the test
uv run python test_nexamem.py
```

---

## 🛠️ Development Workflow

### Daily Development Routine

1. **Work in NexaMem repo**:

   ```bash
   cd nexamem
   # Make your Azure Redis improvements
   # Edit src/nexamem/storage/azure_redis.py
   ```

2. **Test immediately in production project**:

   ```bash
   cd ../c42
   # Run your production code with new NexaMem features
   uv run python your_app.py
   ```

3. **Commit and push improvements**:

   ```bash
   cd ../nexamem
   git add .
   git commit -m "Implement Azure Redis storage improvements"
   git push origin dev/barry/hackathon-memory-svc
   ```

### When Hackathon is Complete

```bash
# In your production project, switch to stable version
cd c42
uv remove nexamem  # Remove dev dependency
uv add nexamem     # Add stable version from PyPI

# Or update pyproject.toml to use released version
```

---

## 🐛 Troubleshooting

### Common Issues and Solutions

#### Import Errors

```bash
# Make sure package is installed in editable mode
uv list | grep nexamem
# Should show: nexamem (editable)

# If not, reinstall:
uv add --dev --editable ../nexamem
```

#### Changes Not Reflecting

```bash
# Verify editable install
uv run python -c "import nexamem; print(nexamem.__file__)"
# Should point to your local nexamem directory

# If pointing to site-packages, reinstall as editable
```

#### Redis Connection Issues

- Check Azure firewall settings
- Verify access keys
- Ensure SSL/TLS settings match Azure requirements
- Test with `fakeredis` for development

#### Virtual Environment Issues

```bash
# Create fresh environment
uv venv --force
uv sync
```

---

## 📚 Additional Resources

### Documentation Links

- **Architecture**: [`NEW_ARCHITECTURE.md`](../NEW_ARCHITECTURE.md) - Complete technical design
- **Work Items**: [`hackathon-docs/hackathon-work-items.md`](./hackathon-work-items.md) - Prioritized tasks
- **Status**: [`hackathon-docs/nexamem-solution-status.md`](./nexamem-solution-status.md) - Current implementation state

### Key Files for Hackathon Development

- **Azure Redis**: [`src/nexamem/storage/azure_redis.py`](../src/nexamem/storage/azure_redis.py)
- **Storage Config**: [`src/nexamem/config/storage.py`](../src/nexamem/config/storage.py)
- **Memory Scope**: [`src/nexamem/memory_scope.py`](../src/nexamem/memory_scope.py)
- **New AIMemory**: [`src/nexamem/new_aimemory.py`](../src/nexamem/new_aimemory.py)

### Quick Commands Reference

```bash
# Setup
uv add --dev --editable ../nexamem

# Test
uv run python -c "import nexamem; print('OK')"

# Run tests
uv run pytest tests/

# Check what's installed
uv list

# Update dependencies
uv sync
```

---

*Setup Guide Updated: September 14, 2025*  
*For Hackathon Development with uv Package Manager*