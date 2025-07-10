"""
Tests for enum configuration functionality.
"""
import pytest
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from nexamem import initialize, ChatHistory, StorageType, RedisAuthMethod
from nexamem.config import ConfigError


class TestEnumConfiguration:
    """Test enum-based configuration functionality."""
    
    def test_storage_type_enum_values(self):
        """Test StorageType enum values."""
        assert StorageType.MEMORY.value == "memory"
        assert StorageType.FILE.value == "file"
        assert StorageType.SQLITE.value == "sqlite"
        assert StorageType.REDIS.value == "redis"
    
    def test_redis_auth_method_enum_values(self):
        """Test RedisAuthMethod enum values."""
        assert RedisAuthMethod.ACCESS_KEY.value == "access_key"
        assert RedisAuthMethod.ENTRA_ID.value == "entra_id"
        assert RedisAuthMethod.AZURE_AD.value == "entra_id"  # Alias
    
    def test_memory_storage_with_enum(self):
        """Test memory storage configuration using enum."""
        config = {
            "history_storage": StorageType.MEMORY,
            "debug": True
        }
        initialize(config)
        history = ChatHistory()
        history.add_message("user", "Test message")
        assert len(history.get_history()) == 1
    
    def test_file_storage_with_enum(self, tmp_path):
        """Test file storage configuration using enum."""
        file_path = tmp_path / "test_enum.json"
        config = {
            "history_storage": StorageType.FILE,
            "file_path": str(file_path),
            "debug": False
        }
        initialize(config)
        history = ChatHistory()
        history.add_message("user", "Enum test")
        assert len(history.get_history()) == 1
        assert file_path.exists()
    
    def test_sqlite_storage_with_enum(self, tmp_path):
        """Test SQLite storage configuration using enum."""
        sqlite_path = tmp_path / "test_enum.db"
        config = {
            "history_storage": StorageType.SQLITE,
            "sqlite_path": str(sqlite_path),
            "debug": False
        }
        initialize(config)
        history = ChatHistory()
        history.add_message("user", "SQLite enum test")
        assert len(history.get_history()) == 1
        assert sqlite_path.exists()
    
    def test_redis_access_key_enum_config(self):
        """Test Redis access key configuration with enum (without actual Redis)."""
        config = {
            "history_storage": StorageType.REDIS,
            "redis_host": "localhost",
            "redis_port": 6379,
            "redis_password": "test-password",
            "redis_ssl": False,
            "redis_auth_method": RedisAuthMethod.ACCESS_KEY,
            "debug": False
        }
        # This should validate without error (even though Redis connection will fail)
        initialize(config)
    
    def test_redis_entra_id_enum_config(self):
        """Test Redis Entra ID configuration with enum (without actual Redis)."""
        config = {
            "history_storage": StorageType.REDIS,
            "redis_host": "test-cache.redis.cache.windows.net",
            "redis_port": 6380,
            "redis_ssl": True,
            "redis_auth_method": RedisAuthMethod.ENTRA_ID,
            "redis_entra_scope": "https://redis.azure.com/.default",
            "debug": False
        }
        # This should validate without error (even though Redis connection will fail)
        initialize(config)
    
    def test_azure_ad_alias_enum(self):
        """Test that AZURE_AD enum alias works."""
        config = {
            "history_storage": StorageType.REDIS,
            "redis_host": "test-cache.redis.cache.windows.net",
            "redis_port": 6380,
            "redis_ssl": True,
            "redis_auth_method": RedisAuthMethod.AZURE_AD,  # Using alias
            "debug": False
        }
        # This should validate without error
        initialize(config)
    
    def test_backward_compatibility_strings(self):
        """Test that string values still work for backward compatibility."""
        config = {
            "history_storage": "memory",  # String, not enum
            "debug": False
        }
        initialize(config)
        history = ChatHistory()
        history.add_message("user", "Backward compatibility test")
        assert len(history.get_history()) == 1
    
    def test_mixed_enum_and_string_config(self):
        """Test mixing enum and string values in same config."""
        config = {
            "history_storage": StorageType.REDIS,  # Enum
            "redis_host": "localhost",
            "redis_port": 6379,
            "redis_password": "test",
            "redis_ssl": False,
            "redis_auth_method": "access_key",  # String, not enum
            "debug": False
        }
        # Should work fine
        initialize(config)
    
    def test_invalid_enum_storage_type(self):
        """Test that invalid storage type raises error."""
        config = {
            "history_storage": "invalid_storage",
            "debug": False
        }
        with pytest.raises(ConfigError):
            initialize(config)
    
    def test_invalid_enum_auth_method(self):
        """Test that invalid auth method raises error."""
        config = {
            "history_storage": StorageType.REDIS,
            "redis_host": "localhost",
            "redis_password": "test",
            "redis_auth_method": "invalid_auth",
            "debug": False
        }
        with pytest.raises(ConfigError):
            initialize(config)
    
    def test_enum_in_exports(self):
        """Test that enums are properly exported."""
        from nexamem import StorageType, RedisAuthMethod
        
        # Should be able to import without error
        assert StorageType.MEMORY is not None
        assert RedisAuthMethod.ACCESS_KEY is not None


class TestEnumIntegration:
    """Integration tests for enum functionality."""
    
    def test_enum_config_creates_working_history(self):
        """Test that enum config creates a working ChatHistory instance."""
        config = {
            "history_storage": StorageType.MEMORY,
            "debug": True
        }
        initialize(config)
        
        history = ChatHistory()
        
        # Add some messages
        history.add_message("user", "Hello")
        history.add_message("assistant", "Hi there!")
        history.add_message("user", "How are you?")
        
        # Verify they're stored correctly
        messages = history.get_history()
        assert len(messages) == 3
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "Hello"
        assert messages[1]["role"] == "assistant"
        assert messages[2]["content"] == "How are you?"
        
        # Test get_message_at
        first_msg = history.get_message_at(0)
        assert first_msg["content"] == "Hello"
    
    def test_file_storage_enum_persistence(self, tmp_path):
        """Test that enum-configured file storage persists correctly."""
        file_path = tmp_path / "enum_persistence.json"
        
        config = {
            "history_storage": StorageType.FILE,
            "file_path": str(file_path),
            "debug": False
        }
        
        # Create first history instance and add message
        initialize(config)
        history1 = ChatHistory()
        history1.add_message("user", "Persistent message")
        
        # Create second history instance (should load from file)
        history2 = ChatHistory()
        messages = history2.get_history()
        
        assert len(messages) == 1
        assert messages[0]["content"] == "Persistent message"
