# ✅ SYNIQ Installation Complete!

## 🎉 Successfully Installed

All components are installed and ready to use!

| Component | Version | Location | Status |
|-----------|---------|----------|--------|
| **Kafka** | 4.2.0 | `C:\kafka\kafka-4.2.0` | ✅ Ready |
| **MinIO** | Latest | `C:\syniq\minio` | ✅ Ready |
| **Spark** | 3.5.8 | `C:\syniq\spark\spark-3.5.8` | ✅ Ready |

---

## 🚀 Quick Start

### Start Services

**Terminal 1 - Start Kafka:**
```powershell
C:\kafka\start-kafka.bat
```
Kafka will run on: `localhost:9092`

**Terminal 2 - Start MinIO:**
```powershell
C:\syniq\minio\start-minio.bat
```
MinIO Console: http://localhost:9001  
MinIO API: http://localhost:9000  
**Credentials:** admin / password123

**Spark is ready to use** - No daemon needed, use spark-submit for jobs

---

## 🧪 Verify Installation

Open a **new PowerShell** terminal:

```powershell
# Test Kafka
C:\kafka\kafka-4.2.0\bin\windows\kafka-topics.bat --bootstrap-server localhost:9092 --list

# Test MinIO (open in browser)
Start-Process "http://localhost:9001"

# Test Spark
C:\syniq\spark\spark-3.5.8\bin\spark-submit.cmd --version
```

---

## ⚙️ Set Environment Variables (Optional - Run as Admin)

To make commands available system-wide, run this **once as Administrator**:

```powershell
[Environment]::SetEnvironmentVariable("KAFKA_HOME", "C:\kafka\kafka-4.2.0", "Machine")
[Environment]::SetEnvironmentVariable("SPARK_HOME", "C:\syniq\spark\spark-3.5.8", "Machine")
[Environment]::SetEnvironmentVariable("MINIO_HOME", "C:\syniq\minio", "Machine")

$path = [Environment]::GetEnvironmentVariable("Path", "Machine")
$newPath = "$path;C:\kafka\kafka-4.2.0\bin\windows;C:\syniq\spark\spark-3.5.8\bin;C:\syniq\minio"
[Environment]::SetEnvironmentVariable("Path", $newPath, "Machine")
```

After setting, restart PowerShell to use commands like `spark-submit` from anywhere.

---

## 📊 Service Endpoints

| Service | Endpoint | Purpose |
|---------|----------|---------|
| Kafka Broker | `localhost:9092` | Message streaming |
| MinIO API | `http://localhost:9000` | S3-compatible object storage |
| MinIO Console | `http://localhost:9001` | Web UI (admin/password123) |
| Spark | N/A | Submit jobs via `spark-submit` |

---

## 🔧 Configuration Files

**Kafka:**
- Config: `C:\kafka\kafka-4.2.0\config\kraft\syniq-server.properties`
- Logs: `C:\kafka\kafka-logs`
- Startup: `C:\kafka\start-kafka.bat`

**MinIO:**
- Data: `C:\syniq\minio\data`
- Startup: `C:\syniq\minio\start-minio.bat`
- Credentials are set in the startup script

**Spark:**
- Home: `C:\syniq\spark\spark-3.5.8`
- Config: `C:\syniq\spark\spark-3.5.8\conf`
- Submit jobs: `spark-submit.cmd [options] <app jar>`

---

## 🎯 Next Steps

### 1. Update Your Application Configuration

Update your `.env` files with these endpoints:

```bash
# Kafka
KAFKA_BOOTSTRAP_SERVERS=localhost:9092

# MinIO
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=admin
MINIO_SECRET_KEY=password123

# If using Spark programmatically
SPARK_HOME=C:\syniq\spark\spark-3.5.8
```

### 2. Create MinIO Buckets

Access MinIO Console at http://localhost:9001 and create buckets:
- `bronze` - for raw ingested data
- `silver` - for cleaned/transformed data
- `gold` - for aggregated/business-ready data

### 3. Test Data Pipeline

```powershell
# Create a test topic in Kafka
cd C:\kafka\kafka-4.2.0\bin\windows
.\kafka-topics.bat --create --topic test-topic --bootstrap-server localhost:9092 --partitions 1 --replication-factor 1

# Start your application
cd "C:\Users\Local user\OneDrive - M Telecommunication Sdn Bhd\Desktop\TASK\Syniq\gui"
.\start_dev.ps1
```

---

## 🛑 Stop Services

Press `Ctrl+C` in each terminal running the services, or:

```powershell
# Stop Kafka
Get-Process | Where-Object {$_.Path -like "*kafka*"} | Stop-Process -Force

# Stop MinIO
Get-Process | Where-Object {$_.Name -eq "minio"} | Stop-Process -Force
```

---

## 📚 Documentation Links

- **Kafka:** https://kafka.apache.org/documentation/
- **MinIO:** https://min.io/docs/minio/windows/index.html
- **Spark:** https://spark.apache.org/docs/latest/

---

## 🎉 You're All Set!

Your data lakehouse infrastructure is ready. Start the services and begin processing data!

**Need help?** Check the documentation or restart services if issues occur.
