@echo off
REM Start Bronze Ready Emitter
REM Consumes from bronze-mongodb and bronze-s3 topics
REM Routes events to bronze-ready or bronze-media-pending based on file type

echo ============================================================
echo  Bronze Ready Emitter - Starting
echo ============================================================
echo.

REM Check for .env file
if exist .env (
    echo [*] Found .env file - environment variables will be loaded
) else (
    echo [!] WARNING: .env file not found - using defaults
    echo     Expected location: Kafka Integration\.env
)

echo.
echo Configuration:
echo   KAFKA_BOOTSTRAP_SERVERS: %KAFKA_BOOTSTRAP_SERVERS%
echo   MINIO_ENDPOINT: %MINIO_ENDPOINT%
echo.

REM Start the emitter
echo [%date% %time%] Starting Bronze Ready Emitter...
python bronze_ready_emitter.py

REM Handle exit
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [!] Bronze Ready Emitter exited with error code %ERRORLEVEL%
    pause
) else (
    echo.
    echo [*] Bronze Ready Emitter stopped gracefully
)
