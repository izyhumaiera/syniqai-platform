# ============================================================================
# Create Debezium Connector for Remote Database
# ============================================================================
# This script creates a CDC connector for a database on another laptop/server

param(
    [Parameter(Mandatory=$false)]
    [string]$RemoteHost = "192.168.1.150",
    
    [Parameter(Mandatory=$false)]
    [int]$RemotePort = 5432,
    
    [Parameter(Mandatory=$false)]
    [string]$Database = "myapp_db",
    
    [Parameter(Mandatory=$false)]
    [string]$User = "debezium_user",
    
    [Parameter(Mandatory=$false)]
    [string]$Password = "secure_password",
    
    [Parameter(Mandatory=$false)]
    [string]$ConnectorName = "remote-postgres-cdc",
    
    [Parameter(Mandatory=$false)]
    [string]$Tables = "public.*"
)

Write-Host "`n================================================================" -ForegroundColor Cyan
Write-Host "   CREATE REMOTE DEBEZIUM CONNECTOR" -ForegroundColor Cyan
Write-Host "================================================================`n" -ForegroundColor Cyan

# Step 1: Test connectivity to remote database
Write-Host "[1/4] Testing connection to remote database..." -ForegroundColor Yellow
$connectionTest = Test-NetConnection -ComputerName $RemoteHost -Port $RemotePort -WarningAction SilentlyContinue

if ($connectionTest.TcpTestSucceeded) {
    Write-Host "  ✓ Remote database is reachable at $RemoteHost:$RemotePort" -ForegroundColor Green
} else {
    Write-Host "  ✗ Cannot reach $RemoteHost:$RemotePort" -ForegroundColor Red
    Write-Host "`nPossible issues:" -ForegroundColor Yellow
    Write-Host "  - Database not running on remote laptop" -ForegroundColor White
    Write-Host "  - Firewall blocking port $RemotePort" -ForegroundColor White
    Write-Host "  - Incorrect IP address" -ForegroundColor White
    exit 1
}

Write-Host ""

# Step 2: Check if Kafka Connect is running
Write-Host "[2/4] Checking Kafka Connect..." -ForegroundColor Yellow
try {
    $kafkaConnect = Invoke-RestMethod -Uri "http://localhost:8083/" -Method Get -TimeoutSec 5
    Write-Host "  ✓ Kafka Connect is running (version: $($kafkaConnect.version))" -ForegroundColor Green
} catch {
    Write-Host "  ✗ Kafka Connect not running on localhost:8083" -ForegroundColor Red
    Write-Host "  Start it with: .\start_kafka_connect.ps1" -ForegroundColor Yellow
    exit 1
}

Write-Host ""

# Step 3: Create connector configuration
Write-Host "[3/4] Creating connector configuration..." -ForegroundColor Yellow

$connectorConfig = @{
    name = $ConnectorName
    config = @{
        "connector.class" = "io.debezium.connector.postgresql.PostgresConnector"
        "database.hostname" = $RemoteHost
        "database.port" = [string]$RemotePort
        "database.user" = $User
        "database.password" = $Password
        "database.dbname" = $Database
        "database.server.name" = $ConnectorName.Replace("-", "_")
        "table.include.list" = $Tables
        "plugin.name" = "pgoutput"
        "slot.name" = "debezium_slot_$($ConnectorName.Replace('-', '_'))"
        "publication.name" = "debezium_publication"
        "snapshot.mode" = "initial"
        "heartbeat.interval.ms" = "10000"
    }
} | ConvertTo-Json -Depth 10

Write-Host "  Connector name: $ConnectorName" -ForegroundColor Gray
Write-Host "  Database: $RemoteHost:$RemotePort/$Database" -ForegroundColor Gray
Write-Host "  Tables: $Tables" -ForegroundColor Gray
Write-Host ""

# Step 4: Create connector
Write-Host "[4/4] Creating connector in Kafka Connect..." -ForegroundColor Yellow

try {
    $result = Invoke-RestMethod -Uri "http://localhost:8083/connectors" `
        -Method Post `
        -ContentType "application/json" `
        -Body $connectorConfig
    
    Write-Host "  ✓ Connector created successfully!" -ForegroundColor Green
    Write-Host ""
    
    # Wait a moment for connector to start
    Start-Sleep -Seconds 3
    
    # Check connector status
    $status = Invoke-RestMethod -Uri "http://localhost:8083/connectors/$ConnectorName/status" -Method Get
    
    Write-Host "================================================================" -ForegroundColor Green
    Write-Host "   ✓✓✓ CONNECTOR ACTIVE!" -ForegroundColor Green
    Write-Host "================================================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Connector Status:" -ForegroundColor Cyan
    Write-Host "  Name: $($status.name)" -ForegroundColor White
    Write-Host "  State: $($status.connector.state)" -ForegroundColor White
    Write-Host "  Worker: $($status.connector.worker_id)" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Tasks:" -ForegroundColor Cyan
    foreach ($task in $status.tasks) {
        Write-Host "  Task $($task.id): $($task.state)" -ForegroundColor White
    }
    Write-Host ""
    Write-Host "Kafka Topics Created:" -ForegroundColor Cyan
    Write-Host "  $($ConnectorName.Replace('-', '_')).<schema>.<table>" -ForegroundColor White
    Write-Host ""
    Write-Host "Next Steps:" -ForegroundColor Yellow
    Write-Host "  1. Start CDC consumer: Click 'Start CDC' in GUI" -ForegroundColor White
    Write-Host "  2. Make changes in remote database" -ForegroundColor White
    Write-Host "  3. Watch CDC messages flow to Bronze layer" -ForegroundColor White
    Write-Host ""
    
} catch {
    Write-Host "  ✗ Failed to create connector" -ForegroundColor Red
    Write-Host ""
    Write-Host "Error details:" -ForegroundColor Yellow
    Write-Host $_.Exception.Message -ForegroundColor Gray
    
    if ($_.ErrorDetails) {
        Write-Host ""
        Write-Host "Kafka Connect response:" -ForegroundColor Yellow
        Write-Host $_.ErrorDetails.Message -ForegroundColor Gray
    }
    
    Write-Host ""
    Write-Host "Common issues:" -ForegroundColor Yellow
    Write-Host "  - Database user doesn't have REPLICATION privilege" -ForegroundColor White
    Write-Host "  - WAL not enabled (wal_level != logical)" -ForegroundColor White
    Write-Host "  - pg_hba.conf doesn't allow remote connection" -ForegroundColor White
    Write-Host "  - Publication not created" -ForegroundColor White
    exit 1
}
