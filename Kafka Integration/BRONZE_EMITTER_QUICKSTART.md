# Bronze Ready Emitter - Quick Start Guide

## What Was Created

### 1. Main Service
- **`bronze_ready_emitter.py`** - The main consumer/emitter service
  - Consumes from `bronze-mongodb` and `bronze-s3` topics
  - Routes messages to `bronze-ready` or `bronze-media-pending`
  - Uses environment variables for configuration

### 2. Startup Script
- **`start_bronze_emitter.bat`** - Windows batch script to start the service
  - Loads environment variables from `.env`
  - Starts the emitter and displays logs

### 3. Test Script
- **`test_bronze_emitter.py`** - Test the routing logic
  - Sends sample messages to bronze topics
  - Verifies routing to correct downstream topics
  - Displays summary of message routing

### 4. Documentation
- **`BRONZE_READY_EMITTER_README.md`** - Comprehensive documentation
  - Architecture overview
  - Message formats
  - Configuration options
  - Monitoring and troubleshooting

### 5. Configuration Template
- **`.env.example`** - Example environment variable file
  - Shows all configurable options
  - Default values documented

## Quick Start (3 Steps)

### Step 1: Verify Prerequisites

```powershell
# 1. Check Kafka is running
Test-NetConnection localhost -Port 9092

# 2. Check MinIO is accessible
Test-NetConnection localhost -Port 9000

# 3. Verify .env file exists
cd "Kafka Integration"
Get-Content .env | Select-String "MINIO_ENDPOINT"
```

### Step 2: Start the Emitter

```powershell
cd "Kafka Integration"
.\start_bronze_emitter.bat
```

You should see:
```
============================================================
 Bronze Ready Emitter - Starting
============================================================
2024-01-01 10:00:00 - BronzeReadyEmitter - INFO - Kafka consumer initialized
2024-01-01 10:00:00 - BronzeReadyEmitter - INFO - Kafka producer initialized
2024-01-01 10:00:00 - BronzeReadyEmitter - INFO - MinIO client connected
2024-01-01 10:00:00 - BronzeReadyEmitter - INFO - Starting message consumption...
```

### Step 3: Test the Routing (Optional)

Open a new terminal:

```powershell
cd "Kafka Integration"
python test_bronze_emitter.py
```

This will:
1. Send test messages to `bronze-mongodb` and `bronze-s3`
2. Wait for the emitter to route them
3. Verify messages appear in correct topics

## How It Fits Into Your Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│  UPSTREAM COMPONENTS (Already Existing)                        │
└─────────────────────────────────────────────────────────────────┘

1. custom_connectors.py
   │ MongoDB Change Streams ──▶ publishes to bronze-mongodb
   │ S3 Polling ──▶ publishes to bronze-s3

2. mongodb_stream_ingestor.py
   │ Streams MongoDB docs ──▶ syniqai-bronze/mongodb/...

3. s3_file_ingestor.py
   │ Streams S3 files ──▶ syniqai-bronze/s3/...

                        ▼

┌─────────────────────────────────────────────────────────────────┐
│  NEW COMPONENT (Bronze Ready Emitter)                          │
└─────────────────────────────────────────────────────────────────┘

bronze_ready_emitter.py
│  Consumes: bronze-mongodb, bronze-s3
│  Detects: file type from extension
│  Routes:
│    ▶ PDF, TXT, Images ──▶ bronze-ready (auto-process)
│    ▶ Audio, Video ──▶ bronze-media-pending (wait for user)

                        ▼

┌─────────────────────────────────────────────────────────────────┐
│  DOWNSTREAM COMPONENTS (To Be Built)                           │
└─────────────────────────────────────────────────────────────────┘

5. AI Processing Service (listens to bronze-ready)
   │ Auto-processes PDFs, text, images
   │ Publishes results to silver layer

6. User Trigger Service (manages bronze-media-pending)
   │ Displays pending audio/video files
   │ Allows manual user trigger for processing
```

## Real-World Example

### Scenario: User uploads a PDF to S3

1. **S3 Connector** detects new file `documents/report.pdf`
   ```json
   {
     "op": "create",
     "source": {"bucket": "my-bucket", "ts_ms": 1640000000000},
     "file": {"key": "documents/report.pdf", "size": 1024000}
   }
   ```
   Published to: `bronze-s3` ✓

2. **S3 File Ingestor** downloads and stores in MinIO
   ```
   syniqai-bronze/s3/my-bucket/documents/report.pdf
   ```
   File stored in MinIO ✓

3. **Bronze Ready Emitter** consumes message
   - Detects: file_type = "pdf"
   - Routes to: `bronze-ready`
   ```json
   {
     "source": "s3",
     "file_type": "pdf",
     "bronze_minio_key": "syniqai-bronze/s3/my-bucket/documents/report.pdf",
     "object_key": "s3/my-bucket/documents/report.pdf"
   }
   ```
   Event emitted ✓

4. **AI Processing Service** receives from `bronze-ready`
   - Extracts text from PDF
   - Runs AI analysis
   - Stores results in Silver layer
   Processing complete ✓

### Scenario: User uploads a video to MongoDB

1. **MongoDB Connector** detects new document with video reference
   ```json
   {
     "op": "insert",
     "source": {"db": "media", "collection": "videos"},
     "after": {"_id": "video123", "path": "training_video.mp4"}
   }
   ```
   Published to: `bronze-mongodb` ✓

2. **MongoDB Stream Ingestor** stores in MinIO
   ```
   syniqai-bronze/mongodb/media_videos/1640000000000_video123.json
   ```
   (Note: actual video file stored separately)

3. **Bronze Ready Emitter** consumes message
   - Detects: file_type = "video" (from .mp4 extension)
   - Routes to: `bronze-media-pending`
   ```json
   {
     "source": "mongodb",
     "file_type": "video",
     "bronze_minio_key": "syniqai-bronze/mongodb/media_videos/...",
     "object_key": "mongodb/media_videos/..."
   }
   ```
   Event emitted ✓

4. **User Trigger Service** receives from `bronze-media-pending`
   - Displays video in pending queue
   - Waits for user to trigger processing
   - User reviews and approves
   Awaiting user action ⏸

## Environment Variables Used

The emitter reads from `.env` file in `Kafka Integration/`:

```env
# Required
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=admin
MINIO_SECRET_KEY=password123

# Optional (has defaults)
BRONZE_BUCKET=syniqai-bronze
MINIO_SECURE=false
```

Your existing `.env` file already has these values! ✓

## Monitoring

### View Live Logs

When running via `start_bronze_emitter.bat`, logs appear in the console:

```
2024-01-01 10:00:00 - INFO - ✓ Routed to bronze-ready: pdf | s3/my-bucket/report.pdf
2024-01-01 10:00:01 - INFO - ⏸ Routed to bronze-media-pending: video | mongodb/media_videos/...
2024-01-01 10:00:05 - INFO - Stats: Processed=100, Ready=87, Pending=13, Errors=0
```

### Check Message Counts

```powershell
# View messages in bronze-ready
cd C:\kafka\kafka-4.2.0
.\bin\windows\kafka-console-consumer.bat --bootstrap-server localhost:9092 --topic bronze-ready --from-beginning --max-messages 10

# View messages in bronze-media-pending
.\bin\windows\kafka-console-consumer.bat --bootstrap-server localhost:9092 --topic bronze-media-pending --from-beginning --max-messages 10
```

### Check Consumer Group Status

```powershell
cd C:\kafka\kafka-4.2.0
.\bin\windows\kafka-consumer-groups.bat --bootstrap-server localhost:9092 --describe --group bronze-ready-emitter
```

Output shows:
- Current offset (messages processed)
- Log end offset (total messages)
- Lag (messages waiting)

## Troubleshooting

### No messages being routed

**Check 1:** Is the emitter running?
```powershell
Get-Process | Where-Object {$_.Name -eq "python"} | Select-Object Id,Name,StartTime
```

**Check 2:** Are messages in bronze topics?
```powershell
cd C:\kafka\kafka-4.2.0
.\bin\windows\kafka-console-consumer.bat --bootstrap-server localhost:9092 --topic bronze-mongodb --max-messages 1
```

**Check 3:** Are upstream connectors running?
- custom_connectors.py (MongoDB/S3 CDC)
- mongodb_stream_ingestor.py
- s3_file_ingestor.py

### Connection errors

**Kafka connection failed:**
```
Failed to initialize Kafka consumer: NoBrokersAvailable
```
→ Start Kafka: `C:\kafka\kafka-4.2.0\bin\windows\kafka-server-start.bat`

**MinIO connection failed:**
```
Failed to initialize MinIO client: MaxRetryError
```
→ Start MinIO: `C:\syniq\minio\start-minio.bat`

### Messages routing to wrong topic

Check file type detection in logs:
```
DEBUG - Extracted metadata: file_type='video', object_key='...'
```

If wrong, update `FILE_TYPE_EXTENSIONS` in `bronze_ready_emitter.py`

## Next Steps

1. ✅ **Emitter created** - Bronze routing layer complete
2. ⏭️ **Build AI Processing Service** - Consume from `bronze-ready`
3. ⏭️ **Build User Trigger UI** - Manage `bronze-media-pending`
4. ⏭️ **Add Error Handling** - Dead letter queue for failed processing
5. ⏭️ **Add Monitoring** - Prometheus metrics, Grafana dashboards

## Files Reference

All created files are in `Kafka Integration/`:

```
Kafka Integration/
├── bronze_ready_emitter.py           ← Main service
├── start_bronze_emitter.bat          ← Startup script (Windows)
├── test_bronze_emitter.py            ← Test script
├── BRONZE_READY_EMITTER_README.md    ← Full documentation
└── .env.example                      ← Configuration template
```

## Support

For issues or questions:
1. Check logs in the console
2. Review BRONZE_READY_EMITTER_README.md
3. Run test_bronze_emitter.py to verify setup
4. Check Kafka and MinIO are running

---

**Status:** ✅ Bronze Ready Emitter Complete and Ready to Use!
