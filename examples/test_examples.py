#!/usr/bin/env python3
"""
Simple test to validate our examples are working correctly.
"""
import sys
import os
import tempfile

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from nexamem.channels import validate_yaml_schema, YamlSchemaError, ChannelManager
from nexamem import AIMemory, MemoryScope

def test_schema_validation():
    """Test schema validation with valid and invalid examples."""
    print("🔍 Testing Schema Validation...")
    
    # Test valid configuration
    valid_yaml = """
channels:
  working:
    ttl_sec: 14400
    encrypt: true
    quota_bytes: 1000000
  
  routing:
    ttl_sec: 86400
    encrypt: false
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(valid_yaml)
        valid_path = f.name
    
    try:
        result = validate_yaml_schema(valid_path)
        print("✅ Valid YAML configuration passed validation")
        print(f"   Found {len(result['channels'])} channels: {list(result['channels'].keys())}")
    except Exception as e:
        print(f"❌ Valid YAML failed: {e}")
    finally:
        os.unlink(valid_path)
    
    # Test invalid configuration
    invalid_yaml = """
channels:
  Invalid-Name:  # Hyphens not allowed
    ttl_sec: 14400
    encrypt: true
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(invalid_yaml)
        invalid_path = f.name
    
    try:
        validate_yaml_schema(invalid_path)
        print("❌ Invalid YAML should have failed validation")
    except YamlSchemaError as e:
        print("✅ Invalid YAML correctly rejected")
        print(f"   Error: {str(e)[:80]}...")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
    finally:
        os.unlink(invalid_path)


def test_aimemory_integration():
    """Test AIMemory with schema validation."""
    print("\n🧠 Testing AIMemory Integration...")
    
    # Create test channels
    channels_yaml = """
channels:
  working:
    ttl_sec: 14400
    encrypt: true
    quota_bytes: 1000000
  
  debug_logs:
    ttl_sec: 3600
    encrypt: false
    quota_bytes: 500000
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(channels_yaml)
        channels_path = f.name
    
    try:
        # Test with strict validation (default)
        memory = AIMemory(
            channels_yaml=channels_path,
            strict_yaml_validation=True,
            use_fakeredis=True
        )
        
        channels = memory.list_channels()
        print(f"✅ AIMemory initialized with {len(channels)} channels")
        
        # Test dynamic registration
        memory.register_channel(
            name="scratch_pad",
            ttl_sec=300,  # 5 minutes
            encrypt=False
        )
        
        updated_channels = memory.list_channels()
        print(f"✅ Dynamic registration works: {len(updated_channels)} channels total")
        
        # Test scope and basic operations
        scope = MemoryScope(
            agent_id="test_agent",
            user_id="user123", 
            session_id="session456",
            env="test"
        )
        
        message_uuid = memory.write(
            scope=scope,
            channel="working",
            content="Test message for validation"
        )
        
        messages, metadata = memory.read(
            scope=scope,
            channel="working"
        )
        
        print(f"✅ Write/read operations work: {len(messages)} messages retrieved")
        
    except Exception as e:
        print(f"❌ AIMemory integration failed: {e}")
    finally:
        os.unlink(channels_path)


def test_default_channels():
    """Test that default channels.yaml is valid."""
    print("\n📋 Testing Default Channels Configuration...")
    
    try:
        # Test the default channels.yaml file
        default_path = os.path.join(os.path.dirname(__file__), '..', 'channels.yaml')
        if os.path.exists(default_path):
            result = validate_yaml_schema(default_path)
            print("✅ Default channels.yaml is valid")
            print(f"   Contains {len(result['channels'])} channels: {list(result['channels'].keys())}")
            
            for name, config in result['channels'].items():
                ttl_hours = config['ttl_sec'] // 3600
                encrypt = config.get('encrypt', False)
                quota = config.get('quota_bytes')
                quota_str = f", quota={quota//1000}KB" if quota else ""
                print(f"   • {name}: {ttl_hours}h TTL, encrypt={encrypt}{quota_str}")
        else:
            print("❌ Default channels.yaml not found")
            
    except Exception as e:
        print(f"❌ Default channels validation failed: {e}")


def main():
    print("🚀 AIMemory Examples Validation Test")
    print("=" * 50)
    
    test_schema_validation()
    test_aimemory_integration()
    test_default_channels()
    
    print("\n" + "=" * 50)
    print("🎉 Examples validation completed!")


if __name__ == "__main__":
    main()
