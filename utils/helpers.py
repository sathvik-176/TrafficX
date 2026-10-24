"""
utils/helpers.py
=================
Small shared utilities used by more than one file. Kept intentionally
minimal on purpose — something only belongs here once at least two
callers would otherwise duplicate the same logic. A "misc" file full of
functions used by exactly one caller is usually a sign the code belongs
in that caller's own file instead.
"""

from typing import Dict

REQUIRED_DIRECTIONS = {"north", "south", "east", "west"}


def validate_directions(direction_counts: Dict[str, dict]) -> None:
    """
    Confirms the exact 4 cardinal directions are present — no more, no
    fewer, no typos like "North" vs "north". Raises ValueError with a
    clear, specific message if not, instead of failing confusingly much
    deeper in the pipeline (e.g. inside signal_timing.py's cycle-time
    math, where a 5th "unknown" direction would silently throw off every
    other direction's allocated seconds).

    Used by both /analyze and /upload in api/traffic.py, so the same
    validation can't drift out of sync between the two endpoints.
    """
    given = set(direction_counts.keys())

    missing = REQUIRED_DIRECTIONS - given
    unexpected = given - REQUIRED_DIRECTIONS

    if missing or unexpected:
        problems = []
        if missing:
            problems.append(f"missing: {sorted(missing)}")
        if unexpected:
            problems.append(f"unexpected: {sorted(unexpected)}")
        raise ValueError(
            f"Direction names must be exactly {sorted(REQUIRED_DIRECTIONS)}. "
            f"Got {sorted(given)} ({'; '.join(problems)})."
        )


if __name__ == "__main__":
    # Quick manual test — run: python -m utils.helpers
    good = {"north": {}, "south": {}, "east": {}, "west": {}}
    validate_directions(good)
    print("PASSED: valid directions accepted silently")

    try:
        bad = {"North": {}, "south": {}, "east": {}, "west": {}}
        validate_directions(bad)
        print("FAILED: should have raised an error for 'North' (capital N)")
    except ValueError as exc:
        print(f"PASSED: correctly rejected bad input -> {exc}")