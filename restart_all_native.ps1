# ============================================================================
# SyniqAI - Complete System Restart (Native Services - NO DOCKER)
# ============================================================================
# Stops all services, restarts Kafka, and starts AI processor
# ============================================================================

Write-Host ""
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "   SyniqAI Complete System Restart (Native Mode)" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Stop All Running Services
Write-Host "[STEP 1/5] Stopping all services..." -ForegroundColor Yellow
Write-Host "  - Stopping AI Processor (Python)..." -ForegroundColor Gray
Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue

Write-Host "  - Stopping Kafka (Java)..." -ForegroundColor Gray
Get-Process java -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue

Start-Sleep -Seconds 3
Write-Host "[+] All services stopped" -ForegroundColor Green
Write-Host ""

# Step 2: Verify Kafka Configuration
Write-Host "[STEP 2/5] Verifying Kafka IPv4 configuration..." -ForegroundColor Yellow
$kafkaConfigFile = "C:\kafka\kafka-4.2.0\config\kraft\syniq-server.properties"

if (Test-Path $kafkaConfigFile) {
    $configContent = Get-Content $kafkaConfigFile -Raw
    
    if ($configContent -match 'advertised\.listeners=PLAINTEXT://127\.0\.0\.1:9092') {
        Write-Host "[+] Kafka configured for IPv4 - 127.0.0.1:9092" -ForegroundColor Green
    } else {
        Write-Host "[!] Fixing Kafka configuration..." -ForegroundColor Yellow
        $configContent = $configContent -replace 'advertised\.listeners=PLAINTEXT://localhost:9092', 'advertised.listeners=PLAINTEXT://127.0.0.1:9092'
        Set-Content $kafkaConfigFile $configContent -NoNewline
        Write-Host "[+] Updated advertised.listeners to 127.0.0.1:9092" -ForegroundColor Green
    }
} else {
    Write-Host "[!] Warning: Kafka config not found" -ForegroundColor Yellow
    Write-Host "    Location: $kafkaConfigFile" -ForegroundColor Gray
}
Write-Host ""

# Step 3: Start Kafka Broker
Write-Host "[STEP 3/5] Starting Kafka broker..." -ForegroundColor Yellow
$kafkaStartScript = "C:\kafka\kafka-4.2.0\bin\windows\kafka-server-start.bat"

if (Test-Path $kafkaStartScript) {
    Start-Process -FilePath $kafkaStartScript -ArgumentList $kafkaConfigFile -WindowStyle Minimized
    
    Write-Host "  - Kafka process started (minimized window)" -ForegroundColor Gray
    Write-Host "  - Waiting for broker to be ready..." -ForegroundColor Gray
    
    # Wait for Kafka to be ready (max 60 seconds)
    $maxWait = 60
    $waited = 0
    $ready = $false
    
    while ($waited -lt $maxWait -and -not $ready) {
        Start-Sleep -Seconds 2
        $waited += 2
        
        try {
            $conn = New-Object System.Net.Sockets.TcpClient
            $conn.Connect("127.0.0.1", 9092)
            $conn.Close()
            $ready = $true
            Write-Host "[+] Kafka broker is ready on 127.0.0.1:9092" -ForegroundColor Green
        } catch {
            Write-Host "." -NoNewline -ForegroundColor Gray
        }
    }
    
    if (-not $ready) {
        Write-Host ""
        Write-Host "[!] Warning: Kafka took longer than expected" -ForegroundColor Yellow
        Write-Host "    Check C:\kafka\kafka-4.2.0\logs for errors" -ForegroundColor Gray
    }
} else {
    Write-Host "[!] Error: Kafka startup script not found" -ForegroundColor Red
    Write-Host "    Expected: $kafkaStartScript" -ForegroundColor Gray
    exit 1
}
Write-Host ""

# Step 4: Verify .env Configuration
Write-Host "[STEP 4/5] Verifying .env configuration..." -ForegroundColor Yellow
$envFile = ".\.env"

if (Test-Path $envFile) {
    $envContent = Get-Content $envFile -Raw
    
    if ($envContent -match 'KAFKA_BOOTSTRAP_SERVERS=127\.0\.0\.1:9092') {
        Write-Host "[+] .env configured correctly - 127.0.0.1:9092" -ForegroundColor Green
    } else {
        Write-Host "[!] Warning: .env may need updating" -ForegroundColor Yellow
        Write-Host "    Expected: KAFKA_BOOTSTRAP_SERVERS=127.0.0.1:9092" -ForegroundColor Gray
    }
} else {
    Write-Host "[!] Warning: .env file not found" -ForegroundColor Yellow
}
Write-Host ""

# Step 5: Start AI Processor
Write-Host "[STEP 5/5] Starting AI Processor..." -ForegroundColor Yellow
Write-Host "  - Location: ai processing\ai_processor.py" -ForegroundColor Gray
Write-Host "  - This will run in the foreground..." -ForegroundColor Gray
Write-Host ""

Start-Sleep -Seconds 2

Write-Host "================================================================" -ForegroundColor Green
Write-Host "              System Restart Complete!" -ForegroundColor Green
Write-Host "================================================================" -ForegroundColor Green
Write-Host "  Kafka Broker:    127.0.0.1:9092         [RUNNING]" -ForegroundColor Green
Write-Host "  Kafka UI:        http://localhost:8080  [ACCESSIBLE]" -ForegroundColor Green
Write-Host "  MinIO API:       localhost:9000         [CONFIGURED]" -ForegroundColor Green
Write-Host "  MinIO Console:   http://localhost:9001  [ACCESSIBLE]" -ForegroundColor Green
Write-Host "================================================================" -ForegroundColor Green
Write-Host "  AI Processor will start now..." -ForegroundColor Green
Write-Host "  Press Ctrl+C to stop" -ForegroundColor Green
Write-Host "================================================================" -ForegroundColor Green
Write-Host ""

# Start AI Processor in foreground
Set-Location "Kafka Integration"
python ai_processor.py
