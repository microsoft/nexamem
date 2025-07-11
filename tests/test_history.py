"""
Comprehensive unit tests for history module.
Tests enhanced ChatHistory functionality with multiple storage backends.
"""
import json
import os
import sqlite3
import tempfile
import time
from unittest.mock import Mock, patch

import pytest

from nexamem.config import initialize
from nexamem.history import ChatHistory


class TestChatHistoryBasics:
    """Test basic ChatHistory functionality."""

    def test_chathistory_initialization_default(self):
        """Test ChatHistory initialization with default settings."""
        history = ChatHistory()

        assert history.messages == []
        assert history.session_context == {}

    def test_add_message_basic(self):
        """Test basic message addition."""
        history = ChatHistory()

        history.add_message("user", "Hello, how are you?")

        assert len(history.messages) == 1
        assert history.messages[0]["role"] == "user"
        assert history.messages[0]["content"] == "Hello, how are you?"

    def test_add_message_with_enhanced_properties(self):
        """Test adding message with enhanced properties."""
        history = ChatHistory()

        history.add_message(
            "assistant",
            "I'm doing well, thank you!",
            agent_id="chatbot_v2",
            user_id="user123",
            session_id="session456",
            env="production",
            tokens=12,
            data=json.dumps({"confidence": 0.95})
        )

        message = history.messages[0]
        assert message["role"] == "assistant"
        assert message["content"] == "I'm doing well, thank you!"
        assert message["agent_id"] == "chatbot_v2"
        assert message["user_id"] == "user123"
        assert message["session_id"] == "session456"
        assert message["env"] == "production"
        assert message["tokens"] == 12
        assert json.loads(message["data"])["confidence"] == 0.95

    def test_add_message_with_defaults(self):
        """Test that default values are applied correctly."""
        history = ChatHistory()

        history.add_message("user", "Test message")

        message = history.messages[0]
        assert message["agent_id"] == ""
        assert message["user_id"] == ""
        assert message["env"] == "prod"
        assert message["tokens"] == 0
        assert message["data"] == ""
        assert "session_id" in message  # Should be auto-generated
        assert "timestamp" in message  # Should be auto-generated

    def test_session_context_management(self):
        """Test session context management."""
        history = ChatHistory()

        # Set session context
        history.set_session_context(
            agent_id="portfolio_advisor",
            user_id="customer789",
            env="staging"
        )

        # Add message - should inherit context
        history.add_message("user", "What's my portfolio balance?")

        message = history.messages[0]
        assert message["agent_id"] == "portfolio_advisor"
        assert message["user_id"] == "customer789"
        assert message["env"] == "staging"

    def test_convenience_methods(self):
        """Test convenience methods for different roles."""
        history = ChatHistory()

        history.set_session_context(
            agent_id="assistant",
            user_id="user123"
        )

        # Test convenience methods
        history.add_user_message("User question", tokens=5)
        history.add_assistant_message("Assistant response", tokens=10)
        history.add_system_message("System notification", tokens=3)

        assert len(history.messages) == 3
        assert history.messages[0]["role"] == "user"
        assert history.messages[0]["tokens"] == 5
        assert history.messages[1]["role"] == "assistant"
        assert history.messages[1]["tokens"] == 10
        assert history.messages[2]["role"] == "system"
        assert history.messages[2]["tokens"] == 3

        # All should inherit session context
        for message in history.messages:
            assert message["agent_id"] == "assistant"
            assert message["user_id"] == "user123"

    def test_get_history(self):
        """Test getting message history."""
        history = ChatHistory()

        history.add_message("user", "First message")
        history.add_message("assistant", "First response")
        history.add_message("user", "Second message")

        messages = history.get_history()

        assert len(messages) == 3
        assert messages[0]["content"] == "First message"
        assert messages[1]["content"] == "First response"
        assert messages[2]["content"] == "Second message"

    def test_get_message_at(self):
        """Test getting specific message by index."""
        history = ChatHistory()

        history.add_message("user", "Message 1")
        history.add_message("assistant", "Message 2")
        history.add_message("user", "Message 3")

        # Test valid indices
        assert history.get_message_at(0)["content"] == "Message 1"
        assert history.get_message_at(1)["content"] == "Message 2"
        assert history.get_message_at(2)["content"] == "Message 3"

        # Test negative indices
        assert history.get_message_at(-1)["content"] == "Message 3"
        assert history.get_message_at(-2)["content"] == "Message 2"

        # Test out of bounds
        assert history.get_message_at(10) is None
        assert history.get_message_at(-10) is None

    def test_clear_history(self):
        """Test clearing message history."""
        history = ChatHistory()

        history.add_message("user", "Message 1")
        history.add_message("assistant", "Message 2")

        assert len(history.messages) == 2

        history.clear_history()

        assert len(history.messages) == 0

    def test_session_id_consistency(self):
        """Test that session ID remains consistent within session."""
        history = ChatHistory()

        history.add_message("user", "First message")
        history.add_message("assistant", "First response")

        session_id_1 = history.messages[0]["session_id"]
        session_id_2 = history.messages[1]["session_id"]

        # Should be the same within one history instance
        assert session_id_1 == session_id_2

    def test_timestamp_ordering(self):
        """Test that timestamps are properly ordered."""
        history = ChatHistory()

        history.add_message("user", "First message")
        time.sleep(0.01)  # Small delay
        history.add_message("assistant", "Second message")

        timestamp_1 = history.messages[0]["timestamp"]
        timestamp_2 = history.messages[1]["timestamp"]

        # Second timestamp should be after first
        assert timestamp_2 > timestamp_1


class TestChatHistoryFileStorage:
    """Test ChatHistory with file storage backend."""

    def test_file_storage_persistence(self):
        """Test file storage persistence."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
            temp_path = temp_file.name

        try:
            # Initialize with file storage
            initialize({
                "history_storage": "file",
                "file_path": temp_path
            })

            history = ChatHistory()
            history.add_message("user", "Test message")

            # Verify file was created and contains data
            assert os.path.exists(temp_path)

            with open(temp_path) as f:
                data = json.load(f)

            assert len(data) == 1
            assert data[0]["content"] == "Test message"

        finally:
            # Cleanup
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_file_storage_load_existing(self):
        """Test loading existing file storage."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
            # Pre-populate file with test data
            test_data = [
                {
                    "role": "user",
                    "content": "Existing message",
                    "agent_id": "",
                    "user_id": "",
                    "session_id": "test_session",
                    "env": "prod",
                    "timestamp": "2025-01-01T00:00:00",
                    "tokens": 5,
                    "data": ""
                }
            ]
            json.dump(test_data, temp_file)
            temp_path = temp_file.name

        try:
            # Initialize with existing file
            initialize({
                "history_storage": "file",
                "file_path": temp_path
            })

            history = ChatHistory()

            # Should load existing data
            messages = history.get_history()
            assert len(messages) == 1
            assert messages[0]["content"] == "Existing message"
            assert messages[0]["session_id"] == "test_session"

        finally:
            # Cleanup
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_file_storage_clear(self):
        """Test clearing file storage."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
            temp_path = temp_file.name

        try:
            initialize({
                "history_storage": "file",
                "file_path": temp_path
            })

            history = ChatHistory()
            history.add_message("user", "Test message")

            assert len(history.get_history()) == 1

            history.clear_history()

            assert len(history.get_history()) == 0

            # File should still exist but be empty
            assert os.path.exists(temp_path)
            with open(temp_path) as f:
                data = json.load(f)
            assert len(data) == 0

        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)


class TestChatHistorySQLiteStorage:
    """Test ChatHistory with SQLite storage backend."""

    def test_sqlite_storage_persistence(self):
        """Test SQLite storage persistence."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as temp_file:
            temp_path = temp_file.name

        try:
            # Initialize with SQLite storage
            initialize({
                "history_storage": "sqlite",
                "sqlite_path": temp_path
            })

            history = ChatHistory()
            history.add_message("user", "SQLite test message", tokens=8)

            # Verify database was created
            assert os.path.exists(temp_path)

            # Verify data in database
            conn = sqlite3.connect(temp_path)
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM messages")
            rows = cursor.fetchall()
            conn.close()

            assert len(rows) == 1
            # Check that the message content is in the row
            row_data = dict(zip([desc[0] for desc in cursor.description], rows[0]))
            assert "SQLite test message" in str(row_data)

        finally:
            # Cleanup
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_sqlite_query_functionality(self):
        """Test SQLite query functionality."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as temp_file:
            temp_path = temp_file.name

        try:
            initialize({
                "history_storage": "sqlite",
                "sqlite_path": temp_path
            })

            history = ChatHistory()

            # Add multiple messages with different properties
            history.add_message("user", "Query test 1", agent_id="agent1", tokens=5)
            history.add_message("assistant", "Response 1", agent_id="agent1", tokens=10)
            history.add_message("user", "Query test 2", agent_id="agent2", tokens=7)
            history.add_message("assistant", "Response 2", agent_id="agent2", tokens=12)

            # Test query by agent
            agent1_messages = history.query_sqlite("agent_id = ?", ("agent1",))
            assert len(agent1_messages) == 2

            # Test query by role
            user_messages = history.query_sqlite("role = ?", ("user",))
            assert len(user_messages) == 2

            # Test query by token count
            high_token_messages = history.query_sqlite("tokens > ?", (8,))
            assert len(high_token_messages) == 2  # 10 and 12 tokens

        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_sqlite_migration_compatibility(self):
        """Test SQLite backward compatibility with legacy data."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as temp_file:
            temp_path = temp_file.name

        try:
            # Create database with legacy schema
            conn = sqlite3.connect(temp_path)
            cursor = conn.cursor()

            # Create table with minimal legacy schema
            cursor.execute('''
                CREATE TABLE messages (
                    id INTEGER PRIMARY KEY,
                    role TEXT,
                    content TEXT,
                    timestamp TEXT
                )
            ''')

            # Insert legacy data
            cursor.execute('''
                INSERT INTO messages (role, content, timestamp)
                VALUES (?, ?, ?)
            ''', ("user", "Legacy message", "2025-01-01T00:00:00"))

            conn.commit()
            conn.close()

            # Initialize with existing database
            initialize({
                "history_storage": "sqlite",
                "sqlite_path": temp_path
            })

            history = ChatHistory()

            # Should handle legacy data gracefully
            messages = history.get_history()
            assert len(messages) >= 1

            # Add new message with enhanced properties
            history.add_message("assistant", "New message", tokens=15)

            # Should work without errors
            updated_messages = history.get_history()
            assert len(updated_messages) >= 2

        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)


class TestChatHistoryRedisStorage:
    """Test ChatHistory with Redis storage backend."""

    @pytest.fixture
    def mock_redis_config(self):
        """Mock Redis configuration."""
        return {
            "history_storage": "redis",
            "redis_config": {
                "host": "localhost",
                "port": 6379,
                "db": 0,
                "use_fakeredis": True
            }
        }

    def test_redis_storage_initialization(self, mock_redis_config):
        """Test Redis storage initialization."""
        with patch('nexamem.history.redis') as mock_redis_module:
            mock_client = Mock()
            mock_redis_module.Redis.return_value = mock_client

            initialize(mock_redis_config)
            history = ChatHistory()

            # Should initialize without errors
            assert history is not None

    def test_redis_storage_operations(self, mock_redis_config):
        """Test Redis storage operations."""
        with patch('nexamem.history.redis') as mock_redis_module:
            mock_client = Mock()
            mock_redis_module.Redis.return_value = mock_client

            # Mock Redis operations
            mock_client.zadd.return_value = 1
            mock_client.zrange.return_value = [b'msg1', b'msg2']
            mock_client.get.side_effect = [
                json.dumps({
                    "role": "user",
                    "content": "Redis message 1",
                    "timestamp": time.time(),
                    "agent_id": "",
                    "user_id": "",
                    "session_id": "test",
                    "env": "prod",
                    "tokens": 0,
                    "data": ""
                }).encode(),
                json.dumps({
                    "role": "assistant",
                    "content": "Redis message 2",
                    "timestamp": time.time(),
                    "agent_id": "",
                    "user_id": "",
                    "session_id": "test",
                    "env": "prod",
                    "tokens": 0,
                    "data": ""
                }).encode()
            ]

            initialize(mock_redis_config)
            history = ChatHistory()

            # Test adding message
            history.add_message("user", "Test Redis message")
            mock_client.zadd.assert_called()

            # Test getting messages
            history.get_history()
            mock_client.zrange.assert_called()

    def test_redis_query_functionality(self, mock_redis_config):
        """Test Redis query functionality."""
        with patch('nexamem.history.redis') as mock_redis_module:
            mock_client = Mock()
            mock_redis_module.Redis.return_value = mock_client

            # Mock scan results
            mock_client.scan_iter.return_value = iter([b'key1', b'key2'])
            mock_client.get.side_effect = [
                json.dumps({
                    "role": "user",
                    "content": "Message 1",
                    "timestamp": time.time(),
                    "agent_id": "agent1",
                    "user_id": "user123",
                    "session_id": "session1",
                    "env": "prod",
                    "tokens": 5,
                    "data": ""
                }).encode(),
                json.dumps({
                    "role": "assistant",
                    "content": "Message 2",
                    "timestamp": time.time(),
                    "agent_id": "agent1",
                    "user_id": "user123",
                    "session_id": "session1",
                    "env": "prod",
                    "tokens": 10,
                    "data": ""
                }).encode()
            ]

            initialize(mock_redis_config)
            history = ChatHistory()

            # Test query_redis method
            results = history.query_redis("*user123*", limit=10)

            mock_client.scan_iter.assert_called()
            assert len(results) == 2

    def test_redis_clear_functionality(self, mock_redis_config):
        """Test Redis clear functionality."""
        with patch('nexamem.history.redis') as mock_redis_module:
            mock_client = Mock()
            mock_redis_module.Redis.return_value = mock_client

            mock_client.scan_iter.return_value = iter([b'key1', b'key2'])
            mock_client.delete.return_value = 2

            initialize(mock_redis_config)
            history = ChatHistory()

            history.clear_history()

            mock_client.scan_iter.assert_called()
            mock_client.delete.assert_called()


class TestChatHistoryAnalytics:
    """Test ChatHistory analytics and enhanced features."""

    def test_token_analytics(self):
        """Test token usage analytics."""
        history = ChatHistory()

        history.add_message("user", "User message 1", tokens=5)
        history.add_message("assistant", "Assistant response 1", tokens=12)
        history.add_message("user", "User message 2", tokens=7)
        history.add_message("assistant", "Assistant response 2", tokens=15)

        messages = history.get_history()

        # Calculate analytics
        total_tokens = sum(msg['tokens'] for msg in messages)
        user_tokens = sum(msg['tokens'] for msg in messages if msg['role'] == 'user')
        assistant_tokens = sum(msg['tokens'] for msg in messages if msg['role'] == 'assistant')

        assert total_tokens == 39  # 5 + 12 + 7 + 15
        assert user_tokens == 12   # 5 + 7
        assert assistant_tokens == 27  # 12 + 15

    def test_agent_analytics(self):
        """Test multi-agent analytics."""
        history = ChatHistory()

        history.add_message("user", "Message 1", agent_id="agent_a")
        history.add_message("assistant", "Response 1", agent_id="agent_a")
        history.add_message("user", "Message 2", agent_id="agent_b")
        history.add_message("assistant", "Response 2", agent_id="agent_b")

        messages = history.get_history()

        # Get unique agents
        agents = {msg['agent_id'] for msg in messages if msg['agent_id']}
        assert agents == {"agent_a", "agent_b"}

        # Count messages per agent
        agent_a_messages = [msg for msg in messages if msg['agent_id'] == 'agent_a']
        agent_b_messages = [msg for msg in messages if msg['agent_id'] == 'agent_b']

        assert len(agent_a_messages) == 2
        assert len(agent_b_messages) == 2

    def test_session_tracking(self):
        """Test session tracking analytics."""
        history = ChatHistory()

        # Set session context
        history.set_session_context(
            agent_id="customer_service",
            user_id="customer_456",
            env="production"
        )

        history.add_message("user", "Need help with order")
        history.add_message("assistant", "I can help with that")

        messages = history.get_history()

        # Verify session consistency
        session_ids = {msg['session_id'] for msg in messages}
        assert len(session_ids) == 1  # All messages in same session

        # Verify context inheritance
        for msg in messages:
            assert msg['agent_id'] == "customer_service"
            assert msg['user_id'] == "customer_456"
            assert msg['env'] == "production"

    def test_custom_data_handling(self):
        """Test custom data field functionality."""
        history = ChatHistory()

        # Add message with custom data
        custom_data = {
            "confidence": 0.95,
            "intent": "order_inquiry",
            "entities": ["order_id", "customer_name"]
        }

        history.add_message(
            "assistant",
            "Your order #12345 has been shipped",
            data=json.dumps(custom_data)
        )

        messages = history.get_history()
        message_data = json.loads(messages[0]['data'])

        assert message_data['confidence'] == 0.95
        assert message_data['intent'] == "order_inquiry"
        assert len(message_data['entities']) == 2


class TestChatHistoryEdgeCases:
    """Test ChatHistory edge cases and error handling."""

    def test_empty_message_content(self):
        """Test handling of empty message content."""
        history = ChatHistory()

        history.add_message("user", "")
        history.add_message("assistant", None)

        messages = history.get_history()

        assert len(messages) == 2
        assert messages[0]["content"] == ""
        assert messages[1]["content"] is None

    def test_special_characters_in_content(self):
        """Test handling of special characters in message content."""
        history = ChatHistory()

        special_content = "Hello! 🎉 This has émojis and spëcial chârs: @#$%^&*()"
        history.add_message("user", special_content)

        messages = history.get_history()
        assert messages[0]["content"] == special_content

    def test_large_message_content(self):
        """Test handling of large message content."""
        history = ChatHistory()

        # Create large content (10KB)
        large_content = "A" * 10000
        history.add_message("user", large_content)

        messages = history.get_history()
        assert len(messages[0]["content"]) == 10000
        assert messages[0]["content"] == large_content

    def test_invalid_role_handling(self):
        """Test handling of invalid role values."""
        history = ChatHistory()

        # Add message with non-standard role
        history.add_message("custom_role", "Custom message")

        messages = history.get_history()
        assert messages[0]["role"] == "custom_role"

    def test_negative_token_values(self):
        """Test handling of negative token values."""
        history = ChatHistory()

        history.add_message("user", "Test message", tokens=-5)

        messages = history.get_history()
        assert messages[0]["tokens"] == -5

    def test_very_large_token_values(self):
        """Test handling of very large token values."""
        history = ChatHistory()

        large_tokens = 1000000
        history.add_message("assistant", "Large token message", tokens=large_tokens)

        messages = history.get_history()
        assert messages[0]["tokens"] == large_tokens

    def test_malformed_json_data(self):
        """Test handling of malformed JSON in data field."""
        history = ChatHistory()

        # Add message with invalid JSON data
        history.add_message("user", "Test message", data="{ invalid json")

        messages = history.get_history()
        # Should store as-is, validation happens at application level
        assert messages[0]["data"] == "{ invalid json"

    def test_unicode_handling(self):
        """Test Unicode character handling."""
        history = ChatHistory()

        unicode_content = "Hello 世界! Café naïve résumé 🌍"
        history.add_message("user", unicode_content, agent_id="unicode_tëst")

        messages = history.get_history()
        assert messages[0]["content"] == unicode_content
        assert messages[0]["agent_id"] == "unicode_tëst"

    def test_none_values_in_properties(self):
        """Test handling of None values in message properties."""
        history = ChatHistory()

        history.add_message(
            "user",
            "Test message",
            agent_id=None,
            user_id=None,
            session_id=None,
            env=None,
            tokens=None,
            data=None
        )

        messages = history.get_history()
        message = messages[0]

        # None values should be preserved or converted appropriately
        assert message["agent_id"] is None or message["agent_id"] == ""
        assert message["user_id"] is None or message["user_id"] == ""
        # session_id should be auto-generated even if None passed
        assert message["session_id"] is not None
        assert message["env"] is None or message["env"] == "prod"
