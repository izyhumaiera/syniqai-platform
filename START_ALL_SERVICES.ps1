# ============================================================================
# SyniqAI - Complete Application Startup Script
# ============================================================================
# Starts all components in the correct order with health checks
# Date: April 13, 2026
# ============================================================================

param(
    [switch]$SkipMinIO,
    [switch]$SkipKafka,
    [switch]$SkipFrontend
)

$ErrorActionPreference = "Continue"
$script:workspaceRoot = $PSScriptRoot

# Console colors
function Write-Step { param($msg) Write-Host "`n[STEP] $msg" -ForegroundColor Cyan }
function Write-Success { param($msg) Write-Host "  [OK] $msg" -ForegroundColor Green }
function Write-Info { param($msg) Write-Host "  [i] $msg" -ForegroundColor Gray }
function Write-Warning { param($msg) Write-Host "  [!] $msg" -ForegroundColor Yellow }
function Write-Error { param($msg) Write-Host "  [X] $msg" -ForegroundColor Red }

Write-Host ""
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "   SyniqAI - Complete Application Startup" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

# ============================================================================
# STEP 1: Verify Prerequisites
# ============================================================================
Write-Step "Verifying prerequisites..."

# Check Java 17
try {
    $javaVersion = java -version 2>&1 | Select-String "version" | Out-String
    if ($javaVersion -match '"17\.') {
        Write-Success "Java 17 detected"
    } else {
        Write-Warning "Java version may not be 17. Required for Kafka."
        Write-Info $javaVersion
    }
} catch {
    Write-Error "Java not found. Install Java 17 from https://adoptium.net"
}

# Check Python
try {
    $pythonVersion = python --version 2>&1
    Write-Success "Python detected: $pythonVersion"
} catch {
    Write-Error "Python not found. Install Python 3.9+"
}

# Check Node.js (for frontend)
if (-not $SkipFrontend) {
    try {
        $nodeVersion = node --version 2>&1
        Write-Success "Node.js detected: $nodeVersion"
    } catch {
        Write-Warning "Node.js not found. Frontend will not start."
        $SkipFrontend = $true
    }
}

# ============================================================================
# STEP 2: Verify PostgreSQL
# ============================================================================
Write-Step "Checking PostgreSQL..."

try {
    $conn = New-Object System.Net.Sockets.TcpClient
    $conn.Connect("localhost", 5432)
    $conn.Close()
    Write-Success "PostgreSQL is running on port 5432"
} catch {
    Write-Error "PostgreSQL not running. Start it manually:"
    Write-Info "  - Open Services (services.msc)"
    Write-Info "  - Find 'postgresql-x64-14' or similar"
    Write-Info "  - Click 'Start'"
    Write-Host ""
    $continue = Read-Host "Continue anyway? (y/N)"
    if ($continue -ne 'y') { exit 1 }
}

# ============================================================================
# STEP 3: Start MinIO
# ============================================================================
if (-not $SkipMinIO) {
    Write-Step "Starting MinIO..."
    
    $minioExe = "C:\minio\minio.exe"
    $minioData = "C:\minio\data"
    
    if (Test-Path $minioExe) {
        # Check if already running
        $minioRunning = Get-Process minio -ErrorAction SilentlyContinue
        if ($minioRunning) {
            Write-Warning "MinIO already running (PID: $($minioRunning.Id))"
        } else {
            # Ensure data directory exists
            if (-not (Test-Path $minioData)) {
                New-Item -ItemType Directory -Path $minioData -Force | Out-Null
            }
            
            # Start MinIO
            Start-Process -FilePath $minioExe -ArgumentList "server", $minioData, "--console-address", ":9001" -WindowStyle Normal
            Start-Sleep -Seconds 3
            
            # Verify MinIO started
            try {
                $response = Invoke-WebRequest -Uri "http://localhost:9000/minio/health/live" -Method GET -TimeoutSec 5 -UseBasicParsing
                Write-Success "MinIO started successfully"
                Write-Info "  API: http://localhost:9000"
                Write-Info "  Console: http://localhost:9001"
            } catch {
                Write-Warning "MinIO started but health check failed (may need time to initialize)"
            }
        }
    } else {
        Write-Error "MinIO not found at $minioExe"
        Write-Info "Download from: https://min.io/download"
    }
} else {
    Write-Info "Skipping MinIO (--SkipMinIO flag)"
}

# ============================================================================
# STEP 4: Start Kafka Brokers
# ============================================================================
if (-not $SkipKafka) {
    Write-Step "Starting Kafka brokers..."
    
    $kafkaScript = Join-Path $script:workspaceRoot "Kafka Integration\start_kafka_native.ps1"
    
    if (Test-Path $kafkaScript) {
        # Check if Kafka already running
        $javaProcesses = Get-Process java -ErrorAction SilentlyContinue
        $kafkaRunning = $javaProcesses | Where-Object { $_.CommandLine -like "*kafka.Kafka*" }
        
        if ($kafkaRunning) {
            Write-Warning "Kafka already running (PID: $($kafkaRunning.Id))"
        } else {
            Write-Info "Executing: $kafkaScript"
            & $kafkaScript
            
            # Wait for Kafka to be ready
            Write-Info "Waiting for Kafka to be ready..."
            $maxWait = 30
            $waited = 0
            $ready = $false
            
            while ($waited -lt $maxWait -and -not $ready) {
                Start-Sleep -Seconds 2
                $waited += 2
                
                try {
                    $conn = New-Object System.Net.Sockets.TcpClient
                    $conn.Connect("127.0.0.1", 9092)
                    $conn.Close()
                    $ready = $true
                    Write-Success "Kafka broker ready on 127.0.0.1:9092"
                } catch {
                    Write-Host "." -NoNewline
                }
            }
            
            if (-not $ready) {
                Write-Warning "Kafka health check timeout (may still be starting)"
            }
        }
    } else {
        Write-Error "Kafka startup script not found: $kafkaScript"
    }
} else {
    Write-Info "Skipping Kafka (--SkipKafka flag)"
}

# ============================================================================
# STEP 5: Start FastAPI Backend
# ============================================================================
Write-Step "Starting FastAPI backend..."

$backendPath = Join-Path $script:workspaceRoot "gui\api"
$backendScript = Join-Path $backendPath "backend.py"

if (Test-Path $backendScript) {
    # Check if already running
    $backendRunning = Get-Process python -ErrorAction SilentlyContinue | Where-Object { 
        $_.CommandLine -like "*backend.py*" -or $_.CommandLine -like "*uvicorn*backend*"
    }
    
    if ($backendRunning) {
        Write-Warning "Backend already running (PID: $($backendRunning.Id))"
    } else {
        # Start backend in new terminal
        Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$backendPath'; Write-Host 'Starting FastAPI Backend...' -ForegroundColor Cyan; python -m uvicorn backend:app --reload --port 8000"
        
        Start-Sleep -Seconds 5
        
        # Verify backend started
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:8000/docs" -Method GET -TimeoutSec 5 -UseBasicParsing
            Write-Success "FastAPI backend started"
            Write-Info "  API Docs: http://localhost:8000/docs"
        } catch {
            Write-Warning "Backend started but health check failed (may need time)"
        }
    }
} else {
    Write-Error "Backend script not found: $backendScript"
}

# ============================================================================
# STEP 6: Start AI Processor Worker
# ============================================================================
Write-Step "Starting AI Processor worker..."

$aiProcessorPath = Join-Path $script:workspaceRoot "ai processing"
$aiProcessorScript = Join-Path $aiProcessorPath "ai_processor.py"

if (Test-Path $aiProcessorScript) {
    # Check if already running
    $aiRunning = Get-Process python -ErrorAction SilentlyContinue | Where-Object { 
        $_.CommandLine -like "*ai_processor.py*"
    }
    
    if ($aiRunning) {
        Write-Warning "AI Processor already running (PID: $($aiRunning.Id))"
    } else {
        # Start AI processor in new terminal
        Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$aiProcessorPath'; Write-Host 'Starting AI Processor...' -ForegroundColor Cyan; python ai_processor.py"
        
        Write-Success "AI Processor started"
        Write-Info "  Processing: Images, PDFs, Documents"
        Write-Info "  Models: Qwen Vision + Text (via OpenRouter)"
    }
} else {
    Write-Error "AI Processor not found: $aiProcessorScript"
}

# ============================================================================
# STEP 7: Start Bronze Ready Emitter
# ============================================================================
Write-Step "Starting Bronze Ready Emitter..."

$bronzePath = Join-Path $script:workspaceRoot "Kafka Integration"
$bronzeScript = Join-Path $bronzePath "bronze_ready_emitter.py"

if (Test-Path $bronzeScript) {
    # Check if already running
    $bronzeRunning = Get-Process python -ErrorAction SilentlyContinue | Where-Object { 
        $_.CommandLine -like "*bronze_ready_emitter.py*"
    }
    
    if ($bronzeRunning) {
        Write-Warning "Bronze Ready Emitter already running (PID: $($bronzeRunning.Id))"
    } else {
        # Start emitter in new terminal
        Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$bronzePath'; Write-Host 'Starting Bronze Ready Emitter...' -ForegroundColor Cyan; python bronze_ready_emitter.py"
        
        Write-Success "Bronze Ready Emitter started"
        Write-Info "  Routes files from Bronze to AI processing"
    }
} else {
    Write-Warning "Bronze Ready Emitter not found (optional component)"
}

# ============================================================================
# STEP 8: Start CDC Consumer
# ============================================================================
Write-Step "Starting CDC Consumer..."

$cdcPath = Join-Path $script:workspaceRoot "Kafka Integration"
$cdcScript = Join-Path $cdcPath "cdc_consumer_native.py"

if (Test-Path $cdcScript) {
    # Check if already running
    $cdcRunning = Get-Process python -ErrorAction SilentlyContinue | Where-Object { 
        $_.CommandLine -like "*cdc_consumer_native.py*"
    }
    
    if ($cdcRunning) {
        Write-Warning "CDC Consumer already running (PID: $($cdcRunning.Id))"
    } else {
        # Start consumer in new terminal
        Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$cdcPath'; Write-Host 'Starting CDC Consumer...' -ForegroundColor Cyan; python cdc_consumer_native.py"
        
        Write-Success "CDC Consumer started"
        Write-Info "  Replicates CDC events to PostgreSQL Silver"
    }
} else {
    Write-Warning "CDC Consumer not found (optional component)"
}

# ============================================================================
# STEP 9: Start React Frontend
# ============================================================================
if (-not $SkipFrontend) {
    Write-Step "Starting React frontend..."
    
    $frontendPath = Join-Path $script:workspaceRoot "gui"
    $packageJson = Join-Path $frontendPath "package.json"
    
    if (Test-Path $packageJson) {
        # Check if already running
        $nodeRunning = Get-Process node -ErrorAction SilentlyContinue | Where-Object { 
            $_.CommandLine -like "*react-scripts*" -or $_.CommandLine -like "*vite*"
        }
        
        if ($nodeRunning) {
            Write-Warning "Frontend already running (PID: $($nodeRunning.Id))"
        } else {
            # Install dependencies if needed
            $nodeModules = Join-Path $frontendPath "node_modules"
            if (-not (Test-Path $nodeModules)) {
                Write-Info "Installing npm dependencies..."
                Push-Location $frontendPath
                npm install
                Pop-Location
            }
            
            # Start frontend in new terminal
            $frontendCmd = "cd '$frontendPath'; Write-Host 'Starting React Frontend...' -ForegroundColor Cyan; npm start"
            Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendCmd
            
            Write-Success "React frontend starting..."
            Write-Info "  Will open at: http://localhost:3000"
        }
    } else {
        Write-Warning "Frontend package.json not found (optional component)"
    }
} else {
    Write-Info "Skipping Frontend (--SkipFrontend flag)"
}

# ============================================================================
# Summary
# ============================================================================
Write-Host ""
Write-Host "================================================================" -ForegroundColor Green
Write-Host "   SyniqAI Startup Complete!" -ForegroundColor Green
Write-Host "================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Services Running:" -ForegroundColor Cyan
Write-Host "  [OK] PostgreSQL:        localhost:5432" -ForegroundColor Gray
if (-not $SkipMinIO) {
    Write-Host "  [OK] MinIO API:         http://localhost:9000" -ForegroundColor Gray
    Write-Host "  [OK] MinIO Console:     http://localhost:9001" -ForegroundColor Gray
}
if (-not $SkipKafka) {
    Write-Host "  [OK] Kafka Broker:      127.0.0.1:9092" -ForegroundColor Gray
}
Write-Host "  [OK] FastAPI Backend:   http://localhost:8000" -ForegroundColor Gray
Write-Host "  [OK] API Docs:          http://localhost:8000/docs" -ForegroundColor Gray
Write-Host "  [OK] AI Processor:      Running" -ForegroundColor Gray
Write-Host "  [OK] Bronze Emitter:    Running" -ForegroundColor Gray
Write-Host "  [OK] CDC Consumer:      Running" -ForegroundColor Gray
if (-not $SkipFrontend) {
    Write-Host "  [OK] React Frontend:    http://localhost:3000" -ForegroundColor Gray
}
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "  1. Open http://localhost:8000/docs to test APIs" -ForegroundColor Gray
if (-not $SkipFrontend) {
    Write-Host "  2. Open http://localhost:3000 for the dashboard" -ForegroundColor Gray
}
Write-Host "  3. Check each terminal window for component logs" -ForegroundColor Gray
Write-Host ""
Write-Host "To Stop All Services:" -ForegroundColor Yellow
Write-Host "  Run: .\STOP_ALL_SERVICES.ps1" -ForegroundColor Gray
Write-Host ""
