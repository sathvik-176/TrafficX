"""
services/vehicle_detection.py
==============================
Adapter between Person A's detection module (ml/inference.py) and the rest
of the pipeline. ml/inference.py only knows about ONE feed at a time (one
image/video = one direction); this file's job is to call it once per
direction and assemble the combined multi-direction dictionary that
traffic_analysis.py and signal_timing.py expect.

Keeping this as its own file (rather than looping over directions inside
api/traffic.py directly) keeps the "detection" concern cleanly separated
from the "routing" concern — api/traffic.py just calls one function here
and doesn't need to know anything about how detection actually works.
"""

import logging
from typing import Dict

from ml.inference import detect_vehicles

logger = logging.getLogger("traffic_api.vehicle_detection")

EMPTY_COUNTS = {"vehicle": 0, "emergency": 0}


def detect_all_directions(direction_files: Dict[str, str]) -> Dict[str, Dict[str, int]]:
    """
    direction_files: e.g.
        {
          "north": "/path/to/north_feed.mp4",
          "south": "/path/to/south_feed.mp4",
          "east":  "/path/to/east_feed.jpg",
          "west":  "/path/to/west_feed.mp4",
        }

    Returns: e.g.
        {
          "north": {"vehicle": 12, "emergency": 0},
          "south": {"vehicle": 4,  "emergency": 0},
          ...
        }

    Design note: if detection fails for one direction (corrupt file,
    unreadable video, wrong format), that direction is NOT silently
    dropped from the response — it's returned with all-zero counts and
    the failure is logged. This means one bad upload doesn't take down
    the whole request; the other three directions still process normally.
    """
    results = {}
    for direction, file_path in direction_files.items():
        try:
            results[direction] = detect_vehicles(file_path)
        except Exception as exc:
            logger.error(f"Detection failed for direction '{direction}' ({file_path}): {exc}")
            results[direction] = dict(EMPTY_COUNTS)
    return results


if __name__ == "__main__":
    # Requires real files and a real model — run:
    # python -m services.vehicle_detection north.mp4 south.mp4 east.mp4 west.mp4
    import sys

    if len(sys.argv) < 5:
        print("Usage: python -m services.vehicle_detection <north_file> <south_file> <east_file> <west_file>")
    else:
        files = {
            "north": sys.argv[1],
            "south": sys.argv[2],
            "east": sys.argv[3],
            "west": sys.argv[4],
        }
        print(detect_all_directions(files))