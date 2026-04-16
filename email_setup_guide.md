# ICSS Email Setup Guide for Multiple Administrators

## 🎯 Overview

Setup email alerts to send notifications to multiple administrators and security personnel for comprehensive monitoring.

## 📧 Email Configuration Options

### Option 1: Gmail (Recommended)
1. **Enable 2-Factor Authentication** on your Gmail account
2. **Create App Password**:
   - Go to Google Account settings → Security → App passwords
   - Generate a new app password for ICSS
   - Use this password instead of your regular password
3. **Configure Environment Variables**:
   ```bash
   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USE_TLS=true
   SMTP_USERNAME=your-email@gmail.com
   SMTP_PASSWORD=your-app-password
   EMAIL_RECIPIENTS=admin1@company.com,admin2@company.com,security@company.com
   ```

### Option 2: Outlook/Office 365
```bash
SMTP_HOST=smtp-mail.outlook.com
SMTP_PORT=587
SMTP_USE_TLS=true
SMTP_USERNAME=your-email@outlook.com
SMTP_PASSWORD=your-password
EMAIL_RECIPIENTS=admin1@company.com,admin2@company.com,security@company.com
```

### Option 3: Custom SMTP
```bash
SMTP_HOST=your-smtp-server.com
SMTP_PORT=587
SMTP_USE_TLS=true
SMTP_USERNAME=your-username
SMTP_PASSWORD=your-password
EMAIL_RECIPIENTS=admin1@company.com,admin2@company.com,security@company.com
```

## 👥 Multiple Recipients Setup

### Security Team Configuration
```bash
# Multiple administrators (comma-separated)
EMAIL_RECIPIENTS=it-security@company.com,operations@company.com,management@company.com,emergency@company.com
```

### Role-Based Recipients
- **IT Security**: it-security@company.com
- **Operations**: operations@company.com  
- **Management**: management@company.com
- **Emergency**: emergency@company.com
- **On-call Engineer**: oncall@company.com

## 🔧 Environment Variables Setup

### Create/Update .env file
```bash
# SMTP Configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USE_TLS=true
SMTP_USERNAME=your-alerts@gmail.com
SMTP_PASSWORD=your-gmail-app-password

# Multiple Recipients (comma-separated)
EMAIL_RECIPIENTS=security@company.com,admin1@company.com,admin2@company.com,it-alerts@company.com
```

### Gmail App Password Setup
1. Go to: https://myaccount.google.com/apppasswords
2. Select "Mail" app
3. Enter "ICSS" as app name
4. Copy the 16-character password
5. Use this password in SMTP_PASSWORD

## 🛡️ Security Best Practices

### 1. Use App Passwords
- Never use your main Gmail password
- Create dedicated app password for ICSS
- Regularly rotate app passwords

### 2. Multiple Administrators
- Configure at least 3-4 recipients
- Include different departments (IT, Operations, Management)
- Ensure 24/7 coverage across time zones

### 3. Access Control
```bash
# Role-based email groups
EMAIL_RECIPIENTS=it-security@company.com,operations@company.com,management@company.com
```

### 4. Monitoring and Redundancy
- Set up email forwarding rules
- Configure mobile notifications
- Use distribution lists for automatic failover

## 🧪 Testing Email Configuration

### Test Different Scenarios
1. **Basic Test**: Send test email to all recipients
2. **Alert Test**: Trigger actual alert to verify delivery
3. **Failure Test**: Test with wrong credentials to see error handling

### Verification Checklist
- [ ] All recipients receive test emails
- [ ] Email format is readable
- [ ] Subject lines include severity levels
- [ ] Links and images work properly
- [ ] Spam filters are not blocking emails

## 🔄 Integration with ICSS

### Automatic Integration
The email system integrates automatically with:
- ✅ Alert generation from zone monitoring
- ✅ Critical severity alerts
- ✅ High risk notifications
- ✅ Custom alert types

### Email Content
Alerts include:
- 📊 Alert type and severity
- 🕒 Timestamp of alert
- 📍 Zone/location information
- 👥 People count and density
- 📸 Alert snapshot (if available)
- 🔗 Direct link to surveillance system

## 🚨 Production Deployment

### Production Checklist
- [ ] Configure SMTP credentials securely
- [ ] Set up multiple recipient emails
- [ ] Test email delivery to all recipients
- [ ] Verify spam filter settings
- [ ] Set up mobile notifications
- [ ] Document email procedures
- [ ] Train security team on alert response

### Monitoring Setup
```bash
# Add to monitoring dashboard
EMAIL_RECIPIENTS=security@company.com,ops-alerts@company.com,manager-alerts@company.com
```

## 🔍 Troubleshooting

### Common Issues

**Gmail Authentication Failed**
- Enable 2-factor authentication
- Generate new app password
- Check username spelling

**Emails Not Received**
- Check spam/junk folders
- Verify recipient email addresses
- Test SMTP connectivity

**Rate Limiting**
- Gmail: 100 emails/day for new accounts
- Use business Gmail for higher limits
- Implement email batching

**SSL/TLS Errors**
- Verify SMTP port (587 for TLS)
- Check firewall settings
- Confirm TLS is enabled

## 📞 Support Contacts

For email setup issues:
1. Check this guide first
2. Verify environment variables
3. Test with email client first
4. Contact IT security team

---

**🎉 Your ICSS system is now ready to send alerts to multiple administrators!**
