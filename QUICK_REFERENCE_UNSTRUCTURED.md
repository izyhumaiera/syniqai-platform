# Quick Reference - Unstructured Data Integration

## 🚀 Essential Code Snippets

### MongoDB Connection

```python
from pymongo import MongoClient

# Atlas Connection
mongo_uri = "mongodb+srv://user:pass@cluster.mongodb.net/"
client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)

# On-Premise Connection
mongo_uri = "mongodb://user:pass@localhost:27017/?authSource=admin"
client = MongoClient(mongo_uri)

# Test connection
client.admin.command('ping')

# Access database and collection
db = client['media_db']
collection = db['images_metadata']

# Insert document
collection.insert_one({"filename": "image.jpg", "size": 1024})

# Query with filter
docs = collection.find({"size": {"$gt": 1000}})
```

### S3/AWS Connection

```python
import boto3
from botocore.exceptions import ClientError

# Create S3 client
s3_client = boto3.client(
    's3',
    aws_access_key_id='YOUR_ACCESS_KEY',
    aws_secret_access_key='YOUR_SECRET_KEY',
    region_name='us-east-1'
)

# List objects
response = s3_client.list_objects_v2(
    Bucket='your-bucket',
    Prefix='path/to/files/'
)

# Download file
s3_client.download_file(
    'your-bucket',
    'path/to/file.jpg',
    'local_file.jpg'
)

# Upload file
s3_client.upload_file(
    'local_file.jpg',
    'your-bucket',
    'path/to/file.jpg'
)

# Get object data
obj = s3_client.get_object(Bucket='bucket', Key='file.jpg')
file_data = obj['Body'].read()
```

### MinIO Connection

```python
from minio import Minio
from minio.error import S3Error
import io

# Create MinIO client
client = Minio(
    'localhost:9000',
    access_key='admin',
    secret_key='password123',
    secure=False
)

# Check if bucket exists
if not client.bucket_exists('bronze'):
    client.make_bucket('bronze')

# Upload file from bytes
file_data = b'binary data here'
client.put_object(
    bucket_name='bronze',
    object_name='path/to/file.jpg',
    data=io.BytesIO(file_data),
    length=len(file_data),
    content_type='image/jpeg'
)

# Download file
response = client.get_object('bronze', 'path/to/file.jpg')
data = response.read()
response.close()
response.release_conn()

# List objects
objects = client.list_objects('bronze', prefix='path/', recursive=True)
for obj in objects:
    print(f"{obj.object_name} - {obj.size} bytes")
```

### Kafka Producer

```python
from kafka import KafkaProducer
import json

# Create producer
producer = KafkaProducer(
    bootstrap_servers='localhost:9092',
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

# Send message
producer.send(
    'bronze-mongodb',
    value={'filename': 'image.jpg', 'size': 1024}
)

producer.flush()
producer.close()
```

---

## 📋 Common Configuration Patterns

### Environment Variables (.env)

```env
# MongoDB
MONGO_URI=mongodb+srv://user:pass@cluster.mongodb.net/
MONGO_DB=media_db
MONGO_HOST=localhost
MONGO_PORT=27017
MONGO_USER=admin
MONGO_PASS=password123

# AWS S3
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=us-east-1
S3_BUCKET=your-bucket-name

# MinIO
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=admin
MINIO_SECRET_KEY=password123

# Kafka
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_CONNECT_HOST=localhost
KAFKA_CONNECT_PORT=8083
```

### Config JSON Files

**mongodb_config.json:**
```json
{
  "source": "mongodb_prod",
  "connection": {
    "uri": "mongodb+srv://user:pass@cluster.mongodb.net/",
    "database": "media_db",
    "collection": "images_metadata"
  },
  "extraction": {
    "query": {},
    "chunk_size": 10000
  }
}
```

**s3_config.json:**
```json
{
  "source": "s3_prod",
  "aws_access_key_id": "YOUR_KEY",
  "aws_secret_access_key": "YOUR_SECRET",
  "region": "us-east-1",
  "bucket": "your-bucket",
  "prefix": "unstructured/",
  "file_extensions": [".jpg", ".png", ".mp4"]
}
```

---

## 🛠️ Command Line Usage

### MongoDB Operations

```powershell
# Test MongoDB connection
cd "data ingestion\Connector\SYNIQ-MONGODB"
python test_connection.py

# Upload images to MongoDB
python upload_images.py

# Upload text files
python upload_txt.py

# Upload videos
python upload_video.py

# Export images from MongoDB
python outputs_image.py

# Launch GUI
python gui.py
```

### Streaming Ingestion

```powershell
# Stream MongoDB to MinIO
cd "data ingestion\Connector"
python mongodb_stream_ingestor.py mongodb_config.json --mode streaming

# Stream S3 to MinIO
python s3_file_ingestor.py s3_config.json --mode streaming

# Hybrid mode (save local backup + MinIO)
python mongodb_stream_ingestor.py mongodb_config.json --mode hybrid
```

### Kafka Operations

```powershell
# Start Kafka CDC for MongoDB
cd "Kafka Integration"
python -c "from custom_connectors import mongodb_runner; mongodb_runner('.env.mongodb')"

# Check Kafka topics
curl http://localhost:8000/api/kafka/topics

# Sample messages from topic
curl "http://localhost:8000/api/kafka/topics/bronze-mongodb/sample?max_messages=10"

# Check CDC messages
curl http://localhost:8000/api/kafka/cdc/messages?topic=cdc.mongodb.media_db.images_metadata

# Kafka health check
curl http://localhost:8000/api/kafka/health
```

### MinIO Operations

```powershell
# Setup MinIO domain structure
cd gui
python setup_minio_domains.py

# Check MinIO buckets (via Python)
python check_minio.py
```

---

## 🔑 Key File Locations

### Configuration Files
```
Kafka Integration/.env                         # Kafka config
Kafka Integration/.env.mongodb                 # MongoDB CDC config
data lakehouse/syniq_project/config/minio_config.yaml  # MinIO config
data ingestion/Connector/SYNIQ-MONGODB/on_prem.env    # MongoDB credentials
data ingestion/Connector/mongodb_config.json   # MongoDB ingestion config
data ingestion/Connector/s3_config.json        # S3 ingestion config
```

### Ingestion Scripts
```
data ingestion/Connector/
├── mongodb_stream_ingestor.py    # MongoDB → MinIO streaming
├── s3_file_ingestor.py            # S3 → MinIO streaming
└── SYNIQ-MONGODB/
    ├── upload_images.py           # Upload images to MongoDB
    ├── upload_txt.py              # Upload text to MongoDB
    ├── upload_video.py            # Upload videos to MongoDB
    ├── outputs_image.py           # Export images from MongoDB
    ├── outputs_txt.py             # Export text from MongoDB
    └── outputs_video.py           # Export videos from MongoDB
```

### API & Services
```
gui/api/
├── backend.py                     # Main FastAPI app
├── ingestion_service.py           # Connection testing & ingestion
├── storage.py                     # MinIO client wrapper
└── mongodb_routes.py              # MongoDB API endpoints

Kafka Integration/
├── kafka_bridge.py                # Kafka publisher
├── kafka_routes.py                # Kafka REST API
├── kafka_service.py               # Kafka management
└── custom_connectors.py           # MongoDB & S3 CDC connectors
```

---

## 🌐 API Endpoints

### Base URL: `http://localhost:8000`

### Ingestion Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/ingestion/test-connection` | POST | Test MongoDB/S3 connection |
| `/api/ingestion/start` | POST | Start ingestion job |
| `/api/ingestion/jobs` | GET | List all jobs |
| `/api/ingestion/jobs/{id}` | GET | Get job status |

**Example: Test MongoDB Connection**
```bash
curl -X POST http://localhost:8000/api/ingestion/test-connection \
  -H "Content-Type: application/json" \
  -d '{
    "source_type": "mongodb",
    "config": {
      "mongo_uri": "mongodb://localhost:27017",
      "database": "media_db"
    }
  }'
```

**Example: Start MongoDB Ingestion**
```bash
curl -X POST http://localhost:8000/api/ingestion/start \
  -H "Content-Type: application/json" \
  -d '{
    "source_type": "mongodb",
    "connection_config": {
      "mongo_uri": "mongodb://localhost:27017",
      "database": "media_db"
    },
    "extraction_request": {
      "collections": ["images_metadata", "videos_metadata"]
    },
    "domain": "general"
  }'
```

### Kafka Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/kafka/status` | GET | Kafka dashboard |
| `/api/kafka/health` | GET | Broker health |
| `/api/kafka/topics` | GET | List topics |
| `/api/kafka/topics/{name}/sample` | GET | Sample messages |
| `/api/kafka/cdc/topics` | GET | List CDC topics |
| `/api/kafka/cdc/messages` | GET | CDC messages |

**Example: List Kafka Topics**
```bash
curl http://localhost:8000/api/kafka/topics
```

**Example: Sample MongoDB CDC Messages**
```bash
curl "http://localhost:8000/api/kafka/cdc/messages?topic=cdc.mongodb.media_db.images_metadata&limit=5"
```

### Storage Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/storage/list` | GET | List MinIO objects |
| `/api/storage/upload` | POST | Upload to MinIO |
| `/api/storage/download/{path}` | GET | Download from MinIO |

---

## 📊 Data Types & Collections

### MongoDB Collections (SYNIQ-MONGODB)

| Collection | Purpose | Key Fields |
|------------|---------|------------|
| `images_metadata` | Image metadata | filename, size, path, upload_date |
| `images_blobs` | Image binary (GridFS) | content (Binary) |
| `txt_metadata` | Text file metadata | filename, size, content_preview |
| `txt_blobs` | Text file content | content (Binary) |
| `videos_metadata` | Video metadata | filename, size, duration, codec |
| `ingestion_state` | Ingestion progress | collection, last_id, timestamp |

### MinIO Bucket Structure

```
syniqai-bronze/        # Raw ingested data
├── general/
│   ├── mongodb/
│   │   ├── images/
│   │   ├── videos/
│   │   └── text/
│   └── s3/
│       ├── images/
│       └── documents/
├── finance/
└── healthcare/

syniqai-silver/        # Processed data
syniqai-gold/          # Analytics-ready data
```

### Supported File Types

| Category | Extensions | Handler |
|----------|-----------|---------|
| Images | .jpg, .jpeg, .png, .gif, .bmp | SYNIQ-MONGODB, S3 ingestor |
| Videos | .mp4, .avi, .mov, .mkv | SYNIQ-MONGODB, S3 ingestor |
| Documents | .pdf, .doc, .docx | S3 ingestor |
| Text | .txt, .log | SYNIQ-MONGODB, S3 ingestor |
| Structured | .csv, .json, .parquet | S3 ingestor |

---

## ⚡ Performance Tuning

### MongoDB Batch Upload

```python
# In SYNIQ-MONGODB scripts
BATCH_SIZE = 1000  # Files per MongoDB bulk write

# Higher = fewer network calls, more memory
# Lower = more network calls, less memory
# Recommended: 500-2000
```

### Kafka Message Size

```env
# In Kafka Integration/.env
KAFKA_MAX_ROWS_PER_MSG=500

# Adjust based on:
# - Average row size
# - Network bandwidth
# - Kafka broker limits (default 1MB)
```

### MongoDB Chunk Size

```python
# In mongodb_stream_ingestor.py
chunk_size=10000  # Documents per chunk

# Recommended: 5000-20000
```

### S3 Pagination

```python
# In s3_file_ingestor.py
# Uses boto3 paginator (auto-handles 1000 object limit)
MaxKeys=1000  # Default pagination size
```

---

## 🐛 Troubleshooting

### MongoDB Connection Issues

```python
# Test connection
from pymongo import MongoClient

try:
    client = MongoClient(
        "mongodb://localhost:27017",
        serverSelectionTimeoutMS=5000
    )
    client.admin.command('ping')
    print("✓ Connected")
except Exception as e:
    print(f"✗ Failed: {e}")
```

**Common Issues:**
- Firewall blocking port 27017
- Incorrect credentials
- MongoDB not running
- Network/DNS issues (Atlas)

### S3 Connection Issues

```python
import boto3
from botocore.exceptions import ClientError

try:
    s3 = boto3.client('s3', region_name='us-east-1')
    s3.head_bucket(Bucket='your-bucket')
    print("✓ Connected")
except ClientError as e:
    print(f"✗ Error: {e}")
```

**Common Issues:**
- Invalid credentials
- Incorrect region
- Bucket doesn't exist
- Permissions (IAM policies)

### MinIO Connection Issues

```python
from minio import Minio

try:
    client = Minio(
        'localhost:9000',
        access_key='admin',
        secret_key='password123',
        secure=False
    )
    buckets = client.list_buckets()
    print(f"✓ Connected. Buckets: {[b.name for b in buckets]}")
except Exception as e:
    print(f"✗ Failed: {e}")
```

**Common Issues:**
- MinIO server not running
- Wrong endpoint (check localhost vs 127.0.0.1)
- Port already in use (9000, 9001)
- Incorrect credentials

### Kafka Connection Issues

```bash
# Check if Kafka is running
curl http://localhost:9092

# Check Kafka Connect
curl http://localhost:8083

# Test with Python
from kafka import KafkaProducer

try:
    producer = KafkaProducer(bootstrap_servers='localhost:9092')
    print("✓ Kafka connected")
    producer.close()
except Exception as e:
    print(f"✗ Failed: {e}")
```

**Common Issues:**
- Kafka broker not running
- Wrong port (9092 for broker, 8083 for Connect)
- Firewall blocking ports
- Topic doesn't exist (auto-create disabled)

---

## 📦 Required Dependencies

### Python Packages

```bash
# MongoDB
pip install pymongo

# AWS S3
pip install boto3

# MinIO
pip install minio

# Kafka
pip install kafka-python

# Data processing
pip install pandas pyarrow

# GUI
pip install fastapi uvicorn

# Utilities
pip install python-dotenv pyyaml
```

### Full Requirements

See:
- `Kafka Integration/requirements.txt`
- `gui/requirements.txt`
- `data ingestion/Connector/SYNIQ-MONGODB/requirements.txt`

---

## 🎯 Use Case Examples

### Use Case 1: Archive Images from MongoDB to MinIO

```python
from mongodb_stream_ingestor import MongoDBStreamIngestor, load_minio_config

minio = load_minio_config()
ingestor = MongoDBStreamIngestor(minio, save_local_backup=False)

result = ingestor.ingest_streaming(
    mongo_uri="mongodb://localhost:27017",
    database="media_db",
    collection="images_metadata",
    source="mongodb_local",
    chunk_size=5000
)

print(f"Ingested {result['total_rows']} images")
```

### Use Case 2: Sync S3 Bucket to MinIO

```python
from s3_file_ingestor import S3FileIngestor, load_minio_config

minio = load_minio_config()
ingestor = S3FileIngestor(minio)

result = ingestor.ingest_streaming(
    s3_bucket="my-files",
    aws_access_key="...",
    aws_secret_key="...",
    aws_region="us-east-1",
    prefix="images/2024/",
    file_extensions=[".jpg", ".png"],
    source="s3_images"
)

print(f"Synced {result['total_files']} files")
```

### Use Case 3: Real-time CDC from MongoDB

```bash
# Start MongoDB CDC connector
cd "Kafka Integration"
python -c "from custom_connectors import mongodb_runner; mongodb_runner('.env.mongodb')"

# Monitor CDC messages
curl http://localhost:8000/api/kafka/cdc/messages?topic=cdc.mongodb.media_db.images_metadata
```

---

## 📖 Further Reading

- [MongoDB Python Driver Docs](https://pymongo.readthedocs.io/)
- [Boto3 S3 Documentation](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3.html)
- [MinIO Python SDK](https://min.io/docs/minio/linux/developers/python/API.html)
- [Kafka Python Client](https://kafka-python.readthedocs.io/)
- Project Documentation:
  - `UNSTRUCTURED_DATA_OVERVIEW.md` (detailed overview)
  - `Kafka Integration/README.md` (Kafka integration)
  - `Kafka Integration/SETUP_GUIDE.md` (setup instructions)
