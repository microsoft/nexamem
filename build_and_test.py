#!/usr/bin/env python3
"""
Build script to verify Python 3.8+ compatibility and build wheel
"""
import os
import subprocess
import sys


def main():
    """Build the wheel and check compatibility"""
    print(f"Python version: {sys.version}")
    print(f"Python executable: {sys.executable}")

    # Change to project directory
    project_dir = r"c:\Users\chadada\source\repos\nexamem"
    os.chdir(project_dir)
    print(f"Working directory: {os.getcwd()}")

    try:
        # Install build if not available
        print("Installing build package...")
        subprocess.run([sys.executable, "-m", "pip", "install", "build"], check=True)

        # Build the wheel
        print("Building wheel...")
        result = subprocess.run([sys.executable, "-m", "build", "--wheel"], check=True, capture_output=True, text=True)
        print("Wheel build completed successfully!")
        print(result.stdout)

        # List the dist directory
        dist_dir = os.path.join(project_dir, "dist")
        if os.path.exists(dist_dir):
            print(f"\nContents of {dist_dir}:")
            for item in os.listdir(dist_dir):
                print(f"  {item}")

        # Try importing the package to verify it works
        print("\nTesting package import...")
        import nexamem
        print(f"Package version: {nexamem.__version__}")
        print("Import successful!")

        # Test basic class instantiation
        from nexamem import ChannelConfig, MemoryScope
        _ = MemoryScope(agent_id="test", user_id="user123", session_id="session123")
        _ = ChannelConfig(name="test_channel", ttl_sec=3600)
        print("Basic functionality test passed!")

        return True

    except subprocess.CalledProcessError as e:
        print(f"Error during build: {e}")
        print(f"stdout: {e.stdout}")
        print(f"stderr: {e.stderr}")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
