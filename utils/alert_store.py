"""
utils/alert_store.py — Enhanced alert storage for ICSS with Firebase integration

Handles real-time alert storage, retrieval, and settings management.
"""

import logging
import queue  # FIXED: Bug 3 Step A - add queue for thread-safe alert bridging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import pandas as pd

from .database import get_db, is_connected as db_is_connected
from .cloudinary_helper import upload_snapshot

# === ICSS UPDATE: TASK 2 - Import streamlit for session_state ===
try:
    import streamlit as st
except ImportError:
    st = None

# FIXED: Bug 3 Step A - module-level queue for thread-safe alert bridging
_alert_queue = queue.Queue()

logger = logging.getLogger(__name__)


class AlertStore:
    """Enhanced alert storage with Firebase integration"""
    
    def __init__(self):
        self._cache_timeout = 5  # Cache alerts for 5 seconds
        self._last_cache_update = None
        self._cached_alerts = []
    
    def is_connected(self) -> bool:
        """Check if Firebase is connected"""
        return db_is_connected()
    
    def insert_alert(
        self,
        alert_type: str,
        severity: str,
        zone: Optional[str] = None,
        count: int = 0,
        density: float = 0.0,
        message: str = "",
        image_url: Optional[str] = None,
        timestamp: Optional[str] = None,
        email_sent: bool = False
    ) -> bool:
        """
        Insert enhanced alert into Firebase alerts collection
        
        Args:
            alert_type: Type of alert (e.g., "Zone Overcrowded", "High Risk")
            severity: Alert severity ("LOW", "MEDIUM", "HIGH", "CRITICAL")
            zone: Zone identifier (optional)
            count: Number of people detected
            density: Crowd density
            message: Alert message
            image_url: Cloudinary image URL (optional)
            timestamp: ISO timestamp (optional, defaults to now)
            email_sent: Whether email was sent (default False)
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_connected():
            logger.warning("Cannot insert alert: Firebase not connected")
            return False
        
        if timestamp is None:
            timestamp = datetime.utcnow().isoformat()
        
        # Build alert data
        alert_data = {
            "timestamp": timestamp,
            "type": alert_type,
            "severity": severity,
            "zone": zone,
            "count": count,
            "density": density,
            "message": message,
            "image_url": image_url,
            "email_sent": email_sent
        }
        
        # Remove None values
        alert_data = {k: v for k, v in alert_data.items() if v is not None}
        
        try:
            db = get_db()
            db.child("alerts").push(alert_data)
            logger.info(f"Alert inserted successfully: {alert_type}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to insert alert: {e}")
            return False
    
    # === ICSS UPDATE: TASK 2 - Add method to store alerts in session_state and database ===
    def add_alert(self, alert_data: Dict[str, Any]) -> bool:
        """
        Add alert to both session_state (in-memory) and Firebase/SQLite database.
        
        Args:
            alert_data: Alert dictionary with alert fields
            
        Returns:
            True if successful (at least one storage succeeded), False otherwise
        """
        # Initialize session_state alert_history and alerts_list if not exists
        if st is not None:
            if "alert_history" not in st.session_state:
                st.session_state["alert_history"] = []
            if "alerts_list" not in st.session_state:
                st.session_state["alerts_list"] = []
        
        # Add timestamp if not provided
        if "timestamp" not in alert_data:
            alert_data["timestamp"] = datetime.utcnow().isoformat()
        
        # Add to session_state (in-memory for real-time dashboard display)
        success = False
        if st is not None:
            try:
                # Add to alert_history (legacy)
                st.session_state["alert_history"].insert(0, alert_data)
                # Cap at last 100 alerts to prevent memory issues
                if len(st.session_state["alert_history"]) > 100:
                    st.session_state["alert_history"] = st.session_state["alert_history"][:100]
                
                # Add to alerts_list (used by alert_tab.py)
                st.session_state["alerts_list"].insert(0, alert_data)
                # Cap at last 100 alerts to prevent memory issues
                if len(st.session_state["alerts_list"]) > 100:
                    st.session_state["alerts_list"] = st.session_state["alerts_list"][:100]
                
                # Update refresh timestamp
                st.session_state["last_alert_refresh"] = datetime.now().timestamp()
                success = True
                logger.info(f"Alert added to session_state: {alert_data.get('type', 'Unknown')}")
                
                # FIXED: Bug 3 Step B - also put in queue for main thread consumption
                try:
                    _alert_queue.put_nowait(alert_data)
                except Exception:
                    pass
            except Exception as e:
                logger.error(f"Failed to add alert to session_state: {e}")
        
        # Also store to Firebase/SQLite for persistence
        try:
            # Extract fields for insert_alert
            db_success = self.insert_alert(
                alert_type=alert_data.get("type", "Alert"),
                severity=alert_data.get("severity", "MEDIUM"),
                zone=alert_data.get("zone"),
                count=alert_data.get("count", 0),
                density=alert_data.get("density", 0.0),
                message=alert_data.get("message", ""),
                image_url=alert_data.get("image_url"),
                timestamp=alert_data.get("timestamp"),
                email_sent=alert_data.get("email_sent", False)
            )
            if db_success:
                success = True
        except Exception as e:
            logger.error(f"Failed to add alert to database: {e}")
        
        return success
    
    def get_active_alerts(self, minutes: int = 5) -> List[Dict]:
        """
        Get active alerts from the last N minutes
        
        Args:
            minutes: How many minutes back to look
            
        Returns:
            List of alert dictionaries
        """
        if not self.is_connected():
            return []
        
        # Check cache
        now = datetime.now()
        if (self._last_cache_update and 
            (now - self._last_cache_update).seconds < self._cache_timeout):
            return self._cached_alerts
        
        try:
            db = get_db()
            # Calculate cutoff time
            cutoff_time = (datetime.utcnow() - timedelta(minutes=minutes)).isoformat()
            
            # Query alerts - Firebase doesn't have direct gte, so we fetch more and filter
            # For simplicity, fetch recent 100 and filter in Python
            try:
                data = db.child("alerts").order_by_child("timestamp").limit_to_last(100).get()
            except Exception as exc:
                # Check if it's an index error
                error_msg = str(exc)
                if "index" in error_msg.lower() or "Index not defined" in error_msg:
                    logger.warning("Index not defined for alerts, falling back to fetch all data")
                    data = db.child("alerts").get()
                else:
                    raise
            
            if not data:
                return []
            
            # Filter and convert to list
            alerts = []
            for key, row in data.items():
                row["id"] = key
                # Filter by timestamp
                alert_time = row.get("timestamp", "")
                if alert_time >= cutoff_time:
                    alerts.append(row)
            
            # Sort by timestamp descending
            alerts.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
            
            # Update cache
            self._cached_alerts = alerts
            self._last_cache_update = now
            
            return alerts
            
        except Exception as e:
            logger.error(f"Failed to get active alerts: {e}")
            return []
    
    def get_recent_alerts(self, limit: int = 50) -> pd.DataFrame:
        """
        Get recent alerts as DataFrame
        
        Args:
            limit: Maximum number of alerts to return
            
        Returns:
            DataFrame with alert data
        """
        if not self.is_connected():
            return pd.DataFrame()
        
        try:
            db = get_db()
            try:
                data = db.child("alerts").order_by_child("timestamp").limit_to_last(limit).get()
            except Exception as exc:
                # Check if it's an index error
                error_msg = str(exc)
                if "index" in error_msg.lower() or "Index not defined" in error_msg:
                    logger.warning("Index not defined for alerts, falling back to fetch all data")
                    all_data = db.child("alerts").get()
                    if not all_data:
                        return pd.DataFrame()
                    # Sort by timestamp descending and limit
                    alerts = []
                    for key, row in all_data.items():
                        row["id"] = key
                        alerts.append(row)
                    alerts.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
                    return pd.DataFrame(alerts[:limit])
                else:
                    raise
            
            if not data:
                return pd.DataFrame()
            
            # Convert to list and reverse
            alerts = []
            for key, row in data.items():
                row["id"] = key
                alerts.append(row)
            
            alerts.reverse()
            return pd.DataFrame(alerts)
            
        except Exception as e:
            logger.error(f"Failed to get recent alerts: {e}")
            return pd.DataFrame()
    
    def get_alert_statistics(self) -> Dict[str, Any]:
        """
        Get alert statistics
        
        Returns:
            Dictionary with alert statistics
        """
        if not self.is_connected():
            return {
                'total_alerts': 0,
                'active_alerts': 0,
                'critical_count': 0,
                'high_count': 0,
                'medium_count': 0,
                'low_count': 0
            }
        
        try:
            db = get_db()
            # Get total count
            data = db.child("alerts").get()
            total_alerts = len(data) if data else 0
            
            # Get active alerts (last 5 minutes)
            active_alerts = self.get_active_alerts(5)
            
            # Count by severity
            severity_counts = {}
            for alert in active_alerts:
                severity = alert.get('severity', 'UNKNOWN')
                severity_counts[severity] = severity_counts.get(severity, 0) + 1
            
            return {
                'total_alerts': total_alerts,
                'active_alerts': len(active_alerts),
                'critical_count': severity_counts.get('CRITICAL', 0),
                'high_count': severity_counts.get('HIGH', 0),
                'medium_count': severity_counts.get('MEDIUM', 0),
                'low_count': severity_counts.get('LOW', 0)
            }
            
        except Exception as e:
            logger.error(f"Failed to get alert statistics: {e}")
            return {
                'total_alerts': 0,
                'active_alerts': 0,
                'critical_count': 0,
                'high_count': 0,
                'medium_count': 0,
                'low_count': 0
            }
    
    def update_email_setting(self, enabled: bool) -> bool:
        """
        Update email alert setting in Firebase settings collection
        
        Args:
            enabled: Whether email alerts should be enabled
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_connected():
            return False
        
        try:
            db = get_db()
            # Upsert email setting
            setting_data = {
                "value": str(enabled),
                "updated_at": datetime.utcnow().isoformat()
            }
            
            db.child("settings").child("email_enabled").set(setting_data)
            
            logger.info(f"Email setting updated: {enabled}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update email setting: {e}")
            return False
    
    def get_email_setting(self) -> bool:
        """
        Get email alert setting from Firebase settings collection
        
        Returns:
            True if email alerts are enabled, False otherwise
        """
        if not self.is_connected():
            return False
        
        try:
            db = get_db()
            setting = db.child("settings").child("email_enabled").get()
            
            if setting:
                value = setting.get('value', 'false')
                return value.lower() in ('true', '1', 'yes', 'on')
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to get email setting: {e}")
            return False


# Global alert store instance
_alert_store = AlertStore()


def get_alert_store() -> AlertStore:
    """Get the global alert store instance"""
    return _alert_store


def get_active_alerts(minutes: int = 5) -> List[Dict]:
    """Get active alerts from the last N minutes"""
    return _alert_store.get_active_alerts(minutes)


def get_alert_statistics() -> Dict[str, Any]:
    """Get alert statistics"""
    return _alert_store.get_alert_statistics()


def insert_enhanced_alert(
    alert_type: str,
    severity: str,
    zone: Optional[str] = None,
    count: int = 0,
    density: float = 0.0,
    message: str = "",
    frame: Optional[Any] = None,
    camera_source: str = "webcam"
) -> bool:
    """
    Insert enhanced alert with optional image upload
    
    Args:
        alert_type: Type of alert
        severity: Alert severity
        zone: Zone identifier
        count: Number of people
        density: Crowd density
        message: Alert message
        frame: OpenCV frame for snapshot upload (optional)
        camera_source: Source of camera (webcam/mobile)
        
    Returns:
        True if successful, False otherwise
    """
    image_url = None
    
    # Upload snapshot if frame provided
    if frame is not None:
        try:
            success, url = upload_snapshot(frame)
            if success:
                image_url = url
        except Exception as e:
            logger.warning(f"Failed to upload alert snapshot: {e}")
    
    # Insert alert with camera source info
    enhanced_message = message
    if camera_source == "mobile":
        enhanced_message = f"[Mobile Camera] {message}"
    
    return _alert_store.insert_alert(
        alert_type=alert_type,
        severity=severity,
        zone=zone,
        count=count,
        density=density,
        message=enhanced_message,
        image_url=image_url,
        timestamp=datetime.utcnow().isoformat(),
        email_sent=False
    )


# FIXED: Bug 3 Step C - drain_alert_queue() function to consume alerts from queue
def drain_alert_queue() -> List[Dict[str, Any]]:
    """
    Drain all alerts from the thread-safe queue and return them.
    Should be called from the main Streamlit thread to update session_state.
    
    Returns:
        List of alert dictionaries
    """
    alerts = []
    try:
        while True:
            alerts.append(_alert_queue.get_nowait())
    except queue.Empty:
        pass
    return alerts
