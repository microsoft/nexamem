"""Tests for configuration models."""

import pytest
from pydantic import ValidationError

from nexamem.config.aimemory import AIMemoryConfig
from nexamem.config.storage import (
    AzureRedisConfig,
    FileConfig,
    MemoryConfig,
    SQLiteConfig,
    StorageConfig,
)


class TestStorageConfigs:
    """Test storage configuration models."""

    def test_memory_config(self):
        """Test memory configuration."""
        config = MemoryConfig()
        assert config.max_size is None
        assert config.cleanup_interval == 300

    def test_memory_config_validation(self):
        """Test memory configuration validation."""
        # Should accept empty config
        config = MemoryConfig()
        assert config.cleanup_interval == 300

    def test_file_config(self):
        """Test file configuration."""
        config = FileConfig(path="./test_data")
        assert config.path == "./test_data"
        assert config.encoding == "utf-8"

    def test_file_config_defaults(self):
        """Test file configuration defaults."""
        config = FileConfig(path="./test_data")
        assert config.encoding == "utf-8"
        assert config.backup_count == 0

    def test_sqlite_config(self):
        """Test SQLite configuration."""
        config = SQLiteConfig(path="./test.db")
        assert config.path == "./test.db"
        assert config.timeout == 30.0

    def test_sqlite_config_defaults(self):
        """Test SQLite configuration defaults."""
        config = SQLiteConfig(path="./test.db")
        assert config.timeout == 30.0
        assert config.check_same_thread is False

    def test_azure_redis_config(self):
        """Test Azure Redis configuration."""
        config = AzureRedisConfig(
            hostname="test.redis.cache.windows.net",
            port=6380,
            access_key="test-key",
            db=0,
            ssl=True,
        )
        assert config.hostname == "test.redis.cache.windows.net"
        assert config.port == 6380
        assert config.access_key == "test-key"
        assert config.db == 0
        assert config.ssl is True

    def test_azure_redis_config_validation(self):
        """Test Azure Redis configuration validation."""
        # Missing required fields should raise validation error
        with pytest.raises(ValidationError):
            AzureRedisConfig()

    def test_azure_redis_config_defaults(self):
        """Test Azure Redis configuration defaults."""
        config = AzureRedisConfig(
            hostname="test.redis.cache.windows.net", access_key="test-key"
        )
        assert config.port == 6380
        assert config.db == 0
        assert config.ssl is True
        assert config.socket_timeout == 5.0
        assert config.socket_connect_timeout == 5.0
        assert config.collection_prefix == "nexamem"
        assert config.use_collections is True


class TestStorageConfig:
    """Test unified storage configuration."""

    def test_memory_factory_method(self):
        """Test memory storage factory method."""
        config = StorageConfig.memory()
        assert config.type == "memory"
        assert isinstance(config.config, MemoryConfig)

    def test_file_factory_method(self):
        """Test file storage factory method."""
        config = StorageConfig.file("./custom_data")
        assert config.type == "file"
        assert isinstance(config.config, FileConfig)
        assert config.config.path == "./custom_data"

    def test_sqlite_factory_method(self):
        """Test SQLite storage factory method."""
        config = StorageConfig.sqlite("./custom.db")
        assert config.type == "sqlite"
        assert isinstance(config.config, SQLiteConfig)
        assert config.config.path == "./custom.db"

    def test_azure_redis_factory_method(self):
        """Test Azure Redis storage factory method."""
        redis_config = AzureRedisConfig(
            hostname="test.redis.cache.windows.net", access_key="test-key"
        )
        config = StorageConfig.azure_redis(redis_config)
        assert config.type == "azure_redis"
        assert isinstance(config.config, AzureRedisConfig)
        assert config.config.hostname == "test.redis.cache.windows.net"

    def test_storage_config_validation(self):
        """Test storage configuration validation."""
        # Valid configurations should work
        memory_config = StorageConfig.memory()
        assert memory_config.type == "memory"


class TestAIMemoryConfig:
    """Test AI Memory configuration."""

    def test_aimemory_config_creation(self):
        """Test creating AI Memory configuration."""
        storage_config = StorageConfig.memory()
        config = AIMemoryConfig(default_scope="test_app", storage=storage_config)

        assert config.default_scope == "test_app"
        assert config.storage.type == "memory"

    def test_aimemory_config_with_different_storages(self):
        """Test AI Memory configuration with different storage types."""
        # Test with file storage
        file_storage = StorageConfig.file("./test_data")
        config = AIMemoryConfig(default_scope="file_test", storage=file_storage)
        assert config.storage.type == "file"

        # Test with SQLite storage
        sqlite_storage = StorageConfig.sqlite("./test.db")
        config = AIMemoryConfig(default_scope="sqlite_test", storage=sqlite_storage)
        assert config.storage.type == "sqlite"

        # Test with Azure Redis storage
        redis_storage = StorageConfig.azure_redis(
            AzureRedisConfig(
                hostname="test.redis.cache.windows.net", access_key="test-key"
            )
        )
        config = AIMemoryConfig(default_scope="redis_test", storage=redis_storage)
        assert config.storage.type == "azure_redis"

    def test_aimemory_config_validation(self):
        """Test AI Memory configuration validation."""
        storage_config = StorageConfig.memory()

        # Valid configuration should work
        config = AIMemoryConfig(default_scope="test", storage=storage_config)
        assert config.default_scope == "test"

        # Missing required fields should raise validation error
        with pytest.raises(ValidationError):
            AIMemoryConfig()  # Missing required fields

    def test_config_serialization(self):
        """Test configuration serialization/deserialization."""
        storage_config = StorageConfig.memory()
        config = AIMemoryConfig(default_scope="test_app", storage=storage_config)

        # Convert to dict
        config_dict = config.model_dump()
        assert config_dict["default_scope"] == "test_app"
        assert config_dict["storage"]["type"] == "memory"

        # Recreate from dict
        new_config = AIMemoryConfig.model_validate(config_dict)
        assert new_config.default_scope == "test_app"
        assert new_config.storage.type == "memory"
