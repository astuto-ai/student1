"""
Q3: Event Overload Detector - Student 1 Solution
Perfect implementation
"""


def find_overloaded_users(events):
    """Identify users with 3+ events within any 10-second window."""
    if not events:
        return set()

    # Group events by user
    user_events = {}
    for user_id, timestamp in events:
        if user_id not in user_events:
            user_events[user_id] = []
        user_events[user_id].append(timestamp)

    overloaded = set()

    # Check each user for overload
    for user_id, timestamps in user_events.items():
        # Sort timestamps
        timestamps.sort()

        # Check sliding window of 10 seconds
        for i in range(len(timestamps)):
            # Count events within 10 seconds from current event
            count = 0
            for j in range(i, len(timestamps)):
                if timestamps[j] - timestamps[i] < 10:
                    count += 1
                else:
                    break

            # If 3 or more events in window, user is overloaded
            if count >= 3:
                overloaded.add(user_id)
                break

    return overloaded
