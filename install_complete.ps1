# ============================================================================
# SYNIQ Complete Installation - Kafka, MinIO, and Spark
# ============================================================================
# Run as Administrator
# ============================================================================

param(
    [string]$InstallPath = "C:\syniq",
    [switch]$SkipKafka,
    [switch]$SkipMinIO,
    [switch]$SkipSpark
)

$ErrorActionPreference = "Continue"

Write-Host "`n================================================================" -ForegroundColor Cyan
Write-Host "  SYNIQ Platform - Complete Native Installation" -ForegroundColor Cyan
Write-Host "================================================================`n" -ForegroundColor Cyan

# Create base installation directory
New-Item -ItemType Directory -Force -Path $InstallPath | Out-Null

# ============================================================================
# PART 1: KAFKA SETUP
# ============================================================================

if (-not $SkipKafka) {
    Write-Host "`n[1/3] Setting up Kafka..." -ForegroundColor Yellow
    
    # Check if Kafka already extracted
    if (Test-Path "C:\kafka\kafka-4.2.0") {
        Write-Host "  Kafka already extracted at C:\kafka\kafka-4.2.0" -ForegroundColor Green
        $kafkaHome = "C:\kafka\kafka-4.2.0"
    } elseif (Test-Path "C:\kafka\kafka_2.13-4.2.0") {
        Write-Host "  Renaming Kafka directory..." -ForegroundColor Gray
        Rename-Item "C:\kafka\kafka_2.13-4.2.0" "C:\kafka\kafka-4.2.0" -Force
        $kafkaHome = "C:\kafka\kafka-4.2.0"
    } else {
        Write-Host "  ERROR: Kafka not found. Please run: .\install_kafka_native.ps1" -ForegroundColor Red
        $SkipKafka = $true
    }
    
    if (-not $SkipKafka) {
        # Create config directories
        New-Item -ItemType Directory -Force -Path "$kafkaHome\config\kraft" | Out-Null
        
        # Create Kafka configuration
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
num.network.threads=3
num.io.threads=8
log.retention.hours=168
group.initial.rebalance.delay.ms=0
"@
        $kraftConfig | Out-File -FilePath "$kafkaHome\config\kraft\syniq-server.properties" -Encoding UTF8
        
        # Generate UUID and format storage
        Write-Host "  Configuring Kafka storage..." -ForegroundColor Gray
        $env:KAFKA_HEAP_OPTS = "-Xmx512M -Xms256M"
        $uuid = & "$kafkaHome\bin\windows\kafka-storage.bat" random-uuid 2>&1 | Select-Object -Last 1
        Write-Host "  Cluster UUID: $uuid" -ForegroundColor Gray
        & "$kafkaHome\bin\windows\kafka-storage.bat" format -t $uuid -c "$kafkaHome\config\kraft\syniq-server.properties" 2>&1 | Out-Null
        
        Write-Host "  Kafka configured successfully!" -ForegroundColor Green
    }
}

# ============================================================================
# PART 2: MINIO SETUP
# ============================================================================

if (-not $SkipMinIO) {
    Write-Host "`n[2/3] Setting up MinIO..." -ForegroundColor Yellow
    
    $minioPath = "$InstallPath\minio"
    New-Item -ItemType Directory -Force -Path $minioPath | Out-Null
    New-Item -ItemType Directory -Force -Path "$minioPath\data" | Out-Null
    
    # Download MinIO
    if (-not (Test-Path "$minioPath\minio.exe")) {
        Write-Host "  Downloading MinIO..." -ForegroundColor Gray
        $minioUrl = "https://dl.min.io/server/minio/release/windows-amd64/minio.exe"
        try {
            Invoke-WebRequest -Uri $minioUrl -OutFile "$minioPath\minio.exe"
            Write-Host "  MinIO downloaded" -ForegroundColor Green
        } catch {
            Write-Host "  ERROR: Failed to download MinIO: $_" -ForegroundColor Red
            Write-Host "  Download manually from: https://min.io/download" -ForegroundColor Yellow
            $SkipMinIO = $true
        }
    } else {
        Write-Host "  MinIO already downloaded" -ForegroundColor Green
    }
    
    if (-not $SkipMinIO) {
        # Create MinIO startup script
        $minioStartScript = @"
@echo off
title MinIO Server
cd "$minioPath"
set MINIO_ROOT_USER=admin
set MINIO_ROOT_PASSWORD=password123
minio.exe server data --console-address ":9001"
"@
        $minioStartScript | Out-File -FilePath "$minioPath\start-minio.bat" -Encoding ASCII
        
        Write-Host "  MinIO configured successfully!" -ForegroundColor Green
        Write-Host "  Location: $minioPath" -ForegroundColor Gray
        Write-Host "  Credentials: admin / password123" -ForegroundColor Gray
    }
}

# ============================================================================
# PART 3: SPARK SETUP
# ============================================================================

if (-not $SkipSpark) {
    Write-Host "`n[3/3] Setting up Apache Spark..." -ForegroundColor Yellow
    
    $sparkVersion = "3.5.0"
    $hadoopVersion = "3"
    $sparkPath = "$InstallPath\spark"
    
    if (-not (Test-Path "$sparkPath\spark-$sparkVersion-bin-hadoop$hadoopVersion")) {
        Write-Host "  Downloading Apache Spark $sparkVersion..." -ForegroundColor Gray
        $sparkUrl = "https://dlcdn.apache.org/spark/spark-$sparkVersion/spark-$sparkVersion-bin-hadoop$hadoopVersion.tgz"
        $sparkArchive = "$sparkPath\spark.tgz"
        
        New-Item -ItemType Directory -Force -Path $sparkPath | Out-Null
        
        try {
            Invoke-WebRequest -Uri $sparkUrl -OutFile $sparkArchive -TimeoutSec 300
            Write-Host "  Extracting Spark..." -ForegroundColor Gray
            tar -xzf $sparkArchive -C $sparkPath
            Remove-Item $sparkArchive
            Write-Host "  Spark installed successfully!" -ForegroundColor Green
        } catch {
            Write-Host "  ERROR: Failed to download Spark: $_" -ForegroundColor Red
            Write-Host "  Download manually from: https://spark.apache.org/downloads.html" -ForegroundColor Yellow
            $SkipSpark = $true
        }
    } else {
        Write-Host "  Spark already installed" -ForegroundColor Green
    }
    
    if (-not $SkipSpark) {
        $sparkHome = "$sparkPath\spark-$sparkVersion-bin-hadoop$hadoopVersion"
        
        # Set environment variables
        [Environment]::SetEnvironmentVariable("SPARK_HOME", $sparkHome, "Machine")
        Write-Host "  Spark configured successfully!" -ForegroundColor Green
        Write-Host "  Location: $sparkHome" -ForegroundColor Gray
    }
}

# ============================================================================
# SUMMARY AND NEXT STEPS
# ============================================================================

Write-Host "`n================================================================" -ForegroundColor Green
Write-Host "  Installation Complete!" -ForegroundColor Green
Write-Host "================================================================`n" -ForegroundColor Green

Write-Host "Installed Components:" -ForegroundColor Cyan

if (-not $SkipKafka -and (Test-Path "C:\kafka\kafka-4.2.0")) {
    Write-Host "  [OK] Kafka 4.2.0" -ForegroundColor Green
    Write-Host "       Location: C:\kafka\kafka-4.2.0" -ForegroundColor Gray
    Write-Host "       Start: cd C:\kafka\kafka-4.2.0\bin\windows; .\kafka-server-start.bat ..\..\config\kraft\syniq-server.properties" -ForegroundColor Gray
}

if (-not $SkipMinIO -and (Test-Path "$InstallPath\minio\minio.exe")) {
    Write-Host "  [OK] MinIO" -ForegroundColor Green
    Write-Host "       Location: $InstallPath\minio" -ForegroundColor Gray
    Write-Host "       Start: $InstallPath\minio\start-minio.bat" -ForegroundColor Gray
    Write-Host "       Console: http://localhost:9001" -ForegroundColor Gray
}

if (-not $SkipSpark -and (Test-Path "$InstallPath\spark")) {
    Write-Host "  [OK] Apache Spark 3.5.0" -ForegroundColor Green
    Write-Host "       Location: $InstallPath\spark" -ForegroundColor Gray
}

Write-Host "`nQuick Start Commands:" -ForegroundColor Cyan
Write-Host "  cd 'Kafka Integration'" -ForegroundColor White
Write-Host "  .\start_kafka_native.ps1" -ForegroundColor White

Write-Host "`nDone!" -ForegroundColor Magenta
