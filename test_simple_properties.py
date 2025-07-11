#!/usr/bin/env python3
"""
Simple test to verify the new message properties work correctly.
"""

import sys
import os
import tempfile

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_message_properties():
    """Test that new message properties work correctly."""
    
    from nexamem.history import Message
    
    print("Testing Message model...")
    msg = Message(
        role="user",
        content="Hello, world!",
        agent_id="test_agent",
        user_id="user123",
        env="dev",
        tokens=10,
        data='{"custom": "data"}'
    )
    
    print(f"Message: {msg.model_dump()}")
    assert msg.role == "user"
    assert msg.content == "Hello, world!"
    assert msg.agent_id == "test_agent"
    assert msg.user_id == "user123"
    assert msg.env == "dev"
    assert msg.tokens == 10
    assert msg.data == '{"custom": "data"}'
    assert msg.session_id  # Should be auto-generated
    assert msg.timestamp   # Should be auto-generated
    print("✓ Message model test passed")

def test_memory_storage():
    """Test memory storage with new properties."""
    print("\nTesting memory storage...")
    
    from nexamem import initialize, ChatHistory
    
    # Initialize with memory storage
    initialize({"history_storage": "memory"})
    
    history = ChatHistory()
    
    # Set session context
    history.set_session_context(
        agent_id="invest_agent",
        user_id="u12345",
        env="prod"
    )
    
    # Add messages using convenience methods
    history.add_user_message("What's my balance?", tokens=5)
    history.add_assistant_message("Your balance is $1,000", tokens=10)
    history.add_system_message("User authenticated", tokens=3)
    
    # Get history and verify
    messages = history.get_history()
    print(f"Retrieved {len(messages)} messages")
    
    for i, msg in enumerate(messages):
        print(f"Message {i}: {msg}")
        assert msg["agent_id"] == "invest_agent"
        assert msg["user_id"] == "u12345"
        assert msg["env"] == "prod"
        assert "session_id" in msg
        assert "timestamp" in msg
        assert msg["tokens"] > 0
        
    print("✓ Memory storage test passed")

def test_direct_add_message():
    """Test add_message with new properties."""
    print("\nTesting direct add_message...")
    
    from nexamem import initialize, ChatHistory
    
    # Initialize with memory storage
    initialize({"history_storage": "memory"})
    
    history = ChatHistory()
    
    # Add message with all new properties
    history.add_message(
        "assistant",
        "Direct test message",
        agent_id="direct_agent",
        user_id="direct_user",
        env="test",
        tokens=25,
        data='{"test": "direct"}'
    )
    
    messages = history.get_history()
    assert len(messages) == 1
    
    msg = messages[0]
    print(f"Direct message: {msg}")
    
    assert msg["role"] == "assistant"
    assert msg["content"] == "Direct test message"
    assert msg["agent_id"] == "direct_agent"
    assert msg["user_id"] == "direct_user"
    assert msg["env"] == "test"
    assert msg["tokens"] == 25
    assert msg["data"] == '{"test": "direct"}'
    assert "session_id" in msg
    assert "timestamp" in msg
    
    print("✓ Direct add_message test passed")

def test_legacy_compatibility():
    """Test that the legacy module still works."""
    print("\nTesting legacy compatibility...")
    
    from llm_chatbot_history.history import ChatHistory as LegacyHistory
    
    history = LegacyHistory()
    history.add_message("user", "Legacy test")
    
    messages = history.get_history()
    assert len(messages) == 1
    
    msg = messages[0]
    print(f"Legacy message: {msg}")
    
    assert msg["role"] == "user"
    assert msg["content"] == "Legacy test"
    # Should have default values for new properties
    assert msg["agent_id"] == ""
    assert msg["user_id"] == ""
    assert msg["env"] == "prod"
    assert msg["tokens"] == 0
    assert msg["data"] == ""
    assert "session_id" in msg
    assert "timestamp" in msg
    
    print("✓ Legacy compatibility test passed")

if __name__ == "__main__":
    print("Testing new message properties...\n")
    
    test_message_properties()
    test_memory_storage()
    test_direct_add_message()
    test_legacy_compatibility()
    
    print("\n🎉 All tests passed!")
    print("\nNew properties now available in messages:")
    print("- agent_id: Agent identifier")
    print("- user_id: User identifier")  
    print("- session_id: Session UUID (auto-generated)")
    print("- env: Environment (default: 'prod')")
    print("- timestamp: ISO datetime string (auto-generated)")
    print("- tokens: Number of tokens used (default: 0)")
    print("- data: JSON string for additional data (default: '')")
