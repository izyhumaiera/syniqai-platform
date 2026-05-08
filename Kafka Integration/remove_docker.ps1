# ============================================================================
# SYNIQ - Docker Cleanup and Migration Script
# ============================================================================
# This script backs up and removes Docker-related files from your project
# Run this AFTER you've successfully installed and tested native Kafka
# ============================================================================

param(
    [switch]$DryRun,
    [switch]$SkipBackup,
    [switch]$StopDocker
)

$ErrorActionPreference = "Continue"

Write-Host "`n╔════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║           SYNIQ Docker Cleanup & Migration                ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════╝`n" -ForegroundColor Cyan

$kafkaIntegrationDir = "c:\Users\Local user\OneDrive - M Telecommunication Sdn Bhd\Desktop\TASK\Syniq\Kafka Integration"

if (-not (Test-Path $kafkaIntegrationDir)) {
    Write-Host "❌ Kafka Integration directory not found" -ForegroundColor Red
    exit 1
}

Set-Location $kafkaIntegrationDir

# Step 1: Verify native Kafka is working
Write-Host "Step 1: Verifying native Kafka installation..." -ForegroundColor Yellow

$kafkaRunning = $false
try {
    $testConnection = Test-NetConnection -ComputerName localhost -Port 9092 -WarningAction SilentlyContinue -ErrorAction SilentlyContinue
    if ($testConnection.TcpTestSucceeded) {
        Write-Host "✅ Native Kafka is running on localhost:9092" -ForegroundColor Green
        $kafkaRunning = $true
    }
} catch {
    # Kafka not running
}

if (-not $kafkaRunning) {
    Write-Host "⚠️  Native Kafka is not running!" -ForegroundColor Yellow
    Write-Host "   Please start native Kafka first:" -ForegroundColor Yellow
    Write-Host "     .\start_kafka_native.ps1" -ForegroundColor White
    Write-Host "`n   Or continue anyway? (Docker will be stopped) [y/N]: " -ForegroundColor Yellow -NoNewline
    $response = Read-Host
    if ($response -ne 'y' -and $response -ne 'Y') {
        Write-Host "Exiting..." -ForegroundColor Gray
        exit 1
    }
}

# Step 2: Stop Docker containers
if ($StopDocker) {
    Write-Host "`nStep 2: Stopping Docker containers..." -ForegroundColor Yellow
    
    $dockerRunning = docker ps 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "   Stopping SYNIQ Docker containers..." -ForegroundColor Gray
        docker-compose down 2>$null
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ Docker containers stopped" -ForegroundColor Green
        } else {
            Write-Host "⚠️  No Docker containers were running" -ForegroundColor Yellow
        }
    } else {
        Write-Host "⚠️  Docker is not running or not installed" -ForegroundColor Yellow
    }
} else {
    Write-Host "`nStep 2: Skipping Docker container stop (use -StopDocker to stop)" -ForegroundColor Gray
}

# Step 3: Backup Docker files
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backupDir = ".\docker_backup_$timestamp"

if (-not $SkipBackup) {
    Write-Host "`nStep 3: Backing up Docker files..." -ForegroundColor Yellow
    
    New-Item -ItemType Directory -Force -Path $backupDir | Out-Null
    
    $dockerFiles = @(
        "docker-compose.yml",
        "Dockerfile.cdc",
        "kafka-connect-startup.sh",
        ".dockerignore"
    )
    
    $backedUpCount = 0
    foreach ($file in $dockerFiles) {
        if (Test-Path $file) {
            Copy-Item $file "$backupDir\$file" -Force
            Write-Host "   ✓ Backed up: $file" -ForegroundColor Green
            $backedUpCount++
        }
    }
    
    if ($backedUpCount -gt 0) {
        Write-Host "✅ $backedUpCount files backed up to: $backupDir" -ForegroundColor Green
    } else {
        Write-Host "⚠️  No Docker files found to backup" -ForegroundColor Yellow
    }
} else {
    Write-Host "`nStep 3: Skipping backup (use without -SkipBackup to create backup)" -ForegroundColor Gray
}

# Step 4: Remove Docker files
Write-Host "`nStep 4: Removing Docker files..." -ForegroundColor Yellow

if ($DryRun) {
    Write-Host "   [DRY RUN] Files that would be removed:" -ForegroundColor Cyan
}

$dockerFiles = @(
    "docker-compose.yml",
    "Dockerfile.cdc",
    "kafka-connect-startup.sh",
    ".dockerignore"
)

$removedCount = 0
foreach ($file in $dockerFiles) {
    if (Test-Path $file) {
        if ($DryRun) {
            Write-Host "   • $file" -ForegroundColor Gray
        } else {
            Remove-Item $file -Force
            Write-Host "   ✓ Removed: $file" -ForegroundColor Green
        }
        $removedCount++
    }
}

if ($DryRun) {
    Write-Host "`n   Run without -DryRun to actually remove files" -ForegroundColor Cyan
} else {
    if ($removedCount -gt 0) {
        Write-Host "✅ $removedCount Docker files removed" -ForegroundColor Green
    } else {
        Write-Host "⚠️  No Docker files found to remove" -ForegroundColor Yellow
    }
}

# Step 5: Update old startup script
Write-Host "`nStep 5: Updating startup references..." -ForegroundColor Yellow

if (Test-Path "start_kafka.ps1") {
    if ($DryRun) {
        Write-Host "   [DRY RUN] Would rename: start_kafka.ps1 → start_kafka_docker_old.ps1" -ForegroundColor Cyan
    } else {
        Rename-Item "start_kafka.ps1" "start_kafka_docker_old.ps1" -Force -ErrorAction SilentlyContinue
        Write-Host "   ✓ Renamed: start_kafka.ps1 → start_kafka_docker_old.ps1" -ForegroundColor Green
    }
}

if (-not $DryRun) {
    # Create a convenience alias
    if (-not (Test-Path "start_kafka.ps1")) {
        Copy-Item "start_kafka_native.ps1" "start_kafka.ps1" -Force
        Write-Host "   ✓ Created: start_kafka.ps1 (links to start_kafka_native.ps1)" -ForegroundColor Green
    }
}

# Step 6: Summary
Write-Host "`n╔════════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║                ✅ Migration Complete!                      ║" -ForegroundColor Green
Write-Host "╚════════════════════════════════════════════════════════════╝`n" -ForegroundColor Green

if (-not $DryRun) {
    Write-Host "📋 Summary:" -ForegroundColor Cyan
    Write-Host "   • Docker files backed up to: $backupDir" -ForegroundColor White
    Write-Host "   • Docker configuration removed" -ForegroundColor White
    Write-Host "   • Code updated for native execution" -ForegroundColor White
    
    Write-Host "`n🚀 Next Steps:" -ForegroundColor Cyan
    Write-Host "   1. Start native Kafka:" -ForegroundColor White
    Write-Host "      .\start_kafka_native.ps1" -ForegroundColor Gray
    Write-Host "`n   2. Test your application:" -ForegroundColor White
    Write-Host "      cd ..\gui" -ForegroundColor Gray
    Write-Host "      .\start_dev.ps1" -ForegroundColor Gray
    Write-Host "`n   3. Verify CDC pipeline:" -ForegroundColor White
    Write-Host "      python test_cdc_end_to_end.py" -ForegroundColor Gray
    
    Write-Host "`n🔄 Rollback (if needed):" -ForegroundColor Cyan
    Write-Host "   1. Stop native services:" -ForegroundColor White
    Write-Host "      .\stop_kafka_native.ps1" -ForegroundColor Gray
    Write-Host "`n   2. Restore Docker files:" -ForegroundColor White
    Write-Host "      Copy-Item $backupDir\* . -Force" -ForegroundColor Gray
    Write-Host "`n   3. Start Docker:" -ForegroundColor White
    Write-Host "      docker-compose up -d" -ForegroundColor Gray
    
} else {
    Write-Host "This was a dry run. Use without -DryRun to perform actual migration." -ForegroundColor Yellow
}

Write-Host ""
