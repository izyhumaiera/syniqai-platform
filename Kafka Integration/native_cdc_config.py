"""
Native Kafka CDC Configuration (NO DOCKER)
==========================================
Pure Python CDC connectors for PostgreSQL, MongoDB, AWS S3, and MariaDB
Uses native Kafka broker at localhost:9092 (KRaft mode)
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment
env_file = Path(__file__).parent / ".env"
load_dotenv(env_file)

# ============================================================================
# NATIVE KAFKA CONFIGURATION (NO DOCKER)
# ============================================================================

KAFKA_CONFIG = {
    "bootstrap_servers": ["localhost:9092"],
    "client_id": "syniq-native-cdc",
    "api_version": (2, 8, 1),  # Kafka 4.2.0 compatible
    "request_timeout_ms": 30000,
    "connections_max_idle_ms": 540000,
    "metadata_max_age_ms": 300000,
}

# Topics for each source
TOPICS = {
    "postgres": "bronze-postgres",
    "mariadb": "bronze-mariadb",
    "mongodb": "bronze-mongodb",
    "s3": "bronze-s3",
    "bronze_ready": "bronze-ready",
    "bronze_media": "bronze-media-pending"
}

# ============================================================================
# DATABASE CONNECTIONS (NO DOCKER)
# ============================================================================

# PostgreSQL
POSTGRES_CONFIG = {
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": int(os.getenv("POSTGRES_PORT", 5432)),
    "database": os.getenv("POSTGRES_DATABASE"),
    "user": os.getenv("POSTGRES_USER"),
    "password": os.getenv("POSTGRES_PASSWORD"),
}

# MariaDB
MARIADB_CONFIG = {
    "host": os.getenv("MARIADB_HOST", "localhost"),
    "port": int(os.getenv("MARIADB_PORT", 3306)),
    "database": os.getenv("MARIADB_DATABASE"),
    "user": os.getenv("MARIADB_USER"),
    "password": os.getenv("MARIADB_PASSWORD"),
}

# MongoDB Atlas (native connection)
MONGODB_CONFIG = {
    "uri": os.getenv("MONGODB_URI", "mongodb+srv://connector_user:ConnectorPass123@test.pw8zb01.mongodb.net/?appName=Test"),
    "database": os.getenv("MONGODB_DATABASE", "media_db"),
    "collections": os.getenv("MONGODB_COLLECTIONS", "images_metadata").split(","),
}

# AWS S3 (native boto3)
S3_CONFIG = {
    "bucket": os.getenv("S3_BUCKET", "izy-raw-datalake-2026"),
    "region": os.getenv("AWS_REGION", "us-east-1"),
    "access_key_id": os.getenv("AWS_ACCESS_KEY_ID"),
    "secret_access_key": os.getenv("AWS_SECRET_ACCESS_KEY"),
    "poll_interval_seconds": int(os.getenv("S3_POLL_INTERVAL", 60)),
}

# MinIO Bronze Layer
MINIO_CONFIG = {
    "endpoint": "localhost:9000",
    "access_key": "admin",
    "secret_key": "password123",
    "bucket": "syniqai-bronze",
    "secure": False
}
