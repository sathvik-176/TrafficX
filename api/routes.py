"""
api/routes.py
==============
Aggregates all API routers into a single place. main.py imports just this
one file instead of importing every individual router directly — if you
ever add another router later, this is the only file that needs to
change; main.py stays untouched.
"""

from fastapi import APIRouter

from api.auth import router as auth_router
from api.traffic import router as traffic_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(traffic_router)

# If a new router is ever added later, wire it in the same way:
# from api.some_new_area import router as some_new_router
# api_router.include_router(some_new_router, prefix="/some-new-area")