"""
Physics-Based Crowd Flow Analysis Module for ICSS

Implements fundamental fluid dynamics principles for crowd flow:
- Flow Rate: Q = D × V (Density × Velocity)
- Congestion Index: C = D / D_critical (D_critical = 4 people/m²)

Works across ALL input modes:
- Live camera feed
- Video upload
- RTSP/stream input
- Image input (single frame fallback estimation)
"""

import numpy as np
import cv2
from typing import Dict, List, Tuple, Optional, Any
from collections import deque
from dataclasses import dataclass
import math
import time

# Constants
D_CRITICAL = 4.0  # Critical density threshold (people/m²)
PIXEL_TO_METER_DEFAULT = 0.01  # Default pixel-to-meter conversion
SPEED_SMOOTHING_WINDOW = 5  # Moving average window for speed smoothing
MIN_SPEED_THRESHOLD = 0.1  # Minimum speed to consider as movement (m/s)


@dataclass
class PhysicsFlowMetrics:
    """Physics-based flow metrics for a zone or entire frame."""
    density: float  # D: People per m²
    avg_speed: float  # V: Average speed in m/s
    flow_rate: float  # Q: Flow rate in people/(m·s)
    congestion_index: float  # C: Congestion index (dimensionless)
    congestion_level: str  # "Free", "Moderate", "Dangerous"
    avg_vector: Tuple[float, float]  # Average flow vector (dx, dy)
    timestamp: float


class PhysicsFlowAnalyzer:
    """
    Physics-based crowd flow analyzer using fluid dynamics principles.
    
    Implements:
    - Speed calculation with smoothing
    - Flow rate computation (Q = D × V)
    - Congestion index calculation (C = D / D_critical)
    - Works across all input modes
    """
    
    def __init__(self, 
                 pixel_to_meter: float = PIXEL_TO_METER_DEFAULT,
                 fps: float = 30.0,
                 smoothing_window: int = SPEED_SMOOTHING_WINDOW,
                 d_critical: float = D_CRITICAL):
        """
        Initialize physics flow analyzer.
        
        Args:
            pixel_to_meter: Conversion factor from pixels to meters
            fps: Frame rate for speed calculation
            smoothing_window: Window size for speed smoothing
            d_critical: Critical density threshold (people/m²)
        """
        self.pixel_to_meter = pixel_to_meter
        self.fps = fps
        self.smoothing_window = smoothing_window
        self.d_critical = d_critical
        
        # Speed history for smoothing (per track ID)
        self.speed_history = {}  # {track_id: deque of speeds}
        
        # Position history for speed calculation (per track ID)
        self.position_history = {}  # {track_id: deque of (x, y, timestamp)}
        
        # Zone-specific metrics
        self.zone_metrics = {}  # {zone_id: PhysicsFlowMetrics}
        
        # Global metrics (entire frame)
        self.global_metrics = None
        
        # For single-frame fallback
        self.default_speed_estimate = 0.5  # m/s (typical walking speed)
    
    def update_fps(self, fps: float):
        """Update frame rate for accurate speed calculation."""
        if fps > 0:
            self.fps = fps
    
    def update_pixel_to_meter(self, pixel_to_meter: float):
        """Update pixel-to-meter conversion factor."""
        if pixel_to_meter > 0:
            self.pixel_to_meter = pixel_to_meter
    
    def calculate_speed(self, 
                       track_id: int, 
                       current_x: float, 
                       current_y: float,
                       current_time: float = None) -> float:
        """
        Calculate speed for a tracked object.
        
        For video/live/RTSP: Uses actual displacement over time
        For image input: Falls back to historical buffer or default estimate
        
        Args:
            track_id: Tracking ID
            current_x: Current x coordinate (pixels)
            current_y: Current y coordinate (pixels)
            current_time: Current timestamp (for video/live modes)
            
        Returns:
            Speed in m/s
        """
        if current_time is None:
            current_time = time.time()
        
        # Initialize history for this track
        if track_id not in self.position_history:
            self.position_history[track_id] = deque(maxlen=2)
            self.speed_history[track_id] = deque(maxlen=self.smoothing_window)
        
        history = self.position_history[track_id]
        
        # Add current position
        history.append((current_x, current_y, current_time))
        
        # Need at least 2 positions for speed calculation
        if len(history) < 2:
            # Single frame - use historical buffer if available
            if len(self.speed_history[track_id]) > 0:
                # Use average of recent speeds
                speeds = list(self.speed_history[track_id])
                return np.mean(speeds)
            else:
                # Use default low-motion assumption
                return self.default_speed_estimate * 0.1  # Very low speed for single frame
        
        # Calculate displacement
        prev_x, prev_y, prev_time = history[-2]
        dx = current_x - prev_x
        dy = current_y - prev_y
        
        # Convert to meters
        dx_m = dx * self.pixel_to_meter
        dy_m = dy * self.pixel_to_meter
        
        # Calculate distance
        distance = math.sqrt(dx_m**2 + dy_m**2)
        
        # Calculate time delta
        time_delta = current_time - prev_time
        
        if time_delta <= 0:
            # Fallback to FPS-based timing
            time_delta = 1.0 / self.fps if self.fps > 0 else 0.033
        
        # Calculate speed (m/s)
        speed = distance / time_delta if time_delta > 0 else 0.0
        
        # Apply minimum threshold
        speed = max(speed, 0.0)
        
        # Add to speed history for smoothing
        self.speed_history[track_id].append(speed)
        
        # Return smoothed speed (moving average)
        speeds = list(self.speed_history[track_id])
        if len(speeds) >= 2:
            return np.mean(speeds[-min(self.smoothing_window, len(speeds)):])
        else:
            return speed
    
    def calculate_avg_speed(self, tracked_objects: List[Dict], 
                           current_time: float = None) -> float:
        """
        Calculate average speed across all tracked objects in a zone.
        
        Args:
            tracked_objects: List of tracked objects with bbox and track_id
            current_time: Current timestamp
            
        Returns:
            Average speed in m/s
        """
        if not tracked_objects:
            return 0.0
        
        speeds = []
        
        for obj in tracked_objects:
            track_id = obj.get('track_id')
            bbox = obj.get('bbox')
            
            if track_id is not None and bbox:
                # Calculate center
                cx = (bbox[0] + bbox[2]) / 2
                cy = (bbox[1] + bbox[3]) / 2
                
                # Calculate speed
                speed = self.calculate_speed(track_id, cx, cy, current_time)
                speeds.append(speed)
        
        if not speeds:
            return 0.0
        
        # Return average speed
        avg_speed = np.mean(speeds)
        
        # Apply minimum threshold
        return max(avg_speed, MIN_SPEED_THRESHOLD)
    
    def calculate_flow_rate(self, density: float, avg_speed: float) -> float:
        """
        Calculate flow rate using physics formula: Q = D × V
        
        Args:
            density: Density in people/m²
            avg_speed: Average speed in m/s
            
        Returns:
            Flow rate in people/(m·s)
        """
        return density * avg_speed
    
    def calculate_congestion_index(self, density: float) -> Tuple[float, str]:
        """
        Calculate congestion index: C = D / D_critical
        
        Args:
            density: Density in people/m²
            
        Returns:
            Tuple of (congestion_index, congestion_level)
        """
        if self.d_critical <= 0:
            return 0.0, "Free"
        
        congestion_index = density / self.d_critical
        
        # Classify congestion level
        if congestion_index < 0.5:
            congestion_level = "Free"
        elif congestion_index < 1.0:
            congestion_level = "Moderate"
        else:
            congestion_level = "Dangerous"
        
        return congestion_index, congestion_level
    
    def calculate_avg_vector(self, tracked_objects: List[Dict]) -> Tuple[float, float]:
        """
        Calculate average flow vector from tracked objects.
        
        Args:
            tracked_objects: List of tracked objects
            
        Returns:
            Tuple of (avg_dx, avg_dy) in pixels
        """
        if not tracked_objects:
            return (0.0, 0.0)
        
        dx_list = []
        dy_list = []
        
        for obj in tracked_objects:
            track_id = obj.get('track_id')
            bbox = obj.get('bbox')
            
            if track_id is not None and bbox and track_id in self.position_history:
                history = self.position_history[track_id]
                if len(history) >= 2:
                    prev_x, prev_y, _ = history[-2]
                    curr_x = (bbox[0] + bbox[2]) / 2
                    curr_y = (bbox[1] + bbox[3]) / 2
                    
                    dx = curr_x - prev_x
                    dy = curr_y - prev_y
                    
                    dx_list.append(dx)
                    dy_list.append(dy)
        
        if not dx_list:
            return (0.0, 0.0)
        
        avg_dx = np.mean(dx_list)
        avg_dy = np.mean(dy_list)
        
        return (avg_dx, avg_dy)
    
    def compute_flow_metrics(self, 
                           tracked_objects: List[Dict],
                           density: float,
                           zone_id: str = "global",
                           current_time: float = None) -> PhysicsFlowMetrics:
        """
        Compute complete physics-based flow metrics for a zone.
        
        Args:
            tracked_objects: List of tracked objects
            density: Density in people/m²
            zone_id: Zone identifier
            current_time: Current timestamp
            
        Returns:
            PhysicsFlowMetrics object with all flow metrics
        """
        if current_time is None:
            current_time = time.time()
        
        # Calculate average speed
        avg_speed = self.calculate_avg_speed(tracked_objects, current_time)
        
        # Calculate flow rate
        flow_rate = self.calculate_flow_rate(density, avg_speed)
        
        # Calculate congestion index
        congestion_index, congestion_level = self.calculate_congestion_index(density)
        
        # Calculate average vector
        avg_vector = self.calculate_avg_vector(tracked_objects)
        
        # Create metrics object
        metrics = PhysicsFlowMetrics(
            density=density,
            avg_speed=avg_speed,
            flow_rate=flow_rate,
            congestion_index=congestion_index,
            congestion_level=congestion_level,
            avg_vector=avg_vector,
            timestamp=current_time
        )
        
        # Store metrics
        if zone_id == "global":
            self.global_metrics = metrics
        else:
            self.zone_metrics[zone_id] = metrics
        
        return metrics
    
    def get_zone_metrics(self, zone_id: str) -> Optional[PhysicsFlowMetrics]:
        """Get stored metrics for a specific zone."""
        if zone_id == "global":
            return self.global_metrics
        return self.zone_metrics.get(zone_id)
    
    def get_all_zone_metrics(self) -> Dict[str, PhysicsFlowMetrics]:
        """Get metrics for all zones."""
        all_metrics = {}
        if self.global_metrics:
            all_metrics["global"] = self.global_metrics
        all_metrics.update(self.zone_metrics)
        return all_metrics
    
    def cleanup_old_tracks(self, active_track_ids: set):
        """
        Clean up history for tracks that are no longer active.
        
        Args:
            active_track_ids: Set of currently active track IDs
        """
        tracks_to_remove = []
        
        for track_id in self.position_history:
            if track_id not in active_track_ids:
                tracks_to_remove.append(track_id)
        
        for track_id in tracks_to_remove:
            del self.position_history[track_id]
            if track_id in self.speed_history:
                del self.speed_history[track_id]
    
    def reset(self):
        """Reset all history and metrics."""
        self.position_history.clear()
        self.speed_history.clear()
        self.zone_metrics.clear()
        self.global_metrics = None


def get_congestion_color(congestion_level: str) -> Tuple[int, int, int]:
    """
    Get color code based on congestion level.
    
    Args:
        congestion_level: "Free", "Moderate", or "Dangerous"
        
    Returns:
        RGB color tuple
    """
    colors = {
        "Free": (0, 255, 0),      # Green
        "Moderate": (0, 165, 255),  # Orange
        "Dangerous": (0, 0, 255)   # Red
    }
    return colors.get(congestion_level, (128, 128, 128))


def draw_flow_arrow(frame: np.ndarray,
                   center_x: float,
                   center_y: float,
                   avg_vector: Tuple[float, float],
                   flow_rate: float,
                   congestion_level: str) -> np.ndarray:
    """
    Draw flow arrow with physics-based styling.
    
    Args:
        frame: Input frame
        center_x: Arrow center x coordinate
        center_y: Arrow center y coordinate
        avg_vector: Average flow vector (dx, dy)
        flow_rate: Flow rate for thickness/intensity
        congestion_level: Congestion level for color
        
    Returns:
        Frame with arrow drawn
    """
    dx, dy = avg_vector
    magnitude = math.sqrt(dx**2 + dy**2)
    
    if magnitude < 1.0:  # Don't draw if negligible movement
        return frame
    
    # Get color based on congestion
    color = get_congestion_color(congestion_level)
    
    # Scale arrow length based on magnitude
    arrow_length = min(magnitude * 3, 60)
    
    # Calculate end point
    if magnitude > 0:
        end_x = center_x + (dx / magnitude) * arrow_length
        end_y = center_y + (dy / magnitude) * arrow_length
    else:
        end_x = center_x
        end_y = center_y
    
    # Thickness based on flow rate
    thickness = max(2, min(int(flow_rate * 2), 8))
    
    # Draw arrow
    start_point = (int(center_x), int(center_y))
    end_point = (int(end_x), int(end_y))
    
    cv2.arrowedLine(frame, start_point, end_point, color, thickness, 
                   tipLength=0.3, line_type=cv2.LINE_AA)
    
    return frame


def format_flow_metrics_text(metrics) -> str:
    """
    Format flow metrics for UI display.
    
    Args:
        metrics: PhysicsFlowMetrics object or dictionary
        
    Returns:
        Formatted string for display
    """
    # Handle both object and dictionary inputs
    if isinstance(metrics, dict):
        density = metrics.get('density', 0.0)
        avg_speed = metrics.get('avg_speed', 0.0)
        flow_rate = metrics.get('flow_rate', 0.0)
        congestion_index = metrics.get('congestion_index', 0.0)
        congestion_level = metrics.get('congestion_level', 'Unknown')
    else:
        # Object with attributes
        density = metrics.density
        avg_speed = metrics.avg_speed
        flow_rate = metrics.flow_rate
        congestion_index = metrics.congestion_index
        congestion_level = metrics.congestion_level
    
    return (f"D: {density:.2f} | "
            f"V: {avg_speed:.2f} | "
            f"Q: {flow_rate:.2f} | "
            f"C: {congestion_index:.2f} ({congestion_level})")
