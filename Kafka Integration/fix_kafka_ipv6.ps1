# ============================================================================
# Fix Kafka IPv6 Connection Timeout Issue
# ============================================================================
# Changes advertised.listeners from localhost to 127.0.0.1 to force IPv4
# ============================================================================

Write-Host "`n=== Fixing Kafka IPv6 Connection Issue ===`n" -ForegroundColor Cyan

$kafkaHome = "C:\kafka\kafka-4.2.0"
$configFile = "$kafkaHome\config\kraft\syniq-server.properties"

# Step 1: Check if Kafka config exists
if (-not (Test-Path $configFile)) {
    Write-Host "[-] Kafka config not found at: $configFile" -ForegroundColor Red
    Write-Host "    Please update KAFKA_HOME path in this script" -ForegroundColor Yellow
    exit 1
}

Write-Host "[1/3] Backing up Kafka configuration..." -ForegroundColor Yellow
Copy-Item $configFile "$configFile.backup.$(Get-Date -Format 'yyyyMMdd-HHmmss')" -Force
Write-Host "      Backed up to: $configFile.backup.*" -ForegroundColor Gray

# Step 2: Update advertised.listeners
Write-Host "[2/3] Updating advertised.listeners to use IPv4..." -ForegroundColor Yellow

$content = Get-Content $configFile -Raw

# Replace localhost with 127.0.0.1 in advertised.listeners
$content = $content -replace 'advertised\.listeners=PLAINTEXT://localhost:9092', 'advertised.listeners=PLAINTEXT://127.0.0.1:9092'

Set-Content $configFile $content -NoNewline

Write-Host "      Changed: localhost:9092 -> 127.0.0.1:9092" -ForegroundColor Green

# Step 3: Show what needs to be done
Write-Host "[3/3] Restart Kafka to apply changes..." -ForegroundColor Yellow
Write-Host ""
Write-Host "      MANUAL STEPS REQUIRED:" -ForegroundColor Cyan
Write-Host "      1. Stop Kafka (if running as service or background process)" -ForegroundColor White
Write-Host "      2. Start Kafka with native startup script:" -ForegroundColor White
Write-Host "         cd 'Kafka Integration'" -ForegroundColor Gray
Write-Host "         .\start_kafka_native.ps1" -ForegroundColor Gray
Write-Host ""
Write-Host "=== Configuration Updated ===" -ForegroundColor Green
Write-Host "After restarting Kafka, ai_processor.py should connect without IPv6 timeouts" -ForegroundColor Green
Write-Host ""
