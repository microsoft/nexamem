#!/usr/bin/env python3
"""
Demo script to show YAML schema validation in action.
"""
import tempfile
import os
from nexamem.channels import validate_yaml_schema, YamlSchemaError, generate_yaml_schema_docs
from nexamem import AIMemory

def main():
    print("=== AIMemory YAML Schema Validation Demo ===\n")
    
    # Print schema documentation
    print("📖 YAML Schema Documentation:")
    print(generate_yaml_schema_docs())
    print("\n" + "="*60 + "\n")
    
    # Test 1: Valid YAML
    print("✅ Test 1: Valid YAML Configuration")
    valid_yaml = """
channels:
  working:
    ttl_sec: 14400      # 4 hours
    encrypt: true
    quota_bytes: 1000000 # 1MB

  procedure:
    ttl_sec: 604800     # 7 days
    encrypt: true

  routing:
    ttl_sec: 86400      # 24 hours
    encrypt: false
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(valid_yaml)
        valid_yaml_path = f.name
    
    try:
        result = validate_yaml_schema(valid_yaml_path)
        print("✅ Validation passed!")
        print(f"   Found {len(result['channels'])} channels: {list(result['channels'].keys())}")
        
        # Test with AIMemory
        memory = AIMemory(
            channels_yaml=valid_yaml_path,
            strict_yaml_validation=True,
            use_fakeredis=True
        )
        print(f"   AIMemory initialized with {len(memory.channels.list_channels())} channels")
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
    finally:
        os.unlink(valid_yaml_path)
    
    print("\n" + "-"*40 + "\n")
    
    # Test 2: Invalid YAML - Bad channel name
    print("❌ Test 2: Invalid Channel Name")
    invalid_yaml1 = """
channels:
  Invalid-Channel:  # Hyphens not allowed
    ttl_sec: 14400
    encrypt: true
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(invalid_yaml1)
        invalid_yaml_path1 = f.name
    
    try:
        validate_yaml_schema(invalid_yaml_path1)
        print("❌ Should have failed validation!")
    except YamlSchemaError as e:
        print("✅ Validation correctly failed:")
        print(f"   Error: {e}")
    finally:
        os.unlink(invalid_yaml_path1)
    
    print("\n" + "-"*40 + "\n")
    
    # Test 3: Invalid YAML - TTL out of range
    print("❌ Test 3: TTL Out of Range")
    invalid_yaml2 = """
channels:
  working:
    ttl_sec: 999999  # Way over 7 days
    encrypt: true
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(invalid_yaml2)
        invalid_yaml_path2 = f.name
    
    try:
        validate_yaml_schema(invalid_yaml_path2)
        print("❌ Should have failed validation!")
    except YamlSchemaError as e:
        print("✅ Validation correctly failed:")
        print(f"   Error: {e}")
    finally:
        os.unlink(invalid_yaml_path2)
    
    print("\n" + "-"*40 + "\n")
    
    # Test 4: Invalid YAML - Unknown field
    print("❌ Test 4: Unknown Field")
    invalid_yaml3 = """
channels:
  working:
    ttl_sec: 14400
    encrypt: true
    unknown_field: "invalid"  # This field doesn't exist
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(invalid_yaml3)
        invalid_yaml_path3 = f.name
    
    try:
        validate_yaml_schema(invalid_yaml_path3)
        print("❌ Should have failed validation!")
    except YamlSchemaError as e:
        print("✅ Validation correctly failed:")
        print(f"   Error: {e}")
    finally:
        os.unlink(invalid_yaml_path3)
    
    print("\n" + "="*60 + "\n")
    print("🎉 Schema validation demo completed!")
    print("\n💡 Key Benefits:")
    print("   • Catches configuration errors early")
    print("   • Provides clear, actionable error messages")
    print("   • Enforces consistent channel naming")
    print("   • Validates TTL and quota limits")
    print("   • Prevents reserved name conflicts")
    print("   • Ensures required fields are present")


if __name__ == "__main__":
    main()
