# SyniqAI PostgreSQL Setup Helper
# This script helps you set up PostgreSQL for SyniqAI

Write-Host "=== SYNIQAI POSTGRESQL SETUP ===" -ForegroundColor Cyan
Write-Host ""

# Find PostgreSQL installation
$psqlPath = Get-Item "C:\Program Files\PostgreSQL\*\bin\psql.exe" -ErrorAction SilentlyContinue | Select-Object -First 1

if (-not $psqlPath) {
    Write-Host "ERROR: psql.exe not found!" -ForegroundColor Red
    exit 1
}

Write-Host "Found PostgreSQL at: $($psqlPath.FullName)" -ForegroundColor Green
Write-Host ""

Write-Host "=== SETUP INSTRUCTIONS ===" -ForegroundColor Yellow
Write-Host ""
Write-Host "We need to create a database user for SyniqAI." -ForegroundColor White
Write-Host ""
Write-Host "OPTION 1: If you know the 'postgres' password:" -ForegroundColor Cyan
Write-Host "  1. Press Enter below" -ForegroundColor White
Write-Host "  2. When prompted, enter your postgres password" -ForegroundColor White
Write-Host "  3. The script will create syniqai_metadata database and syniqai_user" -ForegroundColor White
Write-Host ""
Write-Host "OPTION 2: If you DON'T know the password:" -ForegroundColor Cyan
Write-Host "  1. Press Ctrl+C to cancel" -ForegroundColor White
Write-Host "  2. Open 'SQL Shell (psql)' from Start Menu" -ForegroundColor White
Write-Host "  3. Press Enter 4 times (accept defaults)" -ForegroundColor White
Write-Host "  4. When it asks for postgres password, try: postgres, admin, or 1234" -ForegroundColor White
Write-Host "  5. If successful, run: \i 'C:/Users/Local user/OneDrive - M Telecommunication Sdn Bhd/Desktop/TASK/Syniq/setup_postgres_syniqai.sql'" -ForegroundColor White
Write-Host ""
Write-Host "="*60 -ForegroundColor Cyan
Write-Host ""

$continue = Read-Host "Press Enter to continue with OPTION 1 (or Ctrl+C to cancel)"

Write-Host ""
Write-Host "Attempting to connect to PostgreSQL..." -ForegroundColor Yellow
Write-Host "You will be prompted for the 'postgres' user password" -ForegroundColor White
Write-Host ""

# Run the SQL setup script
& $psqlPath.FullName -U postgres -d postgres -f "C:\Users\Local user\OneDrive - M Telecommunication Sdn Bhd\Desktop\TASK\Syniq\setup_postgres_syniqai.sql"

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "="*60 -ForegroundColor Green
    Write-Host "SUCCESS! SyniqAI PostgreSQL setup complete!" -ForegroundColor Green
    Write-Host "="*60 -ForegroundColor Green
    Write-Host ""
    Write-Host "Database: syniqai_metadata" -ForegroundColor Cyan
    Write-Host "User: syniqai_user" -ForegroundColor Cyan
    Write-Host "Password: syniqai_password" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "You can now run the AI processor!" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "="*60 -ForegroundColor Red
    Write-Host "SETUP FAILED - Try OPTION 2 above" -ForegroundColor Red
    Write-Host "="*60 -ForegroundColor Red
}

Write-Host ""
Read-Host "Press Enter to exit"
