"""CI-specific async test to verify pytest-asyncio is working in GitHub Actions."""

import asyncio

import pytest


@pytest.mark.asyncio
async def test_ci_async_support():
    """Test specifically designed to fail if pytest-asyncio is not working."""
    # This will fail with a clear error if pytest-asyncio is not loaded
    await asyncio.sleep(0.001)
    
    # Verify we're actually in an async context
    loop = asyncio.get_running_loop()
    assert loop is not None
    
    # Test that async context manager works
    class AsyncContextManager:
        async def __aenter__(self):
            return "async_value"
        
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass
    
    async with AsyncContextManager() as value:
        assert value == "async_value"


@pytest.mark.asyncio
async def test_multiple_async_operations():
    """Test multiple async operations to ensure proper event loop handling."""
    results = []
    
    async def async_task(value):
        await asyncio.sleep(0.001)
        return f"task_{value}"
    
    # Run multiple async operations
    tasks = [async_task(i) for i in range(3)]
    results = await asyncio.gather(*tasks)
    
    expected = ["task_0", "task_1", "task_2"]
    assert results == expected


def test_sync_and_async_compatibility():
    """Ensure sync tests still work when pytest-asyncio is loaded."""
    assert True
    
    # This should not interfere with async tests
    import asyncio
    
    # We can create a loop in sync context
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    async def simple_async():
        return "sync_created"
    
    result = loop.run_until_complete(simple_async())
    assert result == "sync_created"
    
    loop.close()
