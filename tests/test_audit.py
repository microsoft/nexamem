"""
Comprehensive unit tests for audit module.
Tests audit logging functionality for AIMemory operations.
"""
import json
import time
from unittest.mock import AsyncMock, Mock

import pytest

from nexamem.audit import AsyncAuditSink, AuditSink
from nexamem.memory_scope import MemoryScope


class TestAuditSink:
    """Test synchronous audit sink functionality."""

    @pytest.fixture
    def mock_redis_adapter(self):
        """Mock Redis adapter for testing."""
        mock = Mock()
        mock.redis = Mock()
        mock.redis.xadd.return_value = b'1234567890-0'
        mock.redis.xrange.return_value = []
        mock.redis.xtrim.return_value = 1
        return mock

    @pytest.fixture
    def audit_sink(self, mock_redis_adapter):
        """Audit sink with mocked Redis adapter."""
        return AuditSink(mock_redis_adapter)

    @pytest.fixture
    def sample_scope(self):
        """Sample memory scope for testing."""
        return MemoryScope(
            agent_id="test_agent",
            user_id="user123",
            session_id="session456",
            env="test"
        )

    def test_audit_sink_initialization(self, mock_redis_adapter):
        """Test audit sink initialization with defaults."""
        audit = AuditSink(mock_redis_adapter)

        assert audit.redis_adapter == mock_redis_adapter
        assert audit.stream_name == "aimemory:audit"
        assert audit.ttl_days == 365
        assert audit.enabled is True

    def test_audit_sink_initialization_custom(self, mock_redis_adapter):
        """Test audit sink initialization with custom parameters."""
        audit = AuditSink(
            mock_redis_adapter,
            stream_name="custom:audit",
            ttl_days=30,
            enabled=False
        )

        assert audit.stream_name == "custom:audit"
        assert audit.ttl_days == 30
        assert audit.enabled is False

    def test_log_operation_basic(self, audit_sink, sample_scope, mock_redis_adapter):
        """Test basic operation logging."""
        audit_sink.log_operation(
            operation="write",
            scope_dict=sample_scope.model_dump(),
            channel="working",
            metadata={"content_length": 100}
        )

        # Verify xadd was called
        mock_redis_adapter.redis.xadd.assert_called_once()
        call_args = mock_redis_adapter.redis.xadd.call_args

        # Check stream name
        assert call_args[0][0] == "aimemory:audit"

        # Check logged data
        logged_data = call_args[0][1]
        assert "operation" in logged_data
        assert "timestamp" in logged_data
        assert "scope" in logged_data
        assert "channel" in logged_data
        assert "metadata" in logged_data

        # Verify content
        assert logged_data["operation"] == "write"
        assert logged_data["channel"] == "working"

        # Verify scope is JSON serialized
        scope_data = json.loads(logged_data["scope"])
        assert scope_data["agent_id"] == "test_agent"
        assert scope_data["user_id"] == "user123"

        # Verify metadata is JSON serialized
        metadata = json.loads(logged_data["metadata"])
        assert metadata["content_length"] == 100

    def test_log_operation_with_result(self, audit_sink, sample_scope, mock_redis_adapter):
        """Test logging operation with result."""
        audit_sink.log_operation(
            operation="read",
            scope_dict=sample_scope.model_dump(),
            channel="working",
            result="success",
            metadata={"messages_returned": 5}
        )

        call_args = mock_redis_adapter.redis.xadd.call_args
        logged_data = call_args[0][1]

        assert logged_data["result"] == "success"

    def test_log_operation_disabled(self, mock_redis_adapter, sample_scope):
        """Test that disabled audit sink doesn't log."""
        audit_sink = AuditSink(mock_redis_adapter, enabled=False)

        audit_sink.log_operation(
            operation="write",
            scope_dict=sample_scope.model_dump(),
            channel="working"
        )

        # Should not call xadd when disabled
        mock_redis_adapter.redis.xadd.assert_not_called()

    def test_log_operation_redis_error(self, audit_sink, sample_scope, mock_redis_adapter):
        """Test handling Redis errors during logging."""
        mock_redis_adapter.redis.xadd.side_effect = Exception("Redis error")

        # Should not raise exception, just silently fail
        audit_sink.log_operation(
            operation="write",
            scope_dict=sample_scope.model_dump(),
            channel="working"
        )

        # Verify xadd was attempted
        mock_redis_adapter.redis.xadd.assert_called_once()

    def test_get_audit_records_basic(self, audit_sink, mock_redis_adapter):
        """Test getting audit records."""
        # Mock Redis response
        mock_records = [
            (b'1234567890-0', {
                b'operation': b'write',
                b'timestamp': b'1234567890.123',
                b'scope': b'{"agent_id": "test"}',
                b'channel': b'working'
            }),
            (b'1234567891-0', {
                b'operation': b'read',
                b'timestamp': b'1234567891.456',
                b'scope': b'{"agent_id": "test"}',
                b'channel': b'working'
            })
        ]
        mock_redis_adapter.redis.xrange.return_value = mock_records

        records = audit_sink.get_audit_records(count=10)

        assert len(records) == 2
        assert records[0]["operation"] == "write"
        assert records[0]["channel"] == "working"
        assert records[1]["operation"] == "read"

        # Verify xrange was called correctly
        mock_redis_adapter.redis.xrange.assert_called_once_with(
            "aimemory:audit", "-", "+", count=10
        )

    def test_get_audit_records_with_since(self, audit_sink, mock_redis_adapter):
        """Test getting audit records with since timestamp."""
        mock_redis_adapter.redis.xrange.return_value = []

        since_timestamp = "1234567890000-0"
        audit_sink.get_audit_records(since=since_timestamp, count=5)

        mock_redis_adapter.redis.xrange.assert_called_once_with(
            "aimemory:audit", since_timestamp, "+", count=5
        )

    def test_get_audit_records_redis_error(self, audit_sink, mock_redis_adapter):
        """Test handling Redis errors when getting records."""
        mock_redis_adapter.redis.xrange.side_effect = Exception("Redis error")

        records = audit_sink.get_audit_records()

        # Should return empty list on error
        assert records == []

    def test_get_audit_records_invalid_json(self, audit_sink, mock_redis_adapter):
        """Test handling invalid JSON in audit records."""
        mock_records = [
            (b'1234567890-0', {
                b'operation': b'write',
                b'scope': b'invalid json',  # Invalid JSON
                b'metadata': b'also invalid'
            })
        ]
        mock_redis_adapter.redis.xrange.return_value = mock_records

        records = audit_sink.get_audit_records()

        assert len(records) == 1
        # Should have operation but not parsed JSON fields
        assert records[0]["operation"] == "write"
        assert "scope" not in records[0]  # Failed to parse, so excluded
        assert "metadata" not in records[0]

    def test_cleanup_old_records(self, audit_sink, mock_redis_adapter):
        """Test cleanup of old audit records."""
        mock_redis_adapter.redis.xtrim.return_value = 100

        deleted_count = audit_sink.cleanup_old_records(max_age_days=30)

        assert deleted_count == 100
        mock_redis_adapter.redis.xtrim.assert_called_once()

    def test_cleanup_old_records_redis_error(self, audit_sink, mock_redis_adapter):
        """Test handling Redis errors during cleanup."""
        mock_redis_adapter.redis.xtrim.side_effect = Exception("Redis error")

        deleted_count = audit_sink.cleanup_old_records()

        # Should return 0 on error
        assert deleted_count == 0

    def test_enable_disable_audit(self, audit_sink, sample_scope, mock_redis_adapter):
        """Test enabling and disabling audit logging."""
        # Initially enabled
        assert audit_sink.enabled is True

        # Disable
        audit_sink.disable()
        assert audit_sink.enabled is False

        # Should not log when disabled
        audit_sink.log_operation(
            operation="write",
            scope_dict=sample_scope.model_dump(),
            channel="working"
        )
        mock_redis_adapter.redis.xadd.assert_not_called()

        # Re-enable
        audit_sink.enable()
        assert audit_sink.enabled is True

        # Should log when re-enabled
        audit_sink.log_operation(
            operation="write",
            scope_dict=sample_scope.model_dump(),
            channel="working"
        )
        mock_redis_adapter.redis.xadd.assert_called_once()

    def test_log_operation_complex_metadata(self, audit_sink, sample_scope, mock_redis_adapter):
        """Test logging with complex metadata structures."""
        complex_metadata = {
            "nested": {"key": "value", "number": 42},
            "list": [1, 2, 3],
            "boolean": True,
            "null": None
        }

        audit_sink.log_operation(
            operation="checkpoint",
            scope_dict=sample_scope.model_dump(),
            channel="workflow",
            metadata=complex_metadata
        )

        call_args = mock_redis_adapter.redis.xadd.call_args
        logged_data = call_args[0][1]

        # Verify complex metadata is properly serialized
        metadata = json.loads(logged_data["metadata"])
        assert metadata == complex_metadata

    def test_timestamp_precision(self, audit_sink, sample_scope, mock_redis_adapter):
        """Test that timestamps have sufficient precision."""
        start_time = time.time()

        audit_sink.log_operation(
            operation="write",
            scope_dict=sample_scope.model_dump(),
            channel="working"
        )

        end_time = time.time()

        call_args = mock_redis_adapter.redis.xadd.call_args
        logged_data = call_args[0][1]
        logged_timestamp = float(logged_data["timestamp"])

        # Timestamp should be within the test window
        assert start_time <= logged_timestamp <= end_time


class TestAsyncAuditSink:
    """Test asynchronous audit sink functionality."""

    @pytest.fixture
    def mock_async_redis_adapter(self):
        """Mock async Redis adapter for testing."""
        mock = Mock()
        mock.client = AsyncMock()
        mock.client.xadd.return_value = b'1234567890-0'
        mock.client.xrange.return_value = []
        mock.client.xtrim.return_value = 1
        return mock

    @pytest.fixture
    def async_audit_sink(self, mock_async_redis_adapter):
        """Async audit sink with mocked Redis adapter."""
        return AsyncAuditSink(mock_async_redis_adapter)

    @pytest.fixture
    def sample_scope(self):
        """Sample memory scope for testing."""
        return MemoryScope(
            agent_id="test_agent",
            user_id="user123",
            session_id="session456",
            env="test"
        )

    def test_async_audit_sink_initialization(self, mock_async_redis_adapter):
        """Test async audit sink initialization."""
        audit = AsyncAuditSink(mock_async_redis_adapter)

        assert audit.redis_adapter == mock_async_redis_adapter
        assert audit.stream_name == "aimemory:audit"
        assert audit.ttl_days == 365
        assert audit.enabled is True

    @pytest.mark.asyncio
    async def test_async_log_operation_basic(self, async_audit_sink, sample_scope, mock_async_redis_adapter):
        """Test basic async operation logging."""
        await async_audit_sink.log_operation(
            operation="write",
            scope_dict=sample_scope.model_dump(),
            channel="working",
            metadata={"content_length": 100}
        )

        # Verify xadd was called
        mock_async_redis_adapter.client.xadd.assert_called_once()
        call_args = mock_async_redis_adapter.client.xadd.call_args

        # Check stream name
        assert call_args[0][0] == "aimemory:audit"

        # Check logged data structure
        logged_data = call_args[0][1]
        assert "operation" in logged_data
        assert "timestamp" in logged_data
        assert "scope" in logged_data
        assert "channel" in logged_data
        assert "metadata" in logged_data

    @pytest.mark.asyncio
    async def test_async_log_operation_disabled(self, mock_async_redis_adapter, sample_scope):
        """Test that disabled async audit sink doesn't log."""
        audit_sink = AsyncAuditSink(mock_async_redis_adapter, enabled=False)

        await audit_sink.log_operation(
            operation="write",
            scope_dict=sample_scope.model_dump(),
            channel="working"
        )

        # Should not call xadd when disabled
        mock_async_redis_adapter.client.xadd.assert_not_called()

    @pytest.mark.asyncio
    async def test_async_log_operation_redis_error(self, async_audit_sink, sample_scope, mock_async_redis_adapter):
        """Test handling Redis errors during async logging."""
        mock_async_redis_adapter.client.xadd.side_effect = Exception("Redis error")

        # Should not raise exception, just silently fail
        await async_audit_sink.log_operation(
            operation="write",
            scope_dict=sample_scope.model_dump(),
            channel="working"
        )

        # Verify xadd was attempted
        mock_async_redis_adapter.client.xadd.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_get_audit_records_basic(self, async_audit_sink, mock_async_redis_adapter):
        """Test getting audit records asynchronously."""
        # Mock Redis response
        mock_records = [
            (b'1234567890-0', {
                b'operation': b'write',
                b'timestamp': b'1234567890.123',
                b'scope': b'{"agent_id": "test"}',
                b'channel': b'working'
            })
        ]
        mock_async_redis_adapter.client.xrange.return_value = mock_records

        records = await async_audit_sink.get_audit_records(count=10)

        assert len(records) == 1
        assert records[0]["operation"] == "write"
        assert records[0]["channel"] == "working"

        # Verify xrange was called correctly
        mock_async_redis_adapter.client.xrange.assert_called_once_with(
            "aimemory:audit", "-", "+", count=10
        )

    @pytest.mark.asyncio
    async def test_async_get_audit_records_redis_error(self, async_audit_sink, mock_async_redis_adapter):
        """Test handling Redis errors when getting records asynchronously."""
        mock_async_redis_adapter.client.xrange.side_effect = Exception("Redis error")

        records = await async_audit_sink.get_audit_records()

        # Should return empty list on error
        assert records == []

    @pytest.mark.asyncio
    async def test_async_cleanup_old_records(self, async_audit_sink, mock_async_redis_adapter):
        """Test async cleanup of old audit records."""
        mock_async_redis_adapter.client.xtrim.return_value = 50

        deleted_count = await async_audit_sink.cleanup_old_records(max_age_days=7)

        assert deleted_count == 50
        mock_async_redis_adapter.client.xtrim.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_cleanup_old_records_redis_error(self, async_audit_sink, mock_async_redis_adapter):
        """Test handling Redis errors during async cleanup."""
        mock_async_redis_adapter.client.xtrim.side_effect = Exception("Redis error")

        deleted_count = await async_audit_sink.cleanup_old_records()

        # Should return 0 on error
        assert deleted_count == 0

    @pytest.mark.asyncio
    async def test_async_enable_disable_audit(self, async_audit_sink, sample_scope, mock_async_redis_adapter):
        """Test enabling and disabling async audit logging."""
        # Initially enabled
        assert async_audit_sink.enabled is True

        # Disable
        async_audit_sink.disable()
        assert async_audit_sink.enabled is False

        # Should not log when disabled
        await async_audit_sink.log_operation(
            operation="write",
            scope_dict=sample_scope.model_dump(),
            channel="working"
        )
        mock_async_redis_adapter.client.xadd.assert_not_called()

        # Re-enable
        async_audit_sink.enable()
        assert async_audit_sink.enabled is True

        # Should log when re-enabled
        await async_audit_sink.log_operation(
            operation="write",
            scope_dict=sample_scope.model_dump(),
            channel="working"
        )
        mock_async_redis_adapter.client.xadd.assert_called_once()


class TestAuditIntegration:
    """Integration tests for audit functionality."""

    def test_audit_sink_with_real_data_flow(self):
        """Test audit sink with realistic data flow."""
        mock_redis_adapter = Mock()
        mock_redis_adapter.redis = Mock()
        mock_redis_adapter.redis.xadd.return_value = b'1234567890-0'

        audit = AuditSink(mock_redis_adapter)

        # Simulate a realistic AIMemory operation sequence
        scope = MemoryScope(
            agent_id="chatbot_v2",
            user_id="customer_456",
            session_id="conv_789",
            env="production"
        )

        # Write operation
        audit.log_operation(
            operation="write",
            scope_dict=scope.model_dump(),
            channel="working",
            result="success",
            metadata={
                "content_length": 256,
                "ttl_sec": 3600,
                "pii_detected": False
            }
        )

        # Read operation
        audit.log_operation(
            operation="read",
            scope_dict=scope.model_dump(),
            channel="working",
            result="success",
            metadata={
                "messages_returned": 5,
                "total_bytes": 1024,
                "since_sec": 300
            }
        )

        # Checkpoint operation
        audit.log_operation(
            operation="checkpoint",
            scope_dict=scope.model_dump(),
            channel="workflow",
            result="success",
            metadata={
                "checkpoint_key": "conversation_state",
                "payload_size": 128
            }
        )

        # Verify all operations were logged
        assert mock_redis_adapter.redis.xadd.call_count == 3

        # Verify each call had the expected stream name
        for call in mock_redis_adapter.redis.xadd.call_args_list:
            assert call[0][0] == "aimemory:audit"

    def test_audit_error_scenarios(self):
        """Test audit behavior in various error scenarios."""
        mock_redis_adapter = Mock()
        audit = AuditSink(mock_redis_adapter)

        scope = MemoryScope(
            agent_id="test",
            user_id="test",
            session_id="test",
            env="test"
        )

        # Test with missing Redis client
        mock_redis_adapter.redis = None
        audit.log_operation(
            operation="write",
            scope_dict=scope.model_dump(),
            channel="working"
        )
        # Should not raise exception

        # Test with Redis connection error
        mock_redis_adapter.redis = Mock()
        mock_redis_adapter.redis.xadd.side_effect = ConnectionError("Redis unavailable")
        audit.log_operation(
            operation="write",
            scope_dict=scope.model_dump(),
            channel="working"
        )
        # Should not raise exception

    def test_audit_serialization_edge_cases(self):
        """Test audit serialization with edge cases."""
        mock_redis_adapter = Mock()
        mock_redis_adapter.redis = Mock()
        mock_redis_adapter.redis.xadd.return_value = b'1234567890-0'

        audit = AuditSink(mock_redis_adapter)

        scope = MemoryScope(
            agent_id="test",
            user_id="test",
            session_id="test",
            env="test"
        )

        # Test with None metadata
        audit.log_operation(
            operation="write",
            scope_dict=scope.model_dump(),
            channel="working",
            metadata=None
        )

        # Test with empty metadata
        audit.log_operation(
            operation="write",
            scope_dict=scope.model_dump(),
            channel="working",
            metadata={}
        )

        # Test with large metadata
        large_metadata = {
            "large_data": "x" * 10000,  # 10KB string
            "nested": {"level1": {"level2": {"level3": "deep"}}}
        }
        audit.log_operation(
            operation="write",
            scope_dict=scope.model_dump(),
            channel="working",
            metadata=large_metadata
        )

        # All should complete without errors
        assert mock_redis_adapter.redis.xadd.call_count == 3
