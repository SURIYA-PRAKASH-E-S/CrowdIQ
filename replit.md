# Intelligent Crowd Surveillance System (ICSS)

## Overview
An AI-powered real-time computer vision application for monitoring crowd density, movement tracking, and risk assessment. Uses multiple deep learning models including YOLO v11/v8 for person detection and CSRNet for dense crowd analysis.

## Tech Stack
- **Language**: Python 3.11
- **Frontend/UI**: Streamlit (v1.56.0) running on port 5000
- **Computer Vision**: YOLO v11/v8 via ultralytics, OpenCV
- **Tracking**: Deep SORT (deep-sort-realtime)
- **Density Estimation**: CSRNet
- **Video Streaming**: streamlit-webrtc with PyAV
- **Database**: Supabase (PostgreSQL via REST API)
- **Visualization**: Plotly, Matplotlib, Seaborn

## Project Structure
- `app.py` — Main Streamlit application (6-tab dashboard)
- `camera1.py` — Mobile/IP webcam streaming integration
- `utils/` — Core logic modules:
  - `detection.py` — YOLO detection pipeline
  - `tracker.py` — Deep SORT integration
  - `risk_engine.py` — Risk scoring (Normal/Average/Risky)
  - `csrnet_density.py` — Dense crowd density estimation
  - `alert_manager.py` — Real-time alert notifications
  - `zone_analyzer.py` / `flow_analyzer.py` — Spatial/movement analysis
  - `crowd_analytics.py` / `advanced_analytics.py` — Analytics
  - `crowd_visualization.py` — Visualization helpers
- `model/` — Pre-trained YOLO weight files (.pt)
- `utils/database.py` — All Supabase calls (single source of truth for DB access)
- `supabase_schema.sql` — Run once in Supabase SQL Editor to create the table

## Running the App
```
streamlit run app.py --server.port 5000 --server.address 0.0.0.0 --server.headless true --server.enableCORS false --server.enableXsrfProtection false
```

## Configuration
- Streamlit config: `.streamlit/config.toml` (port 5000, all hosts allowed)
- System deps: pkg-config, ffmpeg, xorg.libxcb, xorg.libX11, xorg.libXext, xorg.libXrender

## Features
- Live Feed: Webcam/mobile camera/video file input with real-time detection
- Analytics: Historical charts and performance metrics
- Map Area: Zone-based spatial analysis
- Local DB: DuckDB query interface
- Controls: Settings and model configuration
- Alerts: Real-time notifications for critical density levels
