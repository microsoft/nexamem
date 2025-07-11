#!/usr/bin/env python3
"""
NexaMem ChatHistory Demo - Demonstrates the enhanced message properties.

This script shows how to use the new message properties including:
- agent_id, user_id, session_id, env
- timestamp, tokens, data
- Convenience methods and session context
- All storage backends (memory, file, SQLite)
"""

import os
import sys
import tempfile
import json
from datetime import datetime

# Add src to path for local testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from nexamem import initialize, ChatHistory, get_config


def demo_basic_usage():
    """Demonstrate basic usage with new properties."""
    print("🗂️  Basic ChatHistory Demo")
    print("=" * 50)
    
    # Initialize with memory storage
    initialize({"history_storage": "memory", "debug": True})
    
    history = ChatHistory()
    
    # Set session context (applies to all future messages)
    print("📋 Setting session context...")
    history.set_session_context(
        agent_id="portfolio_agent",
        user_id="customer_789",
        env="prod"
    )
    
    # Add messages using convenience methods
    print("💬 Adding conversation messages...")
    history.add_user_message(
        "What's the performance of my investment portfolio?",
        tokens=12
    )
    
    history.add_assistant_message(
        "Your portfolio has gained 8.5% this year, outperforming the S&P 500 by 2.1%.",
        tokens=18,
        data='{"confidence": 0.95, "sources": ["market_data", "portfolio_db"]}'
    )
    
    history.add_system_message(
        "Portfolio analysis completed",
        tokens=4,
        data='{"execution_time_ms": 250, "cache_hit": true}'
    )
    
    # Get and display history
    messages = history.get_history()
    print(f"\n📖 Retrieved {len(messages)} messages:")
    
    for i, msg in enumerate(messages, 1):
        print(f"\n  Message {i}:")
        print(f"    Role: {msg['role']}")
        print(f"    Content: {msg['content'][:60]}...")
        print(f"    Agent: {msg['agent_id']}")
        print(f"    User: {msg['user_id']}")
        print(f"    Session: {msg['session_id'][:8]}...")
        print(f"    Environment: {msg['env']}")
        print(f"    Timestamp: {msg['timestamp']}")
        print(f"    Tokens: {msg['tokens']}")
        if msg['data']:
            try:
                data_obj = json.loads(msg['data'])
                print(f"    Data: {data_obj}")
            except:
                print(f"    Data: {msg['data']}")
    
    print(f"\n✅ Basic demo completed!")
    return history


def demo_file_storage():
    """Demonstrate file storage with persistence."""
    print("\n💾 File Storage Demo")
    print("=" * 50)
    
    # Create temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_file = f.name
    
    try:
        # Initialize with file storage
        initialize({
            "history_storage": "file",
            "file_path": temp_file,
            "debug": True
        })
        
        print(f"📁 Using file: {temp_file}")
        
        # Create history and add messages
        history = ChatHistory()
        
        # Add messages with custom properties
        history.add_message(
            "user",
            "How should I rebalance my portfolio?",
            agent_id="rebalance_agent",
            user_id="investor_456",
            session_id="session_xyz789",
            env="staging",
            tokens=15,
            data='{"portfolio_value": 125000, "risk_tolerance": "moderate"}'
        )
        
        history.add_message(
            "assistant",
            "Based on your risk profile, I recommend increasing bonds to 30% and reducing tech stocks to 40%.",
            agent_id="rebalance_agent",
            user_id="investor_456",
            session_id="session_xyz789",
            env="staging",
            tokens=28,
            data='{"recommendation_id": "RB_2025_001", "confidence": 0.87}'
        )
        
        # Verify persistence by creating new instance
        print("🔄 Testing persistence...")
        history2 = ChatHistory()
        messages = history2.get_history()
        
        print(f"📖 Loaded {len(messages)} messages from file:")
        for msg in messages:
            print(f"  - {msg['role']}: {msg['content'][:50]}... (tokens: {msg['tokens']})")
        
        print("✅ File storage demo completed!")
        
    finally:
        # Clean up
        if os.path.exists(temp_file):
            os.unlink(temp_file)


def demo_sqlite_storage():
    """Demonstrate SQLite storage with querying."""
    print("\n🗄️  SQLite Storage Demo")
    print("=" * 50)
    
    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        temp_db = f.name
    
    try:
        # Initialize with SQLite storage
        initialize({
            "history_storage": "sqlite",
            "sqlite_path": temp_db,
            "debug": True
        })
        
        print(f"📊 Using database: {temp_db}")
        
        history = ChatHistory()
        
        # Add diverse messages for querying
        test_data = [
            {
                "role": "user",
                "content": "What are my investment options?",
                "agent_id": "advisor_bot",
                "user_id": "client_123",
                "env": "prod",
                "tokens": 8
            },
            {
                "role": "assistant", 
                "content": "You have several options: stocks, bonds, ETFs, and mutual funds.",
                "agent_id": "advisor_bot",
                "user_id": "client_123",
                "env": "prod",
                "tokens": 16
            },
            {
                "role": "user",
                "content": "Tell me about ETFs",
                "agent_id": "etf_specialist",
                "user_id": "client_123", 
                "env": "prod",
                "tokens": 5
            },
            {
                "role": "assistant",
                "content": "ETFs are exchange-traded funds that track market indices with low fees.",
                "agent_id": "etf_specialist",
                "user_id": "client_123",
                "env": "prod", 
                "tokens": 14
            }
        ]
        
        for data in test_data:
            history.add_message(**data)
        
        # Demonstrate querying capabilities
        print("🔍 Testing SQLite queries...")
        
        # Query by agent
        advisor_messages = history.query_sqlite("agent_id = ?", ("advisor_bot",))
        print(f"📋 Messages from advisor_bot: {len(advisor_messages)}")
        
        # Query by token count
        high_token_messages = history.query_sqlite("tokens > ?", (10,))
        print(f"🎯 High-token messages (>10): {len(high_token_messages)}")
        
        # Query by role
        user_messages = history.query_sqlite("role = ?", ("user",))
        print(f"👤 User messages: {len(user_messages)}")
        
        # Show detailed results
        print("\n📋 Detailed query results:")
        for msg in high_token_messages:
            print(f"  - {msg['role']} ({msg['tokens']} tokens): {msg['content'][:40]}...")
            print(f"    Agent: {msg['agent_id']}, Time: {msg['timestamp']}")
        
        print("✅ SQLite demo completed!")
        
    finally:
        # Clean up - close connection first
        if hasattr(history, '_conn'):
            history._conn.close()
        if os.path.exists(temp_db):
            try:
                os.unlink(temp_db)
            except PermissionError:
                print(f"[DEBUG] Could not delete {temp_db} - file in use")


def demo_migration_compatibility():
    """Demonstrate backward compatibility and migration."""
    print("\n🔄 Migration & Compatibility Demo")
    print("=" * 50)
    
    # Test legacy compatibility
    print("🔗 Testing legacy compatibility...")
    
    from llm_chatbot_history.history import ChatHistory as LegacyHistory
    
    legacy_history = LegacyHistory()
    legacy_history.add_message("user", "Legacy message test")
    legacy_history.add_message("assistant", "This should work with new properties", 
                              tokens=10, agent_id="legacy_agent")
    
    messages = legacy_history.get_history()
    print(f"📜 Legacy history: {len(messages)} messages")
    
    for msg in messages:
        print(f"  - {msg['role']}: {msg['content'][:30]}...")
        print(f"    Has new properties: agent_id='{msg['agent_id']}', tokens={msg['tokens']}")
    
    print("✅ Legacy compatibility verified!")


def demo_advanced_features():
    """Demonstrate advanced features and use cases."""
    print("\n🚀 Advanced Features Demo")  
    print("=" * 50)
    
    initialize({"history_storage": "memory", "debug": False})
    
    history = ChatHistory()
    
    # Scenario: Multi-agent conversation
    print("🤖 Multi-agent conversation scenario...")
    
    # Customer service handoff
    history.add_message(
        "user",
        "I need help with my account",
        user_id="customer_999",
        env="prod",
        tokens=7
    )
    
    history.add_message(
        "assistant", 
        "I'll help you with that. Let me transfer you to a specialist.",
        agent_id="general_support",
        user_id="customer_999",
        env="prod",
        tokens=14,
        data='{"transfer_reason": "account_issue", "urgency": "medium"}'
    )
    
    history.add_message(
        "system",
        "Transferred to account specialist",
        agent_id="system",
        user_id="customer_999", 
        env="prod",
        tokens=0,
        data='{"transfer_time": "2025-07-11T14:30:00", "from_agent": "general_support", "to_agent": "account_specialist"}'
    )
    
    history.add_message(
        "assistant",
        "Hello! I'm an account specialist. I can see you need help with your account.",
        agent_id="account_specialist",
        user_id="customer_999",
        env="prod", 
        tokens=16,
        data='{"specialist_level": 2, "previous_context_reviewed": true}'
    )
    
    # Analyze conversation
    messages = history.get_history()
    total_tokens = sum(msg['tokens'] for msg in messages)
    agents_involved = set(msg['agent_id'] for msg in messages if msg['agent_id'])
    
    print(f"📊 Conversation analysis:")
    print(f"  - Total messages: {len(messages)}")
    print(f"  - Total tokens used: {total_tokens}")
    print(f"  - Agents involved: {', '.join(agents_involved)}")
    print(f"  - Environment: {messages[0]['env']}")
    print(f"  - Session: {messages[0]['session_id'][:8]}...")
    
    # Show conversation flow
    print(f"\n💬 Conversation flow:")
    for i, msg in enumerate(messages, 1):
        agent_info = f" [{msg['agent_id']}]" if msg['agent_id'] else ""
        token_info = f" ({msg['tokens']} tokens)" if msg['tokens'] > 0 else ""
        print(f"  {i}. {msg['role']}{agent_info}: {msg['content'][:50]}...{token_info}")
    
    print("✅ Advanced features demo completed!")


def main():
    """Run all demos."""
    print("🎯 NexaMem ChatHistory Enhanced Properties Demo")
    print("=" * 60)
    print("Demonstrating the new message properties based on AIMemory requirements:")
    print("- agent_id, user_id, session_id, env")
    print("- timestamp, tokens, data")
    print("- All storage backends")
    print("- Advanced querying and analytics")
    print()
    
    try:
        demo_basic_usage()
        demo_file_storage() 
        demo_sqlite_storage()
        demo_migration_compatibility()
        demo_advanced_features()
        
        print("\n🎉 All demos completed successfully!")
        print("\n📚 Key features demonstrated:")
        print("✅ Enhanced Message model with all required properties")
        print("✅ Session context management")
        print("✅ Convenience methods for different roles")
        print("✅ File and SQLite persistence")
        print("✅ Advanced SQLite querying")
        print("✅ Legacy compatibility")
        print("✅ Multi-agent conversation tracking")
        print("✅ Token usage analytics")
        print("✅ Custom data payload support")
        
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
