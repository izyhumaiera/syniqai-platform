# ============================================================================
# SYNIQ Data Lakehouse - Kafka Native Installation Script
# ============================================================================
# This script installs Apache Kafka in KRaft mode (no Zookeeper needed)
# and Kafka Connect with Debezium connectors on Windows
# ============================================================================

param(
    [string]$InstallPath = "C:\kafka",
    [string]$KafkaVersion = "4.2.0",
    [string]$ScalaVersion = "2.13",
    [string]$DebeziumVersion = "2.5.0.Final",
    [switch]$SkipDownload,
    [switch]$CreateServices
)

$ErrorActionPreference = "Stop"

Write-Host "`n================================================================" -ForegroundColor Cyan
Write-Host "  SYNIQ - Kafka Native Installation (KRaft Mode)           " -ForegroundColor Cyan
Write-Host "================================================================`n" -ForegroundColor Cyan

# Check Java
Write-Host "Checking Java installation..." -ForegroundColor Yellow
$javaInstalled = $false
try {
    $javaVersion = java -version 2>&1 | Select-String "version" | Select-Object -First 1
    if ($javaVersion) {
        $javaInstalled = $true
        Write-Host "Java found: $javaVersion" -ForegroundColor Green
    }
} catch {
    # Java not found
}

if (-not $javaInstalled) {
    Write-Host "Java not found. Installing OpenJDK 21..." -ForegroundColor Red
    
    # Download and install Eclipse Temurin JDK 21
    $jdkUrl = "https://api.adoptium.net/v3/binary/latest/21/ga/windows/x64/jdk/hotspot/normal/eclipse"
    $jdkInstaller = "$env:TEMP\OpenJDK21.msi"
    
    Write-Host "   Downloading OpenJDK 21..." -ForegroundColor Gray
    Invoke-WebRequest -Uri $jdkUrl -OutFile $jdkInstaller
    
    Write-Host "   Installing OpenJDK 21..." -ForegroundColor Gray
    Start-Process msiexec.exe -Wait -ArgumentList "/i `"$jdkInstaller`" /quiet ADDLOCAL=FeatureMain,FeatureEnvironment,FeatureJarFileRunWith,FeatureJavaHome"
    
    Remove-Item $jdkInstaller
    
    # Refresh environment
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
    
    Write-Host "Successfully installed Java" -ForegroundColor Green
}

# Create installation directory
Write-Host "`nCreating installation directory..." -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path $InstallPath | Out-Null
New-Item -ItemType Directory -Force -Path "$InstallPath\connect\plugins" | Out-Null
New-Item -ItemType Directory -Force -Path "$InstallPath\kafka-logs" | Out-Null
Write-Host "Directories created: $InstallPath" -ForegroundColor Green

# Download or check for Kafka archive
$kafkaArchive = "$InstallPath\kafka.tgz"

if (-not $SkipDownload) {
    # Download Kafka
    Write-Host "`nDownloading Apache Kafka $KafkaVersion..." -ForegroundColor Yellow
    
    # Try multiple mirrors for better reliability
    $kafkaUrls = @(
        "https://downloads.apache.org/kafka/$KafkaVersion/kafka_$ScalaVersion-$KafkaVersion.tgz",
        "https://archive.apache.org/dist/kafka/$KafkaVersion/kafka_$ScalaVersion-$KafkaVersion.tgz",
        "https://dlcdn.apache.org/kafka/$KafkaVersion/kafka_$ScalaVersion-$KafkaVersion.tgz"
    )
    
    $downloaded = $false
    
    foreach ($kafkaUrl in $kafkaUrls) {
        try {
            Write-Host "   Trying mirror: $kafkaUrl" -ForegroundColor Gray
            Invoke-WebRequest -Uri $kafkaUrl -OutFile $kafkaArchive -TimeoutSec 180
            Write-Host "Kafka downloaded" -ForegroundColor Green
            $downloaded = $true
            break
        } catch {
            Write-Host "   Mirror failed, trying next..." -ForegroundColor Yellow
        }
    }
    
    if (-not $downloaded) {
        Write-Host "Failed to download Kafka from any mirror" -ForegroundColor Red
        Write-Host "`nPlease download manually:" -ForegroundColor Yellow
        Write-Host "   1. Download from: https://kafka.apache.org/downloads" -ForegroundColor White
        Write-Host "   2. Save as: $kafkaArchive" -ForegroundColor White
        Write-Host "   3. Run: .\install_kafka_native.ps1 -CreateServices -SkipDownload" -ForegroundColor White
        Write-Host "`nOr check KAFKA_MANUAL_INSTALL.md for detailed instructions" -ForegroundColor Cyan
        exit 1
    }
} else {
    # Check if archive exists
    if (-not (Test-Path $kafkaArchive)) {
        Write-Host "Kafka archive not found at: $kafkaArchive" -ForegroundColor Red
        Write-Host "Please download Kafka 4.2.0 and save it as: $kafkaArchive" -ForegroundColor Yellow
        exit 1
    }
    Write-Host "`nUsing existing Kafka archive: $kafkaArchive" -ForegroundColor Green
}

# Extract Kafka (always runs, whether downloaded or using existing file)
Write-Host "Extracting Kafka..." -ForegroundColor Yellow
tar -xzf $kafkaArchive -C $InstallPath

$kafkaDir = "$InstallPath\kafka_$ScalaVersion-$KafkaVersion"
if (Test-Path "$InstallPath\kafka-$KafkaVersion") {
    Remove-Item -Recurse -Force "$InstallPath\kafka-$KafkaVersion"
}
Rename-Item $kafkaDir "$InstallPath\kafka-$KafkaVersion"
Write-Host "Kafka extracted to $InstallPath\kafka-$KafkaVersion" -ForegroundColor Green

# Download Debezium Connectors (optional, separate from Kafka download)
if (-not $SkipDownload) {
    Write-Host "`nDownloading Debezium connectors..." -ForegroundColor Yellow
    
    $connectors = @(
        @{Name="PostgreSQL"; Url="https://repo1.maven.org/maven2/io/debezium/debezium-connector-postgres/$DebeziumVersion/debezium-connector-postgres-$DebeziumVersion-plugin.tar.gz"},
        @{Name="MySQL/MariaDB"; Url="https://repo1.maven.org/maven2/io/debezium/debezium-connector-mysql/$DebeziumVersion/debezium-connector-mysql-$DebeziumVersion-plugin.tar.gz"},
        @{Name="MongoDB"; Url="https://repo1.maven.org/maven2/io/debezium/debezium-connector-mongodb/$DebeziumVersion/debezium-connector-mongodb-$DebeziumVersion-plugin.tar.gz"}
    )
    
    foreach ($connector in $connectors) {
        Write-Host "   Downloading $($connector.Name) connector..." -ForegroundColor Gray
        $connectorFile = "$InstallPath\connect\$($connector.Name)-connector.tar.gz"
        try {
            Invoke-WebRequest -Uri $connector.Url -OutFile $connectorFile -TimeoutSec 300
            tar -xzf $connectorFile -C "$InstallPath\connect\plugins"
            Remove-Item $connectorFile
            Write-Host "   $($connector.Name) connector installed" -ForegroundColor Green
        } catch {
            Write-Host "   Warning: Failed to download $($connector.Name) connector: $_" -ForegroundColor Yellow
        }
    }
}

$kafkaHome = "$InstallPath\kafka-$KafkaVersion"

# Configure KRaft
Write-Host "`nConfiguring Kafka in KRaft mode..." -ForegroundColor Yellow

# Generate cluster UUID
$uuid = & "$kafkaHome\bin\windows\kafka-storage.bat" random-uuid
Write-Host "   Cluster UUID: $uuid" -ForegroundColor Gray

# Create KRaft configuration
$kraftConfigContent = @"
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.

# SYNIQ Data Lakehouse - Kafka KRaft Configuration
# Auto-generated on $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")

process.roles=broker,controller
node.id=1
controller.quorum.voters=1@localhost:9093

# Listeners
listeners=PLAINTEXT://localhost:9092,CONTROLLER://localhost:9093
advertised.listeners=PLAINTEXT://localhost:9092
controller.listener.names=CONTROLLER
inter.broker.listener.name=PLAINTEXT

# Log directories
log.dirs=$InstallPath/kafka-logs

# Auto-create topics
auto.create.topics.enable=true

# Replication settings (single broker)
offsets.topic.replication.factor=1
transaction.state.log.replication.factor=1
transaction.state.log.min.isr=1
default.replication.factor=1
min.insync.replicas=1

# Performance tuning
num.network.threads=3
num.io.threads=8
socket.send.buffer.bytes=102400
socket.receive.buffer.bytes=102400
socket.request.max.bytes=104857600

# Log retention
log.retention.hours=168
log.retention.check.interval.ms=300000
log.segment.bytes=1073741824

# Group coordinator
group.initial.rebalance.delay.ms=0
"@

$kraftConfigContent | Out-File -FilePath "$kafkaHome\config\kraft\syniq-server.properties" -Encoding UTF8
Write-Host "KRaft configuration created" -ForegroundColor Green

# Format storage
Write-Host "Formatting Kafka storage..." -ForegroundColor Yellow
& "$kafkaHome\bin\windows\kafka-storage.bat" format -t $uuid -c "$kafkaHome\config\kraft\syniq-server.properties" | Out-Null
Write-Host "Storage formatted" -ForegroundColor Green

# Create Kafka Connect configuration
Write-Host "`nConfiguring Kafka Connect..." -ForegroundColor Yellow

$connectConfigContent = @"
# SYNIQ Data Lakehouse - Kafka Connect Standalone Configuration
# Auto-generated on $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")

# Bootstrap servers
bootstrap.servers=localhost:9092

# Converters
key.converter=org.apache.kafka.connect.json.JsonConverter
value.converter=org.apache.kafka.connect.json.JsonConverter
key.converter.schemas.enable=false
value.converter.schemas.enable=false

# Offset storage
offset.storage.file.filename=$InstallPath/connect/offsets.dat
offset.flush.interval.ms=10000

# Plugin path
plugin.path=$InstallPath/connect/plugins

# REST API
rest.port=8083
rest.host.name=localhost

# Timeouts
consumer.max.poll.interval.ms=300000
consumer.session.timeout.ms=60000
"@

$connectConfigContent | Out-File -FilePath "$kafkaHome\config\syniq-connect-standalone.properties" -Encoding UTF8
Write-Host "Kafka Connect configuration created" -ForegroundColor Green

# Create startup scripts
Write-Host "`nCreating startup scripts..." -ForegroundColor Yellow

# Kafka startup script
$kafkaStartScriptContent = @"
@echo off
title Kafka Broker
cd "$kafkaHome"
echo Starting Kafka broker...
call bin\windows\kafka-server-start.bat config\kraft\syniq-server.properties
"@
$kafkaStartScriptContent | Out-File -FilePath "$InstallPath\start-kafka.bat" -Encoding ASCII

# Kafka Connect startup script
$connectStartScriptContent = @"
@echo off
title Kafka Connect
cd "$kafkaHome"
echo Starting Kafka Connect...
call bin\windows\connect-standalone.bat config\syniq-connect-standalone.properties
"@
$connectStartScriptContent | Out-File -FilePath "$InstallPath\start-connect.bat" -Encoding ASCII

Write-Host "Startup scripts created" -ForegroundColor Green

# Set environment variables
Write-Host "`nSetting environment variables..." -ForegroundColor Yellow
[Environment]::SetEnvironmentVariable("KAFKA_HOME", $kafkaHome, "Machine")
$currentPath = [Environment]::GetEnvironmentVariable("Path", "Machine")
if ($currentPath -notlike "*$kafkaHome\bin\windows*") {
    [Environment]::SetEnvironmentVariable("Path", "$currentPath;$kafkaHome\bin\windows", "Machine")
}
Write-Host "Environment variables set" -ForegroundColor Green

# Create Windows Services (optional)
if ($CreateServices) {
    Write-Host "`nInstalling as Windows Services..." -ForegroundColor Yellow
    
    # Download NSSM
    $nssmUrl = "https://nssm.cc/release/nssm-2.24.zip"
    $nssmZip = "$InstallPath\nssm.zip"
    
    if (-not (Test-Path "$InstallPath\nssm-2.24")) {
        Write-Host "   Downloading NSSM..." -ForegroundColor Gray
        Invoke-WebRequest -Uri $nssmUrl -OutFile $nssmZip
        Expand-Archive -Path $nssmZip -DestinationPath $InstallPath
        Remove-Item $nssmZip
    }
    
    $nssm = "$InstallPath\nssm-2.24\win64\nssm.exe"
    
    # Install Kafka service
    Write-Host "   Installing Kafka service..." -ForegroundColor Gray
    & $nssm install SyniqKafka "$InstallPath\start-kafka.bat"
    & $nssm set SyniqKafka AppDirectory $kafkaHome
    & $nssm set SyniqKafka DisplayName "SYNIQ Kafka Broker"
    & $nssm set SyniqKafka Description "Apache Kafka broker for SYNIQ Data Lakehouse"
    & $nssm set SyniqKafka Start SERVICE_AUTO_START
    
    # Install Kafka Connect service
    Write-Host "   Installing Kafka Connect service..." -ForegroundColor Gray
    & $nssm install SyniqKafkaConnect "$InstallPath\start-connect.bat"
    & $nssm set SyniqKafkaConnect AppDirectory $kafkaHome
    & $nssm set SyniqKafkaConnect DisplayName "SYNIQ Kafka Connect"
    & $nssm set SyniqKafkaConnect Description "Kafka Connect with Debezium for SYNIQ CDC"
    & $nssm set SyniqKafkaConnect DependOnService SyniqKafka
    & $nssm set SyniqKafkaConnect Start SERVICE_AUTO_START
    
    Write-Host "Windows services created" -ForegroundColor Green
    Write-Host "`n   You can manage services using:" -ForegroundColor Gray
    Write-Host "     Start-Service SyniqKafka" -ForegroundColor Gray
    Write-Host "     Start-Service SyniqKafkaConnect" -ForegroundColor Gray
    Write-Host "     Stop-Service SyniqKafka" -ForegroundColor Gray
    Write-Host "     Stop-Service SyniqKafkaConnect" -ForegroundColor Gray
}

# Summary
Write-Host "`n================================================================" -ForegroundColor Green
Write-Host "             Installation Complete!                     " -ForegroundColor Green
Write-Host "================================================================`n" -ForegroundColor Green

Write-Host "Installation Location:" -ForegroundColor Cyan
Write-Host "   $kafkaHome`n" -ForegroundColor White

Write-Host "To start services manually:" -ForegroundColor Cyan
Write-Host "   Kafka:         $InstallPath\start-kafka.bat" -ForegroundColor White
Write-Host "   Kafka Connect: $InstallPath\start-connect.bat`n" -ForegroundColor White

if ($CreateServices) {
    Write-Host "Services installed and ready to start:" -ForegroundColor Cyan
    Write-Host "   Start-Service SyniqKafka" -ForegroundColor White
    Write-Host "   Start-Service SyniqKafkaConnect`n" -ForegroundColor White
}

Write-Host "Access Points:" -ForegroundColor Cyan
Write-Host "   Kafka Broker:     localhost:9092" -ForegroundColor White
Write-Host "   Kafka Connect:    http://localhost:8083`n" -ForegroundColor White

Write-Host "Test connection:" -ForegroundColor Cyan
Write-Host "   cd $kafkaHome" -ForegroundColor White
Write-Host "   .\bin\windows\kafka-topics.bat --bootstrap-server localhost:9092 --list`n" -ForegroundColor White

Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "   1. Start Kafka broker" -ForegroundColor White
Write-Host "   2. Start Kafka Connect" -ForegroundColor White
Write-Host "   3. Update your application .env file (already configured for localhost:9092)" -ForegroundColor White
Write-Host "   4. Remove Docker files from your project" -ForegroundColor White
Write-Host "`nHappy streaming!" -ForegroundColor Magenta
