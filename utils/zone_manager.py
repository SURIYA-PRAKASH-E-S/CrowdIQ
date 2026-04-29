"""
zone_manager.py - Zone data management and Firebase integration.

This module handles:
- Fetching real-time zone data from Firebase
- Managing zone state and updates
- Fallback to dummy data when Firebase unavailable
"""

import time
import logging
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime

logger = logging.getLogger(__name__)


class ZoneManager:
    """
    Manages zone data with Firebase integration and fallback support.
    """
    
    def __init__(
        self,
        firebase_client=None,
        use_dummy_data: bool = True,
        auto_refresh: bool = True,
        refresh_interval: int = 5
    ):
        """
        Initialize the ZoneManager.
        
        Args:
            firebase_client: Firebase database reference
            use_dummy_data: Use dummy data when Firebase unavailable
            auto_refresh: Enable automatic data refresh
            refresh_interval: Refresh interval in seconds
        """
        self.firebase_client = firebase_client
        self.use_dummy_data = use_dummy_data
        self.auto_refresh = auto_refresh
        self.refresh_interval = refresh_interval
        
        self._zones: Dict[str, Dict[str, Any]] = {}
        self._last_update: Optional[float] = None
        self._is_connected: bool = False
        self._listeners: List[Callable] = []
        
    def connect(self) -> bool:
        """
        Attempt to connect to Firebase and verify connection.
        
        Returns:
            bool: True if connected, False otherwise
        """
        if self.firebase_client is not None:
            try:
                # Test connection by reading root
                self.firebase_client.get("/")
                self._is_connected = True
                logger.info("Firebase connection established")
                return True
            except Exception as e:
                logger.warning(f"Firebase connection failed: {e}")
                self._is_connected = False
        return False
    
    def fetch_realtime_data(self, path: str = "zones") -> Dict[str, Dict[str, Any]]:
        """
        Fetch zone data from Firebase Realtime Database.
        
        Args:
            path: Firebase path to zones data
            
        Returns:
            Dict: Zone data dictionary or empty dict on failure
        """
        if not self._is_connected or self.firebase_client is None:
            logger.warning("Firebase not connected, cannot fetch data")
            return {}
        
        try:
            data = self.firebase_client.get(f"/{path}")
            if data:
                self._zones = data
                self._last_update = time.time()
                self._notify_listeners()
            return self._zones
        except Exception as e:
            logger.error(f"Error fetching Firebase data: {e}")
            return {}
    
    def fetch_zone(self, zone_id: str, path: str = "zones") -> Optional[Dict[str, Any]]:
        """
        Fetch data for a specific zone.
        
        Args:
            zone_id: The zone identifier
            path: Firebase path to zones data
            
        Returns:
            Dict: Zone data or None
        """
        if not self._is_connected or self.firebase_client is None:
            return self._zones.get(zone_id)
        
        try:
            data = self.firebase_client.get(f"/{path}/{zone_id}")
            if data:
                self._zones[zone_id] = data
                self._last_update = time.time()
                self._notify_listeners()
            return data
        except Exception as e:
            logger.error(f"Error fetching zone {zone_id}: {e}")
            return None
    
    def update_zone(
        self,
        zone_id: str,
        crowd_count: int,
        density: float,
        risk_level: str,
        coordinates: List[List[float]],
        path: str = "zones"
    ) -> bool:
        """
        Update zone data in Firebase.
        
        Args:
            zone_id: Zone identifier
            crowd_count: Current crowd count
            density: Density value (0-1)
            risk_level: Risk level (LOW, MEDIUM, HIGH)
            coordinates: Polygon coordinates
            path: Firebase path
            
        Returns:
            bool: True if successful
        """
        if not self._is_connected or self.firebase_client is None:
            logger.warning("Firebase not connected, cannot update zone")
            return False
        
        try:
            zone_data = {
                "crowd_count": crowd_count,
                "density": density,
                "risk_level": risk_level,
                "coordinates": coordinates,
                "updated_at": datetime.now().isoformat()
            }
            self.firebase_client.put(f"/{path}/{zone_id}", zone_data)
            self._zones[zone_id] = zone_data
            self._last_update = time.time()
            self._notify_listeners()
            return True
        except Exception as e:
            logger.error(f"Error updating zone {zone_id}: {e}")
            return False
    
    def set_zones(self, zones: Dict[str, Dict[str, Any]]) -> None:
        """
        Set zone data directly (for dummy data mode).
        
        Args:
            zones: Zone data dictionary
        """
        self._zones = zones
        self._last_update = time.time()
        self._notify_listeners()
    
    def get_zones(self) -> Dict[str, Dict[str, Any]]:
        """
        Get current zone data.
        
        Returns:
            Dict: Current zone data
        """
        return self._zones.copy()
    
    def get_zone(self, zone_id: str) -> Optional[Dict[str, Any]]:
        """
        Get data for a specific zone.
        
        Args:
            zone_id: Zone identifier
            
        Returns:
            Dict: Zone data or None
        """
        return self._zones.get(zone_id)
    
    def get_last_update_time(self) -> Optional[float]:
        """
        Get timestamp of last data update.
        
        Returns:
            float: Unix timestamp or None
        """
        return self._last_update
    
    def is_connected(self) -> bool:
        """
        Check if connected to Firebase.
        
        Returns:
            bool: Connection status
        """
        return self._is_connected
    
    def add_listener(self, callback: Callable) -> None:
        """
        Add a listener callback that fires on data updates.
        
        Args:
            callback: Function to call on updates
        """
        if callback not in self._listeners:
            self._listeners.append(callback)
    
    def remove_listener(self, callback: Callable) -> None:
        """
        Remove a listener callback.
        
        Args:
            callback: Function to remove
        """
        if callback in self._listeners:
            self._listeners.remove(callback)
    
    def _notify_listeners(self) -> None:
        """Notify all listeners of data update."""
        for listener in self._listeners:
            try:
                listener(self._zones)
            except Exception as e:
                logger.error(f"Error in listener callback: {e}")


def fetch_realtime_data(
    firebase_client,
    path: str = "zones",
    use_dummy: bool = False,
    fallback_zones: Dict[str, Dict[str, Any]] = None
) -> Dict[str, Dict[str, Any]]:
    """
    Fetch real-time zone data from Firebase with fallback support.
    
    Args:
        firebase_client: Firebase database reference
        path: Firebase path to zones
        use_dummy: Force use of dummy data
        fallback_zones: Fallback zone data if Firebase unavailable
        
    Returns:
        Dict: Zone data from Firebase or fallback
    """
    if use_dummy or firebase_client is None:
        if fallback_zones:
            return fallback_zones
        return {}
    
    try:
        data = firebase_client.get(f"/{path}")
        return data if data else {}
    except Exception as e:
        logger.error(f"Error fetching realtime data: {e}")
        if fallback_zones:
            return fallback_zones
        return {}


def create_zone_manager(
    firebase_client=None,
    use_dummy_data: bool = True,
    initial_zones: Dict[str, Dict[str, Any]] = None
) -> ZoneManager:
    """
    Factory function to create a configured ZoneManager.
    
    Args:
        firebase_client: Firebase database reference
        use_dummy_data: Use dummy data when Firebase unavailable
        initial_zones: Initial zone data
        
    Returns:
        ZoneManager: Configured zone manager instance
    """
    manager = ZoneManager(
        firebase_client=firebase_client,
        use_dummy_data=use_dummy_data
    )
    
    if use_dummy_data and initial_zones:
        manager.set_zones(initial_zones)
    
    return manager


def validate_zone_data(zone_data: Dict[str, Any]) -> bool:
    """
    Validate zone data structure.
    
    Args:
        zone_data: Zone data to validate
        
    Returns:
        bool: True if valid
    """
    required_fields = ["crowd_count", "density", "risk_level"]
    
    for field in required_fields:
        if field not in zone_data:
            return False
    
    # Validate density range
    density = zone_data.get("density", 0)
    if not isinstance(density, (int, float)) or density < 0 or density > 1:
        return False
    
    # Validate risk level
    risk = zone_data.get("risk_level", "").upper()
    if risk not in ["LOW", "MEDIUM", "HIGH"]:
        return False
    
    return True


def format_zone_summary(zones: Dict[str, Dict[str, Any]]) -> str:
    """
    Create a text summary of zone data.
    
    Args:
        zones: Zone data dictionary
        
    Returns:
        str: Formatted summary
    """
    if not zones:
        return "No zones available"
    
    lines = ["Zone Summary:"]
    for zone_id, data in zones.items():
        lines.append(
            f"  {zone_id}: {data.get('crowd_count', 0)} people, "
            f"density {data.get('density', 0):.2f}, "
            f"risk {data.get('risk_level', 'UNKNOWN')}"
        )
    
    return "\n".join(lines)
