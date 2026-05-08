Write-Host "=== Installing Java 17 and Node.js ===" -ForegroundColor Green
Write-Host ""
Write-Host "Step 1/2: Installing Java 17..." -ForegroundColor Yellow
winget install EclipseAdoptium.Temurin.17.JDK --accept-package-agreements --accept-source-agreements

Write-Host ""
Write-Host "Step 2/2: Installing Node.js LTS..." -ForegroundColor Yellow
winget install OpenJS.NodeJS.LTS --accept-package-agreements --accept-source-agreements

Write-Host ""
Write-Host "=== Installation Complete ===" -ForegroundColor Green
Write-Host "Verifying installations..." -ForegroundColor Cyan

# Refresh environment variables
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

Write-Host ""
Write-Host "Java version:" -ForegroundColor Cyan
java -version 2>&1

Write-Host ""
Write-Host "Node.js version:" -ForegroundColor Cyan
node --version

Write-Host ""
Write-Host "npm version:" -ForegroundColor Cyan
npm --version

Write-Host ""
Write-Host "Please close and reopen your terminal for PATH changes to take effect." -ForegroundColor Yellow
