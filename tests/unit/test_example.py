"""Example unit test - test pure functions with no external dependencies.

Unit tests should be:
- Fast (< 10ms each)
- Isolated (no database, no API calls, no file I/O)
- Focused on testing single functions or classes
"""

import pytest


def add_numbers(a: int, b: int) -> int:
    """Example pure function to test."""
    return a + b


@pytest.mark.unit
def test_add_numbers() -> None:
    """Test basic addition logic."""
    assert add_numbers(2, 3) == 5
    assert add_numbers(-1, 1) == 0
    assert add_numbers(0, 0) == 0
