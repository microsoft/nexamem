"""
Test YAML schema validation functionality.
"""
import tempfile
import os
import pytest

from nexamem.channels import (
    validate_yaml_schema, 
    YamlSchemaError, 
    ChannelManager,
    generate_yaml_schema_docs
)
from nexamem import AIMemory


class TestYamlSchemaValidation:
    """Test comprehensive YAML schema validation."""

    def test_valid_yaml_passes_validation(self):
        """Test that valid YAML passes strict validation."""
        valid_yaml = """
channels:
  working:
    ttl_sec: 14400
    encrypt: true
    quota_bytes: 1000000
  
  routing:
    ttl_sec: 86400
    encrypt: false
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(valid_yaml)
            temp_path = f.name
        
        try:
            # Should not raise any exceptions
            result = validate_yaml_schema(temp_path)
            assert 'channels' in result
            assert 'working' in result['channels']
            assert 'routing' in result['channels']
        finally:
            os.unlink(temp_path)

    def test_missing_required_field_raises_error(self):
        """Test that missing required fields raise validation errors."""
        invalid_yaml = """
channels:
  working:
    encrypt: true
    quota_bytes: 1000000
  # Missing ttl_sec
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(invalid_yaml)
            temp_path = f.name
        
        try:
            with pytest.raises(YamlSchemaError) as exc_info:
                validate_yaml_schema(temp_path)
            assert "missing required field 'ttl_sec'" in str(exc_info.value)
        finally:
            os.unlink(temp_path)

    def test_invalid_channel_name_raises_error(self):
        """Test that invalid channel names raise validation errors."""
        invalid_yaml = """
channels:
  Invalid-Channel-Name:  # Hyphens not allowed
    ttl_sec: 14400
    encrypt: true
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(invalid_yaml)
            temp_path = f.name
        
        try:
            with pytest.raises(YamlSchemaError) as exc_info:
                validate_yaml_schema(temp_path)
            assert "must be snake_case" in str(exc_info.value)
        finally:
            os.unlink(temp_path)

    def test_invalid_ttl_range_raises_error(self):
        """Test that TTL values outside valid range raise errors."""
        invalid_yaml = """
channels:
  working:
    ttl_sec: 604801  # Over 7 days limit
    encrypt: true
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(invalid_yaml)
            temp_path = f.name
        
        try:
            with pytest.raises(YamlSchemaError) as exc_info:
                validate_yaml_schema(temp_path)
            assert "cannot exceed" in str(exc_info.value)
        finally:
            os.unlink(temp_path)

    def test_reserved_channel_name_raises_error(self):
        """Test that reserved channel names raise validation errors."""
        invalid_yaml = """
channels:
  admin:  # Reserved name
    ttl_sec: 14400
    encrypt: true
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(invalid_yaml)
            temp_path = f.name
        
        try:
            with pytest.raises(YamlSchemaError) as exc_info:
                validate_yaml_schema(temp_path)
            assert "is reserved" in str(exc_info.value)
        finally:
            os.unlink(temp_path)

    def test_unknown_field_raises_error(self):
        """Test that unknown fields raise validation errors."""
        invalid_yaml = """
channels:
  working:
    ttl_sec: 14400
    encrypt: true
    unknown_field: "invalid"  # Unknown field
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(invalid_yaml)
            temp_path = f.name
        
        try:
            with pytest.raises(YamlSchemaError) as exc_info:
                validate_yaml_schema(temp_path)
            assert "unknown fields" in str(exc_info.value)
        finally:
            os.unlink(temp_path)

    def test_invalid_quota_bytes_raises_error(self):
        """Test that invalid quota_bytes values raise errors."""
        invalid_yaml = """
channels:
  working:
    ttl_sec: 14400
    encrypt: true
    quota_bytes: -1000  # Negative quota
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(invalid_yaml)
            temp_path = f.name
        
        try:
            with pytest.raises(YamlSchemaError) as exc_info:
                validate_yaml_schema(temp_path)
            assert "must be positive" in str(exc_info.value)
        finally:
            os.unlink(temp_path)

    def test_empty_channels_raises_error(self):
        """Test that empty channels dict raises validation error."""
        invalid_yaml = """
channels: {}  # Empty channels
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(invalid_yaml)
            temp_path = f.name
        
        try:
            with pytest.raises(YamlSchemaError) as exc_info:
                validate_yaml_schema(temp_path)
            assert "At least one channel must be defined" in str(exc_info.value)
        finally:
            os.unlink(temp_path)

    def test_channel_manager_strict_validation_enabled(self):
        """Test ChannelManager with strict validation enabled."""
        invalid_yaml = """
channels:
  working:
    ttl_sec: 999999  # Invalid TTL
    encrypt: true
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(invalid_yaml)
            temp_path = f.name
        
        try:
            with pytest.raises(ValueError) as exc_info:
                ChannelManager(temp_path, strict_validation=True)
            assert "YAML schema validation failed" in str(exc_info.value)
        finally:
            os.unlink(temp_path)

    def test_channel_manager_strict_validation_disabled(self):
        """Test ChannelManager with strict validation disabled (backward compatibility)."""
        valid_yaml = """
channels:
  working:
    ttl_sec: 14400
    encrypt: true
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(valid_yaml)
            temp_path = f.name
        
        try:
            # Should work without issues
            manager = ChannelManager(temp_path, strict_validation=False)
            assert manager.channel_exists("working")
        finally:
            os.unlink(temp_path)

    def test_aimemory_strict_validation_integration(self):
        """Test AIMemory integration with strict YAML validation."""
        valid_yaml = """
channels:
  working:
    ttl_sec: 14400
    encrypt: true
    quota_bytes: 1000000
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(valid_yaml)
            temp_path = f.name
        
        try:
            # Should initialize successfully with strict validation
            memory = AIMemory(
                channels_yaml=temp_path,
                strict_yaml_validation=True,
                use_fakeredis=True
            )
            assert memory.channels.channel_exists("working")
        finally:
            os.unlink(temp_path)

    def test_yaml_schema_docs_generation(self):
        """Test that schema documentation can be generated."""
        docs = generate_yaml_schema_docs()
        assert "channels.yaml Schema Documentation" in docs
        assert "ttl_sec:" in docs
        assert "encrypt:" in docs
        assert "quota_bytes:" in docs
        assert "Example:" in docs

    def test_complex_validation_error_messages(self):
        """Test that complex validation scenarios provide clear error messages."""
        complex_invalid_yaml = """
channels:
  BadName:  # Should be snake_case
    ttl_sec: "not_a_number"  # Should be integer
    encrypt: "yes"  # Should be boolean
    quota_bytes: -500  # Should be positive
    invalid_field: true  # Unknown field
  
  working:
    # Missing ttl_sec
    encrypt: true
    
  system:  # Reserved name
    ttl_sec: 3600
    encrypt: false
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(complex_invalid_yaml)
            temp_path = f.name
        
        try:
            with pytest.raises(YamlSchemaError) as exc_info:
                validate_yaml_schema(temp_path)
            
            error_msg = str(exc_info.value)
            # Should contain multiple specific error messages
            assert "snake_case" in error_msg or "reserved" in error_msg or "unknown fields" in error_msg
        finally:
            os.unlink(temp_path)

    def test_yaml_syntax_error_handling(self):
        """Test handling of invalid YAML syntax."""
        invalid_syntax_yaml = """
channels:
  working:
    ttl_sec: 14400
    encrypt: true
  invalid_yaml: [unclosed_bracket
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(invalid_syntax_yaml)
            temp_path = f.name
        
        try:
            with pytest.raises(YamlSchemaError) as exc_info:
                validate_yaml_schema(temp_path)
            assert "Invalid YAML syntax" in str(exc_info.value)
        finally:
            os.unlink(temp_path)
