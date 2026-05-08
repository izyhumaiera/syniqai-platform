# Native Kafka CDC Setup Guide

## Overview

Your system is running **Native Kafka** (not Docker) at `localhost:9092`. This guide explains how to add database CDC capabilities using Debezium.

## Current Architecture

### ✅ Working Components
- **Kafka Broker**: Native installation at `C:\kafka\kafka-4.2.0` (localhost:9092)
- **PostgreSQL**: localhost:5432
- **MinIO**: localhost:9000 (console at 9001)
- **File Processing Pipeline**:
  - Bronze Ready Emitter (routes files from MinIO CDC)
  - AI Processor (extracts content from files)
  - Working with Bronze → Silver → Gold layers

### ⚠️ Optional: Database CDC
The files you have (debezium_manager.py, fix_debezium.ps1) are for **database CDC** using Debezium. This is separate from your file processing pipeline.

## Two CDC Approaches

### Option 1: File-Based CDC (Currently Working)
**Best for**: Document processing, unstructured data
- ✅ Already configured and working
- ✅ No additional setup needed
- Uses: MinIO events → Bronze Ready Emitter → AI Processor

### Option 2: Database CDC with Debezium (Optional)
**Best for**: Structured database changes (PostgreSQL/MySQL tables)
- ⚠️ Requires Kafka Connect installation
- ⚠️ Requires database configuration (WAL for PostgreSQL, binlog for MySQL)
- Uses: Database changes → Debezium → Kafka topics → Silver CDC Processor

## Setting Up Database CDC (Optional)

### Step 1: Install Kafka Connect
```powershell
cd "Kafka Integration"
.\setup_kafka_connect_native.ps1
```

This will:
- Create plugin directory for Debezium connectors
- Generate Kafka Connect configuration for native Kafka
- Provide download links for Debezium PostgreSQL/MySQL connectors

### Step 2: Download Debezium Connectors

**Automated PowerShell Download:**
```powershell
cd "Kafka Integration"
.\download_debezium_connectors.ps1
```

**Or Manual Download:**
1. PostgreSQL Connector:
   - Download: https://repo1.maven.org/maven2/io/debezium/debezium-connector-postgres/2.4.0.Final/debezium-connector-postgres-2.4.0.Final-plugin.tar.gz
   - Extract to: `C:\kafka\kafka-4.2.0\plugins\debezium-connector-postgres\`

2. MySQL Connector:
   - Download: https://repo1.maven.org/maven2/io/debezium/debezium-connector-mysql/2.4.0.Final/debezium-connector-mysql-2.4.0.Final-plugin.tar.gz
   - Extract to: `C:\kafka\kafka-4.2.0\plugins\debezium-connector-mysql\`

**Using 7-Zip or WinRAR:**
```powershell
# After downloading the .tar.gz files:
# 1. Right-click → Extract Here (twice for .tar.gz)
# 2. Copy extracted folder to C:\kafka\kafka-4.2.0\plugins\
```

**Note**: `confluent-hub` requires Confluent Platform (separate install). The PowerShell script above is easier for Windows users.

### Step 3: Configure PostgreSQL for CDC

Run as PostgreSQL admin:
```sql
-- Enable WAL (requires restart)
ALTER SYSTEM SET wal_level = 'logical';
ALTER SYSTEM SET max_replication_slots = 10;
ALTER SYSTEM SET max_wal_senders = 10;

-- Restart PostgreSQL service
-- PowerShell: Restart-Service postgresql-x64-18

-- Create Debezium user
CREATE USER debezium_user WITH PASSWORD 'debezium_password' REPLICATION LOGIN;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO debezium_user;
GRANT CREATE ON DATABASE postgres TO debezium_user;

-- Create publication
CREATE PUBLICATION dbz_syniq_postgres_publication FOR ALL TABLES;
```

Or use the provided script:
```powershell
python fix_debezium_permissions_local.py
```

### Step 4: Start Kafka Connect

**Terminal 1 - Kafka (already running):**
```powershell
cd C:\kafka\kafka-4.2.0
.\bin\windows\kafka-server-start.bat config\syniq-server.properties
```

**Terminal 2 - Kafka Connect:**
```powershell
cd "Kafka Integration"
.\start_kafka_connect.ps1
```

Wait for: `INFO Kafka Connect started (org.apache.kafka.connect.runtime.Connect)`

### Step 5: Verify Kafka Connect
```powershell
# Check if Kafka Connect is running
curl http://localhost:8083/

# List connector plugins
curl http://localhost:8083/connector-plugins
```

Should show:
- `io.debezium.connector.postgresql.PostgresConnector`
- `io.debezium.connector.mysql.MySqlConnector`

### Step 6: Create Debezium Connector

```python
# test_debezium_setup.py
from debezium_manager import get_debezium_manager, ConnectorConfig

# Initialize manager
manager = get_debezium_manager(
    kafka_connect_url="http://localhost:8083",
    kafka_bootstrap_servers="localhost:9092"
)

# Create PostgreSQL connector
config = ConnectorConfig(
    name="syniq-postgres-connector",
    database_type="postgres",
    hostname="localhost",
    port=5432,
    user="debezium_user",
    password="debezium_password",
    database_name="postgres",
    server_name="syniq_postgres",
    table_include_list=["public.your_table"]  # Specify tables
)

result = manager.create_postgres_connector(config)
print("Connector created:", result)
```

Run:
```powershell
python test_debezium_setup.py
```

### Step 7: Test CDC

```sql
-- Insert test data
INSERT INTO public.your_table (name, value) VALUES ('test', 'data');
```

Check Kafka topic:
```powershell
cd C:\kafka\kafka-4.2.0
.\bin\windows\kafka-console-consumer.bat --bootstrap-server localhost:9092 --topic cdc.syniq_postgres.public.your_table --from-beginning
```

## Architecture Comparison

### File Processing (Current)
```
MinIO Upload → Bronze bucket → Bronze Ready Emitter → bronze-ready topic
             → AI Processor → Silver DB → Gold Analytics
```

### Database CDC (Optional)
```
PostgreSQL Change → Debezium → cdc.syniq_postgres.public.table topic
                  → Silver CDC Processor → Silver tables → Gold Analytics
```

## Startup Sequence (Full Stack)

### For File Processing Only (Current):
1. **Kafka**: `cd C:\kafka\kafka-4.2.0; .\bin\windows\kafka-server-start.bat config\syniq-server.properties`
2. **MinIO**: `C:\syniq\minio\minio.exe server C:\syniq\minio\data --console-address ":9001"`
3. **Bronze Ready Emitter**: `cd "Kafka Integration"; python bronze_ready_emitter.py`
4. **AI Processor**: `cd "Kafka Integration"; python ai_processor.py`
5. **GUI**: `cd gui; npm run dev`

### For Database CDC (Additional):
6. **Kafka Connect**: `cd "Kafka Integration"; .\start_kafka_connect.ps1`
7. **Silver CDC Processor**: `cd "Kafka Integration"; python silver_cdc_processor.py` (requires PySpark)

## Troubleshooting

### Kafka Connect doesn't start
- Check Kafka is running: `Test-NetConnection -ComputerName 127.0.0.1 -Port 9092`
- Check logs in console output
- Verify configuration: `C:\kafka\kafka-4.2.0\config\connect-standalone-native.properties`

### Debezium connector fails
- Test database connection: `python test_debezium_connection.py`
- Verify WAL is enabled: `psql -c "SHOW wal_level;"`
- Check publication exists: `psql -c "SELECT * FROM pg_publication;"`

### Topics not created
- Kafka Connect creates topics automatically
- Check Kafka Connect logs for errors
- Verify bootstrap.servers=localhost:9092 in connector config

## Recommended Approach

**For your current use case (file processing):**
- ✅ Continue using Bronze Ready Emitter + AI Processor
- ✅ No need for Debezium unless you need database CDC
- ✅ Your current setup handles PDF, images, documents perfectly

**Add Debezium only if:**
- You need to track changes in PostgreSQL/MySQL tables
- You want to sync structured data from databases to data lakehouse
- You're implementing the Silver CDC Processor with PySpark

## Quick Reference

### Service URLs
- Kafka Broker: `localhost:9092`
- Kafka Connect: `http://localhost:8083` (when enabled)
- PostgreSQL: `localhost:5432`
- MinIO API: `http://localhost:9000`
- MinIO Console: `http://localhost:9001`
- GUI: `http://localhost:3001`

### Key Files
- Debezium Manager: `Kafka Integration\debezium_manager.py`
- Kafka Connect Config: `C:\kafka\kafka-4.2.0\config\connect-standalone-native.properties`
- Native CDC Connectors: `Kafka Integration\native_cdc_connectors.py` (alternative to Debezium)

### Topics for Database CDC
- Config: `connect-configs`
- Offsets: `connect-offsets`
- Status: `connect-status`
- Data: `cdc.{server_name}.{schema}.{table}`
