# ICSS Alert System Setup Guide

## Overview
The Intelligent Crowd Surveillance System (ICSS) supports real-time email and SMS notifications for critical security events. This guide provides step-by-step instructions for configuring and implementing both alert types.

## Alert Types & Severity Levels

### Alert Categories
- **HIGH_RISK**: Dangerous crowd density detected
- **ZONE_OVERCROWDED**: Specific zone exceeds capacity
- **CROWD_SURGE**: Rapid increase in crowd count

### Severity Filtering
- **Email Alerts**: HIGH and CRITICAL severity only
- **SMS Alerts**: CRITICAL severity only (most urgent)
- **Mobile Camera**: Medium-risk alerts only (special case)

---

## EMAIL ALERT SETUP

### Step 1: Configure Gmail Account

1. **Enable 2-Factor Authentication**
   - Go to [Google Account Security](https://myaccount.google.com/security)
   - Enable 2-Step Verification

2. **Generate App Password**
   - Go to [App Passwords](https://myaccount.google.com/apppasswords)
   - Select "Mail" for app and "Other (Custom name)" for device
   - Enter "ICSS Alerts" as the name
   - Click "Generate" and copy the 16-character password
   - **Save this password** - you won't see it again

### Step 2: Configure Environment Variables

1. **Copy Environment Template**
   ```bash
   cp env_example.txt .env
   ```

2. **Edit .env File**
   ```env
   # EMAIL CONFIGURATION
   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USERNAME=your@gmail.com
   SMTP_PASSWORD=your-16-character-app-password
   EMAIL_TO=recipient@gmail.com
   ```

3. **Replace Placeholders**
   - `your@gmail.com` - Your Gmail address
   - `your-16-character-app-password` - The app password from Step 1
   - `recipient@gmail.com` - Email address to receive alerts

### Step 3: Enable Email Alerts in UI

1. **Start the Application**
   ```bash
   streamlit run app.py
   ```

2. **Navigate to Alerts Tab**
   - Click on "Alerts" tab in the main dashboard

3. **Configure Email Settings**
   - Enter your Gmail address in "Sender Gmail"
   - Enter the app password in "App Password"
   - Enter recipient email in "Recipient Email"
   - Check "Enable Email Alerts"

4. **Test Configuration**
   - Click "Clear All Alerts" to reset
   - Trigger a HIGH/CRITICAL alert to test email delivery

### Step 4: Troubleshooting Email Issues

**Common Issues & Solutions:**

1. **"Auth failed" Error**
   - Verify app password is correct (16 characters, no spaces)
   - Ensure 2-factor authentication is enabled
   - Check Gmail account isn't blocking less secure apps

2. **"Email not configured" Error**
   - Verify all email fields are filled in the UI
   - Check .env file has correct values
   - Restart the application after .env changes

3. **No Email Received**
   - Check spam/junk folder
   - Verify recipient email address is correct
   - Check console logs for error messages

---

## SMS ALERT SETUP

### Step 1: Choose SMS Method

**Method A: Email-to-SMS Gateway (Recommended)**
- Free, uses existing email setup
- Works with major carriers
- Limited to 160 characters per message

**Method B: Twilio API (Advanced)**
- Professional SMS service
- Requires paid account
- More reliable and feature-rich

### Step 2: Configure Email-to-SMS Gateway

1. **Identify Your Carrier**
   ```
   AT&T: txt.att.net
   T-Mobile: tmomail.net
   Verizon: vtext.com
   Airtel: airtelap.com
   Jio: jioworldservice.com
   BSNL: bsnlmobile.com
   VI (Vodafone): vimail.in
   ```

2. **Configure Environment Variables**
   ```env
   # SMS CONFIGURATION
   SMS_PHONE_NUMBER=1234567890
   SMS_CARRIER=AT&T
   ```

3. **Replace Placeholders**
   - `1234567890` - Your phone number (numbers only)
   - `AT&T` - Your carrier from the list above

### Step 3: Enable SMS Alerts in UI

1. **Navigate to Alerts Tab**
   - Click on "Alerts" tab in the main dashboard

2. **Configure SMS Settings**
   - Enter your phone number in "Phone Number"
   - Select your carrier from the dropdown
   - Check "Enable SMS Alerts"

3. **Test Configuration**
   - Trigger a CRITICAL alert to test SMS delivery
   - Check your phone for the SMS message

### Step 4: Optional Twilio Setup (Advanced)

1. **Create Twilio Account**
   - Sign up at [twilio.com](https://twilio.com)
   - Get Account SID and Auth Token from dashboard
   - Purchase a phone number or use trial number

2. **Configure Twilio Environment**
   ```env
   # TWILIO CONFIGURATION (Optional)
   TWILIO_ACCOUNT_SID=your-twilio-sid
   TWILIO_AUTH_TOKEN=your-twilio-token
   TWILIO_FROM_NUMBER=+1234567890
   ```

3. **Modify Code for Twilio**
   - Note: Current implementation uses email-to-SMS gateway
   - Twilio integration requires code modifications

### Step 5: Troubleshooting SMS Issues

**Common Issues & Solutions:**

1. **"SMS not configured" Error**
   - Verify phone number is entered correctly
   - Check carrier selection matches your provider
   - Ensure .env file has SMS_PHONE_NUMBER and SMS_CARRIER

2. **"Unknown carrier" Error**
   - Verify carrier name matches exactly from the list
   - Check spelling (case-sensitive)
   - Contact support if your carrier isn't listed

3. **No SMS Received**
   - Check if your phone blocks SMS from email addresses
   - Verify carrier supports email-to-SMS gateway
   - Test with a regular email to your phone's SMS gateway

---

## ALERT TESTING & VERIFICATION

### Step 1: Test Alert Generation

1. **Simulate High-Risk Scenario**
   - Use webcam with multiple people
   - Or upload video with crowded scene
   - Monitor risk level in Live Feed tab

2. **Check Alert Dashboard**
   - Navigate to "Alerts" tab
   - Verify alerts appear in the list
   - Check alert severity and timestamp

### Step 2: Test Email Delivery

1. **Trigger HIGH/CRITICAL Alert**
   - Risk level should show "HIGH" or "CRITICAL"
   - Email should be sent automatically

2. **Verify Email Receipt**
   - Check recipient email inbox
   - Verify subject: "ICSS Alert [HIGH/CRITICAL]"
   - Check alert details in email body

### Step 3: Test SMS Delivery

1. **Trigger CRITICAL Alert**
   - Only CRITICAL severity triggers SMS
   - SMS should be sent automatically

2. **Verify SMS Receipt**
   - Check phone for SMS message
   - Verify sender is email gateway
   - Check alert details in SMS

---

## ADVANCED CONFIGURATION

### Custom Alert Thresholds

1. **Adjust Alert Cooldown**
   - In Alerts tab, modify "Alert Cooldown (seconds)"
   - Default: 60 seconds between same alert type
   - Increase to reduce alert frequency

2. **Configure Surge Detection**
   - Modify "Surge Threshold (%)" - default 50%
   - Modify "Surge Window (seconds)" - default 10 seconds
   - Adjust based on your environment

### Alert Logging

1. **View Alert History**
   - Alerts tab shows recent alerts
   - Check alert statistics in sidebar
   - Monitor alert frequency patterns

2. **Debug Logging**
   - Check console for email/SMS success/failure logs
   - Look for "Email alert sent successfully" messages
   - Monitor error messages for troubleshooting

---

## SECURITY CONSIDERATIONS

### Protect Your Credentials

1. **Never Share App Password**
   - Gmail app passwords are sensitive
   - Don't commit .env file to version control
   - Use different password for each application

2. **Secure .env File**
   ```bash
   # Set file permissions (Linux/Mac)
   chmod 600 .env
   
   # Add to .gitignore
   echo ".env" >> .gitignore
   ```

3. **Regular Password Rotation**
   - Change Gmail app passwords periodically
   - Update .env file when changing passwords
   - Restart application after credential changes

### Privacy Considerations

1. **Recipient Consent**
   - Ensure alert recipients consent to receive alerts
   - Provide opt-out mechanism for SMS alerts
   - Consider alert frequency impact

2. **Data Protection**
   - Alert logs contain crowd count and density data
   - Follow local privacy regulations
   - Consider data retention policies

---

## MAINTENANCE & MONITORING

### Regular Maintenance Tasks

1. **Weekly Checks**
   - Verify email/SMS delivery is working
   - Check alert logs for errors
   - Monitor alert frequency patterns

2. **Monthly Reviews**
   - Review alert threshold effectiveness
   - Update contact information if needed
   - Check carrier gateway reliability

3. **Quarterly Updates**
   - Rotate Gmail app passwords
   - Update carrier information if needed
   - Review and update alert policies

### Performance Monitoring

1. **Alert Response Time**
   - Monitor time from alert trigger to delivery
   - Check for delays in email/SMS delivery
   - Optimize if response time is slow

2. **System Health**
   - Monitor alert generation rate
   - Check for false positives
   - Adjust thresholds based on patterns

---

## TROUBLESHOOTING GUIDE

### Common Error Messages

1. **"Email not configured"**
   - Check all email fields in UI
   - Verify .env file exists and has correct values
   - Restart application after .env changes

2. **"SMS not configured"**
   - Verify phone number format (numbers only)
   - Check carrier selection matches provider
   - Ensure .env has SMS_PHONE_NUMBER and SMS_CARRIER

3. **"Auth failed"**
   - Verify Gmail app password is correct
   - Ensure 2-factor authentication is enabled
   - Check for account lock or security issues

4. **"Unknown carrier"**
   - Verify carrier name exactly matches list
   - Check spelling and capitalization
   - Consider using email-to-SMS directly

### Debug Steps

1. **Check Console Logs**
   ```bash
   # Look for these messages:
   "Email alert sent successfully"
   "SMS alert sent successfully"
   "Email alert failed: [error details]"
   "SMS alert failed: [error details]"
   ```

2. **Verify Configuration**
   - Check .env file contents
   - Verify UI settings match .env values
   - Test credentials manually if needed

3. **Test Manually**
   - Send test email to recipient
   - Send test SMS to phone via email gateway
   - Verify network connectivity

---

## CONTACT & SUPPORT

### Getting Help

1. **Documentation**
   - Check this guide first
   - Review console error messages
   - Check application logs

2. **Common Issues**
   - Most issues are configuration-related
   - Verify all steps were followed correctly
   - Test credentials independently

3. **Advanced Support**
   - Check GitHub issues for known problems
   - Review application source code
   - Contact development team if needed

### Best Practices

1. **Start Simple**
   - Configure email alerts first
   - Test thoroughly before adding SMS
   - Use test scenarios to verify functionality

2. **Monitor Performance**
   - Watch alert frequency
   - Check delivery success rates
   - Adjust thresholds based on experience

3. **Maintain Security**
   - Protect credentials carefully
   - Update passwords regularly
   - Follow security best practices

---

**Last Updated**: April 14, 2026  
**Version**: 1.0  
**Compatibility**: ICSS v2.1.0+
