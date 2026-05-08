#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Start Kafka Connect for Native Kafka

.DESCRIPTION
    Starts Kafka Connect to enable Debezium CDC connectors with native Kafka at localhost:9092
#>

$KAFKA_HOME = "C:\kafka\kafka-4.2.0"

Write-Host ""
Write-Host "Starting Kafka Connect for Native Kafka..." -ForegroundColor Cyan
Write-Host ""

# Check if Kafka is running
Write-Host "Checking native Kafka broker..." -ForegroundColor Yellow
$kafkaTest = Test-NetConnection -ComputerName 127.0.0.1 -Port 9092 -WarningAction SilentlyContinue
if (-not $kafkaTest.TcpTestSucceeded) {
    Write-Host "[ERROR] Kafka broker not running at localhost:9092" -ForegroundColor Red
    Write-Host "Start Kafka first: cd C:\kafka\kafka-4.2.0; .\bin\windows\kafka-server-start.bat config\syniq-server.properties" -ForegroundColor Yellow
    exit 1
}
Write-Host "  Kafka broker: RUNNING" -ForegroundColor Green
Write-Host ""

# Check if configuration exists
$connectConfig = "$KAFKA_HOME\config\connect-standalone-native.properties"
if (-not (Test-Path $connectConfig)) {
    Write-Host "[ERROR] Kafka Connect configuration not found" -ForegroundColor Red
    Write-Host "Run setup first: .\setup_kafka_connect_native.ps1" -ForegroundColor Yellow
    exit 1
}

Write-Host "Starting Kafka Connect..." -ForegroundColor Yellow
Write-Host "  Config: $connectConfig" -ForegroundColor Gray
Write-Host "  API: http://localhost:8083" -ForegroundColor Gray
Write-Host ""
Write-Host "Press Ctrl+C to stop Kafka Connect" -ForegroundColor Yellow
Write-Host ""

# Start Kafka Connect
Set-Location $KAFKA_HOME
.\bin\windows\connect-standalone.bat $connectConfig
