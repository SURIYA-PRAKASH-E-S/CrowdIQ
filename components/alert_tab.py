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

def render_email_configuration():
    """Render comprehensive email configuration for multiple administrators"""
   
    
    # Email setup UI
    config_updated = setup_email_from_ui()
    
    if config_updated:
        st.rerun()

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
    st.markdown("### 📊 Alert Statistics")
    st.markdown("---")
    
    stats = get_alert_statistics()
    
    # Metrics row
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Total Alerts", stats['total_alerts'])
    with col2:
        st.metric("Active (5m)", stats['active_alerts'])
    with col3:
        st.metric("🔴 Critical", stats['critical_count'])
    with col4:
        st.metric("🟠 High", stats['high_count'])
    with col5:
        st.metric("🔵 Medium", stats['medium_count'])
    
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
        if st.button("🔄 Refresh", key="refresh_main", help="Refresh alert data"):
            st.rerun()
    
    with refresh_col2:
        auto_refresh = st.checkbox(
            "🔄 Auto-refresh every 3 seconds",
            value=st.session_state.get("alert_auto_refresh", False),
            key="alert_auto_refresh_main",
            help="Automatically refresh alerts every 3 seconds"
        )
    
    # Main content in a container to prevent duplication
    with st.container(key="alert_main_container"):
        col_left, col_right = st.columns([1, 2])
        
        with col_left:
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
    
    # Auto-refresh functionality (only if enabled)
    if auto_refresh:
        import time
        time.sleep(3)
        st.rerun()

# Compatibility function for existing code
def render_alert_tab():
    """Compatibility wrapper"""
    render_enhanced_alert_tab()
