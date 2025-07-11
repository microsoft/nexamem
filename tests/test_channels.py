"""
Unit tests for Channels module - ChannelConfig, ChannelManager, and YAML validation
"""
import tempfile
from unittest.mock import patch

import pytest
import yaml
from pydantic import ValidationError

from nexamem.channels import (
    ChannelAlreadyExists,
    ChannelConfig,
    ChannelManager,
    YamlSchemaError,
    validate_yaml_schema,
)


class TestChannelConfig:
    """Test suite for ChannelConfig class."""

    def test_create_valid_channel_config(self):
        """Test creating a valid ChannelConfig."""
        config = ChannelConfig(
            name="test_channel",
            ttl_sec=3600,
            encrypt=True,
            quota_bytes=1000000
        )

        assert config.name == "test_channel"
        assert config.ttl_sec == 3600
        assert config.encrypt is True
        assert config.quota_bytes == 1000000

    def test_channel_config_defaults(self):
        """Test ChannelConfig with default values."""
        config = ChannelConfig(
            name="working",
            ttl_sec=14400
        )

        assert config.name == "working"
        assert config.ttl_sec == 14400
        assert config.encrypt is False  # Default
        assert config.quota_bytes is None  # Default

    def test_valid_channel_names(self):
        """Test various valid channel names."""
        valid_names = [
            "working",
            "procedure",
            "routing",
            "debug_logs",
            "user_context",
            "a",  # Single letter
            "test123",
            "very_long_channel_name_that_is_still_valid"
        ]

        for name in valid_names:
            config = ChannelConfig(name=name, ttl_sec=3600)
            assert config.name == name

    def test_invalid_channel_names(self):
        """Test invalid channel names that should fail validation."""
        invalid_names = [
            "Invalid-Channel",  # Hyphens not allowed
            "CamelCase",  # Uppercase not allowed
            "123channel",  # Can't start with number
            "channel with spaces",  # Spaces not allowed
            "channel@special",  # Special characters
            "",  # Empty string
            "a" * 51,  # Too long (>50 chars)
        ]

        for name in invalid_names:
            with pytest.raises(ValidationError):
                ChannelConfig(name=name, ttl_sec=3600)

    def test_ttl_validation(self):
        """Test TTL validation rules."""
        # Valid TTL values
        valid_ttls = [60, 3600, 86400, 604800]  # 1min, 1hr, 1day, 7days
        for ttl in valid_ttls:
            config = ChannelConfig(name="test", ttl_sec=ttl)
            assert config.ttl_sec == ttl

        # Invalid TTL values
        invalid_ttls = [
            59,  # Too low (< 1 minute)
            604801,  # Too high (> 7 days)
            0,  # Zero
            -1,  # Negative
        ]
        for ttl in invalid_ttls:
            with pytest.raises(ValidationError):
                ChannelConfig(name="test", ttl_sec=ttl)

    def test_quota_bytes_validation(self):
        """Test quota_bytes validation rules."""
        # Valid quota values
        valid_quotas = [1, 1000, 1000000, 1000000000]  # 1B to 1GB
        for quota in valid_quotas:
            config = ChannelConfig(name="test", ttl_sec=3600, quota_bytes=quota)
            assert config.quota_bytes == quota

        # Invalid quota values
        invalid_quotas = [
            0,  # Zero
            -1,  # Negative
            1000000001,  # Too high (> 1GB)
        ]
        for quota in invalid_quotas:
            with pytest.raises(ValidationError):
                ChannelConfig(name="test", ttl_sec=3600, quota_bytes=quota)

    def test_non_integer_ttl(self):
        """Test non-integer TTL values."""
        with pytest.raises(ValidationError):
            ChannelConfig(name="test", ttl_sec="3600")  # String

        with pytest.raises(ValidationError):
            ChannelConfig(name="test", ttl_sec=3600.5)  # Float

    def test_non_integer_quota(self):
        """Test non-integer quota_bytes values."""
        with pytest.raises(ValidationError):
            ChannelConfig(name="test", ttl_sec=3600, quota_bytes="1000")  # String

        with pytest.raises(ValidationError):
            ChannelConfig(name="test", ttl_sec=3600, quota_bytes=1000.5)  # Float


class TestChannelManager:
    """Test suite for ChannelManager class."""

    def test_create_channel_manager_without_yaml(self):
        """Test creating ChannelManager without YAML file."""
        manager = ChannelManager()
        assert len(manager.channels) == 0

    def test_load_channels_from_yaml(self, temp_channels_yaml):
        """Test loading channels from YAML file."""
        manager = ChannelManager(channels_yaml=temp_channels_yaml)

        assert len(manager.channels) == 3
        assert "working" in manager.channels
        assert "procedure" in manager.channels
        assert "routing" in manager.channels

        # Check specific channel properties
        working = manager.get_channel("working")
        assert working.ttl_sec == 14400
        assert working.encrypt is True
        assert working.quota_bytes == 1000000

    def test_register_new_channel(self):
        """Test registering a new channel dynamically."""
        manager = ChannelManager()

        config = ChannelConfig(
            name="scratch",
            ttl_sec=60,
            encrypt=False,
            quota_bytes=500000
        )

        manager.register_channel(config)
        assert "scratch" in manager.channels
        assert manager.get_channel("scratch") == config

    def test_register_duplicate_channel(self):
        """Test registering a channel that already exists."""
        manager = ChannelManager()

        config1 = ChannelConfig(name="test", ttl_sec=3600)
        config2 = ChannelConfig(name="test", ttl_sec=7200)

        manager.register_channel(config1)

        with pytest.raises(ChannelAlreadyExists):
            manager.register_channel(config2)

    def test_get_existing_channel(self, temp_channels_yaml):
        """Test getting an existing channel."""
        manager = ChannelManager(channels_yaml=temp_channels_yaml)

        channel = manager.get_channel("working")
        assert channel is not None
        assert channel.name == "working"
        assert channel.ttl_sec == 14400

    def test_get_nonexistent_channel(self):
        """Test getting a channel that doesn't exist."""
        manager = ChannelManager()

        channel = manager.get_channel("nonexistent")
        assert channel is None

    def test_list_all_channels(self, temp_channels_yaml):
        """Test listing all channels."""
        manager = ChannelManager(channels_yaml=temp_channels_yaml)

        channels = manager.list_channels()
        assert len(channels) == 3
        assert all(isinstance(config, ChannelConfig) for config in channels.values())

    def test_channel_exists(self, temp_channels_yaml):
        """Test checking if channel exists."""
        manager = ChannelManager(channels_yaml=temp_channels_yaml)

        assert manager.channel_exists("working")
        assert manager.channel_exists("procedure")
        assert not manager.channel_exists("nonexistent")

    def test_invalid_yaml_file(self, invalid_channels_yaml):
        """Test loading invalid YAML file with strict validation."""
        with pytest.raises(YamlSchemaError):
            ChannelManager(channels_yaml=invalid_channels_yaml, strict_validation=True)

    def test_invalid_yaml_file_lenient(self, invalid_channels_yaml):
        """Test loading invalid YAML file with lenient validation."""
        # Should not raise exception with strict_validation=False
        manager = ChannelManager(channels_yaml=invalid_channels_yaml, strict_validation=False)
        # Should still create manager, though channels might be empty or partial
        assert isinstance(manager, ChannelManager)

    def test_nonexistent_yaml_file(self):
        """Test loading non-existent YAML file."""
        with pytest.raises(FileNotFoundError):
            ChannelManager(channels_yaml="/path/that/does/not/exist.yaml")


class TestYamlSchemaValidation:
    """Test suite for YAML schema validation functions."""

    def test_validate_valid_yaml(self, temp_channels_yaml):
        """Test validating a valid YAML file."""
        result = validate_yaml_schema(temp_channels_yaml)

        assert "channels" in result
        assert len(result["channels"]) == 3
        assert "working" in result["channels"]

    def test_validate_invalid_yaml(self, invalid_channels_yaml):
        """Test validating an invalid YAML file."""
        with pytest.raises(YamlSchemaError) as exc_info:
            validate_yaml_schema(invalid_channels_yaml)

        error_message = str(exc_info.value)
        assert "validation" in error_message.lower()

    def test_validate_yaml_with_reserved_names(self):
        """Test validation fails with reserved channel names."""
        reserved_names = ["admin", "system", "internal", "redis", "audit"]

        for reserved_name in reserved_names:
            content = {
                "channels": {
                    reserved_name: {
                        "ttl_sec": 3600,
                        "encrypt": False
                    }
                }
            }

            with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
                yaml.dump(content, f)
                temp_file = f.name

            try:
                with pytest.raises(YamlSchemaError) as exc_info:
                    validate_yaml_schema(temp_file)
                assert "reserved" in str(exc_info.value).lower()
            finally:
                import os
                os.unlink(temp_file)

    def test_validate_yaml_missing_required_fields(self):
        """Test validation fails when required fields are missing."""
        content = {
            "channels": {
                "working": {
                    "encrypt": True  # Missing ttl_sec
                }
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(content, f)
            temp_file = f.name

        try:
            with pytest.raises(YamlSchemaError):
                validate_yaml_schema(temp_file)
        finally:
            import os
            os.unlink(temp_file)

    def test_validate_yaml_unknown_fields(self):
        """Test validation fails with unknown fields."""
        content = {
            "channels": {
                "working": {
                    "ttl_sec": 3600,
                    "encrypt": True,
                    "unknown_field": "value"  # Unknown field
                }
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(content, f)
            temp_file = f.name

        try:
            with pytest.raises(YamlSchemaError):
                validate_yaml_schema(temp_file)
        finally:
            import os
            os.unlink(temp_file)

    def test_validate_empty_channels(self):
        """Test validation fails with empty channels."""
        content = {"channels": {}}

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(content, f)
            temp_file = f.name

        try:
            with pytest.raises(YamlSchemaError):
                validate_yaml_schema(temp_file)
        finally:
            import os
            os.unlink(temp_file)

    def test_validate_malformed_yaml(self):
        """Test validation with malformed YAML syntax."""
        malformed_content = "channels:\n  working:\n    ttl_sec: [invalid yaml"

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(malformed_content)
            temp_file = f.name

        try:
            with pytest.raises(YamlSchemaError):
                validate_yaml_schema(temp_file)
        finally:
            import os
            os.unlink(temp_file)

    def test_validate_nonexistent_file(self):
        """Test validation with non-existent file."""
        with pytest.raises(FileNotFoundError):
            validate_yaml_schema("/path/that/does/not/exist.yaml")

    @patch('nexamem.channels.yaml', None)
    def test_yaml_not_available(self):
        """Test behavior when PyYAML is not available."""
        with pytest.raises(ImportError):
            ChannelManager(channels_yaml="test.yaml")

    def test_yaml_with_all_optional_fields(self):
        """Test YAML validation with all optional fields present."""
        content = {
            "channels": {
                "full_config": {
                    "ttl_sec": 3600,
                    "encrypt": True,
                    "quota_bytes": 1000000
                }
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(content, f)
            temp_file = f.name

        try:
            result = validate_yaml_schema(temp_file)
            assert "channels" in result
            assert "full_config" in result["channels"]
            channel = result["channels"]["full_config"]
            assert channel["ttl_sec"] == 3600
            assert channel["encrypt"] is True
            assert channel["quota_bytes"] == 1000000
        finally:
            import os
            os.unlink(temp_file)
