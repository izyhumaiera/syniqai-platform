# ============================================================================
# Start Kafka Connect with Debezium Support
# ============================================================================
# This script starts Kafka Connect which is required for Debezium CDC
# ============================================================================

Write-Host ""
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "   Starting Kafka Connect (Debezium)" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Check if Kafka is running
Write-Host "[1/4] Checking Kafka Broker..." -ForegroundColor Yellow
$kafkaTest = Test-NetConnection -ComputerName 127.0.0.1 -Port 9092 -WarningAction SilentlyContinue -ErrorAction SilentlyContinue

if ($kafkaTest.TcpTestSucceeded) {
    Write-Host "  ✓ Kafka broker is running on 127.0.0.1:9092" -ForegroundColor Green
} else {
    Write-Host "  ✗ Kafka broker is NOT running!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please start Kafka first:" -ForegroundColor Yellow
    Write-Host "  cd C:\kafka\kafka-4.2.0" -ForegroundColor White
    Write-Host "  .\bin\windows\kafka-server-start.bat .\config\kraft\syniq-server.properties" -ForegroundColor White
    Write-Host ""
    exit 1
}
Write-Host ""

# Step 2: Check if Kafka Connect is already running
Write-Host "[2/4] Checking if Kafka Connect is already running..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "http://localhost:8083/" -Method Get -TimeoutSec 3 -ErrorAction SilentlyContinue
    if ($response) {
        Write-Host "  ✓ Kafka Connect is already running!" -ForegroundColor Green
        Write-Host "  Version: $($response.version)" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "No action needed. Kafka Connect is ready." -ForegroundColor Green
        exit 0
    }
} catch {
    Write-Host "  → Kafka Connect is not running yet" -ForegroundColor Gray
}
Write-Host ""

# Step 3: Verify configuration and plugins
Write-Host "[3/4] Verifying configuration..." -ForegroundColor Yellow
$kafkaHome = "C:\kafka\kafka-4.2.0"
$connectConfig = "$kafkaHome\config\connect-standalone-native.properties"
$pluginsDir = "$kafkaHome\plugins"

if (-not (Test-Path $connectConfig)) {
    Write-Host "  ✗ Config file not found: $connectConfig" -ForegroundColor Red
    exit 1
}
Write-Host "  ✓ Config file exists: $connectConfig" -ForegroundColor Green

if (Test-Path $pluginsDir) {
    $plugins = Get-ChildItem -Path $pluginsDir -Directory
    Write-Host "  ✓ Plugins directory: $pluginsDir ($($plugins.Count) plugins)" -ForegroundColor Green
    foreach ($plugin in $plugins) {
        Write-Host "    - $($plugin.Name)" -ForegroundColor Gray
    }
} else {
    Write-Host "  ⚠ Plugins directory not found: $pluginsDir" -ForegroundColor Yellow
}
Write-Host ""

# Step 4: Start Kafka Connect
Write-Host "[4/4] Starting Kafka Connect..." -ForegroundColor Yellow
$startScript = "$kafkaHome\bin\windows\connect-standalone.bat"

if (-not (Test-Path $startScript)) {
    Write-Host "  ✗ Start script not found: $startScript" -ForegroundColor Red
    exit 1
}

Write-Host "  → Launching Kafka Connect (this may take 30-60 seconds)..." -ForegroundColor Gray
Write-Host "  → The process will run in a minimized window" -ForegroundColor Gray
Write-Host ""

# Start Kafka Connect in a new window (minimized)
Start-Process -FilePath $startScript -ArgumentList $connectConfig -WindowStyle Minimized

Write-Host "  ✓ Kafka Connect process started" -ForegroundColor Green
Write-Host ""
Write-Host "Waiting for Kafka Connect REST API to become available..." -ForegroundColor Yellow
Write-Host ""

# Wait for Kafka Connect to be ready (max 60 seconds)
$maxAttempts = 20
$attempt = 0
$ready = $false

while ($attempt -lt $maxAttempts -and -not $ready) {
    Start-Sleep -Seconds 3
    $attempt++
    
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:8083/" -Method Get -TimeoutSec 3 -ErrorAction SilentlyContinue
        if ($response) {
            $ready = $true
            Write-Host ""
            Write-Host "================================================================" -ForegroundColor Green
            Write-Host "   ✓ Kafka Connect is READY!" -ForegroundColor Green
            Write-Host "================================================================" -ForegroundColor Green
            Write-Host ""
            Write-Host "Kafka Connect Info:" -ForegroundColor Cyan
            Write-Host "  Version: $($response.version)" -ForegroundColor White
            Write-Host "  Commit:  $($response.commit)" -ForegroundColor White
            Write-Host "  REST API: http://localhost:8083" -ForegroundColor White
            Write-Host ""
            
            # Check for Debezium plugins
            try {
                $connectors = Invoke-RestMethod -Uri "http://localhost:8083/connector-plugins" -Method Get -TimeoutSec 3
                $debeziumConnectors = $connectors | Where-Object { $_.class -like "*debezium*" }
                
                if ($debeziumConnectors) {
                    Write-Host "Debezium Connectors Available:" -ForegroundColor Cyan
                    foreach ($conn in $debeziumConnectors) {
                        Write-Host "  ✓ $($conn.class)" -ForegroundColor Green
                    }
                } else {
                    Write-Host "⚠ No Debezium connectors found" -ForegroundColor Yellow
                }
            } catch {
                Write-Host "⚠ Could not check connector plugins" -ForegroundColor Yellow
            }
            
            Write-Host ""
            Write-Host "Next Steps:" -ForegroundColor Cyan
            Write-Host "  1. Open your GUI at http://localhost:3000" -ForegroundColor White
            Write-Host "  2. Go to the CDC/Real-time tab" -ForegroundColor White
            Write-Host "  3. Click 'Refresh' to see Kafka Connect status" -ForegroundColor White
            Write-Host ""
        }
    } catch {
        Write-Host "." -NoNewline -ForegroundColor Gray
    }
}

if (-not $ready) {
    Write-Host ""
    Write-Host "⚠ Kafka Connect is taking longer than expected to start" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "This is normal on first startup. Please wait 1-2 minutes more." -ForegroundColor Gray
    Write-Host ""
    Write-Host "To check status manually:" -ForegroundColor Cyan
    Write-Host "  curl http://localhost:8083/" -ForegroundColor White
    Write-Host ""
    Write-Host "To view logs:" -ForegroundColor Cyan
    Write-Host "  Check the Kafka Connect window or logs in: $kafkaHome\logs" -ForegroundColor Gray
    Write-Host ""
}
