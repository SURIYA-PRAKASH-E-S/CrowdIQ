"""
utils/database.py — All Supabase database access for ICSS.

Single source of truth for every DB operation. No other file
imports supabase or runs queries directly.

Supabase table: crowd_metrics
    id             BIGSERIAL PRIMARY KEY
    created_at     TIMESTAMPTZ DEFAULT NOW()  (Supabase default)
    people_count   INTEGER
    density        FLOAT8
    flow_direction TEXT
    risk_level     TEXT
    crowd_level    TEXT         (optional — may not exist on older tables)
    peak_count     INTEGER      (optional)
    average_count  FLOAT8       (optional)

Supabase table: alerts
    id        UUID PRIMARY KEY DEFAULT gen_random_uuid()
    created_at TIMESTAMPTZ DEFAULT NOW()
    message   TEXT
    status    TEXT
    severity  TEXT
"""

import os
import logging
import pandas as pd
from supabase import create_client, Client

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Client initialisation (module-level singleton)
# ---------------------------------------------------------------------------

def _create_supabase_client() -> "Client | None":
    """
    Build the Supabase client from environment secrets.
    Returns None (with a warning) when secrets are missing so the rest
    of the app degrades gracefully instead of crashing.
    """
    # Try to load from .env file first
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    
    url = os.environ.get("SUPABASE_URL", "").strip()
    key = os.environ.get("SUPABASE_ANON_KEY", "").strip()

    if not url or not key:
        logger.warning(
            "SUPABASE_URL or SUPABASE_ANON_KEY is not set. "
            "Create a .env file with your credentials or set them as environment variables. "
            "The database tab will be unavailable."
        )
        print("\n=== SUPABASE SETUP REQUIRED ===")
        print("To enable database features:")
        print("1. Copy env_setup.txt to .env")
        print("2. Replace placeholder values with your actual Supabase credentials")
        print("3. Restart the application")
        print("================================\n")
        return None

    try:
        return create_client(url, key)
    except Exception as exc:
        logger.error("Failed to create Supabase client: %s", exc)
        return None


_client: "Client | None" = _create_supabase_client()

TABLE = "crowd_metrics"


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def is_connected() -> bool:
    """Return True if the Supabase client was initialised successfully."""
    return _client is not None


def insert_metric(
    people_count: int,
    density: float,
    flow_direction: str,
    risk_level: str,
    crowd_level: str = "Low",
    peak_count: int = 0,
    average_count: float = 0.0,
) -> bool:
    """
    Insert one crowd-metrics row.
    Returns True on success, False on failure (errors are logged, never raised
    so a DB hiccup never crashes the live video loop).
    """
    if _client is None:
        return False

    row = {
        "people_count":   people_count,
        "density":        density,
        "flow_direction": flow_direction,
        "risk_level":     risk_level,
        "crowd_level":    crowd_level,
        "peak_count":     peak_count,
        "average_count":  average_count,
    }

    try:
        _client.table(TABLE).insert(row).execute()
        return True
    except Exception as exc:
        # Retry with minimal columns (table may not have optional columns)
        try:
            minimal = {
                "people_count":   people_count,
                "density":        density,
                "flow_direction": flow_direction,
                "risk_level":     risk_level,
            }
            _client.table(TABLE).insert(minimal).execute()
            return True
        except Exception as exc2:
            logger.error("insert_metric failed: %s", exc2)
            return False


def _order_col() -> str:
    """
    Return the timestamp column name actually present in crowd_metrics.
    Supabase tables created from the original schema use 'created_at';
    newer tables created from supabase_schema.sql use 'timestamp'.
    We probe once and cache the result per process.
    """
    if not hasattr(_order_col, "_cached"):
        try:
            _client.table(TABLE).select("timestamp").limit(1).execute()
            _order_col._cached = "timestamp"
        except Exception:
            _order_col._cached = "created_at"
    return _order_col._cached


def fetch_latest_metric() -> "dict | None":
    """
    Return the most-recent row as a dict, or None if no data exists.
    Works with both 'timestamp' and 'created_at' column names.
    """
    if _client is None:
        return None

    col = _order_col()
    try:
        resp = (
            _client.table(TABLE)
            .select("*")
            .order(col, desc=True)
            .limit(1)
            .execute()
        )
        data = resp.data
        if not data:
            return None
        row = data[0]
        # Normalise: always expose key 'timestamp' regardless of column name
        if "created_at" in row and "timestamp" not in row:
            row["timestamp"] = row["created_at"]
        return row
    except Exception as exc:
        logger.error("fetch_latest_metric failed: %s", exc)
        return None


def fetch_recent_metrics(limit: int = 10) -> pd.DataFrame:
    """
    Return the last *limit* rows as a pandas DataFrame (newest first).
    Works with both 'timestamp' and 'created_at' column names.
    Returns an empty DataFrame on failure.
    """
    if _client is None:
        return pd.DataFrame()

    col = _order_col()
    try:
        resp = (
            _client.table(TABLE)
            .select("*")
            .order(col, desc=True)
            .limit(limit)
            .execute()
        )
        rows = resp.data
        if not rows:
            return pd.DataFrame()
        df = pd.DataFrame(rows)
        # Normalise: always expose column 'timestamp'
        if "created_at" in df.columns and "timestamp" not in df.columns:
            df = df.rename(columns={"created_at": "timestamp"})
        return df
    except Exception as exc:
        logger.error("fetch_recent_metrics failed: %s", exc)
        return pd.DataFrame()


def insert_alert(
    message: str,
    status: str = "active",
    severity: str = "HIGH",
) -> bool:
    """
    Insert one alert row into the `alerts` table.
    Returns True on success, False on failure.
    Tries full schema first, then falls back to message-only if columns
    are missing — so it works with any alert table variant.

    Recommended Supabase table schema (see supabase_schema.sql):
        id        UUID  PRIMARY KEY DEFAULT gen_random_uuid()
        timestamp TIMESTAMPTZ DEFAULT NOW()
        message   TEXT
        status    TEXT
        severity  TEXT
    """
    if _client is None:
        return False

    # Try full insert first
    for row in [
        {"message": message, "status": status, "severity": severity},
        {"message": message, "status": status},
        {"message": message},
    ]:
        try:
            _client.table("alerts").insert(row).execute()
            return True
        except Exception:
            continue

    logger.error("insert_alert: all fallback inserts failed for message=%r", message)
    return False


def fetch_recent_alerts(limit: int = 50) -> pd.DataFrame:
    """
    Return the last *limit* alert rows as a DataFrame (newest first).
    Uses SELECT * so it works regardless of the exact column set.
    Returns empty DataFrame on failure or if the table doesn't exist.
    """
    if _client is None:
        return pd.DataFrame()

    # Try ordering by common timestamp column names
    for order_col in ("timestamp", "created_at", "id"):
        try:
            resp = (
                _client.table("alerts")
                .select("*")
                .order(order_col, desc=True)
                .limit(limit)
                .execute()
            )
            rows = resp.data
            if not rows:
                return pd.DataFrame()
            return pd.DataFrame(rows)
        except Exception:
            continue

    logger.error("fetch_recent_alerts: could not determine sort column")
    return pd.DataFrame()


def fetch_total_record_count() -> int:
    """Return the total number of rows in crowd_metrics, or 0 on failure."""
    if _client is None:
        return 0

    try:
        resp = (
            _client.table(TABLE)
            .select("id", count="exact")
            .execute()
        )
        return resp.count or 0
    except Exception as exc:
        logger.error("fetch_total_record_count failed: %s", exc)
        return 0
