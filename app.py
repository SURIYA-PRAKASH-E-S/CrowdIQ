import streamlit as st
import cv2
import av
import numpy as np
from av import VideoFrame
from streamlit_webrtc import webrtc_streamer, VideoTransformerBase, RTCConfiguration
from ultralytics import YOLO
import tempfile
import os
import threading
import time
import logging
from typing import Optional
from streamlit.runtime.scriptrunner import add_script_run_ctx
import plotly.graph_objects as go
import plotly.express as px
from utils.database import (
    insert_metric,
    insert_alert,
    fetch_latest_metric,
    fetch_recent_metrics,
    fetch_recent_alerts,
    fetch_total_record_count,
    is_connected as db_is_connected,
    get_analytics_data,
)
from utils.detection import (
    process_frame, process_frame_dual_models, track_movement, calculate_flow_direction, 
    calculate_density, classify_risk, process_frame_with_deep_sort
)
from utils.tracker import init_tracker
from utils.advanced_analytics import AdvancedCrowdAnalytics
from utils.csrnet_density import init_density_estimator
from utils.crowd_visualization import init_visualizer
from utils.crowd_analytics import (
    init_crowd_analytics, draw_crowd_overlay, draw_heatmap_overlay,
    draw_legend, create_zone_heatmap, draw_zone_grid, calculate_crowd_metrics
)
from utils.zone_analyzer import (
    ZoneAnalyzer, calculate_crowd_bounding_area, draw_crowd_area
)
from camera1 import MobileCameraStream, render_mobile_camera_sidebar
from utils.alert_manager import AlertManager, AlertType, AlertSeverity, AlertNotifier

# ================= LOGGING CONFIGURATION =================
# Configure logging to suppress excessive warnings and spam
logging.basicConfig(level=logging.ERROR)
logging.getLogger("streamlit.runtime.scriptrunner").setLevel(logging.ERROR)
logging.getLogger("streamlit.runtime.AppRunner").setLevel(logging.ERROR)
logging.getLogger("ultralytics").setLevel(logging.ERROR)
logging.getLogger("urllib3").setLevel(logging.ERROR)
logging.getLogger("PIL").setLevel(logging.ERROR)
logging.getLogger("cv2").setLevel(logging.ERROR)

# Suppress specific noisy loggers
logging.getLogger("streamlit").setLevel(logging.ERROR)
logging.getLogger("webrtc").setLevel(logging.ERROR)

# ================= WEBRTC ICE / STUN / TURN CONFIGURATION =================
# WebRTC configuration for reliable camera connections across different network environments
RTC_CONFIGURATION = RTCConfiguration({
    "iceServers": [
        {"urls": ["stun:stun.l.google.com:19302"]},
        {"urls": ["stun:stun1.l.google.com:19302"]},
        {"urls": ["stun:stun2.l.google.com:19302"]},
        {"urls": ["stun:stun3.l.google.com:19302"]},
        {"urls": ["stun:stun4.l.google.com:19302"]},
        # Open Relay TURN servers — handle strict NAT where STUN alone fails
        {
            "urls": ["turn:openrelay.metered.ca:80"],
            "username": "openrelayproject",
            "credential": "openrelayproject",
        },
        {
            "urls": ["turn:openrelay.metered.ca:443"],
            "username": "openrelayproject",
            "credential": "openrelayproject",
        },
        {
            "urls": ["turn:openrelay.metered.ca:443?transport=tcp"],
            "username": "openrelayproject",
            "credential": "openrelayproject",
        },
    ]
})

st.set_page_config(page_title="AI Crowd Surveillance", layout="wide")

st.title("🎥 Intelligent Crowd Surveillance System (ICSS)")

# ================= SESSION STATE INITIALIZATION =================
# Prevent repeated initialization with session state control
if "app_initialized" not in st.session_state:
    st.session_state.app_initialized = True
    
    # Initialize all session state variables once
    if 'input_mode' not in st.session_state:
        st.session_state.input_mode = "Webcam (Live)"
    if 'low_density_threshold' not in st.session_state:
        st.session_state.low_density_threshold = 0.5
    if 'medium_density_threshold' not in st.session_state:
        st.session_state.medium_density_threshold = 1.0
    if 'count_threshold' not in st.session_state:
        st.session_state.count_threshold = 8
    if 'current_frame_data' not in st.session_state:
        st.session_state.current_frame_data = None
    if 'prev_centroids' not in st.session_state:
        st.session_state.prev_centroids = []
    if 'flow_direction' not in st.session_state:
        st.session_state.flow_direction = "Unknown"
    if 'risk_level' not in st.session_state:
        st.session_state.risk_level = "Normal"
    if 'enable_deep_sort' not in st.session_state:
        st.session_state.enable_deep_sort = True  # Deep SORT enabled by default

    # Advanced Analytics session state
    if 'enable_advanced_analytics' not in st.session_state:
        st.session_state.enable_advanced_analytics = True  # Advanced analytics enabled by default
    if 'risk_weights' not in st.session_state:
        st.session_state.risk_weights = {'density': 0.4, 'flow_conflict': 0.35, 'speed_variation': 0.25}
    if 'zone_grid_size' not in st.session_state:
        st.session_state.zone_grid_size = (2, 2)
    if 'restricted_zones' not in st.session_state:
        st.session_state.restricted_zones = []
    if 'enable_zones' not in st.session_state:
        st.session_state.enable_zones = True
    if 'enable_flow_analysis' not in st.session_state:
        st.session_state.enable_flow_analysis = True
    if 'enable_risk_analysis' not in st.session_state:
        st.session_state.enable_risk_analysis = True
    
    # Dense Crowd Detection session state (CSRNet only)
    if 'enable_csrnet' not in st.session_state:
        st.session_state.enable_csrnet = True  # CSRNet density estimation enabled
    if 'enable_density_heatmap' not in st.session_state:
        st.session_state.enable_density_heatmap = True  # Show density heatmap
    if 'dense_grid_size' not in st.session_state:
        st.session_state.dense_grid_size = (3, 3)  # 3x3 grid for zone analysis
    
    # New Crowd Analytics session state
    if 'enable_crowd_analytics' not in st.session_state:
        st.session_state.enable_crowd_analytics = True
    if 'low_crowd_count' not in st.session_state:
        st.session_state.low_crowd_count = 5
    if 'medium_crowd_count' not in st.session_state:
        st.session_state.medium_crowd_count = 15
    if 'show_crowd_heatmap' not in st.session_state:
        st.session_state.show_crowd_heatmap = True
    if "show_zone_grid" not in st.session_state:
        st.session_state["show_zone_grid"] = False  # Single source of truth

    # Zone Analyzer session state (Map Area feature)
    if 'zone_analyzer' not in st.session_state:
        st.session_state.zone_analyzer = ZoneAnalyzer(
            frame_width=640, frame_height=480,
            grid_rows=3, grid_cols=3,
            real_world_width_m=50.0,
            real_world_height_m=30.0
        )
    if 'show_crowd_area' not in st.session_state:
        st.session_state.show_crowd_area = True
    if 'enable_roi' not in st.session_state:
        st.session_state.enable_roi = False
    if 'roi_x1' not in st.session_state:
        st.session_state.roi_x1 = 50
    if 'roi_y1' not in st.session_state:
        st.session_state.roi_y1 = 50
    if 'roi_x2' not in st.session_state:
        st.session_state.roi_x2 = 300
    if 'roi_y2' not in st.session_state:
        st.session_state.roi_y2 = 300
    if 'zone_summary' not in st.session_state:
        st.session_state.zone_summary = []
    if 'zone_alerts' not in st.session_state:
        st.session_state.zone_alerts = []
    
    # Alert Manager initialization
    if 'alert_manager' not in st.session_state:
        st.session_state.alert_manager = AlertManager(
            cooldown_seconds=60,
            surge_threshold_pct=50.0,
            surge_window_seconds=10
        )
    
    # Firebase sync toggle initialization
    if 'firebase_enabled' not in st.session_state:
        st.session_state.firebase_enabled = True
    
    # === ICSS UPDATE: TASK 2 - Initialize alert_history, alerts_list and alert_mode ===
    if 'alert_history' not in st.session_state:
        st.session_state.alert_history = []
    if 'alerts_list' not in st.session_state:
        st.session_state.alerts_list = []
    if 'alert_mode' not in st.session_state:
        st.session_state.alert_mode = 'realtime'
    if 'last_alert_refresh' not in st.session_state:
        st.session_state.last_alert_refresh = 0.0
    # === ICSS UPDATE: TASK 1 - Initialize formula_metrics ===
    if 'formula_metrics' not in st.session_state:
        st.session_state.formula_metrics = None
    
    # Mobile camera session state
    if 'use_mobile_camera' not in st.session_state:
        st.session_state.use_mobile_camera = False
    if 'ip_webcam_url' not in st.session_state:
        st.session_state.ip_webcam_url = ''
    if 'camera_mode' not in st.session_state:
        st.session_state.camera_mode = 'Public URL (ngrok / Tunnel)'

# ================= LOAD MODELS (TRIPLE MODEL SYSTEM) =================
@st.cache_resource
def load_models():
    """Load YOLO models for enhanced detection with silent operation"""
    model_v11 = YOLO("model/yolo11l.pt", verbose=False)
    model_v8 = YOLO("model/V8l-haj.pt", verbose=False)
    model_v11m = YOLO("model/yolo11m.pt", verbose=False)
    return model_v11, model_v8, model_v11m

# Load all models
model_v11, model_v8, model_v11m = load_models()

# Store models in session_state for mobile feed loop access
st.session_state['model_v11'] = model_v11
st.session_state['model_v8'] = model_v8
st.session_state['model_v11m'] = model_v11m

# Model selection in session state
if 'active_models' not in st.session_state:
    st.session_state.active_models = ["v11", "v8"]  # Use both by default

# ================= SESSION STATE MANAGER =================
class SessionStateManager:
    """Thread-safe session state manager for async video processing"""
    
    def __init__(self):
        self._lock = threading.Lock()
        self._session_state = None
    
    def set_session_state(self, session_state):
        """Set the Streamlit session state reference"""
        with self._lock:
            self._session_state = session_state
    
    def get_session_state(self):
        """Get the Streamlit session state reference"""
        with self._lock:
            return self._session_state
    
    def update_data(self, key, value):
        """Thread-safe session state update"""
        with self._lock:
            if self._session_state:
                self._session_state[key] = value
    
    def get_data(self, key, default=None):
        """Thread-safe session state retrieval"""
        with self._lock:
            if self._session_state:
                return self._session_state.get(key, default)
            return default

# Global session state manager
session_manager = SessionStateManager()

# Set session state in session manager
session_manager.set_session_state(st.session_state)

# Initialize session_manager with zone grid state
session_manager.update_data('show_zone_grid', st.session_state.get("show_zone_grid", False))

# ================= FIREBASE CONNECTION CHECK =================
# The Firebase client is initialised lazily inside utils/database.py.
# We just surface a warning once at startup if the secrets are missing.
if not db_is_connected():
    st.warning(
        "Firebase is not configured. Create a .env file with your FIREBASE_DATABASE_URL "
        "and GOOGLE_APPLICATION_CREDENTIALS, then restart the app. "
        "All other features work normally without the database."
    )

# ================= ALERT HELPER FUNCTIONS =================
ALERT_SOUND_HTML = """
<script>
  // Beep using Web Audio API (no file needed)
  (function() {
    var ctx = new (window.AudioContext || window.webkitAudioContext)();
    var oscillator = ctx.createOscillator();
    var gainNode   = ctx.createGain();
    oscillator.connect(gainNode);
    gainNode.connect(ctx.destination);
    oscillator.type      = 'sine';
    oscillator.frequency.value = 880;   // Hz
    gainNode.gain.setValueAtTime(0.3, ctx.currentTime);
    gainNode.gain.exponentialRampToValueAtTime(
      0.0001, ctx.currentTime + 0.5
    );
    oscillator.start(ctx.currentTime);
    oscillator.stop(ctx.currentTime + 0.5);
  })();
</script>
"""

def play_alert_sound():
    """Inject browser beep sound via Streamlit HTML component."""
    import streamlit.components.v1 as components
    components.html(ALERT_SOUND_HTML, height=0)

def draw_alert_overlay(frame, active_alerts: list) -> np.ndarray:
    """Draw flashing alert banner at top of frame."""
    if not active_alerts:
        return frame

    # Flashing red banner at top
    blink = int(time.time() * 2) % 2 == 0
    if blink:
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (frame.shape[1], 50),
                      (0, 0, 200), -1)
        frame = cv2.addWeighted(overlay, 0.7, frame, 0.3, 0)

    # Alert text
    latest = active_alerts[0]
    msg    = latest.message[:60] + "..." \
             if len(latest.message) > 60 else latest.message
    cv2.putText(frame, f"ALERT: {msg}",
                (10, 32), cv2.FONT_HERSHEY_SIMPLEX,
                0.65, (255, 255, 255), 2)

    # Alert count badge top-right
    badge_text = f"{len(active_alerts)} ALERT(S)"
    cv2.putText(frame, badge_text,
                (frame.shape[1] - 160, 32),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65, (255, 255, 0), 2)
    return frame

# ================= HELPER FUNCTIONS =================
def safe_width(width):
    """Safe width helper function for Streamlit components"""
    if width is None or width == 0:
        return "stretch"
    return width

# ================= DEEP SORT TRACKER INITIALIZATION =================
@st.cache_resource
def initialize_tracker():
    """Initialize Deep SORT tracker for persistent object tracking"""
    return init_tracker(max_age=30, n_init=3, nms_max_overlap=0.3)

# Initialize global tracker
deep_sort_tracker = initialize_tracker()

# Store tracker in session_state for mobile feed loop access
st.session_state['tracker'] = deep_sort_tracker

# ================= ENHANCED VIDEO PROCESSOR WITH ADVANCED ANALYTICS =================
class VideoProcessor(VideoTransformerBase):

    def __init__(self):
        self.prev_positions = {}
        self.prev_centroids = []
        # Initialize tracker for this instance with default values
        self.tracker = init_tracker(max_age=30, n_init=3, nms_max_overlap=0.3)
        
        # Initialize advanced analytics with default configuration
        self.advanced_analytics = AdvancedCrowdAnalytics(
            frame_width=640,
            frame_height=480,
            grid_size=(2, 2),
            risk_weights={'density': 0.4, 'flow_conflict': 0.35, 'speed_variation': 0.25},
            restricted_zones=[]
        )
        
        # Initialize integrated detection pipeline for dense crowds
        self.integrated_pipeline = None  # Will be initialized lazily
        self.visualizer = init_visualizer()
        
        # Performance optimization: aggressive frame skipping and resizing
        self.frame_count = 0
        self.process_every_n_frames = 3  # Process every 3rd frame for better performance
        self.last_processed_frame = None
        self.target_size = (640, 480)  # Resize frames for faster inference
        
        # Dense detection settings (defaults - CSRNet only)
        self.enable_csrnet = True
        self.enable_density_heatmap = True
        self.dense_grid_size = (3, 3)
        
        # Initialize new crowd analytics
        self.crowd_analytics = init_crowd_analytics(
            low_count_threshold=5,
            medium_count_threshold=9,
            low_density_threshold=0.1,
            medium_density_threshold=0.2
        )
        self.show_crowd_heatmap = True
        self.show_zone_grid = False

        # Initialize zone analyzer for Map Area feature
        self.zone_analyzer = ZoneAnalyzer(
            frame_width=640, frame_height=480,
            grid_rows=3, grid_cols=3,
            real_world_width_m=50.0,
            real_world_height_m=30.0
        )

    def resize_frame(self, frame, target_size=(640, 480)):
        """Resize frame for faster inference while maintaining aspect ratio"""
        h, w = frame.shape[:2]
        target_w, target_h = target_size
        
        # Calculate aspect ratio
        aspect_ratio = w / h
        
        if aspect_ratio > target_w / target_h:
            # Width is the limiting factor
            new_w = target_w
            new_h = int(target_w / aspect_ratio)
        else:
            # Height is the limiting factor
            new_h = target_h
            new_w = int(target_h * aspect_ratio)
        
        # Resize frame
        resized = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
        
        # Create a black canvas and place the resized frame in center
        canvas = np.zeros((target_h, target_w, 3), dtype=np.uint8)
        y_offset = (target_h - new_h) // 2
        x_offset = (target_w - new_w) // 2
        canvas[y_offset:y_offset+new_h, x_offset:x_offset+new_w] = resized
        
        return canvas

    def recv(self, frame):
        try:
            img = frame.to_ndarray(format="bgr24")
            h, w, _ = img.shape
            
            # Performance optimization: skip frames for better performance
            self.frame_count += 1
            
            # TEST: Print every 30 frames to verify this method is called
            if self.frame_count % 30 == 0:
                print(f"[TEST] VideoProcessor recv called, frame {self.frame_count}")
            if self.frame_count % self.process_every_n_frames != 0:
                # Return last processed frame if available, otherwise return original
                if self.last_processed_frame is not None:
                    return VideoFrame.from_ndarray(self.last_processed_frame, format="bgr24")
                else:
                    # For first frame, process without analytics for speed
                    return VideoFrame.from_ndarray(img, format="bgr24")
            
            # Performance optimization: resize frame for faster inference
            if (h, w) != self.target_size:
                processed_img = self.resize_frame(img, self.target_size)
            else:
                processed_img = img
            
            # Read toggle states from session_manager (thread-safe) so Controls-tab changes take effect
            enable_deep_sort = session_manager.get_data('enable_deep_sort', True)
            enable_advanced_analytics = session_manager.get_data('enable_advanced_analytics', False)
            active_models = session_manager.get_data('active_models', ["v11", "v8"])
            low_threshold = 0.5  # Default thresholds
            medium_threshold = 1.0
            count_threshold = 8
            
            if enable_deep_sort:
                # Use Deep SORT integrated tracking pipeline (optimized for performance)
                tracking_result = process_frame_with_deep_sort(
                    processed_img, model_v11, model_v8, self.tracker, active_models, fps=30, model_v11m=model_v11m
                )
                
                # Update risk classification using default thresholds
                people_count = tracking_result['people_count']
                density = tracking_result['density']
                
                # Recalculate risk with default thresholds
                risk_level, risk_color = classify_risk(
                    density, 
                    people_count,
                    low_count_threshold=5,
                    medium_count_threshold=9,
                    low_density_threshold=0.1,
                    medium_density_threshold=0.2
                )
                
                # Update tracking result with correct risk level
                tracking_result['risk_level'] = risk_level
                tracking_result['risk_color'] = risk_color
                
                # Get annotated frame with tracking information
                annotated_img = tracking_result['annotated_frame']
                
                # Risk level indicator removed for cleaner UI
                
                # Resize back to original dimensions if needed
                if (h, w) != self.target_size:
                    annotated_img = cv2.resize(annotated_img, (w, h), interpolation=cv2.INTER_LINEAR)
                
                # Get tracked objects for analytics
                tracked_objs = tracking_result.get('tracked_objects', [])
                
                # Update crowd analytics with current frame data
                crowd_metrics = self.crowd_analytics.update_metrics(
                    people_count=people_count,
                    density=density,
                    tracked_objects=tracked_objs
                )
                
                # Draw crowd level overlay (clean UI)
                annotated_img = draw_crowd_overlay(
                    annotated_img, crowd_metrics, position=(w-240, 30), font_scale=0.55
                )
                
                # Add heatmap overlay if enabled (reads live toggle from Controls tab)
                if session_manager.get_data('enable_density_heatmap', True) and tracked_objs:
                    heatmap = self.crowd_analytics.update_heatmap(
                        frame_shape=annotated_img.shape[:2],
                        tracked_objects=tracked_objs
                    )
                    annotated_img = draw_heatmap_overlay(annotated_img, heatmap, alpha=0.35)

                # Zone grid rendering removed per FIX 3

                # Zone Analyzer integration (Map Area feature)
                # Get display settings from session state
                show_crowd_area = session_manager.get_data('show_crowd_area', True)
                enable_roi = session_manager.get_data('enable_roi', False)
                roi_x1 = session_manager.get_data('roi_x1', 50)
                roi_y1 = session_manager.get_data('roi_y1', 50)
                roi_x2 = session_manager.get_data('roi_x2', 300)
                roi_y2 = session_manager.get_data('roi_y2', 300)

                # Assign people to zones
                self.zone_analyzer.assign_people_to_zones(tracked_objs)

                # Zone grid rendering removed per FIX 3

                # Draw crowd bounding area
                if show_crowd_area:
                    bbox, area_m2, w_m, h_m = calculate_crowd_bounding_area(
                        tracked_objs, self.zone_analyzer.scale_x, self.zone_analyzer.scale_y)
                    annotated_img = draw_crowd_area(annotated_img, bbox, area_m2, w_m, h_m)

                # Draw ROI if enabled
                if enable_roi:
                    roi_bbox = (roi_x1, roi_y1, roi_x2, roi_y2)
                    roi_stats = self.zone_analyzer.calculate_roi_stats(tracked_objs, roi_bbox)
                    annotated_img = self.zone_analyzer.draw_roi(annotated_img, roi_bbox, roi_stats)

                # Get alerts and summary
                zone_alerts = self.zone_analyzer.check_alerts()
                zone_summary = self.zone_analyzer.get_zone_summary()

                # Store in session state for tab display
                session_manager.update_data('zone_summary', zone_summary)
                session_manager.update_data('zone_alerts', zone_alerts)

                # Enhanced alert workflow based on camera source and manual settings
                camera_source = getattr(st.session_state, 'camera_source', 'webcam')
                manual_settings_active = getattr(st.session_state, 'apply_manual_settings', False)
                # === ICSS UPDATE: TASK 2 - Get alert_mode for demo/realtime handling ===
                alert_mode = getattr(st.session_state, 'alert_mode', 'realtime')
                
                # Persist new zone alerts to Firebase with enhanced features (throttled)
                if zone_alerts:
                    prev_count = getattr(self, '_last_saved_alert_count', 0)
                    if len(zone_alerts) > prev_count:
                        # Import enhanced alert utilities
                        from utils.alert_store import get_alert_store
                        
                        for i, alert_msg in enumerate(zone_alerts[prev_count:]):
                            # Extract zone information if available
                            zone_info = None
                            if isinstance(alert_msg, dict) and 'zone_id' in alert_msg:
                                zone_info = alert_msg
                                alert_text = alert_msg.get('message', str(alert_msg))
                            else:
                                alert_text = str(alert_msg)
                            
                            # Capture current frame for snapshot
                            current_frame = annotated_img.copy()
                            
                            # Camera source and manual settings specific alert handling
                            if manual_settings_active:
                                # Use manual alert level
                                alert_severity = getattr(st.session_state, 'manual_alert_level', 'MEDIUM')
                                alert_type = "Manual Alert"
                                alert_text = f"[Manual] {alert_text}"
                            elif camera_source == 'mobile':
                                # Mobile camera: Medium risk alerts only
                                alert_severity = "MEDIUM"
                                alert_type = "Medium Risk"
                                alert_text = f"[Mobile Camera] {alert_text}"
                            else:
                                # Webcam/Live feed: Full alert severity
                                alert_severity = "HIGH" if zone_info and zone_info.get('people_count', 0) > 20 else "MEDIUM"
                                alert_type = "Zone Overcrowded"
                            
                            # === ICSS UPDATE: TASK 2 - Use alert_store.add_alert() for session_state + Firebase ===
                            # In demo mode, add [Demo] prefix and skip email
                            if alert_mode == 'demo':
                                alert_text = f"[Demo] {alert_text}"
                            
                            # Build alert dict for add_alert (stores to session_state + Firebase)
                            alert_dict = {
                                "type": alert_type,
                                "severity": alert_severity,
                                "zone": zone_info.get('zone_id') if zone_info else None,
                                "count": zone_info.get('people_count', people_count) if zone_info else people_count,
                                "density": zone_info.get('density', density) if zone_info else density,
                                "message": alert_text,
                                "image_url": None,  # Will be set if Cloudinary upload succeeds
                                "email_sent": False
                            }
                            
                            # Store in alert_store (session_state + Firebase)
                            alert_store = get_alert_store()
                            alert_store.add_alert(alert_dict)
                        
                        self._last_saved_alert_count = len(zone_alerts)
                else:
                    self._last_saved_alert_count = 0
                
                # Add crowd level to frame data
                frame_data = {
                    'people_count': people_count,
                    'density': density,
                    'flow_direction': tracking_result.get('flow_direction', 'Unknown'),
                    'risk_level': risk_level,
                    'risk_color': risk_color,
                    'model_info': tracking_result.get('model_info', {}),
                    'avg_speed': tracking_result.get('avg_speed', 0.0),
                    'tracked_objects': tracking_result.get('tracked_objects', []),
                    'tracking_results': tracking_result.get('tracking_results', []),
                    'alerts': [],
                    'crowd_level': crowd_metrics.get('crowd_level', 'Low'),
                    'peak_count': crowd_metrics.get('peak_count', 0),
                    'average_count': crowd_metrics.get('average_count', 0)
                }
                
                # Store processed frame for frame skipping
                self.last_processed_frame = annotated_img.copy()
                
            else:
                # Use legacy detection without Deep SORT (fastest mode)
                detection_result = process_frame_dual_models(
                    processed_img, model_v11, model_v8, active_models
                )
                
                annotated_img = detection_result['annotated_frame']
                people_count = detection_result['people_count']
                density = detection_result['density']
                
                # Resize back to original dimensions if needed
                if (h, w) != self.target_size:
                    annotated_img = cv2.resize(annotated_img, (w, h), interpolation=cv2.INTER_LINEAR)
                
                # Calculate risk with correct thresholds
                risk_level, risk_color = classify_risk(
                    density, 
                    people_count,
                    low_count_threshold=5,
                    medium_count_threshold=9,
                    low_density_threshold=0.1,
                    medium_density_threshold=0.2
                )
                
                # Add minimal overlays for performance
                # People count
                cv2.putText(annotated_img, f"Count: {people_count}",
                            (20, 30),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            1, (255, 0, 0), 2)
                
                # Risk level (color-coded)
                cv2.putText(annotated_img, f"Risk: {risk_level}",
                            (20, 60),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.8, risk_color, 2)
                
                # Performance indicator
                cv2.putText(annotated_img, "Fast Mode",
                            (20, 90),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.6, (0, 255, 0), 2)
                
                # Frame skip indicator
                cv2.putText(annotated_img, f"Skip: 1/{self.process_every_n_frames}",
                            (20, 120),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.6, (255, 255, 0), 2)
                
                # Prepare frame data
                frame_data = {
                    'people_count': people_count,
                    'density': density,
                    'flow_direction': "Unknown",
                    'risk_level': risk_level,
                    'risk_color': risk_color,
                    'model_info': detection_result.get('model_info', {}),
                    'avg_speed': 0.0,
                    'tracked_objects': [],
                    'tracking_results': [],
                    'alerts': []
                }
            
            # === ICSS UPDATE: TASK 1 - Calculate formula-based metrics ===
            # Calculate formula metrics using density and tracked objects
            try:
                tracked_objects = frame_data.get('tracked_objects', [])
                formula_metrics = calculate_crowd_metrics(
                    density=density,
                    tracks=tracked_objects,
                    frame_area=None,  # Will use default scaling
                    d_critical=1.5,
                    alpha=0.40,
                    beta=0.35,
                    gamma=0.25,
                    pixel_to_meter=0.01
                )
                # Store in session state for Analytics tab display
                session_manager.update_data('formula_metrics', formula_metrics)
            except Exception as e:
                # If calculation fails, store None
                session_manager.update_data('formula_metrics', None)
            
            # Update session state with frame data (thread-safe update will be handled by main thread)
            try:
                session_manager.update_data('current_frame_data', frame_data)
            except:
                pass  # Ignore session state errors in async thread

            # Persist to Firebase every 30 frames (~1 s at 30 fps) to avoid flooding the DB
            if self.frame_count % 30 == 0:
                insert_metric(
                    people_count  = frame_data.get('people_count', 0),
                    density       = frame_data.get('density', 0.0),
                    flow_direction= frame_data.get('flow_direction', 'Unknown'),
                    risk_level    = frame_data.get('risk_level', 'Normal'),
                    crowd_level   = frame_data.get('crowd_level', 'Low'),
                    peak_count    = frame_data.get('peak_count', 0),
                    average_count = frame_data.get('average_count', 0.0),
                )

            # === ICSS UPDATE: TASK 2 - Call process_alert for real-time alerts ===
            # Determine severity based on risk level
            risk_lvl = frame_data.get('risk_level', 'Normal')
            people_count = frame_data.get('people_count', 0)
            density = frame_data.get('density', 0.0)
            
            print(f"[WEBCAM DEBUG] risk_level={risk_lvl}, count={people_count}, density={density:.3f}")
            
            if risk_lvl == 'HIGH':
                severity = 'HIGH'
            elif risk_lvl == 'CRITICAL':
                severity = 'CRITICAL'
            elif risk_lvl == 'MEDIUM':
                severity = 'MEDIUM'
            elif risk_lvl == 'LOW':
                severity = 'LOW'
            else:
                severity = 'LOW'

            # Build alert data
            alert_data = {
                "timestamp": time.time(),
                "type": "crowd",
                "severity": severity,
                "count": people_count,
                "density": density,
                "message": f"[Webcam] {risk_lvl} Risk - {people_count} people, density {density:.3f} p/m²"
            }

            # Capture and upload snapshot for HIGH/CRITICAL alerts
            image_url = None
            if severity in ["HIGH", "CRITICAL"]:
                try:
                    from utils.cloudinary_helper import upload_snapshot
                    # Upload the annotated frame (with detection boxes)
                    success, url = upload_snapshot(annotated_img)
                    if success:
                        image_url = url
                        alert_data["image_url"] = url
                        print(f"[WEBCAM DEBUG] Snapshot uploaded: {url}")
                except Exception as e:
                    print(f"[WEBCAM DEBUG] Failed to upload snapshot: {e}")
            
            print(f"[WEBCAM DEBUG] alert_data severity={severity}")

            # Call process_alert (handles cooldown, mode, Firebase, email, UI)
            try:
                from utils.alert_manager import process_alert
                process_alert(alert_data)
            except Exception as e:
                pass  # Don't break the video loop for alert errors

            # Return processed frame as a new VideoFrame
            return VideoFrame.from_ndarray(annotated_img, format="bgr24")
            
        except Exception as e:
            # Add error text to frame if detection fails
            error_img = frame.to_ndarray(format="bgr24")
            cv2.putText(error_img, f"Tracking Error: {str(e)}",
                        (20, 50),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.7, (0, 0, 255), 2)
            # Return error frame as VideoFrame
            return VideoFrame.from_ndarray(error_img, format="bgr24")

# ================= VIDEO FILE PROCESSOR WITH DEEP SORT =================
def process_uploaded_video(video_file):
    """
    Process uploaded video file frame by frame with Deep SORT tracking
    """
    tfile = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
    tfile.write(video_file.read())
    tfile.close()  # Close the file before OpenCV accesses it
    
    cap = cv2.VideoCapture(tfile.name)
    
    if not cap.isOpened():
        st.error("Error: Could not open video file")
        # Clean up temp file if video can't be opened
        try:
            os.unlink(tfile.name)
        except:
            pass
        return
    
    # Get video properties
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    st.info(f"Video loaded: {total_frames} frames at {fps} FPS")
    
    # Create placeholder for video display
    video_placeholder = st.empty()
    
    # Initialize Deep SORT tracker for video processing
    video_tracker = init_tracker(max_age=30, n_init=3, nms_max_overlap=0.3)
    
    # Process frames
    frame_count = 0
    processed_frames = 0
    
    # Create stop button outside the loop to avoid duplicate keys
    stop_processing = st.button("⏹️ Stop Processing", key="stop_video_processing")
    
    try:
        while cap.isOpened() and frame_count < total_frames:
            ret, frame = cap.read()
            
            if not ret:
                break
            
            # Check if user requested to stop processing
            if stop_processing:
                st.info("Video processing stopped by user")
                break
            
            # Process every nth frame for performance
            if frame_count % max(1, fps // 10) == 0:  # Process ~10 frames per second
                try:
                    # Use Deep SORT integrated tracking pipeline
                    tracking_result = process_frame_with_deep_sort(
                        frame, model_v11, model_v8, video_tracker, st.session_state.active_models, fps, model_v11m=model_v11m
                    )
                    
                    # Get annotated frame with tracking information
                    annotated_frame = tracking_result['annotated_frame']
                    
                    # Risk level indicator removed for cleaner UI
                    
                    # Add system overlays to annotated frame
                    # People count
                    cv2.putText(annotated_frame, f"Count: {tracking_result['people_count']}",
                                (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)
                    
                    # Density
                    cv2.putText(annotated_frame, f"Density: {tracking_result['density']:.4f}",
                                (20, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
                    
                    # Flow direction
                    cv2.putText(annotated_frame, f"Flow: {tracking_result['flow_direction']}",
                                (20, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)
                    
                    # Risk level
                    cv2.putText(annotated_frame, f"Risk: {tracking_result['risk_level']}",
                                (20, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.8, tracking_result['risk_color'], 2)
                    
                    # Average speed
                    cv2.putText(annotated_frame, f"Avg Speed: {tracking_result['avg_speed']:.1f} px/s",
                                (20, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
                    
                    # Dual model info
                    active_models_str = "+".join(st.session_state.active_models).upper()
                    cv2.putText(annotated_frame, f"Models: {active_models_str}",
                                (20, 180), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                    
                    # Frame info
                    cv2.putText(annotated_frame, f"Frame: {frame_count}/{total_frames}",
                                (20, 210), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                    
                    # Store in session state
                    st.session_state.current_frame_data = {
                        'people_count': tracking_result['people_count'],
                        'density': tracking_result['density'],
                        'flow_direction': tracking_result['flow_direction'],
                        'risk_level': tracking_result['risk_level'],
                        'risk_color': tracking_result['risk_color'],
                        'model_info': tracking_result['model_info'],
                        'avg_speed': tracking_result['avg_speed'],
                        'tracked_objects': tracking_result['tracked_objects'],
                        'tracking_results': tracking_result['tracking_results'],
                        'frame_number': frame_count,
                        'total_frames': total_frames
                    }
                    
                    # Display annotated frame
                    video_placeholder.image(annotated_frame, channels="BGR", width=safe_width(640))
                    processed_frames += 1

                    # Persist to Firebase every 30 processed frames
                    if processed_frames % 30 == 0:
                        insert_metric(
                            people_count  = tracking_result.get('people_count', 0),
                            density       = tracking_result.get('density', 0.0),
                            flow_direction= tracking_result.get('flow_direction', 'Unknown'),
                            risk_level    = tracking_result.get('risk_level', 'Normal'),
                        )

                except Exception as e:
                    # Add error text to frame if detection fails
                    error_frame = frame.copy()
                    cv2.putText(error_frame, f"Tracking Error: {str(e)}",
                                (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                    video_placeholder.image(error_frame, channels="BGR", width=safe_width(640))
            
            frame_count += 1
            
            # Add small delay for playback effect
            cv2.waitKey(1000 // fps)
            
    except Exception as e:
        st.error(f"Video processing error: {str(e)}")
    
    finally:
        # Always release resources and clean up
        cap.release()
        cv2.destroyAllWindows()
        
        # Clean up temp file with error handling
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                os.unlink(tfile.name)
                break
            except PermissionError:
                if attempt < max_attempts - 1:
                    time.sleep(0.5)  # Wait before retry
                else:
                    st.warning(f"Could not delete temporary file: {tfile.name}")
            except Exception as e:
                st.warning(f"Cleanup warning: {str(e)}")
                break
    
    # Show processing summary
    st.success(f"Video processing completed! Processed {processed_frames} frames out of {total_frames}")

# ================= MAIN UI WITH TABS =================
# FIXED: Bug 3 Step D - Drain alert queue in main thread before tabs
from utils.alert_store import drain_alert_queue
new_alerts = drain_alert_queue()
if new_alerts:
    if "alert_history" not in st.session_state:
        st.session_state["alert_history"] = []
    st.session_state["alert_history"].extend(new_alerts)
    # Cap at 100
    st.session_state["alert_history"] = st.session_state["alert_history"][-100:]
    st.session_state["last_alert_refresh"] = time.time()

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["🎥 Live Feed", "📊 Analytics", "🗺️ Map Area", "📂 Cloud DB", "⚙️ Controls", "🚨 Alerts"])

with tab1:
    st.subheader("Live Surveillance Feed")
    
    # Zone grid status removed per FIX 3
    
    st.markdown("---")
    
    # Input mode selection and content in side-by-side layout
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown("### 📹 Input Settings")
        
        # Input mode selection
        st.session_state.input_mode = st.selectbox(
            "Input Mode",
            ["Webcam (Live)", "Mobile Camera (IP Webcam)", "Upload Video"],
            index=0 if st.session_state.input_mode == "Webcam (Live)" else 1 if st.session_state.input_mode == "Mobile Camera (IP Webcam)" else 2,
            key="input_mode_selector"
        )
        
        # Mode-specific info
        if st.session_state.input_mode == "Webcam (Live)":
            st.info("📹 Using live webcam feed")
            st.markdown("""
            **Webcam Features:**
            - Real-time processing
            - Deep SORT tracking
            - Live analytics
            - Instant alerts
            """)
        elif st.session_state.input_mode == "Mobile Camera (IP Webcam)":
            cam_mode = st.session_state.get("camera_mode", "Public URL (ngrok / Tunnel)")
            if cam_mode == "Browser WebRTC (no tunnel)":
                st.info("📹 Browser WebRTC mode — camera streamed directly from your browser.")
                st.markdown("""
            **Browser WebRTC Features:**
            - No tunnel or local network required
            - Camera runs entirely in your browser
            - Same detection capabilities as webcam mode
            - Works without any extra setup
            """)
            else:
                st.info("📱 Using mobile camera via public tunnel URL")
                st.markdown("""
            **Mobile Camera Features:**
            - Streams over the internet via ngrok / Cloudflare Tunnel
            - Configure the URL in the sidebar → Mobile Camera
            - Same detection capabilities
            - Flexible phone positioning
            """)
        else:
            st.info("📁 Video file upload mode")
            st.markdown("""
            **Upload Features:**
            - Frame-by-frame analysis
            - Complete video processing
            - Detailed tracking history
            - Post-processing analytics
            """)
        
        # System status
        st.markdown("### 📊 System Status")
        
        # Deep SORT status
        deep_sort_status = "🟢 Active" if st.session_state.get('enable_deep_sort', True) else "🔴 Disabled"
        st.metric("Deep SORT", deep_sort_status)
        
        # Active models
        active_models_display = "+".join(st.session_state.active_models).upper()
        st.metric("Models", active_models_display)
        
        # CSRNet status — cache in session_state so model is NOT re-created on every rerun
        if 'csrnet_estimator' not in st.session_state:
            try:
                st.session_state.csrnet_estimator = init_density_estimator()
            except Exception:
                st.session_state.csrnet_estimator = None
        csrnet_estimator = st.session_state.csrnet_estimator
        if csrnet_estimator is not None and csrnet_estimator.is_available():
            st.success("✅ CSRNet Active")
        else:
            st.warning("⚠️ CSRNet Not Loaded — Using YOLO count only")
        
        # ISSUE 2 FIX: Debug panel
        st.markdown("### 🔍 Debug Panel")
        if st.session_state.current_frame_data:
            data = st.session_state.current_frame_data
            yolo_detections = len(data.get('tracked_objects', []))
            deep_sort_tracks = len(data.get('tracked_objects', []))
            current_density = data.get('density', 0.0)
            current_risk = data.get('risk_level', 'Unknown')
            
            st.metric("YOLO Detections", yolo_detections)
            st.metric("Deep SORT Tracks", deep_sort_tracks)
            st.metric("Density", f"{current_density:.4f}")
            st.metric("Risk Level", current_risk)
        else:
            st.info("No frame data yet")
        
        # Performance info
        st.markdown("### ⚡ Performance")
        st.markdown("""
        - **FPS**: ~25-30 frames/sec
        - **Latency**: <500ms
        - **Tracking**: Deep SORT
        - **Detection**: YOLO v11/v8
        """)
    
    with col2:
        st.markdown("### 🎥 Live Feed")
        
        # === LIVE ALERT DISPLAY ===
        # Check for new alerts and display them
        alerts_list = st.session_state.get("alerts_list", [])
        if alerts_list:
            latest_alert = alerts_list[0]
            alert_severity = latest_alert.get("severity", "LOW")
            alert_message = latest_alert.get("message", "")
            
            # Display alert banner
            if alert_severity in ["HIGH", "CRITICAL"]:
                st.error(f"🚨 {alert_severity} ALERT: {alert_message}")
                # Play beep sound for HIGH/CRITICAL alerts
                if "last_alert_sound_time" not in st.session_state:
                    st.session_state.last_alert_sound_time = 0
                current_time = time.time()
                if current_time - st.session_state.last_alert_sound_time > 10:  # Play sound every 10 seconds
                    play_alert_sound()
                    st.session_state.last_alert_sound_time = current_time
            elif alert_severity == "MEDIUM":
                st.warning(f"⚠️ MEDIUM ALERT: {alert_message}")
            elif alert_severity == "LOW":
                st.info(f"ℹ️ LOW ALERT: {alert_message}")
        
        if st.session_state.input_mode == "Webcam (Live)":
            # Set camera source for alert workflow
            st.session_state.camera_source = "webcam"
            
            # ================= WEBRTC STREAM =================
            try:
                webrtc_streamer(
                    key="crowd-detection",
                    rtc_configuration=RTC_CONFIGURATION,
                    video_processor_factory=VideoProcessor,
                    media_stream_constraints={"video": True, "audio": False},
                    async_processing=True,
                )
            except AttributeError:
                # streamlit-webrtc internal _polling_thread not yet initialised
                # on rapid reruns — safe to ignore, component will recover.
                st.info("Camera initialising — please wait a moment.")
        elif st.session_state.input_mode == "Mobile Camera (IP Webcam)":
            # Set camera source for alert workflow
            st.session_state.camera_source = "mobile"
            
            # ================= MOBILE CAMERA — URL or WebRTC =================
            cam_mode = st.session_state.get("camera_mode", "Public URL (ngrok / Tunnel)")

            if cam_mode == "Browser WebRTC (no tunnel)":
                # ── Option B: browser WebRTC (same as webcam mode) ──────────
                st.info("📹 Browser WebRTC active — using your browser camera as the mobile source.")
                try:
                    webrtc_streamer(
                        key="mobile-webrtc",
                        rtc_configuration=RTC_CONFIGURATION,
                        video_processor_factory=VideoProcessor,
                        media_stream_constraints={"video": True, "audio": False},
                        async_processing=True,
                    )
                except AttributeError:
                    # streamlit-webrtc internal _polling_thread not yet initialised
                    # on rapid reruns — safe to ignore, component will recover.
                    st.info("⏳ Camera initialising — please wait a moment.")

            else:
                # ── Option A: public URL stream ─────────────────────────────
                mobile_stream = st.session_state.get('mobile_stream', None)

                if mobile_stream is None or not mobile_stream.connected:
                    st.warning(
                        "📱 Mobile camera not connected.\n\n"
                        "Go to the **sidebar → Mobile Camera** section, enter your "
                        "ngrok / Cloudflare Tunnel URL, then click **▶ Connect**.\n\n"
                        "Local IPs (192.168.x.x) may not be accessible - "
                        "a public tunnel URL is recommended."
                    )
                else:
                    st.success(
                        f"🟢 Mobile Camera Live | {mobile_stream.fps} FPS | {mobile_stream.base_url}"
                    )

                    # Placeholders for live updating
                    frame_placeholder = st.empty()
                    metrics_placeholder = st.empty()

                    # Use session state for stop control
                    if 'stop_mobile_feed' not in st.session_state:
                        st.session_state['stop_mobile_feed'] = False

                    stop_btn = st.button("⏹ Stop Mobile Feed", key="stop_mobile")
                    if stop_btn:
                        st.session_state['stop_mobile_feed'] = True
                        st.rerun()

                    # Get shared models + tracker from session_state
                    model_v11_local    = st.session_state.get('model_v11')
                    model_v8_local     = st.session_state.get('model_v8')
                    model_v11m_local   = st.session_state.get('model_v11m')
                    tracker_local      = st.session_state.get('tracker')
                    zone_analyzer_local = st.session_state.get('zone_analyzer')
                    alert_manager_local = st.session_state.get('alert_manager')
                    active_models_local = st.session_state.get('active_models', ['v11'])

                    # ── MOBILE FEED LOOP ─────────────────────────────────
                    while not st.session_state.get('stop_mobile_feed', False):
                        raw_frame = mobile_stream.get_frame()

                        if raw_frame is None:
                            frame_placeholder.info("⏳ Waiting for frame...")
                            time.sleep(0.05)
                            continue

                        try:
                            result = process_frame_with_deep_sort(
                                frame=raw_frame.copy(),
                                model_v11=model_v11_local,
                                model_v8=model_v8_local,
                                tracker=tracker_local,
                                active_models=active_models_local,
                                fps=mobile_stream.fps,
                                model_v11m=model_v11m_local
                            )

                            # RULE B - Hard cap of 8 people for mobile camera
                            result['people_count'] = min(result['people_count'], 8)

                            annotated = result['annotated_frame']

                            # Zone analysis removed per FIX 3
                            zone_summary = []

                            # ── Alert checks ─────────────────────────────
                            if alert_manager_local:
                                # === ICSS UPDATE: TASK 2 - Wire alert_mode and camera_source ===
                                alert_mode = st.session_state.get('alert_mode', 'realtime')
                                camera_source = 'mobile'
                                new_alerts = alert_manager_local.process_all(
                                    risk_level=result['risk_level'],
                                    count=result['people_count'],
                                    density=result['density'],
                                    zones=zone_summary,
                                    mobile_camera=True,  # Legacy parameter
                                    alert_mode=alert_mode,
                                    camera_source=camera_source
                                )
                                if new_alerts:
                                    critical = [
                                        a for a in new_alerts
                                        if a.severity.value == "CRITICAL"
                                    ]
                                    if critical:
                                        play_alert_sound()

                            # === ICSS UPDATE: TASK 2 - Call process_alert for real-time alerts ===
                            risk_lvl = result.get('risk_level', 'Normal')
                            if risk_lvl == 'HIGH':
                                severity = 'HIGH'
                            elif risk_lvl == 'CRITICAL':
                                severity = 'CRITICAL'
                            elif risk_lvl == 'MEDIUM':
                                severity = 'MEDIUM'
                            elif risk_lvl == 'LOW':
                                severity = 'LOW'
                            else:
                                severity = 'LOW'

                            alert_data = {
                                "timestamp": time.time(),
                                "type": "crowd",
                                "severity": severity,
                                "count": result.get('people_count', 0),
                                "density": result.get('density', 0.0),
                                "message": f"[Mobile] {risk_lvl} Risk - {result.get('people_count', 0)} people, density {result.get('density', 0.0):.3f} p/m²"
                            }

                            # Capture and upload snapshot for HIGH/CRITICAL alerts
                            if severity in ["HIGH", "CRITICAL"]:
                                try:
                                    from utils.cloudinary_helper import upload_snapshot
                                    # Upload the annotated frame (with detection boxes)
                                    success, url = upload_snapshot(annotated)
                                    if success:
                                        alert_data["image_url"] = url
                                        print(f"[MOBILE DEBUG] Snapshot uploaded: {url}")
                                except Exception as e:
                                    print(f"[MOBILE DEBUG] Failed to upload snapshot: {e}")

                            try:
                                from utils.alert_manager import process_alert
                                process_alert(alert_data)
                            except Exception:
                                pass

                            # ── Convert BGR → RGB for st.image() ──────────
                            rgb_frame = cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB)
                            frame_placeholder.image(
                                rgb_frame,
                                channels="RGB",
                                width='stretch',
                                caption=(
                                    f"📱 Mobile Feed | "
                                    f"👥 {result['people_count']} people | "
                                    f"⚡ {result['risk_level']}"
                                )
                            )

                            with metrics_placeholder.container():
                                col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
                                col1.metric("👥 People", result['people_count'])
                                col2.metric("📊 Density", f"{result['density']:.4f}")
                                col3.metric("⚡ Risk", result['risk_level'])
                                col4.metric("📡 FPS", mobile_stream.fps)

                            st.session_state['last_people_count'] = result['people_count']
                            st.session_state['last_density']      = result['density']
                            st.session_state['last_risk_level']   = result['risk_level']

                        except Exception as e:
                            frame_placeholder.error(f"Detection error: {str(e)}")

                        time.sleep(0.033)   # ~30 FPS cap

                    # User clicked Stop
                    st.info("📱 Mobile feed stopped.")
        else:
            st.markdown("### 📁 Video Upload")
            
            # Video file uploader
            uploaded_file = st.file_uploader(
                "Choose a video file",
                type=['mp4', 'avi', 'mov', 'mkv'],
                help="Upload video files for crowd analysis",
                key="video_uploader"
            )
            
            if uploaded_file is not None:
                st.success(f"File uploaded: {uploaded_file.name}")
                
                # Process button
                if st.button("🎬 Process Video", type="primary", key="process_video_btn"):
                    with st.spinner("Processing video..."):
                        process_uploaded_video(uploaded_file)
            else:
                st.warning("Please upload a video file to begin analysis")
                
                # Show placeholder for video
                st.markdown("""
                <div style="
                    border: 2px dashed #ccc;
                    border-radius: 10px;
                    padding: 40px;
                    text-align: center;
                    background-color: #f9f9f9;
                ">
                    <h3>📹 Video Preview Area</h3>
                    <p>Upload a video file to see the analysis here</p>
                </div>
                """, unsafe_allow_html=True)

with tab2:
    st.subheader("📊 Advanced Real-time Analytics")
    if st.session_state.current_frame_data:
        data = st.session_state.current_frame_data
        
        # Check if advanced analytics data is available
        advanced_data = data.get('advanced_analytics')
        
        if advanced_data:
            # Advanced Analytics Dashboard
            st.markdown("### 🎯 Advanced Analytics Dashboard")
            
            # Risk Analysis Section
            if advanced_data.get('risk_analysis'):
                risk_data = advanced_data['risk_analysis']
                
                st.markdown("#### 🚨 Risk Assessment")
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric(
                        "Risk Level", 
                        risk_data['risk_level'],
                        delta=f"Score: {risk_data['risk_score']:.2f}"
                    )
                
                with col2:
                    # Risk level color indicator
                    risk_color_rgb = risk_data['risk_color']
                    risk_hex = '#{:02x}{:02x}{:02x}'.format(risk_color_rgb[2], risk_color_rgb[1], risk_color_rgb[0])
                    st.markdown(f"""
                    <div style="
                        background-color: {risk_hex};
                        color: white;
                        padding: 20px;
                        border-radius: 10px;
                        text-align: center;
                        font-weight: bold;
                    ">
                        {risk_data['risk_level']}
                    </div>
                    """, unsafe_allow_html=True)
                
                with col3:
                    st.metric(
                        "Density Factor",
                        f"{risk_data['normalized_inputs']['density']:.2f}",
                        delta="High" if risk_data['normalized_inputs']['density'] > 0.5 else "Normal"
                    )
                
                with col4:
                    st.metric(
                        "Flow Conflict",
                        f"{risk_data['normalized_inputs']['flow_conflict']:.2f}",
                        delta="Detected" if risk_data['normalized_inputs']['flow_conflict'] > 0.3 else "Clear"
                    )
                
                # Risk Alert
                st.info(f"� **Explainable Alert**: {risk_data['risk_alert']}")
            
            # Zone Analysis Section
            if advanced_data.get('zone_analysis'):
                zone_data = advanced_data['zone_analysis']
                zone_summary = zone_data['summary']
                
                st.markdown("#### 🗺️ Zone Analysis")
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric(
                        "Total Zones",
                        zone_summary['total_zones']
                    )
                
                with col2:
                    st.metric(
                        "People in Zones",
                        zone_summary['total_people']
                    )
                
                with col3:
                    overcrowded_count = len(zone_summary['overcrowded_zones'])
                    st.metric(
                        "Overcrowded Zones",
                        overcrowded_count,
                        delta="Alert" if overcrowded_count > 0 else "Clear"
                    )
                
                with col4:
                    violation_count = len(zone_summary['violation_zones'])
                    st.metric(
                        "Zone Violations",
                        violation_count,
                        delta="Warning" if violation_count > 0 else "Clear"
                    )
                
                # Zone Details Table
                if zone_summary['zone_details']:
                    st.markdown("**Zone Details:**")
                    zone_df_data = []
                    for zone_id, stats in zone_summary['zone_details'].items():
                        zone_df_data.append({
                            'Zone': zone_id,
                            'People': stats['people_count'],
                            'Density': f"{stats['density']:.2f}",
                            'Status': '🔴 Overcrowded' if stats['is_overcrowded'] else '🟡 Moderate' if stats['density'] > 0.5 else '🟢 Normal',
                            'Violation': '⚠️ Yes' if stats['is_violation'] else '✅ No'
                        })
                    
                    st.dataframe(zone_df_data, width="stretch")
            
            # Flow Analysis Section
            if advanced_data.get('flow_analysis'):
                flow_data = advanced_data['flow_analysis']
                flow_metrics = flow_data['metrics']
                flow_summary = flow_data['summary']
                
                st.markdown("#### 🌊 Flow Analysis")
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric(
                        "Tracked Objects",
                        flow_metrics.total_objects
                    )
                
                with col2:
                    st.metric(
                        "Dominant Flow",
                        flow_metrics.dominant_direction
                    )
                
                with col3:
                    conflict_status = "⚠️ Conflict" if flow_metrics.bidirectional_conflict else "✅ Clear"
                    st.metric(
                        "Flow Conflict",
                        conflict_status
                    )
                
                with col4:
                    surge_status = "🚨 Surge" if flow_metrics.surge_detected else "📊 Normal"
                    st.metric(
                        "Crowd Surge",
                        surge_status
                    )
                
                # Flow Distribution
                if flow_metrics.direction_percentages:
                    st.markdown("**Flow Distribution:**")
                    flow_cols = st.columns(min(5, len(flow_metrics.direction_percentages)))
                    col_idx = 0
                    for direction, percentage in flow_metrics.direction_percentages.items():
                        with flow_cols[col_idx % len(flow_cols)]:
                            st.metric(direction, f"{percentage:.1f}%")
                        col_idx += 1
                
                # Flow Alerts
                if flow_summary['active_alerts']:
                    for alert in flow_summary['active_alerts']:
                        st.warning(f"🌊 **Flow Alert**: {alert}")
            
            # Combined Alerts Section
            if data.get('alerts'):
                st.markdown("#### 🚨 System Alerts")
                for alert in data['alerts']:
                    if "Risk" in alert:
                        st.error(f"🚨 **Risk Alert**: {alert}")
                    elif "Zone" in alert:
                        st.warning(f"🗺️ **Zone Alert**: {alert}")
                    elif "Flow" in alert or "Surge" in alert:
                        st.info(f"🌊 **Flow Alert**: {alert}")
                    else:
                        st.info(f"📊 **System Alert**: {alert}")
        
        else:
            # Legacy Analytics Display (fallback)
            st.markdown("### 📊 Basic Analytics")
            
            # Metrics grid
            col1, col2, col3, col4, col5 = st.columns(5)
            
            with col1:
                st.metric(
                    "👥 People Count", 
                    data['people_count'],
                    delta="Active" if data['people_count'] > 0 else "No Detection"
                )
            
            with col2:
                st.metric(
                    "📈 Density", 
                    f"{data['density']:.4f}",
                    delta="High" if data['density'] > 1.0 else "Normal"
                )
            
            with col3:
                # Flow direction with arrow
                arrow_symbols = {
                    "Left": "←", "Right": "→", "Up": "↑", 
                    "Down": "↓", "Mixed": "↔", "Unknown": "?"
                }
                flow_symbol = arrow_symbols.get(data['flow_direction'], "?")
                st.metric(
                    f"🧭 Flow {flow_symbol}", 
                    data['flow_direction'],
                    delta="Detected" if data['flow_direction'] != "Unknown" else "No Data"
                )
            
            with col4:
                # Risk level with color
                risk_colors = {
                    "Normal": "green", "Average": "orange", "Risky": "red"
                }
                risk_color = risk_colors.get(data['risk_level'], "gray")
                st.metric(
                    "⚠️ Risk Level", 
                    data['risk_level'],
                    delta="Alert" if data['risk_level'] == "Risky" else "Monitoring"
                )
            
            with col5:
                # Average speed
                avg_speed = data.get('avg_speed', 0.0)
                st.metric(
                    "⚡ Avg Speed", 
                    f"{avg_speed:.1f} px/s",
                    delta="Moving" if avg_speed > 5.0 else "Static"
                )
            
            # Model information display
            st.markdown("---")
            st.subheader("🤖 Model Performance")
            
            # Model information
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric(
                    "🤖 Active Models", 
                    "+".join(st.session_state.active_models).upper(),
                    delta="Dual Mode" if len(st.session_state.active_models) > 1 else "Single Mode"
                )
            
            with col2:
                if 'detection_count' in data and 'merged_count' in data:
                    st.metric(
                        "🎯 Raw Detections", 
                        data['detection_count'],
                        delta=f"Merged: {data['merged_count']}"
                    )
                else:
                    st.metric("🎯 Raw Detections", "--")
            
            with col3:
                if 'model_info' in data:
                    model_status = "✅ " + " | ".join([f"{k.upper()}: {v}" for k, v in data['model_info'].items() if "Active" in v])
                    st.text(model_status)
                else:
                    st.metric("📊 Model Status", "--")
            
            st.markdown("---")
            st.subheader("🚨 Risk Assessment")
            
            # Color-coded risk indicator
            risk_html = f"""
            <div style="
                background-color: {data['risk_color']};
                color: white;
                padding: 20px;
                border-radius: 10px;
                text-align: center;
                font-size: 24px;
                font-weight: bold;
            ">
                {data['risk_level']} RISK LEVEL
            </div>
            """
            st.markdown(risk_html, unsafe_allow_html=True)
            
            # Additional info
            if data['risk_level'] == "Risky":
                st.error("⚠️ High crowd density detected! Consider crowd control measures.")
            elif data['risk_level'] == "Average":
                st.warning("⚡ Moderate crowd density. Monitor situation closely.")
            else:
                st.success("✅ Normal crowd density. No immediate action required.")
        
        # === ICSS UPDATE: TASK 1 - Formula-Based Metrics Display ===
        st.markdown("---")
        with st.expander("📐 Formula-Based Metrics", expanded=False):
            formula_metrics = st.session_state.get("formula_metrics")
            
            if formula_metrics is None:
                st.info("Processing formula metrics...")
            else:
                # Display formula metrics in 3-column layout
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric(
                        "Flow Rate Q",
                        f"{formula_metrics['flow_rate']:.4f}",
                        help="Formula: Q = D × V (people per second per meter)"
                    )
                
                with col2:
                    st.metric(
                        "Congestion Index C",
                        f"{formula_metrics['congestion_index']:.4f}",
                        help="Formula: C = D / D_critical (D_critical = 1.5 p/m²)"
                    )
                
                with col3:
                    st.metric(
                        "Formula Risk Score R",
                        f"{formula_metrics['risk_score']:.4f}",
                        help="Formula: R = αD + βQ + γC (α=0.40, β=0.35, γ=0.25)"
                    )
                
                st.markdown("---")
                
                # Display additional formula metrics
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric(
                        "Velocity V",
                        f"{formula_metrics['velocity']:.4f} m/s",
                        help="Average crowd velocity from Deep SORT tracking"
                    )
                
                with col2:
                    # is_dangerous badge
                    if formula_metrics['is_dangerous']:
                        st.markdown("🔴 **DANGEROUS** - Congestion index > 1.0")
                    else:
                        st.markdown("🟢 **SAFE** - Congestion index ≤ 1.0")
                
                with col3:
                    st.metric(
                        "Formula Risk Level",
                        formula_metrics['formula_risk_level'],
                        help="Based on composite risk score R"
                    )
    
    # Trend Visualization Charts
    st.markdown("---")
    st.subheader("📈 Historical Trend Analysis")
    
    # Get analytics data
    analytics_df = get_analytics_data(limit=100)
    
    if not analytics_df.empty:
        # Chart 1: People Count Trend (Line Chart)
        st.markdown("#### 👥 People Count Trend")
        fig_count = go.Figure()
        fig_count.add_trace(go.Scatter(
            x=analytics_df['timestamp'],
            y=analytics_df['people_count'],
            mode='lines+markers',
            name='People Count',
            line=dict(color='#3498db', width=2),
            marker=dict(size=6)
        ))
        fig_count.update_layout(
            title='People Count Over Time',
            xaxis_title='Timestamp',
            yaxis_title='People Count',
            hovermode='x unified',
            height=300
        )
        st.plotly_chart(fig_count, width='stretch')
        
        # Chart 2: Density Trend (Line Chart)
        st.markdown("#### 📈 Density Trend")
        fig_density = go.Figure()
        fig_density.add_trace(go.Scatter(
            x=analytics_df['timestamp'],
            y=analytics_df['density'],
            mode='lines+markers',
            name='Density',
            line=dict(color='#e74c3c', width=2),
            marker=dict(size=6)
        ))
        fig_density.update_layout(
            title='Density Over Time',
            xaxis_title='Timestamp',
            yaxis_title='Density (p/m²)',
            hovermode='x unified',
            height=300
        )
        st.plotly_chart(fig_density, width='stretch')
        
        # Charts 3 & 4: Side by side - Risk Distribution and Flow Direction
        col1, col2 = st.columns(2)
        
        with col1:
            # Chart 3: Risk Level Distribution (Pie Chart)
            st.markdown("#### ⚠️ Risk Level Distribution")
            risk_counts = analytics_df['risk_level'].value_counts()
            fig_risk = go.Figure(data=[go.Pie(
                labels=risk_counts.index,
                values=risk_counts.values,
                hole=0.4,
                marker=dict(colors=['#2ecc71', '#f39c12', '#e74c3c'])
            )])
            fig_risk.update_layout(
                title='Risk Level Distribution',
                height=350
            )
            st.plotly_chart(fig_risk, width='stretch')
        
        with col2:
            # Chart 4: Flow Direction Distribution (Bar Chart)
            st.markdown("#### 🧭 Flow Direction Distribution")
            flow_counts = analytics_df['flow_direction'].value_counts()
            fig_flow = go.Figure(data=[go.Bar(
                x=flow_counts.index,
                y=flow_counts.values,
                marker=dict(color=['#3498db', '#9b59b6', '#1abc9c', '#e67e22', '#95a5a6', '#bdc3c7'])
            )])
            fig_flow.update_layout(
                title='Flow Direction Distribution',
                xaxis_title='Flow Direction',
                yaxis_title='Count',
                height=350
            )
            st.plotly_chart(fig_flow, width='stretch')
    else:
        st.info("📊 No historical data available. Start video feed to collect analytics data for trend visualization.")

    with tab3:
        # ================= DUCKDB ANALYTICS DASHBOARD =================
        st.subheader("Zone Map & Area Analysis")
        
        # Zone Map Summary
        st.markdown("### 🗺️ Zone Map Summary")
        
        if st.session_state.zone_summary:
            zone_data = st.session_state.zone_summary
            
            # Overall statistics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                total_zones = len(zone_data)
                st.metric("Total Zones", total_zones)
            
            with col2:
                total_people = sum(z['people_count'] for z in zone_data)
                st.metric("Total People", total_people)
            
            with col3:
                overcrowded_zones = [z for z in zone_data if z['is_overcrowded']]
                st.metric("Overcrowded Zones", len(overcrowded_zones), 
                         delta="Alert" if overcrowded_zones else "Clear")
            
            with col4:
                avg_density = sum(z['density'] for z in zone_data) / len(zone_data)
                st.metric("Avg Density", f"{avg_density:.3f} p/m²")
            
            # Zone details table
            st.markdown("#### 📊 Zone Details")
            zone_df_data = []
            for zone in zone_data:
                zone_df_data.append({
                    'Zone ID': zone['zone_id'],
                    'People Count': zone['people_count'],
                    'Density (p/m²)': f"{zone['density']:.3f}",
                    'Area (m²)': f"{zone.get('real_area_m2', 0.0):.1f}",
                    'Status': '🔴 Overcrowded' if zone['is_overcrowded'] else '🟡 Moderate' if zone['density'] > 0.5 else '🟢 Normal',
                    'Alert': '⚠️ Yes' if zone['is_overcrowded'] else '✅ No'
                })
            
            st.dataframe(zone_df_data, width="stretch")
            
            # Zone alerts
            if st.session_state.zone_alerts:
                st.markdown("#### 🚨 Zone Alerts")
                for alert in st.session_state.zone_alerts:
                    st.warning(f"🗺️ {alert}")
            else:
                st.success("✅ No zone alerts active")
                
        else:
            st.info("📊 No zone data available. Start video feed to see zone analysis.")
        
        # ROI Analysis
        st.markdown("---")
        st.markdown("### 📍 ROI (Region of Interest) Analysis")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**ROI Settings:**")
            st.info(f"ROI Coordinates: ({st.session_state.roi_x1}, {st.session_state.roi_y1}) to ({st.session_state.roi_x2}, {st.session_state.roi_y2})")
            roi_enabled = "✅ Enabled" if st.session_state.enable_roi else "❌ Disabled"
            st.metric("ROI Status", roi_enabled)
        
        with col2:
            st.markdown("**ROI Statistics:**")
            if st.session_state.current_frame_data and st.session_state.enable_roi:
                tracked_objects = st.session_state.current_frame_data.get('tracked_objects', [])
                roi_bbox = (st.session_state.roi_x1, st.session_state.roi_y1, st.session_state.roi_x2, st.session_state.roi_y2)
                
                # Count people in ROI
                people_in_roi = 0
                for obj in tracked_objects:
                    x, y = obj.get('position', (0, 0))
                    if st.session_state.roi_x1 <= x <= st.session_state.roi_x2 and st.session_state.roi_y1 <= y <= st.session_state.roi_y2:
                        people_in_roi += 1
                
                roi_area = (st.session_state.roi_x2 - st.session_state.roi_x1) * (st.session_state.roi_y2 - st.session_state.roi_y1)
                roi_density = people_in_roi / (roi_area / 10000) if roi_area > 0 else 0  # Convert to m²
                
                st.metric("People in ROI", people_in_roi)
                st.metric("ROI Density", f"{roi_density:.3f} p/m²")
            else:
                st.metric("People in ROI", "--")
                st.metric("ROI Density", "--")
        
        # Zone grid visualization settings
        st.markdown("---")
        st.markdown("### ⚙️ Zone Display Settings")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.info("Zone grid settings are in the Controls tab under Dense Crowd Detection section")
        
        with col2:
            show_crowd_area = st.checkbox(
                "Show Crowd Bounding Area",
                value=st.session_state.show_crowd_area,
                help="Display crowd bounding area visualization"
            )
            st.session_state.show_crowd_area = show_crowd_area
            session_manager.update_data('show_crowd_area', show_crowd_area)
    
    with tab4:
        # ================= FIREBASE ANALYTICS DASHBOARD =================
        st.subheader("☁️ Cloud Database Analytics")

        if not db_is_connected():
            st.error(
                "❌ Firebase is not connected.\n\n"
                "Add FIREBASE_DATABASE_URL and GOOGLE_APPLICATION_CREDENTIALS to your .env file, "
                "then restart the app."
            )
        else:
            # ── Latest metric row ──────────────────────────────────────
            latest = fetch_latest_metric()

            if latest:
                people_count  = latest.get('people_count', 0)
                density       = latest.get('density', 0.0)
                flow_direction = latest.get('flow_direction', 'Unknown')
                risk_level    = latest.get('risk_level', 'Normal')
                timestamp     = latest.get('timestamp', '')
                st.success(f"📅 Last Updated: {timestamp}")
            else:
                people_count, density, flow_direction, risk_level = 0, 0.0, "Unknown", "Normal"
                st.info("📊 No data yet. Start video processing to populate the database.")

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("👥 People Count", people_count)
            with col2:
                st.metric("📈 Density", f"{density:.4f}")
            with col3:
                st.metric("🧭 Flow Direction", flow_direction)
            with col4:
                risk_icon = "🔴" if risk_level == "Risky" else "🟡" if risk_level == "Average" else "🟢"
                st.metric(f"{risk_icon} Risk Level", risk_level)

            # ── Historical trends ──────────────────────────────────────
            st.subheader("📈 Historical Trends")
            historical_data = fetch_recent_metrics(limit=10)

            if not historical_data.empty:
                st.dataframe(historical_data, width='stretch')

                df_chron = historical_data.iloc[::-1]  # chronological order
                avg_count   = df_chron['people_count'].mean()
                avg_density = df_chron['density'].mean()
                risk_counts = df_chron['risk_level'].value_counts().to_dict()
                risk_counts = {
                    "Normal":  risk_counts.get("Normal", 0),
                    "Average": risk_counts.get("Average", 0),
                    "Risky":   risk_counts.get("Risky", 0),
                }

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("📊 Avg Count", f"{avg_count:.1f}")
                with col2:
                    st.metric("📊 Avg Density", f"{avg_density:.4f}")
                with col3:
                    st.metric("📊 Risk Distribution", f"Normal: {risk_counts['Normal']}")

            # ── Database info ──────────────────────────────────────────
            st.subheader("💾 Database Information")
            total_records = fetch_total_record_count()
            st.info(f"📊 Total Records: {total_records}")
            st.info("☁️ Database: Firebase Realtime Database")

with tab5:
        st.subheader("⚙️ System Controls")

        # ── Model selection — explicit keys so state survives tab switches ──
        use_v11 = st.checkbox(
            "YOLO v11 Large (Primary)",
            value="v11" in st.session_state.active_models,
            key="ctrl_use_v11",
        )
        use_v8 = st.checkbox(
            "YOLO v8 Large (Secondary)",
            value="v8" in st.session_state.active_models,
            key="ctrl_use_v8",
        )
        use_v11m = st.checkbox(
            "YOLO v11 Medium (Optional)",
            value="v11m" in st.session_state.active_models,
            key="ctrl_use_v11m",
        )

        active_models = []
        if use_v11:
            active_models.append("v11")
        if use_v8:
            active_models.append("v8")
        if use_v11m:
            active_models.append("v11m")

        if active_models:
            st.session_state.active_models = active_models
            session_manager.update_data('active_models', active_models)
            st.success(f"Active models: {', '.join(active_models).upper()}")
        else:
            st.warning("Please select at least one model")

        # ── Deep SORT Toggle ─────────────────────────────────────────────
        st.markdown("---")
        st.subheader("🔍 Tracking Settings")

        st.session_state.enable_deep_sort = st.checkbox(
            "Enable Deep SORT Multi-Object Tracking",
            value=st.session_state.get("enable_deep_sort", True),
            key="ctrl_enable_deep_sort",
            help="Toggle Deep SORT tracking for persistent object IDs, speed estimation, and trajectory visualization",
        )
        session_manager.update_data('enable_deep_sort', st.session_state.enable_deep_sort)

        if st.session_state.enable_deep_sort:
            st.success("🎯 Deep SORT tracking ENABLED - Persistent IDs, Speed & Direction tracking")
        else:
            st.info("📊 Deep SORT tracking DISABLED - Basic detection only")

        # ── Advanced Analytics Toggle ────────────────────────────────────
        st.markdown("---")
        st.subheader("🧠 Advanced Analytics")

        st.session_state.enable_advanced_analytics = st.checkbox(
            "Enable Advanced Analytics Platform",
            value=st.session_state.get("enable_advanced_analytics", True),
            key="ctrl_enable_advanced_analytics",
            help="Enable intelligent risk assessment, zone monitoring, and flow analysis",
        )
        session_manager.update_data('enable_advanced_analytics', st.session_state.enable_advanced_analytics)

        if st.session_state.enable_advanced_analytics:
            st.success("🧠 Advanced Analytics ENABLED - Risk, Zones, Flow Analysis")

            st.markdown("**Analytics Modules:**")
            col1, col2 = st.columns(2)

            with col1:
                st.session_state.enable_zones = st.checkbox(
                    "Zone Monitoring",
                    value=st.session_state.get("enable_zones", True),
                    key="ctrl_enable_zones",
                    help="Enable zone-based crowd analysis",
                )
                session_manager.update_data('enable_zones', st.session_state.enable_zones)
                st.session_state.enable_flow_analysis = st.checkbox(
                    "Flow Analysis",
                    value=st.session_state.get("enable_flow_analysis", True),
                    key="ctrl_enable_flow_analysis",
                    help="Enable crowd flow pattern detection",
                )
                session_manager.update_data('enable_flow_analysis', st.session_state.enable_flow_analysis)
            with col2:
                st.session_state.enable_risk_analysis = st.checkbox(
                    "Risk Assessment",
                    value=st.session_state.get("enable_risk_analysis", True),
                    key="ctrl_enable_risk_analysis",
                    help="Enable intelligent risk evaluation",
                )
                session_manager.update_data('enable_risk_analysis', st.session_state.enable_risk_analysis)
        else:
            st.info("📊 Advanced Analytics DISABLED - Basic monitoring only")

        # ── Dense Crowd Detection (CSRNet) ───────────────────────────────
        st.markdown("---")
        st.subheader("🧪 Dense Crowd Detection")

        st.session_state.enable_csrnet = st.checkbox(
            "Enable CSRNet Density Estimation",
            value=st.session_state.get("enable_csrnet", True),
            key="ctrl_enable_csrnet",
            help="Generate density heatmaps and estimate crowd count from density maps",
        )
        session_manager.update_data('enable_csrnet', st.session_state.enable_csrnet)

        if st.session_state.enable_csrnet:
            st.success("🧪 Dense Crowd Detection ENABLED - Enhanced detection for crowded scenes")
            st.markdown("**Visualization Options:**")
            col1, col2 = st.columns(2)

            with col1:
                st.session_state.enable_density_heatmap = st.checkbox(
                    "Show Density Heatmap",
                    value=st.session_state.get("enable_density_heatmap", True),
                    key="ctrl_enable_density_heatmap",
                    help="Overlay density heatmap on video feed",
                )
                session_manager.update_data('enable_density_heatmap', st.session_state.enable_density_heatmap)
            with col2:
                # Zone grid settings removed per FIX 3
                st.info("Zone grid feature has been removed")

            grid_rows = st.slider(
                "Zone Grid Rows",
                min_value=2, max_value=5,
                value=st.session_state.dense_grid_size[0],
                step=1,
                key="ctrl_grid_rows",
                help="Number of rows in zone grid",
            )
            grid_cols = st.slider(
                "Zone Grid Columns",
                min_value=2, max_value=5,
                value=st.session_state.dense_grid_size[1],
                step=1,
                key="ctrl_grid_cols",
                help="Number of columns in zone grid",
            )
            st.session_state.dense_grid_size = (grid_rows, grid_cols)
        else:
            st.info("📊 Dense Crowd Detection DISABLED - Standard detection mode")
        
        # Detection Thresholds
        st.markdown("---")
        st.markdown("### 🔧 Detection Thresholds")
        
        col1, col2 = st.columns(2)
        
        with col1:
            low_threshold = st.slider(
                "Low Density Threshold",
                min_value=0.1,
                max_value=2.0,
                value=st.session_state.low_density_threshold,
                step=0.1,
                help="Density level to trigger 'Average' risk"
            )
            st.session_state.low_density_threshold = low_threshold
            session_manager.update_data('low_density_threshold', low_threshold)
            
            count_threshold = st.slider(
                "People Count Threshold",
                min_value=1,
                max_value=20,
                value=st.session_state.count_threshold,
                step=1,
                help="Number of people to trigger 'Risky' risk level"
            )
            st.session_state.count_threshold = count_threshold
            session_manager.update_data('count_threshold', count_threshold)
        
        with col2:
            medium_threshold = st.slider(
                "Medium Density Threshold",
                min_value=0.5,
                max_value=3.0,
                value=st.session_state.medium_density_threshold,
                step=0.1,
                help="Density level to trigger 'Risky' risk"
            )
            st.session_state.medium_density_threshold = medium_threshold
            session_manager.update_data('medium_density_threshold', medium_threshold)
        
        # Advanced Analytics Configuration
        if st.session_state.get('enable_advanced_analytics', True):
            st.markdown("---")
            st.markdown("### 🧠 Advanced Analytics Configuration")
            
            # Risk Engine Configuration
            if st.session_state.get('enable_risk_analysis', True):
                st.markdown("#### 🎯 Risk Engine Weights")
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    w_density = st.slider(
                        "Density Weight",
                        min_value=0.0,
                        max_value=1.0,
                        value=st.session_state.risk_weights['density'],
                        step=0.05,
                        help="Weight for crowd density factor in risk calculation"
                    )
                    st.session_state.risk_weights['density'] = w_density
                
                with col2:
                    w_flow = st.slider(
                        "Flow Conflict Weight",
                        min_value=0.0,
                        max_value=1.0,
                        value=st.session_state.risk_weights['flow_conflict'],
                        step=0.05,
                        help="Weight for flow conflict factor in risk calculation"
                    )
                    st.session_state.risk_weights['flow_conflict'] = w_flow
                
                with col3:
                    w_speed = st.slider(
                        "Speed Variation Weight",
                        min_value=0.0,
                        max_value=1.0,
                        value=st.session_state.risk_weights['speed_variation'],
                        step=0.05,
                        help="Weight for speed variation factor in risk calculation"
                    )
                    st.session_state.risk_weights['speed_variation'] = w_speed
                
                # Normalize weights
                total_weight = w_density + w_flow + w_speed
                if total_weight > 0:
                    st.session_state.risk_weights['density'] = w_density / total_weight
                    st.session_state.risk_weights['flow_conflict'] = w_flow / total_weight
                    st.session_state.risk_weights['speed_variation'] = w_speed / total_weight
                
                st.info(f"Normalized weights: Density={st.session_state.risk_weights['density']:.2f}, Flow={st.session_state.risk_weights['flow_conflict']:.2f}, Speed={st.session_state.risk_weights['speed_variation']:.2f}")
            
            # Zone Configuration
            if st.session_state.get('enable_zones', True):
                st.markdown("#### 🗺️ Zone Configuration")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    grid_rows = st.selectbox(
                        "Grid Rows",
                        options=[2, 3, 4],
                        index=[2, 3, 4].index(st.session_state.zone_grid_size[0]),
                        help="Number of rows in zone grid"
                    )
                    
                    grid_cols = st.selectbox(
                        "Grid Columns", 
                        options=[2, 3, 4],
                        index=[2, 3, 4].index(st.session_state.zone_grid_size[1]),
                        help="Number of columns in zone grid"
                    )
                    
                    st.session_state.zone_grid_size = (grid_rows, grid_cols)
                
                with col2:
                    # Restricted zones selection
                    zone_labels = []
                    for i in range(grid_rows * grid_cols):
                        label = chr(65 + i)  # A, B, C, D, ...
                        zone_labels.append(label)
                    
                    selected_restrictions = st.multiselect(
                        "Restricted Zones",
                        options=zone_labels,
                        default=st.session_state.restricted_zones,
                        help="Select zones to mark as restricted areas"
                    )
                    
                    st.session_state.restricted_zones = selected_restrictions
                
                st.info(f"Zone grid: {grid_rows}x{grid_cols} = {grid_rows * grid_cols} zones")
                if selected_restrictions:
                    st.warning(f"Restricted zones: {', '.join(selected_restrictions)}")
            
            # Flow Analysis Configuration
            if st.session_state.get('enable_flow_analysis', True):
                st.markdown("#### 🌊 Flow Analysis Settings")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    min_movement = st.slider(
                        "Minimum Movement Threshold",
                        min_value=1.0,
                        max_value=20.0,
                        value=5.0,
                        step=1.0,
                        help="Minimum movement in pixels to consider as motion"
                    )
                
                with col2:
                    conflict_threshold = st.slider(
                        "Flow Conflict Threshold",
                        min_value=0.1,
                        max_value=0.8,
                        value=0.3,
                        step=0.05,
                        help="Threshold for detecting bidirectional flow conflicts"
                    )
                
                st.info("Flow analysis detects crowd movement patterns and potential conflicts")
        
        # Model Information and System Info
        st.markdown("---")
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🤖 Model Information")
            st.info("""
            **YOLO v11** (model/yolo11l.pt)
            - Size: 51MB
            - Latest version
            - High accuracy
            
            **YOLO v8** (model/V8l-haj.pt)
            - Size: 87MB  
            - Legacy version
            - Good performance
            """)
        
        with col2:
            st.subheader("🎮 Quick Actions")
            if st.button("🔄 Reset Analytics", type="secondary"):
                st.session_state.current_frame_data = None
                st.session_state.flow_direction = "Unknown"
                st.session_state.risk_level = "Normal"
                st.success("Analytics reset successfully!")
            
            if st.button("📊 Export Data", type="secondary"):
                if st.session_state.current_frame_data:
                    st.json(st.session_state.current_frame_data)
                else:
                    st.warning("No data to export")
        
        # Firebase Sync Toggle
        st.markdown("---")
        st.markdown("### 🔥 Firebase Database Sync")
        
        firebase_sync = st.toggle(
            "Enable Firebase Sync",
            value=st.session_state.get("firebase_enabled", True),
            key="ctrl_firebase_sync",
            help="Toggle Firebase Realtime Database synchronization. When disabled, data is stored locally only."
        )
        st.session_state.firebase_enabled = firebase_sync
        session_manager.update_data('firebase_enabled', firebase_sync)
        
        if firebase_sync:
            if db_is_connected():
                st.success("✅ Firebase Sync ENABLED - Data will be synced to cloud database")
            else:
                st.warning("⚠️ Firebase Sync enabled but not connected - Data will be stored locally")
        else:
            st.info("🔴 Firebase Sync DISABLED - Data will be stored locally only")
        
        st.markdown("---")
        st.markdown("### 📋 System Information")
        
        st.info("""
        **System Features:**
        - Real-time person detection using YOLO v11
        - Advanced crowd tracking with centroid matching
        - Flow direction analysis with majority voting
        - 3-level risk classification system
        - Dual input support (Webcam + Video Upload)
        - Enhanced overlays with color-coded alerts
        
        **Model:** YOLO v11 (model/yolo11l.pt)
        **Processing:** Real-time frame analysis
        **Accuracy:** High precision person detection
        """)

# ================= SIDEBAR - ZONE MAP SUMMARY & ROI CONTROLS =================
st.sidebar.markdown("---")
st.sidebar.subheader("🗺️ Zone Map Summary")

if st.session_state.zone_summary:
    overcrowded = [z for z in st.session_state.zone_summary if z['is_overcrowded']]
    safest = min(st.session_state.zone_summary, key=lambda z: z['density'])
    densest = max(st.session_state.zone_summary, key=lambda z: z['density'])

    st.sidebar.metric("Total Zones", len(st.session_state.zone_summary))
    st.sidebar.metric("🚨 Overcrowded", len(overcrowded),
                      delta=None if not overcrowded else "ACTION NEEDED")
    st.sidebar.metric("Densest Zone",
                      f"{densest['zone_id']} ({densest['density']:.3f} p/m²)")
    st.sidebar.metric("Safest Zone",
                      f"{safest['zone_id']} ({safest['density']:.3f} p/m²)")
else:
    st.sidebar.info("No zone data yet")

st.sidebar.markdown("---")
st.sidebar.subheader("📍 Manual ROI Region")

frame_w = 640
frame_h = 480

roi_x1 = st.sidebar.number_input("ROI X1 (pixel)", 0, frame_w, st.session_state.roi_x1, key="sidebar_roi_x1")
roi_y1 = st.sidebar.number_input("ROI Y1 (pixel)", 0, frame_h, st.session_state.roi_y1, key="sidebar_roi_y1")
roi_x2 = st.sidebar.number_input("ROI X2 (pixel)", 0, frame_w, st.session_state.roi_x2, key="sidebar_roi_x2")
roi_y2 = st.sidebar.number_input("ROI Y2 (pixel)", 0, frame_h, st.session_state.roi_y2, key="sidebar_roi_y2")
enable_roi = st.sidebar.checkbox("✅ Enable ROI Analysis", value=st.session_state.enable_roi, key="sidebar_enable_roi")

# Update session state
st.session_state.roi_x1 = roi_x1
st.session_state.roi_y1 = roi_y1
st.session_state.roi_x2 = roi_x2
st.session_state.roi_y2 = roi_y2
st.session_state.enable_roi = enable_roi

if enable_roi:
    st.sidebar.success("ROI Analysis Enabled")
else:
    st.sidebar.info("ROI Analysis Disabled")

# ================= SIDEBAR - MOBILE CAMERA CONTROLS =================
render_mobile_camera_sidebar(st.session_state)

# ================= SIDEBAR - ALERT STATUS =================
st.sidebar.markdown("---")
st.sidebar.subheader("🚨 Alert Status")
alert_manager = st.session_state.alert_manager
stats = alert_manager.get_stats()

if stats['active_alerts'] > 0:
    st.sidebar.error(
        f"🚨 {stats['active_alerts']} Active Alert(s)"
    )
else:
    st.sidebar.success("✅ No Active Alerts")

st.sidebar.metric("Total Alerts",    stats['total_alerts'])
st.sidebar.metric("High Risk",       stats['high_risk_count'])
st.sidebar.metric("Surge Detected",  stats['surge_count'])
st.sidebar.metric("Zone Alerts",     stats['zone_alert_count'])

# ================= TAB6: ENHANCED ALERTS DASHBOARD =================
with tab6:
    # Import the enhanced alert tab component
    from components.alert_tab import render_enhanced_alert_tab
    
    # Render the enhanced alert tab with live monitoring, email toggle, and Cloudinary integration
    render_enhanced_alert_tab()