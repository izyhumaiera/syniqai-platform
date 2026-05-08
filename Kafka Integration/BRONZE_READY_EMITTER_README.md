# Bronze Ready Emitter

## Overview

The **Bronze Ready Emitter** is a Kafka consumer service that acts as a routing layer between the Bronze ingestion topics and downstream AI processing. It listens to `bronze-mongodb` and `bronze-s3` topics, detects file types, and routes messages to appropriate downstream topics based on the file type.

## Architecture

```
┌─────────────────┐     ┌─────────────────┐
│ bronze-mongodb  │────▶│                 │
└─────────────────┘     │  Bronze Ready   │      ┌──────────────────┐
                        │    Emitter      │─────▶│ bronze-ready     │
┌─────────────────┐     │                 │      │ (auto-process)   │
│  bronze-s3      │────▶│  (this service) │      └──────────────────┘
└─────────────────┘     │                 │
                        │                 │      ┌──────────────────┐
                        └─────────────────┘─────▶│ bronze-media-    │
                                                 │ pending          │
                                                 │ (user-triggered) │
                                                 └──────────────────┘
```

## Routing Logic

| File Type | Extensions | Destination Topic | Processing |
|-----------|-----------|------------------|------------|
| **PDF** | `.pdf` | `bronze-ready` | Auto-process |
| **Text** | `.txt`, `.log`, `.md`, `.csv`, `.json`, `.xml`, `.html` | `bronze-ready` | Auto-process |
| **Image** | `.jpg`, `.jpeg`, `.png`, `.gif`, `.bmp`, `.webp`, `.svg` | `bronze-ready` | Auto-process |
| **Audio** | `.mp3`, `.wav`, `.flac`, `.aac`, `.ogg`, `.m4a` | `bronze-media-pending` | Wait for user trigger |
| **Video** | `.mp4`, `.avi`, `.mov`, `.mkv`, `.wmv`, `.webm` | `bronze-media-pending` | Wait for user trigger |
| **Unknown** | Other | `bronze-ready` | Auto-process (can be filtered) |

## Message Flow

### Input Message Format

#### MongoDB Source (bronze-mongodb)
```json
{
    "op": "insert/update/delete/read",
    "source": {
        "db": "database_name",
        "collection": "collection_name",
        "ts_ms": 1234567890000
    },
    "after": {
        "_id": "document_id",
        ...
    }
}
```

#### S3 Source (bronze-s3)
```json
{
    "op": "create/update/delete",
    "source": {
        "bucket": "bucket_name",
        "region": "us-east-1",
        "ts_ms": 1234567890000
    },
    "file": {
        "key": "path/to/file.pdf",
        "etag": "abc123",
        "size": 1024,
        "last_modified": "2024-01-01T00:00:00Z",
        "s3_uri": "s3://bucket/path/to/file.pdf"
    }
}
```

### Output Message Format

Both `bronze-ready` and `bronze-media-pending` topics receive messages in this format:

```json
{
    "source": "mongodb or s3",
    "file_type": "pdf/txt/image/audio/video",
    "bronze_minio_key": "syniqai-bronze/mongodb/db_collection/timestamp_id.json",
    "object_key": "mongodb/db_collection/timestamp_id.json",
    "timestamp": "2024-01-01T00:00:00.000000",
    "metadata": {
        // Source-specific metadata
        "db": "...",
        "collection": "...",
        "document_id": "...",
        "operation": "insert"
    }
}
```

## Configuration

### Environment Variables

Create a `.env` file in the `Kafka Integration/` directory:

```env
# Kafka Configuration
KAFKA_BOOTSTRAP_SERVERS=localhost:9092

# MinIO Configuration
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_SECURE=false

# MinIO Bucket
BRONZE_BUCKET=syniqai-bronze
```

### Default Values

If no `.env` file is present, the following defaults are used:

- `KAFKA_BOOTSTRAP_SERVERS`: `localhost:9092`
- `MINIO_ENDPOINT`: `localhost:9000`
- `MINIO_ACCESS_KEY`: `minioadmin`
- `MINIO_SECRET_KEY`: `minioadmin`
- `MINIO_SECURE`: `false`
- `BRONZE_BUCKET`: `syniqai-bronze`

## Usage

### Prerequisites

1. **Kafka** must be running on `localhost:9092` (or configured endpoint)
2. **MinIO** must be running with the `syniqai-bronze` bucket created
3. Python dependencies installed: `pip install -r requirements.txt`

### Start the Emitter

#### Windows
```batch
cd "Kafka Integration"
start_bronze_emitter.bat
```

#### Linux/Mac
```bash
cd "Kafka Integration"
python bronze_ready_emitter.py
```

### Run as Background Service

#### Windows
```batch
start "Bronze Emitter" /B python bronze_ready_emitter.py >> logs\bronze_emitter.log 2>&1
```

#### Linux/Mac (using nohup)
```bash
nohup python bronze_ready_emitter.py >> logs/bronze_emitter.log 2>&1 &
```

#### Linux/Mac (using screen)
```bash
screen -dmS bronze-emitter python bronze_ready_emitter.py
# To attach: screen -r bronze-emitter
```

## Monitoring

### Real-time Logs

The emitter logs:
- ✓ Successfully routed messages (green checkmark)
- ⏸ Media files routed to pending (pause symbol)
- ⚠ Warnings for unknown file types
- ❌ Errors during processing

Example log output:
```
2024-01-01 10:00:00 - BronzeReadyEmitter - INFO - ✓ Routed to bronze-ready: pdf | s3/mybucket/documents/report.pdf
2024-01-01 10:00:01 - BronzeReadyEmitter - INFO - ⏸ Routed to bronze-media-pending: video | mongodb/media_videos/1234_abc.mp4
2024-01-01 10:00:05 - BronzeReadyEmitter - INFO - Stats: Processed=100, Ready=87, Pending=13, Errors=0
```

### Statistics

The service tracks:
- **Processed**: Total messages processed
- **Ready**: Messages routed to `bronze-ready`
- **Media Pending**: Messages routed to `bronze-media-pending`
- **Errors**: Failed processing attempts

Statistics are logged every 100 messages and at shutdown.

### Health Checks

#### Check Kafka Consumer Group Status
```bash
# Windows
cd C:\kafka\kafka-4.2.0
bin\windows\kafka-consumer-groups.bat --bootstrap-server localhost:9092 --describe --group bronze-ready-emitter

# Linux/Mac
kafka-consumer-groups.sh --bootstrap-server localhost:9092 --describe --group bronze-ready-emitter
```

#### Check Topic Message Counts
```bash
# bronze-ready topic
bin\windows\kafka-run-class.bat kafka.tools.GetOffsetShell --broker-list localhost:9092 --topic bronze-ready

# bronze-media-pending topic
bin\windows\kafka-run-class.bat kafka.tools.GetOffsetShell --broker-list localhost:9092 --topic bronze-media-pending
```

## Integration with Existing Components

### Upstream (Producers)
1. **custom_connectors.py** - MongoDB & S3 CDC connectors publish to `bronze-mongodb` and `bronze-s3`
2. **mongodb_stream_ingestor.py** - Streams MongoDB documents to MinIO `syniqai-bronze/mongodb/`
3. **s3_file_ingestor.py** - Streams S3 files to MinIO `syniqai-bronze/s3/`

### Downstream (Consumers)
1. **AI Processing Service** - Listens to `bronze-ready` and auto-processes files
2. **User Trigger Service** - Allows manual triggering of files in `bronze-media-pending`

## MinIO Path Conventions

The emitter expects files to be stored in MinIO following these conventions:

### MongoDB Files
```
syniqai-bronze/
└── mongodb/
    └── {database}_{collection}/
        ├── {timestamp}_{document_id}.json
        └── {timestamp}_{document_id}.parquet
```

Example: `syniqai-bronze/mongodb/mydb_users/1640000000000_abc123.json`

### S3 Files
```
syniqai-bronze/
└── s3/
    └── {source_bucket}/
        └── {original_key}
```

Example: `syniqai-bronze/s3/my-s3-bucket/documents/report.pdf`

## Troubleshooting

### Emitter Not Consuming Messages
1. Check Kafka is running: `Test-NetConnection localhost -Port 9092`
2. Verify topics exist: `kafka-topics.bat --list --bootstrap-server localhost:9092`
3. Check consumer group lag: `kafka-consumer-groups.bat --describe --group bronze-ready-emitter`

### Messages Not Being Routed
1. Check message structure matches expected format
2. Verify file type detection logic in logs
3. Ensure MinIO bucket exists and is accessible

### High Error Rate
1. Check Kafka connectivity
2. Verify message format from upstream producers
3. Review error logs for specific issues

### Performance Issues
1. Increase `max_poll_records` in consumer configuration
2. Add more emitter instances (Kafka will auto-balance)
3. Check Kafka broker performance

## Advanced Configuration

### Multiple Emitter Instances

For high throughput, run multiple instances. Kafka automatically balances partitions:

```batch
REM Terminal 1
start "Bronze Emitter 1" python bronze_ready_emitter.py

REM Terminal 2
start "Bronze Emitter 2" python bronze_ready_emitter.py
```

### Custom File Type Mappings

Edit `FILE_TYPE_EXTENSIONS` in `bronze_ready_emitter.py`:

```python
FILE_TYPE_EXTENSIONS = {
    'pdf': ['.pdf'],
    'txt': ['.txt', '.log', '.md'],
    # Add custom mappings
    'archive': ['.zip', '.tar', '.gz'],
    'code': ['.py', '.js', '.java'],
}
```

### Environment-Specific Configs

#### Development
```env
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
MINIO_ENDPOINT=localhost:9000
```

#### Production
```env
KAFKA_BOOTSTRAP_SERVERS=kafka1.prod:9092,kafka2.prod:9092,kafka3.prod:9092
MINIO_ENDPOINT=minio.prod.company.com:9000
MINIO_SECURE=true
```

## Dependencies

- **kafka-python** (`>=2.0.2`) - Kafka client
- **minio** - MinIO client (already in requirements.txt)
- **python-dotenv** - Environment variable loading

All dependencies are included in `requirements.txt`.

## License

Part of the SyniqAI project.
