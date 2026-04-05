"""Buggy implementation of calculate_sum."""


def calculate_sum(n):
    """Return sum of 1 to n."""
    # BUG: This returns n * 2 instead of the actual sum
    return n * 2


def main():
    result = calculate_sum(5)
    print(f"Sum of 1 to 5: {result}")


if __name__ == "__main__":
    main()
