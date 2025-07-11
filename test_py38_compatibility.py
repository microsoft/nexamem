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
        import redis
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
        from nexamem import AIMemory, MemoryScope
        print("✓ nexamem imports successful")
    except Exception as e:
        print(f"✗ nexamem imports failed: {e}")
        traceback.print_exc()
        return False
    
    # Test basic functionality
    try:
        memory = AIMemory(use_fakeredis=True)
        scope = MemoryScope(agent_id='test', user_id='user', session_id='session', env='test')
        
        # Register a default channel
        memory.register_channel(
            name="default",
            ttl_sec=3600,  # 1 hour TTL
            encrypt=False
        )
        
        # Test writing to the channel
        result = memory.write(scope, "default", "Hello, world!")
        print(f"✓ basic functionality test successful: {result}")
    except Exception as e:
        print(f"✗ basic functionality test failed: {e}")
        traceback.print_exc()
        return False
    
    print("✓ All Python 3.8 compatibility tests passed!")
    return True

if __name__ == "__main__":
    success = test_python38_compatibility()
    sys.exit(0 if success else 1)
