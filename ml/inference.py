"""
ml/inference.py
================
Loads TWO trained YOLOv8 models and runs vehicle detection on a single
image or video:

  1. GENERAL model (best.pt)      - detects "any vehicle" (single class,
                                     trained on the top-view vehicle dataset)
  2. EMERGENCY model (emergency.pt) - detects ambulances specifically
                                       (trained on a separate ambulance dataset)

Both models run independently on the SAME source and their results are
combined into one counts dict. This design was chosen deliberately over
training one merged model, because fine-tuning a single model only on
ambulance images would risk "catastrophic forgetting" of its general
vehicle-detection ability - two focused models are safer and each is
individually easier to explain and evaluate.

Returns counts for ONE traffic feed (one camera / one direction) - NOT
combined across directions. Combining counts from multiple directions
happens one level up, in services/vehicle_detection.py, which calls
detect_vehicles() once per direction's footage.

IMPORTANT DESIGN NOTE: video is handled differently from images on
purpose. Summing every detection across every frame of a video would
massively overcount - the same physical vehicle sitting in view for 100
frames would otherwise be counted 100 times. For video, this file uses
YOLO's built-in tracker (assigns a consistent ID to each object across
frames) and only counts each track ID once PER MODEL - the general
model's track IDs and the emergency model's track IDs are separate
numbering systems and are never compared to each other.
"""

from __future__ import annotations  # lets type hints reference YOLO without
                                     # importing it at module load time

import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ultralytics import YOLO

logger = logging.getLogger("traffic_api.inference")

MODEL_DIR = Path(__file__).parent / "model"
GENERAL_MODEL_PATH = MODEL_DIR / "best.pt"
EMERGENCY_MODEL_PATH = MODEL_DIR / "emergency.pt"

CONFIDENCE_THRESHOLD = 0.4

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp"}
VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv"}

# Each model has its OWN class names, so each gets its own map.
# General model: trained on "Top-View Vehicle Detection" dataset (nc:1,
# names:['Vehicle']) - single class, no type breakdown.
GENERAL_CLASS_MAP = {
    "Vehicle": "vehicle",
    "vehicle": "vehicle",  # lowercase variant, just in case
}

# Emergency model: trained on a Roboflow ambulance dataset whose single
# class happened to be named 'storbow' (an artifact of however the
# original dataset creator labeled it - just a text label, doesn't
# affect training). Mapped here to our actual field name "emergency".
EMERGENCY_CLASS_MAP = {
    "storbow": "emergency",
    "ambulance": "emergency",  # kept in case a future dataset uses this name instead
}

_general_model = None    # loaded once, lazily, and reused across calls
_emergency_model = None  # loaded once, lazily, and reused across calls


def _load_model(model_path: Path):
    from ultralytics import YOLO  # imported here, not at module top - so
    # anything that imports this file doesn't force-load YOLO/PyTorch
    # unless detection is actually run.

    if not model_path.exists():
        raise FileNotFoundError(
            f"Model weights not found at {model_path}. "
            f"Make sure the file is placed inside ml/model/."
        )
    logger.info(f"Loading YOLO model from {model_path}")
    model = YOLO(str(model_path))
    logger.info(f"Model classes: {model.names}")
    return model


def _get_general_model():
    global _general_model
    if _general_model is None:
        _general_model = _load_model(GENERAL_MODEL_PATH)
    return _general_model


def _get_emergency_model():
    global _emergency_model
    if _emergency_model is None:
        _emergency_model = _load_model(EMERGENCY_MODEL_PATH)
    return _emergency_model


def detect_vehicles(source: str, confidence: float = CONFIDENCE_THRESHOLD) -> Dict[str, int]:
    """
    Runs BOTH models on a single image or video file and returns combined
    counts for that ONE feed.

    Returns e.g. {"vehicle": 14, "emergency": 1}
    """
    ext = Path(source).suffix.lower()
    if ext not in VIDEO_EXTENSIONS and ext not in IMAGE_EXTENSIONS:
        raise ValueError(f"Unsupported file type '{ext}'. Expected an image or video file.")

    general_model = _get_general_model()
    emergency_model = _get_emergency_model()

    run_fn = _run_tracking if ext in VIDEO_EXTENSIONS else _run_detection

    general_detections = run_fn(general_model, source, confidence)
    emergency_detections = run_fn(emergency_model, source, confidence)

    general_counts = _aggregate_detections(general_detections, GENERAL_CLASS_MAP)
    emergency_counts = _aggregate_detections(emergency_detections, EMERGENCY_CLASS_MAP)

    return {
        "vehicle": general_counts.get("vehicle", 0),
        "emergency": emergency_counts.get("emergency", 0),
    }


def _run_detection(model: YOLO, source: str, confidence: float) -> List[Tuple[Optional[int], str]]:
    """Single image: every detection is counted, since there are no repeated frames."""
    results = model.predict(source=source, conf=confidence, verbose=False)
    detections = []
    for frame_result in results:
        for box in frame_result.boxes:
            class_name = model.names[int(box.cls[0])]
            detections.append((None, class_name))  # track_id=None -> always counted
    return detections


def _run_tracking(model: YOLO, source: str, confidence: float) -> List[Tuple[Optional[int], str]]:
    """Video: uses YOLO's tracker so each physical object is only counted once."""
    results = model.track(source=source, conf=confidence, persist=True, verbose=False)
    detections = []
    for frame_result in results:
        if frame_result.boxes.id is None:
            continue  # no tracked objects in this frame
        for box, track_id in zip(frame_result.boxes, frame_result.boxes.id):
            class_name = model.names[int(box.cls[0])]
            detections.append((int(track_id), class_name))
    return detections


def _aggregate_detections(
    detections: List[Tuple[Optional[int], str]],
    class_map: Dict[str, str],
) -> Dict[str, int]:
    """
    Turns a list of (track_id, class_name) pairs into final category counts,
    using whichever class_map matches the model that produced them.

      - track_id = None   -> count every detection (used for single images)
      - track_id = an int -> only count the FIRST time this ID appears
                              (used for video, to avoid counting the same
                              physical object multiple times across frames)

    This function has zero dependency on YOLO itself, so it can be unit
    tested with made-up data - see the __main__ block below.
    """
    counts: Dict[str, int] = {}
    seen_track_ids = set()

    for track_id, class_name in detections:
        if track_id is not None:
            if track_id in seen_track_ids:
                continue
            seen_track_ids.add(track_id)

        category = class_map.get(class_name)
        if category:
            counts[category] = counts.get(category, 0) + 1
        else:
            print(f"Unmapped class ignored: {class_name}")

    return counts


if __name__ == "__main__":
    # Two kinds of test here:
    #
    # 1. Pure logic test (no models/video needed) - proves the dedup logic
    #    itself is correct for BOTH class maps: run with no arguments.
    #
    # 2. Real test against actual files - requires both best.pt and
    #    emergency.pt to be in place. Run:
    #    python -m ml.inference /path/to/sample.mp4

    import sys

    if len(sys.argv) < 2:
        print("No file given — running a logic-only test of _aggregate_detections()\n")

        # General model: vehicle #1 appears 3 times, vehicle #2 twice
        fake_general_detections = [
            (101, "Vehicle"), (101, "Vehicle"), (101, "Vehicle"),
            (102, "Vehicle"), (102, "Vehicle"),
        ]
        general_result = _aggregate_detections(fake_general_detections, GENERAL_CLASS_MAP)
        print("General model (deduplicated):", general_result)
        assert general_result["vehicle"] == 2, "Expected 2 unique vehicles, not 4 raw detections"
        print("PASSED\n")

        # Emergency model: one ambulance ('storbow'), tracked across 2 frames
        fake_emergency_detections = [(201, "storbow"), (201, "storbow")]
        emergency_result = _aggregate_detections(fake_emergency_detections, EMERGENCY_CLASS_MAP)
        print("Emergency model (deduplicated):", emergency_result)
        assert emergency_result["emergency"] == 1, "Expected 1 unique ambulance, not 2 raw detections"
        print("PASSED\n")

        # Image-style: no tracking, every detection counted
        fake_image_detections = [(None, "Vehicle"), (None, "Vehicle"), (None, "Vehicle")]
        image_result = _aggregate_detections(fake_image_detections, GENERAL_CLASS_MAP)
        print("Image-style (every detection counted):", image_result)
        assert image_result["vehicle"] == 3
        print("PASSED")
    else:
        result = detect_vehicles(sys.argv[1])
        print(result)