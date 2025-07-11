"""
Unit tests for MemoryScope class
"""
import uuid
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from nexamem import MemoryScope


class TestMemoryScope:
    """Test suite for MemoryScope class."""

    def test_create_memory_scope_with_all_fields(self):
        """Test creating MemoryScope with all fields provided."""
        scope = MemoryScope(
            agent_id="invest_agent",
            user_id="user123",
            session_id="session456",
            env="prod"
        )

        assert scope.agent_id == "invest_agent"
        assert scope.user_id == "user123"
        assert scope.session_id == "session456"
        assert scope.env == "prod"

    def test_create_memory_scope_with_defaults(self):
        """Test creating MemoryScope with default env."""
        scope = MemoryScope(
            agent_id="test_agent",
            user_id="user123",
            session_id="session456"
        )

        assert scope.agent_id == "test_agent"
        assert scope.user_id == "user123"
        assert scope.session_id == "session456"
        assert scope.env == "prod"  # Default value

    def test_auto_generate_session_id(self):
        """Test automatic session_id generation when not provided."""
        scope = MemoryScope(
            agent_id="test_agent",
            user_id="user123"
        )

        assert scope.agent_id == "test_agent"
        assert scope.user_id == "user123"
        assert scope.session_id is not None
        assert len(scope.session_id) > 0
        # Verify it looks like a UUID
        uuid.UUID(scope.session_id)  # Should not raise exception

    def test_auto_generate_session_id_when_empty(self):
        """Test automatic session_id generation when empty string provided."""
        scope = MemoryScope(
            agent_id="test_agent",
            user_id="user123",
            session_id=""
        )

        assert scope.session_id != ""
        assert scope.session_id is not None
        uuid.UUID(scope.session_id)  # Should not raise exception

    def test_get_key_prefix(self):
        """Test key prefix generation."""
        scope = MemoryScope(
            agent_id="invest_agent",
            user_id="user123",
            session_id="session456",
            env="test"
        )

        prefix = scope.get_key_prefix("working")
        expected = "test:invest_agent:user123:session456:working"
        assert prefix == expected

    def test_get_index_key(self):
        """Test index key generation."""
        scope = MemoryScope(
            agent_id="invest_agent",
            user_id="user123",
            session_id="session456",
            env="prod"
        )

        index_key = scope.get_index_key("routing")
        expected = "prod:invest_agent:user123:session456:routing:index"
        assert index_key == expected

    def test_model_dump_dict(self):
        """Test model_dump_dict method."""
        scope = MemoryScope(
            agent_id="test_agent",
            user_id="user123",
            session_id="session456",
            env="staging"
        )

        result = scope.model_dump_dict()
        expected = {
            "agent_id": "test_agent",
            "user_id": "user123",
            "session_id": "session456",
            "env": "staging"
        }
        assert result == expected

    def test_memory_scope_equality(self):
        """Test MemoryScope equality comparison."""
        scope1 = MemoryScope(
            agent_id="agent1",
            user_id="user1",
            session_id="session1",
            env="test"
        )
        scope2 = MemoryScope(
            agent_id="agent1",
            user_id="user1",
            session_id="session1",
            env="test"
        )
        scope3 = MemoryScope(
            agent_id="agent2",
            user_id="user1",
            session_id="session1",
            env="test"
        )

        assert scope1 == scope2
        assert scope1 != scope3

    def test_memory_scope_immutability(self):
        """Test that MemoryScope fields are immutable after creation."""
        scope = MemoryScope(
            agent_id="test_agent",
            user_id="user123",
            session_id="session456"
        )

        # Pydantic models are immutable by default
        with pytest.raises(ValidationError):
            scope.agent_id = "new_agent"

    def test_required_fields_validation(self):
        """Test that required fields are validated."""
        # Missing agent_id
        with pytest.raises(ValidationError):
            MemoryScope(user_id="user123")

        # Missing user_id
        with pytest.raises(ValidationError):
            MemoryScope(agent_id="agent123")

    def test_field_types_validation(self):
        """Test field type validation."""
        # Non-string agent_id
        with pytest.raises(ValidationError):
            MemoryScope(agent_id=123, user_id="user123")

        # Non-string user_id
        with pytest.raises(ValidationError):
            MemoryScope(agent_id="agent123", user_id=456)

    def test_key_prefix_with_special_characters(self):
        """Test key prefix generation with special characters."""
        scope = MemoryScope(
            agent_id="special-agent",
            user_id="user@domain.com",
            session_id="session_123",
            env="dev"
        )

        prefix = scope.get_key_prefix("test_channel")
        expected = "dev:special-agent:user@domain.com:session_123:test_channel"
        assert prefix == expected

    @patch('uuid.uuid4')
    def test_uuid_generation_mocked(self, mock_uuid):
        """Test UUID generation with mocked uuid4."""
        mock_uuid.return_value.hex = "test-uuid-123"
        mock_uuid.return_value.__str__ = lambda x: "test-uuid-123"

        scope = MemoryScope(
            agent_id="test_agent",
            user_id="user123"
        )

        mock_uuid.assert_called_once()
        assert scope.session_id == "test-uuid-123"

    def test_empty_string_fields(self):
        """Test behavior with empty string fields."""
        # Empty agent_id should fail validation
        with pytest.raises(ValidationError):
            MemoryScope(agent_id="", user_id="user123")

        # Empty user_id should fail validation
        with pytest.raises(ValidationError):
            MemoryScope(agent_id="agent123", user_id="")

    def test_none_fields(self):
        """Test behavior with None fields."""
        # None agent_id should fail validation
        with pytest.raises(ValidationError):
            MemoryScope(agent_id=None, user_id="user123")

        # None user_id should fail validation
        with pytest.raises(ValidationError):
            MemoryScope(agent_id="agent123", user_id=None)
