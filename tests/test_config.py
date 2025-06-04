import pytest
from nexamem import initialize, get_config
from nexamem.config import ConfigError

# Updated to include required 'history_storage' parameter
def test_initialize_and_get_config():
    config = {"api_key": "test-key", "timeout": 30, "history_storage": "memory"}
    initialize(config)
    result = get_config()
    assert result["api_key"] == "test-key"
    assert result["timeout"] == 30
    assert result["history_storage"] == "memory"

def test_initialize_memory():
    config = {"history_storage": "memory", "debug": True}
    initialize(config)
    assert get_config()["history_storage"] == "memory"
    assert get_config()["debug"] is True

def test_initialize_file():
    config = {"history_storage": "file", "file_path": "/tmp/chat_history.json"}
    initialize(config)
    assert get_config()["history_storage"] == "file"
    assert get_config()["file_path"] == "/tmp/chat_history.json"
    assert get_config()["debug"] is False  # default

def test_initialize_missing_file_path():
    config = {"history_storage": "file"}
    with pytest.raises(ConfigError):
        initialize(config)

def test_initialize_invalid_storage():
    config = {"history_storage": "invalid"}
    with pytest.raises(ConfigError):
        initialize(config)
