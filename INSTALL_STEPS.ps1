# ============================================================================
# SYNIQ Installation Guide - Step by Step
# ============================================================================
# Run each section in PowerShell (as Administrator)
# ============================================================================

# ============================================================================
# STEP 1: COMPLETE KAFKA SETUP (5 minutes)
# ============================================================================

# 1.1 Create missing directory
New-Item -ItemType Directory -Force -Path "C:\kafka\kafka-4.2.0\config\kraft"

# 1.2 Create Kafka configuration
$kraftConfig = @"
process.roles=broker,controller
node.id=1
controller.quorum.voters=1@localhost:9093
listeners=PLAINTEXT://localhost:9092,CONTROLLER://localhost:9093
advertised.listeners=PLAINTEXT://localhost:9092
controller.listener.names=CONTROLLER
inter.broker.listener.name=PLAINTEXT
log.dirs=C:/kafka/kafka-logs
auto.create.topics.enable=true
offsets.topic.replication.factor=1
transaction.state.log.replication.factor=1
transaction.state.log.min.isr=1
default.replication.factor=1
min.insync.replicas=1
"@
$kraftConfig | Out-File -FilePath "C:\kafka\kafka-4.2.0\config\kraft\syniq-server.properties" -Encoding UTF8

# 1.3 Format Kafka storage
$env:KAFKA_HEAP_OPTS = "-Xmx512M -Xms256M"
cd C:\kafka\kafka-4.2.0\bin\windows
$uuid = .\kafka-storage.bat random-uuid | Select-Object -Last 1
Write-Host "UUID: $uuid"
.\kafka-storage.bat format -t $uuid -c "..\..\config\kraft\syniq-server.properties"

Write-Host "Kafka setup complete!" -ForegroundColor Green

# ============================================================================
# STEP 2: INSTALL MINIO (2 minutes)
# ============================================================================

# 2.1 Create MinIO directory
New-Item -ItemType Directory -Force -Path "C:\minio"
New-Item -ItemType Directory -Force -Path "C:\minio\data"

# 2.2 Download MinIO
Invoke-WebRequest -Uri "https://dl.min.io/server/minio/release/windows-amd64/minio.exe" -OutFile "C:\minio\minio.exe"

# 2.3 Create startup script
@"
@echo off
cd C:\minio
set MINIO_ROOT_USER=admin
set MINIO_ROOT_PASSWORD=password123
minio.exe server data --console-address ":9001"
"@ | Out-File -FilePath "C:\minio\start-minio.bat" -Encoding ASCII

Write-Host "MinIO setup complete!" -ForegroundColor Green
Write-Host "Start: C:\minio\start-minio.bat" -ForegroundColor Yellow

# ============================================================================
# STEP 3: INSTALL SPARK (5 minutes)
# ============================================================================

# 3.1 Create Spark directory
New-Item -ItemType Directory -Force -Path "C:\spark"

# 3.2 Download Spark
Invoke-WebRequest -Uri "https://dlcdn.apache.org/spark/spark-3.5.0/spark-3.5.0-bin-hadoop3.tgz" -OutFile "C:\spark\spark.tgz"

# 3.3 Extract Spark
cd C:\spark
tar -xzf spark.tgz
Remove-Item spark.tgz

# 3.4 Set environment variable
[Environment]::SetEnvironmentVariable("SPARK_HOME", "C:\spark\spark-3.5.0-bin-hadoop3", "Machine")

Write-Host "Spark setup complete!" -ForegroundColor Green

# ============================================================================
# VERIFICATION
# ============================================================================

Write-Host "`n=== Installation Complete ===" -ForegroundColor Cyan
Write-Host "Kafka:  C:\kafka\kafka-4.2.0" -ForegroundColor Green
Write-Host "MinIO:  C:\minio" -ForegroundColor Green
Write-Host "Spark:  C:\spark\spark-3.5.0-bin-hadoop3" -ForegroundColor Green

Write-Host "`nTo start services:" -ForegroundColor Yellow
Write-Host "  Kafka:  cd C:\kafka\kafka-4.2.0\bin\windows; .\kafka-server-start.bat ..\..\config\kraft\syniq-server.properties"
Write-Host "  MinIO:  C:\minio\start-minio.bat"
