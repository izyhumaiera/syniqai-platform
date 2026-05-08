# Quick Start Guide: CDC to Bronze Integration
## Testing Block 1 - Complete Setup

This guide will walk you through starting all components and testing the CDC pipeline.

---

## Prerequisites

### Check Services Status
```powershell
# Check if Kafka is running
Test-NetConnection -ComputerName localhost -Port 9092

# Check if MinIO is running
Test-NetConnection -ComputerName localhost -Port 9000

# Check if MongoDB is accessible (if using MongoDB CDC)
# (Should be configured in Kafka Integration/.env.mongodb)
```

---

## Step-by-Step Startup

### 1. Start Kafka (if not running)
```powershell
cd C:\kafka\kafka-4.2.0

# Terminal 1: Start Zookeeper
.\bin\windows\zookeeper-server-start.bat .\config\zookeeper.properties

# Terminal 2: Start Kafka
.\bin\windows\kafka-server-start.bat .\config\server.properties

# Wait 30-60 seconds for Kafka to fully start
```

### 2. Start MinIO (if not running)
MinIO should already be running based on your previous setup.

Verify:
```powershell
Invoke-WebRequest -Uri "http://localhost:9000/minio/health/live" -Method GET
```

### 3. Start Bronze Ready Emitter (CDC Consumer)
```powershell
# Open new terminal
cd "C:\Users\Local user\OneDrive - M Telecommunication Sdn Bhd\Desktop\TASK\Syniq\Kafka Integration"

# Start the emitter (this will consume from bronze-mongodb and bronze-s3)
python bronze_ready_emitter.py
```

**Expected Output:**
```
===============================================================================
Bronze Ready Emitter - Starting
===============================================================================
Kafka: localhost:9092
MinIO: localhost:9000/syniqai-bronze
Topics: bronze-mongodb, bronze-s3
Routing: bronze-ready, bronze-media-pending
===============================================================================
✓ Kafka consumer initialized: ['bronze-mongodb', 'bronze-s3'] → bronze-ready-emitter
✓ Kafka producer initialized → localhost:9092
✓ MinIO client connected: syniqai-bronze
✓ All clients initialized
🚀 Starting message consumption...
```

### 4. Start Backend API
```powershell
# Open new terminal
cd "C:\Users\Local user\OneDrive - M Telecommunication Sdn Bhd\Desktop\TASK\Syniq\gui\api"

# Activate Python environment if needed
# For example: ..\..\..\data lakehouse\syniq_env\Scripts\Activate.ps1

# Start FastAPI server
uvicorn backend:app --reload --port 8000
```

**Expected Output:**
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
...
✓ CDC Control routes loaded
✓ CDC Control API routes mounted at /api/cdc
```

### 5. Start Frontend
```powershell
# Open new terminal
cd "C:\Users\Local user\OneDrive - M Telecommunication Sdn Bhd\Desktop\TASK\Syniq\gui"

# Start Vite dev server
npm run dev
```

**Expected Output:**
```
VITE v... ready in ... ms
  ➜  Local:   http://localhost:3000/
  ➜  Network: use --host to expose
```

---

## Testing the CDC Pipeline

### Test 1: Check UI Status
1. Open browser: http://localhost:3000/cdc
2. Click on "MongoDB CDC" tab
3. Verify:
   - ✅ MongoDB CDC shows STOPPED (gray pill)
   - ✅ Kafka Broker shows CONNECTED (green pill)
   - ✅ MinIO Bronze shows status

### Test 2: Start MongoDB CDC
1. In MongoDB CDC tab, click **"Start CDC"** button
2. Verify popup shows: "✓ MongoDB CDC started! PID: 12345"
3. Status should update:
   - ✅ MongoDB CDC → RUNNING (green pill)
   - ✅ PID and Uptime displayed
   - ✅ LIVE indicator appears on events table

### Test 3: Verify Bronze Ready Emitter Console
Check the terminal running bronze_ready_emitter.py:

```
📨 Received event from bronze-mongodb
📥 Downloading file from MongoDB: 65f8a...
📊 File classification: image123.jpg → images → bronze-ready
✓ Wrote 45,231 bytes to MinIO: general/mongodb/images/image123.jpg
✅ File ingested: image123.jpg → general/mongodb/images/image123.jpg → bronze-ready (45,231 bytes)
📊 Stats: Processed=1, Written=1, Ready=1, Pending=0, Errors=0
```

### Test 4: Check MinIO Bronze Bucket
1. Open browser: http://localhost:9000
2. Login with credentials (admin / password123)
3. Navigate to **syniqai-bronze** bucket
4. Verify files appear under:
   - `general/mongodb/{file_type}/` for MongoDB files
   - `general/s3/{file_type}/` for S3 files

### Test 5: Verify Events Table in UI
In the MongoDB CDC tab:
1. Events table should auto-refresh every 10 seconds
2. New rows should appear with:
   - Time (e.g., "2:34:15 PM")
   - Operation (INSERT/UPDATE/DELETE)
   - Collection name
   - File Type (image/pdf/video/etc.)
   - Bronze MinIO Path
   - Routed To pill (green "Auto-Process" or amber "Media Pending")

### Test 6: Check Kafka Topics
Verify messages are flowing:

```powershell
cd C:\kafka\kafka-4.2.0

# Check bronze-mongodb topic
.\bin\windows\kafka-console-consumer.bat --bootstrap-server localhost:9092 --topic bronze-mongodb --from-beginning --max-messages 5

# Check bronze-ready topic (routing output)
.\bin\windows\kafka-console-consumer.bat --bootstrap-server localhost:9092 --topic bronze-ready --from-beginning --max-messages 5

# Check bronze-media-pending topic
.\bin\windows\kafka-console-consumer.bat --bootstrap-server localhost:9092 --topic bronze-media-pending --from-beginning --max-messages 5
```

### Test 7: API Endpoints
Test REST API directly:

```powershell
# Get MongoDB CDC status
Invoke-RestMethod -Uri "http://localhost:8000/api/cdc/mongodb/status" -Method GET | ConvertTo-Json

# Get recent MongoDB events
Invoke-RestMethod -Uri "http://localhost:8000/api/cdc/events?source=mongodb&limit=10" -Method GET | ConvertTo-Json

# Get S3 CDC status
Invoke-RestMethod -Uri "http://localhost:8000/api/cdc/s3/status" -Method GET | ConvertTo-Json
```

---

## Troubleshooting

### Issue: "NoBrokersAvailable" error
**Solution:** Kafka is not running. Start Kafka first.

```powershell
cd C:\kafka\kafka-4.2.0
.\bin\windows\kafka-server-start.bat .\config\server.properties
```

### Issue: Bronze Ready Emitter won't start
**Error:** `kafka-python not installed`
**Solution:**
```powershell
cd "Kafka Integration"
pip install kafka-python pymongo gridfs boto3 minio python-dotenv
```

### Issue: MongoDB connection error
**Error:** `MongoDB URI not configured`
**Solution:** Edit `Kafka Integration/.env.mongodb` and set:
```env
MONGODB_URI=mongodb+srv://user:pass@cluster.mongodb.net/
MONGODB_DATABASE=media_db
```

### Issue: Files not appearing in MinIO
**Check:**
1. Bronze Ready Emitter is running (check terminal output)
2. MongoDB CDC is publishing to bronze-mongodb topic (check Kafka console consumer)
3. MinIO credentials are correct in .env

```powershell
# Test MinIO connection
python -c "from minio import Minio; c = Minio('localhost:9000', 'admin', 'password123', secure=False); print('Buckets:', [b.name for b in c.list_buckets()])"
```

### Issue: Frontend shows "Failed to fetch CDC status"
**Solution:** Backend API is not running. Start it:
```powershell
cd gui/api
uvicorn backend:app --reload --port 8000
```

---

## Stop All Components

When done testing:

```powershell
# Stop Bronze Ready Emitter
Ctrl+C in bronze_ready_emitter.py terminal

# Stop MongoDB CDC via UI
Click "Stop CDC" button in MongoDB CDC tab

# Or stop via API
Invoke-RestMethod -Uri "http://localhost:8000/api/cdc/mongodb/stop" -Method POST

# Stop Backend
Ctrl+C in backend terminal

# Stop Frontend
Ctrl+C in frontend terminal

# Keep Kafka running (it's shared infrastructure)
```

---

## Success Indicators

✅ **Complete Success Checklist:**
- [ ] Kafka broker running on port 9092
- [ ] MinIO running on port 9000
- [ ] Bronze Ready Emitter consuming from Kafka
- [ ] Backend API running on port 8000
- [ ] Frontend UI accessible at http://localhost:3000/cdc
- [ ] MongoDB CDC can be started/stopped via UI
- [ ] Events appear in live events table
- [ ] Files written to MinIO syniqai-bronze bucket
- [ ] Routing events published to bronze-ready or bronze-media-pending

---

## Next Steps After Successful Test

Once all tests pass:

1. **Production Configuration**
   - Update .env files with production credentials
   - Set up log rotation for bronze_ready_emitter.py
   - Configure systemd/Windows services for auto-start

2. **Monitoring Setup**
   - Add Kafka topic lag monitoring
   - Track bronze_ready_emitter.py uptime
   - Alert on file download failures

3. **Silver Layer Integration**
   - Build Silver CDC Processor to consume bronze-ready topic
   - Implement Spark normalization for different file types
   - Write to syniqai-silver/ bucket

4. **Media Pipeline**
   - Handle bronze-media-pending files
   - Implement user-triggered processing
   - Transcription and embedding for audio/video

---

## Support

If you encounter issues not covered here:
1. Check logs in `Kafka Integration/logs/`
2. Review backend logs in terminal
3. Inspect browser console for frontend errors
4. Verify all prerequisites are met

**All components are now ready for end-to-end testing!** 🚀
