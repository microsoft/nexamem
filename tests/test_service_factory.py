"""Tests for the service factory and integration patterns."""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock

from nexamem import (
    MemoryServiceFactory, 
    ConversationMemoryAdapter,
    create_conversation_memory,
    create_from_environment,
    AIMemoryConfig,
    StorageConfig
)


class TestMemoryServiceFactory:
    """Test the MemoryServiceFactory."""
    
    def test_create_conversation_memory_with_memory_backend(self):
        """Test creating conversation memory with in-memory backend."""
        memory_service = MemoryServiceFactory.create_conversation_memory(
            service_type="memory",
            config={"default_scope": "test_factory"},
            async_preferred=True
        )
        
        assert isinstance(memory_service, ConversationMemoryAdapter)
        assert memory_service._is_async is True
    
    def test_create_conversation_memory_sync(self):
        """Test creating synchronous conversation memory."""
        memory_service = MemoryServiceFactory.create_conversation_memory(
            service_type="memory",
            config={"default_scope": "test_factory"},
            async_preferred=False
        )
        
        assert isinstance(memory_service, ConversationMemoryAdapter)
        assert memory_service._is_async is False
    
    def test_create_with_azure_redis_config(self):
        """Test creating conversation memory with Azure Redis configuration."""
        memory_service = MemoryServiceFactory.create_conversation_memory(
            service_type="azure_redis",
            config={
                "default_scope": "test_redis",
                "redis_hostname": "test.redis.cache.windows.net",
                "redis_access_key": "test_key",
                "redis_port": 6380,
                "redis_ssl": True
            },
            async_preferred=True
        )
        
        assert isinstance(memory_service, ConversationMemoryAdapter)
    
    def test_create_with_file_backend(self):
        """Test creating conversation memory with file backend."""
        memory_service = MemoryServiceFactory.create_conversation_memory(
            service_type="file",
            config={
                "default_scope": "test_file",
                "file_path": "/tmp/test_nexamem"
            },
            async_preferred=True
        )
        
        assert isinstance(memory_service, ConversationMemoryAdapter)
    
    def test_create_with_sqlite_backend(self):
        """Test creating conversation memory with SQLite backend."""
        memory_service = MemoryServiceFactory.create_conversation_memory(
            service_type="sqlite",
            config={
                "default_scope": "test_sqlite",
                "sqlite_path": "/tmp/test_nexamem.db"
            },
            async_preferred=True
        )
        
        assert isinstance(memory_service, ConversationMemoryAdapter)
    
    def test_create_ai_memory_direct(self):
        """Test creating AIMemory directly."""
        from nexamem import AsyncAIMemory, AIMemory
        
        ai_memory = MemoryServiceFactory.create_ai_memory(
            service_type="memory",
            config={"default_scope": "test_direct"},
            async_preferred=True
        )
        
        assert isinstance(ai_memory, AsyncAIMemory)
        
        ai_memory_sync = MemoryServiceFactory.create_ai_memory(
            service_type="memory",
            config={"default_scope": "test_direct"},
            async_preferred=False
        )
        
        assert isinstance(ai_memory_sync, AIMemory)
    
    def test_invalid_service_type(self):
        """Test that invalid service type raises error."""
        with pytest.raises(ValueError, match="Unknown service type"):
            MemoryServiceFactory.create_conversation_memory(
                service_type="invalid_type"
            )
    
    def test_missing_redis_config(self):
        """Test that missing Redis config raises error."""
        with pytest.raises(ValueError, match="redis_hostname required"):
            MemoryServiceFactory.create_conversation_memory(
                service_type="azure_redis",
                config={"default_scope": "test"}
            )


class TestConversationMemoryAdapter:
    """Test the ConversationMemoryAdapter."""
    
    @pytest.fixture
    def memory_service(self):
        """Create a memory service for testing."""
        return create_conversation_memory(
            service_type="memory",
            config={"default_scope": "test_adapter"},
            async_preferred=True
        )
    
    @pytest.mark.asyncio
    async def test_store_and_retrieve_turn(self, memory_service):
        """Test storing and retrieving conversation turns."""
        # Store a turn
        turn_id = await memory_service.store_turn(
            conversation_id="test_conversation",
            content="Hello, how can I help you?",
            metadata={"user_id": "user123", "turn_type": "assistant"}
        )
        
        assert turn_id is not None
        assert isinstance(turn_id, str)
        
        # Get history
        history = await memory_service.get_history(
            conversation_id="test_conversation",
            limit=10
        )
        
        assert len(history) == 1
        assert history[0]["content"] == "Hello, how can I help you?"
        assert history[0]["metadata"]["user_id"] == "user123"
        assert history[0]["metadata"]["conversation_id"] == "test_conversation"
    
    @pytest.mark.asyncio
    async def test_multiple_turns(self, memory_service):
        """Test storing multiple conversation turns."""
        conversation_id = "multi_turn_test"
        
        # Store multiple turns
        turn1 = await memory_service.store_turn(
            conversation_id=conversation_id,
            content="What is Python?",
            metadata={"turn_type": "user", "user_id": "user456"}
        )
        
        turn2 = await memory_service.store_turn(
            conversation_id=conversation_id,
            content="Python is a programming language.",
            metadata={"turn_type": "assistant"}
        )
        
        turn3 = await memory_service.store_turn(
            conversation_id=conversation_id,
            content="Can you give me an example?",
            metadata={"turn_type": "user", "user_id": "user456"}
        )
        
        # Get history
        history = await memory_service.get_history(
            conversation_id=conversation_id,
            limit=10
        )
        
        assert len(history) == 3
        
        # Check that we can limit results
        limited_history = await memory_service.get_history(
            conversation_id=conversation_id,
            limit=2
        )
        
        assert len(limited_history) == 2
    
    @pytest.mark.asyncio
    async def test_search_conversations(self, memory_service):
        """Test searching across conversations."""
        # Store turns in different conversations
        await memory_service.store_turn(
            conversation_id="conv1",
            content="I need help with Python programming",
            metadata={"topic": "programming"}
        )
        
        await memory_service.store_turn(
            conversation_id="conv2", 
            content="What is machine learning?",
            metadata={"topic": "ml"}
        )
        
        await memory_service.store_turn(
            conversation_id="conv3",
            content="Python is great for data science",
            metadata={"topic": "data"}
        )
        
        # Search for Python-related conversations
        results = await memory_service.search_conversations(
            query="Python",
            limit=5
        )
        
        # Note: Search results depend on the storage implementation
        # In-memory storage may not implement full-text search
        assert isinstance(results, list)
    
    @pytest.mark.asyncio
    async def test_empty_conversation(self, memory_service):
        """Test getting history for non-existent conversation."""
        history = await memory_service.get_history(
            conversation_id="nonexistent",
            limit=10
        )
        
        assert history == []


class TestConvenienceFunctions:
    """Test the convenience functions."""
    
    def test_create_conversation_memory_function(self):
        """Test the create_conversation_memory convenience function."""
        memory_service = create_conversation_memory(
            service_type="memory",
            config={"default_scope": "convenience_test"},
            async_preferred=True
        )
        
        assert isinstance(memory_service, ConversationMemoryAdapter)
    
    def test_create_from_environment_function(self, monkeypatch):
        """Test creating from environment variables."""
        # Set environment variables
        monkeypatch.setenv("NEXAMEM_SERVICE_TYPE", "memory")
        monkeypatch.setenv("NEXAMEM_DEFAULT_SCOPE", "env_test")
        
        memory_service = create_from_environment(async_preferred=True)
        
        assert isinstance(memory_service, ConversationMemoryAdapter)


class TestIntegrationPatterns:
    """Test integration patterns for external projects."""
    
    @pytest.mark.asyncio
    async def test_flask_integration_pattern(self):
        """Test a Flask-like integration pattern."""
        # Simulate Flask app initialization
        memory_service = create_conversation_memory(
            service_type="memory",
            config={"default_scope": "flask_app"},
            async_preferred=True
        )
        
        # Simulate request handling
        conversation_id = "flask_conversation"
        
        # Store user message
        user_turn = await memory_service.store_turn(
            conversation_id=conversation_id,
            content="Hello from Flask!",
            metadata={"user_id": "flask_user", "turn_type": "user"}
        )
        
        # Store assistant response
        assistant_turn = await memory_service.store_turn(
            conversation_id=conversation_id,
            content="Hello! How can I help you?",
            metadata={"turn_type": "assistant"}
        )
        
        # Get conversation history
        history = await memory_service.get_history(conversation_id, limit=10)
        
        assert len(history) == 2
        assert any(turn["content"] == "Hello from Flask!" for turn in history)
        assert any(turn["content"] == "Hello! How can I help you?" for turn in history)
    
    @pytest.mark.asyncio
    async def test_chatbot_integration_pattern(self):
        """Test a chatbot-like integration pattern."""
        # Create memory service for a chatbot
        memory_service = create_conversation_memory(
            service_type="memory",
            config={"default_scope": "chatbot"},
            async_preferred=True
        )
        
        # Simulate a multi-turn conversation
        conversation_id = "chatbot_session_123"
        
        turns = [
            ("user", "What's the weather like?"),
            ("assistant", "I don't have access to weather data, but I can help with other questions."),
            ("user", "Can you explain machine learning?"),
            ("assistant", "Machine learning is a subset of AI that learns from data."),
            ("user", "Give me an example"),
            ("assistant", "Email spam detection is a common ML application.")
        ]
        
        # Store all turns
        for turn_type, content in turns:
            await memory_service.store_turn(
                conversation_id=conversation_id,
                content=content,
                metadata={
                    "turn_type": turn_type,
                    "user_id": "chatbot_user_123" if turn_type == "user" else None
                }
            )
        
        # Get recent history (last 4 turns)
        recent_history = await memory_service.get_history(
            conversation_id=conversation_id,
            limit=4
        )
        
        assert len(recent_history) == 4
        
        # Search for ML-related content
        ml_results = await memory_service.search_conversations(
            query="machine learning",
            limit=5
        )
        
        assert isinstance(ml_results, list)