# Bronze Ready Emitter - GUI Integration Test Guide

## ✅ What Was Integrated

### Backend (API)
1. **bronze_ready_routes.py** - New API routes at `/api/bronze-ready/`
   - `GET /status` - Check emitter running status
   - `GET /items` - Get ready queue items
   - `GET /media-pending` - Get media pending items
   - `POST /trigger` - Manually trigger media file
   - `POST /start` - Start emitter service
   - `POST /stop` - Stop emitter service

2. **backend.py** - Router registered and mounted

### Frontend (GUI)
1. **BronzeReadyPanel.jsx** - New React component
   - Emitter status display with start/stop controls
   - "Ready Queue" tab - Auto-processable files
   - "Media Pending" tab - Media files requiring approval
   - Manual trigger button for media files

2. **Bronze.jsx** - Component integrated into Bronze page

---

## 🧪 Testing Steps

### Prerequisites

1. **Kafka Running**
   ```powershell
   Test-NetConnection localhost -Port 9092
   ```
   Should show: `TcpTestSucceeded : True`

2. **MinIO Running**
   ```powershell
   Test-NetConnection localhost -Port 9000
   ```
   Should show: `TcpTestSucceeded : True`

3. **GUI Backend Running**
   ```powershell
   cd gui/api
   python backend.py
   ```
   Should show: `✓ Bronze Ready Emitter routes loaded`

4. **GUI Frontend Running**
   ```powershell
   cd gui
   npm run dev
   ```
   Should open at `http://localhost:3000` or `http://localhost:5173`

---

### Test 1: View Bronze Ready Panel

1. Open browser: `http://localhost:3000` (or your Vite port)
2. Navigate to **Bronze** page
3. Scroll down - you should see a new section: **"Bronze Ready Emitter"**
4. Verify you see:
   - ✅ Status indicator (red dot = not running)
   - ✅ Start/Stop/Refresh buttons
   - ✅ Two tabs: "Ready Queue" and "Media Pending"

**Expected Result:**
- Status shows "Not running"
- Kafka availability indicator shows status
- Both queues show "No items" (empty state)

---

### Test 2: Start the Emitter from GUI

1. Click the **"Start"** button in the Bronze Ready Emitter section
2. Wait 2-3 seconds
3. Status should change to:
   - ✅ Green pulsing dot
   - ✅ Shows "Running • PID: XXXX • Uptime: 0h 0m"
   - ✅ Start button changes to Stop button

**Expected Result:**
- Emitter starts successfully
- Process ID displayed
- Status updates to "Running"

**Troubleshooting:**
- If start fails, check Kafka is running
- Check console logs (F12) for errors
- Check backend logs for errors

---

### Test 3: Send Test Messages (Generate Sample Data)

Open a new PowerShell terminal:

```powershell
cd "Kafka Integration"
python test_bronze_emitter.py
```

This will:
1. Send 7 test messages to `bronze-mongodb` and `bronze-s3` topics
2. Wait for emitter to route them
3. Display routing results

**Expected Console Output:**
```
Sending Test Messages
=====================
✓ [1/3] Sent: test_doc_001 (documents/report.pdf)
✓ [2/3] Sent: test_doc_002 (videos/demo.mp4)
✓ [3/3] Sent: test_doc_003 (images/photo.jpg)

Sending 4 messages to bronze-s3...
✓ [1/4] Sent: documents/report.pdf
✓ [2/4] Sent: videos/presentation.mp4
✓ [3/4] Sent: audio/podcast.mp3
✓ [4/4] Sent: logs/application.log

✅ TEST PASSED: Routing working correctly!
```

---

### Test 4: View Routed Items in GUI

1. Go back to the browser
2. Click **"Refresh"** button in Bronze Ready Emitter section
3. Check **"Ready Queue"** tab:
   - Should show 4-5 items (PDFs, TXT, JPG)
   - Each item shows: filename, timestamp, source, file type
   - Status badge: "Ready" (green)

4. Check **"Media Pending"** tab:
   - Should show 2-3 items (MP4, MP3)
   - Each item has a **"Trigger"** button

**Expected Result:**
```
Ready Queue (5)
  ✓ report.pdf (PDF) - 2m ago - s3
  ✓ application.log (TXT) - 2m ago - s3
  ✓ photo.jpg (IMAGE) - 2m ago - mongodb
  ... (more items)

Media Pending (3)
  [Trigger Button] demo.mp4 (VIDEO) - 2m ago - mongodb
  [Trigger Button] presentation.mp4 (VIDEO) - 2m ago - s3
  [Trigger Button] podcast.mp3 (AUDIO) - 2m ago - s3
```

---

### Test 5: Manual Media Trigger

1. In **"Media Pending"** tab, find a media file
2. Click the **"Trigger"** button
3. Should see an alert: `✓ [filename] has been triggered for processing!`
4. The item should move from "Media Pending" to "Ready Queue"

**Expected Result:**
- Item disappears from Media Pending
- Item appears in Ready Queue
- Alert confirms trigger success

---

### Test 6: Stop the Emitter

1. Click the **"Stop"** button
2. Wait 1-2 seconds
3. Status should change to:
   - ✅ Red dot
   - ✅ Shows "Not running"
   - ✅ Stop button changes to Start button

**Expected Result:**
- Emitter stops gracefully
- Status updates to "Not running"
- Queues remain visible (data persists in Kafka)

---

### Test 7: Auto-Refresh

1. Start the emitter again
2. Leave the browser tab open
3. Run test script again: `python test_bronze_emitter.py`
4. Watch the GUI - it should auto-refresh every 10 seconds

**Expected Result:**
- New items appear automatically without manual refresh
- Counter in tabs updates (e.g., "Ready Queue (8)")

---

## 🔍 Verification Checklist

### Backend Verification

```powershell
# Check API endpoints are available
curl http://localhost:8000/api/bronze-ready/status
curl http://localhost:8000/api/bronze-ready/items?limit=10
curl http://localhost:8000/api/bronze-ready/media-pending?limit=10
```

Should return JSON responses (not 404)

### Frontend Verification

1. **Browser Console (F12):**
   - No React errors
   - See API calls: `GET /api/bronze-ready/status`
   - See responses with data

2. **Network Tab (F12):**
   - Check requests to `/api/bronze-ready/*`
   - Should return 200 OK
   - Response contains `items` array

3. **Visual Elements:**
   - ✅ Bronze Ready Emitter card visible
   - ✅ Start/Stop buttons functional
   - ✅ Tabs switch correctly
   - ✅ Items render with icons and file info
   - ✅ Trigger button works

---

## 🐛 Common Issues

### Issue 1: "Kafka is not available"

**Symptom:** Yellow warning banner, Start button disabled

**Solution:**
```powershell
# Start Kafka
cd C:\kafka\kafka-4.2.0
.\bin\windows\kafka-server-start.bat .\config\kraft\syniq-server.properties
```

---

### Issue 2: "Failed to start emitter"

**Symptom:** Error message after clicking Start

**Check:**
1. Emitter script exists: `Kafka Integration\bronze_ready_emitter.py`
2. Python dependencies installed: `pip install kafka-python minio`
3. Check backend logs for details

---

### Issue 3: No items showing in queues

**Symptom:** Both queues empty even after sending test messages

**Check:**
1. Emitter is running (green dot)
2. Kafka topics exist:
   ```powershell
   cd C:\kafka\kafka-4.2.0
   .\bin\windows\kafka-topics.bat --list --bootstrap-server localhost:9092
   ```
   Should see: `bronze-mongodb`, `bronze-s3`, `bronze-ready`, `bronze-media-pending`
3. Check emitter logs: `Kafka Integration\logs\bronze_emitter_*.log`

---

### Issue 4: Component not showing in UI

**Symptom:** Bronze page loads but no Bronze Ready Emitter section

**Check:**
1. Frontend rebuilt: `npm run dev` (should hot-reload)
2. Browser cache cleared (Ctrl+Shift+R)
3. Check browser console for import errors

---

## 📊 Success Metrics

After all tests pass, you should have:

- ✅ Emitter starts/stops from GUI
- ✅ Status displays correctly (PID, uptime, Kafka status)
- ✅ Ready Queue shows auto-processable files (PDF, TXT, images)
- ✅ Media Pending shows audio/video files
- ✅ Manual trigger moves items from pending to ready
- ✅ Auto-refresh works every 10 seconds
- ✅ No console errors
- ✅ All API endpoints return 200 OK

---

## 🚀 Next Steps

Once testing is complete:

1. **Production Deployment:**
   - Configure `.env` with production Kafka/MinIO endpoints
   - Set up emitter as a system service (systemd/Windows Service)
   - Add monitoring alerts

2. **Feature Enhancements:**
   - Add bulk trigger for multiple media files
   - Add filters/search in queues
   - Add file preview functionality
   - Add processing status tracking

3. **Build AI Processing Service:**
   - Consume from `bronze-ready` topic
   - Process files based on type
   - Publish results to Silver layer

---

## 📞 Getting Help

If you encounter issues:

1. Check browser console (F12)
2. Check backend logs: `gui/api/` directory
3. Check emitter logs: `Kafka Integration/logs/`
4. Verify Kafka is running: `localhost:9092`
5. Verify MinIO is running: `localhost:9000`

---

**Happy Testing! 🎉**
