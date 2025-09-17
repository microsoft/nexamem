#!/usr/bin/env python3
"""
Test script to simulate GitHub Actions workflow locally.
This will verify that pytest-asyncio works correctly in CI/CD environments.
"""

import os
import subprocess
import sys


def main():
    """Simulate GitHub Actions workflow steps."""
    print("🔧 Simulating GitHub Actions workflow...")

    # Change to project directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    # Step 1: Install dependencies (like in GitHub Actions)
    print("\n📦 Installing dependencies (simulating GitHub Actions)...")
    result = subprocess.run([
        sys.executable, "-m", "pip", "install", "-r", "requirements-test.txt"
    ], capture_output=True, text=True)

    if result.returncode != 0:
        print("❌ Failed to install dependencies")
        print("STDERR:", result.stderr)
        return 1

    print("✅ Dependencies installed successfully")

    # Step 2: Install package in editable mode
    print("\n📦 Installing package in editable mode...")
    result = subprocess.run([
        sys.executable, "-m", "pip", "install", "-e", "."
    ], capture_output=True, text=True)

    if result.returncode != 0:
        print("❌ Failed to install package")
        print("STDERR:", result.stderr)
        return 1

    print("✅ Package installed successfully")

    # Step 3: Check if pytest-asyncio is available
    print("\n🔍 Checking pytest-asyncio availability...")
    result = subprocess.run([
        sys.executable, "-c", "import pytest_asyncio; print(f'pytest-asyncio version: {pytest_asyncio.__version__}')"
    ], capture_output=True, text=True)

    if result.returncode != 0:
        print("❌ pytest-asyncio not available")
        print("STDERR:", result.stderr)
        return 1

    print("✅", result.stdout.strip())

    # Step 4: Run async tests specifically
    print("\n🧪 Running async tests...")
    result = subprocess.run([
        sys.executable, "-m", "pytest", "tests/test_async_verification.py", "-v", "--tb=short"
    ], capture_output=True, text=True)

    print("STDOUT:", result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)

    if result.returncode != 0:
        print("❌ Async tests failed")
        return 1

    print("✅ Async tests passed successfully")

    # Step 5: Run all tests
    print("\n🧪 Running all tests...")
    result = subprocess.run([
        sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short"
    ], capture_output=True, text=True)

    if result.returncode != 0:
        print("❌ Some tests failed")
        print("STDOUT:", result.stdout)
        print("STDERR:", result.stderr)
        return 1

    print("✅ All tests passed successfully")

    print("\n🎉 GitHub Actions workflow simulation completed successfully!")
    print("✅ pytest-asyncio is working correctly")
    print("✅ All async tests are passing")
    return 0


if __name__ == "__main__":
    sys.exit(main())
