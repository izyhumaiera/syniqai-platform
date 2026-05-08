# ============================================================================
# SyniqAI End-to-End Test Script
# ============================================================================
# Automated verification of all services and processors before testing
# ============================================================================

param(
    [switch]$StartProcessors = $false,
    [switch]$Detailed = $false
)

$ErrorActionPreference = "Continue"

Write-Host ""
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "   SyniqAI End-to-End System Test" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

$allGood = $true

# ============================================================================
# Test 1: Kafka Broker Connectivity
# ============================================================================
Write-Host "[1/7] Testing Kafka Broker..." -ForegroundColor Yellow

try {
    $tcpResult = Test-NetConnection -ComputerName "127.0.0.1" -Port 9092 -WarningAction SilentlyContinue -InformationLevel Quiet
    
    if ($tcpResult.TcpTestSucceeded) {
        Write-Host "  [OK] Kafka broker: CONNECTED (127.0.0.1:9092)" -ForegroundColor Green
    } else {
        Write-Host "  [X] Kafka broker: NOT RESPONDING" -ForegroundColor Red
        Write-Host "     Start Kafka: cd C:\kafka\kafka-4.2.0; .\bin\windows\kafka-server-start.bat .\config\kraft\syniq-server.properties" -ForegroundColor Gray
        $allGood = $false
    }
} catch {
    Write-Host "  [X] Kafka broker: ERROR - $_" -ForegroundColor Red
    $allGood = $false
}

Write-Host ""

# ============================================================================
# Test 2: PostgreSQL Database
# ============================================================================
Write-Host "[2/7] Testing PostgreSQL..." -ForegroundColor Yellow

try {
    $tcpResult = Test-NetConnection -ComputerName "localhost" -Port 5432 -WarningAction SilentlyContinue -InformationLevel Quiet
    
    if ($tcpResult.TcpTestSucceeded) {
        Write-Host "  [OK] PostgreSQL: CONNECTED (localhost:5432)" -ForegroundColor Green
        
        # Try actual database connection
        if ($Detailed) {
            python -c "import psycopg2; conn = psycopg2.connect('postgresql://syniqai_user:syniqai_pass@localhost:5432/syniqai'); print('  [OK] Database syniqai: ACCESSIBLE'); conn.close()" 2>$null
            if ($LASTEXITCODE -ne 0) {
                Write-Host "  [!] Database connection failed - check credentials" -ForegroundColor Yellow
            }
        }
    } else {
        Write-Host "  [X] PostgreSQL: NOT RESPONDING" -ForegroundColor Red
        Write-Host "     Start PostgreSQL: Start-Service postgresql-x64-18" -ForegroundColor Gray
        $allGood = $false
    }
} catch {
    Write-Host "  [X] PostgreSQL: ERROR - $_" -ForegroundColor Red
    $allGood = $false
}

Write-Host ""

# ============================================================================
# Test 3: MinIO Object Storage
# ============================================================================
Write-Host "[3/7] Testing MinIO..." -ForegroundColor Yellow

try {
    $response = Invoke-WebRequest -Uri "http://localhost:9000/minio/health/live" -Method GET -TimeoutSec 3 -UseBasicParsing -ErrorAction SilentlyContinue
    
    if ($response.StatusCode -eq 200) {
        Write-Host "  [OK] MinIO: ONLINE (localhost:9000)" -ForegroundColor Green
        
        if ($Detailed) {
            python -c "from minio import Minio; client = Minio('localhost:9000', 'admin', 'password123', secure=False); buckets = list(client.list_buckets()); print('  Buckets:', len(buckets))" 2>$null
        }
    } else {
        Write-Host "  [X] MinIO: UNEXPECTED RESPONSE" -ForegroundColor Red
        $allGood = $false
    }
} catch {
    Write-Host "  [X] MinIO: NOT RESPONDING" -ForegroundColor Red
    Write-Host "     Check MinIO installation and ensure it's running" -ForegroundColor Gray
    $allGood = $false
}

Write-Host ""

# ============================================================================
# Test 4: Kafka Topics Exist
# ============================================================================
Write-Host "[4/7] Verifying Kafka Topics..." -ForegroundColor Yellow

$requiredTopics = @(
    "bronze-mongodb",
    "bronze-s3", 
    "bronze-ready",
    "bronze-media-pending",
    "silver-ready",
    "dlq-errors"
)

try {
    if (Test-Path "C:\kafka\kafka-4.2.0\bin\windows\kafka-topics.bat") {
        $kafkaTopicsScript = "C:\kafka\kafka-4.2.0\bin\windows\kafka-topics.bat"
        $existingTopics = & $kafkaTopicsScript --list --bootstrap-server 127.0.0.1:9092 2>$null
        
        $missingTopics = @()
        foreach ($topic in $requiredTopics) {
            if ($existingTopics -contains $topic) {
                Write-Host "  [OK] Topic exists: $topic" -ForegroundColor Green
            } else {
                Write-Host "  [X] Topic missing: $topic" -ForegroundColor Red
                $missingTopics += $topic
                $allGood = $false
            }
        }
        
        if ($missingTopics.Count -gt 0) {
            Write-Host ""
            Write-Host "  Create missing topics:" -ForegroundColor Yellow
            foreach ($topic in $missingTopics) {
                Write-Host "     kafka-topics.bat --create --topic $topic --bootstrap-server 127.0.0.1:9092 --partitions 3 --replication-factor 1" -ForegroundColor Gray
            }
        }
    } else {
        Write-Host "  [!] Cannot verify topics - kafka-topics.bat not found" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  [X] Topic verification failed: $_" -ForegroundColor Red
}

Write-Host ""

# ============================================================================
# Test 5: Check Running Processes
# ============================================================================
Write-Host "[5/7] Checking Data Pipeline Processors..." -ForegroundColor Yellow

$processors = @(
    @{Name="Bronze Ready Emitter"; Script="bronze_ready_emitter.py"},
    @{Name="AI Processor"; Script="ai_processor.py"},
    @{Name="Silver CDC Processor"; Script="silver_cdc_processor.py"},
    @{Name="Gold Lineage Consumer"; Script="gold_lineage_consumer.py"}
)

$runningProcessors = 0
$pythonProcesses = Get-Process python -ErrorAction SilentlyContinue

if ($pythonProcesses) {
    foreach ($proc in $processors) {
        $isRunning = $false
        foreach ($p in $pythonProcesses) {
            try {
                $cmdLine = (Get-WmiObject Win32_Process -Filter "ProcessId='$($p.Id)'" -ErrorAction SilentlyContinue).CommandLine
                if ($cmdLine -like "*$($proc.Script)*") {
                    $isRunning = $true
                    $runningProcessors++
                    break
                }
            } catch {
                # Silently continue
            }
        }
        
        if ($isRunning) {
            Write-Host "  [OK] $($proc.Name): RUNNING" -ForegroundColor Green
        } else {
            Write-Host "  [!] $($proc.Name): NOT RUNNING" -ForegroundColor Yellow
            Write-Host "     Start: cd 'Kafka Integration'; python $($proc.Script)" -ForegroundColor Gray
        }
    }
} else {
    Write-Host "  [!] No Python processors running" -ForegroundColor Yellow
    Write-Host "     Run: .\test_end_to_end.ps1 -StartProcessors" -ForegroundColor Gray
}

Write-Host ""
Write-Host "  Running: $runningProcessors / $($processors.Count) processors" -ForegroundColor $(if ($runningProcessors -eq $processors.Count) { "Green" } else { "Yellow" })

Write-Host ""

# ============================================================================
# Test 6: GUI Server
# ============================================================================
Write-Host "[6/7] Checking GUI Server..." -ForegroundColor Yellow

try {
    $response = Invoke-WebRequest -Uri "http://localhost:5173" -Method GET -TimeoutSec 3 -UseBasicParsing -ErrorAction SilentlyContinue
    
    if ($response.StatusCode -eq 200) {
        Write-Host "  [OK] GUI Server: ONLINE (http://localhost:5173)" -ForegroundColor Green
    } else {
        throw "Unexpected response"
    }
} catch {
    Write-Host "  [!] GUI Server: NOT RUNNING" -ForegroundColor Yellow
    Write-Host "     Start: cd gui; npm run dev" -ForegroundColor Gray
}

Write-Host ""

# ============================================================================
# Test 7: Environment Configuration
# ============================================================================
Write-Host "[7/7] Verifying Environment Configuration..." -ForegroundColor Yellow

$envFile = ".\.env"
if (Test-Path $envFile) {
    $envContent = Get-Content $envFile -Raw
    
    # Check critical variables
    $checks = @(
        @{Var="KAFKA_BOOTSTRAP_SERVERS"; Expected="127.0.0.1:9092"},
        @{Var="OPENROUTER_API_KEY"; Expected=$null},
        @{Var="MINIO_ENDPOINT"; Expected="localhost:9000"}
    )
    
    foreach ($check in $checks) {
        if ($envContent -match "$($check.Var)=") {
            if ($check.Expected -and $envContent -match "$($check.Var)=$($check.Expected)") {
                Write-Host "  [OK] $($check.Var): CONFIGURED" -ForegroundColor Green
            } elseif ($check.Expected) {
                Write-Host "  [!] $($check.Var): CHECK VALUE" -ForegroundColor Yellow
            } else {
                Write-Host "  [OK] $($check.Var): SET" -ForegroundColor Green
            }
        } else {
            Write-Host "  [X] $($check.Var): MISSING" -ForegroundColor Red
            $allGood = $false
        }
    }
} else {
    Write-Host "  [X] .env file not found in root directory" -ForegroundColor Red
    $allGood = $false
}

Write-Host ""
Write-Host "================================================================" -ForegroundColor Cyan

# ============================================================================
# Summary and Next Steps
# ============================================================================
if ($allGood -and $runningProcessors -eq $processors.Count) {
    Write-Host ""
    Write-Host "[SUCCESS] ALL SYSTEMS READY FOR END-TO-END TESTING!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next Steps:" -ForegroundColor Cyan
    Write-Host "  1. Open GUI: http://localhost:5173" -ForegroundColor White
    Write-Host "  2. Follow guide: .\END_TO_END_TEST_GUIDE.md" -ForegroundColor White
    Write-Host "  3. Upload test file via Bronze Explorer" -ForegroundColor White
    Write-Host "  4. Monitor processor terminals for activity" -ForegroundColor White
    Write-Host ""
} elseif ($allGood) {
    Write-Host ""
    Write-Host "[PARTIAL] CORE SERVICES READY - START PROCESSORS" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Quick Start All Processors:" -ForegroundColor Cyan
    Write-Host "  .\test_end_to_end.ps1 -StartProcessors" -ForegroundColor White
    Write-Host ""
    Write-Host "Or manually start each:" -ForegroundColor Cyan
    Write-Host "  Terminal 1: cd 'Kafka Integration'; python bronze_ready_emitter.py" -ForegroundColor White
    Write-Host "  Terminal 2: cd 'ai processing'; python ai_processor.py" -ForegroundColor White
    Write-Host "  Terminal 3: cd 'Kafka Integration'; python silver_cdc_processor.py" -ForegroundColor White
    Write-Host "  Terminal 4: cd 'Kafka Integration'; python gold_lineage_consumer.py" -ForegroundColor White
    Write-Host ""
} else {
    Write-Host ""
    Write-Host "[FAILED] SYSTEM NOT READY - FIX ISSUES ABOVE" -ForegroundColor Red
    Write-Host ""
    Write-Host "Common Fixes:" -ForegroundColor Cyan
    Write-Host "  - Restart all: .\restart_all_native.ps1" -ForegroundColor White
    Write-Host "  - Check Kafka: Test-NetConnection 127.0.0.1 -Port 9092" -ForegroundColor White
    Write-Host "  - View logs: C:\kafka\kafka-4.2.0\logs" -ForegroundColor White
    Write-Host ""
}

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

# ============================================================================
# Optional: Auto-start Processors
# ============================================================================
if ($StartProcessors -and $allGood) {
    Write-Host "Starting all processors..." -ForegroundColor Yellow
    Write-Host ""
    
    $kafkaIntegration = "Kafka Integration"
    
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$kafkaIntegration'; Write-Host 'Bronze Ready Emitter' -ForegroundColor Green; python bronze_ready_emitter.py"
    Start-Sleep -Seconds 2
    
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$kafkaIntegration'; Write-Host 'AI Processor' -ForegroundColor Green; python ai_processor.py"
    Start-Sleep -Seconds 2
    
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$kafkaIntegration'; Write-Host 'Silver CDC Processor' -ForegroundColor Green; python silver_cdc_processor.py"
    Start-Sleep -Seconds 2
    
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$kafkaIntegration'; Write-Host 'Gold Lineage Consumer' -ForegroundColor Green; python gold_lineage_consumer.py"
    
    Write-Host "[OK] All processors started in separate windows" -ForegroundColor Green
    Write-Host "   Wait 10 seconds for initialization..." -ForegroundColor Yellow
    Write-Host ""
}

exit 0
