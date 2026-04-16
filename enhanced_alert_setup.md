# Enhanced Alert System Setup Guide

## 🎯 Overview

The ICSS Enhanced Alert System provides real-time alert monitoring with Supabase integration, Cloudinary image uploads, and email control.

## 🔧 Features Implemented

### 1️⃣ 🔴 Live Alert Log (Supabase Integration)
- ✅ Real-time alert fetching from Supabase `alerts` table
- ✅ Auto-refresh every 3 seconds
- ✅ Color-coded severity display (CRITICAL→Red, HIGH→Orange, etc.)
- ✅ Alert snapshots with image thumbnails

### 2️⃣ 📩 Email Toggle (ON/OFF)
- ✅ Email toggle switch in Alert Tab
- ✅ Settings stored in Supabase `settings` table
- ✅ Real-time toggle updates

### 3️⃣ 📸 Snapshot Capture + Cloudinary Upload
- ✅ Automatic frame capture on alert
- ✅ Cloudinary image upload integration
- ✅ Image URLs stored with alerts

### 4️⃣ ⏱️ Enhanced Alert Insert
- ✅ Modified alert insertion with full schema support
- ✅ Timestamp, severity, image_url, email_sent fields
- ✅ Backward compatibility with existing tables

### 5️⃣ 🚫 Clean Email Handling
- ✅ Removed direct email sending from Streamlit
- ✅ Email handled by Supabase Edge Functions
- ✅ Settings-based email control

## 📦 Required Environment Variables

Add these to your `.env` file:

```bash
# Supabase Configuration
SUPABASE_URL=your_supabase_url
SUPABASE_ANON_KEY=your_supabase_anon_key

# Cloudinary Configuration (for snapshot uploads)
CLOUDINARY_CLOUD_NAME=your_cloudinary_cloud_name
CLOUDINARY_API_KEY=your_cloudinary_api_key
CLOUDINARY_API_SECRET=your_cloudinary_api_secret
```

## 🗄️ Database Schema

### Enhanced Alerts Table
```sql
CREATE TABLE IF NOT EXISTS alerts (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp   TIMESTAMPTZ DEFAULT NOW(),
    type        TEXT NOT NULL,
    severity    TEXT NOT NULL,
    zone        TEXT,
    count       INTEGER,
    density     FLOAT8,
    message     TEXT NOT NULL,
    image_url   TEXT,
    email_sent  BOOLEAN DEFAULT FALSE
);
```

### Settings Table (for email toggle)
```sql
CREATE TABLE IF NOT EXISTS settings (
    key        TEXT PRIMARY KEY,
    value      TEXT NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

## 🚀 Installation

Install required packages:
```bash
pip install cloudinary pandas
```

## 🧪 Testing

1. **Start the ICSS application**
2. **Navigate to the "🚨 Alerts" tab**
3. **Verify features:**
   - Live alert log shows real-time data
   - Email toggle works and persists
   - Service status shows connected services
   - Historical alerts display properly

4. **Test alert generation:**
   - Start video feed in "🎥 Live Feed" tab
   - Trigger alerts by exceeding crowd thresholds
   - Check if snapshots are uploaded to Cloudinary
   - Verify alerts appear in Supabase

## 🔍 Troubleshooting

### Supabase Connection Issues
- Verify SUPABASE_URL and SUPABASE_ANON_KEY in .env
- Check if tables exist in your Supabase project
- Run `supabase_schema.sql` if needed

### Cloudinary Upload Issues
- Verify Cloudinary credentials in .env
- Check Cloudinary folder permissions
- Monitor error logs in console

### Email Toggle Not Working
- Ensure `settings` table exists in Supabase
- Check Row Level Security policies
- Verify database write permissions

## 📊 Performance Notes

- Alert caching reduces database queries (5-second cache)
- Image uploads are asynchronous and non-blocking
- Auto-refresh can be disabled for better performance
- Fallback schemas ensure compatibility with existing tables

## 🔄 Migration from Old System

The enhanced system is backward compatible:
- Existing `insert_alert()` calls continue to work
- Old alert tables are supported with fallback logic
- No breaking changes to existing detection logic

## 🎉 Benefits

- **Real-time monitoring** with live updates
- **Visual evidence** with alert snapshots
- **Centralized settings** stored in database
- **Scalable architecture** with cloud services
- **Clean separation** of concerns (UI vs email handling)
