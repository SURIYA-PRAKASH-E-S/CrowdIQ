"""
utils/email_config.py — Email configuration and management for ICSS alerts

Handles multiple recipient configuration, email validation, and security settings.
"""

import os
import logging
from typing import List, Dict, Any
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dataclasses import dataclass
import streamlit as st

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger(__name__)

@dataclass
class EmailConfig:
    """Email configuration data class"""
    smtp_host: str
    smtp_port: int
    sender_email: str
    sender_password: str
    recipients: List[str]
    use_tls: bool = True

class EmailManager:
    """Manages email configuration and sending for ICSS alerts"""
    
    def __init__(self):
        self.config = self._load_config()
        self.enabled = False
    
    def _load_config(self) -> EmailConfig:
        """Load email configuration from environment variables"""
        return EmailConfig(
            smtp_host=os.getenv("SMTP_HOST", "smtp.gmail.com"),
            smtp_port=int(os.getenv("SMTP_PORT", "587")),
            sender_email=os.getenv("SMTP_USERNAME", ""),
            sender_password=os.getenv("SMTP_PASSWORD", ""),
            recipients=self._parse_recipients(os.getenv("EMAIL_RECIPIENTS", "")),
            use_tls=os.getenv("SMTP_USE_TLS", "true").lower() == "true"
        )
    
    def _parse_recipients(self, recipients_str: str) -> List[str]:
        """Parse comma-separated recipients string"""
        if not recipients_str:
            return []
        
        recipients = [email.strip() for email in recipients_str.split(",")]
        return [email for email in recipients if email and "@" in email]
    
    def is_configured(self) -> bool:
        """Check if email is properly configured"""
        return (
            bool(self.config.sender_email) and 
            bool(self.config.sender_password) and 
            len(self.config.recipients) > 0
        )
    
    def get_config_status(self) -> Dict[str, Any]:
        """Get current configuration status"""
        return {
            'configured': self.is_configured(),
            'sender': self.config.sender_email[:10] + "..." if self.config.sender_email else "",
            'recipient_count': len(self.config.recipients),
            'recipients': [email[:10] + "..." for email in self.config.recipients],
            'smtp_host': self.config.smtp_host,
            'smtp_port': self.config.smtp_port,
            'enabled': self.enabled
        }
    
    def enable_email(self, enabled: bool):
        """Enable or disable email sending"""
        self.enabled = enabled
        logger.info(f"Email alerts {'enabled' if enabled else 'disabled'}")
    
    def send_alert_email(self, 
                     subject: str, 
                     message: str, 
                     alert_type: str = "ICSS Alert",
                     severity: str = "HIGH") -> bool:
        """
        Send alert email to all configured recipients
        
        Args:
            subject: Email subject
            message: Email body content
            alert_type: Type of alert for categorization
            severity: Alert severity level
            
        Returns:
            True if successful, False otherwise
        """
        if not self.enabled or not self.is_configured():
            logger.warning("Email not enabled or not configured")
            return False
        
        try:
            # Create email message
            msg = MIMEMultipart()
            msg['From'] = self.config.sender_email
            msg['To'] = ", ".join(self.config.recipients)
            msg['Subject'] = f"[{severity}] {subject}"
            
            # Email body with alert details
            body = f"""
ICSS ALERT NOTIFICATION
{'='*50}

ALERT TYPE: {alert_type}
SEVERITY: {severity}
TIME: {self._get_current_time()}

MESSAGE:
{message}

{'='*50}

This is an automated alert from the Intelligent Crowd Surveillance System.
For security, this email was sent to multiple administrators.
            """
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Send email
            with smtplib.SMTP(self.config.smtp_host, self.config.smtp_port) as server:
                if self.config.use_tls:
                    server.starttls()
                server.login(self.config.sender_email, self.config.sender_password)
                server.send_message(msg)
            
            logger.info(f"Alert email sent to {len(self.config.recipients)} recipients")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send alert email: {e}")
            return False
    
    def _get_current_time(self) -> str:
        """Get current timestamp for email"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def test_email_configuration(self) -> Dict[str, Any]:
        """Test email configuration and return results"""
        if not self.is_configured():
            return {
                'success': False,
                'message': 'Email not properly configured. Check SMTP credentials and recipients.'
            }
        
        try:
            # Send test email with exact format provided
            from datetime import datetime
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            test_message = f"""# ICSS ALERT SYSTEM — TEST EMAIL

ALERT TYPE: System Test
SEVERITY: INFO
TIME: {current_time}

MESSAGE:
This is a test email to verify that ICSS alert notification system is working correctly.

No action is required. If you received this email, email configuration (SMTP) is successfully set up.

SYSTEM DETAILS:

* Module: Email Notification Service
* Status: Operational
* Trigger: Manual Test

SNAPSHOT: Not Applicable

==================================================
This is an automated test email from the Intelligent Crowd Surveillance System (ICSS).
Please ignore this message.


Make this as Test mail"""
            
            test_result = self.send_alert_email(
                subject="ICSS ALERT SYSTEM — TEST EMAIL",
                message=test_message,
                alert_type="System Test",
                severity="INFO"
            )
            
            if test_result:
                return {
                    'success': True,
                    'message': f'Test email sent successfully to {len(self.config.recipients)} recipients.'
                }
            else:
                return {
                    'success': False,
                    'message': 'Failed to send test email. Check SMTP settings.'
                }
                
        except Exception as e:
            return {
                'success': False,
                'message': f'Email test failed: {str(e)}'
            }

# Global email manager instance
_email_manager = EmailManager()

def get_email_manager() -> EmailManager:
    """Get global email manager instance"""
    return _email_manager

def setup_email_from_ui() -> bool:
    """
    Setup email configuration from Streamlit UI
    Returns True if configuration was updated
    """
    email_manager = get_email_manager()
    
    st.markdown("### 📧 Email Configuration")
    st.markdown("---")
    
    # Current status
    status = email_manager.get_config_status()
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Status", "🟢 Configured" if status['configured'] else "🔴 Not Configured")
        st.metric("Recipients", status['recipient_count'])
    
    with col2:
        st.metric("Enabled", "🟢 Yes" if status['enabled'] else "🔴 No")
        st.metric("SMTP Server", status['smtp_host'])
    
    st.markdown("#### 🔧 Email Settings")
    
    # SMTP Configuration
    with st.expander("SMTP Server Settings", expanded=False):
        smtp_host = st.text_input(
            "SMTP Host",
            value=os.getenv("SMTP_HOST", "smtp.gmail.com"),
            help="SMTP server hostname (e.g., smtp.gmail.com)"
        )
        
        smtp_port = st.number_input(
            "SMTP Port",
            value=int(os.getenv("SMTP_PORT", "587")),
            min_value=1,
            max_value=65535,
            help="SMTP server port (usually 587 for TLS)"
        )
        
        use_tls = st.checkbox(
            "Use TLS/SSL",
            value=os.getenv("SMTP_USE_TLS", "true").lower() == "true",
            help="Enable TLS encryption for secure email sending"
        )
    
    # Sender Configuration
    with st.expander("Sender Account", expanded=False):
        sender_email = st.text_input(
            "Sender Email",
            value=os.getenv("SMTP_USERNAME", ""),
            type="default",
            help="Email address that will send alerts (use app password for Gmail)"
        )
        
        sender_password = st.text_input(
            "Sender Password / App Password",
            value=os.getenv("SMTP_PASSWORD", ""),
            type="password",
            help="Email password or app password (recommended for Gmail)"
        )
    
    # Recipients Configuration
    with st.expander("Recipients (Multiple Admins)", expanded=True):
        recipients_str = st.text_area(
            "Email Recipients",
            value=", ".join(email_manager.config.recipients),
            placeholder="admin1@company.com, admin2@company.com, security@company.com",
            help="Comma-separated list of recipient emails for alerts"
        )
        
        st.info("📝 **Security Tip**: Configure multiple administrators (IT security, operations, management) to ensure alerts are always monitored.")
    
    # Enable/Disable
    email_enabled = st.checkbox(
        "✅ Enable Email Alerts",
        value=email_manager.enabled,
        help="Master switch for email alert notifications"
    )
    
    # Update configuration
    config_updated = False
    
    if st.button("💾 Save Email Configuration", type="primary"):
        # Parse recipients
        recipients = [email.strip() for email in recipients_str.split(",")]
        recipients = [email for email in recipients if email and "@" in email]
        
        if not recipients:
            st.error("❌ Please provide at least one valid email recipient")
            return False
        
        if not sender_email or not sender_password:
            st.error("❌ Please provide sender email and password")
            return False
        
        # Update configuration
        os.environ["SMTP_HOST"] = smtp_host
        os.environ["SMTP_PORT"] = str(smtp_port)
        os.environ["SMTP_USE_TLS"] = str(use_tls).lower()
        os.environ["SMTP_USERNAME"] = sender_email
        os.environ["SMTP_PASSWORD"] = sender_password
        os.environ["EMAIL_RECIPIENTS"] = ", ".join(recipients)
        
        # Reload configuration
        email_manager.config = email_manager._load_config()
        email_manager.enable_email(email_enabled)
        
        st.success("✅ Email configuration saved successfully!")
        config_updated = True
    
    # Test configuration
    if st.button("🧪 Send Test Email"):
        test_result = email_manager.test_email_configuration()
        if test_result['success']:
            st.success(test_result['message'])
        else:
            st.error(test_result['message'])
    
    # Update enabled state
    if email_enabled != email_manager.enabled:
        email_manager.enable_email(email_enabled)
        config_updated = True
    
    return config_updated
