#!/usr/bin/env python3
"""
Test script to verify Python 3.8 compatibility.
This script can be run manually to test import compatibility.
"""
import sys
import traceback

def test_python38_compatibility():
    """Test that all imports work correctly in Python 3.8."""
    print(f"Python version: {sys.version}")

    # Test basic imports
    try:
        # Test redis import but don't store reference to avoid unused import warning
        __import__('redis')
        print("✓ redis import successful")
    except Exception as e:
        print(f"✗ redis import failed: {e}")
        return False

    # Test fakeredis import
    try:
        import fakeredis
        print(f"✓ fakeredis import successful (version: {fakeredis.__version__})")
    except Exception as e:
        print(f"✗ fakeredis import failed: {e}")
        traceback.print_exc()
        return False

    # Test nexamem imports
    try:
        from nexamem import AIMemory, AIMemoryConfig, StorageConfig
        print("✓ nexamem imports successful")
    except Exception as e:
        print(f"✗ nexamem imports failed: {e}")
        traceback.print_exc()
        return False

    # Test basic functionality with new API
    try:
        # Create configuration for in-memory storage (fakeredis equivalent)
        storage_config = StorageConfig.memory()
        config = AIMemoryConfig(default_scope="test", storage=storage_config)

        # Create AIMemory instance
        memory = AIMemory(config)

        # Test storing and retrieving
        memory_id = memory.store("Hello, world!", metadata={"type": "test"})
        retrieved = memory.retrieve(memory_id)

        if memory_id and retrieved:
            print(f"✓ basic functionality test successful: stored and retrieved memory {memory_id[:8]}...")
            print(f"  Content: {retrieved['content']}")
        else:
            raise Exception("Failed to store or retrieve memory")
    except Exception as e:
        print(f"✗ basic functionality test failed: {e}")
        traceback.print_exc()
        return False

    print("✓ All Python 3.8 compatibility tests passed!")
    return True

if __name__ == "__main__":
    success = test_python38_compatibility()
    sys.exit(0 if success else 1)
