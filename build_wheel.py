#!/usr/bin/env python3
"""Build wheel using setuptools directly"""
import os
import sys
import subprocess
from pathlib import Path

def main():
    # Change to project directory
    project_dir = Path(__file__).parent
    os.chdir(project_dir)
    
    print(f"Building from: {project_dir}")
    print(f"Python: {sys.executable}")
    
    # Clean previous builds
    for cleanup_dir in ["build", "dist", "src/nexamem.egg-info"]:
        cleanup_path = Path(cleanup_dir)
        if cleanup_path.exists():
            import shutil
            shutil.rmtree(cleanup_path)
            print(f"Cleaned: {cleanup_dir}")
    
    try:
        # Build wheel using setup.py sdist bdist_wheel
        cmd = [sys.executable, "setup.py", "bdist_wheel"]
        print(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("Build successful!")
        print(result.stdout)
        
        # List built files
        dist_dir = Path("dist")
        if dist_dir.exists():
            print(f"\nBuilt files in {dist_dir}:")
            for file in dist_dir.iterdir():
                print(f"  {file.name}")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"Build failed: {e}")
        print(f"stdout: {e.stdout}")
        print(f"stderr: {e.stderr}")
        return False
    except FileNotFoundError:
        print("setup.py not found, trying with pyproject.toml build")
        try:
            # Try using pip to build
            cmd = [sys.executable, "-m", "pip", "wheel", ".", "--no-deps"]
            print(f"Running: {' '.join(cmd)}")
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            print("Build successful!")
            print(result.stdout)
            return True
        except subprocess.CalledProcessError as e2:
            print(f"Pip wheel also failed: {e2}")
            print(f"stdout: {e2.stdout}")
            print(f"stderr: {e2.stderr}")
            return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
