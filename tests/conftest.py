"""
Conftest.py - Shared fixtures and configuration for pytest
"""
import os
import tempfile
from unittest.mock import Mock

import pytest
import yaml

from nexamem import AIMemory, ChannelConfig, ChannelManager, MemoryScope
from nexamem.redis_adapter import RedisAdapter


@pytest.fixture
def sample_scope():
    """Fixture providing a sample MemoryScope for testing."""
    return MemoryScope(
        agent_id="test_agent",
        user_id="user123",
        session_id="session456",
        env="test"
    )


@pytest.fixture
def sample_channel_config():
    """Fixture providing a sample ChannelConfig for testing."""
    return ChannelConfig(
        name="test_channel",
        ttl_sec=3600,
        encrypt=True,
        quota_bytes=1000000
    )


@pytest.fixture
def channels_yaml_content():
    """Fixture providing sample YAML content for channel configuration."""
    return {
        "channels": {
            "working": {
                "ttl_sec": 14400,
                "encrypt": True,
                "quota_bytes": 1000000
            },
            "procedure": {
                "ttl_sec": 604800,
                "encrypt": True
            },
            "routing": {
                "ttl_sec": 86400,
                "encrypt": False,
                "quota_bytes": 500000
            }
        }
    }


@pytest.fixture
def temp_channels_yaml(channels_yaml_content):
    """Fixture creating a temporary YAML file with channel configuration."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(channels_yaml_content, f)
        temp_file_path = f.name
    
    yield temp_file_path
    
    # Cleanup
    try:
        os.unlink(temp_file_path)
    except FileNotFoundError:
        pass


@pytest.fixture
def invalid_channels_yaml():
    """Fixture creating a temporary YAML file with invalid channel configuration."""
    invalid_content = {
        "channels": {
            "Invalid-Channel": {  # Invalid name (not snake_case)
                "ttl_sec": 999999,  # Invalid TTL (too high)
                "encrypt": "not_boolean",  # Invalid type
                "unknown_field": "value"  # Unknown field
            }
        }
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(invalid_content, f)
        temp_file_path = f.name
    
    yield temp_file_path
    
    # Cleanup
    try:
        os.unlink(temp_file_path)
    except FileNotFoundError:
        pass


@pytest.fixture
def mock_redis():
    """Fixture providing a mock Redis instance."""
    mock = Mock()
    # Setup common Redis method mocks
    mock.ping.return_value = True
    mock.set.return_value = True
    mock.get.return_value = None
    mock.zadd.return_value = 1
    mock.zrange.return_value = []
    mock.zrangebyscore.return_value = []
    mock.zrem.return_value = 1
    mock.delete.return_value = 1
    mock.scan_iter.return_value = iter([])
    mock.xadd.return_value = b'1234567890-0'
    mock.pipeline.return_value = mock
    mock.execute.return_value = []
    return mock


@pytest.fixture
def redis_adapter(mock_redis):
    """Fixture providing a RedisAdapter with mocked Redis."""
    adapter = RedisAdapter(use_fakeredis=True)
    adapter.redis = mock_redis
    return adapter


@pytest.fixture
def channel_manager(temp_channels_yaml):
    """Fixture providing a ChannelManager with test configuration."""
    return ChannelManager(channels_yaml=temp_channels_yaml)


@pytest.fixture
def aimemory_instance(temp_channels_yaml):
    """Fixture providing an AIMemory instance for testing."""
    return AIMemory(
        channels_yaml=temp_channels_yaml,
        use_fakeredis=True,
        enable_audit=False,  # Disable for cleaner tests
        enable_metrics=False,  # Disable for cleaner tests
        enable_content_processing=False
    )


@pytest.fixture
def aimemory_with_features(temp_channels_yaml):
    """Fixture providing an AIMemory instance with all features enabled."""
    return AIMemory(
        channels_yaml=temp_channels_yaml,
        use_fakeredis=True,
        enable_audit=True,
        enable_metrics=True,
        enable_content_processing=True
    )


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "slow: marks tests as slow running"
    )
    config.addinivalue_line(
        "markers", "redis: marks tests that require Redis"
    )
    config.addinivalue_line(
        "markers", "azure: marks tests that require Azure services"
    )
