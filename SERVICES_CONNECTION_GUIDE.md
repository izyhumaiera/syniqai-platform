# 🔗 SYNIQ Services Connection Guide

## Overview

This guide explains how Kafka UI, MinIO, and Kafka Broker are connected in your SYNIQ data platform.

---

## 🌐 Service Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    SYNIQ Data Platform Services                  │
└─────────────────────────────────────────────────────────────────┘

        ┌──────────────────┐
        │   Kafka Broker   │
        │  127.0.0.1:9092  │
        │  (Data Streaming)│
        └────────┬─────────┘
                 │
         ┌───────┴────────┐
         │                │
    ┌────▼────┐     ┌────▼────────┐
    │Kafka UI │     │AI Processor │
    │ :8080   │     │   Python    │
    │(Monitor)│     │  Consumer   │
    └─────────┘     └─────┬───────┘
                          │
                     ┌────▼────┐
                     │  MinIO  │
                     │ :9000   │
                     │ :9001   │
                     │(Storage)│
                     └─────────┘
```

---

## 📋 Service Details

### 1. **Kafka Broker** (Message Streaming)
- **Purpose:** Core message broker for CDC events and data flow
- **Address:** `127.0.0.1:9092` (IPv4 explicit)
- **Mode:** KRaft (no Zookeeper needed)
- **Location:** `C:\kafka\kafka-4.2.0`
- **Config:** `C:\kafka\kafka-4.2.0\config\kraft\syniq-server.properties`
- **Status Check:** 
  ```powershell
  Test-NetConnection -ComputerName 127.0.0.1 -Port 9092
  ```

### 2. **Kafka UI** (Web Interface)
- **Purpose:** Monitor topics, messages, consumer groups
- **Web URL:** http://localhost:8080
- **JAR Location:** `C:\syniq\kafka-ui\kafka-ui.jar`
- **Config File:** `C:\syniq\kafka-ui\config.yml`
- **Connected to:** Kafka Broker at `127.0.0.1:9092`
- **Features:**
  - View all Kafka topics in real-time
  - Browse messages in topics
  - Monitor consumer lag
  - Create/delete topics
  - View partition distribution

### 3. **MinIO** (Object Storage)
- **Purpose:** S3-compatible storage for Bronze/Silver/Gold data layers
- **API Endpoint:** `localhost:9000` (for S3 client connections)
- **Console URL:** http://localhost:9001
- **Credentials:**
  - Access Key: `admin`
  - Secret Key: `password123`
- **Buckets:**
  - `syniqai-bronze` → Raw data from CDC
  - `syniqai-silver` → AI-processed structured data
  - `syniqai-gold` → Transformed analytics-ready data
  - `syniqai-iceberg` → Iceberg table metadata

---

## 🔌 Connection Flow

### CDC Data Flow Example

```
1. File uploaded to AWS S3
         ↓
2. S3 CDC Connector detects change
         ↓ (emits to Kafka)
3. Kafka Broker receives message on "bronze-s3" topic
         ↓ (visible in Kafka UI)
4. Bronze Ready Emitter consumes message
         ↓ (downloads from S3)
5. Saves to MinIO Bronze bucket
         ↓ (visible in MinIO Console)
6. Emits "bronze-ready" message to Kafka
         ↓
7. AI Processor consumes "bronze-ready"
         ↓ (processes with OpenRouter)
8. Saves results to MinIO Silver bucket
         ↓
9. Emits "silver-ready" to Kafka
```

---

## 🚀 Starting Services

### Option 1: Start All Services (Recommended)

```powershell
# Navigate to project root
cd "C:\Users\Local user\OneDrive - M Telecommunication Sdn Bhd\Desktop\TASK\Syniq"

# Run complete restart script
.\restart_all_native.ps1
```

This script:
1. ✅ Stops all running services
2. ✅ Starts Kafka Broker (127.0.0.1:9092)
3. ✅ Waits for Kafka to be ready
4. ✅ Starts AI Processor

### Option 2: Start Services Individually

#### Start Kafka Broker
```powershell
cd C:\kafka\kafka-4.2.0
.\bin\windows\kafka-server-start.bat .\config\kraft\syniq-server.properties
```

#### Start Kafka UI
```powershell
cd C:\syniq\kafka-ui
java -jar kafka-ui.jar --spring.config.additional-location=config.yml
```
Or use the batch file:
```powershell
cd C:\syniq\kafka-ui
.\start-kafka-ui.bat
```

#### Start MinIO
```powershell
# MinIO should already be running as a Windows service
# Check status:
Get-Service minio -ErrorAction SilentlyContinue

# Or start manually:
cd C:\syniq\minio
.\minio.exe server .\data --console-address ":9001"
```

---

## ✅ Verify Connections

### Quick Health Check Script

```powershell
# Check all services
python check_services.py
```

### Manual Verification

#### 1. Check Kafka Broker
```powershell
# Test connection
Test-NetConnection -ComputerName 127.0.0.1 -Port 9092

# List topics
cd C:\kafka\kafka-4.2.0
.\bin\windows\kafka-topics.bat --bootstrap-server 127.0.0.1:9092 --list
```

Expected topics:
- `bronze-s3`
- `bronze-mongodb`
- `bronze-ready`
- `silver-ready`
- `dlq-errors`

#### 2. Check Kafka UI
```powershell
# Open in browser
Start-Process "http://localhost:8080"
```

You should see:
- Cluster name: **SYNIQ-Local**
- Broker: **127.0.0.1:9092**
- All topics listed

#### 3. Check MinIO
```powershell
# Test API connection
$env:AWS_ACCESS_KEY_ID="admin"
$env:AWS_SECRET_ACCESS_KEY="password123"
aws s3 ls --endpoint-url http://localhost:9000

# Open console in browser
Start-Process "http://localhost:9001"
```

Expected buckets:
- ✅ syniqai-bronze
- ✅ syniqai-silver
- ✅ syniqai-gold
- ✅ syniqai-iceberg

---

## 🔧 Kafka UI Configuration

### Config File Location
`C:\syniq\kafka-ui\config.yml`

### Key Settings
```yaml
kafka:
  clusters:
    - name: SYNIQ-Local
      bootstrapServers: 127.0.0.1:9092  # ✅ IPv4 explicit
      
server:
  port: 8080  # Web UI port
  
spring:
  security:
    enabled: false  # No authentication for local dev
```

### Viewing Kafka Messages in UI

1. Open http://localhost:8080
2. Click **Topics** in sidebar
3. Select a topic (e.g., `bronze-ready`)
4. Click **Messages** tab
5. See real-time data flow

---

## 📊 Monitoring Dashboard URLs

| Service | URL | Purpose |
|---------|-----|---------|
| **Kafka UI** | http://localhost:8080 | Monitor Kafka topics and messages |
| **MinIO Console** | http://localhost:9001 | Browse S3 buckets and files |
| **SyniqAI GUI** | http://localhost:3000 | Main application interface |
| **Backend API** | http://localhost:5000 | Flask API endpoints |

---

## 🐛 Troubleshooting

### Issue: Kafka UI can't connect to broker

**Solution 1:** Verify Kafka is using 127.0.0.1
```powershell
# Check Kafka config
Select-String -Path "C:\kafka\kafka-4.2.0\config\kraft\syniq-server.properties" -Pattern "advertised.listeners"
# Should be: advertised.listeners=PLAINTEXT://127.0.0.1:9092
```

**Solution 2:** Restart Kafka UI
```powershell
# Stop java processes
Get-Process java -ErrorAction SilentlyContinue | Stop-Process -Force

# Restart Kafka broker first
cd C:\kafka\kafka-4.2.0
Start-Process .\bin\windows\kafka-server-start.bat -ArgumentList ".\config\kraft\syniq-server.properties" -WindowStyle Minimized

# Wait 10 seconds
Start-Sleep -Seconds 10

# Start Kafka UI
cd C:\syniq\kafka-ui
.\start-kafka-ui.bat
```

### Issue: MinIO not accessible

**Check if MinIO is running:**
```powershell
Test-NetConnection -ComputerName localhost -Port 9000
Test-NetConnection -ComputerName localhost -Port 9001
```

**Start MinIO manually:**
```powershell
cd C:\syniq\minio
.\minio.exe server .\data --console-address ":9001"
```

### Issue: "localhost" vs "127.0.0.1" confusion

**Why we use 127.0.0.1:**
- Windows can resolve `localhost` to IPv6 `::1`, causing connection delays
- Explicit IPv4 `127.0.0.1` avoids timeout issues
- All configs should use `127.0.0.1` for consistency

**Update .env file:**
```env
KAFKA_BOOTSTRAP_SERVERS=127.0.0.1:9092
MINIO_ENDPOINT=localhost:9000  # MinIO works with localhost
POSTGRES_HOST=localhost
```

---

## 📝 Testing the Connection

### End-to-End Test

1. **Upload a test file to Bronze:**
   ```powershell
   python upload_sample_data.py
   ```

2. **Watch in Kafka UI:**
   - Open http://localhost:8080
   - Navigate to **Topics** → `bronze-ready`
   - Click **Messages** tab
   - You should see the CDC event

3. **Verify in MinIO:**
   - Open http://localhost:9001
   - Login: `admin` / `password123`
   - Browse `syniqai-bronze` bucket
   - File should appear

4. **Check AI Processing:**
   - Watch AI Processor terminal logs
   - File should be processed
   - Results in `syniqai-silver` bucket

---

## 🎯 Quick Reference

### Ports in Use
| Port | Service |
|------|---------|
| 9092 | Kafka Broker |
| 8080 | Kafka UI |
| 9000 | MinIO API |
| 9001 | MinIO Console |
| 5432 | PostgreSQL |
| 5000 | Backend API |
| 3000 | Frontend UI |

### Key Directories
| Path | Purpose |
|------|---------|
| `C:\kafka\kafka-4.2.0` | Kafka installation |
| `C:\syniq\kafka-ui` | Kafka UI JAR and config |
| `C:\syniq\minio` | MinIO binary and data |
| `.\Kafka Integration\` | CDC and processors |
| `.\gui\` | Frontend and backend |

### Common Commands
```powershell
# Check all services
python check_services.py

# Restart everything
.\restart_all_native.ps1

# List Kafka topics
cd C:\kafka\kafka-4.2.0
.\bin\windows\kafka-topics.bat --bootstrap-server 127.0.0.1:9092 --list

# Test MinIO
aws s3 ls --endpoint-url http://localhost:9000
```

---

## ✅ Connection Checklist

- [ ] Kafka Broker running on 127.0.0.1:9092
- [ ] Kafka UI accessible at http://localhost:8080
- [ ] Kafka UI shows "SYNIQ-Local" cluster connected
- [ ] MinIO API responding on localhost:9000
- [ ] MinIO Console accessible at http://localhost:9001
- [ ] All 4 buckets visible in MinIO
- [ ] Topics visible in Kafka UI
- [ ] AI Processor consuming from `bronze-ready`
- [ ] PostgreSQL accepting connections on 5432

---

**Last Updated:** March 31, 2026  
**Platform Version:** SYNIQ Data Lakehouse v2.0  
**Configuration:** Native Windows Services (No Docker)
