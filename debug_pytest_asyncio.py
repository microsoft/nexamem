#!/usr/bin/env python3
"""
Debug script for pytest-asyncio issues in CI/CD environments.

This script helps diagnose common pytest-asyncio issues:
1. Check if pytest-asyncio is properly installed
2. Verify asyncio mode configuration
3. Test basic async functionality
4. Provide troubleshooting information
"""

import asyncio
import subprocess
import sys


def check_pytest_asyncio():
    """Check if pytest-asyncio is installed and its version."""
    try:
        import pytest_asyncio
        print(f"✓ pytest-asyncio is installed: {pytest_asyncio.__version__}")
        return True
    except ImportError:
        print("✗ pytest-asyncio is not installed")
        return False


def check_pytest():
    """Check pytest installation and version."""
    try:
        import pytest
        print(f"✓ pytest is installed: {pytest.__version__}")
        return True
    except ImportError:
        print("✗ pytest is not installed")
        return False


def check_asyncio_functionality():
    """Test basic asyncio functionality."""
    try:
        async def test_async():
            await asyncio.sleep(0.001)
            return "success"
        
        result = asyncio.run(test_async())
        print(f"✓ Basic asyncio functionality works: {result}")
        return True
    except Exception as e:
        print(f"✗ Basic asyncio functionality failed: {e}")
        return False


def check_pytest_config():
    """Check for pytest configuration files."""
    import os
    config_files = ['pytest.ini', 'pyproject.toml', 'tox.ini', 'setup.cfg']
    found_configs = []
    
    for config_file in config_files:
        if os.path.exists(config_file):
            found_configs.append(config_file)
    
    if found_configs:
        print(f"✓ Found pytest config files: {', '.join(found_configs)}")
        
        # Check pytest.ini specifically
        if 'pytest.ini' in found_configs:
            with open('pytest.ini') as f:
                content = f.read()
                if 'asyncio_mode' in content:
                    print("✓ asyncio_mode found in pytest.ini")
                else:
                    print("⚠ asyncio_mode not found in pytest.ini")
    else:
        print("⚠ No pytest configuration files found")


def run_pytest_version_check():
    """Run pytest --version to check installation."""
    try:
        result = subprocess.run([sys.executable, '-m', 'pytest', '--version'],
                              capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✓ pytest --version output: {result.stdout.strip()}")
        else:
            print(f"✗ pytest --version failed: {result.stderr}")
    except Exception as e:
        print(f"✗ Failed to run pytest --version: {e}")


def run_pytest_markers_check():
    """Check if asyncio marker is available."""
    try:
        result = subprocess.run([sys.executable, '-m', 'pytest', '--markers'],
                              capture_output=True, text=True)
        if result.returncode == 0:
            if 'asyncio' in result.stdout:
                print("✓ asyncio marker is available in pytest")
            else:
                print("⚠ asyncio marker not found in pytest markers")
        else:
            print(f"✗ pytest --markers failed: {result.stderr}")
    except Exception as e:
        print(f"✗ Failed to run pytest --markers: {e}")


def main():
    """Run all diagnostic checks."""
    print("=== pytest-asyncio Diagnostic Script ===")
    print(f"Python version: {sys.version}")
    print(f"Python executable: {sys.executable}")
    print()
    
    checks = [
        check_pytest,
        check_pytest_asyncio,
        check_asyncio_functionality,
        check_pytest_config,
        run_pytest_version_check,
        run_pytest_markers_check,
    ]
    
    results = []
    for check in checks:
        try:
            result = check()
            results.append(result)
        except Exception as e:
            print(f"✗ Check {check.__name__} failed with exception: {e}")
            results.append(False)
        print()
    
    print("=== Summary ===")
    passed = sum(1 for r in results if r is True)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("✓ All checks passed - pytest-asyncio should work correctly")
    else:
        print("⚠ Some checks failed - there may be issues with pytest-asyncio")
        print("\nTroubleshooting tips:")
        print("1. Install pytest-asyncio: pip install pytest-asyncio")
        print("2. Add 'asyncio_mode = auto' to pytest.ini")
        print("3. Use '--asyncio-mode=auto' command line option")
        print("4. Ensure pytest-asyncio plugin is loaded: -p pytest_asyncio")


if __name__ == "__main__":
    main()
