# ICSS Alert System - Doubts & FAQ

## 🚨 **Types of Alerts in ICSS**

### 1️⃣ **Zone Overcrowding Alerts**
- **Trigger**: When people count exceeds threshold in a specific zone
- **Severity**: HIGH
- **Details**: Zone ID, people count, density
- **Example**: "Zone A overcrowded! 25 people, 0.850 p/m²"

### 2️⃣ **High Risk Level Alerts**
- **Trigger**: When overall risk assessment reaches "HIGH"
- **Severity**: CRITICAL
- **Details**: Total people count, overall density
- **Example**: "🚨 HIGH RISK detected! 45 people, density 1.250 p/m²"

### 3️⃣ **Sudden Crowd Surge Alerts**
- **Trigger**: Rapid increase in crowd count (>50% in 10 seconds)
- **Severity**: CRITICAL
- **Details**: Percentage increase, current count
- **Example**: "📈 CROWD SURGE! Count increased 75% rapidly → 60 people now"

### 4️⃣ **Medium Risk Alerts (Mobile Camera)**
- **Trigger**: Medium risk level detected on mobile camera feed
- **Severity**: MEDIUM
- **Details**: Current count and density
- **Example**: "⚠️ MEDIUM RISK - 12 people, density 0.450 p/m²"

---

## 📧 **Email Setup - Complete Guide**

### 🔧 **Step 1: Choose Email Provider**

#### **Gmail (Recommended)**
```bash
# Add to .env file
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USE_TLS=true
SMTP_USERNAME=your-alerts@gmail.com
SMTP_PASSWORD=your-app-password
EMAIL_RECIPIENTS=admin1@company.com,admin2@company.com,security@company.com
```

#### **Outlook/Office 365**
```bash
SMTP_HOST=smtp-mail.outlook.com
SMTP_PORT=587
SMTP_USE_TLS=true
SMTP_USERNAME=your-email@outlook.com
SMTP_PASSWORD=your-password
EMAIL_RECIPIENTS=admin1@company.com,admin2@company.com,security@company.com
```

#### **Custom SMTP**
```bash
SMTP_HOST=your-company-smtp.com
SMTP_PORT=587
SMTP_USE_TLS=true
SMTP_USERNAME=your-username
SMTP_PASSWORD=your-password
EMAIL_RECIPIENTS=admin1@company.com,admin2@company.com,security@company.com
```

### 🔐 **Step 2: Gmail App Password Setup**

#### **Why App Password?**
- More secure than using main password
- Can be revoked independently
- Required for 2FA-enabled accounts
- Limited to specific app access

#### **Create Gmail App Password**
1. **Go to**: https://myaccount.google.com/apppasswords
2. **Sign in** to your Google account
3. **Select app**: Choose "Mail" → "Other (Custom name)"
4. **Enter name**: "ICSS Alerts"
5. **Generate**: Copy the 16-character password
6. **Use this password** in `SMTP_PASSWORD`

### 👥 **Step 3: Configure Multiple Recipients**

#### **Format for Multiple Admins**
```bash
# Comma-separated (no spaces)
EMAIL_RECIPIENTS=it-security@company.com,operations@company.com,management@company.com,emergency@company.com
```

#### **Recommended Recipient Structure**
- **IT Security**: it-security@company.com
- **Operations Team**: operations@company.com
- **Management**: management@company.com
- **Emergency Contact**: emergency@company.com
- **On-call Engineer**: oncall@company.com

### 🎛️ **Step 4: ICSS UI Configuration**

#### **Access Email Settings**
1. Open ICSS application
2. Go to **"🚨 Alerts"** tab
3. Find **"📧 Email Configuration"** section
4. Expand to see all settings

#### **Configure in UI**
1. **SMTP Server Settings**:
   - SMTP Host: smtp.gmail.com
   - SMTP Port: 587
   - Use TLS: ✅ checked

2. **Sender Account**:
   - Sender Email: your-alerts@gmail.com
   - Sender Password: your-16-digit-app-password

3. **Recipients (Multiple Admins)**:
   ```
   it-security@company.com,operations@company.com,management@company.com
   ```

4. **Save Configuration**:
   - Click **"💾 Save Email Configuration"**
   - Verify success message

#### **Test Email Setup**
1. Click **"🧪 Send Test Email"**
2. Check all recipient inboxes
3. Verify email content and formatting

---

## 🔍 **Troubleshooting Common Issues**

### ❌ **"Authentication Failed" Error**
**Causes**:
- Wrong email/password
- 2FA not enabled
- Using main password instead of app password

**Solutions**:
1. Enable 2-factor authentication on Gmail
2. Generate new app password
3. Double-check email spelling
4. Use app password (not main password)

### 📭 **"Emails Not Received"**
**Causes**:
- Spam filters blocking emails
- Wrong recipient addresses
- SMTP server issues

**Solutions**:
1. Check spam/junk folders
2. Verify recipient email addresses
3. Whitelist sender email
4. Test with fewer recipients

### 🔢 **"Rate Limit Exceeded"**
**Causes**:
- Gmail: 100 emails/day limit
- Too many alerts in short time

**Solutions**:
1. Use business Gmail account
2. Implement alert cooldown
3. Use email batching
4. Consider dedicated email service

---

## 🎯 **Production Best Practices**

### 🛡️ **Security Recommendations**
1. **Use App Passwords**: Never main passwords
2. **Regular Rotation**: Change passwords quarterly
3. **Limited Access**: Only necessary personnel
4. **Audit Logs**: Monitor email access

### 📊 **Monitoring Setup**
1. **Multiple Recipients**: At least 3-4 admins
2. **Different Departments**: IT, Ops, Management
3. **24/7 Coverage**: Time zone distribution
4. **Backup Contacts**: Secondary email addresses

### 🔄 **Testing Procedures**
1. **Weekly Tests**: Send test emails
2. **Alert Drills**: Test actual alert scenarios
3. **Delivery Verification**: Confirm all recipients receive emails
4. **Format Checking**: Ensure email readability

---

## 📞 **Support & Help**

### 🆘 **Quick Help**
- **Email Issues**: Check `email_setup_guide.md`
- **Configuration**: Use ICSS UI Email Configuration section
- **Testing**: Use "Send Test Email" button
- **Logs**: Check browser console for errors

### 📚 **Documentation**
- **Complete Guide**: `email_setup_guide.md`
- **Environment Setup**: `enhanced_alert_setup.md`
- **Troubleshooting**: Check browser console logs

### 🧪 **Test Scenarios**
Test these scenarios to verify setup:
1. **Basic Test**: Send test email to all recipients
2. **Alert Test**: Trigger actual zone overcrowding
3. **Failure Test**: Test with wrong credentials
4. **Load Test**: Multiple rapid alerts

---

## ✅ **Setup Verification Checklist**

### 📧 **Email Configuration**
- [ ] SMTP server configured correctly
- [ ] App password generated (Gmail)
- [ ] Multiple recipients added
- [ ] Test email sent successfully
- [ ] All recipients received test email

### 🔔 **Alert Integration**
- [ ] Email alerts enabled in UI
- [ ] Database email setting synchronized
- [ ] Local SMTP configuration working
- [ ] Alert generation triggers emails
- [ ] Email content includes all details

### 🛡️ **Security Setup**
- [ ] 2FA enabled on email account
- [ ] App passwords used instead of main passwords
- [ ] Recipient list reviewed and approved
- [ ] Access control measures in place

---

## 📧 **Email Output - What Recipients Receive**

### 📨 **Alert Email Content**

When an alert is triggered, all configured recipients receive an email with:

#### **Subject Line**
```
[CRITICAL] Zone Overcrowding Alert
[HIGH] Crowd Surge Alert
[MEDIUM] Medium Risk Alert
```

#### **Email Body Format**
```
ICSS ALERT NOTIFICATION
==================================================

ALERT TYPE: Zone Overcrowding
SEVERITY: CRITICAL
TIME: 2024-04-16 11:05:30

MESSAGE:
Zone A overcrowded! 25 people, 0.850 p/m²

==================================================
This is an automated alert from the Intelligent Crowd Surveillance System.
For security, this email was sent to multiple administrators.
```

#### **Included Information**
- 🚨 **Alert Type**: Zone Overcrowding / High Risk / Crowd Surge
- 🔴 **Severity Level**: CRITICAL / HIGH / MEDIUM
- 🕒 **Timestamp**: Exact time of alert trigger
- 📍 **Zone Information**: Which zone triggered the alert
- 👥 **People Count**: Number of people detected
- 📊 **Density**: People per square meter
- 📸 **Snapshot Link**: Direct link to alert image (if available)
- 🔗 **System Link**: Direct URL to ICSS dashboard

### 📸 **Email with Snapshot**

If Cloudinary is configured and snapshots are enabled:

#### **Image Attachment Details**
- **Format**: JPEG image, 85% quality
- **Resolution**: Same as video frame (640x480 or higher)
- **File Size**: Typically 50-200KB
- **Storage**: Hosted on Cloudinary CDN

#### **Email Integration**
- **Thumbnail Preview**: Small image in email body
- **Full Resolution Link**: Click to view original
- **CDN Delivery**: Fast loading from Cloudinary
- **Automatic Cleanup**: Images stored for 30 days

### 📊 **Multiple Recipient Delivery**

#### **Simultaneous Delivery**
- **All recipients** receive the same email
- **No delays** between recipients
- **Individual delivery** (not BCC - visible to all)
- **Tracking**: Delivery status logged

#### **Recipient List Example**
If `EMAIL_RECIPIENTS=admin1@company.com,admin2@company.com,security@company.com`:

```
To: admin1@company.com, admin2@company.com, security@company.com
Subject: [CRITICAL] Zone Overcrowding Alert
Body: [Full alert details as shown above]
```

### 🔄 **Alert Frequency Control**

#### **Cooldown Period**
- **Default**: 60 seconds between same alert type
- **Purpose**: Prevent email spam
- **Configurable**: Adjustable in ICSS Controls tab
- **Per-alert type**: Separate cooldowns for different alert types

#### **Rate Limiting Examples**
- **Zone Overcrowding**: Max 1 per minute per zone
- **High Risk**: Max 1 per 2 minutes globally
- **Crowd Surge**: Max 1 per 5 minutes globally
- **Medium Risk**: Max 1 per minute (mobile camera)

### 📱 **Mobile Device Access**

#### **Responsive Email Format**
- **Mobile-friendly**: Optimized for phone screens
- **Quick Actions**: Direct links to dashboard
- **Image Optimization**: Compressed for mobile data
- **Touch-friendly**: Large tap targets

#### **Push Notification Integration**
- **Email to SMS**: Via carrier gateways
- **Mobile Apps**: Direct push notifications
- **Browser Notifications**: Desktop alerts
- **Sound Alerts**: Audio notification options

---

## 🎯 **Example Email Scenarios**

### 🚨 **Critical Zone Overcrowding**
```
Subject: [CRITICAL] Zone A Overcrowded

ICSS ALERT NOTIFICATION
==================================================

ALERT TYPE: Zone Overcrowding
SEVERITY: CRITICAL
TIME: 2024-04-16 11:05:30

MESSAGE:
Zone A overcrowded! 35 people, 1.200 p/m²
Threshold exceeded: 15 people max per zone

SNAPSHOT: https://res.cloudinary.com/icss-alerts/alert_20240416_110530.jpg

==================================================
This is an automated alert from the Intelligent Crowd Surveillance System.
For security, this email was sent to multiple administrators.
```

### 📈 **Crowd Surge Alert**
```
Subject: [CRITICAL] Crowd Surge Detected

ICSS ALERT NOTIFICATION
==================================================

ALERT TYPE: Crowd Surge
SEVERITY: CRITICAL
TIME: 2024-04-16 11:10:15

MESSAGE:
📈 CROWD SURGE! Count increased 75% rapidly → 80 people now
Previous count: 45 people (30 seconds ago)
Surge threshold: 50% increase

SNAPSHOT: https://res.cloudinary.com/icss-alerts/alert_20240416_111015.jpg

==================================================
This is an automated alert from the Intelligent Crowd Surveillance System.
For security, this email was sent to multiple administrators.
```

### ⚠️ **Medium Risk Alert**
```
Subject: [MEDIUM] Medium Risk Level

ICSS ALERT NOTIFICATION
==================================================

ALERT TYPE: Medium Risk
SEVERITY: MEDIUM
TIME: 2024-04-16 11:15:45

MESSAGE:
⚠️ MEDIUM RISK - 18 people, density 0.720 p/m²
Risk factors: High density in central area

SNAPSHOT: https://res.cloudinary.com/icss-alerts/alert_20240416_111545.jpg

==================================================
This is an automated alert from the Intelligent Crowd Surveillance System.
For security, this email was sent to multiple administrators.
```

---

---

## 🎯 **Risk Level System - Complete Guide**

### 📊 **Risk Level Classifications**

#### 🟢 **NORMAL (Green)**
- **Condition**: Low crowd density and count
- **Threshold**: Count < 5 AND Density < 0.3 p/m²
- **Message**: "Normal crowd activity"
- **Action**: Continue monitoring, no alert
- **Color**: Green overlay on video

#### 🟡 **AVERAGE (Yellow)**
- **Condition**: Moderate crowd density
- **Threshold**: Count 5-15 OR Density 0.3-0.7 p/m²
- **Message**: "Moderate crowd density detected"
- **Action**: Increased monitoring, no alert
- **Color**: Yellow overlay on video

#### 🟠 **RISKY (Orange/Red)**
- **Condition**: High crowd density
- **Threshold**: Count > 15 OR Density > 0.7 p/m²
- **Message**: "High crowd density - risk level increased"
- **Action**: Prepare for potential alerts
- **Color**: Orange/Red overlay on video

---

## 🚨 **Alert Trigger Conditions**

### 1️⃣ **Zone Overcrowding Alerts**

#### **Trigger Conditions**
```python
# Zone-based overcrowding
if zone_people_count > zone_max_capacity:
    trigger_alert("Zone Overcrowding", "HIGH")
    
if zone_density > 0.5:  # p/m²
    trigger_alert("Zone Overcrowding", "CRITICAL")
```

#### **Threshold Values**
- **Zone Capacity**: Default 15 people per zone
- **Density Threshold**: 0.5 people per square meter
- **Check Frequency**: Every video frame (30 fps)
- **Cooldown**: 60 seconds per zone

#### **Generated Messages**
```
Zone A overcrowded! 25 people, 0.850 p/m²
Zone B critical overcrowding! 35 people, 1.200 p/m²
Zone C approaching capacity! 18 people, 0.650 p/m²
```

#### **Severity Mapping**
- **HIGH**: 15-25 people OR 0.5-0.8 p/m²
- **CRITICAL**: >25 people OR >0.8 p/m²

### 2️⃣ **High Risk Level Alerts**

#### **Trigger Conditions**
```python
# Global risk assessment
if overall_risk_level == "HIGH":
    trigger_alert("High Risk", "CRITICAL")
    
if people_count > 25 and density > 0.8:
    trigger_alert("High Risk", "CRITICAL")
```

#### **Threshold Values**
- **People Count**: >25 globally
- **Density**: >0.8 p/m² globally
- **Risk Factors**: Flow conflicts, speed variations
- **Assessment**: Combined weighted analysis

#### **Generated Messages**
```
🚨 HIGH RISK detected! 45 people, density 1.250 p/m²
🚨 CRITICAL RISK! 60 people, density 1.800 p/m²
High risk due to flow conflicts and abnormal speed patterns
```

#### **Risk Calculation Formula**
```python
risk_score = (
    density_weight * density_score +
    flow_conflict_weight * flow_conflict_score +
    speed_variation_weight * speed_variation_score
)

# Default weights
density_weight = 0.4
flow_conflict_weight = 0.35
speed_variation_weight = 0.25
```

### 3️⃣ **Sudden Crowd Surge Alerts**

#### **Trigger Conditions**
```python
# Surge detection algorithm
current_count = get_current_people_count()
previous_count = get_count_from_seconds_ago(10)

if previous_count > 0:
    percentage_increase = ((current_count - previous_count) / previous_count) * 100
    
    if percentage_increase >= 50:  # 50% surge threshold
        trigger_alert("Crowd Surge", "CRITICAL")
```

#### **Threshold Values**
- **Surge Percentage**: 50% increase minimum
- **Time Window**: 10 seconds lookback
- **Minimum Count**: 5 people required before surge detection
- **Cooldown**: 10 seconds between surge alerts

#### **Generated Messages**
```
📈 CROWD SURGE! Count increased 75% rapidly → 80 people now
📈 CROWD SURGE! Count increased 120% rapidly → 55 people now
📈 CROWD SURGE! Count increased 50% rapidly → 30 people now (previous: 20)
```

### 4️⃣ **Medium Risk Alerts (Mobile Camera)**

#### **Trigger Conditions**
```python
# Mobile camera specific logic
if camera_source == "mobile" and risk_level == "MEDIUM":
    trigger_alert("Medium Risk", "MEDIUM")
```

#### **Threshold Values**
- **Camera Type**: Mobile/IP camera only
- **Risk Level**: MEDIUM threshold
- **Count**: 8-15 people
- **Density**: 0.4-0.7 p/m²

#### **Generated Messages**
```
⚠️ MEDIUM RISK - 12 people, density 0.450 p/m²
⚠️ MEDIUM RISK - 10 people, density 0.520 p/m² (Mobile Camera)
Medium risk detected on mobile camera feed
```

---

## 📋 **Complete Alert Message Examples**

### 🚨 **CRITICAL Level Messages**

#### **Zone Overcrowding - CRITICAL**
```
🚨 CRITICAL ZONE OVERCROWDING!
Zone: Sector A (Entrance Area)
People Count: 35 people
Density: 1.200 p/m²
Capacity: 15 people max
Time: 2024-04-16 11:47:30
Action: Immediate crowd dispersal required
```

#### **High Risk - CRITICAL**
```
🚨 CRITICAL RISK LEVEL DETECTED!
Global Count: 60 people
Global Density: 1.800 p/m²
Risk Factors: High density + flow conflicts
Threshold Exceeded: 25 people / 0.8 p/m²
Time: 2024-04-16 11:47:30
Action: Emergency response protocols activated
```

#### **Crowd Surge - CRITICAL**
```
🚨 CRITICAL CROWD SURGE ALERT!
Previous Count: 30 people (10 seconds ago)
Current Count: 80 people
Surge Percentage: 167% increase
Surge Rate: 5 people per second
Time: 2024-04-16 11:47:30
Action: Immediate crowd control measures
```

### ⚠️ **HIGH Level Messages**

#### **Zone Overcrowding - HIGH**
```
⚠️ HIGH ZONE OVERCROWDING!
Zone: Sector B (Main Stage)
People Count: 22 people
Density: 0.750 p/m²
Capacity: 15 people max
Time: 2024-04-16 11:47:30
Action: Monitor and prepare for intervention
```

#### **High Risk - HIGH**
```
⚠️ HIGH RISK LEVEL DETECTED!
Global Count: 35 people
Global Density: 0.950 p/m²
Risk Factors: Elevated density detected
Threshold Approaching: 25 people / 0.8 p/m²
Time: 2024-04-16 11:47:30
Action: Increased monitoring, prepare for escalation
```

### 📋 **MEDIUM Level Messages**

#### **Medium Risk - MEDIUM**
```
⚠️ MEDIUM RISK LEVEL DETECTED!
Global Count: 18 people
Global Density: 0.650 p/m²
Risk Factors: Moderate density increase
Time: 2024-04-16 11:47:30
Action: Continue monitoring with increased vigilance
```

#### **Mobile Camera - MEDIUM**
```
⚠️ MEDIUM RISK (Mobile Camera)!
Camera Feed: Mobile Camera 1
People Count: 12 people
Density: 0.520 p/m²
Mobile Threshold: 8-15 people range
Time: 2024-04-16 11:47:30
Action: Enhanced monitoring required
```

---

## ⚙️ **Configurable Thresholds**

### 🎛️ **In ICSS Controls Tab**

#### **Density Thresholds**
- **Low Density**: < 0.3 p/m² (Normal)
- **Medium Density**: 0.3-0.7 p/m² (Average)
- **High Density**: > 0.7 p/m² (Risky)

#### **Count Thresholds**
- **Low Count**: < 5 people (Normal)
- **Medium Count**: 5-15 people (Average)
- **High Count**: > 15 people (Risky)

#### **Alert Configuration**
- **Cooldown Period**: 60 seconds (adjustable)
- **Surge Threshold**: 50% (adjustable)
- **Surge Window**: 10 seconds (adjustable)

### 🔧 **Advanced Settings**

#### **Zone Analysis**
- **Grid Size**: 3x3 zones (configurable)
- **Zone Capacity**: 15 people per zone (default)
- **Real-world Mapping**: 50m x 30m area
- **Restricted Zones**: Custom no-go areas

#### **Risk Assessment Weights**
- **Density Weight**: 40% (default)
- **Flow Conflict Weight**: 35% (default)
- **Speed Variation Weight**: 25% (default)

---

**🎉 Your ICSS Risk Level System is now fully documented!**

**Key Points:**
1. **Multiple risk levels** with clear thresholds
2. **Different alert types** for various scenarios
3. **Configurable parameters** for different environments
4. **Real-time assessment** with multiple factors
5. **Actionable messages** with specific recommendations
