# ============================================================================
# SYNIQ - Services Connection Verification
# ============================================================================
# This script verifies connectivity between Kafka UI, MinIO, and Kafka Broker
# ============================================================================

$ErrorActionPreference = "SilentlyContinue"

Write-Host ""
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "   SYNIQ Data Platform - Connection Verification" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

# Test all services
Write-Host "Testing service connectivity..." -ForegroundColor Yellow
Write-Host ""

# Kafka Broker
$kafkaTest = Test-NetConnection -ComputerName 127.0.0.1 -Port 9092 -WarningAction SilentlyContinue -ErrorAction SilentlyContinue
if ($kafkaTest.TcpTestSucceeded) {
    Write-Host "  ✓ CONNECTED  " -ForegroundColor Green -NoNewline
    Write-Host "Kafka Broker".PadRight(20) -NoNewline
    Write-Host "127.0.0.1:9092" -ForegroundColor White
} else {
    Write-Host "  ✗ OFFLINE    " -ForegroundColor Red -NoNewline
    Write-Host "Kafka Broker".PadRight(20) -NoNewline
    Write-Host "127.0.0.1:9092 (Not running)" -ForegroundColor Gray
}

# Kafka UI
$uiTest = Test-NetConnection -ComputerName localhost -Port 8080 -WarningAction SilentlyContinue -ErrorAction SilentlyContinue
if ($uiTest.TcpTestSucceeded) {
    Write-Host "  ✓ CONNECTED  " -ForegroundColor Green -NoNewline
    Write-Host "Kafka UI".PadRight(20) -NoNewline
    Write-Host "http://localhost:8080" -ForegroundColor Cyan
} else {
    Write-Host "  ✗ OFFLINE    " -ForegroundColor Red -NoNewline
    Write-Host "Kafka UI".PadRight(20) -NoNewline
    Write-Host "localhost:8080 (Not running)" -ForegroundColor Gray
}

# MinIO API  
$minioAPITest = Test-NetConnection -ComputerName localhost -Port 9000 -WarningAction SilentlyContinue -ErrorAction SilentlyContinue
if ($minioAPITest.TcpTestSucceeded) {
    Write-Host "  ✓ CONNECTED  " -ForegroundColor Green -NoNewline
    Write-Host "MinIO API".PadRight(20) -NoNewline
    Write-Host "localhost:9000" -ForegroundColor White
} else {
    Write-Host "  ✗ OFFLINE    " -ForegroundColor Red -NoNewline
    Write-Host "MinIO API".PadRight(20) -NoNewline
    Write-Host "localhost:9000 (Not running)" -ForegroundColor Gray
}

# MinIO Console
$minioConsoleTest = Test-NetConnection -ComputerName localhost -Port 9001 -WarningAction SilentlyContinue -ErrorAction SilentlyContinue
if ($minioConsoleTest.TcpTestSucceeded) {
    Write-Host "  ✓ CONNECTED  " -ForegroundColor Green -NoNewline
    Write-Host "MinIO Console".PadRight(20) -NoNewline
    Write-Host "http://localhost:9001" -ForegroundColor Cyan
} else {
    Write-Host "  ✗ OFFLINE    " -ForegroundColor Red -NoNewline
    Write-Host "MinIO Console".PadRight(20) -NoNewline
    Write-Host "localhost:9001 (Not running)" -ForegroundColor Gray
}

# PostgreSQL
$postgresTest = Test-NetConnection -ComputerName localhost -Port 5432 -WarningAction SilentlyContinue -ErrorAction SilentlyContinue
if ($postgresTest.TcpTestSucceeded) {
    Write-Host "  ✓ CONNECTED  " -ForegroundColor Green -NoNewline
    Write-Host "PostgreSQL".PadRight(20) -NoNewline
    Write-Host "localhost:5432" -ForegroundColor White
} else {
    Write-Host "  ℹ  INFO      " -ForegroundColor Yellow -NoNewline
    Write-Host "PostgreSQL".PadRight(20) -NoNewline
    Write-Host "localhost:5432 (Check service)" -ForegroundColor Gray
}

Write-Host ""
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

# Connection Summary
$connectedCount = 0
if ($kafkaTest.TcpTestSucceeded) { $connectedCount++ }
if ($uiTest.TcpTestSucceeded) { $connectedCount++ }
if ($minioAPITest.TcpTestSucceeded) { $connectedCount++ }
if ($minioConsoleTest.TcpTestSucceeded) { $connectedCount++ }

if ($connectedCount -eq 4) {
    Write-Host "Status: All core services connected! ✓" -ForegroundColor Green
    Write-Host "" 
    Write-Host "Web Interfaces:" -ForegroundColor Cyan 
    Write-Host "  • Kafka UI:       http://localhost:8080" -ForegroundColor White
    Write-Host "  • MinIO Console:  http://localhost:9001" -ForegroundColor White
    Write-Host "    Credentials:    admin / password123" -ForegroundColor Gray
} elseif ($connectedCount -eq 0) {
    Write-Host "Status: No services running" -ForegroundColor Red
    Write-Host ""
    Write-Host "To start services, run:" -ForegroundColor Yellow
    Write-Host "  .\restart_all_native.ps1" -ForegroundColor White
} else {
    Write-Host "Status: $connectedCount of 4 core services connected" -ForegroundColor Yellow
    Write-Host ""
    
    if (-not $kafkaTest.TcpTestSucceeded) {
        Write-Host "To start Kafka:" -ForegroundColor Yellow
        Write-Host "  cd C:\kafka\kafka-4.2.0" -ForegroundColor White
        Write-Host "  .\bin\windows\kafka-server-start.bat .\config\kraft\syniq-server.properties" -ForegroundColor White
        Write-Host ""
    }
    
    if (-not $uiTest.TcpTestSucceeded) {
        Write-Host "To start Kafka UI:" -ForegroundColor Yellow
        Write-Host "  cd C:\syniq\kafka-ui" -ForegroundColor White
        Write-Host "  .\start-kafka-ui.bat" -ForegroundColor White
        Write-Host ""
    }
    
    if (-not $minioAPITest.TcpTestSucceeded -or -not $minioConsoleTest.TcpTestSucceeded) {
        Write-Host "To start MinIO:" -ForegroundColor Yellow
        Write-Host "  cd C:\syniq\minio" -ForegroundColor White
        Write-Host "  .\minio.exe server .\data --console-address `":9001`"" -ForegroundColor White
        Write-Host ""
    }
}

Write-Host ""
Write-Host "For more information, see: SERVICES_CONNECTION_GUIDE.md" -ForegroundColor Cyan
Write-Host ""
