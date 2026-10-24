"""
database/connection.py
=======================
Sets up and validates the Supabase connection. This is the ONLY file that
creates the Supabase client — every other file that needs database access
imports `supabase` from here instead of creating its own connection.

Why validate on import: if SUPABASE_URL or SUPABASE_KEY is missing/wrong,
you want the app to fail immediately with a clear message when it starts,
not fail confusingly on whichever request happens to hit the database first.
"""

import os
import logging
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

logger = logging.getLogger("traffic_api.connection")

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
SUPABASE_PUBLISHABLE_KEY = os.environ.get("SUPABASE_PUBLISHABLE_KEY", "")


def _validate_env() -> None:
    missing = [
        name for name, value in
        [("SUPABASE_URL", SUPABASE_URL), ("SUPABASE_KEY", SUPABASE_KEY)]
        if not value
    ]
    if missing:
        raise RuntimeError(
            f"Missing required environment variable(s): {', '.join(missing)}. "
            f"Check that your .env file exists in the backend folder and is filled in."
        )


_validate_env()

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Supabase password authentication uses the public client key. Keep this
# client separate from the database client, which may use a server key.
if not SUPABASE_PUBLISHABLE_KEY:
    raise RuntimeError(
        "Missing required environment variable: SUPABASE_PUBLISHABLE_KEY. "
        "Add it to the backend .env file."
    )

supabase_auth: Client = create_client(SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY)


def check_connection() -> bool:
    """
    Quick reachability check — call this at app startup (in main.py) so a
    broken Supabase connection is caught loudly and early, not silently.
    """
    try:
        supabase.table("traffic_results").select("id").limit(1).execute()
        logger.info("Supabase connection OK.")
        return True
    except Exception as exc:
        logger.error(f"Supabase connection FAILED: {exc}")
        return False