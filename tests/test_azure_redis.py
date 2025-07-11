"""
Tests for Azure Cache for Redis integration.
"""
import pytest
import json
from unittest.mock import MagicMock, patch
from nexamem.redis_adapter import RedisAdapter, AsyncRedisAdapter, AzureRedisConnectionHelper, RedisConnectionError
from nexamem.config import initialize, ConfigError
from nexamem.history import ChatHistory


class TestAzureRedisConnectionHelper:
    """Test Azure Redis connection helper utilities."""
    
    def test_azure_config_with_access_key(self):
        """Test Azure Redis configuration with access key."""
        config = AzureRedisConnectionHelper.get_azure_redis_config(
            hostname="test.redis.cache.windows.net",
            access_key="test_access_key"
        )
        
        assert config['host'] == "test.redis.cache.windows.net"
        assert config['port'] == 6380
        assert config['ssl'] is True
        assert config['password'] == "test_access_key"
        assert config['decode_responses'] is True

    @patch('nexamem.redis_adapter.DefaultAzureCredential')
    def test_azure_config_with_entra_id(self, mock_credential_class):
        """Test Azure Redis configuration with Entra ID."""
        # Mock credential and token
        mock_credential = MagicMock()
        mock_token = MagicMock()
        mock_token.token = "test_entra_token"
        mock_credential.get_token.return_value = mock_token
        mock_credential_class.return_value = mock_credential
        
        config = AzureRedisConnectionHelper.get_azure_redis_config(
            hostname="test.redis.cache.windows.net",
            use_entra_id=True,
            username="test_user"
        )
        
        assert config['host'] == "test.redis.cache.windows.net"
        assert config['username'] == "test_user"
        assert config['password'] == "test_entra_token"
        mock_credential.get_token.assert_called_once_with("https://redis.azure.com/.default")

    @patch('nexamem.redis_adapter.ClientSecretCredential')
    def test_azure_config_with_service_principal(self, mock_credential_class):
        """Test Azure Redis configuration with service principal."""
        mock_credential = MagicMock()
        mock_token = MagicMock()
        mock_token.token = "test_sp_token"
        mock_credential.get_token.return_value = mock_token
        mock_credential_class.return_value = mock_credential
        
        config = AzureRedisConnectionHelper.get_azure_redis_config(
            hostname="test.redis.cache.windows.net",
            use_entra_id=True,
            client_id="test_client_id",
            client_secret="test_client_secret",
            tenant_id="test_tenant_id"
        )
        
        assert config['host'] == "test.redis.cache.windows.net"
        assert config['username'] == "test_client_id"
        assert config['password'] == "test_sp_token"
        mock_credential_class.assert_called_once_with(
            tenant_id="test_tenant_id",
            client_id="test_client_id",
            client_secret="test_client_secret"
        )

    @patch('nexamem.redis_adapter.SecretClient')
    @patch('nexamem.redis_adapter.DefaultAzureCredential')
    def test_azure_config_with_keyvault(self, mock_credential_class, mock_secret_client_class):
        """Test Azure Redis configuration with Key Vault."""
        # Mock credential
        mock_credential = MagicMock()
        mock_credential_class.return_value = mock_credential
        
        # Mock secret client and secret
        mock_secret_client = MagicMock()
        mock_secret = MagicMock()
        mock_secret.value = "keyvault_redis_key"
        mock_secret_client.get_secret.return_value = mock_secret
        mock_secret_client_class.return_value = mock_secret_client
        
        config = AzureRedisConnectionHelper.get_azure_redis_config(
            hostname="test.redis.cache.windows.net",
            keyvault_url="https://test-kv.vault.azure.net/",
            secret_name="redis-access-key"
        )
        
        assert config['host'] == "test.redis.cache.windows.net"
        assert config['password'] == "keyvault_redis_key"
        mock_secret_client_class.assert_called_once_with(
            vault_url="https://test-kv.vault.azure.net/",
            credential=mock_credential
        )
        mock_secret_client.get_secret.assert_called_once_with("redis-access-key")

    def test_azure_config_no_auth_raises_error(self):
        """Test that Azure config without auth raises error."""
        with pytest.raises(ValueError, match="Must provide either access_key"):
            AzureRedisConnectionHelper.get_azure_redis_config(
                hostname="test.redis.cache.windows.net"
            )

    def test_create_connection_string(self):
        """Test Azure Redis connection string creation."""
        conn_str = AzureRedisConnectionHelper.create_azure_connection_string(
            hostname="test.redis.cache.windows.net",
            access_key="test_key",
            ssl=True,
            port=6380
        )
        
        expected = "rediss://:test_key@test.redis.cache.windows.net:6380"
        assert conn_str == expected

    def test_create_connection_string_no_key_raises_error(self):
        """Test connection string creation without key raises error."""
        with pytest.raises(ValueError, match="Access key required"):
            AzureRedisConnectionHelper.create_azure_connection_string(
                hostname="test.redis.cache.windows.net"
            )


class TestRedisAdapterAzure:
    """Test RedisAdapter with Azure configurations."""
    
    def test_redis_adapter_with_fakeredis(self):
        """Test Redis adapter with fakeredis for testing."""
        adapter = RedisAdapter(use_fakeredis=True)
        
        assert adapter.use_fakeredis is True
        assert adapter.is_azure is False
        assert adapter.ping() is True
        
        info = adapter.get_info()
        assert info['use_fakeredis'] is True
        assert info['is_azure'] is False

    @patch('nexamem.redis_adapter.redis.Redis')
    @patch.object(AzureRedisConnectionHelper, 'get_azure_redis_config')
    def test_redis_adapter_with_azure_access_key(self, mock_get_config, mock_redis_class):
        """Test Redis adapter with Azure access key."""
        # Mock Azure config
        mock_get_config.return_value = {
            'host': 'test.redis.cache.windows.net',
            'port': 6380,
            'password': 'test_key',
            'ssl': True,
            'ssl_cert_reqs': None,
            'decode_responses': True
        }
        
        # Mock Redis client
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_redis_class.return_value = mock_client
        
        adapter = RedisAdapter(
            azure_hostname="test.redis.cache.windows.net",
            azure_access_key="test_key"
        )
        
        assert adapter.is_azure is True
        assert adapter.host == "test.redis.cache.windows.net"
        assert adapter.port == 6380
        assert adapter.ssl is True
        
        mock_get_config.assert_called_once()
        mock_redis_class.assert_called_once()

    @patch('nexamem.redis_adapter.redis.Redis')
    @patch.object(AzureRedisConnectionHelper, 'get_azure_redis_config')
    def test_redis_adapter_with_azure_entra_id(self, mock_get_config, mock_redis_class):
        """Test Redis adapter with Azure Entra ID."""
        # Mock Azure config
        mock_get_config.return_value = {
            'host': 'test.redis.cache.windows.net',
            'port': 6380,
            'password': 'entra_token',
            'ssl': True,
            'ssl_cert_reqs': None,
            'username': 'test_user',
            'decode_responses': True
        }
        
        # Mock Redis client
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_redis_class.return_value = mock_client
        
        adapter = RedisAdapter(
            azure_hostname="test.redis.cache.windows.net",
            use_azure_entra_id=True,
            azure_username="test_user"
        )
        
        assert adapter.is_azure is True
        mock_get_config.assert_called_once_with(
            hostname="test.redis.cache.windows.net",
            access_key=None,
            use_entra_id=True,
            username="test_user",
            client_id=None,
            client_secret=None,
            tenant_id=None,
            keyvault_url=None,
            secret_name=None
        )

    @patch('nexamem.redis_adapter.redis.Redis')
    def test_redis_adapter_connection_failure(self, mock_redis_class):
        """Test Redis adapter connection failure."""
        mock_client = MagicMock()
        mock_client.ping.side_effect = Exception("Connection failed")
        mock_redis_class.return_value = mock_client
        
        with pytest.raises(RedisConnectionError, match="Failed to connect to Redis"):
            RedisAdapter(host="invalid_host")


class TestAsyncRedisAdapterAzure:
    """Test AsyncRedisAdapter with Azure configurations."""
    
    @patch('nexamem.redis_adapter.redis_async.Redis')
    @patch.object(AzureRedisConnectionHelper, 'get_azure_redis_config')
    def test_async_redis_adapter_with_azure(self, mock_get_config, mock_redis_class):
        """Test async Redis adapter with Azure configuration."""
        # Mock Azure config
        mock_get_config.return_value = {
            'host': 'test.redis.cache.windows.net',
            'port': 6380,
            'password': 'test_key',
            'ssl': True,
            'ssl_cert_reqs': None,
            'decode_responses': True
        }
        
        # Mock async Redis client
        mock_client = MagicMock()
        mock_redis_class.return_value = mock_client
        
        adapter = AsyncRedisAdapter(
            azure_hostname="test.redis.cache.windows.net",
            azure_access_key="test_key"
        )
        
        assert adapter.is_azure is True
        assert adapter.host == "test.redis.cache.windows.net"
        
        info = adapter.get_info()
        assert info['is_azure'] is True
        assert info['async'] is True


class TestChatHistoryRedis:
    """Test ChatHistory with Redis storage."""
    
    def test_config_validation_redis_missing_config(self):
        """Test that Redis storage requires redis_config."""
        with pytest.raises(ConfigError, match="'redis_config' is required"):
            initialize({"history_storage": "redis"})

    def test_config_validation_redis_invalid_config(self):
        """Test that Redis config must be a dictionary."""
        with pytest.raises(ConfigError, match="'redis_config' must be a dictionary"):
            initialize({
                "history_storage": "redis",
                "redis_config": "invalid"
            })

    def test_config_validation_azure_redis_no_auth(self):
        """Test that Azure Redis requires authentication config."""
        with pytest.raises(ConfigError, match="For Azure Redis, must provide either"):
            initialize({
                "history_storage": "redis",
                "redis_config": {
                    "azure_hostname": "test.redis.cache.windows.net"
                }
            })

    def test_config_validation_azure_redis_with_access_key(self):
        """Test valid Azure Redis config with access key."""
        config = {
            "history_storage": "redis",
            "redis_config": {
                "azure_hostname": "test.redis.cache.windows.net",
                "azure_access_key": "test_key"
            }
        }
        initialize(config)  # Should not raise

    def test_config_validation_azure_redis_with_entra_id(self):
        """Test valid Azure Redis config with Entra ID."""
        config = {
            "history_storage": "redis",
            "redis_config": {
                "azure_hostname": "test.redis.cache.windows.net",
                "use_azure_entra_id": True
            }
        }
        initialize(config)  # Should not raise

    def test_config_validation_azure_redis_with_keyvault(self):
        """Test valid Azure Redis config with Key Vault."""
        config = {
            "history_storage": "redis",
            "redis_config": {
                "azure_hostname": "test.redis.cache.windows.net",
                "azure_keyvault_url": "https://test-kv.vault.azure.net/",
                "azure_secret_name": "redis-key"
            }
        }
        initialize(config)  # Should not raise

    def test_config_validation_standard_redis_no_host(self):
        """Test that standard Redis requires host."""
        with pytest.raises(ConfigError, match="Redis 'host' or 'hostname' is required"):
            initialize({
                "history_storage": "redis",
                "redis_config": {
                    "port": 6379
                }
            })

    def test_config_validation_standard_redis_with_host(self):
        """Test valid standard Redis config."""
        config = {
            "history_storage": "redis",
            "redis_config": {
                "host": "localhost",
                "use_fakeredis": True  # For testing
            }
        }
        initialize(config)  # Should not raise

    @patch('nexamem.history.RedisAdapter')
    def test_chat_history_redis_initialization(self, mock_redis_adapter):
        """Test ChatHistory initialization with Redis."""
        mock_adapter = MagicMock()
        mock_adapter.get_info.return_value = {"connected": True}
        mock_redis_adapter.return_value = mock_adapter
        
        config = {
            "history_storage": "redis",
            "redis_config": {
                "host": "localhost",
                "use_fakeredis": True
            }
        }
        initialize(config)
        
        history = ChatHistory()
        assert history._storage == "redis"
        mock_redis_adapter.assert_called_once()

    @patch('nexamem.history.RedisAdapter')
    def test_chat_history_redis_add_and_get_messages(self, mock_redis_adapter):
        """Test adding and retrieving messages with Redis storage."""
        mock_adapter = MagicMock()
        mock_adapter.get_info.return_value = {"connected": True}
        mock_redis_adapter.return_value = mock_adapter
        
        config = {
            "history_storage": "redis",
            "redis_config": {
                "host": "localhost",
                "use_fakeredis": True
            }
        }
        initialize(config)
        
        history = ChatHistory()
        history.set_session_context(
            agent_id="test_agent",
            user_id="test_user",
            env="test"
        )
        
        # Add messages
        history.add_user_message("Hello", tokens=3)
        history.add_assistant_message("Hi there!", tokens=5)
        
        # Verify messages were saved to Redis
        assert mock_adapter.client.setex.call_count == 2
        assert mock_adapter.client.zadd.call_count == 2

    @patch('nexamem.history.RedisAdapter')
    def test_chat_history_redis_query(self, mock_redis_adapter):
        """Test Redis query functionality."""
        mock_adapter = MagicMock()
        mock_adapter.get_info.return_value = {"connected": True}
        mock_adapter.client.keys.return_value = ["nexamem:chat_history:key1"]
        mock_adapter.client.get.return_value = json.dumps({
            "role": "user",
            "content": "test message",
            "timestamp": "2025-01-01T00:00:00"
        })
        mock_redis_adapter.return_value = mock_adapter
        
        config = {
            "history_storage": "redis",
            "redis_config": {
                "host": "localhost",
                "use_fakeredis": True
            }
        }
        initialize(config)
        
        history = ChatHistory()
        results = history.query_redis("*")
        
        assert len(results) == 1
        assert results[0]["content"] == "test message"
        mock_adapter.client.keys.assert_called_once()

    def test_chat_history_redis_query_wrong_storage(self):
        """Test Redis query with non-Redis storage raises error."""
        initialize({"history_storage": "memory"})
        history = ChatHistory()
        
        with pytest.raises(ConfigError, match="query_redis is only available when using Redis"):
            history.query_redis("*")


class TestIntegrationAzureRedis:
    """Integration tests for Azure Redis functionality."""
    
    def test_azure_redis_with_fakeredis_integration(self):
        """Test full integration with fakeredis simulating Azure Redis."""
        config = {
            "history_storage": "redis",
            "redis_config": {
                "azure_hostname": "test.redis.cache.windows.net",
                "azure_access_key": "test_key",
                "use_fakeredis": True  # Override for testing
            }
        }
        initialize(config)
        
        history = ChatHistory()
        history.set_session_context(
            agent_id="investment_advisor",
            user_id="customer_789",
            env="prod"
        )
        
        # Add messages
        history.add_user_message("What's my portfolio performance?", tokens=8)
        history.add_assistant_message("Your portfolio gained 12% this year.", tokens=14)
        history.add_system_message("Analysis completed", tokens=0)
        
        # Verify messages
        messages = history.get_history()
        assert len(messages) == 3
        
        expected_properties = [
            'role', 'content', 'agent_id', 'user_id', 'session_id',
            'env', 'timestamp', 'tokens', 'data'
        ]
        
        for msg in messages:
            for prop in expected_properties:
                assert prop in msg, f"Missing property: {prop}"
            
            assert msg['agent_id'] == "investment_advisor"
            assert msg['user_id'] == "customer_789"
            assert msg['env'] == "prod"
        
        # Test clear
        history.clear()
        messages_after_clear = history.get_history()
        assert len(messages_after_clear) == 0

    def test_standard_redis_with_fakeredis_integration(self):
        """Test full integration with standard Redis using fakeredis."""
        config = {
            "history_storage": "redis",
            "redis_config": {
                "host": "localhost",
                "port": 6379,
                "use_fakeredis": True
            }
        }
        initialize(config)
        
        history = ChatHistory()
        history.set_session_context(agent_id="test_agent", user_id="test_user")
        
        # Add and verify messages
        history.add_user_message("Test message", tokens=5)
        messages = history.get_history()
        
        assert len(messages) == 1
        assert messages[0]['content'] == "Test message"
        assert messages[0]['tokens'] == 5


if __name__ == "__main__":
    pytest.main([__file__])
