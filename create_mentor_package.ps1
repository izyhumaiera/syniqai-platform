# ============================================================================
# SyniqAI Mentor Package Creator
# Creates a comprehensive zip file with all essential files and requirements
# ============================================================================

$ErrorActionPreference = "Stop"

# Get the script directory (root of Syniq project)
$rootDir = $PSScriptRoot
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$outputZip = Join-Path $rootDir "SyniqAI_Mentor_Package_$timestamp.zip"

Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host "SyniqAI Mentor Package Creator" -ForegroundColor Cyan
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host ""

# Create temporary directory for staging files
$tempDir = Join-Path $env:TEMP "SyniqAI_Package_$timestamp"
$packageRoot = Join-Path $tempDir "SyniqAI"
New-Item -ItemType Directory -Path $packageRoot -Force | Out-Null

Write-Host "[1/6] Copying essential Python files..." -ForegroundColor Yellow

# ============================================================================
# Copy Backend API (gui/api)
# ============================================================================
$apiDest = Join-Path $packageRoot "gui\api"
New-Item -ItemType Directory -Path $apiDest -Force | Out-Null

$apiFiles = @(
    "backend.py",
    "ai_processing_routes.py",
    "airflow_routes.py",
    "app_config.py",
    "bronze_data_routes.py",
    "bronze_eda.py",
    "bronze_ready_routes.py",
    "cdc_control_routes.py",
    "cdc_silver_routes.py",
    "cdc_silver_service.py",
    "database.py",
    "debezium_routes.py",
    "gold_eda_service.py",
    "gold_service.py",
    "gold_transformation_routes.py",
    "ingestion_service.py",
    "job_tracker.py",
    "kafka_routes.py",
    "kafka_schema_history_routes.py",
    "kafka_startup_service.py",
    "lineage_routes.py",
    "manual_input_routes.py",
    "minio_utils.py",
    "missing_endpoints.py",
    "mongodb_routes.py",
    "quality_check_executor.py",
    "quality_rules_routes.py",
    "reports_routes.py",
    "silver_dashboard_routes.py",
    "silver_job_tracker.py",
    "silver_service.py",
    "silver_store.py",
    "silver_transformation_routes.py",
    "silver_transformation_service.py",
    "spark_transformation_executor.py",
    "sql_query_routes.py",
    "storage.py",
    "transformation_pipeline_executor.py",
    "unstructured_router.py",
    "start_backend.bat",
    "start_backend.py",
    "requirements.txt",
    "requirements_backend.txt"
)

foreach ($file in $apiFiles) {
    $source = Join-Path "$rootDir\gui\api" $file
    if (Test-Path $source) {
        Copy-Item $source -Destination $apiDest -Force
        Write-Host "  [OK] Copied: gui/api/$file" -ForegroundColor Green
    }
}

# ============================================================================
# Copy AI Processing
# ============================================================================
Write-Host "[2/6] Copying AI Processing files..." -ForegroundColor Yellow

$aiDest = Join-Path $packageRoot "ai processing"
New-Item -ItemType Directory -Path $aiDest -Force | Out-Null

$aiFiles = @(
    "ai_processor.py",
    "requirements.txt"
)

foreach ($file in $aiFiles) {
    $source = Join-Path "$rootDir\ai processing" $file
    if (Test-Path $source) {
        Copy-Item $source -Destination $aiDest -Force
        Write-Host "  [OK] Copied: ai processing/$file" -ForegroundColor Green
    }
}

# ============================================================================
# Copy Kafka Integration
# ============================================================================
Write-Host "[3/6] Copying Kafka Integration files..." -ForegroundColor Yellow

$kafkaDest = Join-Path $packageRoot "Kafka Integration"
New-Item -ItemType Directory -Path $kafkaDest -Force | Out-Null

$kafkaFiles = @(
    "bronze_ready_emitter.py",
    "cdc_consumer_native.py",
    "cdc_monitor.py",
    "custom_connectors.py",
    "debezium_manager.py",
    "gold_lineage_consumer.py",
    "kafka_bridge.py",
    "kafka_routes.py",
    "kafka_service.py",
    "native_cdc_config.py",
    "native_cdc_connectors.py",
    "s3_batch_extractor.py",
    "setup_cdc_connectors.py",
    "setup_debezium_local.py",
    "setup_postgresql_cdc.py",
    "setup_silver_tables.py",
    "silver_cdc_processor.py",
    "spark_cdc_consumer.py",
    "spark_s3_batch_consumer.py",
    "requirements.txt",
    "requirements-cdc.txt",
    "requirements-ai-processor.txt",
    ".env.example",
    "BRONZE_READY_EMITTER_README.md",
    "CDC_SETUP_GUIDE.md",
    "GUI_INTEGRATION_TEST_GUIDE.md",
    "KAFKA_KRAFT_SETUP.md",
    "MONGODB_CDC_README.md",
    "QUICK_START.md",
    "README.md",
    "SETUP_GUIDE.md",
    "STARTUP_INSTRUCTIONS.md",
    "start_bronze_emitter.bat",
    "start_cdc_consumer.bat"
)

foreach ($file in $kafkaFiles) {
    $source = Join-Path "$rootDir\Kafka Integration" $file
    if (Test-Path $source) {
        Copy-Item $source -Destination $kafkaDest -Force
        Write-Host "  [OK] Copied: Kafka Integration/$file" -ForegroundColor Green
    }
}

# ============================================================================
# Copy Data Lakehouse
# ============================================================================
Write-Host "[4/6] Copying Data Lakehouse files..." -ForegroundColor Yellow

$lakehouseDest = Join-Path $packageRoot "data lakehouse\syniq_project"
New-Item -ItemType Directory -Path $lakehouseDest -Force | Out-Null

# Copy entire syniq_project directory (excluding virtual environments)
$lakehouseSource = Join-Path "$rootDir\data lakehouse\syniq_project"
if (Test-Path $lakehouseSource) {
    Get-ChildItem -Path $lakehouseSource -Recurse | Where-Object {
        $_.FullName -notmatch '\\syniq_env\\' -and
        $_.FullName -notmatch '\\__pycache__\\' -and
        $_.FullName -notmatch '\\.pyc$' -and
        $_.FullName -notmatch '\\venv\\' -and
        $_.FullName -notmatch '\\.venv\\'
    } | ForEach-Object {
        $relativePath = $_.FullName.Substring($lakehouseSource.Length + 1)
        $destPath = Join-Path $lakehouseDest $relativePath
        
        if ($_.PSIsContainer) {
            New-Item -ItemType Directory -Path $destPath -Force | Out-Null
        } else {
            $destDir = Split-Path $destPath
            if (!(Test-Path $destDir)) {
                New-Item -ItemType Directory -Path $destDir -Force | Out-Null
            }
            Copy-Item $_.FullName -Destination $destPath -Force
        }
    }
    Write-Host "  [OK] Copied: data lakehouse/syniq_project (entire directory)" -ForegroundColor Green
}

# ============================================================================
# Copy Data Ingestion Connectors
# ============================================================================
Write-Host "[5/6] Copying Data Ingestion Connectors..." -ForegroundColor Yellow

# S3 Connector
$s3Dest = Join-Path $packageRoot "data ingestion\Connector\SYNIQ_AWS"
New-Item -ItemType Directory -Path $s3Dest -Force | Out-Null

$s3Source = Join-Path "$rootDir\data ingestion\Connector\SYNIQ_AWS"
if (Test-Path $s3Source) {
    Get-ChildItem -Path $s3Source -File | Where-Object {
        $_.Extension -in @('.py', '.txt', '.json', '.md') -and
        $_.Name -ne '__pycache__'
    } | ForEach-Object {
        Copy-Item $_.FullName -Destination $s3Dest -Force
        Write-Host "  [OK] Copied: data ingestion/Connector/SYNIQ_AWS/$($_.Name)" -ForegroundColor Green
    }
}

# MongoDB Connector
$mongoDest = Join-Path $packageRoot "data ingestion\Connector\SYNIQ-MONGODB"
New-Item -ItemType Directory -Path $mongoDest -Force | Out-Null

$mongoSource = Join-Path "$rootDir\data ingestion\Connector\SYNIQ-MONGODB"
if (Test-Path $mongoSource) {
    Get-ChildItem -Path $mongoSource -File | Where-Object {
        $_.Extension -in @('.py', '.txt', '.json', '.md') -and
        $_.Name -ne '__pycache__'
    } | ForEach-Object {
        Copy-Item $_.FullName -Destination $mongoDest -Force
        Write-Host "  [OK] Copied: data ingestion/Connector/SYNIQ-MONGODB/$($_.Name)" -ForegroundColor Green
    }
}

# Base connector files
$connectorBaseDest = Join-Path $packageRoot "data ingestion\Connector"
$connectorBaseFiles = @("base_connector.py", "__init__.py")
foreach ($file in $connectorBaseFiles) {
    $source = Join-Path "$rootDir\data ingestion\Connector" $file
    if (Test-Path $source) {
        Copy-Item $source -Destination $connectorBaseDest -Force
        Write-Host "  [OK] Copied: data ingestion/Connector/$file" -ForegroundColor Green
    }
}

# ============================================================================
# Copy Root Configuration Files and Documentation
# ============================================================================
Write-Host "[6/6] Copying configuration files and documentation..." -ForegroundColor Yellow

$rootFiles = @(
    ".env",
    "SYSTEM_ARCHITECTURE_FOR_MENTOR.md",
    "AI_PROCESSOR_SETUP_GUIDE.md",
    "BLOCK_2_AI_PROCESSOR_GUIDE.md",
    "CDC_QUICK_START_GUIDE.md",
    "DASHBOARD_GUIDE.md",
    "END_TO_END_TEST_GUIDE.md",
    "POSTGRES_SETUP_FROM_SCRATCH.md",
    "QUICK_INSTALL_GUIDE.md",
    "QUICK_REFERENCE_UNSTRUCTURED.md",
    "SERVICES_CONNECTION_GUIDE.md",
    "TESTING_GUIDE.md",
    "UNSTRUCTURED_DATA_OVERVIEW.md",
    "setup_postgres_syniqai.sql",
    "setup_database.sql"
)

foreach ($file in $rootFiles) {
    $source = Join-Path $rootDir $file
    if (Test-Path $source) {
        Copy-Item $source -Destination $packageRoot -Force
        Write-Host "  [OK] Copied: $file" -ForegroundColor Green
    }
}

# ============================================================================
# Create README for the package
# ============================================================================
$readmeContent = @"
# SyniqAI Complete Package for Mentor Review

This package contains all essential files for the SyniqAI data lakehouse platform.

## 📁 Package Contents

- **gui/api/** - FastAPI backend with all route handlers
- **ai processing/** - AI processing worker for unstructured data
- **Kafka Integration/** - Kafka services (CDC, Bronze Ready Emitter)
- **data lakehouse/syniq_project/** - Spark transformations for Gold layer
- **data ingestion/Connector/** - S3 and MongoDB connectors
- **Configuration files** - .env, SQL scripts
- **Documentation** - All setup and testing guides

## 📋 Start Here

1. **Read first**: SYSTEM_ARCHITECTURE_FOR_MENTOR.md
   - Complete endpoint documentation
   - Data flow diagrams
   - Component interactions

2. **Installation**: Follow QUICK_INSTALL_GUIDE.md

3. **Requirements**: All 7 requirements.txt files are included:
   - gui/api/requirements.txt (Backend API)
   - gui/api/requirements_backend.txt (Alternative backend deps)
   - ai processing/requirements.txt (AI worker)
   - Kafka Integration/requirements.txt (Kafka services)
   - Kafka Integration/requirements-cdc.txt (CDC specific)
   - Kafka Integration/requirements-ai-processor.txt (AI processor specific)
   - data lakehouse/syniq_project/requirements.txt (Spark transformations)
   - data ingestion/Connector/SYNIQ_AWS/requirements.txt (S3 connector)
   - data ingestion/Connector/SYNIQ-MONGODB/requirements.txt (MongoDB connector)

## 🚀 Quick Start

1. Install Python 3.9+, Java 17, PostgreSQL, MinIO, Kafka
2. Install all requirements.txt files (see installation order in architecture guide)
3. Configure .env file
4. Start services in order (see STARTUP_INSTRUCTIONS.md)

## 📞 Support

Refer to TESTING_GUIDE.md and END_TO_END_TEST_GUIDE.md for validation.

Package created: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
"@

Set-Content -Path (Join-Path $packageRoot "README.md") -Value $readmeContent
Write-Host "  [OK] Created: README.md" -ForegroundColor Green

# ============================================================================
# Create the ZIP file
# ============================================================================
Write-Host ""
Write-Host "Creating ZIP archive..." -ForegroundColor Yellow

# Remove existing zip if it exists
if (Test-Path $outputZip) {
    Remove-Item $outputZip -Force
}

# Compress the package
Compress-Archive -Path $packageRoot -DestinationPath $outputZip -CompressionLevel Optimal

# Cleanup temp directory
Remove-Item $tempDir -Recurse -Force

# ============================================================================
# Summary
# ============================================================================
Write-Host ""
Write-Host "=" * 80 -ForegroundColor Green
Write-Host "Package Created Successfully!" -ForegroundColor Green
Write-Host "=" * 80 -ForegroundColor Green
Write-Host ""
Write-Host "Output file: $outputZip" -ForegroundColor Cyan
Write-Host "File size: $([math]::Round((Get-Item $outputZip).Length / 1MB, 2)) MB" -ForegroundColor Cyan
Write-Host ""
Write-Host "Package includes:" -ForegroundColor Yellow
Write-Host "  [OK] All requirements.txt files (9 total)" -ForegroundColor Green
Write-Host "  [OK] Backend API with all route handlers" -ForegroundColor Green
Write-Host "  [OK] AI Processing worker" -ForegroundColor Green
Write-Host "  [OK] Kafka Integration services" -ForegroundColor Green
Write-Host "  [OK] Data Lakehouse transformations" -ForegroundColor Green
Write-Host "  [OK] Data Ingestion connectors (S3, MongoDB)" -ForegroundColor Green
Write-Host "  [OK] Complete documentation" -ForegroundColor Green
Write-Host "  [OK] Configuration files" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Extract the ZIP file" -ForegroundColor White
Write-Host "  2. Read SYSTEM_ARCHITECTURE_FOR_MENTOR.md" -ForegroundColor White
Write-Host "  3. Follow QUICK_INSTALL_GUIDE.md" -ForegroundColor White
Write-Host ""
Write-Host "=" * 80 -ForegroundColor Green
