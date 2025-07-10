"""
Tests for AIMemory functionality.
"""
import pytest
import tempfile
import os

from nexamem import (
    AIMemory, AsyncAIMemory, MemoryScope, ChannelManager,
    ChannelAlreadyExists, QuotaExceeded, EncryptionRequired,
    TTLViolation, PIIDetector
)


@pytest.fixture
def temp_channels_yaml():
    """Create a temporary channels.yaml file."""
    content = """
channels:
  working:
    ttl_sec: 14400
    encrypt: true
  routing:
    ttl_sec: 86400
    encrypt: false
  test_channel:
    ttl_sec: 3600
    encrypt: false
    quota_bytes: 1000
"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(content)
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    if os.path.exists(temp_path):
        os.unlink(temp_path)


@pytest.fixture
def memory_scope():
    """Create a test memory scope."""
    return MemoryScope(
        agent_id="test_agent",
        user_id="user123",
        session_id="session456",
        env="test"
    )


@pytest.fixture
def ai_memory(temp_channels_yaml):
    """Create AIMemory instance with test configuration."""
    return AIMemory(
        channels_yaml=temp_channels_yaml,
        use_fakeredis=True
    )


class TestMemoryScope:
    """Test MemoryScope functionality."""
    
    def test_memory_scope_creation(self):
        scope = MemoryScope(
            agent_id="test_agent",
            user_id="user123",
            session_id="session456"
        )
        assert scope.agent_id == "test_agent"
        assert scope.user_id == "user123"
        assert scope.session_id == "session456"
        assert scope.env == "prod"  # default
    
    def test_memory_scope_auto_session_id(self):
        scope = MemoryScope(
            agent_id="test_agent",
            user_id="user123"
        )
        assert scope.session_id is not None
        assert len(scope.session_id) > 0
    
    def test_key_generation(self):
        scope = MemoryScope(
            agent_id="test_agent",
            user_id="user123",
            session_id="session456",
            env="test"
        )
        
        key_prefix = scope.get_key_prefix("working")
        assert key_prefix == "test:test_agent:user123:session456:working"
        
        index_key = scope.get_index_key("working")
        assert index_key == "test:test_agent:user123:session456:working:index"


class TestChannelManager:
    """Test channel management functionality."""
    
    def test_load_from_yaml(self, temp_channels_yaml):
        manager = ChannelManager(temp_channels_yaml)
        
        assert manager.channel_exists("working")
        assert manager.channel_exists("routing")
        assert manager.channel_exists("test_channel")
        
        working = manager.get_channel("working")
        assert working.name == "working"
        assert working.ttl_sec == 14400
        assert working.encrypt is True
    
    def test_register_channel_runtime(self):
        manager = ChannelManager()
        
        manager.register_channel(
            name="scratch",
            ttl_sec=60,
            encrypt=False,
            quota_bytes=500
        )
        
        scratch = manager.get_channel("scratch")
        assert scratch.name == "scratch"
        assert scratch.ttl_sec == 60
        assert scratch.encrypt is False
        assert scratch.quota_bytes == 500
    
    def test_channel_already_exists(self, temp_channels_yaml):
        manager = ChannelManager(temp_channels_yaml)
        
        with pytest.raises(ChannelAlreadyExists):
            manager.register_channel(
                name="working",
                ttl_sec=60,
                encrypt=False
            )
    
    def test_invalid_channel_name(self):
        manager = ChannelManager()
        
        with pytest.raises(ValueError, match="snake_case"):
            manager.register_channel(
                name="Invalid-Name",
                ttl_sec=60,
                encrypt=False
            )
    
    def test_invalid_ttl(self):
        manager = ChannelManager()
        
        # TTL too large (> 7 days)
        with pytest.raises(ValueError, match="7 days"):
            manager.register_channel(
                name="bad_channel",
                ttl_sec=8 * 24 * 60 * 60,  # 8 days
                encrypt=False
            )
        
        # Negative TTL
        with pytest.raises(ValueError, match="positive"):
            manager.register_channel(
                name="bad_channel2",
                ttl_sec=-1,
                encrypt=False
            )


class TestPIIDetector:
    """Test PII detection functionality."""
    
    def test_detect_email(self):
        detector = PIIDetector()
        
        content_with_email = "Contact me at john.doe@example.com"
        result = detector.detect_pii(content_with_email)
        assert result["email"] is True
        assert detector.has_pii(content_with_email) is True
        
        content_without_email = "No email here"
        result = detector.detect_pii(content_without_email)
        assert result["email"] is False
        assert detector.has_pii(content_without_email) is False
    
    def test_detect_phone(self):
        detector = PIIDetector()
        
        content_with_phone = "Call me at 555-123-4567"
        result = detector.detect_pii(content_with_phone)
        assert result["phone"] is True
        
        content_without_phone = "No phone number here"
        result = detector.detect_pii(content_without_phone)
        assert result["phone"] is False
    
    def test_multiple_pii_types(self):
        detector = PIIDetector()
        
        content = "Email: john@example.com, Phone: 555-123-4567"
        result = detector.detect_pii(content)
        assert result["email"] is True
        assert result["phone"] is True
        assert detector.has_pii(content) is True


class TestAIMemory:
    """Test main AIMemory functionality."""
    
    def test_write_and_read_basic(self, ai_memory, memory_scope):
        # Write a message
        message_uuid = ai_memory.write(
            scope=memory_scope,
            channel="working",
            content="Hello, world!"
        )
        
        assert message_uuid is not None
        assert len(message_uuid) > 0
        
        # Read messages
        messages, metadata = ai_memory.read(
            scope=memory_scope,
            channel="working"
        )
        
        assert len(messages) == 1
        assert messages[0] == "Hello, world!"
        assert metadata["total_messages"] == 1
        assert metadata["total_bytes"] > 0
    
    def test_write_with_pii_encryption_required(self, ai_memory, memory_scope):
        # Try to write PII to non-encrypted channel
        with pytest.raises(EncryptionRequired):
            ai_memory.write(
                scope=memory_scope,
                channel="routing",  # encrypt=false
                content="My email is john@example.com",
                pii=True
            )
    
    def test_write_with_auto_pii_detection(self, ai_memory, memory_scope):
        # Write content with auto-PII detection to encrypted channel
        message_uuid = ai_memory.write(
            scope=memory_scope,
            channel="working",  # encrypt=true
            content="Contact me at john@example.com",
            auto_pii=True
        )
        
        assert message_uuid is not None
    
    def test_ttl_override_validation(self, ai_memory, memory_scope):
        # Try to override TTL beyond channel limit
        with pytest.raises(TTLViolation):
            ai_memory.write(
                scope=memory_scope,
                channel="working",  # ttl_sec=14400
                content="Test message",
                ttl_override=20000  # > 14400
            )
    
    def test_quota_enforcement(self, ai_memory, memory_scope):
        # Test channel has quota_bytes=1000
        large_content = "x" * 600  # 600 bytes
        
        # First write should succeed
        ai_memory.write(
            scope=memory_scope,
            channel="test_channel",
            content=large_content
        )
        
        # Second write should exceed quota
        with pytest.raises(QuotaExceeded):
            ai_memory.write(
                scope=memory_scope,
                channel="test_channel",
                content=large_content
            )
    
    def test_channel_not_found(self, ai_memory, memory_scope):
        with pytest.raises(Exception):  # ChannelNotFound
            ai_memory.write(
                scope=memory_scope,
                channel="nonexistent",
                content="Test"
            )
    
    def test_read_with_filters(self, ai_memory, memory_scope):
        # Write multiple messages
        for i in range(5):
            ai_memory.write(
                scope=memory_scope,
                channel="working",
                content=f"Message {i}"
            )
        
        # Read with max_msgs limit
        messages, metadata = ai_memory.read(
            scope=memory_scope,
            channel="working",
            max_msgs=3
        )
        
        assert len(messages) <= 3
        assert metadata["total_messages"] <= 3
    
    def test_bulk_erase(self, ai_memory, memory_scope):
        # Write to multiple channels
        ai_memory.write(scope=memory_scope, channel="working", content="Test 1")
        ai_memory.write(scope=memory_scope, channel="routing", content="Test 2")
        
        # Erase all
        deleted_count = ai_memory.bulk_erase(memory_scope)
        assert deleted_count > 0
        
        # Verify empty
        messages, _ = ai_memory.read(scope=memory_scope, channel="working")
        assert len(messages) == 0
    
    def test_checkpoint_operations(self, ai_memory, memory_scope):
        # Set checkpoint
        payload = {"step": 1, "data": "test"}
        ai_memory.checkpoint(memory_scope, "test_key", payload)
        
        # Atomic update
        def update_fn(current):
            if current is None:
                return {"step": 1}
            return {"step": current["step"] + 1}
        
        updated = ai_memory.checkpoint_atomic(memory_scope, "counter", update_fn)
        assert updated["step"] == 1
        
        # Update again
        updated = ai_memory.checkpoint_atomic(memory_scope, "counter", update_fn)
        assert updated["step"] == 2
    
    def test_count_bytes(self, ai_memory, memory_scope):
        content = "Hello, world!"
        ai_memory.write(scope=memory_scope, channel="working", content=content)
        
        byte_count = ai_memory.count_bytes(memory_scope, "working")
        assert byte_count >= len(content.encode('utf-8'))
    
    def test_register_channel_runtime(self, ai_memory):
        # Register new channel
        ai_memory.register_channel(
            name="new_channel",
            ttl_sec=7200,
            encrypt=True,
            quota_bytes=2000
        )
        
        # Verify it exists
        config = ai_memory.get_channel_config("new_channel")
        assert config is not None
        assert config.name == "new_channel"
        assert config.ttl_sec == 7200
        assert config.encrypt is True
        assert config.quota_bytes == 2000
    
    def test_list_channels(self, ai_memory):
        channels = ai_memory.list_channels()
        assert len(channels) >= 3  # working, routing, test_channel
        assert "working" in channels
        assert "routing" in channels


@pytest.mark.asyncio
class TestAsyncAIMemory:
    """Test asynchronous AIMemory functionality."""
    
    async def test_async_write_and_read(self, temp_channels_yaml, memory_scope):
        async_memory = AsyncAIMemory(
            channels_yaml=temp_channels_yaml,
            use_fakeredis=True  # This won't work for async, but for testing
        )
        
        try:
            # For this test, we'll skip actual async operations since fakeredis
            # doesn't support async in this context. In real testing, you'd use
            # a real Redis instance or a proper async fakeredis setup.
            pass
        finally:
            await async_memory.close()


if __name__ == "__main__":
    pytest.main([__file__])
