"""
utils/alert_store.py — Enhanced alert storage for ICSS with Supabase integration

Handles real-time alert storage, retrieval, and settings management.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import pandas as pd

from .database import _client, is_connected as db_is_connected
from .cloudinary_helper import upload_snapshot

logger = logging.getLogger(__name__)


class AlertStore:
    """Enhanced alert storage with Supabase integration"""
    
    def __init__(self):
        self._client = _client
        self._cache_timeout = 5  # Cache alerts for 5 seconds
        self._last_cache_update = None
        self._cached_alerts = []
    
    def is_connected(self) -> bool:
        """Check if Supabase is connected"""
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
        Insert enhanced alert into Supabase alerts table
        
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
            logger.warning("Cannot insert alert: Supabase not connected")
            return False
        
        if timestamp is None:
            timestamp = datetime.utcnow().isoformat()
        
        # Build alert data
        alert_data = {
            "type": alert_type,
            "severity": severity,
            "zone": zone,
            "count": count,
            "density": density,
            "message": message,
            "timestamp": timestamp,
            "image_url": image_url,
            "email_sent": email_sent
        }
        
        # Remove None values to avoid SQL issues
        alert_data = {k: v for k, v in alert_data.items() if v is not None}
        
        try:
            # Try full schema first
            response = self._client.table("alerts").insert(alert_data).execute()
            logger.info(f"Alert inserted successfully: {alert_type}")
            return True
            
        except Exception as e:
            # Try fallback with minimal columns
            try:
                minimal_data = {
                    "message": message,
                    "severity": severity,
                    "type": alert_type
                }
                response = self._client.table("alerts").insert(minimal_data).execute()
                logger.info(f"Alert inserted with minimal schema: {alert_type}")
                return True
                
            except Exception as e2:
                logger.error(f"Failed to insert alert: {e2}")
                return False
    
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
            # Calculate cutoff time
            cutoff_time = (datetime.utcnow() - timedelta(minutes=minutes)).isoformat()
            
            # Query alerts
            response = self._client.table("alerts")\
                .select("*")\
                .gte("timestamp", cutoff_time)\
                .order("timestamp", desc=True)\
                .execute()
            
            alerts = response.data or []
            
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
            response = self._client.table("alerts")\
                .select("*")\
                .order("timestamp", desc=True)\
                .limit(limit)\
                .execute()
            
            alerts = response.data or []
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
            # Get total count
            total_response = self._client.table("alerts")\
                .select("id", count="exact")\
                .execute()
            total_alerts = total_response.count or 0
            
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
        Update email alert setting in Supabase settings table
        
        Args:
            enabled: Whether email alerts should be enabled
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_connected():
            return False
        
        try:
            # Upsert email setting
            setting_data = {
                "key": "email_enabled",
                "value": str(enabled),
                "updated_at": datetime.utcnow().isoformat()
            }
            
            response = self._client.table("settings")\
                .upsert(setting_data, on_conflict="key")\
                .execute()
            
            logger.info(f"Email setting updated: {enabled}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update email setting: {e}")
            return False
    
    def get_email_setting(self) -> bool:
        """
        Get email alert setting from Supabase settings table
        
        Returns:
            True if email alerts are enabled, False otherwise
        """
        if not self.is_connected():
            return False
        
        try:
            response = self._client.table("settings")\
                .select("value")\
                .eq("key", "email_enabled")\
                .single()\
                .execute()
            
            if response.data:
                value = response.data.get('value', 'false')
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
