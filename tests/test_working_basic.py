"""
Simple working test to verify the test setup and basic functionality.
"""
import pytest

from nexamem import AIMemory, MemoryScope


def test_basic_aimemory_initialization():
    """Test that AIMemory can be initialized successfully."""
    memory = AIMemory(use_fakeredis=True)
    assert memory is not None
    assert memory.redis is not None
    assert memory.channels is not None
    assert memory.policy is not None


def test_memory_scope_creation():
    """Test that MemoryScope can be created successfully."""
    scope = MemoryScope(
        agent_id="test_agent",
        user_id="user123",
        session_id="session456",
        env="test"
    )
    assert scope.agent_id == "test_agent"
    assert scope.user_id == "user123"
    assert scope.session_id == "session456"
    assert scope.env == "test"


def test_aimemory_with_features():
    """Test AIMemory initialization with features enabled."""
    memory = AIMemory(
        use_fakeredis=True,
        enable_audit=True,
        enable_metrics=True,
        enable_content_processing=True
    )
    assert memory is not None
    # Check that audit is enabled
    assert memory.audit is not None
    # Check that content processor is enabled
    assert memory.content_processor is not None


if __name__ == "__main__":
    # Run tests if script is executed directly
    pytest.main([__file__, "-v"])
