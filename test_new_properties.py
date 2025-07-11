#!/usr/bin/env python3
"""
Test script to verify the new message properties work correctly.
"""

import sys
import os
import tempfile
import json

# Add the src directory to the path so we can import nexamem
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from nexamem.history import ChatHistory, Message
from nexamem import init

def test_message_properties():
    """Test that new message properties work correctly."""
    
    # Test the Message model directly
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
    
    # Initialize with memory storage
    init(history_storage="memory")
    
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

def test_file_storage():
    """Test file storage with new properties."""
    print("\nTesting file storage...")
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_file = f.name
    
    try:
        # Initialize with file storage
        init(history_storage="file", file_path=temp_file)
        
        history = ChatHistory()
        history.add_message(
            "user", 
            "Test message",
            agent_id="file_agent",
            user_id="file_user",
            tokens=15,
            data='{"file": "test"}'
        )
        
        # Create new instance to test loading
        history2 = ChatHistory()
        messages = history2.get_history()
        
        assert len(messages) == 1
        msg = messages[0]
        assert msg["role"] == "user"
        assert msg["content"] == "Test message"
        assert msg["agent_id"] == "file_agent"
        assert msg["user_id"] == "file_user"
        assert msg["tokens"] == 15
        assert msg["data"] == '{"file": "test"}'
        
        print("✓ File storage test passed")
        
    finally:
        # Clean up
        if os.path.exists(temp_file):
            os.unlink(temp_file)

def test_sqlite_storage():
    """Test SQLite storage with new properties."""
    print("\nTesting SQLite storage...")
    
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        temp_db = f.name
    
    try:
        # Initialize with SQLite storage
        init(history_storage="sqlite", sqlite_path=temp_db)
        
        history = ChatHistory()
        history.add_message(
            "assistant",
            "SQLite test message",
            agent_id="sqlite_agent",
            user_id="sqlite_user",
            env="test",
            tokens=20,
            data='{"db": "sqlite"}'
        )
        
        # Test query functionality
        results = history.query_sqlite("tokens > ?", (10,))
        assert len(results) == 1
        
        msg = results[0]
        assert msg["role"] == "assistant"
        assert msg["content"] == "SQLite test message"
        assert msg["agent_id"] == "sqlite_agent"
        assert msg["user_id"] == "sqlite_user"
        assert msg["env"] == "test"
        assert msg["tokens"] == 20
        assert msg["data"] == '{"db": "sqlite"}'
        
        print("✓ SQLite storage test passed")
        
    finally:
        # Clean up
        if os.path.exists(temp_db):
            os.unlink(temp_db)

def test_legacy_compatibility():
    """Test that the legacy module still works."""
    print("\nTesting legacy compatibility...")
    
    from llm_chatbot_history.history import ChatHistory as LegacyHistory
    
    history = LegacyHistory()
    history.add_message("user", "Legacy test")
    
    messages = history.get_history()
    assert len(messages) == 1
    
    msg = messages[0]
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
    test_file_storage()
    test_sqlite_storage()
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
