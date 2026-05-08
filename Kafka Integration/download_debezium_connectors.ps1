why #!/usr/bin/env pwsh
<#
.SYNOPSIS
    Download Debezium connectors for native Kafka Connect

.DESCRIPTION
    Downloads and extracts Debezium PostgreSQL and MySQL connectors to Kafka plugins directory.
    This is a Windows-friendly alternative to confluent-hub.
#>

Write-Host ""
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "          DEBEZIUM CONNECTOR DOWNLOADER" -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host ""

$KAFKA_HOME = "C:\kafka\kafka-4.2.0"
$PLUGINS_DIR = "$KAFKA_HOME\plugins"
$TEMP_DIR = "$env:TEMP\debezium-download"

# Connector versions and URLs
$DEBEZIUM_VERSION = "2.4.0.Final"
$POSTGRES_CONNECTOR_URL = "https://repo1.maven.org/maven2/io/debezium/debezium-connector-postgres/$DEBEZIUM_VERSION/debezium-connector-postgres-$DEBEZIUM_VERSION-plugin.tar.gz"
$MYSQL_CONNECTOR_URL = "https://repo1.maven.org/maven2/io/debezium/debezium-connector-mysql/$DEBEZIUM_VERSION/debezium-connector-mysql-$DEBEZIUM_VERSION-plugin.tar.gz"

# Check if Kafka exists
if (-not (Test-Path $KAFKA_HOME)) {
    Write-Host "[ERROR] Kafka not found at $KAFKA_HOME" -ForegroundColor Red
    Write-Host "Please verify your Kafka installation path." -ForegroundColor Yellow
    exit 1
}

# Create directories
Write-Host "[1/5] Creating directories..." -ForegroundColor Yellow
if (-not (Test-Path $PLUGINS_DIR)) {
    New-Item -ItemType Directory -Path $PLUGINS_DIR -Force | Out-Null
}
if (-not (Test-Path $TEMP_DIR)) {
    New-Item -ItemType Directory -Path $TEMP_DIR -Force | Out-Null
}
Write-Host "  Plugins directory: $PLUGINS_DIR" -ForegroundColor Green
Write-Host "  Temp directory: $TEMP_DIR" -ForegroundColor Green
Write-Host ""

# Check if connectors already exist
$postgresExists = Test-Path "$PLUGINS_DIR\debezium-connector-postgres"
$mysqlExists = Test-Path "$PLUGINS_DIR\debezium-connector-mysql"

if ($postgresExists -and $mysqlExists) {
    Write-Host "Both connectors already exist at:" -ForegroundColor Green
    Write-Host "  $PLUGINS_DIR\debezium-connector-postgres" -ForegroundColor Gray
    Write-Host "  $PLUGINS_DIR\debezium-connector-mysql" -ForegroundColor Gray
    Write-Host ""
    $overwrite = Read-Host "Overwrite existing connectors? (y/N)"
    if ($overwrite -ne 'y' -and $overwrite -ne 'Y') {
        Write-Host "Skipping download. Existing connectors will be used." -ForegroundColor Yellow
        exit 0
    }
}

# Download PostgreSQL connector
if (-not $postgresExists -or $overwrite -eq 'y' -or $overwrite -eq 'Y') {
    Write-Host "[2/5] Downloading PostgreSQL connector..." -ForegroundColor Yellow
    Write-Host "  URL: $POSTGRES_CONNECTOR_URL" -ForegroundColor Gray
    
    $postgresFile = "$TEMP_DIR\postgres-connector.tar.gz"
    try {
        Invoke-WebRequest -Uri $POSTGRES_CONNECTOR_URL -OutFile $postgresFile -UseBasicParsing
        Write-Host "  Downloaded: $('{0:N2}' -f ((Get-Item $postgresFile).Length / 1MB)) MB" -ForegroundColor Green
    } catch {
        Write-Host "  [ERROR] Download failed: $($_.Exception.Message)" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "[2/5] PostgreSQL connector already exists, skipping..." -ForegroundColor Green
}
Write-Host ""

# Download MySQL connector
if (-not $mysqlExists -or $overwrite -eq 'y' -or $overwrite -eq 'Y') {
    Write-Host "[3/5] Downloading MySQL connector..." -ForegroundColor Yellow
    Write-Host "  URL: $MYSQL_CONNECTOR_URL" -ForegroundColor Gray
    
    $mysqlFile = "$TEMP_DIR\mysql-connector.tar.gz"
    try {
        Invoke-WebRequest -Uri $MYSQL_CONNECTOR_URL -OutFile $mysqlFile -UseBasicParsing
        Write-Host "  Downloaded: $('{0:N2}' -f ((Get-Item $mysqlFile).Length / 1MB)) MB" -ForegroundColor Green
    } catch {
        Write-Host "  [ERROR] Download failed: $($_.Exception.Message)" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "[3/5] MySQL connector already exists, skipping..." -ForegroundColor Green
}
Write-Host ""

# Extract files (requires tar which is built into Windows 10+)
Write-Host "[4/5] Extracting connectors..." -ForegroundColor Yellow

if (-not $postgresExists -or $overwrite -eq 'y' -or $overwrite -eq 'Y') {
    Write-Host "  Extracting PostgreSQL connector..." -ForegroundColor Cyan
    if (Test-Path "$PLUGINS_DIR\debezium-connector-postgres") {
        Remove-Item -Path "$PLUGINS_DIR\debezium-connector-postgres" -Recurse -Force
    }
    
    # Extract to temp first
    tar -xzf "$TEMP_DIR\postgres-connector.tar.gz" -C $TEMP_DIR
    
    # Move to plugins
    $extractedDir = Get-ChildItem -Path $TEMP_DIR -Directory | Where-Object { $_.Name -like "debezium-connector-postgres*" } | Select-Object -First 1
    if ($extractedDir) {
        Move-Item -Path $extractedDir.FullName -Destination "$PLUGINS_DIR\debezium-connector-postgres" -Force
        Write-Host "  PostgreSQL connector extracted to: $PLUGINS_DIR\debezium-connector-postgres" -ForegroundColor Green
    } else {
        Write-Host "  [ERROR] Could not find extracted directory" -ForegroundColor Red
    }
}

if (-not $mysqlExists -or $overwrite -eq 'y' -or $overwrite -eq 'Y') {
    Write-Host "  Extracting MySQL connector..." -ForegroundColor Cyan
    if (Test-Path "$PLUGINS_DIR\debezium-connector-mysql") {
        Remove-Item -Path "$PLUGINS_DIR\debezium-connector-mysql" -Recurse -Force
    }
    
    # Extract to temp first
    tar -xzf "$TEMP_DIR\mysql-connector.tar.gz" -C $TEMP_DIR
    
    # Move to plugins
    $extractedDir = Get-ChildItem -Path $TEMP_DIR -Directory | Where-Object { $_.Name -like "debezium-connector-mysql*" } | Select-Object -First 1
    if ($extractedDir) {
        Move-Item -Path $extractedDir.FullName -Destination "$PLUGINS_DIR\debezium-connector-mysql" -Force
        Write-Host "  MySQL connector extracted to: $PLUGINS_DIR\debezium-connector-mysql" -ForegroundColor Green
    } else {
        Write-Host "  [ERROR] Could not find extracted directory" -ForegroundColor Red
    }
}
Write-Host ""

# Verify installation
Write-Host "[5/5] Verifying installation..." -ForegroundColor Yellow
$postgresJars = Get-ChildItem -Path "$PLUGINS_DIR\debezium-connector-postgres" -Filter "*.jar" -ErrorAction SilentlyContinue
$mysqlJars = Get-ChildItem -Path "$PLUGINS_DIR\debezium-connector-mysql" -Filter "*.jar" -ErrorAction SilentlyContinue

if ($postgresJars -and $postgresJars.Count -gt 0) {
    Write-Host "  PostgreSQL connector: $($postgresJars.Count) JAR files" -ForegroundColor Green
} else {
    Write-Host "  [ERROR] PostgreSQL connector JARs not found" -ForegroundColor Red
}

if ($mysqlJars -and $mysqlJars.Count -gt 0) {
    Write-Host "  MySQL connector: $($mysqlJars.Count) JAR files" -ForegroundColor Green
} else {
    Write-Host "  [ERROR] MySQL connector JARs not found" -ForegroundColor Red
}
Write-Host ""

# Cleanup
Write-Host "Cleaning up temporary files..." -ForegroundColor Yellow
Remove-Item -Path $TEMP_DIR -Recurse -Force -ErrorAction SilentlyContinue
Write-Host "  Cleaned: $TEMP_DIR" -ForegroundColor Green
Write-Host ""

Write-Host "================================================================================" -ForegroundColor Green
Write-Host "          DEBEZIUM CONNECTORS INSTALLED SUCCESSFULLY!" -ForegroundColor Green
Write-Host "================================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Installed connectors:" -ForegroundColor Cyan
Write-Host "  PostgreSQL: $PLUGINS_DIR\debezium-connector-postgres" -ForegroundColor White
Write-Host "  MySQL:      $PLUGINS_DIR\debezium-connector-mysql" -ForegroundColor White
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. Configure PostgreSQL for CDC:" -ForegroundColor White
Write-Host "     python fix_debezium_permissions_local.py" -ForegroundColor Yellow
Write-Host ""
Write-Host "  2. Start Kafka Connect:" -ForegroundColor White
Write-Host "     .\start_kafka_connect.ps1" -ForegroundColor Yellow
Write-Host ""
Write-Host "  3. Verify connectors are loaded:" -ForegroundColor White
Write-Host "     curl http://localhost:8083/connector-plugins" -ForegroundColor Yellow
Write-Host ""
