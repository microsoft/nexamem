# PyProject.toml Updates for AIMemory v0.3

## Summary of Changes

The `pyproject.toml` file has been significantly updated to align with the AIMemory v0.3 architecture and improve compatibility with both PIP and UV package managers.

## Key Changes Made

### 1. **Enhanced Project Metadata**
- **Description**: Updated to reflect enterprise-grade Redis-backed conversational memory
- **Keywords**: Added AI-specific terms: `aimemory`, `governance`, `policy`, `audit`, `compliance`, `pii`, `content-processing`, `enterprise`, `async`, `channels`
- **Classifiers**: Added comprehensive classifiers for better discoverability:
  - Development status, audience, topics
  - Framework support (AsyncIO)
  - Type checking support

### 2. **Improved Dependencies**
- **Redis**: Changed from `redis>=5.0.0` to `redis[asyncio]>=5.0.0,<6.0` for async support
- **Version Pinning**: Added upper bounds for better stability (`<3.0`, `<6.0`, `<7.0`)
- **Azure Integration**: Added conditional Azure Identity dependency
- **YAML Support**: Maintained PyYAML for channel configuration

### 3. **Optional Dependencies (Extras)**
Added comprehensive optional dependency groups:

```toml
[project.optional-dependencies]
azure = ["azure-identity>=1.15.0,<2.0", "azure-keyvault-secrets>=4.7.0,<5.0"]
dev = ["pytest>=7.0.0,<8.0", "pytest-asyncio>=0.21.0,<1.0", ...]
docs = ["mkdocs>=1.5.0,<2.0", "mkdocs-material>=9.0.0,<10.0", ...]
perf = ["pytest-benchmark>=4.0.0,<5.0", "memory-profiler>=0.60.0,<1.0"]
all = ["nexamem[azure,dev,docs,perf]"]
```

### 4. **Enhanced URLs**
- Added documentation, repository, changelog, and discussions links
- Better project discoverability and maintainability

### 5. **Tool Configuration**
Added comprehensive tool configurations for:
- **Black**: Code formatting
- **Ruff**: Fast linting with specific rules
- **MyPy**: Type checking with strict settings
- **Pytest**: Testing with coverage and async support
- **Coverage**: Detailed coverage reporting

### 6. **UV Package Manager Support**
- **UV-specific configuration** in dedicated sections
- **Workspace support** for monorepo development
- **Dev dependencies** optimized for UV's fast resolution
- **Lock file configuration** for reproducible builds

### 7. **Type Support**
- Added `py.typed` marker file for PEP 561 compliance
- Package data configuration for YAML files
- Type checking classifier added

## Installation Benefits

### Simplified Installation (Everything Included):
```bash
# Basic installation - includes ALL essential features
pip install nexamem
# OR with UV (10x faster)
uv add nexamem
```

**What's included by default:**
- Core AIMemory functionality
- Redis with async support
- YAML configuration
- Azure identity & KeyVault integration
- Policy enforcement & governance
- Content processing & PII detection
- Audit logging & metrics

### Optional Development Tools:
```bash
# Development environment (only for contributors)
pip install nexamem[dev]
# OR with UV
uv add --dev nexamem[dev]

# Everything including docs and performance tools
pip install nexamem[all]
# OR with UV
uv add nexamem[all]
```

## Compatibility

- **Python Versions**: 3.8 - 3.13 (including 3.13 support)
- **Package Managers**: PIP, UV, Poetry, PDM
- **Deployment**: Compatible with Docker, Azure, AWS, GCP
- **CI/CD**: Optimized for GitHub Actions, Azure DevOps, GitLab CI

## Version Information

- **Current Version**: 0.3.4
- **Version accessible**: `import nexamem; print(nexamem.__version__)`
- **Semantic Versioning**: Following SemVer for predictable upgrades

## Files Modified

1. `pyproject.toml` - Main project configuration
2. `requirements.txt` - Updated with new dependencies
3. `src/nexamem/__init__.py` - Added version information
4. `src/nexamem/py.typed` - Type checking marker (new)
5. `uv.toml` - UV-specific configuration (new)
6. `INSTALLATION.md` - Installation guide (new)

## Benefits for Development

1. **Faster builds** with UV support
2. **Better dependency resolution** with version constraints
3. **Enhanced tooling** with linting, formatting, and type checking
4. **Comprehensive testing** with async support
5. **Documentation generation** capabilities
6. **Performance profiling** tools
7. **Azure integration** for enterprise deployments

## Migration Impact

- **Backward Compatible**: Existing installations continue to work
- **Optional Upgrades**: New features available through extras
- **Gradual Adoption**: Can migrate tools one by one
- **Enhanced Security**: Better dependency pinning and verification

This update positions NexaMem/AIMemory as an enterprise-ready package with modern tooling support and enhanced developer experience.
