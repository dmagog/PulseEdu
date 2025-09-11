"""
Basic tests to verify testing setup works.
"""
import pytest


def test_basic_math():
    """Test basic math operations."""
    assert 2 + 2 == 4
    assert 3 * 3 == 9


def test_string_operations():
    """Test string operations."""
    text = "Hello, World!"
    assert len(text) == 13
    assert "World" in text


def test_list_operations():
    """Test list operations."""
    numbers = [1, 2, 3, 4, 5]
    assert len(numbers) == 5
    assert sum(numbers) == 15


@pytest.mark.parametrize("input_value,expected", [
    (1, 1),
    (2, 4),
    (3, 9),
    (4, 16),
])
def test_square_function(input_value, expected):
    """Test square function with parametrized inputs."""
    assert input_value ** 2 == expected


class TestBasicClass:
    """Test class structure."""
    
    def test_instance_creation(self):
        """Test creating class instance."""
        class SimpleClass:
            def __init__(self, value):
                self.value = value
        
        obj = SimpleClass(42)
        assert obj.value == 42
    
    def test_method_calling(self):
        """Test calling class methods."""
        class Calculator:
            def add(self, a, b):
                return a + b
        
        calc = Calculator()
        assert calc.add(2, 3) == 5
