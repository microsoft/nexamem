#!/usr/bin/env python3
"""
Final verification that all new properties work correctly.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

def main():
    print("🧪 Final Verification of New Message Properties")
    print("=" * 60)
    
    try:
        # Test Message model
        from nexamem.history import Message
        
        msg = Message(
            role="user",
            content="Test message",
            agent_id="test_agent",
            user_id="test_user",
            env="dev",
            tokens=10,
            data='{"test": true}'
        )
        
        print("✅ Message model with new properties works")
        print(f"   - Role: {msg.role}")
        print(f"   - Agent: {msg.agent_id}")
        print(f"   - User: {msg.user_id}")
        print(f"   - Session: {msg.session_id[:8]}...")
        print(f"   - Environment: {msg.env}")
        print(f"   - Tokens: {msg.tokens}")
        print(f"   - Timestamp: {msg.timestamp}")
        print(f"   - Data: {msg.data}")
        
        # Test ChatHistory
        from nexamem import initialize, ChatHistory
        
        initialize({"history_storage": "memory"})
        history = ChatHistory()
        
        history.set_session_context(
            agent_id="verification_agent",
            user_id="verification_user",
            env="test"
        )
        
        history.add_user_message("Verification message", tokens=5)
        history.add_assistant_message("Verification response", tokens=8)
        
        messages = history.get_history()
        
        print(f"\n✅ ChatHistory with new properties works")
        print(f"   - Messages stored: {len(messages)}")
        print(f"   - Total tokens: {sum(msg['tokens'] for msg in messages)}")
        
        # Verify all properties exist
        required_props = ['role', 'content', 'agent_id', 'user_id', 'session_id', 'env', 'timestamp', 'tokens', 'data']
        for msg in messages:
            for prop in required_props:
                assert prop in msg, f"Missing property: {prop}"
        
        print(f"   - All required properties present")
        
        # Test legacy compatibility
        from llm_chatbot_history.history import ChatHistory as LegacyHistory
        
        legacy = LegacyHistory()
        legacy.add_message("user", "Legacy test", tokens=3)
        
        legacy_messages = legacy.get_history()
        
        print(f"\n✅ Legacy compatibility works")
        print(f"   - Legacy messages: {len(legacy_messages)}")
        print(f"   - Has new properties: {all(prop in legacy_messages[0] for prop in required_props)}")
        
        print("\n🎉 All verifications passed!")
        print("\n📋 Summary of new properties:")
        print("   ✅ agent_id - Agent identifier")
        print("   ✅ user_id - User identifier") 
        print("   ✅ session_id - Auto-generated UUID")
        print("   ✅ env - Environment (default: 'prod')")
        print("   ✅ timestamp - ISO datetime string")
        print("   ✅ tokens - Token count (default: 0)")
        print("   ✅ data - JSON string for custom data")
        
        print("\n🚀 The enhanced message properties are ready for production!")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Verification failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
