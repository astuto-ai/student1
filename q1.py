"""
Q1: Stable Character - Student 1 Solution
Perfect implementation
"""


def first_stable_character(s):
    """Find the first stable character in the string."""
    if len(s) <= 1:
        return None

    # Track first and last occurrence of each character
    first_occurrence = {}
    last_occurrence = {}

    for i, char in enumerate(s):
        if char not in first_occurrence:
            first_occurrence[char] = i
        last_occurrence[char] = i

    # Check each character for stability
    for i, char in enumerate(s):
        # Skip if we've already checked this character
        if i != first_occurrence[char]:
            continue

        # Character appears only once - not stable
        if first_occurrence[char] == last_occurrence[char]:
            continue

        # Check if all occurrences are continuous
        start = first_occurrence[char]
        end = last_occurrence[char]
        expected_length = end - start + 1
        actual_count = s.count(char)

        if expected_length == actual_count:
            return char

    return None
