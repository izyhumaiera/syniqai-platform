# ============================================================================
# SYNIQ Complete System Restart Script
# ============================================================================
# Checks and starts Kafka, then launches AI Processor
# NO DOCKER - Native Windows Services Only
# ============================================================================

param(
    [switch]$ForceRestart,
    [int]$KafkaWaitSeconds = 30
)

$ErrorActionPreference = "Continue"

Write-Host "`n" -NoNewline
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "         SYNIQ AI PROCESSOR - SYSTEM RESTART" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

# Configuration
$KAFKA_HOME = "C:\kafka\kafka-4.2.0"
$KAFKA_CONFIG = "$KAFKA_HOME\config\kraft\syniq-server.properties"
$KAFKA_PORT = 9092
$KAFKA_HOST = "127.0.0.1"

# ============================================================================
# Step 1: Check if Kafka is already running
# ============================================================================

Write-Host "[1/5] Checking Kafka status..." -ForegroundColor Yellow

function Test-KafkaRunning {
    try {
        $connection = Test-NetConnection -ComputerName $KAFKA_HOST -Port $KAFKA_PORT -WarningAction SilentlyContinue -ErrorAction SilentlyContinue -InformationLevel Quiet
        return $connection
    } catch {
        return $false
    }
}

$kafkaRunning = Test-KafkaRunning

if ($kafkaRunning) {
    Write-Host "      [✓] Kafka is already running on ${KAFKA_HOST}:${KAFKA_PORT}" -ForegroundColor Green
    
    if ($ForceRestart) {
        Write-Host "      [!] Force restart requested - stopping Kafka..." -ForegroundColor Yellow
        
        # Kill all Java processes (Kafka runs on Java)
        Get-Process java -ErrorAction SilentlyContinue | ForEach-Object {
            Write-Host "      Stopping process: $($_.Id)" -ForegroundColor Gray
            Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
        }
        
        Start-Sleep -Seconds 3
        $kafkaRunning = $false
        Write-Host "      [✓] Kafka stopped" -ForegroundColor Green
    } else {
        Write-Host "      [→] Skipping Kafka startup (use -ForceRestart to restart)" -ForegroundColor Gray
    }
} else {
    Write-Host "      [!] Kafka is NOT running" -ForegroundColor Yellow
}

# ============================================================================
# Step 2: Start Kafka if not running
# ============================================================================

if (-not $kafkaRunning) {
    Write-Host ""
    Write-Host "[2/5] Starting Kafka broker..." -ForegroundColor Yellow
    
    # Verify Kafka installation
    if (-not (Test-Path $KAFKA_HOME)) {
        Write-Host "      [✗] ERROR: Kafka not found at $KAFKA_HOME" -ForegroundColor Red
        Write-Host "      Please install Kafka or update KAFKA_HOME path in script" -ForegroundColor Red
        exit 1
    }
    
    if (-not (Test-Path $KAFKA_CONFIG)) {
        Write-Host "      [✗] ERROR: Kafka config not found at $KAFKA_CONFIG" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "      Kafka Home: $KAFKA_HOME" -ForegroundColor Gray
    Write-Host "      Config: $KAFKA_CONFIG" -ForegroundColor Gray
    
    # Start Kafka in a new minimized window
    try {
        $kafkaStartScript = "$KAFKA_HOME\bin\windows\kafka-server-start.bat"
        
        $processInfo = Start-Process -FilePath $kafkaStartScript `
            -ArgumentList "`"$KAFKA_CONFIG`"" `
            -WindowStyle Minimized `
            -PassThru
        
        Write-Host "      [✓] Kafka process started (PID: $($processInfo.Id))" -ForegroundColor Green
        Write-Host "      [→] Waiting for Kafka to be ready..." -ForegroundColor Gray
        
    } catch {
        Write-Host "      [✗] Failed to start Kafka: $_" -ForegroundColor Red
        exit 1
    }
    
} else {
    Write-Host ""
    Write-Host "[2/5] Kafka already running - skip startup" -ForegroundColor Gray
}

# ============================================================================
# Step 3: Wait for Kafka to be ready
# ============================================================================

Write-Host ""
Write-Host "[3/5] Waiting for Kafka port ${KAFKA_PORT} to be ready..." -ForegroundColor Yellow

$maxAttempts = $KafkaWaitSeconds
$attempt = 0
$ready = $false

while ($attempt -lt $maxAttempts -and -not $ready) {
    $attempt++
    
    Write-Host "      Attempt $attempt/$maxAttempts... " -NoNewline -ForegroundColor Gray
    
    $ready = Test-KafkaRunning
    
    if ($ready) {
        Write-Host "[✓] READY" -ForegroundColor Green
        break
    } else {
        Write-Host "[•] waiting..." -ForegroundColor Yellow
        Start-Sleep -Seconds 1
    }
}

if (-not $ready) {
    Write-Host ""
    Write-Host "      [✗] ERROR: Kafka did not become ready within ${KafkaWaitSeconds} seconds" -ForegroundColor Red
    Write-Host "      Check Kafka logs at: $KAFKA_HOME\logs" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "      Manual start command:" -ForegroundColor Cyan
    Write-Host "      cd `"$KAFKA_HOME`"" -ForegroundColor White
    Write-Host "      .\bin\windows\kafka-server-start.bat `"$KAFKA_CONFIG`"" -ForegroundColor White
    exit 1
}

Write-Host "      [✓] Kafka broker is ready at ${KAFKA_HOST}:${KAFKA_PORT}" -ForegroundColor Green

# ============================================================================
# Step 4: Verify Kafka connectivity with Python client
# ============================================================================

Write-Host ""
Write-Host "[4/5] Testing Kafka connectivity with Python..." -ForegroundColor Yellow

$testScript = @"
import socket
import sys
try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(3)
    result = sock.connect_ex(('$KAFKA_HOST', $KAFKA_PORT))
    sock.close()
    if result == 0:
        print('CONNECTED')
        sys.exit(0)
    else:
        print('FAILED')
        sys.exit(1)
except Exception as e:
    print('ERROR: ' + str(e))
    sys.exit(1)
"@

$testResult = python -c $testScript 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "      [✓] Python can connect to Kafka" -ForegroundColor Green
} else {
    Write-Host "      [!] Warning: Python connection test failed: $testResult" -ForegroundColor Yellow
    Write-Host "      Proceeding anyway..." -ForegroundColor Gray
}

# ============================================================================
# Step 5: Start AI Processor
# ============================================================================

Write-Host ""
Write-Host "[5/5] Starting AI Processor..." -ForegroundColor Yellow
Write-Host ""

# Change to project root directory
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptDir
Set-Location $projectRoot

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "         AI PROCESSOR STARTING" -ForegroundColor Green
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Kafka:        ${KAFKA_HOST}:${KAFKA_PORT}" -ForegroundColor White
Write-Host "  Bronze Topic: bronze-ready" -ForegroundColor White
Write-Host "  Silver Topic: silver-ready" -ForegroundColor White
Write-Host ""
Write-Host "  Press Ctrl+C to stop" -ForegroundColor Gray
Write-Host ""
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

# Start AI processor (blocking - runs in foreground)
python "ai processing\ai_processor.py"

# This line only runs if ai_processor exits or is interrupted
Write-Host ""
Write-Host "================================================================" -ForegroundColor Yellow
Write-Host "  AI Processor stopped" -ForegroundColor Yellow
Write-Host "================================================================" -ForegroundColor Yellow
