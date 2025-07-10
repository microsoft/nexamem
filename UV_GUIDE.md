# UV Usage Guide for NexaMem

UV is a fast Python package installer and resolver. Here's how to use it with NexaMem:

## Installation

### Install uv
```bash
# On macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# On Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Or with pip
pip install uv
```

### Install NexaMem with uv

```bash
# Install from PyPI (when published)
uv pip install nexamem

# Install from source
uv pip install -e .

# Install with development dependencies
uv pip install -e ".[dev]"

# Install with test dependencies
uv pip install -e ".[test]"

# Install with all optional dependencies
uv pip install -e ".[dev,test,docs]"
```

## Development Workflow

```bash
# Create virtual environment with uv
uv venv

# Activate virtual environment
source .venv/bin/activate  # Linux/macOS
# or
.venv\Scripts\activate  # Windows

# Install in development mode
uv pip install -e ".[dev]"

# Run tests
uv run pytest

# Build package
uv run python -m build

# Install from local wheel
uv pip install dist/nexamem-0.3.1-py3-none-any.whl
```

## Benefits of using uv with NexaMem

- **Speed**: 10-100x faster than pip for dependency resolution
- **Reliability**: Better dependency resolution and conflict detection
- **Modern**: Built for modern Python packaging standards
- **Compatible**: Drop-in replacement for most pip commands
- **Caching**: Smart caching reduces repeated downloads

## Environment Variables

```bash
# Faster dependency resolution
export UV_RESOLUTION=highest

# Enable pre-release packages if needed
export UV_PRERELEASE=allow

# Use system Python if preferred
export UV_SYSTEM_PYTHON=1
```

## Example: Quick Start with uv

```bash
# Clone repository
git clone https://github.com/microsoft/nexamem.git
cd nexamem

# Setup with uv (faster than pip)
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"

# Run tests
uv run pytest

# Start using NexaMem with enum support!
python -c "from nexamem import StorageType, RedisAuthMethod; print('✅ Ready!')"
```
