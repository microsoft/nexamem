#!/usr/bin/env python3
"""Test summary script for NexaMem new architecture."""

import subprocess
import sys

def run_tests():
    """Run tests and show summary."""
    print("=" * 60)
    print("NexaMem New Architecture - Test Summary")
    print("=" * 60)
    
    # Run tests
    result = subprocess.run([
        sys.executable, "-m", "pytest", "tests/", 
        "-v", "--tb=no", "--quiet"
    ], capture_output=True, text=True, cwd=".")
    
    print("STDOUT:")
    print(result.stdout)
    print("\nSTDERR:")
    print(result.stderr)
    print(f"\nReturn code: {result.returncode}")
    
    if result.returncode == 0:
        print("✅ All tests PASSED!")
    else:
        print("❌ Some tests FAILED")
    
    return result.returncode

if __name__ == "__main__":
    exit_code = run_tests()
    sys.exit(exit_code)
