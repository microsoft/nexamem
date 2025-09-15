# pytest-asyncio GitHub Actions Fix

This document explains the changes made to fix pytest-asyncio issues in GitHub Actions CI pipeline.

## Problem

The `pytest-asyncio` plugin wasn't properly loaded in GitHub Actions, causing async tests to fail or be skipped in the CI environment while working locally.

## Root Causes

1. **Plugin Loading**: pytest-asyncio wasn't being explicitly loaded as a plugin in some CI environments
2. **Configuration Format**: Incorrect pytest.ini format (`[tool:pytest]` instead of `[pytest]`)
3. **Missing CLI Options**: Not explicitly specifying asyncio mode in CI commands
4. **Version Compatibility**: Using older pytest-asyncio version with potential compatibility issues

## Solutions Implemented

### 1. Updated GitHub Actions Workflow (`.github/workflows/ci.yml`)

**Added verification step:**
```yaml
- name: Verify pytest-asyncio installation
  run: |
    python -c "import pytest_asyncio; print(f'pytest-asyncio version: {pytest_asyncio.__version__}')"
    python -m pytest --version
    python -m pytest --markers | grep asyncio || echo "asyncio marker not found"
```

**Enhanced test execution:**
```yaml
- name: Run tests
  run: |
    python -m pytest tests/ -v --tb=short --asyncio-mode=auto -p pytest_asyncio

- name: Run async-specific tests
  run: |
    python -m pytest tests/test_async_verification.py tests/test_ci_async_verification.py -v --asyncio-mode=auto
```

### 2. Fixed pytest.ini Configuration

**Before:**
```ini
[tool:pytest]
testpaths = ["tests"]
addopts = --import-mode=importlib
pythonpath = src
asyncio_mode = auto
```

**After:**
```ini
[pytest]
testpaths = tests
addopts = --import-mode=importlib --asyncio-mode=auto
pythonpath = src
asyncio_mode = auto
```

### 3. Updated pytest-asyncio Version

**Before:**
```
pytest-asyncio>=0.21.0,<2.0
```

**After:**
```
pytest-asyncio>=0.23.0,<2.0
```

### 4. Added CI-Specific Test File

Created `tests/test_ci_async_verification.py` with comprehensive async tests that will fail obviously if pytest-asyncio isn't working properly.

### 5. Created Debug Script

Added `debug_pytest_asyncio.py` for troubleshooting pytest-asyncio issues:

```bash
python debug_pytest_asyncio.py
```

This script checks:
- pytest and pytest-asyncio installation
- Configuration files
- Basic async functionality
- pytest markers and plugins

## Key CLI Options for pytest-asyncio

1. **`--asyncio-mode=auto`**: Automatically detects and runs async tests
2. **`-p pytest_asyncio`**: Explicitly loads the pytest-asyncio plugin
3. **`--tb=short`**: Shorter traceback for better CI output readability

## Testing the Fix

### Local Testing
```bash
# Test all async tests
python -m pytest -k "asyncio" -v

# Test specific async files
python -m pytest tests/test_async_verification.py tests/test_ci_async_verification.py -v --asyncio-mode=auto

# Run debug script
python debug_pytest_asyncio.py
```

### CI Testing
The GitHub Actions workflow now includes:
1. Verification that pytest-asyncio is properly installed
2. Explicit plugin loading
3. Separate async test runs for better debugging

## Common Issues and Solutions

### Issue: "RuntimeError: no running event loop"
**Solution**: Ensure `asyncio_mode = auto` in pytest.ini and use `--asyncio-mode=auto`

### Issue: Async tests are skipped
**Solution**: Add `-p pytest_asyncio` to explicitly load the plugin

### Issue: "SyntaxError: 'async with' requires entering an async context"
**Solution**: Use proper async context managers with `__aenter__` and `__aexit__` methods

### Issue: Tests work locally but fail in CI
**Solution**: 
1. Verify pytest-asyncio installation in CI
2. Use explicit CLI options
3. Check pytest.ini format
4. Ensure consistent Python versions

## Best Practices

1. **Always specify asyncio mode explicitly** in CI environments
2. **Use the correct pytest.ini section format** (`[pytest]` not `[tool:pytest]`)
3. **Include verification steps** in CI to catch plugin loading issues early
4. **Test async functionality separately** to isolate issues
5. **Keep pytest-asyncio updated** to the latest stable version

## Files Modified

1. `.github/workflows/ci.yml` - Enhanced CI workflow
2. `pytest.ini` - Fixed configuration format
3. `requirements-test.txt` - Updated pytest-asyncio version
4. `tests/test_ci_async_verification.py` - New CI-specific tests
5. `debug_pytest_asyncio.py` - New diagnostic tool
