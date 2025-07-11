"""
Unit tests for AIMemory main class
"""
from unittest.mock import Mock, patch

import pytest
from pydantic import ValidationError

from nexamem import AIMemory, ChannelConfig, MemoryScope
from nexamem.aimemory import ChannelNotFound


class TestAIMemory:
    """Test suite for AIMemory main class."""

    def test_aimemory_initialization_default(self):
        """Test AIMemory initialization with default parameters."""
        memory = AIMemory(use_fakeredis=True)

        assert memory.redis_adapter is not None
        assert memory.channel_manager is not None
        assert memory.policy_engine is not None

    def test_aimemory_initialization_with_yaml(self, temp_channels_yaml):
        """Test AIMemory initialization with YAML configuration."""
        memory = AIMemory(
            channels_yaml=temp_channels_yaml,
            use_fakeredis=True
        )

        # Should have loaded channels from YAML
        channels = memory.list_channels()
        assert len(channels) == 3
        assert "working" in channels
        assert "procedure" in channels
        assert "routing" in channels

    def test_aimemory_initialization_with_features(self, temp_channels_yaml):
        """Test AIMemory initialization with all features enabled."""
        memory = AIMemory(
            channels_yaml=temp_channels_yaml,
            use_fakeredis=True,
            enable_audit=True,
            enable_metrics=True,
            enable_content_processing=True
        )

        assert memory.audit_sink is not None
        assert memory.metrics is not None
        assert memory.content_processor is not None

    def test_aimemory_initialization_with_redis_params(self):
        """Test AIMemory initialization with Redis parameters."""
        memory = AIMemory(
            redis_host="localhost",
            redis_port=6379,
            redis_password="secret",
            redis_ssl=True,
            redis_db=1,
            use_fakeredis=True
        )

        assert memory.redis_adapter is not None

    def test_write_basic(self, aimemory_instance, sample_scope):
        """Test basic write operation."""
        content = "Test message for working memory"

        # Mock the underlying operations
        with patch.object(aimemory_instance.redis_adapter, 'write_message') as mock_write:
            mock_write.return_value = "uuid-123"

            result_uuid = aimemory_instance.write(
                scope=sample_scope,
                channel="working",
                content=content
            )

            assert result_uuid == "uuid-123"
            mock_write.assert_called_once()

    def test_write_with_pii_flag(self, aimemory_instance, sample_scope):
        """Test write operation with PII flag."""
        content = "Sensitive information"

        with patch.object(aimemory_instance.redis_adapter, 'write_message') as mock_write:
            mock_write.return_value = "uuid-456"

            result_uuid = aimemory_instance.write(
                scope=sample_scope,
                channel="working",
                content=content,
                pii=True
            )

            assert result_uuid == "uuid-456"

    def test_write_with_ttl_override(self, aimemory_instance, sample_scope):
        """Test write operation with TTL override."""
        content = "Test message"

        with patch.object(aimemory_instance.redis_adapter, 'write_message') as mock_write:
            mock_write.return_value = "uuid-789"

            result_uuid = aimemory_instance.write(
                scope=sample_scope,
                channel="working",
                content=content,
                ttl_override=1800  # 30 minutes
            )

            assert result_uuid == "uuid-789"

    def test_write_nonexistent_channel(self, aimemory_instance, sample_scope):
        """Test write to non-existent channel."""
        with pytest.raises(ChannelNotFound):
            aimemory_instance.write(
                scope=sample_scope,
                channel="nonexistent",
                content="test"
            )

    def test_write_with_auto_pii(self, aimemory_with_features, sample_scope):
        """Test write operation with auto PII detection."""
        content = "Contact me at user@example.com"

        with patch.object(aimemory_with_features.redis_adapter, 'write_message') as mock_write:
            mock_write.return_value = "uuid-pii"

            result_uuid = aimemory_with_features.write(
                scope=sample_scope,
                channel="working",
                content=content,
                auto_pii=True
            )

            assert result_uuid == "uuid-pii"

    def test_read_basic(self, aimemory_instance, sample_scope):
        """Test basic read operation."""
        mock_messages = ["Message 1", "Message 2"]
        mock_metadata = {"total_count": 2}

        with patch.object(aimemory_instance.redis_adapter, 'read_messages') as mock_read:
            mock_read.return_value = (mock_messages, mock_metadata)

            messages, metadata = aimemory_instance.read(
                scope=sample_scope,
                channel="working"
            )

            assert messages == mock_messages
            assert metadata == mock_metadata
            mock_read.assert_called_once()

    def test_read_with_filters(self, aimemory_instance, sample_scope):
        """Test read operation with various filters."""
        with patch.object(aimemory_instance.redis_adapter, 'read_messages') as mock_read:
            mock_read.return_value = ([], {})

            aimemory_instance.read(
                scope=sample_scope,
                channel="working",
                since_sec=3600,
                max_bytes=10000,
                max_msgs=50,
                max_tokens=1000
            )

            mock_read.assert_called_once()

    def test_read_nonexistent_channel(self, aimemory_instance, sample_scope):
        """Test read from non-existent channel."""
        with pytest.raises(ChannelNotFound):
            aimemory_instance.read(
                scope=sample_scope,
                channel="nonexistent"
            )

    def test_checkpoint_basic(self, aimemory_instance, sample_scope):
        """Test basic checkpoint operation."""
        payload = {"step": "data_analysis", "progress": 0.75}

        with patch.object(aimemory_instance.redis_adapter, 'set_checkpoint') as mock_checkpoint:
            aimemory_instance.checkpoint(
                scope=sample_scope,
                key="workflow",
                payload=payload
            )

            mock_checkpoint.assert_called_once_with(sample_scope, "workflow", payload)

    def test_checkpoint_atomic(self, aimemory_instance, sample_scope):
        """Test atomic checkpoint operation."""
        def update_func(current):
            return {"step": "next", "previous": current}

        mock_result = {"step": "next", "previous": {"step": "current"}}

        with patch.object(aimemory_instance.redis_adapter, 'atomic_checkpoint') as mock_atomic:
            mock_atomic.return_value = mock_result

            result = aimemory_instance.checkpoint_atomic(
                scope=sample_scope,
                key="workflow",
                update_fn=update_func
            )

            assert result == mock_result
            mock_atomic.assert_called_once()

    def test_bulk_erase(self, aimemory_instance, sample_scope):
        """Test bulk erase operation."""
        with patch.object(aimemory_instance.redis_adapter, 'bulk_delete') as mock_delete:
            mock_delete.return_value = 15

            count = aimemory_instance.bulk_erase(scope=sample_scope)

            assert count == 15
            mock_delete.assert_called_once_with(sample_scope)

    def test_count_bytes(self, aimemory_instance, sample_scope):
        """Test count bytes operation."""
        with patch.object(aimemory_instance.redis_adapter, 'count_bytes') as mock_count:
            mock_count.return_value = 5000

            byte_count = aimemory_instance.count_bytes(
                scope=sample_scope,
                channel="working"
            )

            assert byte_count == 5000
            mock_count.assert_called_once()

    def test_count_bytes_nonexistent_channel(self, aimemory_instance, sample_scope):
        """Test count bytes for non-existent channel."""
        with pytest.raises(ChannelNotFound):
            aimemory_instance.count_bytes(
                scope=sample_scope,
                channel="nonexistent"
            )

    def test_register_channel(self, aimemory_instance):
        """Test dynamic channel registration."""
        aimemory_instance.register_channel(
            name="scratch",
            ttl_sec=60,
            encrypt=False,
            quota_bytes=500000
        )

        # Verify channel was registered
        channel = aimemory_instance.get_channel_config("scratch")
        assert channel is not None
        assert channel.name == "scratch"
        assert channel.ttl_sec == 60
        assert channel.encrypt is False
        assert channel.quota_bytes == 500000

    def test_list_channels(self, aimemory_instance):
        """Test listing all channels."""
        channels = aimemory_instance.list_channels()

        # Should have the default channels from YAML
        assert isinstance(channels, dict)
        assert len(channels) >= 3  # At least working, procedure, routing

    def test_get_channel_config_existing(self, aimemory_instance):
        """Test getting existing channel configuration."""
        config = aimemory_instance.get_channel_config("working")

        assert config is not None
        assert isinstance(config, ChannelConfig)
        assert config.name == "working"

    def test_get_channel_config_nonexistent(self, aimemory_instance):
        """Test getting non-existent channel configuration."""
        config = aimemory_instance.get_channel_config("nonexistent")
        assert config is None

    def test_write_with_metrics(self, aimemory_with_features, sample_scope):
        """Test write operation with metrics enabled."""
        content = "Test message"

        with patch.object(aimemory_with_features.redis_adapter, 'write_message') as mock_write:
            mock_write.return_value = "uuid-metrics"

            # Mock metrics
            aimemory_with_features.metrics = Mock()

            result_uuid = aimemory_with_features.write(
                scope=sample_scope,
                channel="working",
                content=content
            )

            assert result_uuid == "uuid-metrics"
            # Verify metrics were called
            assert aimemory_with_features.metrics.increment_counter.called

    def test_write_with_audit(self, aimemory_with_features, sample_scope):
        """Test write operation with audit logging enabled."""
        content = "Test message for audit"

        with patch.object(aimemory_with_features.redis_adapter, 'write_message') as mock_write:
            mock_write.return_value = "uuid-audit"

            # Mock audit sink
            aimemory_with_features.audit_sink = Mock()

            result_uuid = aimemory_with_features.write(
                scope=sample_scope,
                channel="working",
                content=content
            )

            assert result_uuid == "uuid-audit"
            # Verify audit was called
            assert aimemory_with_features.audit_sink.log_operation.called

    def test_write_bytes_content(self, aimemory_instance, sample_scope):
        """Test write operation with bytes content."""
        content = b"Binary test data"

        with patch.object(aimemory_instance.redis_adapter, 'write_message') as mock_write:
            mock_write.return_value = "uuid-bytes"

            result_uuid = aimemory_instance.write(
                scope=sample_scope,
                channel="working",
                content=content
            )

            assert result_uuid == "uuid-bytes"

    def test_error_handling_redis_failure(self, aimemory_instance, sample_scope):
        """Test error handling when Redis operations fail."""
        with patch.object(aimemory_instance.redis_adapter, 'write_message') as mock_write:
            mock_write.side_effect = Exception("Redis connection failed")

            with pytest.raises(Exception, match="Redis connection failed"):
                aimemory_instance.write(
                    scope=sample_scope,
                    channel="working",
                    content="test"
                )

    def test_policy_violation_handling(self, aimemory_instance, sample_scope):
        """Test handling of policy violations."""
        from nexamem.policy import TTLViolation

        with patch.object(aimemory_instance.policy_engine, 'check_all_policies') as mock_policy:
            mock_policy.side_effect = TTLViolation("TTL exceeds limit")

            with pytest.raises(TTLViolation):
                aimemory_instance.write(
                    scope=sample_scope,
                    channel="working",
                    content="test",
                    ttl_override=999999  # Very high TTL
                )

    def test_memory_scope_validation(self, aimemory_instance):
        """Test that invalid MemoryScope is rejected."""
        # This should be caught by Pydantic validation
        with pytest.raises(ValidationError):
            MemoryScope(agent_id="", user_id="user123")

    def test_concurrent_operations(self, aimemory_instance, sample_scope):
        """Test that concurrent operations don't interfere."""
        import threading

        results = []
        errors = []

        def write_operation(content_suffix):
            try:
                with patch.object(aimemory_instance.redis_adapter, 'write_message') as mock_write:
                    mock_write.return_value = f"uuid-{content_suffix}"
                    result = aimemory_instance.write(
                        scope=sample_scope,
                        channel="working",
                        content=f"Message {content_suffix}"
                    )
                    results.append(result)
            except Exception as e:
                errors.append(e)

        # Start multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=write_operation, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 5

    def test_large_content_handling(self, aimemory_instance, sample_scope):
        """Test handling of large content."""
        # Create large content (1MB)
        large_content = "x" * (1024 * 1024)

        with patch.object(aimemory_instance.redis_adapter, 'write_message') as mock_write:
            mock_write.return_value = "uuid-large"

            result_uuid = aimemory_instance.write(
                scope=sample_scope,
                channel="working",
                content=large_content
            )

            assert result_uuid == "uuid-large"
