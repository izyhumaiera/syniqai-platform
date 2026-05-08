# ============================================================================
# SYNIQ - Stop Native Kafka Services
# ============================================================================
# Stops Kafka and Kafka Connect running natively
# ============================================================================

Write-Host "`n=== Stopping SYNIQ Kafka Services ===`n" -ForegroundColor Cyan

# Function to stop process by port
function Stop-ProcessByPort {
    param([int]$Port)
    
    $connection = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
    if ($connection) {
        $processId = $connection.OwningProcess
        $process = Get-Process -Id $processId -ErrorAction SilentlyContinue
        if ($process) {
            Write-Host "Stopping process on port $Port (PID: $processId)..." -ForegroundColor Yellow
            Stop-Process -Id $processId -Force
            Write-Host "✓ Process stopped" -ForegroundColor Green
            return $true
        }
    }
    return $false
}

# Stop services if they exist
$kafkaService = Get-Service -Name "SyniqKafka" -ErrorAction SilentlyContinue
$connectService = Get-Service -Name "SyniqKafkaConnect" -ErrorAction SilentlyContinue

if ($connectService -and $connectService.Status -eq "Running") {
    Write-Host "Stopping Kafka Connect service..." -ForegroundColor Yellow
    Stop-Service -Name "SyniqKafkaConnect" -Force
    Write-Host "✓ Kafka Connect service stopped" -ForegroundColor Green
} else {
    # Try to stop by port
    $stopped = Stop-ProcessByPort -Port 8083
    if (-not $stopped) {
        Write-Host "Kafka Connect is not running" -ForegroundColor Gray
    }
}

if ($kafkaService -and $kafkaService.Status -eq "Running") {
    Write-Host "Stopping Kafka service..." -ForegroundColor Yellow
    Stop-Service -Name "SyniqKafka" -Force
    Write-Host "✓ Kafka service stopped" -ForegroundColor Green
} else {
    # Try to stop by port
    $stopped = Stop-ProcessByPort -Port 9092
    if (-not $stopped) {
        Write-Host "Kafka broker is not running" -ForegroundColor Gray
    }
}

# Also stop any remaining kafka processes
$kafkaProcesses = Get-Process | Where-Object { $_.Name -like "*kafka*" -or $_.Name -like "*zookeeper*" }
if ($kafkaProcesses) {
    Write-Host "`nStopping remaining Kafka processes..." -ForegroundColor Yellow
    $kafkaProcesses | ForEach-Object {
        Write-Host "  Stopping $($_.Name) (PID: $($_.Id))" -ForegroundColor Gray
        Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
    }
    Write-Host "✓ All Kafka processes stopped" -ForegroundColor Green
}

Write-Host "`n✓ Kafka services stopped successfully`n" -ForegroundColor Green
