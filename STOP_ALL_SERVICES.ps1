# ============================================================================
# SyniqAI - Stop All Services Script
# ============================================================================
# Gracefully stops all SyniqAI components
# Date: April 13, 2026
# ============================================================================

$ErrorActionPreference = "Continue"

function Write-Step { param($msg) Write-Host "`n[STEP] $msg" -ForegroundColor Cyan }
function Write-Success { param($msg) Write-Host "  [OK] $msg" -ForegroundColor Green }
function Write-Info { param($msg) Write-Host "  [i] $msg" -ForegroundColor Gray }

Write-Host ""
Write-Host "================================================================" -ForegroundColor Red
Write-Host "   SyniqAI - Stop All Services" -ForegroundColor Red
Write-Host "================================================================" -ForegroundColor Red
Write-Host ""

# ============================================================================
# Stop Python Processes (Backend, AI Processor, CDC, Bronze Emitter)
# ============================================================================
Write-Step "Stopping Python processes..."

$pythonProcesses = Get-Process python -ErrorAction SilentlyContinue

if ($pythonProcesses) {
    Write-Info "Found $($pythonProcesses.Count) Python process(es)"
    
    foreach ($proc in $pythonProcesses) {
        try {
            $proc.Kill()
            Write-Success "Stopped process PID: $($proc.Id)"
        } catch {
            Write-Info "Could not stop PID: $($proc.Id) (may require admin)"
        }
    }
} else {
    Write-Info "No Python processes found"
}

Start-Sleep -Seconds 2

# ============================================================================
# Stop Java Processes (Kafka)
# ============================================================================
Write-Step "Stopping Kafka (Java processes)..."

$javaProcesses = Get-Process java -ErrorAction SilentlyContinue

if ($javaProcesses) {
    Write-Info "Found $($javaProcesses.Count) Java process(es)"
    
    foreach ($proc in $javaProcesses) {
        try {
            $proc.Kill()
            Write-Success "Stopped Kafka process PID: $($proc.Id)"
        } catch {
            Write-Info "Could not stop PID: $($proc.Id) (may require admin)"
        }
    }
} else {
    Write-Info "No Kafka processes found"
}

Start-Sleep -Seconds 2

# ============================================================================
# Stop Node.js Processes (React Frontend)
# ============================================================================
Write-Step "Stopping Node.js (React frontend)..."

$nodeProcesses = Get-Process node -ErrorAction SilentlyContinue

if ($nodeProcesses) {
    Write-Info "Found $($nodeProcesses.Count) Node.js process(es)"
    
    foreach ($proc in $nodeProcesses) {
        try {
            $proc.Kill()
            Write-Success "Stopped Node.js process PID: $($proc.Id)"
        } catch {
            Write-Info "Could not stop PID: $($proc.Id) (may require admin)"
        }
    }
} else {
    Write-Info "No Node.js processes found"
}

Start-Sleep -Seconds 2

# ============================================================================
# Stop MinIO
# ============================================================================
Write-Step "Stopping MinIO..."

$minioProcesses = Get-Process minio -ErrorAction SilentlyContinue

if ($minioProcesses) {
    Write-Info "Found $($minioProcesses.Count) MinIO process(es)"
    
    foreach ($proc in $minioProcesses) {
        try {
            $proc.Kill()
            Write-Success "Stopped MinIO process PID: $($proc.Id)"
        } catch {
            Write-Info "Could not stop PID: $($proc.Id) (may require admin)"
        }
    }
} else {
    Write-Info "No MinIO processes found"
}

# ============================================================================
# Note: PostgreSQL not stopped (Windows service)
# ============================================================================
Write-Host ""
Write-Info "Note: PostgreSQL service not stopped (runs as Windows service)"
Write-Info "To stop PostgreSQL manually:"
Write-Info "  1. Open Services (services.msc)"
Write-Info "  2. Find 'postgresql-x64-14' or similar"
Write-Info "  3. Click 'Stop'"

# ============================================================================
# Summary
# ============================================================================
Write-Host ""
Write-Host "================================================================" -ForegroundColor Green
Write-Host "   All SyniqAI Services Stopped" -ForegroundColor Green
Write-Host "================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Stopped Components:" -ForegroundColor Cyan
Write-Host "  [OK] FastAPI Backend" -ForegroundColor Gray
Write-Host "  [OK] AI Processor Worker" -ForegroundColor Gray
Write-Host "  [OK] Bronze Ready Emitter" -ForegroundColor Gray
Write-Host "  [OK] CDC Consumer" -ForegroundColor Gray
Write-Host "  [OK] Kafka Brokers" -ForegroundColor Gray
Write-Host "  [OK] React Frontend" -ForegroundColor Gray
Write-Host "  [OK] MinIO Server" -ForegroundColor Gray
Write-Host ""
Write-Host "To Restart All Services:" -ForegroundColor Yellow
Write-Host "  Run: .\START_ALL_SERVICES.ps1" -ForegroundColor Gray
Write-Host ""
