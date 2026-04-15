# Intelligent Crowd Surveillance System (ICSS) - Project Update

## Overview
An AI-powered real-time computer vision application for monitoring crowd density, movement tracking, and risk assessment. Uses multiple deep learning models including YOLO v11/v8 for person detection and CSRNet for dense crowd analysis.

## Tech Stack
- **Language**: Python 3.11
- **Frontend/UI**: Streamlit (v1.56.0) running on port 8501
- **Computer Vision**: YOLO v11/v8 via ultralytics, OpenCV
- **Tracking**: Deep SORT (deep-sort-realtime)
- **Density Estimation**: CSRNet
- **Video Streaming**: streamlit-webrtc with PyAV
- **Database**: Supabase (PostgreSQL via REST API)
- **Visualization**: Plotly, Matplotlib, Seaborn

## Project Structure
```
TestIcss/
app.py                          # Main Streamlit application (6-tab dashboard)
camera1.py                      # Mobile/IP webcam streaming integration
utils/
  detection.py                  # YOLO detection pipeline
  tracker.py                    # Deep SORT integration
  risk_engine.py                # Risk scoring (Normal/Average/Risky)
  csrnet_density.py             # Dense crowd density estimation
  alert_manager.py              # Real-time alert notifications
  zone_analyzer.py              # Spatial/movement analysis
  flow_analyzer.py              # Movement flow analysis
  crowd_analytics.py            # Analytics and zone grid functions
  advanced_analytics.py         # Advanced analytics
  crowd_visualization.py        # Visualization helpers
  database.py                   # Supabase integration
.env                            # Environment variables
requirements.txt                # Python dependencies
```

## Recent Updates & Fixes

### Version 2.1.0 - April 14, 2026

#### Critical Fixes Applied:

**FIX 1 - Streamlit Deprecation Update**
- **File**: `app.py` line 1070
- **Issue**: `use_column_width` parameter deprecated in newer Streamlit versions
- **Solution**: Replaced `use_column_width=True` with `use_container_width=True`
- **Impact**: Mobile camera feed now displays correctly without width parameter errors

**FIX 2 - Mobile Camera Alert System Enhancement**
- **Files**: `app.py` line 1082, `utils/alert_manager.py` lines 321-351
- **Changes**:
  - **8-People Cap**: Added hard limit of 8 people for mobile camera feeds
    ```python
    result['people_count'] = min(result['people_count'], 8)
    ```
  - **Medium-Risk Only**: Modified alert system to show ONLY medium-risk alerts for mobile camera
  - **New Parameter**: Added `mobile_camera` boolean to `process_all()` method
- **Impact**: Mobile camera now provides simplified, focused alerting with capped detection

**FIX 3 - Zone Grid Feature Removal**
- **Files**: `app.py` multiple locations (504-536, 555-556, 1087-1093, 874-879, 1781-1796)
- **Changes**:
  - Removed zone grid rendering from VideoProcessor `recv()` method
  - Removed zone grid rendering from mobile camera processing
  - Removed zone grid status display from Live Feed tab
  - Removed zone grid checkbox from Controls tab
  - Preserved zone computation for other features
- **Impact**: Simplified UI and removed zone grid overlay functionality

#### Previous Zone Grid Debugging Session:
- **Issue**: Zone grid not displaying despite toggle enabled
- **Root Causes Identified**:
  - Session manager sync issues between UI and video processing threads
  - Undefined `row` and `col` variables in `draw_zone_grid` function
  - Frame processing dependencies
- **Solutions Implemented**:
  - Added comprehensive debugging across UI and console
  - Fixed undefined variables with proper zone ID parsing
  - Added fallback grid drawing mechanisms
  - Enhanced state synchronization between threads

## Core Features

### 1. Multi-Tab Dashboard
- **Live Feed**: Real-time video processing with analytics overlay
- **Analytics**: Crowd density, movement patterns, risk metrics
- **Map Area**: Zone-based spatial analysis
- **Local DB**: Data storage and retrieval
- **Controls**: System configuration and feature toggles
- **Alerts**: Real-time alert management

### 2. Video Input Sources
- **Webcam (Live)**: Direct camera integration
- **Mobile Camera (IP Webcam)**: Remote camera streaming
- **Upload Video**: Video file processing

### 3. Detection & Tracking
- **YOLO v11/v8**: Person detection with multiple model support
- **Deep SORT**: Object tracking across frames
- **CSRNet**: Dense crowd density estimation

### 4. Risk Assessment
- **Risk Levels**: Normal, Average, Risky
- **Density Analysis**: People per square meter
- **Movement Tracking**: Flow patterns and speed variations

### 5. Alert System
- **Real-time Alerts**: Visual and sound notifications
- **Alert Types**: Zone overcrowding, high risk, crowd surge
- **Severity Levels**: LOW, MEDIUM, HIGH, CRITICAL
- **Mobile Camera Specific**: Medium-risk only, 8-people cap

### 6. Database Integration
- **Supabase**: PostgreSQL backend
- **Real-time Sync**: Live data updates
- **Historical Data**: Storage and retrieval of analytics

## Configuration

### Session State Management
```python
# Core settings
st.session_state.input_mode = "Webcam (Live)"
st.session_state.active_models = ["YOLOv11"]
st.session_state.risk_weights = {'density': 0.4, 'flow_conflict': 0.35, 'speed_variation': 0.25}

# Feature toggles
st.session_state.enable_density_heatmap = True
st.session_state.show_crowd_heatmap = True

# Alert settings
st.session_state.enable_sound_alerts = True
st.session_state.enable_email_alerts = False
```

### Model Configuration
- **Primary Model**: YOLO v11 (ultralytics)
- **Fallback Model**: YOLO v8
- **Mobile Model**: YOLO v11m (optimized for mobile)
- **Tracker**: Deep SORT with ReID features

### Performance Optimizations
- **Frame Skipping**: Process every N frames for better performance
- **Resolution Scaling**: Resize frames for faster inference
- **Thread-Safe State**: Session manager for inter-thread communication
- **Memory Management**: Circular buffer for frame storage

## Installation & Setup

### Prerequisites
```bash
# Python 3.11+
pip install -r requirements.txt

# Environment variables
cp .env.example .env
# Edit .env with your configurations
```

### Running the Application
```bash
# Activate virtual environment
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# Run Streamlit app
streamlit run app.py --server.port 8501
```

### Mobile Camera Setup
1. Install IP Webcam app on mobile device
2. Configure camera URL in app sidebar
3. Select "Mobile Camera (IP Webcam)" input mode
4. Start streaming

## API Integration

### Supabase Database
```python
# Connection handled in utils/database.py
# Tables: crowd_data, alerts, analytics, settings
# Real-time subscriptions enabled
```

### Alert Notifications
- **Email**: SMTP configuration in settings
- **SMS**: Gateway support for multiple carriers
- **Sound**: Local audio alerts

## Troubleshooting

### Common Issues

1. **Zone Grid Not Displaying** (RESOLVED - Feature Removed)
   - Zone grid feature has been completely removed from the application

2. **Mobile Camera Width Error** (RESOLVED)
   - Fixed Streamlit deprecation: `use_container_width=True`

3. **Alert System Issues**
   - Mobile camera now shows only medium-risk alerts
   - People count capped at 8 for mobile feeds

4. **Performance Issues**
   - Adjust frame processing rate in Controls tab
   - Reduce input resolution if needed
   - Enable/disable features based on system resources

### Debug Mode
- Console logging enabled for troubleshooting
- Debug information available in Live Feed tab
- Session state tracking for feature toggles

## Future Enhancements

### Planned Features
- [ ] Advanced zone analytics
- [ ] Multi-camera support
- [ ] Cloud deployment options
- [ ] Enhanced reporting dashboard
- [ ] Machine learning model optimization

### Performance Improvements
- [ ] GPU acceleration support
- [ ] Edge computing capabilities
- [ ] Optimized model quantization
- [ ] Real-time streaming improvements

## Dependencies

### Core Libraries
```
streamlit>=1.56.0
opencv-python>=4.8.0
ultralytics>=8.0.0
deep-sort-realtime>=1.3.0
numpy>=1.24.0
pandas>=2.0.0
plotly>=5.15.0
matplotlib>=3.7.0
seaborn>=0.12.0
```

### Computer Vision
```
torch>=2.0.0
torchvision>=0.15.0
av>=10.0.0
streamlit-webrtc>=0.43.0
```

### Database & Networking
```
supabase>=1.0.0
requests>=2.31.0
aiohttp>=3.8.0
```

## License & Credits

### License
MIT License - See LICENSE file for details

### Credits
- YOLO Models: Ultralytics
- Deep SORT: nwojke/deep-sort-python
- Streamlit Framework: Streamlit Inc.
- CSRNet: Adapted for crowd density estimation

## Support & Contact

### Documentation
- Inline help text available in application
- Tooltips and guidance in Controls tab
- Console logging for debugging

### Issues & Feature Requests
- Report issues through project repository
- Feature requests welcome in project discussions

---

**Last Updated**: April 14, 2026  
**Version**: 2.1.0  
**Status**: Production Ready with Recent Critical Fixes
