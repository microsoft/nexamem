# Async Testing Configuration for NexaMem

## Overview
This document outlines the async testing setup for NexaMem and provides troubleshooting guidance for CI/CD pipelines.

## Async Testing Dependencies

### Required Packages
- `pytest>=7.0.0,<9.0` - Core testing framework
- `pytest-asyncio>=0.21.0,<2.0` - Async support for pytest
- `pytest-cov>=4.0.0,<7.0` - Coverage reporting

### Installation
```bash
# For development
pip install nexamem[dev]

# For CI/CD pipelines
pip install -r requirements-test.txt
```

## Configuration

### pytest.ini Configuration
The project uses `pyproject.toml` for pytest configuration:

```toml
[tool.pytest.ini_options]
minversion = "7.0"
addopts = [
    "--strict-markers",
    "--strict-config",
    "--cov=nexamem",
    "--cov-report=term-missing",
    "--cov-report=html",
    "--cov-report=xml",
]
testpaths = ["tests"]
markers = [
    "slow: marks tests as slow (deselect with '-m \"not slow\"')",
    "integration: marks tests as integration tests",
    "redis: marks tests that require Redis",
    "azure: marks tests that require Azure services",
]
asyncio_mode = "auto"
```

### Key Configuration Notes
- `asyncio_mode = "auto"` enables automatic async test detection
- Tests marked with `@pytest.mark.asyncio` will run in async mode
- Both sync and async tests can coexist in the same test suite

## Running Tests

### Local Development
```bash
# Run all tests
python -m pytest tests/ -v

# Run only async tests
python -m pytest tests/ -v -k "async"

# Run with coverage
python -m pytest tests/ --cov=nexamem --cov-report=term-missing
```

### CI/CD Pipelines
Use the provided test runner:
```bash
python run_tests.py
```

Or run tests directly:
```bash
pip install -r requirements-test.txt
python -m pytest tests/ -v --tb=short --strict-markers --strict-config
```

## Async Test Examples

### Basic Async Test
```python
import pytest

@pytest.mark.asyncio
async def test_async_functionality():
    async def async_operation():
        await asyncio.sleep(0.01)
        return "result"
    
    result = await async_operation()
    assert result == "result"
```

### Async Class Tests
```python
@pytest.mark.asyncio
class TestAsyncClass:
    async def test_method(self):
        # Async test method
        pass
```

## Troubleshooting

### Common Issues

1. **ImportError: No module named 'pytest_asyncio'**
   - Solution: Install pytest-asyncio: `pip install pytest-asyncio>=0.21.0`

2. **RuntimeError: asyncio.run() cannot be called from a running event loop**
   - Solution: Ensure `asyncio_mode = "auto"` is set in pytest configuration

3. **Tests hang or timeout**
   - Check for infinite loops in async code
   - Ensure all async operations are properly awaited
   - Add timeout markers: `@pytest.mark.timeout(30)`

4. **Version compatibility issues**
   - Ensure pytest-asyncio version is compatible: `>=0.21.0,<2.0`
   - Check Python version compatibility (3.8+)

### Pipeline-Specific Issues

1. **Dependencies not installed**
   - Ensure test dependencies are installed: `pip install -r requirements-test.txt`
   - Or install dev extras: `pip install nexamem[dev]`

2. **Different behavior in CI vs local**
   - Check Python version consistency
   - Verify environment variables
   - Use `python run_tests.py` for consistent behavior

### Debugging Commands

```bash
# Check pytest-asyncio version
python -c "import pytest_asyncio; print(pytest_asyncio.__version__)"

# List all tests
python -m pytest tests/ --collect-only

# Run with maximum verbosity
python -m pytest tests/ -vvv --tb=long

# Run specific async test
python -m pytest tests/test_async_verification.py::test_basic_async_functionality -v
```

## Best Practices

1. **Test Organization**
   - Keep async and sync tests in the same files when related
   - Use descriptive test names that indicate async behavior
   - Group related async tests in classes marked with `@pytest.mark.asyncio`

2. **Performance**
   - Use `asyncio.sleep(0.01)` for minimal delays in tests
   - Avoid unnecessary `await` statements
   - Mock external async dependencies

3. **Error Handling**
   - Test both success and error cases for async operations
   - Use `pytest.raises` for expected exceptions in async code
   - Ensure proper cleanup in async fixtures

## Files Modified/Created

1. **pyproject.toml** - Updated pytest-asyncio version constraints
2. **requirements.txt** - Updated development dependency versions
3. **requirements-test.txt** - New file for CI/CD test dependencies
4. **run_tests.py** - New comprehensive test runner script
5. **tests/test_storage_base.py** - Fixed MockStorage implementation
6. **tests/test_async_verification.py** - New async verification tests
7. **ASYNC_TESTING.md** - This documentation file

## Verification

All async tests should pass with the current configuration. Run the verification test:

```bash
python -m pytest tests/test_async_verification.py -v
```

Expected output:
- ✅ test_basic_async_functionality PASSED
- ✅ test_async_with_redis_mock PASSED  
- ✅ test_sync_functionality PASSED
