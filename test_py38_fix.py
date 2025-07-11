#!/usr/bin/env python3
"""Test script to verify Python 3.8 compatibility fix."""

import sys
from typing import Tuple, List, Dict, Any

def test_function() -> Tuple[List[str], Dict[str, Any]]:
    """Test function with the fixed tuple annotation."""
    return ["test"], {"status": "success"}

def main():
    print(f"Python version: {sys.version}")
    print("Testing tuple annotation syntax...")
    
    try:
        result = test_function()
        print(f"✓ Function call successful: {result}")
        
        # Test the actual imports that were failing
        from nexamem.new_aimemory import AIMemory, AsyncAIMemory
        print("✓ AIMemory imports successful")
        
        from nexamem.config.aimemory import AIMemoryConfig
        print("✓ AIMemoryConfig import successful")
        
        print("🎉 All Python 3.8 compatibility tests passed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return 1
        
    return 0

if __name__ == "__main__":
    sys.exit(main())
