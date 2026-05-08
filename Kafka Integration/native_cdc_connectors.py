"""
Native Kafka CDC Connectors (NO DOCKER)
========================================
Pure Python CDC for PostgreSQL, MongoDB, AWS S3, and MariaDB
Connects to native Kafka broker at localhost:9092

Features:
- Works with native Kafka (KRaft mode, no Zookeeper)
- No Docker dependencies
- Direct database connections
- Real-time change streaming
"""

import json
import logging
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from kafka import KafkaProducer
from kafka.errors import KafkaError
import pymongo
from pymongo import MongoClient
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import mysql.connector
import boto3
from pathlib import Path

from native_cdc_config import (
    KAFKA_CONFIG, TOPICS, POSTGRES_CONFIG, MARIADB_CONFIG,
    MONGODB_CONFIG, S3_CONFIG, MINIO_CONFIG
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class NativeKafkaProducer:
    """Native Kafka producer with proper configuration"""
    
    def __init__(self):
        self.producer = None
        self._connect()
    
    def _connect(self):
        """Connect to native Kafka broker"""
        try:
            self.producer = KafkaProducer(
                **KAFKA_CONFIG,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None,
                acks='all',
                compression_type='snappy',
                max_in_flight_requests_per_connection=5,
                retries=3
            )
            logger.info(f"✓ Connected to native Kafka broker: {KAFKA_CONFIG['bootstrap_servers']}")
        except Exception as e:
            logger.error(f"✗ Failed to connect to Kafka: {e}")
            raise
    
    def send(self, topic: str, value: Dict[str, Any], key: Optional[str] = None):
        """Send message to Kafka topic"""
        try:
            future = self.producer.send(topic, value=value, key=key)
            record_metadata = future.get(timeout=10)
            logger.debug(f"Sent to {topic}: partition={record_metadata.partition}, offset={record_metadata.offset}")
            return True
        except KafkaError as e:
            logger.error(f"Kafka send error: {e}")
            return False
    
    def close(self):
        """Close Kafka producer"""
        if self.producer:
            self.producer.flush()
            self.producer.close()
            logger.info("✓ Kafka producer closed")


class MongoDBCDC:
    """Native MongoDB Change Data Capture"""
    
    def __init__(self, kafka_producer: NativeKafkaProducer):
        self.producer = kafka_producer
        self.client = None
        self.db = None
        self._connect()
    
    def _connect(self):
        """Connect to MongoDB"""
        try:
            self.client = MongoClient(
                MONGODB_CONFIG["uri"],
                serverSelectionTimeoutMS=5000
            )
            self.client.server_info()  # Test connection
            self.db = self.client[MONGODB_CONFIG["database"]]
            logger.info(f"✓ Connected to MongoDB: {MONGODB_CONFIG['database']}")
        except Exception as e:
            logger.error(f"✗ MongoDB connection failed: {e}")
            raise
    
    def start_change_stream(self):
        """Start MongoDB change stream"""
        logger.info(f"Starting MongoDB CDC for collections: {MONGODB_CONFIG['collections']}")
        
        for collection_name in MONGODB_CONFIG["collections"]:
            try:
                collection = self.db[collection_name]
                
                # Create change stream with full document
                with collection.watch(full_document='updateLookup') as stream:
                    logger.info(f"✓ Watching {collection_name} for changes...")
                    
                    for change in stream:
                        event = {
                            "operation": change["operationType"],
                            "collection": collection_name,
                            "database": MONGODB_CONFIG["database"],
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "document": self._serialize_document(change.get("fullDocument", {})),
                            "document_key": str(change.get("documentKey", {}).get("_id", ""))
                        }
                        
                        # Send to Kafka
                        self.producer.send(
                            TOPICS["mongodb"],
                            value=event,
                            key=f"{collection_name}:{event['document_key']}"
                        )
                        logger.info(f"📤 MongoDB CDC: {event['operation']} on {collection_name}")
            
            except Exception as e:
                logger.error(f"✗ Error watching {collection_name}: {e}")
    
    def _serialize_document(self, doc: Dict) -> Dict:
        """Serialize MongoDB document to JSON-compatible format"""
        from bson import ObjectId
        
        def convert(obj):
            if isinstance(obj, ObjectId):
                return str(obj)
            elif isinstance(obj, datetime):
                return obj.isoformat()
            elif isinstance(obj, dict):
                return {k: convert(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert(item) for item in obj]
            return obj
        
        return convert(doc)
    
    def close(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            logger.info("✓ MongoDB connection closed")


class S3CDC:
    """Native AWS S3 Change Data Capture via polling"""
    
    def __init__(self, kafka_producer: NativeKafkaProducer):
        self.producer = kafka_producer
        self.s3_client = None
        self.last_modified_cache = {}
        self._connect()
    
    def _connect(self):
        """Connect to AWS S3"""
        try:
            self.s3_client = boto3.client(
                's3',
                region_name=S3_CONFIG["region"],
                aws_access_key_id=S3_CONFIG["access_key_id"],
                aws_secret_access_key=S3_CONFIG["secret_access_key"]
            )
            # Test connection
            self.s3_client.head_bucket(Bucket=S3_CONFIG["bucket"])
            logger.info(f"✓ Connected to S3 bucket: {S3_CONFIG['bucket']}")
        except Exception as e:
            logger.error(f"✗ S3 connection failed: {e}")
            raise
    
    def start_polling(self):
        """Poll S3 bucket for new/updated files"""
        logger.info(f"Starting S3 CDC polling every {S3_CONFIG['poll_interval_seconds']}s...")
        
        while True:
            try:
                response = self.s3_client.list_objects_v2(Bucket=S3_CONFIG["bucket"])
                
                if 'Contents' in response:
                    for obj in response['Contents']:
                        key = obj['Key']
                        last_modified = obj['LastModified']
                        
                        # Check if new or updated
                        if key not in self.last_modified_cache or self.last_modified_cache[key] < last_modified:
                            event = {
                                "operation": "update" if key in self.last_modified_cache else "insert",
                                "bucket": S3_CONFIG["bucket"],
                                "key": key,
                                "size": obj['Size'],
                                "last_modified": last_modified.isoformat(),
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                                "etag": obj.get('ETag', '').strip('"')
                            }
                            
                            # Send to Kafka
                            self.producer.send(
                                TOPICS["s3"],
                                value=event,
                                key=key
                            )
                            logger.info(f"📤 S3 CDC: {event['operation']} - {key}")
                            
                            # Update cache
                            self.last_modified_cache[key] = last_modified
                
                time.sleep(S3_CONFIG["poll_interval_seconds"])
            
            except Exception as e:
                logger.error(f"✗ S3 polling error: {e}")
                time.sleep(S3_CONFIG["poll_interval_seconds"])


def run_mongodb_cdc():
    """Run MongoDB CDC"""
    producer = NativeKafkaProducer()
    mongo_cdc = MongoDBCDC(producer)
    
    try:
        mongo_cdc.start_change_stream()
    except KeyboardInterrupt:
        logger.info("Stopping MongoDB CDC...")
    finally:
        mongo_cdc.close()
        producer.close()


def run_s3_cdc():
    """Run S3 CDC"""
    producer = NativeKafkaProducer()
    s3_cdc = S3CDC(producer)
    
    try:
        s3_cdc.start_polling()
    except KeyboardInterrupt:
        logger.info("Stopping S3 CDC...")
    finally:
        producer.close()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python native_cdc_connectors.py [mongodb|s3]")
        sys.exit(1)
    
    source = sys.argv[1].lower()
    
    if source == "mongodb":
        run_mongodb_cdc()
    elif source == "s3":
        run_s3_cdc()
    else:
        print(f"Unknown source: {source}")
        print("Available: mongodb, s3")
        sys.exit(1)
