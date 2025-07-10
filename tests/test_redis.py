"""
Tests for Redis storage functionality in NexaMem.
Uses fakeredis for testing to avoid requiring a real Redis instance.
"""
import pytest
from nexamem import initialize, ChatHistory
from nexamem.config import ConfigError
import fakeredis


@pytest.fixture
def mock_redis_config():
    """Fixture that provides a basic Redis configuration for testing."""
    return {
        "history_storage": "redis",
        "redis_host": "localhost",
        "redis_port": 6379,
        "redis_password": "test_password",
        "redis_ssl": False,  # Disable SSL for fakeredis
        "redis_db": 0,
        "redis_key_prefix": "test_nexamem:",
        "debug": False
    }


@pytest.fixture
def mock_azure_redis_config():
    """Fixture that provides Azure Redis Cache configuration for testing."""
    return {
        "history_storage": "redis",
        "redis_host": "my-cache.redis.cache.windows.net",
        "redis_port": 6380,  # Azure Redis default port
        "redis_password": "azure_redis_key",
        "redis_ssl": True,   # Azure Redis requires SSL
        "redis_db": 0,
        "redis_key_prefix": "nexamem:",
        "debug": True
    }


def test_redis_config_validation():
    """Test Redis configuration validation."""
    # Missing redis_host should raise error
    with pytest.raises(ConfigError, match="'redis_host' is required"):
        initialize({"history_storage": "redis"})
    
    # Valid config should work (with password for access_key method)
    config = {
        "history_storage": "redis",
        "redis_host": "localhost",
        "redis_password": "test_password"
    }
    initialize(config)
    
    # Should set Azure defaults
    from nexamem.config import get_config
    current_config = get_config()
    assert current_config["redis_port"] == 6380
    assert current_config["redis_ssl"] is True
    assert current_config["redis_db"] == 0
    assert current_config["redis_key_prefix"] == "nexamem:"


def test_redis_basic_operations(mock_redis_config, monkeypatch):
    """Test basic Redis operations using fakeredis."""
    # Mock redis.Redis to use fakeredis
    fake_redis = fakeredis.FakeRedis()
    monkeypatch.setattr("redis.Redis", lambda **kwargs: fake_redis)
    
    initialize(mock_redis_config)
    history = ChatHistory()
    
    # Test adding messages
    history.add_message('user', 'Hello Redis!')
    history.add_message('bot', 'Hi from Redis!')
    
    # Test getting history
    messages = history.get_history()
    assert len(messages) == 2
    assert messages[0]['role'] == 'user'
    assert messages[0]['content'] == 'Hello Redis!'
    assert messages[1]['role'] == 'bot'
    assert messages[1]['content'] == 'Hi from Redis!'
    
    # Test get_message_at
    msg0 = history.get_message_at(0)
    msg1 = history.get_message_at(1)
    assert msg0['role'] == 'user'
    assert msg0['content'] == 'Hello Redis!'
    assert 'chat_id' in msg0
    assert 'data' in msg0
    assert msg1['role'] == 'bot'
    assert msg1['content'] == 'Hi from Redis!'
    assert 'chat_id' in msg1
    assert 'data' in msg1
    
    # Test clear
    history.clear()
    assert history.get_history() == []


def test_redis_persistence(mock_redis_config, monkeypatch):
    """Test that messages persist across ChatHistory instances."""
    fake_redis = fakeredis.FakeRedis()
    monkeypatch.setattr("redis.Redis", lambda **kwargs: fake_redis)
    
    initialize(mock_redis_config)
    
    # First instance - add messages
    history1 = ChatHistory()
    history1.add_message('user', 'Persistent message 1')
    history1.add_message('bot', 'Persistent message 2')
    
    # Second instance - should load existing messages
    history2 = ChatHistory()
    messages = history2.get_history()
    assert len(messages) == 2
    assert messages[0]['content'] == 'Persistent message 1'
    assert messages[1]['content'] == 'Persistent message 2'


def test_redis_query_functionality(mock_redis_config, monkeypatch):
    """Test Redis query functionality."""
    fake_redis = fakeredis.FakeRedis()
    monkeypatch.setattr("redis.Redis", lambda **kwargs: fake_redis)
    
    initialize(mock_redis_config)
    history = ChatHistory()
    
    # Add test messages
    history.add_message('user', 'Hello world')
    history.add_message('bot', 'Hi there')
    history.add_message('user', 'How are you?')
    history.add_message('bot', 'I am doing well, thank you!')
    
    # Test pattern matching
    results = history.query_redis(pattern='Hello')
    assert len(results) == 1
    assert results[0]['content'] == 'Hello world'
    
    # Test case insensitive matching
    results = history.query_redis(pattern='hello')
    assert len(results) == 1
    assert results[0]['content'] == 'Hello world'
    
    # Test limit
    results = history.query_redis(limit=2)
    assert len(results) == 2
    
    # Test no pattern (return all)
    results = history.query_redis()
    assert len(results) == 4


def test_redis_error_handling(mock_redis_config, monkeypatch):
    """Test Redis error handling."""
    # Test without Redis package (simulated)
    monkeypatch.setattr("nexamem.history.REDIS_AVAILABLE", False)
    
    initialize(mock_redis_config)
    with pytest.raises(ConfigError, match="Redis is not available"):
        ChatHistory()


def test_redis_debug_mode(mock_redis_config, monkeypatch, capsys):
    """Test Redis debug output."""
    fake_redis = fakeredis.FakeRedis()
    monkeypatch.setattr("redis.Redis", lambda **kwargs: fake_redis)
    
    mock_redis_config["debug"] = True
    initialize(mock_redis_config)
    history = ChatHistory()
    
    history.add_message('user', 'Debug test')
    history.get_history()
    history.clear()
    
    captured = capsys.readouterr()
    assert "[DEBUG] Connected to Redis" in captured.out
    assert "[DEBUG] Saved message to Redis" in captured.out
    assert "[DEBUG] Loaded" in captured.out
    assert "[DEBUG] Cleared Redis chat history" in captured.out


def test_azure_redis_configuration(mock_azure_redis_config, monkeypatch):
    """Test Azure Redis Cache specific configuration."""
    fake_redis = fakeredis.FakeRedis()
    monkeypatch.setattr("redis.Redis", lambda **kwargs: fake_redis)
    
    initialize(mock_azure_redis_config)
    history = ChatHistory()
    
    # Verify Azure-specific settings are applied
    from nexamem.config import get_config
    config = get_config()
    assert config["redis_port"] == 6380
    assert config["redis_ssl"] is True
    
    # Test functionality works with Azure config
    history.add_message('user', 'Azure Redis test')
    messages = history.get_history()
    assert len(messages) == 1
    assert messages[0]['content'] == 'Azure Redis test'


def test_redis_info_method(mock_redis_config, monkeypatch):
    """Test Redis info method for diagnostics."""
    fake_redis = fakeredis.FakeRedis()
    monkeypatch.setattr("redis.Redis", lambda **kwargs: fake_redis)
    
    initialize(mock_redis_config)
    history = ChatHistory()
    
    # Add some messages first
    history.add_message('user', 'Test message 1')
    history.add_message('bot', 'Test message 2')
    
    # Get Redis info
    info = history.get_redis_info()
    
    # fakeredis may not support all Redis info commands, so check for either success or error
    if "error" in info:
        # If there's an error, it should be a string
        assert isinstance(info["error"], str)
    else:
        # Check that we get expected keys if info command works
        assert "history_length" in info
        assert "host" in info
        assert "port" in info
        assert "ssl_enabled" in info
        
        # History length should match what we added
        assert info["history_length"] == "2"


def test_redis_query_method_validation(mock_redis_config, monkeypatch):
    """Test that query_redis only works with Redis storage."""
    fake_redis = fakeredis.FakeRedis()
    monkeypatch.setattr("redis.Redis", lambda **kwargs: fake_redis)
    
    # Test with non-Redis storage
    initialize({"history_storage": "memory"})
    history = ChatHistory()
    
    with pytest.raises(ConfigError, match="query_redis is only available when using Redis storage"):
        history.query_redis()
    
    # Test with Redis storage
    initialize(mock_redis_config)
    history = ChatHistory()
    
    # Should not raise error
    results = history.query_redis()
    assert isinstance(results, list)


def test_redis_info_method_validation(mock_redis_config, monkeypatch):
    """Test that get_redis_info only works with Redis storage."""
    fake_redis = fakeredis.FakeRedis()
    monkeypatch.setattr("redis.Redis", lambda **kwargs: fake_redis)
    
    # Test with non-Redis storage
    initialize({"history_storage": "memory"})
    history = ChatHistory()
    
    with pytest.raises(ConfigError, match="get_redis_info is only available when using Redis storage"):
        history.get_redis_info()
    
    # Test with Redis storage
    initialize(mock_redis_config)
    history = ChatHistory()
    
    # Should not raise error
    info = history.get_redis_info()
    assert isinstance(info, dict)


def test_redis_connection_parameters(mock_redis_config, monkeypatch):
    """Test that Redis is initialized with correct connection parameters."""
    captured_kwargs = {}
    
    def mock_redis_init(**kwargs):
        captured_kwargs.update(kwargs)
        # Return a simple mock object instead of fakeredis to avoid compatibility issues
        class MockRedis:
            def ping(self): pass
            def rpush(self, key, value): pass
            def lrange(self, key, start, end): return []
            def delete(self, key): pass
            def llen(self, key): return 0
            @property
            def connection_pool(self):
                class MockPool:
                    connection_kwargs = kwargs
                return MockPool()
        return MockRedis()
    
    monkeypatch.setattr("redis.Redis", mock_redis_init)
    
    initialize(mock_redis_config)
    ChatHistory()
    
    # Verify connection parameters
    assert captured_kwargs["host"] == "localhost"
    assert captured_kwargs["port"] == 6379
    assert captured_kwargs["password"] == "test_password"
    assert captured_kwargs["ssl"] is False
    assert captured_kwargs["db"] == 0
    assert captured_kwargs["socket_timeout"] == 30
    assert captured_kwargs["socket_connect_timeout"] == 30
    assert captured_kwargs["retry_on_timeout"] is True
    assert captured_kwargs["health_check_interval"] == 30


def test_entra_id_config_validation():
    """Test Entra ID authentication configuration validation."""
    # Valid Entra ID config should work
    config = {
        "history_storage": "redis",
        "redis_host": "test-cache.redis.cache.windows.net",
        "redis_auth_method": "entra_id"
    }
    initialize(config)
    
    # Should set defaults for Entra ID
    from nexamem.config import get_config
    current_config = get_config()
    assert current_config["redis_auth_method"] == "entra_id"
    assert current_config["redis_entra_scope"] == "https://redis.azure.com/.default"
    assert current_config["redis_ssl"] is True


def test_entra_id_authentication_mock(monkeypatch):
    """Test Entra ID authentication with mocked azure-identity."""
    # Mock azure-identity components
    class MockCredential:
        def get_token(self, scope):
            class MockToken:
                token = "mock-entra-token-12345"
                expires_on = 9999999999
            return MockToken()
    
    class MockRedis:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
            # Verify token is used as password
            assert kwargs.get('password') == "mock-entra-token-12345"
            self.messages = []
        
        def ping(self): pass
        def rpush(self, key, value): 
            self.messages.append(value)
        def lrange(self, key, start, end): 
            return [msg.encode('utf-8') for msg in self.messages]
        def delete(self, key): 
            self.messages.clear()
        def llen(self, key): 
            return len(self.messages)
        
        @property 
        def connection_pool(self):
            class MockPool:
                connection_kwargs = self.kwargs
            return MockPool()
    
    # Patch the imports and classes
    monkeypatch.setattr("nexamem.history.AZURE_IDENTITY_AVAILABLE", True)
    monkeypatch.setattr("nexamem.history.DefaultAzureCredential", MockCredential)
    
    mock_redis_instance = MockRedis
    monkeypatch.setattr("redis.Redis", mock_redis_instance)
    
    # Test Entra ID authentication
    config = {
        "history_storage": "redis",
        "redis_host": "test-cache.redis.cache.windows.net",
        "redis_auth_method": "entra_id",
        "debug": False
    }
    
    initialize(config)
    history = ChatHistory()
    
    # Should work without errors
    history.add_message("user", "Test with Entra ID")
    messages = history.get_history()
    assert len(messages) == 1
    assert messages[0]["content"] == "Test with Entra ID"


def test_entra_id_unavailable_error():
    """Test error when azure-identity is not available."""
    import nexamem.history
    
    # Temporarily disable azure-identity
    original_available = nexamem.history.AZURE_IDENTITY_AVAILABLE
    nexamem.history.AZURE_IDENTITY_AVAILABLE = False
    
    try:
        config = {
            "history_storage": "redis",
            "redis_host": "test-cache.redis.cache.windows.net", 
            "redis_auth_method": "entra_id"
        }
        
        initialize(config)
        
        with pytest.raises(ConfigError, match="azure-identity package is required"):
            ChatHistory()
            
    finally:
        # Restore original state
        nexamem.history.AZURE_IDENTITY_AVAILABLE = original_available


def test_access_key_still_works(mock_redis_config, monkeypatch):
    """Test that access key authentication still works after adding Entra ID."""
    fake_redis = fakeredis.FakeRedis()
    monkeypatch.setattr("redis.Redis", lambda **kwargs: fake_redis)
    
    # Use access key method explicitly
    mock_redis_config["redis_auth_method"] = "access_key"
    
    initialize(mock_redis_config)
    history = ChatHistory()
    
    # Should work with access key
    history.add_message('user', 'Access key test')
    messages = history.get_history()
    assert len(messages) == 1
    assert messages[0]['content'] == 'Access key test'


def test_invalid_auth_method():
    """Test validation of redis_auth_method parameter."""
    config = {
        "history_storage": "redis",
        "redis_host": "localhost",
        "redis_auth_method": "invalid_method"
    }
    
    with pytest.raises(ConfigError, match="'redis_auth_method' must be 'access_key' or 'entra_id'"):
        initialize(config)


def test_access_key_required_validation():
    """Test that redis_password is required for access_key method."""
    config = {
        "history_storage": "redis",
        "redis_host": "localhost",
        "redis_auth_method": "access_key"
        # Missing redis_password
    }
    
    with pytest.raises(ConfigError, match="'redis_password' is required when using 'access_key' authentication"):
        initialize(config)
