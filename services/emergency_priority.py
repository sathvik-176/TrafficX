"""
services/emergency_priority.py
================================
Overrides the normal proportional signal timing when an emergency vehicle
(ambulance, fire truck, police) is detected in any direction — this is
objective 4 of the project.

Design: this file calls signal_timing.allocate_green_time() first to get
the normal, non-emergency allocation, then overrides it only if needed.
It never duplicates the proportional-split logic itself — the single
source of truth for normal allocation stays in signal_timing.py. This
file's only job is deciding WHEN and HOW to override that.
"""

from typing import Dict, Optional, Tuple

from services.signal_timing import allocate_green_time, TOTAL_CYCLE_SECONDS, MIN_GREEN_SECONDS

# How much of the cycle an emergency direction gets when overridden.
# Chosen generously so the emergency vehicle clears the intersection
# quickly, while every other direction still gets its safety-minimum.
EMERGENCY_GREEN_SECONDS = 60


def apply_emergency_priority(
    direction_counts: Dict[str, Dict[str, int]],
    total_cycle: int = TOTAL_CYCLE_SECONDS,
    min_green: int = MIN_GREEN_SECONDS,
    emergency_green: int = EMERGENCY_GREEN_SECONDS,
) -> Tuple[Dict[str, int], Optional[dict]]:
    """
    Returns:
        (allocation, emergency_info)

        allocation: {"north": .., "south": .., ...} — final green times.
                    Equal to the normal proportional split if no
                    emergency vehicle was found, or overridden otherwise.
        emergency_info: None if no override happened, otherwise
                    {"direction": "north", "reason": "..."} explaining
                    what triggered the override — this maps directly to
                    the EmergencyPriorityInfo schema.
    """
    priority_direction = _find_priority_direction(direction_counts)

    if priority_direction is None:
        # No emergency vehicles anywhere — just use the normal allocation.
        return allocate_green_time(direction_counts, total_cycle, min_green), None

    other_directions = [d for d in direction_counts if d != priority_direction]
    n_others = len(other_directions)

    reserved_for_others = min_green * n_others
    effective_emergency_green = emergency_green
    if effective_emergency_green + reserved_for_others > total_cycle:
        # Not enough cycle time to give the full boost while still giving
        # everyone else their minimum — scale it back instead of raising
        # an error mid-demo.
        effective_emergency_green = total_cycle - reserved_for_others

    allocation = {priority_direction: effective_emergency_green}

    # Split whatever time is LEFT OVER among the other directions,
    # proportionally to their vehicle counts (not just a flat minimum) —
    # this keeps the full cycle accounted for and still treats the
    # non-priority directions fairly relative to each other.
    remaining_for_others = total_cycle - effective_emergency_green
    other_counts = {d: direction_counts[d] for d in other_directions}
    others_allocation = allocate_green_time(other_counts, total_cycle=remaining_for_others, min_green=min_green)
    allocation.update(others_allocation)

    emergency_count = direction_counts[priority_direction].get("emergency", 0)
    emergency_info = {
        "direction": priority_direction,
        "reason": (
            f"{emergency_count} emergency vehicle(s) detected in '{priority_direction}' — "
            f"granted {allocation[priority_direction]}s priority green time."
        ),
    }

    return allocation, emergency_info


def _find_priority_direction(direction_counts: Dict[str, Dict[str, int]]) -> Optional[str]:
    """
    Picks which direction gets emergency priority, if any.

    If more than one direction has emergency vehicles at once (rare, but
    possible), the direction with the MOST emergency vehicles wins. Ties
    are broken by picking the direction with the higher total vehicle
    count, since that intersection is under more overall pressure.
    """
    candidates = [
        (direction, counts.get("emergency", 0))
        for direction, counts in direction_counts.items()
        if counts.get("emergency", 0) > 0
    ]

    if not candidates:
        return None

    def sort_key(item):
        direction, emergency_count = item
        total_count = sum(direction_counts[direction].values())
        return (emergency_count, total_count)

    candidates.sort(key=sort_key, reverse=True)
    return candidates[0][0]


if __name__ == "__main__":
    # Quick manual test — run: python -m services.emergency_priority
    sample = {
        "north": {"car": 12, "bike": 5, "bus": 1, "truck": 2, "emergency": 0},
        "south": {"car": 4, "bike": 2, "bus": 0, "truck": 1, "emergency": 1},
        "east": {"car": 8, "bike": 3, "bus": 1, "truck": 0, "emergency": 0},
        "west": {"car": 6, "bike": 1, "bus": 0, "truck": 1, "emergency": 0},
    }
    allocation, info = apply_emergency_priority(sample)
    print("With emergency  ->", allocation, "| sum =", sum(allocation.values()))
    print("Emergency info  ->", info)

    no_emergency = {
        "north": {"car": 12, "bike": 5, "bus": 1, "truck": 2, "emergency": 0},
        "south": {"car": 4, "bike": 2, "bus": 0, "truck": 1, "emergency": 0},
    }
    allocation2, info2 = apply_emergency_priority(no_emergency)
    print("No emergency    ->", allocation2, "| sum =", sum(allocation2.values()))
    print("Emergency info  ->", info2)