#!/usr/bin/env python3
"""
AIMemory Demo Script - Demonstrates the new Redis-backed memory system.

This script shows how to use AIMemory for governed conversational memory
with channels, policies, and scope-based access control.
"""

import asyncio
import tempfile
import os

# Import AIMemory components
from nexamem import (
    AIMemory, MemoryScope, 
    ChannelAlreadyExists, QuotaExceeded, EncryptionRequired
)


def create_demo_channels_yaml():
    """Create a demo channels configuration file."""
    content = """
channels:
  working:
    ttl_sec: 14400      # 4 hours
    encrypt: true

  procedure:
    ttl_sec: 604800     # 7 days
    encrypt: true

  routing:
    ttl_sec: 86400      # 24 hours
    encrypt: false

  debug:
    ttl_sec: 3600       # 1 hour
    encrypt: false
    quota_bytes: 10000  # 10KB daily quota
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(content.strip())
        return f.name


def demo_sync_aimemory():
    """Demonstrate synchronous AIMemory usage."""
    print("🧠 AIMemory Synchronous Demo")
    print("=" * 50)
    
    # Create demo channels configuration
    channels_yaml = create_demo_channels_yaml()
    
    try:
        # Initialize AIMemory with fakeredis for demo
        memory = AIMemory(
            channels_yaml=channels_yaml,
            use_fakeredis=True  # Use fake Redis for demo
        )
        
        # Create memory scope for an investment agent
        scope = MemoryScope(
            agent_id="invest_agent",
            user_id="user_12345",
            session_id="session_abc",
            env="demo"
        )
        
        print(f"📍 Created scope: {scope.agent_id}:{scope.user_id}:{scope.session_id}")
        print(f"🌍 Environment: {scope.env}")
        print()
        
        # List available channels
        channels = memory.list_channels()
        print("📺 Available channels:")
        for name, config in channels.items():
            print(f"  - {name}: TTL={config.ttl_sec}s, Encrypt={config.encrypt}")
        print()
        
        # Write messages to different channels
        print("✍️  Writing messages...")
        
        # Working memory - recent conversation
        working_uuid = memory.write(
            scope=scope,
            channel="working",
            content="User asked about investment portfolio diversification"
        )
        print(f"   Working channel: {working_uuid[:8]}...")
        
        # Routing hints
        routing_uuid = memory.write(
            scope=scope,
            channel="routing", 
            content="topic=investments, confidence=0.95, next_agent=portfolio_specialist"
        )
        print(f"   Routing channel: {routing_uuid[:8]}...")
        
        # Procedure checkpoint
        procedure_uuid = memory.write(
            scope=scope,
            channel="procedure",
            content="Completed risk assessment step, proceed to portfolio analysis"
        )
        print(f"   Procedure channel: {procedure_uuid[:8]}...")
        print()
        
        # Read messages back
        print("📖 Reading messages...")
        
        working_msgs, working_meta = memory.read(scope=scope, channel="working")
        print(f"   Working ({working_meta['total_messages']} msgs): {working_msgs[0][:50]}...")
        
        routing_msgs, routing_meta = memory.read(scope=scope, channel="routing")
        print(f"   Routing ({routing_meta['total_messages']} msgs): {routing_msgs[0][:50]}...")
        print()
        
        # Demonstrate policy enforcement
        print("🛡️  Testing policy enforcement...")
        
        try:
            # Try to write PII to non-encrypted channel
            memory.write(
                scope=scope,
                channel="routing",  # encrypt=false
                content="Customer SSN: 123-45-6789",
                pii=True
            )
        except EncryptionRequired as e:
            print(f"   ✅ Policy blocked PII in non-encrypted channel: {e}")
        
        try:
            # Test quota enforcement
            large_content = "x" * 5000  # 5KB
            memory.write(scope=scope, channel="debug", content=large_content)
            memory.write(scope=scope, channel="debug", content=large_content)
            memory.write(scope=scope, channel="debug", content=large_content)  # Should exceed 10KB quota
        except QuotaExceeded as e:
            print(f"   ✅ Quota enforcement working: {e}")
        print()
        
        # Register new channel at runtime
        print("🔧 Dynamic channel registration...")
        try:
            memory.register_channel(
                name="scratch_pad",
                ttl_sec=300,  # 5 minutes
                encrypt=False,
                quota_bytes=1000
            )
            print("   ✅ Registered 'scratch_pad' channel")
            
            # Use the new channel
            scratch_uuid = memory.write(
                scope=scope,
                channel="scratch_pad",
                content="Temporary calculation: risk_score = 0.75"
            )
            print(f"   ✅ Wrote to scratch_pad: {scratch_uuid[:8]}...")
            
        except ChannelAlreadyExists as e:
            print(f"   ⚠️  Channel already exists: {e}")
        print()
        
        # Checkpoint operations
        print("📋 Checkpoint operations...")
        
        # Set initial checkpoint
        memory.checkpoint(scope, "workflow_state", {
            "current_step": "risk_assessment",
            "completed_steps": ["onboarding", "kyc_verification"],
            "progress": 0.6
        })
        print("   ✅ Set workflow checkpoint")
        
        # Atomic update
        def advance_workflow(current_state):
            if current_state is None:
                return {"current_step": "start", "progress": 0.0}
            
            steps = ["onboarding", "kyc_verification", "risk_assessment", "portfolio_analysis", "complete"]
            current_step = current_state.get("current_step", "start")
            
            try:
                current_index = steps.index(current_step)
                if current_index < len(steps) - 1:
                    next_step = steps[current_index + 1]
                    return {
                        "current_step": next_step,
                        "completed_steps": steps[:current_index + 1],
                        "progress": (current_index + 1) / len(steps)
                    }
            except ValueError:
                pass
            
            return current_state
        
        updated_state = memory.checkpoint_atomic(scope, "workflow_state", advance_workflow)
        print(f"   ✅ Advanced workflow: {updated_state['current_step']} ({updated_state['progress']:.0%})")
        print()
        
        # Count bytes and cleanup
        print("🧹 Cleanup operations...")
        
        total_bytes = sum(
            memory.count_bytes(scope, channel) 
            for channel in ["working", "routing", "procedure"]
        )
        print(f"   📊 Total bytes stored: {total_bytes}")
        
        deleted_keys = memory.bulk_erase(scope)
        print(f"   🗑️  Deleted {deleted_keys} keys")
        
    finally:
        # Cleanup temp file
        if os.path.exists(channels_yaml):
            os.unlink(channels_yaml)


async def demo_async_aimemory():
    """Demonstrate asynchronous AIMemory usage."""
    print("\n🚀 AIMemory Asynchronous Demo")
    print("=" * 50)
    
    # Create demo channels configuration
    channels_yaml = create_demo_channels_yaml()
    
    try:
        # For demo purposes, we'll show the API but skip actual async operations
        # since fakeredis async support requires additional setup
        print("📝 Async AIMemory would be used like this:")
        print("""
async_memory = AsyncAIMemory(
    redis_host="your-redis-host",
    redis_port=6379,
    channels_yaml="channels.yaml"
)

scope = MemoryScope(
    agent_id="async_agent",
    user_id="user_456", 
    session_id="session_xyz"
)

# Async operations
message_uuid = await async_memory.write(
    scope=scope,
    channel="working",
    content="Async message"
)

messages, metadata = await async_memory.read(
    scope=scope,
    channel="working"
)

await async_memory.close()  # Important: close connection
""")
        
    finally:
        # Cleanup temp file
        if os.path.exists(channels_yaml):
            os.unlink(channels_yaml)


def main():
    """Run the complete AIMemory demo."""
    print("🎯 AIMemory Demo - Redis-backed Conversational Memory")
    print("=" * 60)
    print("This demo showcases the new AIMemory system with:")
    print("  • Channel-based organization")
    print("  • Policy enforcement (TTL, encryption, quotas)")
    print("  • Scope-based access control")
    print("  • PII detection and protection")
    print("  • Dynamic channel registration")
    print("  • Checkpoint operations")
    print("  • Both sync and async APIs")
    print()
    
    # Run synchronous demo
    demo_sync_aimemory()
    
    # Run asynchronous demo
    asyncio.run(demo_async_aimemory())
    
    print("\n✅ Demo completed! AIMemory is ready for production use.")
    print("\n📚 Next steps:")
    print("  1. Configure Redis connection for your environment")
    print("  2. Create channels.yaml with your specific channels")
    print("  3. Set up proper authentication and SSL for production")
    print("  4. Integrate with your AI agents and orchestrators")


if __name__ == "__main__":
    main()
