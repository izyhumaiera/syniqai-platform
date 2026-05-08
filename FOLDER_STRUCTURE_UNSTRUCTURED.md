# Complete Folder Structure - Unstructured Data Components

## 📂 Workspace Root: `Syniq/`

```
Syniq/
│
├── 📄 UNSTRUCTURED_DATA_OVERVIEW.md        ← Comprehensive guide (JUST CREATED)
├── 📄 QUICK_REFERENCE_UNSTRUCTURED.md      ← Quick reference (JUST CREATED)
│
├── 📁 data ingestion/
│   ├── 📄 __init__.py
│   └── 📁 Connector/
│       ├── 📄 __init__.py
│       │
│       ├── 📄 mongodb_stream_ingestor.py   ← MongoDB → MinIO streaming
│       ├── 📄 s3_file_ingestor.py          ← S3 → MinIO streaming
│       ├── 📄 mongodb_config.json          ← MongoDB config template
│       ├── 📄 s3_config.json               ← S3 config template
│       │
│       ├── 📁 SYNIQ-MONGODB/               ← MongoDB Unstructured Media Pipeline
│       │   ├── 📄 .env.template            ← Environment template
│       │   ├── 📄 on_prem.env              ← Your MongoDB credentials
│       │   ├── 📄 requirements.txt
│       │   │
│       │   ├── 📄 upload_images.py         ← Upload images to MongoDB
│       │   ├── 📄 upload_txt.py            ← Upload text files to MongoDB
│       │   ├── 📄 upload_video.py          ← Upload videos to MongoDB
│       │   │
│       │   ├── 📄 outputs_image.py         ← Export images from MongoDB
│       │   ├── 📄 outputs_txt.py           ← Export text from MongoDB
│       │   ├── 📄 outputs_video.py         ← Export videos from MongoDB
│       │   │
│       │   ├── 📄 gui.py                   ← Interactive GUI for operations
│       │   └── 📄 test_connection.py       ← Test MongoDB connection
│       │
│       └── 📁 SYNIQ_AWS/
│           └── 📄 SYNIQ_TSD.md             ← Technical specification
│
├── 📁 Kafka Integration/                   ← Kafka & CDC Integration
│   ├── 📄 README.md                        ← Overview
│   ├── 📄 SETUP_GUIDE.md                   ← Setup instructions
│   ├── 📄 QUICK_START.md                   ← Quick start guide
│   ├── 📄 MONGODB_CDC_README.md            ← MongoDB CDC guide
│   │
│   ├── 📄 .env                             ← Kafka configuration
│   ├── 📄 .env.mongodb                     ← MongoDB CDC config
│   ├── 📄 requirements.txt
│   │
│   ├── 📄 kafka_bridge.py                  ← Kafka publisher (singleton)
│   ├── 📄 kafka_service.py                 ← Kafka management service
│   ├── 📄 kafka_routes.py                  ← FastAPI Kafka endpoints
│   │
│   ├── 📄 custom_connectors.py             ← MongoDB & S3 CDC connectors
│   ├── 📄 debezium_manager.py              ← Debezium connector manager
│   │
│   ├── 📄 check_minio_bucket.py            ← MinIO bucket checker
│   └── 📄 monitor_cdc_events.py            ← CDC event monitor
│
├── 📁 gui/                                 ← Web GUI & Backend API
│   ├── 📄 app.py                           ← Main GUI application
│   ├── 📄 requirements.txt
│   │
│   ├── 📄 check_minio.py                   ← MinIO health check
│   ├── 📄 setup_minio_domains.py           ← Setup MinIO structure
│   ├── 📄 upload_sample_data.py            ← Upload sample data
│   │
│   └── 📁 api/                             ← FastAPI Backend
│       ├── 📄 backend.py                   ← Main FastAPI app
│       ├── 📄 ingestion_service.py         ← Ingestion & connections
│       ├── 📄 storage.py                   ← MinIO client wrapper
│       ├── 📄 mongodb_routes.py            ← MongoDB API routes
│       └── 📄 kafka_startup_service.py     ← Kafka lifecycle manager
│
├── 📁 data lakehouse/
│   └── 📁 syniq_project/
│       ├── 📁 config/
│       │   └── 📄 minio_config.yaml        ← MinIO configuration
│       │
│       ├── 📁 ingestion/
│       │   ├── 📄 spark_unstructured_processor.py  ← Spark unstructured processing
│       │   └── 📄 upload_to_lakehouse.py          ← Bronze → MinIO bridge
│       │
│       └── 📁 syniq_project/
│           ├── 📁 catalog/                 ← Data catalog
│           │   └── 📄 catalog_manager.py
│           ├── 📁 quality/                 ← Data quality
│           │   └── 📄 profiler.py
│           └── 📁 lineage/                 ← Data lineage
│               └── 📄 lineage_tracker.py
│
└── 📁 airflow/
    └── 📁 airflow_dags/
        ├── 📄 mongodb_cdc_dag.py           ← MongoDB CDC Airflow DAG
        └── 📄 airflow_s3_dag.py            ← S3 ingestion Airflow DAG
```

---

## 📊 Component Relationships

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           DATA SOURCES                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────┐         ┌────────────────────────────┐        │
│  │   MongoDB Atlas/On-Prem  │         │      AWS S3 Buckets        │        │
│  │   ═══════════════════     │         │      ═══════════════        │        │
│  │   • images_metadata      │         │      • Images              │        │
│  │   • images_blobs (GridFS)│         │      • Videos              │        │
│  │   • txt_metadata         │         │      • Documents           │        │
│  │   • txt_blobs            │         │      • CSV/JSON/Parquet    │        │
│  │   • videos_metadata      │         │      • Text files          │        │
│  └────────────┬─────────────┘         └──────────┬─────────────────┘        │
│               │                                   │                          │
└───────────────┼───────────────────────────────────┼──────────────────────────┘
                │                                   │
                │                                   │
┌───────────────┼───────────────────────────────────┼──────────────────────────┐
│               ▼                                   ▼                          │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                  INGESTION LAYER                                       │ │
│  ├────────────────────────────────────────────────────────────────────────┤ │
│  │                                                                        │ │
│  │  ┌──────────────────────────────┐  ┌───────────────────────────────┐ │ │
│  │  │  SYNIQ-MONGODB Scripts       │  │  S3 File Ingestor             │ │ │
│  │  │  ════════════════════         │  │  ═════════════════             │ │ │
│  │  │  • upload_images.py          │  │  • s3_file_ingestor.py        │ │ │
│  │  │  • upload_txt.py             │  │  • File type detection        │ │ │
│  │  │  • upload_video.py           │  │  • Metadata extraction        │ │ │
│  │  │  • outputs_*.py              │  │  • boto3 S3 client            │ │ │
│  │  │  • gui.py                    │  │                               │ │ │
│  │  └──────────────┬───────────────┘  └───────────┬───────────────────┘ │ │
│  │                 │                               │                     │ │
│  │  ┌──────────────┴───────────────────────────────┴───────────────────┐ │ │
│  │  │            MongoDB Stream Ingestor                               │ │ │
│  │  │            ═══════════════════════                               │ │ │
│  │  │            • mongodb_stream_ingestor.py                          │ │ │
│  │  │            • Direct MongoDB → MinIO streaming                    │ │ │
│  │  │            • Flatten/preserve nested docs                        │ │ │
│  │  │            • Catalog & quality tracking                          │ │ │
│  │  └──────────────────────────────────────────────────────────────────┘ │ │
│  │                                                                        │ │
│  └────────────────────────────────┬───────────────────────────────────────┘ │
└───────────────────────────────────┼─────────────────────────────────────────┘
                                    │
                     ┌──────────────┴────────────────┐
                     │                               │
                     ▼                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         KAFKA LAYER (Optional)                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │  Kafka Integration/                                                   │ │
│  │  ══════════════════                                                    │ │
│  │                                                                        │ │
│  │  • kafka_bridge.py          ← Publishes to Kafka topics               │ │
│  │  • custom_connectors.py     ← MongoDB & S3 CDC connectors             │ │
│  │  • kafka_service.py         ← Topic & connector management            │ │
│  │  • kafka_routes.py          ← REST API endpoints                      │ │
│  │                                                                        │ │
│  │  Topics:                                                               │ │
│  │  • bronze-mongodb           ← MongoDB data                            │ │
│  │  • bronze-s3                ← S3 files                                │ │
│  │  • cdc.mongodb.*            ← MongoDB change streams                  │ │
│  │  • dlq-errors               ← Failed messages                         │ │
│  │                                                                        │ │
│  └────────────────────────────────┬───────────────────────────────────────┘ │
└───────────────────────────────────┼─────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         MinIO STORAGE                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Configuration: data lakehouse/syniq_project/config/minio_config.yaml       │
│  Client Wrapper: gui/api/storage.py                                         │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │  syniqai-bronze/                     ← Raw ingested data              │ │
│  │  ├── general/                                                          │ │
│  │  │   ├── mongodb/                                                      │ │
│  │  │   │   ├── images/                 ← Images from MongoDB            │ │
│  │  │   │   ├── videos/                 ← Videos from MongoDB            │ │
│  │  │   │   └── text/                   ← Text files from MongoDB        │ │
│  │  │   └── s3/                                                           │ │
│  │  │       ├── images/                 ← Images from S3                 │ │
│  │  │       ├── videos/                 ← Videos from S3                 │ │
│  │  │       └── documents/              ← Documents from S3              │ │
│  │  ├── finance/                        ← Finance domain                 │ │
│  │  └── healthcare/                     ← Healthcare domain              │ │
│  │                                                                         │ │
│  │  syniqai-silver/                     ← Processed/cleansed data        │ │
│  │  syniqai-gold/                       ← Analytics-ready data           │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  Metadata Store:                                                             │
│  • _metadata/catalog/          ← Data catalog                               │
│  • _metadata/quality/          ← Quality profiles                           │
│  • _metadata/lineage/          ← Lineage tracking                           │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         GUI & API                                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  gui/api/backend.py                      ← FastAPI application              │
│  ├── /api/ingestion/*                    ← Ingestion endpoints             │
│  ├── /api/kafka/*                        ← Kafka management                │
│  ├── /api/storage/*                      ← MinIO operations                │
│  └── /api/mongodb/*                      ← MongoDB operations              │
│                                                                              │
│  Services:                                                                   │
│  • ingestion_service.py                  ← Connection testing & ingestion   │
│  • storage.py                            ← MinIO client wrapper             │
│  • kafka_startup_service.py              ← Kafka lifecycle                  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🔧 Key Configuration Files

### 1. MongoDB Configuration

```
data ingestion/Connector/SYNIQ-MONGODB/on_prem.env
├── MONGO_HOST
├── MONGO_PORT
├── MONGO_USER
├── MONGO_PASS
└── MONGO_DB

Kafka Integration/.env.mongodb
├── MONGODB_URI
├── MONGODB_DATABASE
├── MONGODB_COLLECTIONS
├── MONGODB_BATCH_SIZE
└── MONGODB_POLL_INTERVAL_MINUTES
```

### 2. S3 Configuration

```
data ingestion/Connector/s3_config.json
├── aws_access_key_id
├── aws_secret_access_key
├── region
├── bucket
└── prefix
```

### 3. MinIO Configuration

```
data lakehouse/syniq_project/config/minio_config.yaml
├── endpoint
├── access_key
├── secret_key
└── buckets
    ├── bronze
    ├── silver
    └── gold
```

### 4. Kafka Configuration

```
Kafka Integration/.env
├── KAFKA_BOOTSTRAP_SERVERS
├── KAFKA_CONNECT_HOST
├── KAFKA_CONNECT_PORT
├── KAFKA_DLQ_TOPIC
└── KAFKA_MAX_ROWS_PER_MSG
```

---

## 🚀 Execution Flow

### Scenario 1: Upload Images to MongoDB

```
1. User runs: upload_images.py
   └── Loads: on_prem.env
   └── Connects: MongoClient → MongoDB
   └── Reads: Local image folder
   └── Inserts: 
       ├── images_metadata collection (filename, size, path)
       └── images_blobs collection (binary data)
   └── Tracks: ingestion_state collection
```

### Scenario 2: Stream MongoDB to MinIO

```
1. User runs: mongodb_stream_ingestor.py
   └── Loads: mongodb_config.json
   └── Connects: MongoClient → MongoDB
   └── Queries: Collection with query filter
   └── Chunks: 10,000 documents per chunk
   └── Transforms: Parquet format
   └── Uploads: MinIO bronze bucket
   └── Records: Catalog, quality, lineage metadata
```

### Scenario 3: Stream S3 to MinIO

```
1. User runs: s3_file_ingestor.py
   └── Loads: s3_config.json
   └── Connects: boto3 → AWS S3
   └── Lists: Objects with prefix filter
   └── Downloads: Files in streaming mode
   └── Uploads: MinIO bronze bucket
   └── Extracts: File metadata (size, type, mime)
   └── Records: Catalog, quality, lineage metadata
```

### Scenario 4: Real-time CDC from MongoDB

```
1. User runs: custom_connectors.py (MongoDB mode)
   └── Loads: .env.mongodb
   └── Connects: 
       ├── MongoClient → MongoDB
       └── KafkaProducer → Kafka broker
   └── Watches: Change streams OR polls collection
   └── Publishes: Changes to bronze-mongodb topic
   └── Handles: INSERT/UPDATE/DELETE operations
```

### Scenario 5: GUI-triggered Ingestion

```
1. User opens: http://localhost:8000
2. User clicks: "Test Connection" (MongoDB)
   └── POST /api/ingestion/test-connection
   └── ingestion_service.py executes test
   └── Returns: Connection status + collections
3. User clicks: "Start Ingestion"
   └── POST /api/ingestion/start
   └── ingestion_service.py creates job
   └── Spawns: Background thread for ingestion
   └── Returns: job_id
4. User monitors: GET /api/ingestion/jobs/{job_id}
   └── Returns: Status, progress, errors
```

---

## 📦 Dependencies by Component

### SYNIQ-MONGODB
```
pymongo             # MongoDB driver
bson                # BSON encoding
tkinter             # GUI (built-in)
python-dotenv       # Environment variables
```

### Streaming Ingestors
```
pymongo             # MongoDB
boto3               # AWS S3
minio               # MinIO client
pandas              # Data manipulation
pyarrow             # Parquet format
pyyaml              # Config parsing
```

### Kafka Integration
```
kafka-python        # Kafka producer/consumer
pymongo             # MongoDB connector
boto3               # S3 connector
requests            # REST API calls
python-dotenv       # Environment variables
```

### GUI/API
```
fastapi             # Web framework
uvicorn             # ASGI server
minio               # MinIO client
kafka-python        # Kafka integration
pymongo             # MongoDB support
boto3               # S3 support
```

---

## 🎯 Entry Points

### Python Scripts (Direct Execution)

```
data ingestion/Connector/SYNIQ-MONGODB/
├── upload_images.py        ← Upload images to MongoDB
├── upload_txt.py           ← Upload text files to MongoDB
├── upload_video.py         ← Upload videos to MongoDB
├── outputs_image.py        ← Export images from MongoDB
├── outputs_txt.py          ← Export text from MongoDB
├── outputs_video.py        ← Export videos from MongoDB
├── gui.py                  ← Launch GUI
└── test_connection.py      ← Test MongoDB connection

data ingestion/Connector/
├── mongodb_stream_ingestor.py  ← MongoDB → MinIO
└── s3_file_ingestor.py         ← S3 → MinIO

Kafka Integration/
└── custom_connectors.py        ← MongoDB/S3 CDC

gui/
├── app.py                      ← Launch GUI
└── setup_minio_domains.py      ← Setup MinIO structure
```

### API Endpoints (HTTP)

```
http://localhost:8000/api/ingestion/test-connection
http://localhost:8000/api/ingestion/start
http://localhost:8000/api/kafka/status
http://localhost:8000/api/kafka/topics
http://localhost:8000/api/storage/list
```

### Airflow DAGs (Scheduled)

```
airflow/airflow_dags/
├── mongodb_cdc_dag.py          ← MongoDB CDC (scheduled)
└── airflow_s3_dag.py           ← S3 ingestion (scheduled)
```

---

## ✅ Ready to Use

All the files you need are already in place! Here's what to do next:

1. **Review Configuration**
   - Check `UNSTRUCTURED_DATA_OVERVIEW.md` for detailed information
   - Read `QUICK_REFERENCE_UNSTRUCTURED.md` for quick snippets

2. **Configure Connections**
   - Update MongoDB credentials in `data ingestion/Connector/SYNIQ-MONGODB/on_prem.env`
   - Update S3 credentials in `data ingestion/Connector/s3_config.json`
   - Verify MinIO is running: `http://localhost:9000`

3. **Test Connections**
   - MongoDB: Run `SYNIQ-MONGODB/test_connection.py`
   - S3: Use GUI API test endpoint
   - MinIO: Run `gui/check_minio.py`

4. **Start Ingesting**
   - Choose your data source (MongoDB or S3)
   - Run appropriate ingestor script
   - Monitor progress in logs and MinIO buckets

5. **Optional: Enable Kafka**
   - Start Kafka broker
   - Configure CDC connectors
   - Monitor topics via API
