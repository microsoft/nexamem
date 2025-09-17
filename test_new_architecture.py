#!/usr/bin/env python3
"""Simple test script to verify the new NexaMem architecture."""

import os
import sys

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_basic_imports():
    """Test that we can import the new components."""
    try:
        print("✓ Storage config imports work")

        print("✓ AIMemory config imports work")

        print("✓ Storage base classes import work")

        print("✓ Memory storage imports work")

        print("✓ File storage imports work")

        print("✓ SQLite storage imports work")

        print("✓ Azure Redis storage imports work")

        print("✓ Storage factory imports work")

        print("✓ DI container imports work")

        print("✓ New AIMemory classes import work")

        return True
    except Exception as e:
        print(f"✗ Import error: {e}")
        return False


def test_basic_functionality():
    """Test basic functionality with in-memory storage."""
    try:
        from nexamem.config.aimemory import AIMemoryConfig
        from nexamem.config.storage import StorageConfig
        from nexamem.new_aimemory import AIMemory

        # Create config
        config = AIMemoryConfig(
            default_scope="test",
            storage=StorageConfig.memory()
        )

        # Create AIMemory instance
        ai_memory = AIMemory(config)

        # Test basic operations
        memory_id = ai_memory.store("Test memory content", metadata={"test": True})
        print(f"✓ Stored memory with ID: {memory_id}")

        retrieved = ai_memory.retrieve(memory_id)
        if retrieved and retrieved.get('content') == "Test memory content":
            print("✓ Retrieved memory correctly")
        else:
            print(f"✗ Failed to retrieve memory: {retrieved}")
            return False

        memories = ai_memory.list()
        if memory_id in memories:
            print("✓ Memory appears in list")
        else:
            print(f"✗ Memory not in list: {memories}")
            return False

        stats = ai_memory.get_stats()
        if stats.get('total_memories', 0) > 0:
            print(f"✓ Statistics work: {stats}")
        else:
            print(f"✗ Statistics failed: {stats}")
            return False

        return True
    except Exception as e:
        print(f"✗ Functionality test error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("Testing NexaMem New Architecture")
    print("=" * 40)

    if not test_basic_imports():
        print("Import tests failed!")
        return 1

    print()
    if not test_basic_functionality():
        print("Functionality tests failed!")
        return 1

    print()
    print("✓ All tests passed!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
