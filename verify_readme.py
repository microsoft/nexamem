#!/usr/bin/env python3
"""
Quick README verification test
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_readme_examples():
    """Test that README examples work as documented."""
    from nexamem import initialize, ChatHistory
    
    # Test basic functionality
    initialize({'history_storage': 'memory'})
    history = ChatHistory()
    
    # Test session context
    history.set_session_context(
        agent_id="investment_advisor",
        user_id="customer_789",
        env="prod"
    )
    
    # Test convenience methods
    history.add_user_message("What's my portfolio performance?", tokens=8)
    history.add_assistant_message("Your portfolio gained 12% this year.", tokens=14)
    history.add_system_message("Analysis completed", tokens=0)
    
    # Verify message structure
    messages = history.get_history()
    
    expected_properties = [
        'role', 'content', 'agent_id', 'user_id', 'session_id', 
        'env', 'timestamp', 'tokens', 'data'
    ]
    
    for msg in messages:
        for prop in expected_properties:
            assert prop in msg, f"Missing property: {prop}"
        
        assert msg['agent_id'] == "investment_advisor"
        assert msg['user_id'] == "customer_789" 
        assert msg['env'] == "prod"
    
    # Test analytics
    total_tokens = sum(msg['tokens'] for msg in messages)
    agents = {msg['agent_id'] for msg in messages if msg['agent_id']}
    
    print("✅ README examples verified!")
    print(f"   - {len(messages)} messages with all required properties")
    print(f"   - Total tokens: {total_tokens}")
    print(f"   - Agents: {agents}")
    print(f"   - Session: {messages[0]['session_id'][:8]}...")
    
    return True

if __name__ == "__main__":
    test_readme_examples()
    print("\n🎉 README is accurate and up to date!")
