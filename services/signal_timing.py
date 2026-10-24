"""
services/signal_timing.py
==========================
Calculates adaptive green-light time allocation across directions, based
on relative vehicle volume.

This function deliberately does NOT know anything about emergency
vehicles — that override logic lives separately in emergency_priority.py,
which calls this function first to get the normal allocation, then
adjusts the result if an emergency vehicle needs priority. Keeping this
file emergency-agnostic means the core allocation formula stays simple,
single-purpose, and testable entirely on its own.
"""

from typing import Dict

TOTAL_CYCLE_SECONDS = 120
MIN_GREEN_SECONDS = 10


def allocate_green_time(
    direction_counts: Dict[str, Dict[str, int]],
    total_cycle: int = TOTAL_CYCLE_SECONDS,
    min_green: int = MIN_GREEN_SECONDS,
) -> Dict[str, int]:
    """
    direction_counts: e.g.
        {
          "north": {"car": 12, "bike": 5, "bus": 1, "truck": 2, "emergency": 0},
          "south": {"car": 4,  "bike": 2, "bus": 0, "truck": 1, "emergency": 0},
        }

    Logic: every direction gets a `min_green` floor first (safety — nobody
    ever gets zero seconds), then the REMAINING cycle time is split
    proportionally to each direction's total vehicle count.

    Returns: {"north": 44, "south": 22, ...} — values sum to `total_cycle`.
    """
    totals = {direction: sum(counts.values()) for direction, counts in direction_counts.items()}
    n = len(totals)
    if n == 0:
        return {}

    remaining = total_cycle - (min_green * n)
    if remaining < 0:
        raise ValueError(
            f"total_cycle ({total_cycle}s) is too small for {n} directions "
            f"with a {min_green}s minimum each. Increase total_cycle or lower min_green."
        )

    grand_total = sum(totals.values())
    allocation: Dict[str, int] = {}

    if grand_total == 0:
        # No vehicles detected anywhere — split the remaining time evenly
        even_share = remaining // n
        for direction in totals:
            allocation[direction] = min_green + even_share
        return allocation

    # Largest-remainder method: rounding each direction's share independently
    # (e.g. plain round()) can lose or gain a second here and there due to
    # rounding drift, so the total stops matching `total_cycle` exactly —
    # a real bug that surfaced during testing. This method guarantees an
    # exact total every time:
    #   1. Give each direction the whole-number (floor) part of its share
    #   2. Whatever seconds are left over (always a small integer) go to
    #      the directions with the largest leftover fractions, one second
    #      each, until the full remaining time is accounted for.
    exact_shares = {d: remaining * (t / grand_total) for d, t in totals.items()}
    floor_shares = {d: int(exact_shares[d]) for d in totals}
    leftover_seconds = remaining - sum(floor_shares.values())

    directions_by_fraction = sorted(
        totals.keys(),
        key=lambda d: exact_shares[d] - floor_shares[d],
        reverse=True,
    )

    for direction in totals:
        allocation[direction] = min_green + floor_shares[direction]

    for direction in directions_by_fraction[:leftover_seconds]:
        allocation[direction] += 1

    return allocation


if __name__ == "__main__":
    # Quick manual test — run: python -m services.signal_timing
    sample = {
        "north": {"car": 12, "bike": 5, "bus": 1, "truck": 2, "emergency": 0},
        "south": {"car": 4, "bike": 2, "bus": 0, "truck": 1, "emergency": 0},
        "east": {"car": 8, "bike": 3, "bus": 1, "truck": 0, "emergency": 0},
        "west": {"car": 6, "bike": 1, "bus": 0, "truck": 1, "emergency": 0},
    }
    result = allocate_green_time(sample)
    print(result, "| sum =", sum(result.values()))