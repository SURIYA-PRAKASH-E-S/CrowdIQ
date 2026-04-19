"""
alert_manager.py — Real-Time Alert System
Handles: Dashboard alerts, Sound alerts, SMS/Email notifications
"""

import time
import smtplib
import threading
import os
import logging
import requests
import tempfile
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from email.mime.application import MIMEApplication
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ── ALERT TYPES ─────────────────────────────────────────────────

class AlertType(Enum):
    ZONE_OVERCROWDED  = "Zone Overcrowded"
    HIGH_RISK         = "High Risk Level"
    CROWD_SURGE       = "Sudden Crowd Surge"


class AlertSeverity(Enum):
    LOW    = "LOW"
    MEDIUM = "MEDIUM"
    HIGH   = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass
class Alert:
    alert_type  : AlertType
    severity    : AlertSeverity
    message     : str
    zone_id     : Optional[str]   = None
    count       : int             = 0
    density     : float           = 0.0
    timestamp   : float           = field(default_factory=time.time)
    acknowledged: bool            = False
    image_url   : Optional[str]   = None  # Cloudinary URL for snapshot image

    def formatted_time(self) -> str:
        import datetime
        return datetime.datetime.fromtimestamp(
            self.timestamp
        ).strftime("%Y-%m-%d %H:%M:%S")

    def to_dict(self) -> dict:
        return {
            'type'     : self.alert_type.value,
            'severity' : self.severity.value,
            'message'  : self.message,
            'zone_id'  : self.zone_id,
            'count'    : self.count,
            'density'  : self.density,
            'time'     : self.formatted_time(),
        }


# ── SURGE DETECTOR ───────────────────────────────────────────────

class SurgeDetector:
    """
    Detects sudden rapid increase in crowd count.
    Triggers if count increases by surge_threshold% within
    surge_window_seconds seconds.
    """

    def __init__(self,
                 surge_threshold_pct: float = 50.0,
                 surge_window_seconds: int  = 10):
        self.threshold   = surge_threshold_pct   # % increase
        self.window      = surge_window_seconds
        self._history    = []                    # [(timestamp, count)]

    def update(self, current_count: int) -> tuple[bool, float]:
        """
        Returns (surge_detected: bool, pct_change: float)
        """
        now = time.time()
        self._history.append((now, current_count))

        # Keep only entries within the window
        self._history = [
            (t, c) for t, c in self._history
            if now - t <= self.window
        ]

        if len(self._history) < 2:
            return False, 0.0

        oldest_count = self._history[0][1]
        if oldest_count == 0:
            return False, 0.0

        pct_change = ((current_count - oldest_count) / oldest_count) * 100

        if pct_change >= self.threshold:
            return True, round(pct_change, 1)

        return False, round(pct_change, 1)


# ── EMAIL/SMS NOTIFIER ───────────────────────────────────────────

class AlertNotifier:
    """Sends Email and SMS (via email-to-SMS gateway) notifications."""

    # Common carrier email-to-SMS gateways
    SMS_GATEWAYS = {
        'AT&T'       : 'txt.att.net',
        'T-Mobile'   : 'tmomail.net',
        'Verizon'    : 'vtext.com',
        'Airtel'     : 'airtelap.com',
        'Jio'        : 'jioworldservice.com',
        'BSNL'       : 'bsnlmobile.com',
        'VI (Vodafone)': 'vimail.in',
    }

    def __init__(self,
                 smtp_host    : str = None,
                 smtp_port    : int = None,
                 sender_email : str = None,
                 sender_password: str = None,
                 recipient_email: str = None,
                 phone_number : str = None,
                 carrier      : str = None):

        # Load from environment if not provided
        self.smtp_host   = smtp_host or os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port   = smtp_port or int(os.getenv("SMTP_PORT", "587"))
        self.sender      = sender_email or os.getenv("SMTP_USERNAME", "")
        self.password    = sender_password or os.getenv("SMTP_PASSWORD", "")
        
        # FIXED: Use EMAIL_RECIPIENTS (comma-separated) instead of EMAIL_TO for consistency with email_config.py
        recipients_str = recipient_email or os.getenv("EMAIL_RECIPIENTS", "") or os.getenv("EMAIL_TO", "")
        # Parse comma-separated recipients
        self.recipients = [r.strip() for r in recipients_str.split(",") if r.strip() and "@" in r]
        # For backward compatibility, keep single recipient
        self.recipient = self.recipients[0] if self.recipients else ""
        
        self.phone       = (phone_number or os.getenv("SMS_PHONE_NUMBER", "")).replace("-","").replace(" ","")
        self.carrier     = carrier or os.getenv("SMS_CARRIER", "")
        self.enabled     = bool(self.sender and self.password and self.recipients)

    def _send_email(self, subject: str, body: str,
                    to_email: str) -> tuple[bool, str]:
        try:
            msg = MIMEMultipart()
            msg['From']    = self.sender
            msg['To']      = to_email
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))

            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.ehlo()
                server.starttls()
                server.login(self.sender, self.password)
                server.sendmail(self.sender, to_email, msg.as_string())
            return True, "Sent"
        except smtplib.SMTPAuthenticationError:
            return False, "Auth failed — check email/password or App Password"
        except Exception as e:
            return False, str(e)
    
    def _send_email_with_attachment(self, subject: str, body: str,
                                    to_email: str, image_data: bytes = None) -> tuple[bool, str]:
        """Send email with optional image attachment"""
        try:
            msg = MIMEMultipart()
            msg['From']    = self.sender
            msg['To']      = to_email
            msg['Subject'] = subject
            
            # Attach text body
            msg.attach(MIMEText(body, 'plain'))
            
            # Attach image if provided
            if image_data:
                image_attachment = MIMEImage(image_data)
                image_attachment.add_header('Content-Disposition', 'attachment', filename='alert_snapshot.jpg')
                msg.attach(image_attachment)
                logger.info(f"Attached snapshot image to email for {to_email}")
            
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.ehlo()
                server.starttls()
                server.login(self.sender, self.password)
                server.sendmail(self.sender, to_email, msg.as_string())
            return True, "Sent"
        except smtplib.SMTPAuthenticationError:
            return False, "Auth failed — check email/password or App Password"
        except Exception as e:
            return False, str(e)

    def send_email_alert(self, alert: Alert) -> tuple[bool, str]:
        # FIXED: Check for recipients list instead of single recipient
        if not self.enabled or not self.recipients:
            logger.warning(f"Email not configured: enabled={self.enabled}, recipients={len(self.recipients)}")
            return False, "Email not configured"
        
        # FIXED: Remove severity filter - allow MEDIUM emails (LOW still suppressed in process_alert)
        # Severity filtering is now handled in process_alert() to allow MEDIUM when configured
        logger.info(f"Sending email alert for severity: {alert.severity.value}")
        
        subject = f"ICSS Alert [{alert.severity.value}]"
        
        # Build email body with image URL if available
        body = (
            f"Intelligent Crowd Surveillance ALERT\n"
            f"{'='*40}\n"
            f"Type     : {alert.alert_type.value}\n"
            f"Severity : {alert.severity.value}\n"
            f"Time     : {alert.formatted_time()}\n"
            f"Zone     : {alert.zone_id or 'N/A'}\n"
            f"Count    : {alert.count} people\n"
            f"Density  : {alert.density:.3f} p/m²\n"
            f"\nMessage:\n{alert.message}\n"
            f"{'='*40}\n"
        )
        
        # Add image URL to body if available
        if alert.image_url:
            body += f"\nSnapshot Image: {alert.image_url}\n"
        
        body += f"\nAI Crowd Surveillance System"
        
        def send_with_logging():
            # FIXED: Send to all recipients instead of just one
            success_count = 0
            image_data = None
            
            # Try to download image for attachment if URL is available
            if alert.image_url:
                try:
                    response = requests.get(alert.image_url, timeout=10)
                    if response.status_code == 200:
                        image_data = response.content
                        logger.info(f"Downloaded snapshot image for attachment ({len(image_data)} bytes)")
                    else:
                        logger.warning(f"Failed to download image: HTTP {response.status_code}")
                except Exception as e:
                    logger.warning(f"Failed to download image for attachment: {e}")
            
            for recipient in self.recipients:
                success, message = self._send_email_with_attachment(
                    subject, body, recipient, image_data
                )
                if success:
                    success_count += 1
                    logger.info(f"Email alert sent successfully to {recipient}: {alert.alert_type.value}")
                else:
                    logger.error(f"Email alert failed to {recipient}: {message}")
            
            if success_count > 0:
                logger.info(f"Email alert sent to {success_count}/{len(self.recipients)} recipients")
            else:
                logger.error(f"Email alert failed to all {len(self.recipients)} recipients")
        
        # Run in thread to avoid blocking
        threading.Thread(target=send_with_logging, daemon=True).start()
        return True, f"Email sending in background to {len(self.recipients)} recipients"

    def send_sms_alert(self, alert: Alert) -> tuple[bool, str]:
        if not self.enabled or not self.phone or not self.carrier:
            return False, "SMS not configured"
        
        # Severity filtering: Only send CRITICAL alerts via SMS
        if alert.severity != AlertSeverity.CRITICAL:
            logger.info(f"SMS alert skipped for {alert.severity.value} severity - only CRITICAL sent via SMS")
            return False, f"Severity {alert.severity.value} below SMS threshold"
        
        gateway = self.SMS_GATEWAYS.get(self.carrier)
        if not gateway:
            return False, f"Unknown carrier: {self.carrier}"
        sms_email = f"{self.phone}@{gateway}"
        subject   = "Crowd Alert"
        body      = (
            f"[{alert.severity.value}] {alert.alert_type.value}\n"
            f"{alert.message}\n"
            f"Time: {alert.formatted_time()}"
        )
        
        def send_with_logging():
            success, message = self._send_email(subject, body, sms_email)
            if success:
                logger.info(f"SMS alert sent successfully: {alert.alert_type.value}")
            else:
                logger.error(f"SMS alert failed: {message}")
        
        threading.Thread(target=send_with_logging, daemon=True).start()
        return True, "SMS sending in background"


# ── MAIN ALERT MANAGER ───────────────────────────────────────────

class AlertManager:
    """
    Central alert manager.
    Detects conditions, creates alerts, sends notifications,
    manages alert log and cooldowns.
    """

    def __init__(self,
                 cooldown_seconds      : int   = 60,
                 surge_threshold_pct   : float = 50.0,
                 surge_window_seconds  : int   = 10,
                 high_risk_count_thresh: int   = 15,
                 zone_density_thresh   : float = 0.5,
                 enable_email          : bool  = False,
                 enable_sms            : bool  = False,
                 notifier_config       : dict  = None):

        self.cooldown          = cooldown_seconds
        self.high_risk_thresh  = high_risk_count_thresh
        self.zone_dens_thresh  = zone_density_thresh
        self.enable_email      = enable_email
        self.enable_sms        = enable_sms

        self._alert_log        = []          # all alerts ever
        self._last_alert_time  = {}          # key → timestamp
        self._surge_detector   = SurgeDetector(
            surge_threshold_pct, surge_window_seconds
        )

        # Setup notifier
        cfg = notifier_config or {}
        self._notifier = AlertNotifier(**cfg) if cfg else AlertNotifier()

    # ── COOLDOWN CHECK ───────────────────────────────────────────

    def _can_alert(self, key: str) -> bool:
        last = self._last_alert_time.get(key, 0)
        return (time.time() - last) >= self.cooldown

    def _record_alert(self, key: str, alert: Alert):
        self._last_alert_time[key] = time.time()
        self._alert_log.append(alert)
        # Keep last 100 alerts
        if len(self._alert_log) > 100:
            self._alert_log = self._alert_log[-100:]

        # Send notifications in background
        if self.enable_email:
            self._notifier.send_email_alert(alert)
        if self.enable_sms:
            self._notifier.send_sms_alert(alert)

    # ── DETECTION METHODS ────────────────────────────────────────

    def check_high_risk(self, risk_level: str,
                        count: int, density: float) -> list[Alert]:
        """Trigger if risk_level == HIGH"""
        alerts = []
        if risk_level == "HIGH" and self._can_alert("high_risk"):
            alert = Alert(
                alert_type = AlertType.HIGH_RISK,
                severity   = AlertSeverity.CRITICAL,
                message    = (
                    f"🚨 HIGH RISK detected! "
                    f"{count} people, density {density:.3f} p/m²"
                ),
                count   = count,
                density = density
            )
            self._record_alert("high_risk", alert)
            alerts.append(alert)
        return alerts

    def check_zone_overcrowding(self, zones: list) -> list[Alert]:
        """Trigger for each overcrowded zone"""
        alerts = []
        for zone in zones:
            if not zone.get('is_overcrowded'):
                continue
            key = f"zone_{zone['zone_id']}"
            if self._can_alert(key):
                alert = Alert(
                    alert_type = AlertType.ZONE_OVERCROWDED,
                    severity   = AlertSeverity.HIGH,
                    message    = (
                        f"⚠️ Zone {zone['zone_id']} overcrowded! "
                        f"{zone['people_count']} people, "
                        f"{zone['density']:.3f} p/m²"
                    ),
                    zone_id = zone['zone_id'],
                    count   = zone['people_count'],
                    density = zone['density']
                )
                self._record_alert(key, alert)
                alerts.append(alert)
        return alerts

    def check_surge(self, current_count: int) -> list[Alert]:
        """Trigger on sudden crowd increase"""
        alerts = []
        surge, pct = self._surge_detector.update(current_count)
        if surge and self._can_alert("surge"):
            alert = Alert(
                alert_type = AlertType.CROWD_SURGE,
                severity   = AlertSeverity.CRITICAL,
                message    = (
                    f"📈 CROWD SURGE! Count increased {pct:.1f}% "
                    f"rapidly → {current_count} people now"
                ),
                count = current_count
            )
            self._record_alert("surge", alert)
            alerts.append(alert)
        return alerts

    # === ICSS UPDATE: TASK 2 - Add alert_mode and camera_source parameters ===
    def process_all(self, risk_level: str, count: int,
                    density: float, zones: list, 
                    mobile_camera: bool = False,
                    alert_mode: str = "realtime",
                    camera_source: str = "webcam") -> list[Alert]:
        """
        Run all checks in one call.
        Returns list of NEW alerts triggered this frame.
        
        Args:
            risk_level: Current risk level
            count: People count
            density: Crowd density
            zones: List of zone data
            mobile_camera: Legacy parameter (use camera_source instead)
            alert_mode: "realtime" or "demo"
            camera_source: "webcam", "mobile", or "upload"
        """
        new_alerts = []
        
        # In demo mode, skip automatic alert generation
        if alert_mode == "demo":
            # Demo mode: automatic alerts are paused for display purposes
            # Manual alerts are handled separately in the UI
            return new_alerts
        
        # Realtime mode: use existing automatic logic
        if camera_source == "mobile":
            # RULE - Show ONLY medium and above risk alerts for mobile camera
            if risk_level in ["MEDIUM", "HIGH", "CRITICAL"] and self._can_alert("mobile_risk"):
                # Map risk level to severity
                if risk_level == "MEDIUM":
                    severity = AlertSeverity.MEDIUM
                elif risk_level == "HIGH":
                    severity = AlertSeverity.HIGH
                else:
                    severity = AlertSeverity.CRITICAL
                
                alert = Alert(
                    alert_type = AlertType.HIGH_RISK,
                    severity   = severity,
                    message    = (
                        f"⚠️ {risk_level} RISK [Mobile Camera] - "
                        f"{count} people, density {density:.3f} p/m²"
                    ),
                    count   = count,
                    density = density
                )
                self._record_alert("mobile_risk", alert)
                new_alerts.append(alert)
        else:
            # Normal processing for desktop/webcam - all severity levels
            new_alerts += self.check_high_risk(risk_level, count, density)
            new_alerts += self.check_zone_overcrowding(zones)
            new_alerts += self.check_surge(count)
        
        return new_alerts

    # ── LOG ACCESS ───────────────────────────────────────────────

    def get_recent_alerts(self, n: int = 20) -> list[Alert]:
        return list(reversed(self._alert_log[-n:]))

    def get_active_alerts(self) -> list[Alert]:
        """Alerts from the last 5 minutes"""
        cutoff = time.time() - 300
        return [a for a in self._alert_log if a.timestamp >= cutoff]

    def clear_alerts(self):
        self._alert_log.clear()
        self._last_alert_time.clear()

    def get_stats(self) -> dict:
        active = self.get_active_alerts()
        return {
            'total_alerts'   : len(self._alert_log),
            'active_alerts'  : len(active),
            'high_risk_count': sum(
                1 for a in active
                if a.alert_type == AlertType.HIGH_RISK
            ),
            'surge_count'    : sum(
                1 for a in active
                if a.alert_type == AlertType.CROWD_SURGE
            ),
            'zone_alert_count': sum(
                1 for a in active
                if a.alert_type == AlertType.ZONE_OVERCROWDED
            ),
        }


# === ICSS UPDATE: TASK 2 - Central alert handling functions ===

def handle_alert(alert_data: dict) -> bool:
    """
    Central function to handle alert: store to Firebase, send email, update UI.
    Called from both real-time pipeline and manual alert UI.
    
    Args:
        alert_data: dict with keys: type, severity, count, density, message, zone, etc.
    
    Returns:
        True if alert handled successfully, False on error
    """
    try:
        # 1. Store alert to Firebase/SQLite via alert_store
        from utils.alert_store import get_alert_store
        alert_store = get_alert_store()
        
        # Build alert dict for storage
        storage_dict = {
            "type": alert_data.get("type", "Crowd Alert"),
            "severity": alert_data.get("severity", "MEDIUM"),
            "zone": alert_data.get("zone"),
            "count": alert_data.get("count", 0),
            "density": alert_data.get("density", 0.0),
            "message": alert_data.get("message", ""),
            "image_url": alert_data.get("image_url"),
            "email_sent": False
        }
        
        alert_store.add_alert(storage_dict)
        
        # 2. Send email notification (only for HIGH/CRITICAL)
        severity = alert_data.get("severity", "MEDIUM")
        if severity in ["HIGH", "CRITICAL"]:
            try:
                notifier = AlertNotifier()
                if notifier.enabled:
                    # Create Alert object for email
                    alert_obj = Alert(
                        alert_type=AlertType.HIGH_RISK,
                        severity=AlertSeverity[severity],
                        message=alert_data.get("message", ""),
                        zone_id=alert_data.get("zone"),
                        count=alert_data.get("count", 0),
                        density=alert_data.get("density", 0.0),
                        image_url=alert_data.get("image_url")  # Pass image_url for snapshot attachment
                    )
                    notifier.send_email_alert(alert_obj)
                    # Mark email as sent
                    storage_dict["email_sent"] = True
            except Exception as e:
                logger.warning(f"Email send failed: {e}")
        
        # 3. Update UI state (session_state for real-time display)
        try:
            import streamlit as st
            if "latest_alert" not in st.session_state:
                st.session_state.latest_alert = None
            st.session_state.latest_alert = alert_data
            
            # Also update alerts_list for dashboard display
            if "alerts_list" not in st.session_state:
                st.session_state.alerts_list = []
            
            # Insert at beginning (newest first)
            st.session_state.alerts_list.insert(0, alert_data)
            
            # Keep only last 50 alerts in memory
            if len(st.session_state.alerts_list) > 50:
                st.session_state.alerts_list = st.session_state.alerts_list[:50]
        except Exception:
            pass  # May fail outside Streamlit context
        
        logger.info(f"Alert handled: {alert_data.get('type')} - {severity}")
        return True
        
    except Exception as e:
        logger.error(f"handle_alert error: {e}")
        return False


def process_alert(alert_data: dict) -> bool:
    """
    Process alert with AUTO/MANUAL mode support.
    Should be called from detection loop after each frame.
    
    Args:
        alert_data: dict with keys: timestamp, type, severity, count, density, message
    
    Returns:
        True if alert was processed, False if skipped (cooldown, mode, etc.)
    """
    try:
        import streamlit as st
        
        # Get alert mode (AUTO or MANUAL)
        mode = st.session_state.get("alert_mode", "realtime")
        
        # DEBUG: Print alert data
        print(f"[ALERT DEBUG] mode={mode}, severity={alert_data.get('severity')}, count={alert_data.get('count')}, density={alert_data.get('density')}")
        
        # In demo/manual mode, override with manual settings
        if mode == "demo" or mode == "manual":
            # Override with manual values from session state
            alert_data["severity"] = st.session_state.get("manual_severity", "HIGH")
            alert_data["count"] = st.session_state.get("manual_count", 20)
            alert_data["density"] = st.session_state.get("manual_density", 1.2)
            alert_data["message"] = f"[Manual] {alert_data.get('message', 'Alert triggered')}"
            print(f"[ALERT DEBUG] Demo mode: severity overridden to {alert_data['severity']}")
        
        # FIXED: Bug 1 - Use separate throttle timestamps per severity level
        current_time = time.time()
        if "last_stored" not in st.session_state:
            st.session_state.last_stored = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}
        
        severity = alert_data.get("severity", "MEDIUM")
        
        # FIXED: Bug 1 - Throttle windows per severity
        throttle_windows = {
            "LOW": 30,       # Store at most once per 30s
            "MEDIUM": 15,    # Store at most once per 15s
            "HIGH": 10,      # Store at most once per 10s
            "CRITICAL": 0    # NO throttle - always store immediately
        }
        
        throttle_window = throttle_windows.get(severity, 10)
        
        if throttle_window > 0:
            time_since_last = current_time - st.session_state.last_stored.get(severity, 0)
            if time_since_last < throttle_window:
                print(f"[ALERT DEBUG] {severity} alert throttled (last stored {time_since_last:.2f}s ago, window: {throttle_window}s)")
                return False  # Skip this alert due to throttling
            st.session_state.last_stored[severity] = current_time
        
        # Store ALL alerts in alert_store for live log display
        print(f"[ALERT DEBUG] Storing alert in alert_store: {severity}")
        
        # Build alert dict for storage (stores to session_state + Firebase)
        alert_dict = {
            "type": alert_data.get("type", "crowd"),
            "severity": severity,
            "count": alert_data.get("count", 0),
            "density": alert_data.get("density", 0.0),
            "message": alert_data.get("message", "Alert triggered"),
            "image_url": None,
            "email_sent": False  # Will be updated to True if email is sent
        }
        
        # Store in alert_store (session_state + Firebase)
        from utils.alert_store import get_alert_store
        alert_store = get_alert_store()
        alert_store.add_alert(alert_dict)
        
        # FIXED: Bug 2 - Email sending conditions
        # CRITICAL: always send
        # HIGH: always send
        # MEDIUM: send only if SMTP is configured
        # LOW: never send
        send_email = False
        if severity == "CRITICAL":
            send_email = True
        elif severity == "HIGH":
            send_email = True
        elif severity == "MEDIUM":
            # Check if email is configured
            try:
                from utils.alert_manager import AlertNotifier
                notifier = AlertNotifier()
                if notifier.enabled:
                    send_email = True
                    print(f"[ALERT DEBUG] Email configured for MEDIUM")
                else:
                    print(f"[ALERT DEBUG] Email skipped (not configured for MEDIUM)")
            except Exception:
                print(f"[ALERT DEBUG] Email skipped (not configured for MEDIUM)")
        else:  # LOW
            print(f"[ALERT DEBUG] Email skipped (intentionally suppressed for LOW)")
        
        if send_email:
            print(f"[ALERT DEBUG] Sending email for {severity}")
            # FIXED: Bug 2 - Wrap email call in try/except so failed email never blocks storage
            try:
                return handle_alert(alert_data)
            except Exception as e:
                logger.warning(f"Email send failed but alert was stored: {e}")
                print(f"[ALERT DEBUG] Email send failed but alert was stored: {e}")
                return True  # Return True because alert was stored even if email failed
        else:
            return True  # Return True because alert was stored (even if no email)
        
    except Exception as e:
        logger.error(f"process_alert error: {e}")
        print(f"[ALERT DEBUG] Error in process_alert: {e}")
        return False
