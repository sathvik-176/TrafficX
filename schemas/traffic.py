"""
schemas/traffic.py
===================
Defines the exact shape of data this API accepts and returns. FastAPI uses
these to auto-validate incoming requests and to generate the /docs page.

DESIGN NOTE: DirectionCounts has just `vehicle` + `emergency`, not a
car/bike/bus/truck breakdown. This matches what the actual detection
model can produce — the Kaggle/Roboflow dataset used for the general
detector is single-class ("Vehicle"), so it can count vehicles but not
classify their type. None of the 4 approved objectives (detection,
density/congestion, signal timing, emergency priority) require type
classification, so this isn't a missing feature — it's the schema
honestly matching what the system actually measures.

`emergency` comes from a SEPARATE fine-tuned model (ambulance-only),
combined with the general vehicle count in vehicle_detection.py.
"""

from typing import Dict, Optional
from pydantic import BaseModel, Field


class DirectionCounts(BaseModel):
    vehicle: int = Field(0, ge=0, description="Total vehicles detected (no type breakdown)")
    emergency: int = Field(0, ge=0, description="Emergency vehicles detected (ambulance/fire/police)")


class AnalyzeRequest(BaseModel):
    # Data contract agreed with Person A (detection module):
    # each direction name maps to category counts for that direction.
    directions: Dict[str, DirectionCounts]


class DirectionResult(BaseModel):
    counts: DirectionCounts
    density: float
    congestion_level: str
    has_emergency: bool = Field(False, description="True if any emergency vehicle was detected in this direction")


class EmergencyPriorityInfo(BaseModel):
    direction: str
    reason: str


class AnalyzeResponse(BaseModel):
    upload_id: str
    per_direction: Dict[str, DirectionResult]
    recommended_green_time_seconds: Dict[str, int]
    emergency_priority: Optional[EmergencyPriorityInfo] = Field(
        None, description="Set only when an emergency vehicle triggered a signal override"
    )