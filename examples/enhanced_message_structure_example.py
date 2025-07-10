"""
Example: Enhanced Message Structure with Chat ID and Data Field

This example demonstrates NexaMem's enhanced message structure where every message includes:
- role: The message role (user, assistant, etc.)
- content: The actual message content
- chat_id: The unique chat session identifier
- data: Optional JSON string for custom metadata

This enables advanced features like message tracking, analytics, and custom metadata storage.
"""

import json
import tempfile
import os
from nexamem import initialize, ChatHistory

def demo_enhanced_message_structure():
    """Demonstrate the enhanced message structure with all four fields."""
    print("🔍 Enhanced Message Structure Demo")
    print("=" * 50)
    
    # Initialize with a custom chat ID
    initialize({
        "history_storage": "memory",
        "chat_id": "enhanced-demo-session",
        "debug": False
    })
    
    history = ChatHistory()
    
    # Add messages with various data scenarios
    print("\n📝 Adding messages with different metadata scenarios:")
    
    # 1. User message with rich metadata
    user_metadata = {
        "timestamp": "2025-01-10T15:30:00Z",
        "user_id": "user_12345",
        "session_id": "web_session_789",
        "platform": "web",
        "priority": "high",
        "language": "en"
    }
    history.add_message(
        "user", 
        "I need urgent help with my account being locked",
        json.dumps(user_metadata)
    )
    print("   1. ✅ User message with rich metadata (timestamp, user ID, priority, etc.)")
    
    # 2. Assistant response with AI model metadata
    assistant_metadata = {
        "model": "gpt-4",
        "confidence": 0.94,
        "response_time_ms": 250,
        "intent_detected": "account_support",
        "sentiment": "urgent",
        "requires_escalation": False
    }
    history.add_message(
        "assistant",
        "I understand you're having trouble with your account. Let me help you unlock it right away.",
        json.dumps(assistant_metadata)
    )
    print("   2. ✅ Assistant response with AI metadata (model, confidence, intent, etc.)")
    
    # 3. User message without data field (empty string)
    history.add_message("user", "Thank you! That would be great.")
    print("   3. ✅ User message without metadata (data field will be empty)")
    
    # 4. Assistant message with simple data
    history.add_message(
        "assistant",
        "Perfect! I've unlocked your account. You should be able to log in now.",
        '{"action_taken": "account_unlocked", "resolution_time_seconds": 45}'
    )
    print("   4. ✅ Assistant message with simple action metadata")
    
    # 5. System message with workflow data
    system_metadata = {
        "message_type": "system_notification",
        "workflow_step": "resolution_completed",
        "satisfaction_survey_sent": True,
        "case_id": "CASE-2025-001234"
    }
    history.add_message(
        "system",
        "Case resolved successfully. Satisfaction survey sent to user.",
        json.dumps(system_metadata)
    )
    print("   5. ✅ System message with workflow metadata")
    
    # Display the complete enhanced message structure
    print(f"\n📊 Complete Message Analysis:")
    print(f"Chat ID: {history.get_chat_id()}")
    print(f"Total Messages: {len(history.get_history())}")
    
    messages = history.get_history()
    for i, message in enumerate(messages):
        print(f"\n--- Message {i + 1} ---")
        print(f"  Role: {message['role']}")
        print(f"  Content: {message['content']}")
        print(f"  Chat ID: {message['chat_id']}")
        print(f"  Data: {message['data']}")
        
        # Parse and display structured data if present
        if message['data']:
            try:
                parsed_data = json.loads(message['data'])
                print(f"  Parsed Metadata:")
                for key, value in parsed_data.items():
                    print(f"    {key}: {value}")
            except json.JSONDecodeError:
                print(f"    Raw Data: {message['data']}")
    
    print(f"\n✨ Enhanced Message Structure Benefits:")
    print(f"  ✅ Complete traceability with chat_id in every message")
    print(f"  ✅ Flexible metadata storage via data field")
    print(f"  ✅ Easy filtering and analytics by chat session")
    print(f"  ✅ Support for complex workflows and business logic")
    print(f"  ✅ Backward compatible with existing implementations")

def demo_data_field_use_cases():
    """Demonstrate real-world use cases for the data field."""
    print("\n🎯 Data Field Use Cases Demo")
    print("=" * 40)
    
    initialize({
        "history_storage": "memory",
        "chat_id": "use-cases-demo",
        "debug": False
    })
    
    history = ChatHistory()
    
    print("\n📋 Use Case Examples:")
    
    # Use Case 1: Customer Support with Ticket Information
    print("\n1. 💼 Customer Support Ticketing:")
    support_data = {
        "ticket_id": "TICK-2025-5678",
        "customer_tier": "premium",
        "issue_category": "billing",
        "priority": "high",
        "assigned_agent": "agent_sarah_123"
    }
    history.add_message("user", "My billing amount seems incorrect this month", json.dumps(support_data))
    print(f"   Data: {json.dumps(support_data, indent=6)}")
    
    # Use Case 2: A/B Testing and Analytics
    print("\n2. 🧪 A/B Testing & Analytics:")
    analytics_data = {
        "experiment_id": "chat_ui_v2_test", 
        "variant": "treatment_group_b",
        "user_segment": "power_user",
        "session_start_time": "2025-01-10T15:30:00Z",
        "page_context": "/dashboard/billing"
    }
    history.add_message("assistant", "I can help you review your billing details", json.dumps(analytics_data))
    print(f"   Data: {json.dumps(analytics_data, indent=6)}")
    
    # Use Case 3: AI Model Performance Tracking
    print("\n3. 🤖 AI Model Performance:")
    ai_performance_data = {
        "model_version": "gpt-4-turbo-2024-12",
        "confidence_score": 0.92,
        "response_tokens": 156,
        "processing_time_ms": 890,
        "fallback_triggered": False,
        "knowledge_base_used": ["billing_kb_v3", "policy_kb_v1"]
    }
    history.add_message("assistant", "Based on your account, I can see the charge breakdown", json.dumps(ai_performance_data))
    print(f"   Data: {json.dumps(ai_performance_data, indent=6)}")
    
    # Use Case 4: Compliance and Audit Logging
    print("\n4. 📜 Compliance & Audit:")
    compliance_data = {
        "data_classification": "PII",
        "retention_policy": "7_years_financial",
        "access_logged": True,
        "gdpr_consent": True,
        "audit_trail_id": "AUD-2025-0110-1530"
    }
    history.add_message("user", "Can you show me my payment history?", json.dumps(compliance_data))
    print(f"   Data: {json.dumps(compliance_data, indent=6)}")
    
    print(f"\n📈 Analytics Potential:")
    print(f"  • Track conversation success rates by chat_id")
    print(f"  • Monitor AI model performance across sessions")
    print(f"  • Generate business intelligence reports")
    print(f"  • Implement dynamic routing based on metadata")
    print(f"  • Ensure compliance with data retention policies")

def demo_cross_storage_compatibility():
    """Demonstrate that enhanced structure works across all storage backends."""
    print("\n🔄 Cross-Storage Backend Compatibility")
    print("=" * 45)
    
    # Test with SQLite
    print("\n💾 Testing with SQLite storage:")
    db_path = os.path.join(tempfile.gettempdir(), "enhanced_demo.db")
    
    initialize({
        "history_storage": "sqlite",
        "sqlite_path": db_path,
        "chat_id": "sqlite-enhanced-demo",
        "debug": False
    })
    
    sqlite_history = ChatHistory()
    sqlite_history.add_message(
        "user", 
        "Testing SQLite with metadata",
        '{"storage_backend": "sqlite", "test_scenario": "enhanced_structure"}'
    )
    
    messages = sqlite_history.get_history()
    print(f"   ✅ SQLite: Message has {len(messages[0].keys())} fields: {list(messages[0].keys())}")
    
    # Test with file storage
    print("\n📁 Testing with File storage:")
    file_path = os.path.join(tempfile.gettempdir(), "enhanced_demo.json")
    
    initialize({
        "history_storage": "file",
        "file_path": file_path,
        "chat_id": "file-enhanced-demo", 
        "debug": False
    })
    
    file_history = ChatHistory()
    file_history.add_message(
        "assistant",
        "Testing file storage with metadata",
        '{"storage_backend": "file", "persistence": "json_format"}'
    )
    
    messages = file_history.get_history()
    print(f"   ✅ File: Message has {len(messages[0].keys())} fields: {list(messages[0].keys())}")
    
    # Cleanup
    for path in [db_path, file_path.replace('.json', '_file-enhanced-demo.json')]:
        try:
            if os.path.exists(path):
                os.remove(path)
        except OSError:
            pass
    
    print(f"\n🎯 All storage backends support the enhanced 4-field message structure!")

if __name__ == "__main__":
    print("🚀 NexaMem Enhanced Message Structure Examples")
    print("=" * 60)
    
    demo_enhanced_message_structure()
    demo_data_field_use_cases()
    demo_cross_storage_compatibility()
    
    print(f"\n🎉 Demo completed! Key takeaways:")
    print(f"  • Every message now has: role, content, chat_id, data")
    print(f"  • Data field enables rich metadata and business logic")
    print(f"  • Chat ID provides complete conversation traceability")
    print(f"  • All storage backends support the enhanced structure")
    print(f"  • Backward compatible with existing implementations")
