# MinIO Installation Guide

**Date**: April 13, 2026  
**Status**: MinIO not installed - follow steps below

---

## The download failed due to connection issues. Here's how to install manually:

---

## STEP 1: Download MinIO

### Method A: Direct Download Link
Download directly from:
```
https://dl.min.io/server/minio/release/windows-amd64/minio.exe
```

### Method B: Official Website
1. Visit: https://min.io/download
2. Click the **Windows** tab
3. Download `minio.exe`

---

## STEP 2: Install MinIO

Open PowerShell and run:

```powershell
# Create MinIO directory
New-Item -ItemType Directory -Path "C:\minio" -Force

# Create data directory
New-Item -ItemType Directory -Path "C:\minio\data" -Force
```

Then:
1. Move the downloaded `minio.exe` to `C:\minio\`
2. Verify the file exists at: `C:\minio\minio.exe`

---

## STEP 3: Start MinIO

### Option A: Manual Start
Open PowerShell and run:

```powershell
C:\minio\minio.exe server C:\minio\data --console-address ":9001"
```

### Option B: Use START_ALL_SERVICES.ps1
The startup script will automatically detect and start MinIO:

```powershell
.\START_ALL_SERVICES.ps1
```

---

## STEP 4: Access MinIO

Once started, access MinIO at:

- **API Endpoint**: http://localhost:9000
- **Web Console**: http://localhost:9001

### Default Credentials:
- **Username**: `minioadmin`
- **Password**: `minioadmin`

---

## Creating Buckets for SyniqAI

After logging into the MinIO console (http://localhost:9001):

1. Click **"Buckets"** in the left menu
2. Click **"Create Bucket"**
3. Create these three buckets:
   - `syniqai-bronze` (for raw ingestion)
   - `syniqai-silver` (for processed data)
   - `syniqai-gold` (for analytics)

---

## Quick Commands Reference

```powershell
# Check if MinIO is installed
Test-Path "C:\minio\minio.exe"

# Start MinIO
C:\minio\minio.exe server C:\minio\data --console-address ":9001"

# Stop MinIO (if running in background)
Get-Process minio | Stop-Process

# Access web console
Start-Process "http://localhost:9001"
```

---

## Troubleshooting

### MinIO won't start
- Make sure port 9000 and 9001 are not in use
- Check Windows Firewall isn't blocking MinIO
- Run PowerShell as Administrator

### Can't access console
- Wait 5-10 seconds after starting
- Try: http://127.0.0.1:9001
- Check MinIO process is running: `Get-Process minio`

---

## Note

**MinIO is optional for basic testing.** The following will work without it:
- ✓ FastAPI Backend
- ✓ PostgreSQL database
- ✓ CDC pipeline
- ✓ SQL queries

You **need** MinIO for:
- ✗ File ingestion (Bronze layer)
- ✗ AI processing of files
- ✗ Unstructured data pipeline

---

**After installation, run `.\START_ALL_SERVICES.ps1` again to start all services including MinIO.**

