# ============================================================================
# SYNIQ Phase 5 - Native Kafka Integration Quick Start
# ============================================================================
# Replaces Docker-based start_kafka.ps1
# Starts Kafka and Kafka Connect natively on Windows
# ============================================================================

Write-Host "`n=== SYNIQ Native Kafka Integration Quick Start ===`n" -ForegroundColor Cyan

# Change to Kafka Integration directory
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptPath

# Load environment variables
if (Test-Path .env) {
    Get-Content .env | ForEach-Object {
        if ($_ -match '^\s*([^#][^=]*)\s*=\s*(.*)$') {
            $name = $matches[1].Trim()
            $value = $matches[2].Trim()
            [Environment]::SetEnvironmentVariable($name, $value, "Process")
        }
    }
    Write-Host "✓ Environment variables loaded" -ForegroundColor Green
}

# Check if Kafka is installed
$kafkaHome = $env:KAFKA_HOME
if (-not $kafkaHome) {
    $kafkaHome = "C:\kafka\kafka-3.6.1"
}

if (-not (Test-Path $kafkaHome)) {
    Write-Host "❌ Kafka not found at $kafkaHome" -ForegroundColor Red
    Write-Host "`n📦 Please run the installation script first:" -ForegroundColor Yellow
    Write-Host "   .\install_kafka_native.ps1" -ForegroundColor White
    Write-Host "`nOr specify KAFKA_HOME environment variable." -ForegroundColor Gray
    exit 1
}

Write-Host "✓ Kafka found at: $kafkaHome" -ForegroundColor Green

# Step 1: Check if Kafka is already running
Write-Host "`nStep 1: Checking Kafka status..." -ForegroundColor Yellow

$kafkaRunning = $false
try {
    $testConnection = Test-NetConnection -ComputerName localhost -Port 9092 -WarningAction SilentlyContinue -ErrorAction SilentlyContinue
    if ($testConnection.TcpTestSucceeded) {
        Write-Host "✓ Kafka broker is already running on localhost:9092" -ForegroundColor Green
        $kafkaRunning = $true
    }
} catch {
    # Port not open, Kafka not running
}

if (-not $kafkaRunning) {
    # Check if Kafka service exists
    $kafkaService = Get-Service -Name "SyniqKafka" -ErrorAction SilentlyContinue
    
    if ($kafkaService) {
        Write-Host "Starting Kafka service..." -ForegroundColor Yellow
        Start-Service -Name "SyniqKafka"
        Start-Sleep -Seconds 5
        Write-Host "✓ Kafka service started" -ForegroundColor Green
    } else {
        Write-Host "Starting Kafka broker (background process)..." -ForegroundColor Yellow
        
        # Start Kafka in background
        $kafkaProcess = Start-Process -FilePath "$kafkaHome\bin\windows\kafka-server-start.bat" `
            -ArgumentList "$kafkaHome\config\kraft\syniq-server.properties" `
            -WindowStyle Minimized `
            -PassThru
        
        if ($kafkaProcess) {
            Write-Host "✓ Kafka broker started (PID: $($kafkaProcess.Id))" -ForegroundColor Green
            
            # Wait for Kafka to be ready
            Write-Host "Waiting for Kafka to be ready..." -ForegroundColor Gray
            $maxAttempts = 30
            $attempt = 0
            $ready = $false
            
            while ($attempt -lt $maxAttempts -and -not $ready) {
                Start-Sleep -Seconds 2
                $attempt++
                try {
                    $testConnection = Test-NetConnection -ComputerName localhost -Port 9092 -WarningAction SilentlyContinue -ErrorAction SilentlyContinue
                    if ($testConnection.TcpTestSucceeded) {
                        $ready = $true
                        Write-Host "✓ Kafka broker is ready" -ForegroundColor Green
                    }
                } catch {
                    # Keep waiting
                }
                Write-Host "." -NoNewline -ForegroundColor Gray
            }
            
            if (-not $ready) {
                Write-Host "`n⚠️  Kafka is taking longer than expected to start" -ForegroundColor Yellow
                Write-Host "   Check logs at: $kafkaHome\logs" -ForegroundColor Gray
            }
        } else {
            Write-Host "❌ Failed to start Kafka broker" -ForegroundColor Red
            exit 1
        }
    }
} else {
    Write-Host "Kafka is already running, skipping start." -ForegroundColor Gray
}

# Step 2: Check Kafka Connect
Write-Host "`nStep 2: Checking Kafka Connect status..." -ForegroundColor Yellow

$connectRunning = $false
try {
    $response = Invoke-RestMethod -Uri "http://localhost:8083/" -Method Get -TimeoutSec 3 -ErrorAction SilentlyContinue
    if ($response) {
        Write-Host "✓ Kafka Connect is already running on localhost:8083" -ForegroundColor Green
        $connectRunning = $true
    }
} catch {
    # Connect not running
}

if (-not $connectRunning) {
    $connectService = Get-Service -Name "SyniqKafkaConnect" -ErrorAction SilentlyContinue
    
    if ($connectService) {
        Write-Host "Starting Kafka Connect service..." -ForegroundColor Yellow
        Start-Service -Name "SyniqKafkaConnect"
        Start-Sleep -Seconds 5
        Write-Host "✓ Kafka Connect service started" -ForegroundColor Green
    } else {
        Write-Host "Starting Kafka Connect (background process)..." -ForegroundColor Yellow
        
        $connectProcess = Start-Process -FilePath "$kafkaHome\bin\windows\connect-standalone.bat" `
            -ArgumentList "$kafkaHome\config\syniq-connect-standalone.properties" `
            -WindowStyle Minimized `
            -PassThru
        
        if ($connectProcess) {
            Write-Host "✓ Kafka Connect started (PID: $($connectProcess.Id))" -ForegroundColor Green
            
            # Wait for Connect to be ready
            Write-Host "Waiting for Kafka Connect to be ready..." -ForegroundColor Gray
            $maxAttempts = 20
            $attempt = 0
            $ready = $false
            
            while ($attempt -lt $maxAttempts -and -not $ready) {
                Start-Sleep -Seconds 3
                $attempt++
                try {
                    $response = Invoke-RestMethod -Uri "http://localhost:8083/" -Method Get -TimeoutSec 3 -ErrorAction SilentlyContinue
                    if ($response) {
                        $ready = $true
                        Write-Host "✓ Kafka Connect is ready" -ForegroundColor Green
                    }
                } catch {
                    Write-Host "." -NoNewline -ForegroundColor Gray
                }
            }
            
            if (-not $ready) {
                Write-Host "`n⚠️  Kafka Connect is taking longer than expected" -ForegroundColor Yellow
            }
        } else {
            Write-Host "❌ Failed to start Kafka Connect" -ForegroundColor Red
            exit 1
        }
    }
} else {
    Write-Host "Kafka Connect is already running, skipping start." -ForegroundColor Gray
}

# Step 3: Verify Services
Write-Host "`nStep 3: Verifying services..." -ForegroundColor Yellow

# Test Kafka
try {
    python -c "from kafka import KafkaAdminClient; client = KafkaAdminClient(bootstrap_servers='localhost:9092', request_timeout_ms=3000); print('✓ Kafka broker reachable'); client.close()" 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Kafka broker connection verified" -ForegroundColor Green
    }
} catch {
    Write-Host "⚠️  Could not verify Kafka connection with Python" -ForegroundColor Yellow
}

# Test Kafka Connect
try {
    $connectors = Invoke-RestMethod -Uri "http://localhost:8083/connectors" -Method Get -TimeoutSec 5
    Write-Host "✓ Kafka Connect connection verified ($($connectors.Count) connectors)" -ForegroundColor Green
} catch {
    Write-Host "⚠️  Could not verify Kafka Connect connection" -ForegroundColor Yellow
}

# Step 4: Install Python dependencies (if needed)
Write-Host "`nStep 4: Checking Python dependencies..." -ForegroundColor Yellow
if (Test-Path requirements.txt) {
    $needsInstall = $false
    
    # Quick check if kafka-python is installed
    python -c "import kafka" 2>$null
    if ($LASTEXITCODE -ne 0) {
        $needsInstall = $true
    }
    
    if ($needsInstall) {
        Write-Host "Installing Python dependencies..." -ForegroundColor Yellow
        pip install -q -r requirements.txt
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✓ Dependencies installed" -ForegroundColor Green
        } else {
            Write-Host "⚠️  Some dependencies may have failed to install" -ForegroundColor Yellow
        }
    } else {
        Write-Host "✓ Dependencies already installed" -ForegroundColor Green
    }
}

# Display status
Write-Host "`n╔════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║          🚀 Kafka Integration Ready!               ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════╝" -ForegroundColor Cyan

Write-Host "`n📊 Service Status:" -ForegroundColor Cyan
Write-Host "  • Kafka Broker:      localhost:9092         ✓" -ForegroundColor Green
Write-Host "  • Kafka Connect:     http://localhost:8083  ✓" -ForegroundColor Green

Write-Host "`n🎯 Available Commands:" -ForegroundColor Cyan
Write-Host "  List Topics:" -ForegroundColor White
Write-Host "    cd $kafkaHome" -ForegroundColor Gray
Write-Host "    .\bin\windows\kafka-topics.bat --bootstrap-server localhost:9092 --list" -ForegroundColor Gray

Write-Host "`n  List Connectors:" -ForegroundColor White
Write-Host "    curl http://localhost:8083/connectors" -ForegroundColor Gray

Write-Host "`n  Monitor CDC Events:" -ForegroundColor White
Write-Host "    python monitor_cdc_events.py" -ForegroundColor Gray

Write-Host "`n  Setup CDC Connectors:" -ForegroundColor White
Write-Host "    python setup_cdc_connectors.py" -ForegroundColor Gray

Write-Host "`n📖 Quick Reference:" -ForegroundColor Cyan
Write-Host "  Documentation:     .\SETUP_GUIDE.md" -ForegroundColor Gray
Write-Host "  CDC Setup:         .\CDC_SETUP_GUIDE.md" -ForegroundColor Gray
Write-Host "  Environment:       .\.env" -ForegroundColor Gray

Write-Host "`n✨ Ready to process data!" -ForegroundColor Magenta
Write-Host ""
