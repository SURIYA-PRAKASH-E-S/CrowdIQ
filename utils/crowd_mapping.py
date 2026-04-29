"""
crowd_mapping.py - Real-time crowd zone mapping system using OpenStreetMap.

This module provides functions for:
- Loading interactive maps with Folium
- Drawing zone polygons with color-coded risk levels
- Fetching real-time data from Firebase
- Dynamic map updates for crowd analytics
"""

import folium
import streamlit as st
from streamlit_folium import st_folium
from typing import Dict, List, Tuple, Optional, Any
import json
import random
import time


# Risk level color mapping
RISK_COLORS = {
    "LOW": "#28a745",      # Green
    "MEDIUM": "#ffc107",   # Yellow
    "HIGH": "#dc3545"      # Red
}

# Default center location (can be customized)
DEFAULT_CENTER = [28.6139, 77.2090]  # New Delhi, India
DEFAULT_ZOOM = 14


def load_map(
    center: Tuple[float, float] = None,
    zoom: int = DEFAULT_ZOOM,
    tile_provider: str = "OpenStreetMap"
) -> folium.Map:
    """
    Create and return a Folium map with OpenStreetMap tiles.
    
    Args:
        center: Tuple of (latitude, longitude) for map center
        zoom: Initial zoom level
        tile_provider: Map tile provider name
        
    Returns:
        folium.Map: Initialized map object
    """
    if center is None:
        center = DEFAULT_CENTER
        
    m = folium.Map(
        location=center,
        zoom_start=zoom,
        tiles=tile_provider
    )
    
    return m


def get_risk_color(risk_level: str) -> str:
    """
    Get the color code for a given risk level.
    
    Args:
        risk_level: Risk level string (LOW, MEDIUM, HIGH)
        
    Returns:
        str: Hex color code
    """
    return RISK_COLORS.get(risk_level.upper(), "#808080")


def calculate_risk_level(density: float) -> str:
    """
    Calculate risk level based on crowd density.
    
    Args:
        density: Density value between 0 and 1
        
    Returns:
        str: Risk level (LOW, MEDIUM, HIGH)
    """
    if density < 0.3:
        return "LOW"
    elif density < 0.7:
        return "MEDIUM"
    else:
        return "HIGH"


def draw_zones(m: folium.Map, zones) -> folium.Map:
    """
    Draw zone polygons on the map with color-coded risk levels.
    
    Args:
        m: Folium map object
        zones: Dictionary of zone data with structure:
               {
                   "zone_id": {
                       "coordinates": [[lat, lon], ...],
                       "crowd_count": int,
                       "density": float,
                       "risk_level": str
                   }
               }
               
    Returns:
        folium.Map: Map with drawn zones
    """
    if not zones:
        return m
    
    try:
        if not isinstance(zones, dict):
            return m
        
        for zone_id, zone_data in zones.items():
            if not isinstance(zone_data, dict):
                continue
                
            coordinates = zone_data.get("coordinates", [])
            crowd_count = zone_data.get("crowd_count", 0)
            density = zone_data.get("density", 0.0)
            risk_level = zone_data.get("risk_level", calculate_risk_level(density))
            
            area_sq_m = zone_data.get("area_sq_m", 0)
            area_sq_ft = zone_data.get("area_sq_ft", 0)
            safe_capacity = zone_data.get("safe_capacity", 0)
            occupancy_ratio = zone_data.get("occupancy_ratio", 0)
            
            color = get_risk_color(risk_level)
            
            popup_html = f"""
            <div style="font-family: Arial, sans-serif; min-width: 220px;">
                <h4 style="margin: 0 0 10px 0; color: {color};">{zone_id}</h4>
                <table style="width: 100%; font-size: 12px;">
                    <tr><td><strong>Area:</strong></td><td>{area_sq_m:.1f} sq.m ({area_sq_ft:.1f} sq.ft)</td></tr>
                    <tr><td><strong>Safe Capacity:</strong></td><td>{safe_capacity} people</td></tr>
                    <tr><td><strong>Current Count:</strong></td><td>{crowd_count}</td></tr>
                    <tr><td><strong>Occupancy:</strong></td><td>{occupancy_ratio*100:.0f}%</td></tr>
                    <tr><td><strong>Density:</strong></td><td>{density:.2f}</td></tr>
                    <tr><td><strong>Risk Level:</strong></td><td style="color: {color}; font-weight: bold;">{risk_level}</td></tr>
                </table>
            </div>
            """
            
            if coordinates and len(coordinates) >= 3:
                folium.Polygon(
                    locations=coordinates,
                    popup=folium.Popup(popup_html, max_width=300),
                    color=color,
                    fill=True,
                    fill_color=color,
                    fill_opacity=0.4,
                    weight=2
                ).add_to(m)
            
            # Add zone label at centroid
            if len(coordinates) > 0:
                centroid_lat = sum(c[0] for c in coordinates) / len(coordinates)
                centroid_lon = sum(c[1] for c in coordinates) / len(coordinates)
                
                folium.Marker(
                    location=[centroid_lat, centroid_lon],
                    icon=folium.DivIcon(
                        html=f'<div style="font-size: 10px; font-weight: bold; color: white; '
                             f'background-color: {color}; padding: 2px 6px; border-radius: 3px;">'
                             f'{zone_id}</div>'
                    )
                ).add_to(m)
    except Exception:
        pass
    
    return m


def create_sample_zones(
    center: Tuple[float, float] = None,
    num_zones: int = 6
) -> Dict[str, Dict[str, Any]]:
    """
    Create sample zone data for demonstration purposes.
    
    Args:
        center: Center coordinates (lat, lon)
        num_zones: Number of zones to generate
        
    Returns:
        Dict: Sample zone data
    """
    if center is None:
        center = DEFAULT_CENTER
        
    lat, lon = center
    zones = {}
    
    # Define zone offsets to create a grid pattern
    offsets = [
        (-0.003, -0.004),
        (-0.003, 0.004),
        (0.003, -0.004),
        (0.003, 0.004),
        (0.006, 0),
        (-0.006, 0)
    ]
    
    for i in range(min(num_zones, len(offsets))):
        offset_lat, offset_lon = offsets[i]
        
        # Create polygon coordinates for each zone
        zone_lat = lat + offset_lat
        zone_lon = lon + offset_lon
        
        coordinates = [
            [zone_lat - 0.002, zone_lon - 0.002],
            [zone_lat - 0.002, zone_lon + 0.002],
            [zone_lat + 0.002, zone_lon + 0.002],
            [zone_lat + 0.002, zone_lon - 0.002]
        ]
        
        # Generate random crowd data
        crowd_count = random.randint(20, 200)
        density = random.uniform(0.1, 1.0)
        risk_level = calculate_risk_level(density)
        
        zone_id = f"Zone_{chr(65 + i)}"  # Zone_A, Zone_B, etc.
        
        zones[zone_id] = {
            "coordinates": coordinates,
            "crowd_count": crowd_count,
            "density": round(density, 2),
            "risk_level": risk_level
        }
    
    return zones


def generate_dummy_data(zones) -> Dict[str, Dict[str, Any]]:
    """
    Generate random updates for zone data (for demo when Firebase unavailable).
    
    Args:
        zones: Current zone data
        
    Returns:
        Dict: Updated zone data with random changes
    """
    if not isinstance(zones, dict):
        return {}
    
    updated_zones = {}
    
    for zone_id, zone_data in zones.items():
        # Randomly adjust crowd count
        change = random.randint(-20, 30)
        new_count = max(10, zone_data.get("crowd_count", 50) + change)
        
        # Calculate new density
        max_capacity = 200
        new_density = min(1.0, new_count / max_capacity)
        
        # Determine risk level
        new_risk = calculate_risk_level(new_density)
        
        updated_zones[zone_id] = {
            "coordinates": zone_data.get("coordinates", []),
            "crowd_count": new_count,
            "density": round(new_density, 2),
            "risk_level": new_risk
        }
    
    return updated_zones


def render_map_component(
    m: folium.Map,
    height: int = 600,
    width: str = "100%"
) -> None:
    """
    Render a Folium map in Streamlit.
    
    Args:
        m: Folium map object
        height: Map height in pixels
        width: Map width (CSS value)
    """
    st_folium(m, height=height, width=width)


def add_heatmap_layer(m: folium.Map, zones) -> folium.Map:
    """
    Add a heatmap layer showing crowd density.
    
    Args:
        m: Folium map object
        zones: Zone data with density information
        
    Returns:
        folium.Map: Map with heatmap layer
    """
    heat_data = []
    
    if not isinstance(zones, dict):
        return m
    
    for zone_id, zone_data in zones.items():
        coordinates = zone_data.get("coordinates", [])
        density = zone_data.get("density", 0)
        
        if coordinates:
            # Use centroid for heat point
            centroid_lat = sum(c[0] for c in coordinates) / len(coordinates)
            centroid_lon = sum(c[1] for c in coordinates) / len(coordinates)
            heat_data.append([centroid_lat, centroid_lon, density])
    
    if heat_data:
        from folium.plugins import HeatMap
        HeatMap(heat_data, radius=25, blur=15).add_to(m)
    
    return m


def check_alerts(zones, threshold: float = 0.8) -> List[Dict[str, Any]]:
    """
    Check for zones exceeding density threshold and generate alerts.
    
    Args:
        zones: Zone data dictionary or other iterable
        threshold: Density threshold for alerts (default 0.8)
        
    Returns:
        List: List of alert dictionaries
    """
    alerts = []
    
    if not isinstance(zones, dict):
        return alerts
    
    for zone_id, zone_data in zones.items():
        if not isinstance(zone_data, dict):
            continue
        density = zone_data.get("density", 0)
        
        if density >= threshold:
            alerts.append({
                "zone_id": zone_id,
                "density": density,
                "crowd_count": zone_data.get("crowd_count", 0),
                "risk_level": zone_data.get("risk_level", "HIGH"),
                "timestamp": time.time()
            })
    
    return alerts


def get_zone_statistics(zones) -> Dict[str, Any]:
    """
    Calculate overall statistics from zone data.
    
    Args:
        zones: Zone data dictionary or other iterable
        
    Returns:
        Dict: Statistics including total crowd, avg density, risk distribution
    """
    if not zones:
        return {
            "total_zones": 0,
            "total_crowd": 0,
            "avg_density": 0.0,
            "risk_distribution": {"LOW": 0, "MEDIUM": 0, "HIGH": 0}
        }
    
    try:
        if isinstance(zones, dict):
            zone_items = zones.values()
        else:
            zone_items = zones
        
        total_crowd = sum(z.get("crowd_count", 0) if isinstance(z, dict) else 0 for z in zone_items)
        avg_density = sum(z.get("density", 0) if isinstance(z, dict) else 0 for z in zone_items)
        
        zone_count = len(zones) if isinstance(zones, dict) else 1
        if zone_count > 0:
            avg_density = avg_density / zone_count
        
        risk_dist = {"LOW": 0, "MEDIUM": 0, "HIGH": 0}
        for z in zone_items:
            if isinstance(z, dict):
                risk = z.get("risk_level", "LOW")
                if risk in risk_dist:
                    risk_dist[risk] += 1
        
        return {
            "total_zones": zone_count,
            "total_crowd": total_crowd,
            "avg_density": round(avg_density, 2),
            "risk_distribution": risk_dist
        }
    except Exception as e:
        return {
            "total_zones": 0,
            "total_crowd": 0,
            "avg_density": 0.0,
            "risk_distribution": {"LOW": 0, "MEDIUM": 0, "HIGH": 0}
        }


def calculate_area(coordinates: List[List[float]]) -> Dict[str, float]:
    """
    Calculate area of a polygon from coordinates using the Shoelace formula.
    Handles lat/lon coordinates by converting to approximate meter-based projection.
    
    Args:
        coordinates: List of [lat, lon] coordinate pairs
        
    Returns:
        Dict with area_sq_m (square meters) and area_sq_ft (square feet)
    """
    if not coordinates or len(coordinates) < 3:
        return {"area_sq_m": 0.0, "area_sq_ft": 0.0}
    
    try:
        from math import radians, cos, sin, sqrt, atan2
        
        def haversine_distance(lat1, lon1, lat2, lon2):
            R = 6371000
            phi1, phi2 = radians(lat1), radians(lat2)
            dphi = radians(lat2 - lat1)
            dlambda = radians(lon2 - lon1)
            a = sin(dphi/2)**2 + cos(phi1)*cos(phi2)*sin(dlambda/2)**2
            return 2 * R * atan2(sqrt(a), sqrt(1-a))
        
        total_area = 0.0
        n = len(coordinates)
        
        for i in range(n):
            j = (i + 1) % n
            lat1, lon1 = coordinates[i]
            lat2, lon2 = coordinates[j]
            
            d1 = haversine_distance(28.6139, 77.2090, lat1, lon1)
            d2 = haversine_distance(28.6139, 77.2090, lat2, lon2)
            angle = radians((lon2 - lon1) * cos(radians((lat1 + lat2) / 2)))
            
            total_area += d1 * d2 * abs(angle) / 2
        
        area_sq_m = abs(total_area)
        area_sq_ft = area_sq_m * 10.764
        
        return {"area_sq_m": round(area_sq_m, 2), "area_sq_ft": round(area_sq_ft, 2)}
    except Exception:
        return {"area_sq_m": 0.0, "area_sq_ft": 0.0}


def calculate_capacity(area_sq_m: float, density_factor: float = 1.0) -> int:
    """
    Calculate safe crowd capacity based on area and density factor.
    
    Args:
        area_sq_m: Area in square meters
        density_factor: People per sq.m (default 1.0 = 1 person per sq.m)
        
    Returns:
        int: Safe capacity (maximum number of people)
    """
    if area_sq_m <= 0 or density_factor <= 0:
        return 0
    return int(area_sq_m * density_factor)


def update_zone_metrics(zone_data: Dict[str, Any], people_count: int, 
                        density_factor: float = 1.0) -> Dict[str, Any]:
    """
    Update zone metrics with ICSS live detection data.
    
    Args:
        zone_data: Existing zone data dict
        people_count: Current people count from ICSS
        density_factor: People per sq.m for capacity calculation
        
    Returns:
        Updated zone data with capacity, risk level, and occupancy info
    """
    if not isinstance(zone_data, dict):
        return zone_data
    
    coordinates = zone_data.get("coordinates", [])
    area_info = calculate_area(coordinates)
    area_sq_m = area_info.get("area_sq_m", 0)
    
    safe_capacity = calculate_capacity(area_sq_m, density_factor)
    current_count = people_count if people_count > 0 else zone_data.get("crowd_count", 0)
    
    if safe_capacity > 0:
        occupancy_ratio = current_count / safe_capacity
    else:
        occupancy_ratio = 0
    
    if current_count > safe_capacity:
        risk_level = "HIGH"
    elif occupancy_ratio >= 0.7:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"
    
    zone_data["area_sq_m"] = area_info["area_sq_m"]
    zone_data["area_sq_ft"] = area_info["area_sq_ft"]
    zone_data["safe_capacity"] = safe_capacity
    zone_data["current_count"] = current_count
    zone_data["occupancy_ratio"] = round(occupancy_ratio, 2)
    zone_data["crowd_count"] = current_count
    zone_data["density"] = min(1.0, occupancy_ratio)
    zone_data["risk_level"] = risk_level
    
    return zone_data


def add_live_location_marker(m: folium.Map, lat: float, lon: float, 
                             label: str = "Live Location") -> folium.Map:
    """
    Add a marker for live location on the map.
    
    Args:
        m: Folium map object
        lat: Latitude
        lon: Longitude
        label: Label for the marker
        
    Returns:
        folium.Map: Map with location marker
    """
    folium.Marker(
        location=[lat, lon],
        popup=label,
        icon=folium.Icon(color="blue", icon="crosshairs")
    ).add_to(m)
    return m
