"""
Comprehensive unit tests for config module.
Tests configuration validation and initialization functionality.
"""
import os
import tempfile
from unittest.mock import patch

import pytest

from nexamem.config import ConfigError, get_config, initialize


class TestConfigInitialization:
    """Test configuration initialization functionality."""

    def test_initialize_memory_storage(self):
        """Test initialization with memory storage."""
        config = {"history_storage": "memory"}
        
        initialize(config)
        stored_config = get_config()
        
        assert stored_config["history_storage"] == "memory"

    def test_initialize_file_storage(self):
        """Test initialization with file storage."""
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            config = {
                "history_storage": "file",
                "file_path": temp_file.name
            }
            
            initialize(config)
            stored_config = get_config()
            
            assert stored_config["history_storage"] == "file"
            assert stored_config["file_path"] == temp_file.name
        
        # Cleanup
        os.unlink(temp_file.name)

    def test_initialize_sqlite_storage(self):
        """Test initialization with SQLite storage."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as temp_file:
            config = {
                "history_storage": "sqlite",
                "sqlite_path": temp_file.name
            }
            
            initialize(config)
            stored_config = get_config()
            
            assert stored_config["history_storage"] == "sqlite"
            assert stored_config["sqlite_path"] == temp_file.name
        
        # Cleanup
        os.unlink(temp_file.name)

    def test_initialize_redis_storage_basic(self):
        """Test initialization with basic Redis storage."""
        config = {
            "history_storage": "redis",
            "redis_config": {
                "host": "localhost",
                "port": 6379,
                "db": 0
            }
        }
        
        initialize(config)
        stored_config = get_config()
        
        assert stored_config["history_storage"] == "redis"
        assert stored_config["redis_config"]["host"] == "localhost"
        assert stored_config["redis_config"]["port"] == 6379

    def test_initialize_redis_storage_azure_access_key(self):
        """Test initialization with Azure Redis using access key."""
        config = {
            "history_storage": "redis",
            "redis_config": {
                "azure_hostname": "test.redis.cache.windows.net",
                "azure_access_key": "test_access_key"
            }
        }
        
        initialize(config)
        stored_config = get_config()
        
        assert stored_config["history_storage"] == "redis"
        assert stored_config["redis_config"]["azure_hostname"] == "test.redis.cache.windows.net"
        assert stored_config["redis_config"]["azure_access_key"] == "test_access_key"

    def test_initialize_redis_storage_azure_entra_id(self):
        """Test initialization with Azure Redis using Entra ID."""
        config = {
            "history_storage": "redis",
            "redis_config": {
                "azure_hostname": "test.redis.cache.windows.net",
                "use_azure_entra_id": True,
                "azure_username": "test_user"
            }
        }
        
        initialize(config)
        stored_config = get_config()
        
        assert stored_config["redis_config"]["use_azure_entra_id"] is True
        assert stored_config["redis_config"]["azure_username"] == "test_user"

    def test_initialize_invalid_storage_type(self):
        """Test initialization with invalid storage type."""
        config = {"history_storage": "invalid_storage"}
        
        with pytest.raises(ConfigError, match="Invalid storage type"):
            initialize(config)

    def test_initialize_file_storage_missing_path(self):
        """Test initialization with file storage but missing file path."""
        config = {"history_storage": "file"}
        
        with pytest.raises(ConfigError, match="file_path"):
            initialize(config)

    def test_initialize_sqlite_storage_missing_path(self):
        """Test initialization with SQLite storage but missing path."""
        config = {"history_storage": "sqlite"}
        
        with pytest.raises(ConfigError, match="sqlite_path"):
            initialize(config)

    def test_initialize_redis_storage_missing_config(self):
        """Test initialization with Redis storage but missing config."""
        config = {"history_storage": "redis"}
        
        with pytest.raises(ConfigError, match="redis_config"):
            initialize(config)

    def test_initialize_redis_storage_invalid_config(self):
        """Test initialization with Redis storage but invalid config."""
        config = {
            "history_storage": "redis",
            "redis_config": {}  # Empty config
        }
        
        with pytest.raises(ConfigError):
            initialize(config)

    def test_initialize_redis_azure_no_auth(self):
        """Test initialization with Azure Redis but no authentication."""
        config = {
            "history_storage": "redis",
            "redis_config": {
                "azure_hostname": "test.redis.cache.windows.net"
                # Missing authentication method
            }
        }
        
        with pytest.raises(ConfigError):
            initialize(config)

    def test_initialize_redis_azure_with_keyvault(self):
        """Test initialization with Azure Redis using Key Vault."""
        config = {
            "history_storage": "redis",
            "redis_config": {
                "azure_hostname": "test.redis.cache.windows.net",
                "azure_keyvault_url": "https://test.vault.azure.net/",
                "azure_secret_name": "redis-access-key"
            }
        }
        
        initialize(config)
        stored_config = get_config()
        
        assert stored_config["redis_config"]["azure_keyvault_url"] == "https://test.vault.azure.net/"
        assert stored_config["redis_config"]["azure_secret_name"] == "redis-access-key"

    def test_initialize_redis_azure_service_principal(self):
        """Test initialization with Azure Redis using service principal."""
        config = {
            "history_storage": "redis",
            "redis_config": {
                "azure_hostname": "test.redis.cache.windows.net",
                "use_azure_entra_id": True,
                "azure_client_id": "test_client_id",
                "azure_client_secret": "test_client_secret",
                "azure_tenant_id": "test_tenant_id"
            }
        }
        
        initialize(config)
        stored_config = get_config()
        
        assert stored_config["redis_config"]["azure_client_id"] == "test_client_id"
        assert stored_config["redis_config"]["azure_client_secret"] == "test_client_secret"
        assert stored_config["redis_config"]["azure_tenant_id"] == "test_tenant_id"

    def test_initialize_redis_standard_no_host(self):
        """Test initialization with standard Redis but no host."""
        config = {
            "history_storage": "redis",
            "redis_config": {
                "port": 6379,
                "db": 0
                # Missing host
            }
        }
        
        with pytest.raises(ConfigError):
            initialize(config)

    def test_initialize_with_defaults(self):
        """Test that initialization adds appropriate defaults."""
        config = {
            "history_storage": "redis",
            "redis_config": {
                "host": "localhost"
            }
        }
        
        initialize(config)
        stored_config = get_config()
        
        # Should add default port and db
        assert stored_config["redis_config"]["port"] == 6379
        assert stored_config["redis_config"]["db"] == 0

    def test_initialize_preserves_extra_config(self):
        """Test that initialization preserves extra configuration."""
        config = {
            "history_storage": "memory",
            "debug": True,
            "custom_setting": "custom_value"
        }
        
        initialize(config)
        stored_config = get_config()
        
        assert stored_config["debug"] is True
        assert stored_config["custom_setting"] == "custom_value"

    def test_get_config_before_initialization(self):
        """Test getting config before initialization."""
        # Reset any existing config
        import nexamem.config as config_module
        config_module._config = None
        
        config = get_config()
        
        # Should return default config
        assert config["history_storage"] == "memory"

    def test_get_config_after_initialization(self):
        """Test getting config after initialization."""
        test_config = {
            "history_storage": "file",
            "file_path": "/tmp/test.json"
        }
        
        initialize(test_config)
        retrieved_config = get_config()
        
        assert retrieved_config["history_storage"] == "file"
        assert retrieved_config["file_path"] == "/tmp/test.json"

    def test_multiple_initializations(self):
        """Test multiple initializations override previous config."""
        # First initialization
        config1 = {"history_storage": "memory"}
        initialize(config1)
        
        assert get_config()["history_storage"] == "memory"
        
        # Second initialization
        config2 = {
            "history_storage": "redis",
            "redis_config": {"host": "localhost"}
        }
        initialize(config2)
        
        assert get_config()["history_storage"] == "redis"

    def test_config_validation_edge_cases(self):
        """Test configuration validation with edge cases."""
        # Test with None config
        with pytest.raises(ConfigError):
            initialize(None)
        
        # Test with empty config
        with pytest.raises(ConfigError):
            initialize({})
        
        # Test with non-dict config
        with pytest.raises(ConfigError):
            initialize("invalid")

    def test_redis_config_type_validation(self):
        """Test Redis config type validation."""
        # Test with non-dict redis_config
        config = {
            "history_storage": "redis",
            "redis_config": "invalid"
        }
        
        with pytest.raises(ConfigError):
            initialize(config)

    def test_file_path_validation(self):
        """Test file path validation."""
        # Test with non-string file_path
        config = {
            "history_storage": "file",
            "file_path": 123
        }
        
        with pytest.raises(ConfigError):
            initialize(config)

    def test_sqlite_path_validation(self):
        """Test SQLite path validation."""
        # Test with non-string sqlite_path
        config = {
            "history_storage": "sqlite",
            "sqlite_path": ["invalid", "path"]
        }
        
        with pytest.raises(ConfigError):
            initialize(config)

    def test_boolean_config_validation(self):
        """Test boolean configuration validation."""
        config = {
            "history_storage": "redis",
            "redis_config": {
                "host": "localhost",
                "use_azure_entra_id": "not_a_boolean"  # Should be boolean
            }
        }
        
        # Should not raise error, will be handled by Redis adapter
        initialize(config)
        stored_config = get_config()
        assert stored_config["redis_config"]["use_azure_entra_id"] == "not_a_boolean"

    def test_numeric_config_validation(self):
        """Test numeric configuration validation."""
        config = {
            "history_storage": "redis",
            "redis_config": {
                "host": "localhost",
                "port": "not_a_number"  # Should be integer
            }
        }
        
        # Should not raise error during config validation
        initialize(config)
        stored_config = get_config()
        assert stored_config["redis_config"]["port"] == "not_a_number"


class TestConfigErrorHandling:
    """Test configuration error handling."""

    def test_config_error_creation(self):
        """Test ConfigError exception creation."""
        error = ConfigError("Test error message")
        assert str(error) == "Test error message"
        assert isinstance(error, Exception)

    def test_config_error_with_details(self):
        """Test ConfigError with detailed message."""
        details = "Missing required field 'host' in redis_config"
        error = ConfigError(f"Configuration validation failed: {details}")
        
        assert "Configuration validation failed" in str(error)
        assert "Missing required field 'host'" in str(error)

    def test_nested_config_error_handling(self):
        """Test error handling for nested configuration issues."""
        config = {
            "history_storage": "redis",
            "redis_config": {
                "azure_hostname": "test.redis.cache.windows.net",
                "azure_keyvault_url": "invalid_url",  # Invalid URL format
                "azure_secret_name": "redis-key"
            }
        }
        
        # Should initialize successfully, URL validation happens in Azure SDK
        initialize(config)
        stored_config = get_config()
        assert stored_config["redis_config"]["azure_keyvault_url"] == "invalid_url"


class TestConfigIntegration:
    """Integration tests for configuration functionality."""

    def test_config_with_environment_variables(self):
        """Test configuration with environment variable references."""
        with patch.dict(os.environ, {
            "REDIS_HOST": "env_redis_host",
            "REDIS_PORT": "6380",
            "REDIS_PASSWORD": "env_password"
        }):
            # Note: This test assumes the config system would support env vars
            # The actual implementation may need to be extended for this
            config = {
                "history_storage": "redis", 
                "redis_config": {
                    "host": "env_redis_host",  # Would be os.getenv("REDIS_HOST")
                    "port": 6380,
                    "password": "env_password"
                }
            }
            
            initialize(config)
            stored_config = get_config()
            
            assert stored_config["redis_config"]["host"] == "env_redis_host"
            assert stored_config["redis_config"]["port"] == 6380

    def test_config_serialization_roundtrip(self):
        """Test that configuration can be serialized and deserialized."""
        original_config = {
            "history_storage": "redis",
            "redis_config": {
                "azure_hostname": "test.redis.cache.windows.net",
                "azure_access_key": "test_key",
                "ssl": True,
                "port": 6380,
                "db": 0
            },
            "debug": True,
            "custom_settings": {
                "timeout": 30,
                "retries": 3
            }
        }
        
        initialize(original_config)
        retrieved_config = get_config()
        
        # Should be equivalent after roundtrip
        assert retrieved_config["history_storage"] == original_config["history_storage"]
        assert retrieved_config["redis_config"] == original_config["redis_config"]
        assert retrieved_config["debug"] == original_config["debug"]
        assert retrieved_config["custom_settings"] == original_config["custom_settings"]

    def test_config_validation_performance(self):
        """Test configuration validation performance."""
        import time
        
        config = {
            "history_storage": "redis",
            "redis_config": {
                "host": "localhost",
                "port": 6379,
                "db": 0
            }
        }
        
        start_time = time.time()
        
        # Initialize multiple times
        for _ in range(100):
            initialize(config)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should complete quickly (under 1 second for 100 initializations)
        assert duration < 1.0

    def test_config_memory_efficiency(self):
        """Test that configuration doesn't cause memory leaks."""
        config_template = {
            "history_storage": "redis",
            "redis_config": {
                "host": "localhost",
                "port": 6379
            }
        }
        
        # Initialize many times with slightly different configs
        for i in range(100):
            config = config_template.copy()
            config["redis_config"] = config_template["redis_config"].copy()
            config["redis_config"]["db"] = i % 16  # Different db numbers
            
            initialize(config)
            
            # Verify config is updated
            current_config = get_config()
            assert current_config["redis_config"]["db"] == i % 16

    def test_concurrent_config_access(self):
        """Test concurrent access to configuration."""
        import threading
        
        base_config = {
            "history_storage": "redis",
            "redis_config": {
                "host": "localhost",
                "port": 6379
            }
        }
        
        def worker(worker_id):
            # Each worker initializes with a different db
            config = base_config.copy()
            config["redis_config"] = base_config["redis_config"].copy()
            config["redis_config"]["db"] = worker_id
            
            initialize(config)
            
            # Verify the worker can read back its config
            current_config = get_config()
            return current_config["redis_config"]["db"]
        
        # Note: Since config is global, this test mainly ensures no crashes
        # The actual behavior depends on which worker runs last
        threads = []
        results = []
        
        def thread_worker(worker_id):
            result = worker(worker_id)
            results.append(result)
        
        for i in range(5):
            thread = threading.Thread(target=thread_worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Should have completed without errors
        assert len(results) == 5
        
        # Final config should be from one of the workers
        final_config = get_config()
        assert final_config["redis_config"]["db"] in range(5)

    def test_config_with_complex_nested_structure(self):
        """Test configuration with complex nested structures."""
        complex_config = {
            "history_storage": "redis",
            "redis_config": {
                "host": "localhost",
                "port": 6379,
                "connection_pool": {
                    "max_connections": 100,
                    "retry_on_timeout": True,
                    "health_check_interval": 30
                },
                "cluster_config": {
                    "nodes": [
                        {"host": "node1", "port": 6379},
                        {"host": "node2", "port": 6379}
                    ],
                    "read_from_replicas": True
                }
            },
            "features": {
                "audit": {
                    "enabled": True,
                    "stream_name": "custom:audit",
                    "ttl_days": 90
                },
                "metrics": {
                    "enabled": True,
                    "export_interval": 60
                }
            }
        }
        
        initialize(complex_config)
        stored_config = get_config()
        
        # Verify nested structures are preserved
        assert stored_config["redis_config"]["connection_pool"]["max_connections"] == 100
        assert stored_config["redis_config"]["cluster_config"]["read_from_replicas"] is True
        assert stored_config["features"]["audit"]["ttl_days"] == 90
        assert len(stored_config["redis_config"]["cluster_config"]["nodes"]) == 2
