# ============================================================================
# SYNIQ Complete Infrastructure Installation Script
# Installs: Kafka, MinIO, and Spark (all native, no Docker)
# ============================================================================

param(
    [string]$InstallPath = "C:\syniq",
    [switch]$CreateServices
)

$ErrorActionPreference = "Stop"

Write-Host "`n================================================================" -ForegroundColor Cyan
Write-Host "  SYNIQ Complete Infrastructure Installation" -ForegroundColor Cyan
Write-Host "  Installing: Kafka + MinIO + Spark" -ForegroundColor Cyan
Write-Host "================================================================`n" -ForegroundColor Cyan

# Create base installation directory
New-Item -ItemType Directory -Force -Path $InstallPath | Out-Null
Write-Host "Installation directory: $InstallPath`n" -ForegroundColor White

# ============================================================================
# PART 1: Complete Kafka Installation (using existing C:\kafka)
# ============================================================================

Write-Host "`n[1/3] Finalizing Kafka Installation..." -ForegroundColor Yellow

$kafkaHome = "C:\kafka\kafka-4.2.0"

if (Test-Path $kafkaHome) {
    Write-Host "  Kafka found at: $kafkaHome" -ForegroundColor Green
    
    # Create config directories if missing
    New-Item -ItemType Directory -Force -Path "$kafkaHome\config\kraft" | Out-Null
    
    # Create KRaft configuration
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
"@
    $kraftConfig | Out-File -FilePath "$kafkaHome\config\kraft\syniq-server.properties" -Encoding UTF8
    
    # Format storage
    $env:KAFKA_HEAP_OPTS = "-Xmx512M -Xms256M"
    $uuidOutput = & "$kafkaHome\bin\windows\kafka-storage.bat" random-uuid 2>&1
    $uuid = ($uuidOutput | Where-Object { $_ -match '^[a-zA-Z0-9_-]{22}$' }) | Select-Object -Last 1
    
    if ($uuid) {
        & "$kafkaHome\bin\windows\kafka-storage.bat" format -t $uuid -c "$kafkaHome\config\kraft\syniq-server.properties" 2>&1 | Out-Null
        Write-Host "  Kafka configured successfully" -ForegroundColor Green
        Write-Host "  Cluster UUID: $uuid" -ForegroundColor Gray
    } else {
        Write-Host "  Using existing Kafka configuration" -ForegroundColor Green
    }
} else {
    Write-Host "  ERROR: Kafka not found. Please run install_kafka_native.ps1 first" -ForegroundColor Red
    exit 1
}

# ============================================================================
# PART 2: Install MinIO
# ============================================================================

Write-Host "`n[2/3] Installing MinIO..." -ForegroundColor Yellow

$minioPath = "$InstallPath\minio"
New-Item -ItemType Directory -Force -Path $minioPath | Out-Null
New-Item -ItemType Directory -Force -Path "$minioPath\data" | Out-Null

$minioExe = "$minioPath\minio.exe"

if (-not (Test-Path $minioExe)) {
    Write-Host "  Downloading MinIO..." -ForegroundColor Gray
    $minioUrl = "https://dl.min.io/server/minio/release/windows-amd64/minio.exe"
    Invoke-WebRequest -Uri $minioUrl -OutFile $minioExe
    Write-Host "  MinIO downloaded" -ForegroundColor Green
} else {
    Write-Host "  MinIO already downloaded" -ForegroundColor Green
}

# Create MinIO startup script
$minioStartScript = @"
@echo off
title MinIO Server
set MINIO_ROOT_USER=admin
set MINIO_ROOT_PASSWORD=password123
cd "$minioPath"
minio.exe server data --console-address ":9001" --address ":9000"
"@
$minioStartScript | Out-File -FilePath "$minioPath\start-minio.bat" -Encoding ASCII

Write-Host "  MinIO installed at: $minioPath" -ForegroundColor Green
Write-Host "  Access: http://localhost:9000 (API)" -ForegroundColor Gray
Write-Host "  Console: http://localhost:9001 (admin/password123)" -ForegroundColor Gray

# ============================================================================
# PART 3: Install Apache Spark
# ============================================================================

Write-Host "`n[3/3] Installing Apache Spark..." -ForegroundColor Yellow

$sparkVersion = "3.5.0"
$hadoopVersion = "3"
$sparkPath = "$InstallPath\spark"
$sparkHome = "$sparkPath\spark-$sparkVersion"

if (-not (Test-Path $sparkHome)) {
    Write-Host "  Downloading Spark $sparkVersion..." -ForegroundColor Gray
    
    $sparkUrl = "https://archive.apache.org/dist/spark/spark-$sparkVersion/spark-$sparkVersion-bin-hadoop$hadoopVersion.tgz"
    $sparkArchive = "$sparkPath\spark.tgz"
    
    New-Item -ItemType Directory -Force -Path $sparkPath | Out-Null
    
    try {
        Invoke-WebRequest -Uri $sparkUrl -OutFile $sparkArchive -TimeoutSec 300
        Write-Host "  Extracting Spark..." -ForegroundColor Gray
        tar -xzf $sparkArchive -C $sparkPath
        Remove-Item $sparkArchive
        
        # Rename directory
        $extractedDir = "$sparkPath\spark-$sparkVersion-bin-hadoop$hadoopVersion"
        if (Test-Path $extractedDir) {
            Rename-Item $extractedDir $sparkHome
        }
        
        Write-Host "  Spark installed at: $sparkHome" -ForegroundColor Green
    } catch {
        Write-Host "  ERROR: Failed to download Spark: $_" -ForegroundColor Red
        Write-Host "  Please download manually from: https://spark.apache.org/downloads.html" -ForegroundColor Yellow
    }
} else {
    Write-Host "  Spark already installed at: $sparkHome" -ForegroundColor Green
}

# ============================================================================
# Set Environment Variables
# ============================================================================

Write-Host "`nSetting environment variables..." -ForegroundColor Yellow

[Environment]::SetEnvironmentVariable("KAFKA_HOME", "C:\kafka\kafka-4.2.0", "Machine")
[Environment]::SetEnvironmentVariable("SPARK_HOME", $sparkHome, "Machine")
[Environment]::SetEnvironmentVariable("MINIO_HOME", $minioPath, "Machine")

$currentPath = [Environment]::GetEnvironmentVariable("Path", "Machine")
$pathsToAdd = @(
    "C:\kafka\kafka-4.2.0\bin\windows",
    "$sparkHome\bin",
    $minioPath
)

foreach ($pathToAdd in $pathsToAdd) {
    if ($currentPath -notlike "*$pathToAdd*") {
        $currentPath = "$currentPath;$pathToAdd"
    }
}

[Environment]::SetEnvironmentVariable("Path", $currentPath, "Machine")
Write-Host "Environment variables set" -ForegroundColor Green

# ============================================================================
# Create Windows Services (Optional)
# ============================================================================

if ($CreateServices) {
    Write-Host "`nInstalling Windows Services..." -ForegroundColor Yellow
    
    # Download NSSM if not exists
    $nssmPath = "$InstallPath\nssm-2.24"
    if (-not (Test-Path $nssmPath)) {
        Write-Host "  Downloading NSSM..." -ForegroundColor Gray
        $nssmUrl = "https://nssm.cc/release/nssm-2.24.zip"
        $nssmZip = "$InstallPath\nssm.zip"
        Invoke-WebRequest -Uri $nssmUrl -OutFile $nssmZip
        Expand-Archive -Path $nssmZip -DestinationPath $InstallPath
        Remove-Item $nssmZip
    }
    
    $nssm = "$nssmPath\win64\nssm.exe"
    
    # Create startup scripts
    $kafkaStartBat = "C:\kafka\start-kafka.bat"
    @"
@echo off
set KAFKA_HEAP_OPTS=-Xmx1G -Xms512M
cd C:\kafka\kafka-4.2.0
bin\windows\kafka-server-start.bat config\kraft\syniq-server.properties
"@ | Out-File -FilePath $kafkaStartBat -Encoding ASCII
    
    # Install services
    Write-Host "  Installing Kafka service..." -ForegroundColor Gray
    & $nssm install SyniqKafka $kafkaStartBat
    & $nssm set SyniqKafka AppDirectory "C:\kafka\kafka-4.2.0"
    & $nssm set SyniqKafka DisplayName "SYNIQ Kafka Broker"
    & $nssm set SyniqKafka Start SERVICE_AUTO_START
    
    Write-Host "  Installing MinIO service..." -ForegroundColor Gray
    & $nssm install SyniqMinIO "$minioPath\start-minio.bat"
    & $nssm set SyniqMinIO AppDirectory $minioPath
    & $nssm set SyniqMinIO DisplayName "SYNIQ MinIO Server"
    & $nssm set SyniqMinIO Start SERVICE_AUTO_START
    
    Write-Host "Windows services created" -ForegroundColor Green
}

# ============================================================================
# Summary
# ============================================================================

Write-Host "`n================================================================" -ForegroundColor Green
Write-Host "             Installation Complete!" -ForegroundColor Green
Write-Host "================================================================`n" -ForegroundColor Green

Write-Host "Installed Components:" -ForegroundColor Cyan
Write-Host "  [+] Kafka 4.2.0      - localhost:9092" -ForegroundColor White
Write-Host "  [+] MinIO            - localhost:9000 (API), localhost:9001 (Console)" -ForegroundColor White
Write-Host "  [+] Spark $sparkVersion    - $sparkHome" -ForegroundColor White

Write-Host "`nTo Start Services:" -ForegroundColor Cyan

if ($CreateServices) {
    Write-Host "  Start-Service SyniqKafka" -ForegroundColor White
    Write-Host "  Start-Service SyniqMinIO" -ForegroundColor White
} else {
    Write-Host "  Kafka:  C:\kafka\start-kafka.bat" -ForegroundColor White
    Write-Host "  MinIO:  $minioPath\start-minio.bat" -ForegroundColor White
    Write-Host "`n  Or run this script with -CreateServices to install as Windows services" -ForegroundColor Gray
}

Write-Host "`nMinIO Credentials:" -ForegroundColor Cyan
Write-Host "  Username: admin" -ForegroundColor White
Write-Host "  Password: password123" -ForegroundColor White

Write-Host "`nVerify Installation:" -ForegroundColor Cyan
Write-Host "  kafka-topics.bat --bootstrap-server localhost:9092 --list" -ForegroundColor White
Write-Host "  Open http://localhost:9001 in browser for MinIO" -ForegroundColor White
Write-Host "  spark-shell --version" -ForegroundColor White

Write-Host "`nDocumentation:" -ForegroundColor Cyan
Write-Host "  Kafka:  https://kafka.apache.org/documentation/" -ForegroundColor Gray
Write-Host "  MinIO:  https://min.io/docs/minio/windows/index.html" -ForegroundColor Gray
Write-Host "  Spark:  https://spark.apache.org/docs/latest/" -ForegroundColor Gray

Write-Host "`nReady to process data!`n" -ForegroundColor Magenta
