# PostgreSQL Password Reset Helper for Windows
# This script helps you reset the postgres user password

Write-Host "=== POSTGRESQL PASSWORD RESET HELPER ===" -ForegroundColor Cyan
Write-Host ""

# Check if running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "ERROR: This script must be run as Administrator!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Right-click PowerShell -> 'Run as Administrator'" -ForegroundColor Yellow
    Write-Host "Then run this script again" -ForegroundColor Yellow
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "[OK] Running as Administrator" -ForegroundColor Green
Write-Host ""

# Find PostgreSQL data directory
$pgDataDir = "C:\Program Files\PostgreSQL\18\data"
$pgHbaFile = Join-Path $pgDataDir "pg_hba.conf"
$pgHbaBackup = Join-Path $pgDataDir "pg_hba.conf.backup"

if (-not (Test-Path $pgHbaFile)) {
    Write-Host "ERROR: pg_hba.conf not found at: $pgHbaFile" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "Found pg_hba.conf at: $pgHbaFile" -ForegroundColor Green
Write-Host ""

# Backup pg_hba.conf
Write-Host "Creating backup..." -ForegroundColor Yellow
Copy-Item $pgHbaFile $pgHbaBackup -Force
Write-Host "[OK] Backup created: $pgHbaBackup" -ForegroundColor Green
Write-Host ""

# Modify pg_hba.conf to use 'trust' authentication
Write-Host "Modifying pg_hba.conf to allow passwordless access..." -ForegroundColor Yellow
$content = Get-Content $pgHbaFile
$newContent = $content -replace 'scram-sha-256', 'trust' -replace 'md5', 'trust'
$newContent | Set-Content $pgHbaFile
Write-Host "[OK] Modified pg_hba.conf" -ForegroundColor Green
Write-Host ""

# Restart PostgreSQL service
Write-Host "Restarting PostgreSQL service..." -ForegroundColor Yellow
try {
    Restart-Service postgresql-x64-18 -ErrorAction Stop
    Start-Sleep -Seconds 3
    Write-Host "[OK] PostgreSQL service restarted" -ForegroundColor Green
}
catch {
    Write-Host "ERROR: Failed to restart service: $_" -ForegroundColor Red
    Write-Host "Restoring backup..." -ForegroundColor Yellow
    Copy-Item $pgHbaBackup $pgHbaFile -Force
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "STEP 1 COMPLETE: PostgreSQL is now in TRUST mode" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""

Write-Host "Now you can connect to PostgreSQL WITHOUT a password!" -ForegroundColor Cyan
Write-Host ""
Write-Host "NEXT STEPS:" -ForegroundColor Yellow
Write-Host "1. Open pgAdmin 4" -ForegroundColor White
Write-Host "2. Connect to PostgreSQL 18 (no password needed)" -ForegroundColor White
Write-Host "3. Right-click 'postgres' user -> Properties -> Definition tab" -ForegroundColor White
Write-Host "4. Set new password: postgres" -ForegroundColor White
Write-Host "5. Run this SQL to create SyniqAI database:" -ForegroundColor White
Write-Host ""
Write-Host "   CREATE DATABASE syniqai_metadata;" -ForegroundColor Cyan
Write-Host "   CREATE USER syniqai_user WITH PASSWORD 'syniqai_password';" -ForegroundColor Cyan
Write-Host "   GRANT ALL PRIVILEGES ON DATABASE syniqai_metadata TO syniqai_user;" -ForegroundColor Cyan
Write-Host ""
Write-Host "6. After setting the password, run this script AGAIN to restore security" -ForegroundColor White
Write-Host ""

$response = Read-Host "Have you set the new password? (yes/no)"

if ($response -eq "yes" -or $response -eq "y") {
    Write-Host ""
    Write-Host "Restoring pg_hba.conf security..." -ForegroundColor Yellow
    Copy-Item $pgHbaBackup $pgHbaFile -Force
    Write-Host "[OK] Restored original pg_hba.conf" -ForegroundColor Green
    Write-Host ""
    
    Write-Host "Restarting PostgreSQL service..." -ForegroundColor Yellow
    Restart-Service postgresql-x64-18
    Start-Sleep -Seconds 3
    Write-Host "[OK] PostgreSQL service restarted with secure authentication" -ForegroundColor Green
    Write-Host ""
    
    Write-Host "============================================================" -ForegroundColor Green
    Write-Host "PASSWORD RESET COMPLETE!" -ForegroundColor Green
    Write-Host "============================================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "You can now connect with:" -ForegroundColor Cyan
    Write-Host "  Username: postgres" -ForegroundColor White
    Write-Host "  Password: postgres" -ForegroundColor White
    Write-Host ""
    Write-Host "Or use SyniqAI dedicated user:" -ForegroundColor Cyan
    Write-Host "  Username: syniqai_user" -ForegroundColor White
    Write-Host "  Password: syniqai_password" -ForegroundColor White
}
else {
    Write-Host ""
    Write-Host "============================================================" -ForegroundColor Yellow
    Write-Host "IMPORTANT: PostgreSQL is still in TRUST mode!" -ForegroundColor Yellow
    Write-Host "============================================================" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Run this script again after setting the password to restore security" -ForegroundColor Yellow
}

Write-Host ""
Read-Host "Press Enter to exit"
