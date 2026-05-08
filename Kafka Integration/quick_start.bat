@echo off
REM ============================================================================
REM SYNIQ Quick Start - Simple Batch Script
REM Starts Kafka and AI Processor
REM ============================================================================

echo.
echo ================================================================
echo          SYNIQ AI PROCESSOR - QUICK START
echo ================================================================
echo.

set KAFKA_HOME=C:\kafka\kafka-4.2.0
set KAFKA_CONFIG=%KAFKA_HOME%\config\kraft\syniq-server.properties

echo [1/3] Checking Kafka...
echo.

REM Test if Kafka port is open
powershell -Command "$test = Test-NetConnection -ComputerName 127.0.0.1 -Port 9092 -WarningAction SilentlyContinue -InformationLevel Quiet; if($test) { Write-Host '      [OK] Kafka is already running' -ForegroundColor Green; exit 0 } else { Write-Host '      [!] Kafka is not running - starting now...' -ForegroundColor Yellow; exit 1 }"

if %ERRORLEVEL% EQU 1 (
    echo.
    echo [2/3] Starting Kafka broker...
    echo       Location: %KAFKA_HOME%
    echo       Config: %KAFKA_CONFIG%
    echo.
    
    start "Kafka Broker" /MIN "%KAFKA_HOME%\bin\windows\kafka-server-start.bat" "%KAFKA_CONFIG%"
    
    echo       [OK] Kafka started in background window
    echo       [→] Waiting 20 seconds for Kafka to initialize...
    echo.
    
    timeout /t 20 /nobreak >nul
    
    powershell -Command "$test = Test-NetConnection -ComputerName 127.0.0.1 -Port 9092 -WarningAction SilentlyContinue -InformationLevel Quiet; if($test) { Write-Host '      [OK] Kafka is ready!' -ForegroundColor Green } else { Write-Host '      [WARNING] Kafka may need more time to start' -ForegroundColor Yellow }"
) else (
    echo.
    echo [2/3] Kafka already running - skipping startup
)

echo.
echo [3/3] Starting AI Processor...
echo.
echo ================================================================
echo          AI PROCESSOR RUNNING
echo ================================================================
echo.
echo   Kafka:        127.0.0.1:9092
echo   Bronze Topic: bronze-ready
echo   Silver Topic: silver-ready
echo.
echo   Press Ctrl+C to stop
echo.
echo ================================================================
echo.

cd ..
python "ai processing\ai_processor.py"

echo.
echo.
echo ================================================================
echo   AI Processor stopped
echo ================================================================
pause
