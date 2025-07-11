"""
Unit tests to verify the existence of classes, methods, enums, and values in the nexamem package.
These tests ensure that the public API remains stable and all expected components are present.
"""
import pytest
import inspect

# Import all modules from nexamem
import nexamem
from nexamem import (
    # Core classes
    AIMemory,
    AsyncAIMemory,
    MemoryScope,
    ChatHistory,
    
    # Channel management
    ChannelConfig,
    ChannelManager,
    ChannelAlreadyExists,
    
    # Policy engine
    PolicyEngine,
    PIIDetector,
    PolicyViolation,
    QuotaExceeded,
    EncryptionRequired,
    TTLViolation,
    
    # Content processing
    ContentProcessorChain,
    PIIRedactor,
    ContentEnricher,
    
    # Audit and metrics
    AuditSink,
    AsyncAuditSink,
    metrics
)

# Import specific modules for deeper inspection
from nexamem import (
    aimemory,
    memory_scope,
    channels,
    policy,
    content_processor,
    audit,
    config,
    redis_adapter,
    history
)


class TestPackageStructure:
    """Test the overall package structure and exported symbols."""
    
    def test_package_version(self):
        """Test that package has version information."""
        assert hasattr(nexamem, '__version__')
        assert isinstance(nexamem.__version__, str)
        assert len(nexamem.__version__) > 0
    
    def test_package_all_exports(self):
        """Test that all expected symbols are in __all__."""
        expected_exports = {
            "__version__",
            "ChatHistory",
            "initialize", 
            "get_config",
            "AIMemory",
            "AsyncAIMemory",
            "MemoryScope",
            "ChannelConfig",
            "ChannelManager",
            "ChannelAlreadyExists",
            "PolicyEngine",
            "PIIDetector",
            "PolicyViolation",
            "QuotaExceeded",
            "EncryptionRequired",
            "TTLViolation",
            "ContentProcessorChain",
            "PIIRedactor",
            "ContentEnricher",
            "AuditSink",
            "AsyncAuditSink",
            "metrics"
        }
        
        assert hasattr(nexamem, '__all__')
        actual_exports = set(nexamem.__all__)
        assert expected_exports == actual_exports


class TestAIMemoryClass:
    """Test AIMemory class structure and methods."""
    
    def test_aimemory_class_exists(self):
        """Test that AIMemory class exists and is importable."""
        assert inspect.isclass(AIMemory)
        assert hasattr(aimemory, 'AIMemory')
    
    def test_aimemory_constructor_parameters(self):
        """Test AIMemory constructor has expected parameters."""
        sig = inspect.signature(AIMemory.__init__)
        params = list(sig.parameters.keys())
        
        expected_params = [
            'self', 'redis_host', 'redis_port', 'redis_password', 'redis_ssl',
            'redis_db', 'channels_yaml', 'use_fakeredis', 'enable_audit',
            'enable_metrics', 'enable_content_processing', 'strict_yaml_validation'
        ]
        
        for param in expected_params:
            assert param in params
    
    def test_aimemory_methods_exist(self):
        """Test that all expected AIMemory methods exist."""
        expected_methods = [
            'write', 'read', 'checkpoint', 'checkpoint_atomic',
            'bulk_erase', 'count_bytes', 'register_channel',
            'list_channels', 'get_channel_config'
        ]
        
        for method_name in expected_methods:
            assert hasattr(AIMemory, method_name)
            assert callable(getattr(AIMemory, method_name))
    
    def test_aimemory_write_method_signature(self):
        """Test AIMemory.write method signature."""
        sig = inspect.signature(AIMemory.write)
        params = list(sig.parameters.keys())
        
        expected_params = ['self', 'scope', 'channel', 'content']
        for param in expected_params:
            assert param in params
    
    def test_aimemory_read_method_signature(self):
        """Test AIMemory.read method signature."""
        sig = inspect.signature(AIMemory.read)
        params = list(sig.parameters.keys())
        
        expected_params = ['self', 'scope', 'channel']
        for param in expected_params:
            assert param in params


class TestAsyncAIMemoryClass:
    """Test AsyncAIMemory class structure and methods."""
    
    def test_async_aimemory_class_exists(self):
        """Test that AsyncAIMemory class exists."""
        assert inspect.isclass(AsyncAIMemory)
        assert hasattr(aimemory, 'AsyncAIMemory')
    
    def test_async_aimemory_methods_exist(self):
        """Test that all expected AsyncAIMemory methods exist."""
        expected_methods = [
            'write', 'read', 'checkpoint', 'checkpoint_atomic',
            'bulk_erase', 'count_bytes', 'register_channel',
            'list_channels', 'get_channel_config', 'close'
        ]
        
        for method_name in expected_methods:
            assert hasattr(AsyncAIMemory, method_name)
            assert callable(getattr(AsyncAIMemory, method_name))
    
    def test_async_methods_are_coroutines(self):
        """Test that async methods are properly declared as coroutines."""
        async_methods = ['write', 'read', 'checkpoint', 'checkpoint_atomic', 'bulk_erase', 'count_bytes', 'close']
        
        for method_name in async_methods:
            method = getattr(AsyncAIMemory, method_name)
            assert inspect.iscoroutinefunction(method)


class TestMemoryScopeClass:
    """Test MemoryScope class structure and methods."""
    
    def test_memory_scope_class_exists(self):
        """Test that MemoryScope class exists."""
        assert inspect.isclass(MemoryScope)
        assert hasattr(memory_scope, 'MemoryScope')
    
    def test_memory_scope_fields(self):
        """Test MemoryScope has expected fields."""
        # Create instance to check fields
        scope = MemoryScope(agent_id="test", user_id="user123")
        
        assert hasattr(scope, 'agent_id')
        assert hasattr(scope, 'user_id')
        assert hasattr(scope, 'session_id')
        assert hasattr(scope, 'env')
    
    def test_memory_scope_methods_exist(self):
        """Test that all expected MemoryScope methods exist."""
        expected_methods = ['get_key_prefix', 'get_index_key', 'model_dump_dict']
        
        for method_name in expected_methods:
            assert hasattr(MemoryScope, method_name)
            assert callable(getattr(MemoryScope, method_name))


class TestChannelClasses:
    """Test channel-related classes."""
    
    def test_channel_config_class_exists(self):
        """Test that ChannelConfig class exists."""
        assert inspect.isclass(ChannelConfig)
        assert hasattr(channels, 'ChannelConfig')
    
    def test_channel_config_fields(self):
        """Test ChannelConfig has expected fields."""
        config = ChannelConfig(name="test_channel", ttl_sec=3600)
        
        assert hasattr(config, 'name')
        assert hasattr(config, 'ttl_sec')
        assert hasattr(config, 'encrypt')
        assert hasattr(config, 'quota_bytes')
    
    def test_channel_manager_class_exists(self):
        """Test that ChannelManager class exists."""
        assert inspect.isclass(ChannelManager)
        assert hasattr(channels, 'ChannelManager')
    
    def test_channel_manager_methods_exist(self):
        """Test that all expected ChannelManager methods exist."""
        expected_methods = [
            'load_from_yaml', 'register_channel', 'get_channel',
            'list_channels', 'channel_exists'
        ]
        
        for method_name in expected_methods:
            assert hasattr(ChannelManager, method_name)
            assert callable(getattr(ChannelManager, method_name))
    
    def test_channel_exceptions_exist(self):
        """Test that channel-related exceptions exist."""
        assert inspect.isclass(ChannelAlreadyExists)
        assert issubclass(ChannelAlreadyExists, Exception)
        assert hasattr(channels, 'ChannelAlreadyExists')
    
    def test_yaml_schema_classes_exist(self):
        """Test that YAML schema validation classes exist."""
        assert hasattr(channels, 'ChannelsYamlSchema')
        assert hasattr(channels, 'YamlSchemaError')
        assert inspect.isclass(channels.ChannelsYamlSchema)
        assert inspect.isclass(channels.YamlSchemaError)
    
    def test_yaml_utility_functions_exist(self):
        """Test that YAML utility functions exist."""
        expected_functions = [
            'validate_yaml_schema',
            'generate_yaml_schema_docs',
            'get_default_channels_config',
            'create_default_channels_yaml'
        ]
        
        for func_name in expected_functions:
            assert hasattr(channels, func_name)
            assert callable(getattr(channels, func_name))


class TestPolicyClasses:
    """Test policy engine classes."""
    
    def test_policy_engine_class_exists(self):
        """Test that PolicyEngine class exists."""
        assert inspect.isclass(PolicyEngine)
        assert hasattr(policy, 'PolicyEngine')
    
    def test_policy_engine_methods_exist(self):
        """Test that all expected PolicyEngine methods exist."""
        expected_methods = ['validate_write', 'post_write_update']
        
        for method_name in expected_methods:
            assert hasattr(PolicyEngine, method_name)
            assert callable(getattr(PolicyEngine, method_name))
    
    def test_pii_detector_class_exists(self):
        """Test that PIIDetector class exists."""
        assert inspect.isclass(PIIDetector)
        assert hasattr(policy, 'PIIDetector')
    
    def test_pii_detector_methods_exist(self):
        """Test that all expected PIIDetector methods exist."""
        expected_methods = ['detect_pii', 'has_pii']
        
        for method_name in expected_methods:
            assert hasattr(PIIDetector, method_name)
            assert callable(getattr(PIIDetector, method_name))
    
    def test_pii_detector_patterns_exist(self):
        """Test that PIIDetector has pattern constants."""
        assert hasattr(PIIDetector, 'PII_PATTERNS')
        assert isinstance(PIIDetector.PII_PATTERNS, dict)
        
        expected_patterns = ['email', 'phone', 'ssn', 'credit_card']
        for pattern in expected_patterns:
            assert pattern in PIIDetector.PII_PATTERNS
    
    def test_quota_tracker_class_exists(self):
        """Test that QuotaTracker class exists."""
        assert hasattr(policy, 'QuotaTracker')
        assert inspect.isclass(policy.QuotaTracker)
    
    def test_quota_tracker_methods_exist(self):
        """Test that all expected QuotaTracker methods exist."""
        expected_methods = ['check_quota', 'update_quota']
        quota_tracker = policy.QuotaTracker
        
        for method_name in expected_methods:
            assert hasattr(quota_tracker, method_name)
            assert callable(getattr(quota_tracker, method_name))
    
    def test_policy_exceptions_exist(self):
        """Test that all policy exception classes exist."""
        policy_exceptions = [
            PolicyViolation,
            QuotaExceeded,
            EncryptionRequired,
            TTLViolation
        ]
        
        for exc_class in policy_exceptions:
            assert inspect.isclass(exc_class)
            assert issubclass(exc_class, Exception)
        
        # Test inheritance hierarchy
        assert issubclass(QuotaExceeded, PolicyViolation)
        assert issubclass(EncryptionRequired, PolicyViolation)
        assert issubclass(TTLViolation, PolicyViolation)


class TestContentProcessorClasses:
    """Test content processor classes."""
    
    def test_content_processor_protocol_exists(self):
        """Test that ContentProcessor protocol exists."""
        assert hasattr(content_processor, 'ContentProcessor')
    
    def test_content_processor_chain_class_exists(self):
        """Test that ContentProcessorChain class exists."""
        assert inspect.isclass(ContentProcessorChain)
        assert hasattr(content_processor, 'ContentProcessorChain')
    
    def test_content_processor_chain_methods_exist(self):
        """Test that all expected ContentProcessorChain methods exist."""
        expected_methods = ['add_processor', 'process']
        
        for method_name in expected_methods:
            assert hasattr(ContentProcessorChain, method_name)
            assert callable(getattr(ContentProcessorChain, method_name))
    
    def test_pii_redactor_class_exists(self):
        """Test that PIIRedactor class exists."""
        assert inspect.isclass(PIIRedactor)
        assert hasattr(content_processor, 'PIIRedactor')
    
    def test_pii_redactor_methods_exist(self):
        """Test that PIIRedactor has process method."""
        assert hasattr(PIIRedactor, 'process')
        assert callable(PIIRedactor.process)
    
    def test_content_enricher_class_exists(self):
        """Test that ContentEnricher class exists."""
        assert inspect.isclass(ContentEnricher)
        assert hasattr(content_processor, 'ContentEnricher')
    
    def test_content_enricher_methods_exist(self):
        """Test that ContentEnricher has process method."""
        assert hasattr(ContentEnricher, 'process')
        assert callable(ContentEnricher.process)
    
    def test_default_chain_function_exists(self):
        """Test that create_default_chain function exists."""
        assert hasattr(content_processor, 'create_default_chain')
        assert callable(content_processor.create_default_chain)


class TestAuditClasses:
    """Test audit-related classes."""
    
    def test_audit_sink_class_exists(self):
        """Test that AuditSink class exists."""
        assert inspect.isclass(AuditSink)
        assert hasattr(audit, 'AuditSink')
    
    def test_audit_sink_methods_exist(self):
        """Test that all expected AuditSink methods exist."""
        expected_methods = [
            'log_operation', 'get_audit_records', 'disable', 'enable'
        ]
        
        for method_name in expected_methods:
            assert hasattr(AuditSink, method_name)
            assert callable(getattr(AuditSink, method_name))
    
    def test_async_audit_sink_class_exists(self):
        """Test that AsyncAuditSink class exists."""
        assert inspect.isclass(AsyncAuditSink)
        assert hasattr(audit, 'AsyncAuditSink')
    
    def test_async_audit_sink_methods_exist(self):
        """Test that all expected AsyncAuditSink methods exist."""
        expected_methods = ['log_operation', 'disable', 'enable']
        
        for method_name in expected_methods:
            assert hasattr(AsyncAuditSink, method_name)
            assert callable(getattr(AsyncAuditSink, method_name))
    
    def test_async_audit_methods_are_coroutines(self):
        """Test that async audit methods are coroutines."""
        assert inspect.iscoroutinefunction(AsyncAuditSink.log_operation)


class TestMetricsModule:
    """Test metrics module classes and functions."""
    
    def test_metrics_collector_class_exists(self):
        """Test that MetricsCollector class exists."""
        assert hasattr(metrics, 'MetricsCollector')
        assert inspect.isclass(metrics.MetricsCollector)
    
    def test_metrics_collector_methods_exist(self):
        """Test that all expected MetricsCollector methods exist."""
        expected_methods = [
            'increment_counter', 'record_duration', 'get_counter',
            'get_histogram_stats', 'get_all_metrics', 'reset',
            'disable', 'enable'
        ]
        
        metrics_collector = metrics.MetricsCollector
        for method_name in expected_methods:
            assert hasattr(metrics_collector, method_name)
            assert callable(getattr(metrics_collector, method_name))
    
    def test_metrics_timer_class_exists(self):
        """Test that MetricsTimer class exists."""
        assert hasattr(metrics, 'MetricsTimer')
        assert inspect.isclass(metrics.MetricsTimer)
    
    def test_metrics_timer_context_manager(self):
        """Test that MetricsTimer is a context manager."""
        timer_class = metrics.MetricsTimer
        assert hasattr(timer_class, '__enter__')
        assert hasattr(timer_class, '__exit__')
    
    def test_global_metrics_functions_exist(self):
        """Test that global metrics functions exist."""
        expected_functions = [
            'get_metrics', 'increment_counter', 'record_duration', 'timer',
            'record_write_operation', 'record_read_operation', 'record_checkpoint_operation'
        ]
        
        for func_name in expected_functions:
            assert hasattr(metrics, func_name)
            assert callable(getattr(metrics, func_name))


class TestConfigModule:
    """Test configuration module."""
    
    def test_config_functions_exist(self):
        """Test that configuration functions exist."""
        assert hasattr(config, 'initialize')
        assert hasattr(config, 'get_config')
        assert callable(config.initialize)
        assert callable(config.get_config)
    
    def test_config_error_exception_exists(self):
        """Test that ConfigError exception exists."""
        assert hasattr(config, 'ConfigError')
        assert inspect.isclass(config.ConfigError)
        assert issubclass(config.ConfigError, Exception)


class TestRedisAdapterModule:
    """Test Redis adapter module."""
    
    def test_redis_adapter_class_exists(self):
        """Test that RedisAdapter class exists."""
        assert hasattr(redis_adapter, 'RedisAdapter')
        assert inspect.isclass(redis_adapter.RedisAdapter)
    
    def test_async_redis_adapter_class_exists(self):
        """Test that AsyncRedisAdapter class exists."""
        assert hasattr(redis_adapter, 'AsyncRedisAdapter')
        assert inspect.isclass(redis_adapter.AsyncRedisAdapter)
    
    def test_azure_redis_helper_exists(self):
        """Test that AzureRedisConnectionHelper class exists."""
        assert hasattr(redis_adapter, 'AzureRedisConnectionHelper')
        assert inspect.isclass(redis_adapter.AzureRedisConnectionHelper)
    
    def test_redis_connection_error_exists(self):
        """Test that RedisConnectionError exception exists."""
        assert hasattr(redis_adapter, 'RedisConnectionError')
        assert inspect.isclass(redis_adapter.RedisConnectionError)
        assert issubclass(redis_adapter.RedisConnectionError, Exception)


class TestHistoryModule:
    """Test legacy history module."""
    
    def test_chat_history_class_exists(self):
        """Test that ChatHistory class exists."""
        assert inspect.isclass(ChatHistory)
        assert hasattr(history, 'ChatHistory')
    
    def test_message_class_exists(self):
        """Test that Message class exists."""
        assert hasattr(history, 'Message')
        assert inspect.isclass(history.Message)
    
    def test_message_fields(self):
        """Test that Message has expected fields."""
        # Check that Message is a Pydantic model
        assert hasattr(history.Message, 'model_fields')
        
        expected_fields = [
            'role', 'content', 'agent_id', 'user_id', 'session_id',
            'env', 'timestamp', 'tokens', 'data'
        ]
        
        model_fields = history.Message.model_fields
        for field in expected_fields:
            assert field in model_fields


class TestAIMemoryExceptions:
    """Test AIMemory-specific exceptions."""
    
    def test_aimemory_error_exists(self):
        """Test that AIMemoryError exception exists."""
        assert hasattr(aimemory, 'AIMemoryError')
        assert inspect.isclass(aimemory.AIMemoryError)
        assert issubclass(aimemory.AIMemoryError, Exception)
    
    def test_channel_not_found_error_exists(self):
        """Test that ChannelNotFound exception exists."""
        assert hasattr(aimemory, 'ChannelNotFound')
        assert inspect.isclass(aimemory.ChannelNotFound)
        assert issubclass(aimemory.ChannelNotFound, aimemory.AIMemoryError)


class TestImportCompatibility:
    """Test that all expected symbols can be imported."""
    
    def test_top_level_imports(self):
        """Test that all symbols can be imported from the top level."""
        # These should all work without raising ImportError
        # All imports already done at module level, just verify they exist
        assert AIMemory is not None
        assert AsyncAIMemory is not None
        assert MemoryScope is not None
        assert ChatHistory is not None
        assert ChannelConfig is not None
        assert ChannelManager is not None
        assert PolicyEngine is not None
        assert PIIDetector is not None
        assert ContentProcessorChain is not None
        assert PIIRedactor is not None
        assert ContentEnricher is not None
        assert AuditSink is not None
        assert AsyncAuditSink is not None
        assert metrics is not None
        
        # Test exception classes
        assert ChannelAlreadyExists is not None
        assert PolicyViolation is not None
        assert QuotaExceeded is not None
        assert EncryptionRequired is not None
        assert TTLViolation is not None
    
    def test_module_level_imports(self):
        """Test that modules can be imported directly."""
        # All modules already imported at module level, just verify they exist
        assert aimemory is not None
        assert memory_scope is not None
        assert channels is not None
        assert policy is not None
        assert content_processor is not None
        assert audit is not None
        assert config is not None
        assert redis_adapter is not None
        assert history is not None
        assert metrics is not None


if __name__ == "__main__":
    pytest.main([__file__])
