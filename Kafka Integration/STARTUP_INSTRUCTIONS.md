# ============================================================================
# SYNIQ System Startup Instructions
# ============================================================================
# After Docker removal - Native Kafka & MinIO only
# ============================================================================

## ✅ Configuration Complete

All Docker references removed and system configured for native services:

- **Kafka Broker**: 127.0.0.1:9092 (IPv4 explicit)
- **Kafka UI**: http://localhost:8080
- **MinIO API**: localhost:9000
- **MinIO Console**: http://localhost:9001

---

## 🚀 **QUICK START - Start Everything**

### **Option 1: Simple Batch Script (Recommended)**

Open PowerShell in the `Kafka Integration` folder and run:

```powershell
cd "C:\Users\Local user\OneDrive - M Telecommunication Sdn Bhd\Desktop\TASK\Syniq\Kafka Integration"
.\quick_start.bat
```

This will:
1. Check if Kafka is running
2. Start Kafka if needed (waits 20 seconds)
3. Start AI Processor automatically

---

### **Option 2: PowerShell Script (Advanced)**

```powershell
cd "C:\Users\Local user\OneDrive - M Telecommunication Sdn Bhd\Desktop\TASK\Syniq\Kafka Integration"
.\restart_system.ps1
```

Features:
- Force restart with: `.\restart_system.ps1 -ForceRestart`
- Custom wait time: `.\restart_system.ps1 -KafkaWaitSeconds 45`

---

### **Option 3: Manual Step-by-Step**

If you prefer manual control:

#### **Step 1: Start Kafka**

```powershell
# Open new PowerShell window for Kafka
cd C:\kafka\kafka-4.2.0
.\bin\windows\kafka-server-start.bat .\config\kraft\syniq-server.properties
```

Keep this window open (Kafka runs in foreground).

#### **Step 2: Wait for Kafka (20-30 seconds)**

Test if ready:
```powershell
Test-NetConnection -ComputerName 127.0.0.1 -Port 9092
```

Should show `TcpTestSucceeded: True`

#### **Step 3: Start AI Processor**

Open new PowerShell window:
```powershell
cd "C:\Users\Local user\OneDrive - M Telecommunication Sdn Bhd\Desktop\TASK\Syniq"
python "Kafka Integration\ai_processor.py"
```

---

## 📊 **Verify Everything is Running**

### Check Kafka Status:
```powershell
Test-NetConnection -ComputerName 127.0.0.1 -Port 9092
```

### Check Kafka Topics:
```powershell
cd C:\kafka\kafka-4.2.0
.\bin\windows\kafka-topics.bat --bootstrap-server 127.0.0.1:9092 --list
```

### Check AI Processor Logs:
Look for these messages:
```
✓ AI Processor initialized - Block 2 ready
  Consuming from: bronze-ready
  Vision Model: qwen/qwen3-vl-8b-thinking
  Text Model: qwen/qwen3-8b
  Audio Model: openai/gpt-audio-mini
```

---

## 🧪 **Test AI Models**

Once AI Processor is running, open another PowerShell window:

```powershell
cd "C:\Users\Local user\OneDrive - M Telecommunication Sdn Bhd\Desktop\TASK\Syniq"
python "Kafka Integration\test_ai_models.py"
```

Follow the prompts to test:
- ✅ Image processing (qwen/qwen3-vl-8b-thinking)
- ✅ Text documents (qwen/qwen3-8b)
- ✅ Audio files (openai/gpt-audio-mini)

---

## ❌ **Troubleshooting**

### Issue: "Connection timeout" or "NoBrokersAvailable"

**Solution**: Kafka is not running or not ready yet

1. Check if Kafka process exists:
   ```powershell
   Get-Process java -ErrorAction SilentlyContinue
   ```

2. Check if port 9092 is open:
   ```powershell
   Test-NetConnection -ComputerName 127.0.0.1 -Port 9092
   ```

3. If Kafka won't start, check logs:
   ```powershell
   Get-Content "C:\kafka\kafka-4.2.0\logs\server.log" -Tail 50
   ```

### Issue: "ffmpeg-python not available"

**Not critical** - Only needed for video processing (currently disabled)

### Issue: "api_version warning"

**Harmless** - Client auto-negotiates correct version with server

---

## 🛑 **Stop Everything**

### Stop AI Processor:
Press `Ctrl+C` in the AI Processor window

### Stop Kafka:
```powershell
Get-Process java | Stop-Process -Force
```

Or close the Kafka window (if running in foreground)

---

## 📁 **Files Created**

1. **`quick_start.bat`** - Simple one-command startup
2. **`restart_system.ps1`** - Advanced PowerShell script with checks
3. **`fix_kafka_ipv6.ps1`** - Already applied (fixed IPv6 timeout issue)
4. **`.env`** - Updated with 127.0.0.1:9092 (IPv4 explicit)

---

## 🎯 **Summary**

**Everything is configured to run WITHOUT Docker!**

✅ Kafka: Native Windows (C:\kafka)
✅ MinIO: Native Windows service
✅ PostgreSQL: Native Windows service
✅ AI Processor: Python script

**Just run**: `quick_start.bat` and you're ready to test! 🚀
