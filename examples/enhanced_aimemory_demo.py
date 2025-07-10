#!/usr/bin/env python3
"""
Enhanced AIMemory Demo - Showcases new features aligned with requirements.

This demo shows:
- Content processing with PII detection/redaction
- Audit logging to Redis Stream  
- Metrics collection
- All requirements compliance
"""

import asyncio
import tempfile
import os
import json

from nexamem import (
    AIMemory, MemoryScope, PIIRedactor, 
    ContentEnricher, metrics
)


def create_enhanced_channels_yaml():
    """Create a channels configuration that matches the requirements."""
    channels_config = {
        'channels': {
            'working': {
                'ttl_sec': 14400,  # 4 hours
                'encrypt': True,
                'quota_bytes': 1000000  # 1MB
            },
            'procedure': {
                'ttl_sec': 604800,  # 7 days
                'encrypt': True,
                'quota_bytes': 5000000  # 5MB
            },
            'routing': {
                'ttl_sec': 86400,  # 24 hours
                'encrypt': False,
                'quota_bytes': 100000  # 100KB
            }
        }
    }
    
    # Create temporary YAML file
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False)
    
    # Write YAML content
    temp_file.write("# AIMemory Channels Configuration - Requirements Compliant\n")
    temp_file.write("channels:\n")
    for channel_name, config in channels_config['channels'].items():
        temp_file.write(f"  {channel_name}:\n")
        temp_file.write(f"    ttl_sec: {config['ttl_sec']}\n")
        temp_file.write(f"    encrypt: {config['encrypt']}\n")
        if config.get('quota_bytes'):
            temp_file.write(f"    quota_bytes: {config['quota_bytes']}\n")
    
    temp_file.close()
    return temp_file.name


def demo_enhanced_features():
    """Demonstrate enhanced AIMemory features."""
    print("🚀 Enhanced AIMemory Demo - Requirements v0.3 Compliant")
    print("=" * 60)
    
    # Create channels configuration
    channels_yaml = create_enhanced_channels_yaml()
    
    try:
        # Initialize AIMemory with all new features enabled
        memory = AIMemory(
            channels_yaml=channels_yaml,
            use_fakeredis=True,
            enable_audit=True,
            enable_metrics=True,
            enable_content_processing=True  # Enable the content processor chain
        )
        
        # Create MemoryScope matching requirements format
        scope = MemoryScope(
            agent_id="invest_agent",
            user_id="u12345",  # hashed customer id
            session_id="s98765",  # chat session uuid  
            env="prod"  # environment isolation
        )
        
        print(f"📍 MemoryScope: {scope.agent_id}:{scope.user_id}:{scope.session_id}")
        print(f"🌍 Environment: {scope.env}")
        print(f"🔑 Key format: {scope.get_key_prefix('working')}:{{uuid}}")
        print()
        
        # Demonstrate content processing with PII detection
        print("🛡️  Content Processing with PII Detection")
        print("-" * 50)
        
        # Add custom content processors
        memory.content_processor.add_processor(PIIRedactor())
        memory.content_processor.add_processor(ContentEnricher())
        
        # Write content with PII that will be auto-detected and redacted
        pii_content = "Customer John Doe called about his account. Email: john.doe@email.com, Phone: 555-123-4567"
        
        working_uuid = memory.write(
            scope=scope,
            channel="working",
            content=pii_content,
            auto_pii=True  # Enable auto-PII detection
        )
        print(f"✅ Wrote content with auto-PII detection: {working_uuid[:8]}...")
        
        # Read back to see processed content
        messages, metadata = memory.read(scope=scope, channel="working")
        print(f"📖 Retrieved message: {messages[0][:80]}...")
        print(f"📊 Metadata: {json.dumps(metadata, indent=2)}")
        print()
        
        # Demonstrate different channels per requirements
        print("📺 Channel Usage per Requirements")
        print("-" * 50)
        
        # Orchestrator uses routing and working
        memory.write(
            scope=scope,
            channel="routing",
            content="topic=investments, confidence=0.95, next_agent=portfolio_specialist"
        )
        print("✅ Orchestrator -> routing channel")
        
        # Domain agents use working and procedure  
        memory.write(
            scope=scope,
            channel="procedure",
            content="Completed risk assessment step, proceed to portfolio analysis"
        )
        print("✅ Domain agent -> procedure channel")
        print()
        
        # Demonstrate dynamic channel registration (requirements 7.1)
        print("🔧 Dynamic Channel Registration")
        print("-" * 50)
        
        memory.register_channel(
            name="scratch",
            ttl_sec=60,  # 1 minute
            encrypt=False,
            quota_bytes=1000000  # 1MB quota
        )
        print("✅ Registered 'scratch' channel (60s TTL)")
        
        scratch_uuid = memory.write(
            scope=scope,
            channel="scratch",
            content="Temporary calculation: risk_score = 0.75"
        )
        print(f"✅ Wrote to scratch channel: {scratch_uuid[:8]}...")
        print()
        
        # Demonstrate checkpoint operations
        print("📋 Checkpoint Operations")
        print("-" * 50)
        
        # Set workflow checkpoint
        memory.checkpoint(scope, "workflow_state", {
            "current_step": "risk_assessment",
            "completed_steps": ["onboarding", "kyc"],
            "progress": 0.6
        })
        print("✅ Set workflow checkpoint")
        
        # Atomic update
        def advance_workflow(current_state):
            if current_state is None:
                return {"current_step": "start", "progress": 0.0}
            
            steps = ["onboarding", "kyc", "risk_assessment", "portfolio_analysis", "complete"]
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
        print(f"✅ Advanced workflow: {updated_state['current_step']} ({updated_state['progress']:.0%})")
        print()
        
        # Show metrics
        print("📊 Metrics Collection")
        print("-" * 50)
        
        all_metrics = metrics.get_metrics().get_all_metrics()
        
        print("Counters:")
        for metric_name, count in all_metrics['counters'].items():
            print(f"  {metric_name}: {count}")
        
        print("\nLatency Histograms:")
        for metric_name, stats in all_metrics['histograms'].items():
            if stats['count'] > 0:
                print(f"  {metric_name}: avg={stats['avg']:.3f}s, count={stats['count']}")
        print()
        
        # Show audit records (if available)
        print("📝 Audit Trail")
        print("-" * 50)
        
        if memory.audit:
            try:
                recent_records = memory.audit.get_audit_records(count=5)
                print(f"Recent audit records ({len(recent_records)}):")
                for record in recent_records[-3:]:  # Show last 3
                    print(f"  {record['timestamp']:.0f}: {record['operation']} -> {record.get('channel', 'N/A')}")
            except Exception as e:
                print(f"⚠️  Audit records not available: {e}")
        print()
        
        # Demonstrate bulk operations
        print("🧹 Bulk Operations")
        print("-" * 50)
        
        # Count bytes across channels
        total_bytes = 0
        for channel in ["working", "routing", "procedure", "scratch"]:
            try:
                bytes_count = memory.count_bytes(scope, channel)
                total_bytes += bytes_count
                print(f"📊 {channel}: {bytes_count} bytes")
            except Exception:
                pass
        
        print(f"📊 Total: {total_bytes} bytes")
        
        # Clean up
        deleted_keys = memory.bulk_erase(scope)
        print(f"🗑️  Bulk erased {deleted_keys} keys")
        
    finally:
        # Cleanup
        if os.path.exists(channels_yaml):
            os.unlink(channels_yaml)


async def demo_async_features():
    """Demonstrate async AIMemory features."""
    print("\n🔄 Async AIMemory Demo")
    print("=" * 50)
    
    print("📝 Async AIMemory API example:")
    print("""
from nexamem import AsyncAIMemory

async_memory = AsyncAIMemory(
    redis_host="your-redis-host",
    redis_port=6379,
    enable_audit=True,
    enable_metrics=True
)

scope = MemoryScope(
    agent_id="async_agent", 
    user_id="user_456",
    session_id="session_xyz"
)

# All operations are async
message_uuid = await async_memory.write(
    scope=scope,
    channel="working",
    content="Async message"
)

messages, metadata = await async_memory.read(
    scope=scope,
    channel="working"
)

await async_memory.close()  # Important!
""")


def main():
    """Run the enhanced demo."""
    print("🎯 AIMemory Enhanced Demo - Fully Requirements Compliant")
    print("=" * 70)
    print("This demo showcases AIMemory v0.3 with all MVP requirements:")
    print("  • Redis-backed channels with user-defined YAML config")
    print("  • Sync and async client classes")  
    print("  • Policy enforcement (TTL, encryption, quota)")
    print("  • Content processor chain with PII detection/redaction")
    print("  • Audit sink mirroring operations to Redis Stream")
    print("  • Base metrics capturing (Prometheus-style)")
    print("  • Dynamic channel registration at runtime")
    print("  • MemoryScope with env isolation")
    print("  • Checkpoint operations for workflow state")
    print()
    
    # Run synchronous demo
    demo_enhanced_features()
    
    # Run async demo (conceptual)
    asyncio.run(demo_async_features())
    
    print("\n✅ Enhanced demo completed! AIMemory v0.3 is requirements-compliant.")
    print("\n📚 Key requirements implemented:")
    print("  ✓ Architecture: Caller → AIMemory → PolicyEngine → RedisAdapter")
    print("  ✓ MemoryScope: {env}:{agent_id}:{user_id}:{session_id}:{channel}:{uuid}")
    print("  ✓ Channels: YAML config + dynamic registration")
    print("  ✓ Policy Rules: TTL, Encryption, Quota, PII protection")
    print("  ✓ Content Processing: Optional redaction/enrichment chain")
    print("  ✓ Audit Sink: Operations mirrored to Redis Stream (365d TTL)")
    print("  ✓ Metrics: Prometheus counters and latency histograms")


if __name__ == "__main__":
    main()
