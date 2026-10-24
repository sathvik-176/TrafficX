"""
database/models.py
===================
Read/write functions for the traffic_results table. This is the only file
that runs actual queries against Supabase — services and api routes call
functions from here instead of talking to `supabase` directly. If the
table structure ever changes, this is the only file that needs to change.
"""

import logging
from typing import Dict, List

from database.connection import supabase

logger = logging.getLogger("traffic_api.models")


def save_direction_results(
    upload_id: str,
    per_direction: Dict[str, dict],
    green_times: Dict[str, int],
) -> None:
    """
    Writes one row per direction into traffic_results.

    per_direction: e.g.
        {
          "north": {"counts": {"car": 12, ...}, "density": 1.0,
                     "congestion_level": "High", "has_emergency": False},
          ...
        }
    green_times: e.g. {"north": 44, "south": 22, ...}
    """
    rows = []
    for direction, info in per_direction.items():
        counts = info["counts"]
        rows.append({
            "upload_id": upload_id,
            "direction": direction,
            "vehicle_count": counts.get("vehicle", 0),
            "emergency_count": counts.get("emergency", 0),
            "density": info["density"],
            "congestion_level": info["congestion_level"],
            "green_time_seconds": green_times.get(direction, 0),
        })

    try:
        supabase.table("traffic_results").insert(rows).execute()
        logger.info(f"Saved {len(rows)} rows for upload_id={upload_id}")
    except Exception as exc:
        logger.error(f"Failed to save results for upload_id={upload_id}: {exc}")
        raise


def fetch_results(upload_id: str) -> List[dict]:
    """Fetches all direction rows for a given upload_id, most recent first."""
    try:
        response = (
            supabase.table("traffic_results")
            .select("*")
            .eq("upload_id", upload_id)
            .order("created_at", desc=True)
            .execute()
        )
        return response.data
    except Exception as exc:
        logger.error(f"Failed to fetch results for upload_id={upload_id}: {exc}")
        raise


def fetch_recent(limit: int = 20) -> List[dict]:
    """
    Fetches the most recent N rows across all uploads — useful later for
    a 'recent activity' view on Person C's frontend dashboard.
    """
    try:
        response = (
            supabase.table("traffic_results")
            .select("*")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return response.data
    except Exception as exc:
        logger.error(f"Failed to fetch recent results: {exc}")
        raise