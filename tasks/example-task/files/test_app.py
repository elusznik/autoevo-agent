"""Tests for calculate_sum."""


def calculate_sum(n):
    """Return sum of 1 to n."""
    return n * 2  # Bug! Should be n * (n + 1) / 2


def test_calculate_sum():
    """Test the calculate_sum function."""
    assert calculate_sum(5) == 15, f"Expected 15, got {calculate_sum(5)}"
    assert calculate_sum(10) == 55, f"Expected 55, got {calculate_sum(10)}"
    assert calculate_sum(1) == 1, f"Expected 1, got {calculate_sum(1)}"
    print("All tests passed!")


if __name__ == "__main__":
    test_calculate_sum()
