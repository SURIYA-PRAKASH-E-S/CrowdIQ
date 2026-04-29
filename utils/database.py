"""
utils/database.py — All Firebase Realtime Database access for ICSS.

Single source of truth for every DB operation. No other file
imports firebase or runs queries directly.

Firebase Realtime DB structure:
    crowd_metrics/
        {push_id}:
            timestamp: ISO string
            people_count: integer
            density: float
            flow_direction: string
            risk_level: string
            crowd_level: string (optional)
            peak_count: integer (optional)
            average_count: float (optional)

    alerts/
        {push_id}:
            timestamp: ISO string
            type: string
            severity: string
            zone: string (optional)
            count: integer (optional)
            density: float (optional)
            message: string
            image_url: string (optional)
            email_sent: boolean (optional)

    settings/
        {key}:
            value: string
            updated_at: ISO string
"""

import os
import logging
import pandas as pd
import sqlite3
from datetime import datetime
from firebase_client import get_db

logger = logging.getLogger(__name__)

TABLE = "crowd_metrics"
LOCAL_DB_PATH = "icss_local.db"

# Initialize local SQLite database
def _init_local_db():
    """Initialize local SQLite database for fallback storage."""
    conn = sqlite3.connect(LOCAL_DB_PATH)
    cursor = conn.cursor()
    
    # Create crowd_metrics table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS crowd_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            people_count INTEGER NOT NULL,
            density REAL NOT NULL,
            flow_direction TEXT NOT NULL,
            risk_level TEXT NOT NULL,
            crowd_level TEXT,
            peak_count INTEGER DEFAULT 0,
            average_count REAL DEFAULT 0.0,
            flow_rate REAL DEFAULT 0.0,
            avg_speed REAL DEFAULT 0.0,
            congestion_index REAL DEFAULT 0.0
        )
    ''')
    
    # Add new columns if table exists (for migration)
    try:
        cursor.execute("ALTER TABLE crowd_metrics ADD COLUMN flow_rate REAL DEFAULT 0.0")
    except:
        pass  # Column may already exist
    try:
        cursor.execute("ALTER TABLE crowd_metrics ADD COLUMN avg_speed REAL DEFAULT 0.0")
    except:
        pass  # Column may already exist
    try:
        cursor.execute("ALTER TABLE crowd_metrics ADD COLUMN congestion_index REAL DEFAULT 0.0")
    except:
        pass  # Column may already exist
    
    # Create alerts table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            type TEXT,
            severity TEXT NOT NULL,
            zone TEXT,
            count INTEGER DEFAULT 0,
            density REAL DEFAULT 0.0,
            message TEXT NOT NULL,
            image_url TEXT,
            email_sent BOOLEAN DEFAULT 0
        )
    ''')
    
    conn.commit()
    conn.close()

# Initialize local DB on module load
_init_local_db()

# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def is_connected() -> bool:
    """Return True if the Firebase client was initialised successfully."""
    return get_db() is not None


def is_firebase_enabled() -> bool:
    """
    Check if Firebase sync is enabled via session state toggle.
    Returns True if enabled, False otherwise.
    Falls back to True if session state is not available.
    """
    try:
        import streamlit as st
        return st.session_state.get('firebase_enabled', True)
    except Exception:
        return True  # Default to enabled if Streamlit not available


def insert_metric(
    people_count: int,
    density: float,
    flow_direction: str,
    risk_level: str,
    crowd_level: str = "Low",
    peak_count: int = 0,
    average_count: float = 0.0,
    flow_rate: float = 0.0,
    avg_speed: float = 0.0,
    congestion_index: float = 0.0,
) -> bool:
    """
    Insert one crowd-metrics row.
    Returns True on success, False on failure (errors are logged, never raised
    so a DB hiccup never crashes the live video loop).
    
    If Firebase is disabled, stores to local SQLite database.
    """
    row = {
        "timestamp": datetime.utcnow().isoformat(),
        "people_count": people_count,
        "density": density,
        "flow_direction": flow_direction,
        "risk_level": risk_level,
        "crowd_level": crowd_level,
        "peak_count": peak_count,
        "average_count": average_count,
        "flow_rate": flow_rate,
        "avg_speed": avg_speed,
        "congestion_index": congestion_index,
    }
    
    # Check if Firebase is enabled
    if is_firebase_enabled():
        db = get_db()
        if db is not None:
            try:
                db.child(TABLE).push(row)
                return True
            except Exception as exc:
                logger.error("Firebase insert_metric failed: %s", exc)
                # Fallback to local DB
    
    # Store to local SQLite database
    try:
        conn = sqlite3.connect(LOCAL_DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO crowd_metrics 
            (timestamp, people_count, density, flow_direction, risk_level, crowd_level, peak_count, average_count, flow_rate, avg_speed, congestion_index)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            row['timestamp'], row['people_count'], row['density'], row['flow_direction'],
            row['risk_level'], row['crowd_level'], row['peak_count'], row['average_count'],
            row['flow_rate'], row['avg_speed'], row['congestion_index']
        ))
        conn.commit()
        conn.close()
        return True
    except Exception as exc:
        logger.error("Local DB insert_metric failed: %s", exc)
        return False


def fetch_latest_metric() -> "dict | None":
    """
    Return the most-recent row as a dict, or None if no data exists.
    Firebase doesn't have native descending order, so we fetch and reverse.
    Falls back to fetching all data if index is not defined.
    """
    db = get_db()
    if db is None:
        return None

    try:
        # Try with index first
        data = db.child(TABLE).order_by_child("timestamp").limit_to_last(1).get()
        if not data:
            return None
        # data is a dict with one key-value pair
        for key, row in data.items():
            row["id"] = key  # Add Firebase key as id for compatibility
            return row
        return None
    except Exception as exc:
        # Check if it's an index error
        error_msg = str(exc)
        if "index" in error_msg.lower() or "Index not defined" in error_msg:
            logger.warning("Index not defined for %s, falling back to fetch all data", TABLE)
            try:
                # Fallback: fetch all data and find latest
                all_data = db.child(TABLE).get()
                if not all_data:
                    return None
                # Find the item with the latest timestamp
                latest_key = None
                latest_timestamp = None
                for key, row in all_data.items():
                    timestamp = row.get("timestamp", "")
                    if latest_timestamp is None or timestamp > latest_timestamp:
                        latest_timestamp = timestamp
                        latest_key = key
                if latest_key:
                    row = all_data[latest_key]
                    row["id"] = latest_key
                    return row
                return None
            except Exception as fallback_exc:
                logger.error("Fallback fetch_latest_metric failed: %s", fallback_exc)
                return None
        logger.error("fetch_latest_metric failed: %s", exc)
        return None


def fetch_recent_metrics(limit: int = 10) -> pd.DataFrame:
    """
    Return the last *limit* rows as a pandas DataFrame (newest first).
    Returns an empty DataFrame on failure.
    Falls back to fetching all data if index is not defined.
    """
    db = get_db()
    if db is None:
        return pd.DataFrame()

    try:
        # Try with index first
        data = db.child(TABLE).order_by_child("timestamp").limit_to_last(limit).get()
        if not data:
            return pd.DataFrame()
        
        # Convert to list and reverse for descending order
        rows = []
        for key, row in data.items():
            row["id"] = key  # Add Firebase key as id
            rows.append(row)
        
        # Reverse to get newest first
        rows.reverse()
        return pd.DataFrame(rows)
    except Exception as exc:
        # Check if it's an index error
        error_msg = str(exc)
        if "index" in error_msg.lower() or "Index not defined" in error_msg:
            logger.warning("Index not defined for %s, falling back to fetch all data", TABLE)
            try:
                # Fallback: fetch all data and sort locally
                all_data = db.child(TABLE).get()
                if not all_data:
                    return pd.DataFrame()
                
                # Convert to list
                rows = []
                for key, row in all_data.items():
                    row["id"] = key
                    rows.append(row)
                
                # Sort by timestamp descending
                rows.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
                
                # Limit to requested number
                return pd.DataFrame(rows[:limit])
            except Exception as fallback_exc:
                logger.error("Fallback fetch_recent_metrics failed: %s", fallback_exc)
                return pd.DataFrame()
        logger.error("fetch_recent_metrics failed: %s", exc)
        return pd.DataFrame()


def insert_alert(
    message: str,
    status: str = "active",
    severity: str = "HIGH",
) -> bool:
    """
    Insert one alert row into the `alerts` collection.
    Returns True on success, False on failure.
    
    If Firebase is disabled, stores to local SQLite database.
    """
    row = {
        "timestamp": datetime.utcnow().isoformat(),
        "message": message,
        "status": status,
        "severity": severity,
    }
    
    # Check if Firebase is enabled
    if is_firebase_enabled():
        db = get_db()
        if db is not None:
            try:
                db.child("alerts").push(row)
                return True
            except Exception as exc:
                logger.error("Firebase insert_alert failed: %s", exc)
                # Fallback to local DB
    
    # Store to local SQLite database
    try:
        conn = sqlite3.connect(LOCAL_DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO alerts (timestamp, message, status, severity)
            VALUES (?, ?, ?, ?)
        ''', (row['timestamp'], row['message'], row['status'], row['severity']))
        conn.commit()
        conn.close()
        return True
    except Exception as exc:
        logger.error("Local DB insert_alert failed: %s", exc)
        return False


def insert_enhanced_alert(
    alert_type: str,
    severity: str,
    zone: str = None,
    count: int = 0,
    density: float = 0.0,
    message: str = "",
    image_url: str = None,
    timestamp: str = None,
    email_sent: bool = False
) -> bool:
    """
    Insert enhanced alert with additional fields for the new alert system.
    Returns True on success, False on failure.
    
    If Firebase is disabled, stores to local SQLite database.
    """
    # Build alert data
    alert_data = {
        "timestamp": timestamp or datetime.utcnow().isoformat(),
        "type": alert_type,
        "severity": severity,
        "message": message,
    }
    
    # Add optional fields if provided
    if zone is not None:
        alert_data["zone"] = zone
    if count > 0:
        alert_data["count"] = count
    if density > 0:
        alert_data["density"] = density
    if image_url:
        alert_data["image_url"] = image_url
    alert_data["email_sent"] = email_sent

    # Check if Firebase is enabled
    if is_firebase_enabled():
        db = get_db()
        if db is not None:
            try:
                db.child("alerts").push(alert_data)
                logger.info(f"Enhanced alert inserted: {alert_type}")
                return True
            except Exception as exc:
                logger.error("Firebase insert_enhanced_alert failed: %s", exc)
                # Fallback to local DB
    
    # Store to local SQLite database
    try:
        conn = sqlite3.connect(LOCAL_DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO alerts (timestamp, type, severity, zone, count, density, message, image_url, email_sent)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            alert_data['timestamp'], alert_data['type'], alert_data['severity'],
            alert_data.get('zone'), alert_data.get('count', 0), alert_data.get('density', 0.0),
            alert_data['message'], alert_data.get('image_url'), alert_data.get('email_sent', False)
        ))
        conn.commit()
        conn.close()
        return True
    except Exception as exc:
        logger.error("Local DB insert_enhanced_alert failed: %s", exc)
        return False


def fetch_recent_alerts(limit: int = 50) -> pd.DataFrame:
    """
    Return the last *limit* alert rows as a DataFrame (newest first).
    Returns empty DataFrame on failure.
    Falls back to fetching all data if index is not defined.
    """
    db = get_db()
    if db is None:
        return pd.DataFrame()

    try:
        # Try with index first
        data = db.child("alerts").order_by_child("timestamp").limit_to_last(limit).get()
        if not data:
            return pd.DataFrame()
        
        # Convert to list and reverse for descending order
        rows = []
        for key, row in data.items():
            row["id"] = key  # Add Firebase key as id
            rows.append(row)
        
        # Reverse to get newest first
        rows.reverse()
        return pd.DataFrame(rows)
    except Exception as exc:
        # Check if it's an index error
        error_msg = str(exc)
        if "index" in error_msg.lower() or "Index not defined" in error_msg:
            logger.warning("Index not defined for alerts, falling back to fetch all data")
            try:
                # Fallback: fetch all data and sort locally
                all_data = db.child("alerts").get()
                if not all_data:
                    return pd.DataFrame()
                
                # Convert to list
                rows = []
                for key, row in all_data.items():
                    row["id"] = key
                    rows.append(row)
                
                # Sort by timestamp descending
                rows.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
                
                # Limit to requested number
                return pd.DataFrame(rows[:limit])
            except Exception as fallback_exc:
                logger.error("Fallback fetch_recent_alerts failed: %s", fallback_exc)
                return pd.DataFrame()
        logger.error("fetch_recent_alerts failed: %s", exc)
        return pd.DataFrame()


def fetch_total_record_count() -> int:
    """Return the total number of rows in crowd_metrics, or 0 on failure."""
    db = get_db()
    if db is None:
        return 0

    try:
        data = db.child(TABLE).get()
        return len(data) if data else 0
    except Exception as exc:
        logger.error("fetch_total_record_count failed: %s", exc)
        return 0


# Export for alert_store compatibility
_client = None  # Legacy compatibility, not used in Firebase version


def get_analytics_data(limit: int = 100) -> pd.DataFrame:
    """
    Get analytics data from Firebase or local SQLite database.
    
    Args:
        limit: Maximum number of records to fetch
        
    Returns:
        DataFrame with crowd_metrics data (newest first)
    """
    # Try Firebase first if enabled
    if is_firebase_enabled():
        db = get_db()
        if db is not None:
            try:
                # Try with index first
                data = db.child(TABLE).order_by_child("timestamp").limit_to_last(limit).get()
                if data:
                    rows = []
                    for key, row in data.items():
                        row["id"] = key
                        rows.append(row)
                    rows.reverse()
                    return pd.DataFrame(rows)
            except Exception as exc:
                # Check if it's an index error
                error_msg = str(exc)
                if "index" in error_msg.lower() or "Index not defined" in error_msg:
                    logger.warning("Index not defined for %s, falling back to fetch all data", TABLE)
                    try:
                        # Fallback: fetch all data and sort locally
                        all_data = db.child(TABLE).get()
                        if all_data:
                            rows = []
                            for key, row in all_data.items():
                                row["id"] = key
                                rows.append(row)
                            # Sort by timestamp descending
                            rows.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
                            # Limit to requested number
                            return pd.DataFrame(rows[:limit])
                    except Exception as fallback_exc:
                        logger.warning("Firebase fallback get_analytics_data failed: %s", fallback_exc)
                else:
                    logger.warning("Firebase get_analytics_data failed: %s", exc)
    
    # Fallback to local SQLite database
    try:
        conn = sqlite3.connect(LOCAL_DB_PATH)
        query = '''
            SELECT * FROM crowd_metrics 
            ORDER BY timestamp DESC 
            LIMIT ?
        '''
        df = pd.read_sql_query(query, conn, params=(limit,))
        conn.close()
        return df
    except Exception as exc:
        logger.error("Local DB get_analytics_data failed: %s", exc)
        return pd.DataFrame()


def get_analytics_alerts(limit: int = 50) -> pd.DataFrame:
    """
    Get alerts data from Firebase or local SQLite database.
    
    Args:
        limit: Maximum number of records to fetch
        
    Returns:
        DataFrame with alerts data (newest first)
    """
    # Try Firebase first if enabled
    if is_firebase_enabled():
        db = get_db()
        if db is not None:
            try:
                # Try with index first
                data = db.child("alerts").order_by_child("timestamp").limit_to_last(limit).get()
                if data:
                    rows = []
                    for key, row in data.items():
                        row["id"] = key
                        rows.append(row)
                    rows.reverse()
                    return pd.DataFrame(rows)
            except Exception as exc:
                # Check if it's an index error
                error_msg = str(exc)
                if "index" in error_msg.lower() or "Index not defined" in error_msg:
                    logger.warning("Index not defined for alerts, falling back to fetch all data")
                    try:
                        # Fallback: fetch all data and sort locally
                        all_data = db.child("alerts").get()
                        if all_data:
                            rows = []
                            for key, row in all_data.items():
                                row["id"] = key
                                rows.append(row)
                            # Sort by timestamp descending
                            rows.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
                            # Limit to requested number
                            return pd.DataFrame(rows[:limit])
                    except Exception as fallback_exc:
                        logger.warning("Firebase fallback get_analytics_alerts failed: %s", fallback_exc)
                else:
                    logger.warning("Firebase get_analytics_alerts failed: %s", exc)
    
    # Fallback to local SQLite database
    try:
        conn = sqlite3.connect(LOCAL_DB_PATH)
        query = '''
            SELECT * FROM alerts 
            ORDER BY timestamp DESC 
            LIMIT ?
        '''
        df = pd.read_sql_query(query, conn, params=(limit,))
        conn.close()
        return df
    except Exception as exc:
        logger.error("Local DB get_analytics_alerts failed: %s", exc)
        return pd.DataFrame()
