"""
alert_tab.py - Enhanced ICSS Alert Tab with Supabase + Resend + Cloudinary integration
Replaces the existing alert tab render function with enhanced features
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, List
import numpy as np

# Import new utilities
from utils.alert_store import get_alert_store, get_active_alerts, get_alert_statistics
from utils.cloudinary_helper import is_cloudinary_available, upload_snapshot
from utils.database import is_connected as db_is_connected
from utils.email_config import setup_email_from_ui, get_email_manager

def render_severity_badge(severity: str) -> str:
    """Return Streamlit color function and icon for severity"""
    severity_colors = {
        "CRITICAL": ("error", "danger", "red"),
        "HIGH": ("warning", "warning", "orange"),
        "MEDIUM": ("info", "info", "blue"),
        "LOW": ("success", "check-circle", "green")
    }
    
    return severity_colors.get(severity, ("info", "info", "blue"))

def format_alert_timestamp(timestamp_str: str) -> str:
    """Format timestamp for display"""
    try:
        if timestamp_str:
            dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            return dt.strftime("%H:%M:%S")
        return ""
    except:
        return timestamp_str

def render_live_alert_log():
    """Render live alert log with real-time updates"""
    st.markdown("### 🔴 Live Alert Log")
    st.markdown("---")
    
    # Get active alerts
    alert_store = get_alert_store()
    active_alerts = alert_store.get_active_alerts(minutes=5)
    
    if active_alerts:
        st.success(f"📊 Showing {len(active_alerts)} active alerts (last 5 minutes)")
        
        # Create DataFrame for display
        df_data = []
        for alert in active_alerts:
            df_data.append({
                "Type": alert.get('type', 'Unknown'),
                "Severity": alert.get('severity', 'UNKNOWN'),
                "Zone": alert.get('zone', 'N/A'),
                "Count": alert.get('count', 0),
                "Density": f"{alert.get('density', 0):.3f}",
                "Timestamp": format_alert_timestamp(alert.get('timestamp', '')),
                "Message": alert.get('message', '')[:50] + "..." if len(alert.get('message', '')) > 50 else alert.get('message', ''),
                "Image": "📸" if alert.get('image_url') else ""
            })
        
        df = pd.DataFrame(df_data)
        
        # Apply color coding to severity
        def color_severity(val):
            color_map = {
                "CRITICAL": "background-color: #ffcccc",
                "HIGH": "background-color: #fff3cd",
                "MEDIUM": "background-color: #d1ecf1",
                "LOW": "background-color: #d4edda"
            }
            return color_map.get(val, "")
        
        styled_df = df.style.applymap(color_severity, subset=['Severity'])
        st.dataframe(styled_df, use_container_width=True, hide_index=True)
        
        # Show images if available
        images_available = any(alert.get('image_url') for alert in active_alerts)
        if images_available:
            st.markdown("### 📸 Alert Snapshots")
            for alert in active_alerts:
                if alert.get('image_url'):
                    with st.expander(f"📸 {alert.get('type', 'Alert')} - {format_alert_timestamp(alert.get('timestamp', ''))}"):
                        st.image(alert['image_url'], caption=alert.get('message', 'Alert snapshot'), use_column_width=True)
    else:
        st.info("✅ No active alerts in the last 5 minutes")

def render_manual_alert_controls():
    """Render manual alert level and density controls"""
    st.markdown("### Manual Alert Controls")
    st.markdown("---")
    
    # Initialize session state for manual controls
    if 'manual_alert_level' not in st.session_state:
        st.session_state.manual_alert_level = "MEDIUM"
    if 'manual_density_threshold' not in st.session_state:
        st.session_state.manual_density_threshold = 0.5
    if 'manual_people_threshold' not in st.session_state:
        st.session_state.manual_people_threshold = 10
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Alert Level Control
        st.markdown("#### Alert Level")
        alert_level = st.selectbox(
            "Set Alert Level",
            options=["LOW", "MEDIUM", "HIGH", "CRITICAL"],
            index=1,  # Default to MEDIUM
            key="manual_alert_level_select_unique",
            help="Manually set the alert severity level"
        )
        
        # Update session state
        if alert_level != st.session_state.manual_alert_level:
            st.session_state.manual_alert_level = alert_level
            st.success(f"Alert level set to: {alert_level}")
    
    with col2:
        # Density Threshold Control
        st.markdown("#### Density Threshold")
        density_threshold = st.slider(
            "Density Threshold (p/m²)",
            min_value=0.1,
            max_value=2.0,
            value=st.session_state.manual_density_threshold,
            step=0.1,
            key="manual_density_slider_unique",
            help="Set manual density threshold for alerts"
        )
        
        # Update session state
        if density_threshold != st.session_state.manual_density_threshold:
            st.session_state.manual_density_threshold = density_threshold
            st.success(f"Density threshold set to: {density_threshold} p/m²")
    
    # People Count Threshold
    st.markdown("#### People Count Threshold")
    people_threshold = st.slider(
        "People Count Threshold",
        min_value=1,
        max_value=50,
        value=st.session_state.manual_people_threshold,
        step=1,
        key="manual_people_slider_unique",
        help="Set manual people count threshold for alerts"
    )
    
    # Update session state
    if people_threshold != st.session_state.manual_people_threshold:
        st.session_state.manual_people_threshold = people_threshold
        st.success(f"People threshold set to: {people_threshold}")
    
    # Apply Settings Button
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Apply Manual Settings", type="primary", key="apply_manual_settings_unique"):
            # Store settings in session state for use in alert processing
            st.session_state.apply_manual_settings = True
            st.success("Manual alert settings applied!")
            st.rerun()
    
    with col2:
        if st.button("Reset to Default", key="reset_manual_settings_unique"):
            # Reset to default values
            st.session_state.manual_alert_level = "MEDIUM"
            st.session_state.manual_density_threshold = 0.5
            st.session_state.manual_people_threshold = 10
            st.session_state.apply_manual_settings = False
            st.success("Settings reset to default!")
            st.rerun()
    
    # Current Settings Display
    st.markdown("#### Current Manual Settings")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Alert Level", st.session_state.manual_alert_level)
    with col2:
        st.metric("Density", f"{st.session_state.manual_density_threshold} p/m²")
    with col3:
        st.metric("People", st.session_state.manual_people_threshold)
    
    # Status Indicator
    if st.session_state.get('apply_manual_settings', False):
        st.success("Manual settings are currently active")
    else:
        st.info("Using automatic alert detection")

def render_email_configuration():
    """Render comprehensive email configuration for multiple administrators"""
    st.markdown("### Email Configuration")
    st.markdown("---")
    
    # Email setup UI
    config_updated = setup_email_from_ui()
    
    if config_updated:
        st.rerun()
    
    # SMS coming soon section
    st.markdown("### SMS Alerts")
    st.markdown("---")
    st.info("**SMS alerts feature coming soon!** Currently available: Email notifications for multiple administrators.")
    
    with st.expander("SMS Configuration", expanded=False):
        st.warning("SMS alerts are under development and will be available soon!")
        st.write("Planned features:")
        st.write("- SMS notifications for CRITICAL alerts")
        st.write("- Multiple phone number support") 
        st.write("- Carrier gateway integration")
        st.write("- International number support")

def render_email_toggle():
    """Render simple email toggle (legacy compatibility)"""
    st.markdown("### 📩 Quick Email Toggle")
    st.markdown("---")
    
    alert_store = get_alert_store()
    email_manager = get_email_manager()
    
    # Get current settings
    db_setting = alert_store.get_email_setting()
    local_enabled = email_manager.enabled
    
    col1, col2 = st.columns(2)
    with col1:
        # Database toggle
        db_enabled = st.toggle(
            "Database Email Setting",
            value=db_setting,
            key="db_email_toggle",
            help="Email setting stored in Supabase database"
        )
        
        if db_enabled != db_setting:
            if alert_store.update_email_setting(db_enabled):
                st.success("✅ Database email setting updated")
            else:
                st.error("❌ Failed to update database setting")
    
    with col2:
        # Local toggle
        local_enabled = st.toggle(
            "Local Email Setting",
            value=local_enabled,
            key="local_email_toggle", 
            help="Local email configuration for direct SMTP sending"
        )
        
        if local_enabled != email_manager.enabled:
            email_manager.enable_email(local_enabled)
            st.success("✅ Local email setting updated")
    
    # Status display
    st.markdown("#### 📊 Email Status")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Database", "🟢 ON" if db_setting else "🔴 OFF")
    with col2:
        st.metric("Local SMTP", "🟢 ON" if local_enabled else "🔴 OFF")
    with col3:
        overall_status = "🟢 ACTIVE" if (db_setting or local_enabled) else "🔴 INACTIVE"
        st.metric("Overall", overall_status)
    
    # Configuration info
    email_status = email_manager.get_config_status()
    if email_status['configured']:
        st.info(f"📧 **Configured**: {email_status['recipient_count']} recipients, SMTP: {email_status['smtp_host']}")
    else:
        st.warning("⚠️ **Not Configured**: Set up SMTP credentials and recipients below")
    
    st.markdown("---")
    st.info("🔧 **For full email setup**, use the Email Configuration section above to set up SMTP and multiple recipients.")

def render_alert_statistics():
    """Render alert statistics dashboard"""
    st.markdown("### Alert Statistics")
    st.markdown("---")
    
    stats = get_alert_statistics()
    
    # Check if manual settings are active
    manual_active = st.session_state.get('apply_manual_settings', False)
    
    # Metrics row
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Total Alerts", stats['total_alerts'])
    with col2:
        st.metric("Active (5m)", stats['active_alerts'])
    with col3:
        st.metric("Critical", stats['critical_count'])
    with col4:
        st.metric("High", stats['high_count'])
    with col5:
        st.metric("Medium", stats['medium_count'])
    
    # Manual settings status
    st.markdown("#### Manual Settings Status")
    col1, col2, col3 = st.columns(3)
    with col1:
        status = "Active" if manual_active else "Inactive"
        status_color = "Active" if manual_active else "Inactive"
        st.metric("Manual Mode", status_color)
    
    with col2:
        if manual_active:
            st.metric("Alert Level", st.session_state.get('manual_alert_level', 'MEDIUM'))
        else:
            st.metric("Alert Level", "Auto")
    
    with col3:
        if manual_active:
            st.metric("Density", f"{st.session_state.get('manual_density_threshold', 0.5)} p/m²")
        else:
            st.metric("Density", "Auto")
    
    # Manual settings info
    if manual_active:
        st.info(f"Manual settings active: Level={st.session_state.get('manual_alert_level', 'MEDIUM')}, Density={st.session_state.get('manual_density_threshold', 0.5)} p/m², People={st.session_state.get('manual_people_threshold', 10)}")
    else:
        st.info("Using automatic alert detection thresholds")
    
    # Connection status
    st.markdown("### 🔌 Service Status")
    st.markdown("---")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        supabase_status = "🟢 Connected" if db_is_connected() else "🔴 Disconnected"
        st.metric("Supabase", supabase_status)
    
    with col2:
        cloudinary_status = "🟢 Available" if is_cloudinary_available() else "🔴 Not Configured"
        st.metric("Cloudinary", cloudinary_status)
    
    with col3:
        email_status = "🟢 Enabled" if get_alert_store().get_email_setting() else "🔴 Disabled"
        st.metric("Email Service", email_status)

def render_historical_alerts():
    """Render historical alerts table"""
    st.markdown("### 📜 Historical Alerts (Last 50)")
    st.markdown("---")
    
    alert_store = get_alert_store()
    df = alert_store.get_recent_alerts(limit=50)
    
    if not df.empty:
        # Format for display
        display_df = df.copy()
        if 'timestamp' in display_df.columns:
            display_df['timestamp'] = display_df['timestamp'].apply(format_alert_timestamp)
        
        if 'density' in display_df.columns:
            display_df['density'] = display_df['density'].apply(lambda x: f"{float(x):.3f}" if pd.notna(x) else "0.000")
        
        # Truncate long messages
        if 'message' in display_df.columns:
            display_df['message'] = display_df['message'].apply(
                lambda x: x[:50] + "..." if len(str(x)) > 50 else str(x)
            )
        
        st.dataframe(display_df, use_container_width=True, hide_index=True)
    else:
        st.info("No historical alerts found")

def render_enhanced_alert_tab():
    """Main render function for enhanced alert tab"""
    st.subheader("🚨 Enhanced Real-Time Alert System")
    
    # Check database connection
    if not db_is_connected():
        st.error(
            "❌ Supabase is not connected.\n\n"
            "Add SUPABASE_URL and SUPABASE_ANON_KEY to your environment, "
            "then restart the app for full alert functionality."
        )
        st.info("Basic alert functionality will work, but data persistence is disabled.")
    
    # Auto-refresh controls at the top
    refresh_col1, refresh_col2 = st.columns([1, 3])
    with refresh_col1:
        if st.button("Refresh", key="refresh_main_unique", help="Refresh alert data"):
            st.rerun()
    
    with refresh_col2:
        auto_refresh = st.checkbox(
            "Auto-refresh every 3 seconds",
            value=st.session_state.get("alert_auto_refresh", False),
            key="alert_auto_refresh_unique",
            help="Automatically refresh alerts every 3 seconds"
        )
    
    # Main content in a container to prevent duplication
    with st.container(key="alert_main_container_unique"):
        col_left, col_right = st.columns([1, 2])
        
        with col_left:
            # Manual alert controls
            render_manual_alert_controls()
            
            st.markdown("---")
            
            # Email configuration
            render_email_configuration()
            
            st.markdown("---")
            
            # Quick email toggle
            render_email_toggle()
            
            st.markdown("---")
            
            # Quick stats
            render_alert_statistics()
        
        with col_right:
            # Live alerts
            render_live_alert_log()
            
            st.markdown("---")
            
            # Historical alerts
            render_historical_alerts()
    
    # Auto-refresh functionality (only if enabled and not already refreshing)
    if auto_refresh and not st.session_state.get('is_refreshing', False):
        st.session_state['is_refreshing'] = True
        import time
        time.sleep(3)
        st.session_state['is_refreshing'] = False
        st.rerun()
    elif not auto_refresh:
        st.session_state['is_refreshing'] = False

# Compatibility function for existing code
def render_alert_tab():
    """Compatibility wrapper"""
    render_enhanced_alert_tab()
