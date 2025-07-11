#!/usr/bin/env python3
"""
Simple test runner script for NexaMem/AIMemory
Provides easy access to different test categories and configurations.
"""
import argparse
import subprocess
import sys
from pathlib import Path


def run_command(cmd, description):
    """Run a command and handle errors."""
    print(f"\n🧪 {description}")
    print(f"Command: {' '.join(cmd)}")
    print("-" * 50)

    try:
        subprocess.run(cmd, check=True, cwd=Path(__file__).parent)
        print(f"✅ {description} completed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed with exit code {e.returncode}")
        return False


def main():
    parser = argparse.ArgumentParser(description="NexaMem Test Runner")
    parser.add_argument(
        "category",
        nargs="?",
        default="all",
        choices=[
            "all", "quick", "core", "features", "legacy",
            "fresh", "coverage", "lint", "format"
        ],
        help="Test category to run"
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--no-cov", action="store_true", help="Skip coverage report")
    
    args = parser.parse_args()
    
    # Base pytest command
    base_cmd = [sys.executable, "-m", "pytest"]
    if args.verbose:
        base_cmd.append("-v")
    
    success = True
    
    if args.category == "all":
        # Run all tests with coverage
        cmd = base_cmd + ["tests/"]
        if not args.no_cov:
            cmd.extend(["--cov=nexamem", "--cov-report=html", "--cov-report=term-missing"])
        success = run_command(cmd, "Running all tests")
        
    elif args.category == "quick":
        # Run fast tests only
        cmd = base_cmd + ["tests/", "-m", "not slow"]
        success = run_command(cmd, "Running quick tests")
        
    elif args.category == "core":
        # Run core AIMemory functionality tests (working tests)
        cmd = base_cmd + [
            "tests/test_working_basic.py",
            "tests/test_memory_scope.py",
        ]
        success = run_command(cmd, "Running core functionality tests")
        
    elif args.category == "features":
        # Run feature-specific tests
        cmd = base_cmd + [
            "tests/test_fresh_comprehensive.py::TestFreshPolicyEngine",
            "tests/test_fresh_comprehensive.py::TestFreshMetrics",
            "tests/test_fresh_comprehensive.py::TestFreshAuditSink",
            "tests/test_fresh_comprehensive.py::TestFreshConfig",
        ]
        success = run_command(cmd, "Running feature-specific tests")
        
    elif args.category == "legacy":
        # Run legacy API tests
        cmd = base_cmd + [
            "tests/test_channels.py",
            "tests/test_memory_scope.py",
            "tests/test_policy.py",
            "tests/test_content_processor.py",
            "tests/test_aimemory.py",
        ]
        success = run_command(cmd, "Running legacy API tests")
        
    elif args.category == "fresh":
        # Run only the new comprehensive tests
        cmd = base_cmd + ["tests/test_fresh_comprehensive.py"]
        success = run_command(cmd, "Running fresh comprehensive tests")
        
    elif args.category == "coverage":
        # Run tests with detailed coverage report
        cmd = base_cmd + [
            "tests/",
            "--cov=nexamem",
            "--cov-report=html",
            "--cov-report=term-missing",
            "--cov-report=xml",
        ]
        success = run_command(cmd, "Running tests with coverage report")
        print("\n📊 Coverage report generated in htmlcov/index.html")
        
    elif args.category == "lint":
        # Run linting
        commands = [
            ([sys.executable, "-m", "ruff", "check", "src/", "tests/"], "Running Ruff linter"),
            ([sys.executable, "-m", "mypy", "src/"], "Running MyPy type checker"),
        ]
        
        for cmd, desc in commands:
            if not run_command(cmd, desc):
                success = False

    elif args.category == "format":
        # Run formatting
        cmd = [sys.executable, "-m", "ruff", "format", "src/", "tests/"]
        success = run_command(cmd, "Formatting code with Ruff")
    
    if success:
        print("\n🎉 All operations completed successfully!")
        return 0
    else:
        print("\n💥 Some operations failed. Check the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
