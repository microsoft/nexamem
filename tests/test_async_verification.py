"""Simple async test to verify pytest-asyncio is working correctly."""

import asyncio
import pytest


@pytest.mark.asyncio
async def test_basic_async_functionality():
    """Test that basic async functionality works in pytest."""
    async def async_function():
        await asyncio.sleep(0.01)
        return "async_result"
    
    result = await async_function()
    assert result == "async_result"


@pytest.mark.asyncio
async def test_async_with_redis_mock():
    """Test async functionality with Redis-like operations."""
    # Simulate async Redis operations
    data_store = {}
    
    async def async_set(key, value):
        await asyncio.sleep(0.01)  # Simulate async operation
        data_store[key] = value
        return True
    
    async def async_get(key):
        await asyncio.sleep(0.01)  # Simulate async operation
        return data_store.get(key)
    
    # Test the async operations
    assert await async_set("test_key", "test_value") is True
    assert await async_get("test_key") == "test_value"
    assert await async_get("nonexistent") is None


def test_sync_functionality():
    """Test that sync tests still work alongside async tests."""
    assert True is True
    assert 1 + 1 == 2
