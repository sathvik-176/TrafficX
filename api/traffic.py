
"""
api/traffic.py
===============
FastAPI routes for the traffic analysis pipeline.
"""

import logging
import shutil
import tempfile
import uuid
from pathlib import Path
from typing import Dict

from utils.helpers import validate_directions
from fastapi import APIRouter, UploadFile, File, HTTPException, status

import database.models as db
from schemas.traffic import AnalyzeRequest, AnalyzeResponse
from services.vehicle_detection import detect_all_directions
from services.traffic_analysis import estimate_all_directions
from services.emergency_priority import apply_emergency_priority


# Allow only JPG and PNG image extensions
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}

logger = logging.getLogger("traffic_api.routes.traffic")

router = APIRouter(tags=["Pipeline"])


@router.post("/upload", response_model=AnalyzeResponse)
def upload_videos(
    north: UploadFile = File(...),
    south: UploadFile = File(...),
    east: UploadFile = File(...),
    west: UploadFile = File(...),
):
    """
    Accepts one image per direction, runs the full
    detection -> congestion -> signal-timing -> emergency-priority
    pipeline, saves the result to Supabase, and returns it.
    """
    upload_id = str(uuid.uuid4())

    uploads = {
        "north": north,
        "south": south,
        "east": east,
        "west": west,
    }

    # Validate uploaded file extensions before saving files
    for direction, f in uploads.items():
        if Path(f.filename or "").suffix.lower() not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"{direction}: only .jpg/.jpeg/.png "
                    "images are supported for now"
                ),
            )

    with tempfile.TemporaryDirectory() as tmp_dir:
        direction_files = {}

        for direction, upload_file in uploads.items():
            dest_path = Path(tmp_dir) / f"{direction}_{upload_file.filename}"

            with open(dest_path, "wb") as f:
                shutil.copyfileobj(upload_file.file, f)

            direction_files[direction] = str(dest_path)

        # Run detection before temporary files are deleted
        direction_counts = detect_all_directions(direction_files)

    result = _run_pipeline(upload_id, direction_counts)

    return {"upload_id": upload_id, **result}


@router.post("/analyze", response_model=AnalyzeResponse)
def analyze(request: AnalyzeRequest):
    direction_counts = {
        direction: counts.model_dump()
        for direction, counts in request.directions.items()
    }

    try:
        validate_directions(direction_counts)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )

    upload_id = str(uuid.uuid4())

    result = _run_pipeline(upload_id, direction_counts)

    return {"upload_id": upload_id, **result}


@router.get("/results/{upload_id}")
def get_results(upload_id: str):
    """Fetch previously saved results from Supabase."""
    data = db.fetch_results(upload_id)

    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No results found for upload_id '{upload_id}'",
        )

    return data


def _run_pipeline(
    upload_id: str,
    direction_counts: Dict[str, Dict[str, int]],
) -> dict:
    """
    Shared logic between /upload and /analyze:
      1. Estimate density/congestion per direction.
      2. Compute signal timing and emergency priority.
      3. Persist results to Supabase.
    """
    per_direction = estimate_all_directions(direction_counts)

    green_times, emergency_info = apply_emergency_priority(
        direction_counts
    )

    try:
        db.save_direction_results(
            upload_id,
            per_direction,
            green_times,
        )
    except Exception:
        logger.warning(
            f"Continuing without DB save for upload_id={upload_id}"
        )

    return {
        "per_direction": per_direction,
        "recommended_green_time_seconds": green_times,
        "emergency_priority": emergency_info,
    }
