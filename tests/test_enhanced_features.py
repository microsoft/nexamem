"""
Test the enhanced AIMemory functionality against requirements.
"""
import tempfile
import os

# Import from the local source
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from nexamem import (
    AIMemory, MemoryScope, PIIRedactor,
    ContentEnricher, metrics
)


def create_test_channels_yaml():
    """Create test channels configuration."""
    channels_config = """
channels:
  working:
    ttl_sec: 14400
    encrypt: true
    quota_bytes: 1000000
  procedure:
    ttl_sec: 604800
    encrypt: true
  routing:
    ttl_sec: 86400
    encrypt: false
"""
    
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False)
    temp_file.write(channels_config)
    temp_file.close()
    return temp_file.name


def test_enhanced_aimemory_features():
    """Test enhanced AIMemory features."""
    channels_yaml = create_test_channels_yaml()
    
    try:
        # Initialize with enhanced features
        memory = AIMemory(
            channels_yaml=channels_yaml,
            use_fakeredis=True,
            enable_audit=True,
            enable_metrics=True,
            enable_content_processing=True
        )
        
        # Test MemoryScope format
        scope = MemoryScope(
            agent_id="invest_agent",
            user_id="u12345",
            session_id="s98765",
            env="prod"
        )
        
        # Verify key format
        key_prefix = scope.get_key_prefix("working")
        assert key_prefix == "prod:invest_agent:u12345:s98765:working"
        
        # Test content processing
        if memory.content_processor:
            memory.content_processor.add_processor(PIIRedactor())
            memory.content_processor.add_processor(ContentEnricher())
        
        # Test write with PII auto-detection
        pii_content = "Customer email: john@example.com"
        message_uuid = memory.write(
            scope=scope,
            channel="working",
            content=pii_content,
            auto_pii=True
        )
        
        assert message_uuid is not None
        assert len(message_uuid) > 0
        
        # Test read
        messages, metadata = memory.read(scope=scope, channel="working")
        assert len(messages) == 1
        
        # Test dynamic channel registration
        memory.register_channel(
            name="scratch",
            ttl_sec=60,
            encrypt=False,
            quota_bytes=1000
        )
        
        # Use the new channel
        scratch_uuid = memory.write(
            scope=scope,
            channel="scratch",
            content="Test scratch content"
        )
        assert scratch_uuid is not None
        
        # Test checkpoint operations
        memory.checkpoint(scope, "test_key", {"status": "test"})
        
        def update_fn(current):
            return {"status": "updated", "previous": current}
        
        updated = memory.checkpoint_atomic(scope, "test_key", update_fn)
        assert updated["status"] == "updated"
        assert updated["previous"]["status"] == "test"
        
        # Test metrics collection
        metrics_data = metrics.get_metrics().get_all_metrics()
        assert "counters" in metrics_data
        assert len(metrics_data["counters"]) > 0
        
        # Test audit functionality
        if memory.audit:
            assert memory.audit.enabled
        
        # Test bulk operations
        byte_count = memory.count_bytes(scope, "working")
        assert byte_count >= 0
        
        deleted_count = memory.bulk_erase(scope)
        assert deleted_count >= 0
        
        print("✅ All enhanced features tested successfully!")
        
    finally:
        if os.path.exists(channels_yaml):
            os.unlink(channels_yaml)


def test_requirements_compliance():
    """Test compliance with specific requirements."""
    channels_yaml = create_test_channels_yaml()
    
    try:
        memory = AIMemory(
            channels_yaml=channels_yaml,
            use_fakeredis=True
        )
        
        # Test MemoryScope with env field (requirement 4.1)
        scope = MemoryScope(
            agent_id="invest_agent",
            user_id="u12345",
            session_id="s98765",
            env="prod"  # defaults to "prod"
        )
        assert scope.env == "prod"
        
        # Test key format (requirement 4.2)
        key_prefix = scope.get_key_prefix("working")
        assert key_prefix == "prod:invest_agent:u12345:s98765:working"
        
        index_key = scope.get_index_key("working")
        assert index_key == "prod:invest_agent:u12345:s98765:working:index"
        
        # Test channel configuration matches requirements examples
        working_config = memory.get_channel_config("working")
        assert working_config.ttl_sec == 14400  # 4 hours
        assert working_config.encrypt
        
        routing_config = memory.get_channel_config("routing")
        assert routing_config.ttl_sec == 86400  # 24 hours
        assert not routing_config.encrypt
        
        procedure_config = memory.get_channel_config("procedure")
        assert procedure_config.ttl_sec == 604800  # 7 days
        assert procedure_config.encrypt
        
        # Test dynamic channel registration (requirement 7.1)
        memory.register_channel(
            name="scratch",
            ttl_sec=60,  # 1 minute
            encrypt=False,
            quota_bytes=1_000_000  # 1MB
        )
        
        scratch_config = memory.get_channel_config("scratch")
        assert scratch_config.name == "scratch"
        assert scratch_config.ttl_sec == 60
        assert not scratch_config.encrypt
        assert scratch_config.quota_bytes == 1_000_000
        
        print("✅ Requirements compliance verified!")
        
    finally:
        if os.path.exists(channels_yaml):
            os.unlink(channels_yaml)


if __name__ == "__main__":
    test_enhanced_aimemory_features()
    test_requirements_compliance()
    print("🎯 All tests passed! Enhanced AIMemory is requirements-compliant.")
