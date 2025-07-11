"""
Unit tests to verify existence of enums and constant values in the nexamem package.
This file specifically tests for enums, constants, and other value definitions.
"""
import inspect

import pytest

from nexamem import metrics, policy


class TestEnumsAndConstants:
    """Test enums and constant values in the package."""
    
    def test_pii_detector_patterns_constants(self):
        """Test that PIIDetector has pattern constants."""
        pii_detector = policy.PIIDetector
        
        # Test that PII_PATTERNS class attribute exists
        assert hasattr(pii_detector, 'PII_PATTERNS')
        assert isinstance(pii_detector.PII_PATTERNS, dict)
        
        # Test expected PII pattern types
        expected_patterns = ['email', 'phone', 'ssn', 'credit_card']
        for pattern_name in expected_patterns:
            assert pattern_name in pii_detector.PII_PATTERNS
            assert isinstance(pii_detector.PII_PATTERNS[pattern_name], str)
    
    def test_metrics_constants(self):
        """Test metrics module constants and global instance."""
        # Test that the global metrics collector exists
        assert hasattr(metrics, '_global_metrics')
        global_metrics = metrics.get_metrics()
        assert global_metrics is not None
        assert type(global_metrics).__name__ == 'MetricsCollector'
    
    def test_audit_sink_default_values(self):
        """Test AuditSink default configuration values."""
        from nexamem.audit import AuditSink
        
        # Check that the class has expected default values
        # We can't instantiate without Redis, but we can check defaults in constructor
        sig = inspect.signature(AuditSink.__init__)
        params = sig.parameters
        
        # Check stream_name default
        assert 'stream_name' in params
        assert params['stream_name'].default == "aimemory:audit"
    
    def test_config_error_hierarchy(self):
        """Test ConfigError exception hierarchy."""
        from nexamem.config import ConfigError
        
        assert issubclass(ConfigError, Exception)
        assert ConfigError.__name__ == 'ConfigError'
    
    def test_channel_validation_constants(self):
        """Test channel validation constants and limits."""
        from nexamem.channels import ChannelConfig
        
        # Test by creating a channel and checking validation limits
        # The actual values are embedded in validators, but we can test behavior
        
        # Test minimum TTL
        with pytest.raises(ValueError, match="TTL must be at least"):
            ChannelConfig(name="test", ttl_sec=30)  # Below 60 second minimum
        
        # Test maximum TTL (7 days = 604800 seconds)
        with pytest.raises(ValueError, match="TTL cannot exceed"):
            ChannelConfig(name="test", ttl_sec=604801)  # Above 7 day maximum
        
        # Test valid TTL
        config = ChannelConfig(name="test", ttl_sec=3600)
        assert config.ttl_sec == 3600
    
    def test_quota_limits_constants(self):
        """Test quota validation constants."""
        from nexamem.channels import ChannelConfig
        
        # Test quota byte limits
        with pytest.raises(ValueError, match="quota_bytes cannot exceed"):
            ChannelConfig(name="test", ttl_sec=3600, quota_bytes=1_000_000_001)  # Above 1GB
        
        with pytest.raises(ValueError, match="quota_bytes must be positive"):
            ChannelConfig(name="test", ttl_sec=3600, quota_bytes=0)
        
        # Test valid quota
        config = ChannelConfig(name="test", ttl_sec=3600, quota_bytes=1000000)
        assert config.quota_bytes == 1000000
    
    def test_channel_name_validation_patterns(self):
        """Test channel name validation pattern constants."""
        from nexamem.channels import ChannelConfig
        
        # Test snake_case pattern validation
        valid_names = ["test", "test_channel", "a1_b2_c3", "my_long_channel_name"]
        invalid_names = ["Test", "test-channel", "1test", "test.channel", "", "a" * 51]
        
        for name in valid_names:
            config = ChannelConfig(name=name, ttl_sec=3600)
            assert config.name == name
        
        for name in invalid_names:
            with pytest.raises(ValueError):
                ChannelConfig(name=name, ttl_sec=3600)
    
    def test_reserved_channel_names(self):
        """Test reserved channel names constants."""
        from nexamem.channels import ChannelsYamlSchema
        
        # Test reserved names by attempting to create them
        reserved_names = ['admin', 'system', 'internal', 'redis', 'audit']
        
        for reserved_name in reserved_names:
            channels_data = {
                'channels': {
                    reserved_name: {'ttl_sec': 3600}
                }
            }
            with pytest.raises(ValueError, match=f"Channel name '{reserved_name}' is reserved"):
                ChannelsYamlSchema(**channels_data)
    
    def test_default_memory_scope_env(self):
        """Test MemoryScope default environment value."""
        from nexamem import MemoryScope
        
        # Test default environment value
        scope = MemoryScope(agent_id="test", user_id="user123")
        assert scope.env == "prod"  # Default environment
    
    def test_async_audit_sink_defaults(self):
        """Test AsyncAuditSink default values."""
        from nexamem.audit import AsyncAuditSink
        
        sig = inspect.signature(AsyncAuditSink.__init__)
        params = sig.parameters
        
        # Check stream_name default
        assert 'stream_name' in params
        assert params['stream_name'].default == "aimemory:audit"
    
    def test_redis_adapter_defaults(self):
        """Test RedisAdapter default connection parameters."""
        from nexamem.redis_adapter import RedisAdapter
        
        sig = inspect.signature(RedisAdapter.__init__)
        params = sig.parameters
        
        # Check common default parameters
        assert params['host'].default == "localhost"
        assert params['port'].default == 6379
        assert params['db'].default == 0
        assert params['ssl'].default is False
        assert params['use_fakeredis'].default is False


class TestExceptionHierarchy:
    """Test exception class hierarchies and relationships."""
    
    def test_policy_violation_hierarchy(self):
        """Test PolicyViolation exception hierarchy."""
        from nexamem.policy import (
            PolicyViolation, QuotaExceeded, EncryptionRequired, TTLViolation
        )
        
        # Test base class
        assert issubclass(PolicyViolation, Exception)
        
        # Test derived classes
        assert issubclass(QuotaExceeded, PolicyViolation)
        assert issubclass(EncryptionRequired, PolicyViolation)
        assert issubclass(TTLViolation, PolicyViolation)
        
        # Test that they're not subclasses of each other
        assert not issubclass(QuotaExceeded, EncryptionRequired)
        assert not issubclass(QuotaExceeded, TTLViolation)
        assert not issubclass(EncryptionRequired, TTLViolation)
    
    def test_aimemory_exception_hierarchy(self):
        """Test AIMemory exception hierarchy."""
        from nexamem.aimemory import AIMemoryError, ChannelNotFound
        
        assert issubclass(AIMemoryError, Exception)
        assert issubclass(ChannelNotFound, AIMemoryError)
    
    def test_channel_exception_hierarchy(self):
        """Test channel exception hierarchy."""
        from nexamem.channels import ChannelAlreadyExists, YamlSchemaError
        
        assert issubclass(ChannelAlreadyExists, Exception)
        assert issubclass(YamlSchemaError, Exception)
    
    def test_redis_exception_hierarchy(self):
        """Test Redis exception hierarchy."""
        from nexamem.redis_adapter import RedisConnectionError
        
        assert issubclass(RedisConnectionError, Exception)


class TestPackageConstants:
    """Test package-level constants and version information."""
    
    def test_package_version_format(self):
        """Test package version format."""
        import nexamem
        
        assert hasattr(nexamem, '__version__')
        version = nexamem.__version__
        assert isinstance(version, str)
        assert len(version) > 0
        
        # Test version format (should be semantic versioning like "0.3.4")
        parts = version.split('.')
        assert len(parts) >= 2  # At least major.minor
        assert all(part.isdigit() for part in parts)
    
    def test_package_all_completeness(self):
        """Test that __all__ contains all public symbols."""
        import nexamem
        
        assert hasattr(nexamem, '__all__')
        all_exports = nexamem.__all__
        
        # Test that __all__ is a list/tuple
        assert isinstance(all_exports, (list, tuple))
        assert len(all_exports) > 0
        
        # Test that all items in __all__ are strings
        assert all(isinstance(item, str) for item in all_exports)
        
        # Test that __version__ is included
        assert '__version__' in all_exports


if __name__ == "__main__":
    pytest.main([__file__])
