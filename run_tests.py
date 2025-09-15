#!/usr/bin/env python3
"""
Test runner script for CI/CD pipelines.
Ensures async tests run properly and provides clear exit codes.
"""

import os
import subprocess
import sys


def run_command(cmd, description):
    """Run a command and return success status."""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("✅ SUCCESS")
        if result.stdout:
            print("STDOUT:", result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print("❌ FAILED")
        print("STDOUT:", e.stdout)
        print("STDERR:", e.stderr)
        return False


def main():
    """Main test runner."""
    # Change to project directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    print("NexaMem Test Runner")
    print(f"Working directory: {os.getcwd()}")
    
    # Check Python version
    print(f"Python version: {sys.version}")
    
    # Install test dependencies
    if not run_command([
        sys.executable, "-m", "pip", "install", "-r", "requirements-test.txt"
    ], "Installing test dependencies"):
        return 1
    
    # Run all tests
    if not run_command([
        sys.executable, "-m", "pytest", "tests/", "-v",
        "--tb=short", "--strict-markers", "--strict-config"
    ], "Running all tests"):
        return 1

    # Run async tests specifically
    if not run_command([
        sys.executable, "-m", "pytest", "tests/", "-v",
        "-k", "async", "--tb=short"
    ], "Running async tests"):
        return 1

    # Run tests with coverage
    if not run_command([
        sys.executable, "-m", "pytest", "tests/",
        "--cov=nexamem", "--cov-report=term-missing", "--cov-report=xml"
    ], "Running tests with coverage"):
        return 1
    
    print("\n🎉 All tests passed successfully!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
