"""
Smart Traffic Management API
=============================
Entry point. This file only does four things:
  1. Creates the FastAPI app
  2. Sets up CORS (so the React frontend can call this API)
  3. Runs a startup check against Supabase (fails loudly if unreachable)
  4. Includes every route from api/routes.py

No business logic lives here - that's the whole point of the folder
structure: config, database, schemas, services, ml, and api each own
one concern, and this file just wires them together.

Run:
    uvicorn main:app --reload
    (or just:  python main.py)

Docs:
    http://127.0.0.1:8000/docs
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from database.connection import check_connection
from api.routes import api_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("traffic_api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    if check_connection():
        logger.info("Startup check passed - Supabase connection is working.")
    else:
        logger.error("Startup check FAILED - Supabase unreachable. Check your .env file.")
    yield
    logger.info("Shutting down.")


app = FastAPI(
    title="Smart Traffic Management API",
    description=(
        "Accepts vehicle detection footage/counts per direction, estimates "
        "traffic density/congestion, recommends adaptive signal timing, and "
        "applies emergency vehicle priority overrides where needed."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# Lets the React frontend (a different origin/port, e.g. localhost:5173)
# call this API from the browser. Before final submission, replace "*"
# with your actual frontend URL for a tighter, more defensible setup.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """
    Catches anything not already handled and returns clean JSON instead
    of a raw Python traceback - safer to demo, easier for the frontend
    to parse if something unexpected happens.
    """
    logger.exception(f"Unhandled error on {request.method} {request.url.path}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "Something went wrong processing your request."},
    )


@app.get("/", tags=["Health"])
def health_check() -> dict:
    """Simple liveness check - confirms the server process is up."""
    return {"status": "ok", "message": "Smart Traffic Management API is running"}


app.include_router(api_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)