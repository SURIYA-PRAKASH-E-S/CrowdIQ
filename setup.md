# Setup Guide

Complete setup instructions for CrowdIQ — Intelligent Crowd Surveillance System.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Environment Configuration](#environment-configuration)
4. [Firebase Setup](#firebase-setup)
5. [Email/SMTP Setup](#emailsmtp-setup)
6. [Mobile Camera Setup](#mobile-camera-setup)
7. [Cloudinary Setup](#cloudinary-setup)
8. [Running the Application](#running-the-application)
9. [Troubleshooting](#troubleshooting)

---

## Prerequisites

- **Python 3.8 or higher** (Python 3.10 recommended)
- **Git** (for cloning the repository)
- **Webcam** or video files for testing
- **Google Account** (for Firebase and Gmail)
- **WiFi Network** (for mobile camera streaming)

---

## Installation

### Step 1: Clone the Repository

```bash
git clone https://github.com/SURIYA-PRAKASH-E-S/CrowdIQ.git
cd CrowdIQ
```

### Step 2: Create Virtual Environment

```bash
# Create virtual environment
python -3.10 -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

**Core Dependencies:**
- streamlit>=1.28.0
- streamlit-webrtc>=1.0.0
- opencv-python>=4.8.0
- ultralytics>=8.0.0
- numpy>=1.24.0
- av>=10.0.0
- firebase-admin==6.5.0
- plotly>=5.15.0
- pandas>=2.0.0
- torch>=2.0.0
- torchvision>=0.15.0
- scipy>=1.10.0
- scikit-learn>=1.2.0
- matplotlib>=3.7.0
- seaborn>=0.12.0

### Step 4: Verify Models

Ensure YOLO models are in the `model/` directory:
- `model/yolo11l.pt` (51MB)
- `model/V8l-haj.pt` (87MB)

If models are missing, download them from your training source or the provided links.

---

## Environment Configuration

### Step 1: Create .env File

```bash
cp env_example.txt .env
```

### Step 2: Edit .env File

The `.env` file contains all sensitive configuration. Edit it with your credentials:

```env
# Firebase Realtime Database
FIREBASE_DATABASE_URL=https://your-project-id-default-rtdb.firebaseio.com
GOOGLE_APPLICATION_CREDENTIALS=firebase-service-account.json

# SMTP Email Configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USE_TLS=true
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password

# Cloudinary (for alert snapshots)
CLOUDINARY_CLOUD_NAME=your-cloud-name
CLOUDINARY_API_KEY=your-api-key
CLOUDINARY_API_SECRET=your-api-secret
```

**Security Note:** Never commit `.env` or `firebase-service-account.json` to version control.

---

## Firebase Setup

### Overview

CrowdIQ uses Firebase Realtime Database for cloud storage of analytics data and alert history.

### Step 1: Create a Firebase Project

1. Go to [Firebase Console](https://console.firebase.google.com)
2. Click **"Add project"**
3. Enter a project name (e.g., `crowdiq-surveillance`)
4. Accept the Firebase terms and conditions
5. **Important**: Disable Google Analytics for this project (not needed)
6. Click **"Create project"**
7. Wait for the project to be created

### Step 2: Enable Realtime Database

1. In the Firebase Console, select your project
2. In the left sidebar, click **"Build"** → **"Realtime Database"**
3. Click **"Create Database"**
4. Select a location (choose closest to your users)
5. Click **"Next"**
6. **Security Rules**: Select **"Start in test mode"**
7. Click **"Enable"**

### Step 3: Configure Database Rules

#### For Development (Test Mode)

```json
{
  "rules": {
    ".read": true,
    ".write": true
  }
}
```

**Warning**: Test mode allows anyone to read/write. Only for development!

#### For Production (Recommended)

1. Go to **Realtime Database** → **Rules** tab
2. Replace with:

```json
{
  "rules": {
    ".read": true,
    ".write": true,
    "crowd_metrics": {
      ".indexOn": ["timestamp"],
      "$pushId": {
        ".read": true,
        ".write": true
      }
    },
    "alerts": {
      ".indexOn": ["timestamp"],
      "$pushId": {
        ".read": true,
        ".write": true
      }
    }
  }
}
```

3. Click **"Publish"**

### Step 4: Get Database URL

1. Go to **Project Settings** (gear icon)
2. Note your **Project ID** (e.g., `crowdiq-surveillance-12345`)
3. Your Database URL: `https://<project-id>-default-rtdb.firebaseio.com`

### Step 5: Download Service Account Key

1. Go to **Project Settings** → **Service Accounts**
2. Click **"Generate new private key"**
3. Click **"Generate key"**
4. Rename the file to `firebase-service-account.json`
5. Move to project root (same level as `app.py`)

**Security Warning**: Never commit this file to version control!

### Step 6: Update .env File

```env
FIREBASE_DATABASE_URL=https://your-project-id-default-rtdb.firebaseio.com
GOOGLE_APPLICATION_CREDENTIALS=firebase-service-account.json
```

Replace `your-project-id` with your actual project ID.

### Step 7: Test Connection

Run the application:

```bash
streamlit run app.py
```

Check the **Cloud DB** tab to verify Firebase connection.

---

## Email/SMTP Setup

### Overview

CrowdIQ supports multi-admin email notifications via SMTP. Gmail is recommended.

### Step 1: Enable 2-Factor Authentication

1. Go to [Google Account Settings](https://myaccount.google.com/security)
2. Enable **2-Step Verification**

### Step 2: Generate App Password

1. Go to [App Passwords](https://myaccount.google.com/apppasswords)
2. Select app: **"Mail"** and device: **"Other (Custom name)"**
3. Enter name: **"CrowdIQ Alerts"**
4. Click **"Generate"**
5. Copy the 16-character password

### Step 3: Configure SMTP in .env

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USE_TLS=true
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-16-char-app-password
```

### Step 4: Configure Recipients

Add multiple administrators (comma-separated):

```env
EMAIL_RECIPIENTS=admin1@company.com,admin2@company.com,security@company.com
```

### Step 5: Configure in App UI

1. Open CrowdIQ application
2. Go to **"Alerts"** tab
3. Find **"Email Configuration"** section
4. Enter SMTP settings
5. Add recipient emails
6. Click **"Save Email Configuration"**
7. Click **"Send Test Email"** to verify

### Alternative Email Providers

**Outlook:**
```env
SMTP_HOST=smtp-mail.outlook.com
SMTP_PORT=587
SMTP_USE_TLS=true
```

**Custom SMTP:**
```env
SMTP_HOST=your-smtp-server.com
SMTP_PORT=your-port
SMTP_USE_TLS=true
```

---

## Mobile Camera Setup

### Overview

Use your phone as a camera via IP Webcam app over WiFi.

### Step 1: Install IP Webcam App

**Android:**
- Download "IP Webcam" from Google Play Store

**iOS:**
- Download "IP Webcam" from App Store

### Step 2: Configure App Settings

1. Open IP Webcam app
2. Go to **Settings**
3. Configure:
   - **Username/Password**: (Optional) Set for security
   - **Resolution**: 640x480 or higher
   - **FPS**: 30 or higher
   - **Port**: 8080 (default)

### Step 3: Start Server

1. Tap **"Start Server"** in the app
2. Note the IP address (e.g., `192.168.1.5:8080`)
3. Ensure phone and PC are on same WiFi network

### Step 4: Connect in CrowdIQ

1. Open CrowdIQ application
2. Go to sidebar → **"Mobile Camera"** section
3. Enter the IP address from Step 3
4. Click **"Connect"**
5. In **Live Feed** tab, select **"Mobile Camera (IP Webcam)"**

### Troubleshooting Mobile Camera

| Issue | Solution |
|-------|----------|
| Connection failed | Check phone and PC on same WiFi |
| Black screen | Try different stream URL in settings |
| Lag | Reduce resolution or FPS in app |

---

## Cloudinary Setup

### Overview

Cloudinary is used for storing alert snapshots with automatic CDN delivery.

### Step 1: Create Cloudinary Account

1. Go to [Cloudinary](https://cloudinary.com)
2. Sign up for free account
3. Verify your email

### Step 2: Get API Credentials

1. Go to **Dashboard** in Cloudinary Console
2. Note:
   - **Cloud Name** (e.g., `your-cloud-name`)
   - **API Key**
   - **API Secret**

### Step 3: Configure in .env

```env
CLOUDINARY_CLOUD_NAME=your-cloud-name
CLOUDINARY_API_KEY=your-api-key
CLOUDINARY_API_SECRET=your-api-secret
```

### Step 4: Test Upload

The system will automatically test Cloudinary when the first alert is triggered. You can also test via the **Alerts** tab in the app.

---

## Running the Application

### Start the Application

```bash
streamlit run app.py
```

### Access the Application

After running, you'll see:

```
You can now view your Streamlit app in your browser.

Local URL: http://localhost:8501
Network URL: http://192.168.1.4:8501
```

Open **http://localhost:8501** in your browser.

### Quick Start Guide

1. **Select Input Mode** (Tab 1: Live Feed)
   - Choose "Webcam (Live)" for real-time camera
   - Choose "Mobile Camera (IP Webcam)" for phone camera
   - Or "Upload Video" to process a video file

2. **Start Processing**
   - Click "Start" to begin video processing
   - View real-time detections and overlays

3. **Monitor Analytics** (Tab 2: Analytics)
   - View people count, density, flow direction
   - Check risk level and alerts

4. **View Zone Analysis** (Tab 3: Map Area)
   - Visualize zone-based risk distribution
   - Monitor overcrowded areas

5. **View Historical Data** (Tab 4: Cloud DB)
   - Check stored analytics from Firebase
   - View trends and statistics

6. **Configure Settings** (Tab 5: Controls)
   - Enable/disable detection features
   - Adjust thresholds and parameters

7. **Manage Alerts** (Tab 6: Alerts)
   - View active and historical alerts
   - Configure alert thresholds

---

## Troubleshooting

### Common Issues

#### 1. Model Loading Errors

**Symptoms:** Error loading YOLO models

**Solutions:**
- Verify model files exist in `model/` directory
- Check file sizes: `yolo11l.pt` (51MB), `V8l-haj.pt` (87MB)
- Re-download models if corrupted
- Check file permissions

#### 2. Webcam Not Working

**Symptoms:** Camera not detected or black screen

**Solutions:**
- Check browser permissions (allow camera access)
- Try different browser (Chrome recommended)
- Verify webcam is not used by another application
- Check if webcam is properly connected
- Try "Mobile Camera" or "Upload Video" as alternative

#### 3. Low FPS / Slow Processing

**Symptoms:** Video lag or slow frame rate

**Solutions:**
- Disable Deep SORT tracking (Controls tab)
- Use single YOLO model (v11 only)
- Disable CSRNet (Controls tab)
- Reduce frame resolution
- Use GPU if available (CUDA)

#### 4. Firebase Connection Errors

**Symptoms:** "Firebase is not configured" warning

**Solutions:**
- Check `FIREBASE_DATABASE_URL` in .env
- Ensure `firebase-service-account.json` exists in project root
- Verify Firebase project is active
- Check network connectivity
- Review console for detailed error messages

#### 5. Email Not Sending

**Symptoms:** Alert emails not received

**Solutions:**
- Enable 2FA on Gmail account
- Generate App Password (not regular password)
- Verify SMTP credentials in .env
- Check spam folder
- Test email configuration in Alerts tab
- Verify recipient email addresses

#### 6. Mobile Camera Connection Failed

**Symptoms:** Cannot connect to phone camera

**Solutions:**
- Ensure phone and PC on same WiFi network
- Check IP address is correct
- Verify IP Webcam app is running
- Try different port in app settings
- Check firewall settings

#### 7. Cloudinary Upload Errors

**Symptoms:** Alert snapshots not uploading

**Solutions:**
- Verify Cloudinary credentials in .env
- Check Cloudinary account status
- Verify API key and secret are correct
- Check internet connection
- Test via Alerts tab

#### 8. "Thread 'async_media_processor' missing ScriptRunContext"

**Symptoms:** Warning in console

**Solution:** This warning can be ignored - it's expected behavior in async video processing.

### Performance Optimization

| Issue | Solution |
|-------|----------|
| High CPU usage | Disable CSRNet, use single model |
| High memory usage | Reduce frame resolution |
| Slow database writes | Firebase writes are async, local cache used |
| Lag in UI | Reduce frame rate, disable heavy features |

### Debug Mode

Enable debug output by setting environment variable:

```bash
export STREAMLIT_LOGGER_LEVEL=debug  # Linux/macOS
set STREAMLIT_LOGGER_LEVEL=debug     # Windows
```

---

## Additional Resources

- [Streamlit Documentation](https://docs.streamlit.io)
- [YOLO Documentation](https://docs.ultralytics.com)
- [Firebase Documentation](https://firebase.google.com/docs)
- [Cloudinary Documentation](https://cloudinary.com/documentation)

---

## Support

For issues or questions:
1. Check this setup guide
2. Check the Troubleshooting section
3. Verify all dependencies are installed
4. Check model files exist
5. Review console output for errors
6. Open an issue on GitHub

---

## Security Best Practices

1. **Never commit** `.env` or `firebase-service-account.json` to version control
2. **Use different environments** for development and production
3. **Rotate API keys** and passwords regularly
4. **Enable 2FA** on all accounts
5. **Use strong passwords** for SMTP and Cloudinary
6. **Monitor Firebase usage** and set up alerts
7. **Keep dependencies updated** for security patches

---

## License

This setup guide is part of CrowdIQ, licensed under MIT License.
