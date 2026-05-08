# SyniqAI Requirements Summary

This document provides a complete overview of all Python dependencies across the SyniqAI platform.

## Requirements Files Locations

### 1. Backend API - `gui/api/requirements.txt`
**Purpose**: Main FastAPI backend server with all route handlers  
**Port**: 8000  
**Key Dependencies**:
- fastapi
- uvicorn
- pydantic
- psycopg2-binary
- python-dotenv
- minio
- kafka-python
- pyspark
- duckdb
- pyiceberg
- requests

### 2. Backend API (Alternative) - `gui/api/requirements_backend.txt`
**Purpose**: Alternative backend dependencies (if requirements.txt fails)  
**Key Dependencies**: Same as above

### 3. AI Processing - `ai processing/requirements.txt`
**Purpose**: AI worker that processes unstructured files using OpenRouter  
**Key Dependencies**:
- minio
- psycopg2-binary
- python-dotenv
- requests
- pillow (image processing)
- pdfplumber (PDF processing)
- python-docx (DOCX processing)
- ffmpeg-python (video/audio processing)

### 4. Kafka Integration - `Kafka Integration/requirements.txt`
**Purpose**: Main Kafka services (Bronze Ready Emitter, monitoring)  
**Key Dependencies**:
- kafka-python
- minio
- psycopg2-binary
- python-dotenv
- pymongo (for MongoDB CDC)
- boto3 (for S3 CDC)

### 5. Kafka CDC - `Kafka Integration/requirements-cdc.txt`
**Purpose**: CDC Consumer (writes to Iceberg tables)  
**Key Dependencies**:
- kafka-python
- pyiceberg
- psycopg2-binary
- pyspark
- python-dotenv

### 6. Kafka AI Processor - `Kafka Integration/requirements-ai-processor.txt`
**Purpose**: AI processor dependencies for Kafka integration  
**Key Dependencies**: Related to AI processing

### 7. Data Lakehouse - `data lakehouse/syniq_project/requirements.txt`
**Purpose**: Spark transformations for Gold layer  
**Key Dependencies**:
- pyspark
- pyiceberg
- delta-spark
- psycopg2-binary
- python-dotenv
- pandas
- numpy
- matplotlib
- seaborn

### 8. S3 Connector - `data ingestion/Connector/SYNIQ_AWS/requirements.txt`
**Purpose**: Extracts files from AWS S3  
**Key Dependencies**:
- boto3
- minio
- kafka-python
- python-dotenv

### 9. MongoDB Connector - `data ingestion/Connector/SYNIQ-MONGODB/requirements.txt`
**Purpose**: Streams data from MongoDB GridFS  
**Key Dependencies**:
- pymongo
- minio
- kafka-python
- python-dotenv

## Installation Priority

Install in this order to resolve dependencies correctly:

```bash
# 1. Backend API (install first - most comprehensive)
pip install -r "gui/api/requirements.txt"

# 2. Data Lakehouse (Spark dependencies)
pip install -r "data lakehouse/syniq_project/requirements.txt"

# 3. Kafka Integration (core Kafka services)
pip install -r "Kafka Integration/requirements.txt"

# 4. CDC specific
pip install -r "Kafka Integration/requirements-cdc.txt"

# 5. AI Processing
pip install -r "ai processing/requirements.txt"

# 6. Data connectors
pip install -r "data ingestion/Connector/SYNIQ_AWS/requirements.txt"
pip install -r "data ingestion/Connector/SYNIQ-MONGODB/requirements.txt"
```

## Common Dependencies Across All Modules

These are used throughout the platform:
- **python-dotenv**: Environment variable management
- **psycopg2-binary**: PostgreSQL database connectivity
- **minio**: MinIO object storage client
- **kafka-python**: Kafka messaging
- **requests**: HTTP client for API calls

## System Requirements

### Software Prerequisites
- **Python**: 3.9 or higher
- **Java**: 17 (required for Spark 3.5+)
- **PostgreSQL**: 14 or higher
- **MinIO**: Latest version
- **Apache Kafka**: 3.0 or higher
- **Node.js**: 16+ (for frontend, if applicable)

### OS-Specific Notes
- **Windows**: Requires Java 17 installed (Eclipse Adoptium recommended)
- **Linux/Mac**: Set JAVA_HOME environment variable

## Virtual Environment Setup

Recommended approach - create separate virtual environments for each component:

```bash
# Backend API
cd gui/api
python -m venv venv_backend
venv_backend\Scripts\activate  # Windows
source venv_backend/bin/activate  # Linux/Mac
pip install -r requirements.txt

# AI Processing
cd "../../ai processing"
python -m venv venv_ai
venv_ai\Scripts\activate
pip install -r requirements.txt

# Kafka Integration
cd "../Kafka Integration"
python -m venv venv_kafka
venv_kafka\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-cdc.txt
```

## Troubleshooting

### Common Issues

1. **pyspark installation fails**:
   - Ensure Java 17 is installed and JAVA_HOME is set
   - Windows: Install from https://adoptium.net/temurin/releases/?version=17

2. **psycopg2-binary fails**:
   - On Windows: May need Microsoft C++ Build Tools
   - Alternative: Try `psycopg2` instead

3. **kafka-python connection issues**:
   - Ensure Kafka broker is running on localhost:9092
   - Check firewall settings

4. **minio connection fails**:
   - Verify MinIO is running on localhost:9000
   - Check credentials in .env file

5. **ffmpeg-python fails**:
   - Requires ffmpeg system binary installed
   - Windows: Download from https://ffmpeg.org/download.html
   - Add to PATH

## Dependency Conflicts

If you encounter version conflicts:

1. Create isolated virtual environments per component
2. Install backend dependencies first (most comprehensive)
3. Use `pip list` to check installed versions
4. Refer to individual requirements.txt for version constraints

## Testing Installation

After installing dependencies, test each component:

```bash
# Test imports
python -c "import fastapi, pyspark, kafka, minio, psycopg2; print('All imports successful')"

# Test backend
cd gui/api
python backend.py

# Test AI processor
cd "../../ai processing"
python ai_processor.py

# Test Kafka services
cd "../Kafka Integration"
python bronze_ready_emitter.py
```

## License & Credits

SyniqAI uses open-source dependencies. Refer to individual package licenses.

---

**Last Updated**: 2026-04-01
