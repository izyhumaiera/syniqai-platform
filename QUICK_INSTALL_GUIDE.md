# SYNIQ Quick Installation Guide - Manual Steps

## Prerequisites
✅ Java is already installed
✅ Kafka 4.2.0 is already downloaded to C:\kafka

---

## Step 1: Complete Kafka Setup (2 minutes)

```powershell
# Set memory limit
$env:KAFKA_HEAP_OPTS = "-Xmx512M -Xms256M"

# Generate UUID
cd C:\kafka\kafka-4.2.0\bin\windows
.\kafka-storage.bat random-uuid

# Copy the UUID from output (looks like: zQn6ztG7QzKy1UBaa0TG3Q)
# Then format storage (replace YOUR-UUID with the copied UUID):
.\kafka-storage.bat format -t YOUR-UUID-HERE -c "C:\kafka\kafka-4.2.0\config\kraft\syniq-server.properties"

# Start Kafka
.\kafka-server-start.bat "C:\kafka\kafka-4.2.0\config\kraft\syniq-server.properties"
```

**Leave this terminal open!** Kafka is now running.

---

## Step 2: Install MinIO (3 minutes)

Open a **new PowerShell terminal (as Admin)**:

```powershell
# Create directory
New-Item -ItemType Directory -Force -Path "C:\syniq\minio\data"

# Download MinIO
cd C:\syniq\minio
Invoke-WebRequest -Uri "https://dl.min.io/server/minio/release/windows-amd64/minio.exe" -OutFile "minio.exe"

# Set credentials and start MinIO
$env:MINIO_ROOT_USER = "admin"
$env:MINIO_ROOT_PASSWORD = "password123"
.\minio.exe server data --console-address ":9001" --address ":9000"
```

**Leave this terminal open!** MinIO is now running.

**Access MinIO Console:** http://localhost:9001 (admin / password123)

---

## Step 3: Install Spark (5 minutes)

Open a **new PowerShell terminal (as Admin)**:

```powershell
# Create directory
New-Item -ItemType Directory -Force -Path "C:\syniq\spark"

# Download Spark 3.5.0
$sparkUrl = "https://archive.apache.org/dist/spark/spark-3.5.0/spark-3.5.0-bin-hadoop3.tgz"
Invoke-WebRequest -Uri $sparkUrl -OutFile "C:\syniq\spark\spark.tgz"

# Extract
cd C:\syniq\spark
tar -xzf spark.tgz
Rename-Item "spark-3.5.0-bin-hadoop3" "spark-3.5.0"

# Set environment variables (requires Admin)
[Environment]::SetEnvironmentVariable("SPARK_HOME", "C:\syniq\spark\spark-3.5.0", "Machine")
$currentPath = [Environment]::GetEnvironmentVariable("Path", "Machine")
[Environment]::SetEnvironmentVariable("Path", "$currentPath;C:\syniq\spark\spark-3.5.0\bin", "Machine")

Write-Host "Spark installed successfully!" -ForegroundColor Green
```

---

## Step 4: Verify Everything Works

Open a **new PowerShell terminal**:

```powershell
# Test Kafka
C:\kafka\kafka-4.2.0\bin\windows\kafka-topics.bat --bootstrap-server localhost:9092 --list

# Test MinIO (open in browser)
Start-Process "http://localhost:9001"

# Test Spark
C:\syniq\spark\spark-3.5.0\bin\spark-submit.cmd --version
```

---

## Quick Status Check

| Service | Status Check | URL |
|---------|-------------|-----|
| **Kafka** | `netstat -an \| findstr :9092` | localhost:9092 |
| **MinIO** | `netstat -an \| findstr :9000` | http://localhost:9001 |
| **Spark** | `spark-submit --version` | N/A (batch processing) |

---

## Optional: Install as Windows Services

If you want services to auto-start, run this **once** (as Admin):

```powershell
.\install_complete_stack.ps1 -CreateServices
```

This creates:
- **SyniqKafka** - Kafka broker service
- **SyniqMinIO** - MinIO server service

Start/stop with:
```powershell
Start-Service SyniqKafka
Start-Service SyniqMinIO
```

---

## Troubleshooting

**Kafka won't start:**
```powershell
# Check if port is in use
netstat -an | findstr :9092

# Kill process if needed
$conn = Get-NetTCPConnection -LocalPort 9092
Stop-Process -Id $conn.OwningProcess -Force
```

**MinIO won't start:**
```powershell
# Check port
netstat -an | findstr :9000
```

**Java errors:**
```powershell
# Reduce memory
$env:KAFKA_HEAP_OPTS = "-Xmx256M -Xms128M"
```

---

## Next Steps

1. ✅ Kafka running on localhost:9092
2. ✅ MinIO running on localhost:9000
3. ✅ Spark installed and ready

**Now you can:**
- Configure your application to use `localhost:9092` for Kafka
- Set MinIO endpoint to `localhost:9000` in your .env
- Run Spark jobs for data processing

**Configuration files location:**
- Kafka: `C:\kafka\kafka-4.2.0\config\kraft\syniq-server.properties`
- MinIO data: `C:\syniq\minio\data\`
- Spark: `C:\syniq\spark\spark-3.5.0\conf\`
