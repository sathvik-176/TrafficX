"""
services/traffic_analysis.py
=============================
Estimates traffic density and congestion level from vehicle counts.

This is pure calculation logic with no dependencies on FastAPI, Supabase,
or YOLO — it takes numbers in and returns numbers/labels out. That makes
it independently testable (see the __main__ block below) and reusable
anywhere in the app.
"""

from typing import Dict, Tuple

# Tunable settings — adjust these based on what you observe in Week 4
# testing against your real sample videos. Document your final choice
# and reasoning in your report.
DEFAULT_CAPACITY_PER_DIRECTION = 20   # assumed max comfortable vehicles per direction
LOW_THRESHOLD = 0.3                    # density below this => "Low"
MEDIUM_THRESHOLD = 0.6                 # density below this (and above LOW) => "Medium"
                                        # anything at or above MEDIUM_THRESHOLD => "High"


def estimate_congestion(
    counts: Dict[str, int],
    capacity: int = DEFAULT_CAPACITY_PER_DIRECTION,
) -> Tuple[float, str]:
    """
    Calculates density and congestion level for one direction.

    Args:
        counts: e.g. {"car": 12, "bike": 5, "bus": 1, "truck": 2, "emergency": 0}
                Any dict of category -> count works; emergency vehicles are
                counted toward density too, since they still occupy road space.
        capacity: assumed max comfortable vehicle count for this direction.

    Returns:
        (density, congestion_level) e.g. (0.6, "High")
    """
    total_vehicles = sum(counts.values())
    density = total_vehicles / capacity if capacity > 0 else 0.0

    if density < LOW_THRESHOLD:
        level = "Low"
    elif density < MEDIUM_THRESHOLD:
        level = "Medium"
    else:
        level = "High"

    return round(density, 3), level


def estimate_all_directions(
    direction_counts: Dict[str, Dict[str, int]],
    capacity: int = DEFAULT_CAPACITY_PER_DIRECTION,
) -> Dict[str, dict]:
    """
    Convenience wrapper: runs estimate_congestion() for every direction at once.

    Args:
        direction_counts: e.g.
            {
              "north": {"car": 12, "bike": 5, "bus": 1, "truck": 2, "emergency": 0},
              "south": {"car": 4,  "bike": 2, "bus": 0, "truck": 1, "emergency": 0},
            }

    Returns:
        {
          "north": {"counts": {...}, "density": 1.0, "congestion_level": "High", "has_emergency": False},
          "south": {"counts": {...}, "density": 0.35, "congestion_level": "Medium", "has_emergency": False},
        }
    """
    results = {}
    for direction, counts in direction_counts.items():
        density, level = estimate_congestion(counts, capacity)
        results[direction] = {
            "counts": counts,
            "density": density,
            "congestion_level": level,
            "has_emergency": counts.get("emergency", 0) > 0,
        }
    return results


if __name__ == "__main__":
    # Quick manual test — run: python -m services.traffic_analysis
    sample = {
        "north": {"car": 12, "bike": 5, "bus": 1, "truck": 2, "emergency": 0},
        "south": {"car": 4, "bike": 2, "bus": 0, "truck": 1, "emergency": 1},
    }
    for direction, result in estimate_all_directions(sample).items():
        print(direction, "->", result)