"""
Simple test to verify our fresh test setup works.
"""
import pytest


def test_simple_addition():
    """Simple test to verify pytest is working."""
    assert 2 + 2 == 4


def test_simple_string():
    """Simple test to verify string operations."""
    assert "hello".upper() == "HELLO"


class TestBasicFunctionality:
    """Basic test class to verify class-based tests work."""

    def test_list_operations(self):
        """Test basic list operations."""
        my_list = [1, 2, 3]
        my_list.append(4)
        assert len(my_list) == 4
        assert my_list[-1] == 4

    def test_dict_operations(self):
        """Test basic dictionary operations."""
        my_dict = {"key": "value"}
        my_dict["new_key"] = "new_value"
        assert len(my_dict) == 2
        assert my_dict["key"] == "value"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
