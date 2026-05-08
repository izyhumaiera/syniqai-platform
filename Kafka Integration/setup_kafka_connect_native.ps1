#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Setup Kafka Connect for Native Kafka Installation

.DESCRIPTION
    This script sets up Kafka Connect to work with your native Kafka broker at localhost:9092.
    Kafka Connect is required for Debezium CDC connectors.
#>

Write-Host ""
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "          KAFKA CONNECT SETUP FOR NATIVE KAFKA" -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host ""

$KAFKA_HOME = "C:\kafka\kafka-4.2.0"
$CONNECT_PLUGINS_DIR = "$KAFKA_HOME\plugins"

# Check if Kafka is installed
if (-not (Test-Path $KAFKA_HOME)) {
    Write-Host "[ERROR] Kafka not found at $KAFKA_HOME" -ForegroundColor Red
    Write-Host "Please verify your Kafka installation path." -ForegroundColor Yellow
    exit 1
}

Write-Host "[1/5] Creating plugins directory..." -ForegroundColor Yellow
if (-not (Test-Path $CONNECT_PLUGINS_DIR)) {
    New-Item -ItemType Directory -Path $CONNECT_PLUGINS_DIR -Force | Out-Null
    Write-Host "  Created: $CONNECT_PLUGINS_DIR" -ForegroundColor Green
} else {
    Write-Host "  Already exists: $CONNECT_PLUGINS_DIR" -ForegroundColor Green
}
Write-Host ""

Write-Host "[2/5] Checking for Debezium connectors..." -ForegroundColor Yellow
$postgresConnector = "$CONNECT_PLUGINS_DIR\debezium-connector-postgresql"
$mysqlConnector = "$CONNECT_PLUGINS_DIR\debezium-connector-mysql"

$needsDownload = $false

if (-not (Test-Path $postgresConnector)) {
    Write-Host "  PostgreSQL connector: NOT FOUND" -ForegroundColor Yellow
    $needsDownload = $true
} else {
    Write-Host "  PostgreSQL connector: FOUND" -ForegroundColor Green
}

if (-not (Test-Path $mysqlConnector)) {
    Write-Host "  MySQL connector: NOT FOUND" -ForegroundColor Yellow
    $needsDownload = $true
} else {
    Write-Host "  MySQL connector: FOUND" -ForegroundColor Green
}
Write-Host ""

if ($needsDownload) {
    Write-Host "[3/5] Download Debezium connectors manually:" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  1. PostgreSQL Connector:" -ForegroundColor Cyan
    Write-Host "     URL: https://repo1.maven.org/maven2/io/debezium/debezium-connector-postgres/2.4.0.Final/debezium-connector-postgres-2.4.0.Final-plugin.tar.gz" -ForegroundColor Gray
    Write-Host "     Extract to: $postgresConnector" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  2. MySQL Connector:" -ForegroundColor Cyan
    Write-Host "     URL: https://repo1.maven.org/maven2/io/debezium/debezium-connector-mysql/2.4.0.Final/debezium-connector-mysql-2.4.0.Final-plugin.tar.gz" -ForegroundColor Gray
    Write-Host "     Extract to: $mysqlConnector" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  Or use Confluent Hub (if installed):" -ForegroundColor Cyan
    Write-Host "     confluent-hub install debezium/debezium-connector-postgresql:2.4.0 --component-dir $CONNECT_PLUGINS_DIR" -ForegroundColor Gray
    Write-Host "     confluent-hub install debezium/debezium-connector-mysql:2.4.0 --component-dir $CONNECT_PLUGINS_DIR" -ForegroundColor Gray
    Write-Host ""
} else {
    Write-Host "[3/5] Connectors already installed" -ForegroundColor Green
    Write-Host ""
}

Write-Host "[4/5] Creating Kafka Connect configuration..." -ForegroundColor Yellow
$connectConfig = @"
# Native Kafka Connect Configuration for Native Kafka Broker
# Bootstrap servers point to native Kafka at localhost:9092

bootstrap.servers=localhost:9092

# Plugin path for Debezium connectors
plugin.path=$CONNECT_PLUGINS_DIR

# Kafka Connect REST API
rest.port=8083
rest.host.name=localhost

# Group ID for this Connect cluster
group.id=kafka-connect-cluster

# Topics for storing connector state
config.storage.topic=connect-configs
config.storage.replication.factor=1

offset.storage.topic=connect-offsets
offset.storage.replication.factor=1

status.storage.topic=connect-status
status.storage.replication.factor=1

# Key and value converters
key.converter=org.apache.kafka.connect.json.JsonConverter
value.converter=org.apache.kafka.connect.json.JsonConverter
key.converter.schemas.enable=false
value.converter.schemas.enable=false

# Internal key and value converters
internal.key.converter=org.apache.kafka.connect.json.JsonConverter
internal.value.converter=org.apache.kafka.connect.json.JsonConverter
internal.key.converter.schemas.enable=false
internal.value.converter.schemas.enable=false
"@

$connectPropsFile = "$KAFKA_HOME\config\connect-standalone-native.properties"
$connectConfig | Out-File -FilePath $connectPropsFile -Encoding UTF8
Write-Host "  Created: $connectPropsFile" -ForegroundColor Green
Write-Host ""

Write-Host "[5/5] Setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "================================================================================" -ForegroundColor Green
Write-Host "          KAFKA CONNECT CONFIGURATION READY" -ForegroundColor Green
Write-Host "================================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "To start Kafka Connect:" -ForegroundColor Cyan
Write-Host "  cd $KAFKA_HOME" -ForegroundColor White
Write-Host "  .\bin\windows\connect-standalone.bat config\connect-standalone-native.properties" -ForegroundColor Yellow
Write-Host ""
Write-Host "Or create a start script:" -ForegroundColor Cyan
Write-Host "  cd 'Kafka Integration'" -ForegroundColor White
Write-Host "  .\start_kafka_connect.ps1" -ForegroundColor Yellow
Write-Host ""
Write-Host "After Kafka Connect is running:" -ForegroundColor Cyan
Write-Host "  1. Verify: http://localhost:8083/" -ForegroundColor White
Write-Host "  2. Setup databases: .\fix_debezium_permissions_local.py" -ForegroundColor White
Write-Host "  3. Create connectors: python debezium_manager.py" -ForegroundColor White
Write-Host ""
Write-Host "Current Setup:" -ForegroundColor Cyan
Write-Host "  Kafka Broker:     localhost:9092 (Native, Running)" -ForegroundColor Gray
Write-Host "  Kafka Connect:    localhost:8083 (Not started yet)" -ForegroundColor Gray
Write-Host "  PostgreSQL:       localhost:5432" -ForegroundColor Gray
Write-Host "  MinIO:            localhost:9000" -ForegroundColor Gray
Write-Host ""
