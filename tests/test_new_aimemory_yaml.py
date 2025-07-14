"""Tests for new AIMemory YAML channel configuration support."""

import tempfile
import os
import pytest

from nexamem import AIMemory, AIMemoryConfig, AsyncAIMemory, StorageConfig, MemoryScope
from nexamem.channels import ChannelAlreadyExists


class TestNewAIMemoryYAMLSupport:
    """Test YAML channel configuration support in new AIMemory."""

    def create_test_yaml(self) -> str:
        """Create a temporary YAML file for testing."""
        yaml_content = """
channels:
  working:
    ttl_sec: 14400
    encrypt: true
    quota_bytes: 1000000

  routing:
    ttl_sec: 86400
    encrypt: false
"""
        f = tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False)
        f.write(yaml_content)
        f.close()
        return f.name

    def test_aimemory_yaml_loading(self):
        """Test that AIMemory can load YAML configuration."""
        yaml_path = self.create_test_yaml()
        
        try:
            config = AIMemoryConfig(
                default_scope="test",
                storage=StorageConfig.memory(),
                channels_yaml=yaml_path,
                strict_yaml_validation=True
            )
            
            memory = AIMemory(config)
            
            # Verify channels were loaded
            channels = memory.list_channels()
            assert len(channels) == 2
            assert "working" in channels
            assert "routing" in channels
            
            # Verify channel details
            working = memory.get_channel("working")
            assert working.ttl_sec == 14400
            assert working.encrypt is True
            assert working.quota_bytes == 1000000
            
            routing = memory.get_channel("routing")
            assert routing.ttl_sec == 86400
            assert routing.encrypt is False
            assert routing.quota_bytes is None
            
        finally:
            os.unlink(yaml_path)

    @pytest.mark.asyncio
    async def test_async_aimemory_yaml_loading(self):
        """Test that AsyncAIMemory can load YAML configuration."""
        yaml_path = self.create_test_yaml()
        
        try:
            config = AIMemoryConfig(
                default_scope="test",
                storage=StorageConfig.memory(),
                channels_yaml=yaml_path,
                strict_yaml_validation=True
            )
            
            memory = AsyncAIMemory(config)
            
            # Verify channels were loaded
            channels = memory.list_channels()
            assert len(channels) == 2
            assert memory.channel_exists("working")
            assert memory.channel_exists("routing")
            
        finally:
            os.unlink(yaml_path)

    def test_dynamic_channel_registration(self):
        """Test dynamic channel registration."""
        config = AIMemoryConfig(
            default_scope="test",
            storage=StorageConfig.memory()
        )
        
        memory = AIMemory(config)
        
        # Initially no channels
        assert len(memory.list_channels()) == 0
        
        # Register a channel
        memory.register_channel(
            name="test_channel",
            ttl_sec=3600,
            encrypt=True,
            quota_bytes=500000
        )
        
        # Verify it exists
        assert memory.channel_exists("test_channel")
        channel = memory.get_channel("test_channel")
        assert channel.ttl_sec == 3600
        assert channel.encrypt is True
        assert channel.quota_bytes == 500000
        
        # Test duplicate registration fails
        with pytest.raises(ChannelAlreadyExists):
            memory.register_channel(
                name="test_channel",
                ttl_sec=7200,
                encrypt=False
            )

    def test_legacy_api_compatibility(self):
        """Test legacy write/read API compatibility."""
        yaml_path = self.create_test_yaml()
        
        try:
            config = AIMemoryConfig(
                default_scope="test",
                storage=StorageConfig.memory(),
                channels_yaml=yaml_path
            )
            
            memory = AIMemory(config)
            
            scope = MemoryScope(
                agent_id="test_agent",
                user_id="test_user",
                session_id="test_session",
                env="test"
            )
            
            # Test write
            message_id = memory.write(
                scope=scope,
                channel="working",
                content="Test message",
                pii=False
            )
            
            assert message_id is not None
            assert isinstance(message_id, str)
            
            # Test read
            messages, metadata = memory.read(
                scope=scope,
                channel="working",
                max_msgs=10
            )
            
            assert len(messages) == 1
            assert messages[0] == "Test message"
            assert metadata["channel"] == "working"
            assert metadata["messages_returned"] == 1
            
        finally:
            os.unlink(yaml_path)

    @pytest.mark.asyncio
    async def test_async_legacy_api_compatibility(self):
        """Test async legacy write/read API compatibility."""
        yaml_path = self.create_test_yaml()
        
        try:
            config = AIMemoryConfig(
                default_scope="test",
                storage=StorageConfig.memory(),
                channels_yaml=yaml_path
            )
            
            memory = AsyncAIMemory(config)
            
            scope = MemoryScope(
                agent_id="test_agent",
                user_id="test_user",
                session_id="test_session",
                env="test"
            )
            
            # Test async write
            message_id = await memory.write(
                scope=scope,
                channel="working",
                content="Async test message",
                pii=False
            )
            
            assert message_id is not None
            
            # Test async read
            messages, metadata = await memory.read(
                scope=scope,
                channel="working",
                max_msgs=10
            )
            
            assert len(messages) == 1
            assert messages[0] == "Async test message"
            
        finally:
            os.unlink(yaml_path)

    def test_channel_not_found_error(self):
        """Test that using non-existent channel raises error."""
        config = AIMemoryConfig(
            default_scope="test",
            storage=StorageConfig.memory()
        )
        
        memory = AIMemory(config)
        scope = MemoryScope(
            agent_id="test_agent",
            user_id="test_user",
            session_id="test_session",
            env="test"
        )
        
        # Should raise ChannelNotFound for non-existent channel
        from nexamem.aimemory import ChannelNotFound
        with pytest.raises(ChannelNotFound):
            memory.write(
                scope=scope,
                channel="nonexistent",
                content="Test message"
            )

    def test_config_from_env(self):
        """Test creating AIMemoryConfig from environment variables."""
        # Set environment variables
        os.environ['NEXAMEM_DEFAULT_SCOPE'] = 'env_test'
        os.environ['NEXAMEM_STORAGE_TYPE'] = 'memory'
        os.environ['NEXAMEM_STRICT_YAML_VALIDATION'] = 'false'
        os.environ['NEXAMEM_ENABLE_AUDIT'] = 'false'
        
        try:
            config = AIMemoryConfig.from_env()
            
            assert config.default_scope == 'env_test'
            assert config.storage.type.value == 'memory'
            assert config.strict_yaml_validation is False
            assert config.enable_audit is False
            
            # Test creating AIMemory with env config
            memory = AIMemory(config)
            assert memory.config.default_scope == 'env_test'
            
        finally:
            # Clean up environment variables
            for key in ['NEXAMEM_DEFAULT_SCOPE', 'NEXAMEM_STORAGE_TYPE', 
                       'NEXAMEM_STRICT_YAML_VALIDATION', 'NEXAMEM_ENABLE_AUDIT']:
                os.environ.pop(key, None)

    def test_mixed_api_usage(self):
        """Test using both new DI API and legacy API together."""
        yaml_path = self.create_test_yaml()
        
        try:
            config = AIMemoryConfig(
                default_scope="mixed_test",
                storage=StorageConfig.memory(),
                channels_yaml=yaml_path
            )
            
            memory = AIMemory(config)
            
            # Use new API
            new_memory_id = memory.store(
                content="New API content",
                metadata={"source": "new_api"}
            )
            
            # Use legacy API
            scope = MemoryScope(
                agent_id="test",
                user_id="user",
                session_id="session",
                env="test"
            )
            
            legacy_memory_id = memory.write(
                scope=scope,
                channel="working",
                content="Legacy API content"
            )
            
            # Verify both work
            new_retrieved = memory.retrieve(new_memory_id)
            assert new_retrieved["content"] == "New API content"
            assert new_retrieved["metadata"]["source"] == "new_api"
            
            legacy_messages, _ = memory.read(scope=scope, channel="working")
            assert len(legacy_messages) == 1
            assert legacy_messages[0] == "Legacy API content"
            
        finally:
            os.unlink(yaml_path)
