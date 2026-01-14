"""
Q2: Compressed Stack Length - Student 1 Solution
Perfect implementation
"""


def compressed_stack_length(lst):
    """Calculate remaining stack size after cancellations."""
    stack = []

    for num in lst:
        if stack and stack[-1] == num:
            # Current number matches top of stack - cancel both
            stack.pop()
        else:
            # Add to stack
            stack.append(num)

    return len(stack)
