import sys
import os
import pytest
from nexamem import initialize

# Ensure the src directory is on sys.path for test discovery
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))


@pytest.fixture(autouse=True)
def reset_nexamem_state():
    """Reset NexaMem configuration state before each test."""
    # Reset the global config state
    import nexamem.config
    nexamem.config._config = None
    
    # Initialize with memory storage as default for tests
    initialize({"history_storage": "memory", "debug": False})
    
    yield
    
    # Clean up after test
    nexamem.config._config = None
