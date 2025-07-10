"""
Example demonstrating chat ID functionality in NexaMem.

This example shows how to:
1. Use auto-generated chat IDs
2. Use custom chat IDs
3. Manage multiple chat sessions
4. See how different storage backends handle chat separation
"""

import os
import tempfile
from nexamem import initialize, ChatHistory

def demo_auto_generated_chat_id():
    """Demonstrate auto-generated chat ID functionality."""
    print("=== Auto-Generated Chat ID Demo ===")
    
    # Initialize without providing chat_id - one will be auto-generated
    initialize({
        "history_storage": "memory",
        "debug": True
    })
    
    history = ChatHistory()
    print(f"Auto-generated chat ID: {history.get_chat_id()}")
    
    history.add_message("user", "Hello!")
    history.add_message("assistant", "Hi! How can I help you?")
    
    print(f"Messages in chat {history.get_chat_id()}: {len(history.get_history())}")
    print()

def demo_custom_chat_id():
    """Demonstrate custom chat ID functionality."""
    print("=== Custom Chat ID Demo ===")
    
    # Initialize with a custom chat_id
    initialize({
        "history_storage": "memory",
        "chat_id": "customer-support-session-123",
        "debug": True
    })
    
    history = ChatHistory()
    print(f"Custom chat ID: {history.get_chat_id()}")
    
    history.add_message("user", "I need help with my order")
    history.add_message("assistant", "I'd be happy to help! What's your order number?")
    
    print(f"Messages in chat {history.get_chat_id()}: {len(history.get_history())}")
    print()

def demo_multiple_sqlite_chats():
    """Demonstrate multiple chat sessions using SQLite."""
    print("=== Multiple SQLite Chats Demo ===")
    
    # Create a temporary database file
    db_path = os.path.join(tempfile.gettempdir(), "nexamem_demo.db")
    
    # First chat session
    initialize({
        "history_storage": "sqlite",
        "sqlite_path": db_path,
        "chat_id": "session-alpha",
        "debug": True
    })
    
    chat_alpha = ChatHistory()
    chat_alpha.add_message("user", "Hello from Alpha!")
    chat_alpha.add_message("assistant", "Hi Alpha user!")
    
    print(f"Chat Alpha ID: {chat_alpha.get_chat_id()}")
    print(f"Chat Alpha messages: {len(chat_alpha.get_history())}")
    
    # Second chat session (same database, different chat_id)
    initialize({
        "history_storage": "sqlite",
        "sqlite_path": db_path,
        "chat_id": "session-beta",
        "debug": True
    })
    
    chat_beta = ChatHistory()
    chat_beta.add_message("user", "Hello from Beta!")
    chat_beta.add_message("assistant", "Hi Beta user!")
    chat_beta.add_message("user", "This is a longer conversation")
    
    print(f"Chat Beta ID: {chat_beta.get_chat_id()}")
    print(f"Chat Beta messages: {len(chat_beta.get_history())}")
    
    # Verify separation - reinitialize Alpha and check it still has only 2 messages
    initialize({
        "history_storage": "sqlite",
        "sqlite_path": db_path,
        "chat_id": "session-alpha",
        "debug": True
    })
    
    chat_alpha_reload = ChatHistory()
    print(f"Chat Alpha (reloaded) messages: {len(chat_alpha_reload.get_history())}")
    
    # Clean up
    try:
        os.remove(db_path)
        print(f"Cleaned up database: {db_path}")
    except OSError:
        pass
    
    print()

def demo_file_storage_separation():
    """Demonstrate how file storage separates chats using filenames."""
    print("=== File Storage Chat Separation Demo ===")
    
    temp_dir = tempfile.gettempdir()
    base_filename = os.path.join(temp_dir, "nexamem_demo.json")
    
    # First chat
    initialize({
        "history_storage": "file",
        "file_path": base_filename,
        "chat_id": "user-123",
        "debug": True
    })
    
    chat1 = ChatHistory()
    chat1.add_message("user", "Message from user 123")
    print(f"Chat 1 ID: {chat1.get_chat_id()}")
    
    # Second chat  
    initialize({
        "history_storage": "file",
        "file_path": base_filename,
        "chat_id": "user-456",
        "debug": True
    })
    
    chat2 = ChatHistory()
    chat2.add_message("user", "Message from user 456")
    print(f"Chat 2 ID: {chat2.get_chat_id()}")
    
    print("File storage creates separate files for each chat_id:")
    expected_files = [
        f"{os.path.splitext(base_filename)[0]}_user-123.json",
        f"{os.path.splitext(base_filename)[0]}_user-456.json"
    ]
    
    for filename in expected_files:
        if os.path.exists(filename):
            print(f"  ✓ {filename}")
            try:
                os.remove(filename)
            except OSError:
                pass
        else:
            print(f"  ✗ {filename}")
    
    print()

if __name__ == "__main__":
    print("NexaMem Chat ID Functionality Demo")
    print("=" * 50)
    
    demo_auto_generated_chat_id()
    demo_custom_chat_id()
    demo_multiple_sqlite_chats()
    demo_file_storage_separation()
    
    print("Demo completed! 🎉")
