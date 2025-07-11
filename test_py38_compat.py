#!/usr/bin/env python3
"""Simple Python 3.8+ compatibility test"""
import sys

def main():
    print(f"Python version: {sys.version_info}")
    
    # Test typing imports (Python 3.8 compatible)
    from typing import Dict, List, Optional, Union
    print("✓ typing imports work")
    
    # Test that we can import the package
    try:
        import nexamem
        print(f"✓ nexamem imported successfully, version: {nexamem.__version__}")
    except ImportError as e:
        print(f"✗ Failed to import nexamem: {e}")
        return False
    
    # Test basic classes
    try:
        from nexamem import MemoryScope, ChannelConfig
        scope = MemoryScope(agent_id="test", user_id="user123", session_id="session123")
        config = ChannelConfig(name="test_channel", ttl_sec=3600)
        print("✓ Basic classes work")
    except Exception as e:
        print(f"✗ Basic classes failed: {e}")
        return False
    
    # Test pydantic validation
    try:
        from nexamem import ChannelConfig
        from pydantic import ValidationError
        
        # Test valid config
        config = ChannelConfig(name="valid_name", ttl_sec=3600)
        print(f"✓ Valid config created: {config.name}")
        
        # Test invalid config should raise ValidationError
        try:
            ChannelConfig(name="Invalid-Name", ttl_sec=3600)
            print("✗ Should have failed validation")
            return False
        except ValidationError:
            print("✓ Validation works correctly")
            
    except Exception as e:
        print(f"✗ Pydantic validation test failed: {e}")
        return False
    
    print("✅ All Python 3.8+ compatibility tests passed!")
    return True

if __name__ == "__main__":
    success = main()
    if not success:
        sys.exit(1)
