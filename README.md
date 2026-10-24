# Smart Traffic Management System: Backend

FastAPI backend that analyzes one intersection from four images (N/S/E/W),
detects vehicles with two YOLOv8 models, estimates congestion, and recommends
adaptive signal timing with an emergency-vehicle override. Results are stored
in Supabase.

## Pipeline
Upload 4 images → YOLOv8 vehicle detection → congestion analysis →
emergency check (60s override) or proportional signal timing →
store in Supabase → return JSON to the dashboard.

## Setup
```bash
python -m venv .venv
.venv\Scripts\Activate.ps1        # Windows PowerShell
python -m pip install -r requirements.txt
```

1. Create a Supabase project and run `database/traffic_results.sql` in the SQL editor.
2. Create `.env` in this folder with your Supabase values (use the variable names
   from `database/connection.py`).
3. Put `best.pt` and `emergency.pt` inside `ml/model/`.

## Run
```bash
python -m uvicorn main:app --reload
```
API docs: http://127.0.0.1:8000/docs

## Endpoints
| Method | Path | Purpose |
|---|---|---|
| POST | /upload | 4 images (north, south, east, west) → full analysis |
| POST | /analyze | Vehicle counts → analysis (no models needed) |
| GET | /results/{upload_id} | Fetch saved results |

## Current scope and future work
Image input only. Planned next: video input with object tracking, live
monitoring, congestion prediction from stored history, and retraining both
models for higher accuracy.