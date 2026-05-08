"""
Bronze Ready Emitter - CDC File Downloader & Router
====================================================
Consumes CDC events from bronze-mongodb and bronze-s3 topics,
downloads actual files from source systems (MongoDB GridFS or AWS S3),
writes them to MinIO Bronze layer, and routes them to appropriate topics
based on file type.

Architecture Flow:
  1. Kafka Consumer → bronze-mongodb, bronze-s3
  2. File Download → MongoDB GridFS or AWS S3
  3. MinIO Write → syniqai-bronze/general/{source}/{file_type}/{filename}
  4. File Type Detection → extension-based routing
  5. Kafka Producer → bronze-media-pending (videos/audio) or bronze-ready (documents)

Routing Logic:
    - audio/video → bronze-media-pending (wait for user trigger)
    - pdf/txt/image/doc → bronze-ready (auto AI processing)

Usage:
    python bronze_ready_emitter.py
    
Environment Variables:
    KAFKA_BOOTSTRAP_SERVERS (default: localhost:9092)
    MINIO_ENDPOINT (default: localhost:9000)
    MINIO_ACCESS_KEY (default: admin)
    MINIO_SECRET_KEY (default: password123)
    MONGODB_URI (MongoDB connection string)
    MONGODB_DATABASE (MongoDB database name)
"""

import os
import json
import logging
import io
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional, List, Any
from threading import Event
import signal
import sys
import mimetypes

# Load environment variables
from dotenv import load_dotenv
_THIS_DIR = Path(__file__).resolve().parent
load_dotenv(_THIS_DIR / ".env")
load_dotenv(_THIS_DIR / ".env.mongodb")

# Kafka imports
from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import KafkaError

# MinIO imports
from minio import Minio
from minio.error import S3Error as MinioError

# MongoDB imports (optional)
try:
    from pymongo import MongoClient
    from gridfs import GridFS
    from bson import ObjectId
    MONGODB_AVAILABLE = True
except ImportError:
    logger = logging.getLogger("BronzeReadyEmitter")
    logger.warning("pymongo not installed. MongoDB CDC will be disabled.")
    MONGODB_AVAILABLE = False

# AWS S3 imports (optional)
try:
    import boto3
    from botocore.exceptions import ClientError
    S3_AVAILABLE = True
except ImportError:
    logger = logging.getLogger("BronzeReadyEmitter")
    logger.warning("boto3 not installed. S3 CDC will be disabled.")
    S3_AVAILABLE = False

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger("BronzeReadyEmitter")

# ============================================================================
# Configuration
# ============================================================================

# Kafka configuration
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
KAFKA_GROUP_ID = os.getenv("KAFKA_CONSUMER_GROUP", "bronze-ready-emitter")

# Input topics
TOPIC_BRONZE_MONGODB = "bronze-mongodb"
TOPIC_BRONZE_S3 = "bronze-s3"

# Output topics
TOPIC_BRONZE_READY = "bronze-ready"
TOPIC_BRONZE_MEDIA_PENDING = "bronze-media-pending"

# MinIO configuration
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "admin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "password123")
MINIO_SECURE = os.getenv("MINIO_SECURE", "false").lower() == "true"
MINIO_BRONZE_BUCKET = os.getenv("MINIO_BRONZE_BUCKET", "syniqai-bronze")

# MongoDB configuration
MONGODB_URI = os.getenv("MONGODB_URI", "")
MONGODB_DATABASE = os.getenv("MONGODB_DATABASE", "media_db")

# AWS S3 configuration (from s3_config.json)
S3_CONFIG_PATH = _THIS_DIR.parent / "data ingestion" / "Connector" / "s3_config.json"

# File type classification
MEDIA_EXTENSIONS = {
    # Audio
    '.mp3', '.wav', '.flac', '.aac', '.ogg', '.m4a', '.wma', '.opus',
    # Video
    '.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm', '.m4v', '.mpg', '.mpeg'
}

DOCUMENT_EXTENSIONS = {
    '.pdf', '.doc', '.docx', '.txt', '.csv', '.xls', '.xlsx',
    '.ppt', '.pptx', '.odt', '.rtf', '.md', '.json', '.xml',
    '.html', '.htm'
}

IMAGE_EXTENSIONS = {
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp',
    '.tiff', '.tif', '.ico', '.heic', '.heif'
}


# ============================================================================
# File Type Classifier
# ============================================================================

def classify_file(filename: str) -> tuple:
    """
    Classify file by extension.
    
    Returns:
      (file_type: str, routing_topic: str)
      
    Examples:
      video.mp4 → ('video', 'bronze-media-pending')
      document.pdf → ('pdf', 'bronze-ready')
    """
    ext = Path(filename).suffix.lower()
    
    # Determine file type
    if ext in MEDIA_EXTENSIONS:
        if ext in {'.mp3', '.wav', '.flac', '.aac', '.ogg', '.m4a', '.wma', '.opus'}:
            file_type = 'audio'
        else:
            file_type = 'video'
        routing_topic = TOPIC_BRONZE_MEDIA_PENDING
    elif ext in IMAGE_EXTENSIONS:
        file_type = 'images'
        routing_topic = TOPIC_BRONZE_READY
    elif ext in DOCUMENT_EXTENSIONS:
        file_type = ext[1:]  # Remove the dot
        routing_topic = TOPIC_BRONZE_READY
    else:
        file_type = 'other'
        routing_topic = TOPIC_BRONZE_READY
    
    return file_type, routing_topic


# ============================================================================
# MinIO Bronze Client
# ============================================================================

class MinIOBronzeClient:
    """MinIO client for writing files to Bronze layer"""
    
    def __init__(self):
        self.client = Minio(
            MINIO_ENDPOINT,
            access_key=MINIO_ACCESS_KEY,
            secret_key=MINIO_SECRET_KEY,
            secure=MINIO_SECURE
        )
        self._ensure_bucket()
    
    def _ensure_bucket(self):
        """Ensure Bronze bucket exists"""
        try:
            if not self.client.bucket_exists(MINIO_BRONZE_BUCKET):
                self.client.make_bucket(MINIO_BRONZE_BUCKET)
                logger.info(f"Created MinIO bucket: {MINIO_BRONZE_BUCKET}")
        except MinioError as e:
            logger.error(f"Failed to create/check bucket: {e}")
            raise
    
    def write_file(
        self,
        source: str,
        file_type: str,
        filename: str,
        data: bytes,
        metadata: Optional[Dict] = None
    ) -> str:
        """
        Write file to MinIO Bronze layer.
        
        Path structure: general/{source}/{file_type}/{filename}
        
        Returns: MinIO object key
        """
        # Build object key
        object_key = f"general/{source}/{file_type}/{filename}"
        
        # Prepare metadata
        minio_metadata = {
            "source": source,
            "file_type": file_type,
            "ingested_at": datetime.now(timezone.utc).isoformat(),
        }
        if metadata:
            minio_metadata.update({
                f"x-amz-meta-{k}": str(v)
                for k, v in metadata.items()
            })
        
        # Detect content type
        content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        
        try:
            # Upload to MinIO
            file_stream = io.BytesIO(data)
            self.client.put_object(
                MINIO_BRONZE_BUCKET,
                object_key,
                file_stream,
                length=len(data),
                content_type=content_type,
                metadata=minio_metadata
            )
            
            logger.info(f"✓ Wrote {len(data):,} bytes to MinIO: {object_key}")
            return object_key
            
        except MinioError as e:
            logger.error(f"Failed to write to MinIO: {e}")
            raise


# ============================================================================
# MongoDB GridFS Downloader
# ============================================================================

class MongoDBFileDownloader:
    """Downloads files from MongoDB GridFS"""
    
    def __init__(self):
        if not MONGODB_AVAILABLE:
            raise RuntimeError("pymongo not installed")
        
        if not MONGODB_URI:
            raise RuntimeError("MONGODB_URI not configured")
        
        self.client = MongoClient(MONGODB_URI)
        self.db = self.client[MONGODB_DATABASE]
        self.fs = GridFS(self.db)
        
        # Test connection
        self.client.admin.command('ping')
        logger.info(f"✓ MongoDB connected: {MONGODB_DATABASE}")
    
    def download_file(self, file_id: str) -> Optional[Dict[str, Any]]:
        """
        Download file from GridFS.
        
        Returns:
          {
              'data': bytes,
              'filename': str,
              'content_type': str,
              'size': int,
              'metadata': dict
          }
        """
        try:
            # Convert string to ObjectId if needed
            if isinstance(file_id, str):
                file_id = ObjectId(file_id)
            
            # Get GridFS file
            grid_file = self.fs.get(file_id)
            
            return {
                'data': grid_file.read(),
                'filename': grid_file.filename or f"file_{file_id}",
                'content_type': grid_file.content_type or "application/octet-stream",
                'size': grid_file.length,
                'metadata': grid_file.metadata or {}
            }
            
        except Exception as e:
            logger.error(f"Failed to download from MongoDB GridFS: {e}")
            return None
    
    def close(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()


# ============================================================================
# AWS S3 Downloader
# ============================================================================

class S3FileDownloader:
    """Downloads files from AWS S3"""
    
    def __init__(self):
        if not S3_AVAILABLE:
            raise RuntimeError("boto3 not installed")
        
        # Load S3 config from JSON
        if not S3_CONFIG_PATH.exists():
            raise RuntimeError(f"S3 config not found: {S3_CONFIG_PATH}")
        
        with open(S3_CONFIG_PATH, 'r') as f:
            config = json.load(f)
        
        self.bucket = config['s3_bucket']
        self.client = boto3.client(
            's3',
            region_name=config.get('aws_region', 'us-east-1'),
            aws_access_key_id=config['aws_access_key'],
            aws_secret_access_key=config['aws_secret_key']
        )
        
        logger.info(f"✓ S3 client initialized: {self.bucket}")
    
    def download_file(self, s3_key: str) -> Optional[Dict[str, Any]]:
        """
        Download file from S3.
        
        Returns:
          {
              'data': bytes,
              'filename': str,
              'content_type': str,
              'size': int,
              'metadata': dict
          }
        """
        try:
            # Get object metadata first
            head = self.client.head_object(Bucket=self.bucket, Key=s3_key)
            
            # Download object
            response = self.client.get_object(Bucket=self.bucket, Key=s3_key)
            data = response['Body'].read()
            
            # Extract filename from key
            filename = Path(s3_key).name
            
            return {
                'data': data,
                'filename': filename,
                'content_type': head.get('ContentType', 'application/octet-stream'),
                'size': head.get('ContentLength', len(data)),
                'metadata': head.get('Metadata', {})
            }
            
        except ClientError as e:
            logger.error(f"Failed to download from S3: {e}")
            return None


# ============================================================================
# Bronze Ready Emitter
# ============================================================================

class BronzeReadyEmitter:
    """
    Main Kafka consumer that processes CDC events, downloads files from source systems,
    writes them to MinIO Bronze, and routes them to appropriate downstream topics.
    """
    
    def __init__(self):
        self.consumer: Optional[KafkaConsumer] = None
        self.producer: Optional[KafkaProducer] = None
        self.minio_client: Optional[MinIOBronzeClient] = None
        self.mongodb_downloader: Optional[MongoDBFileDownloader] = None
        self.s3_downloader: Optional[S3FileDownloader] = None
        self.stop_event = Event()
        
        # Statistics
        self.stats = {
            'events_processed': 0,
            'files_written': 0,
            'bytes_written': 0,
            'routed_ready': 0,
            'routed_media_pending': 0,
            'errors': 0,
            'started_at': datetime.now(timezone.utc).isoformat(),
            'last_event_at': None
        }
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        logger.info(f"Received signal {signum}, shutting down...")
        self.stop_event.set()
    
    def _init_kafka_consumer(self) -> KafkaConsumer:
        """Initialize Kafka consumer"""
        try:
            topics = [TOPIC_BRONZE_MONGODB, TOPIC_BRONZE_S3]
            consumer = KafkaConsumer(
                *topics,
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS.split(','),
                group_id=KAFKA_GROUP_ID,
                auto_offset_reset='earliest',
                enable_auto_commit=True,
                api_version=(2, 8, 0),  # Explicit API version for compatibility
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                key_deserializer=lambda k: k.decode('utf-8') if k else None,
                max_poll_records=10,  # Process fewer at a time since we're downloading
                session_timeout_ms=30000,
                heartbeat_interval_ms=10000
            )
            logger.info(f"Kafka consumer initialized: {topics} → {KAFKA_GROUP_ID}")
            return consumer
        except Exception as e:
            logger.error(f"Failed to initialize Kafka consumer: {e}")
            raise
    
    def _init_kafka_producer(self) -> KafkaProducer:
        """Initialize Kafka producer"""
        try:
            producer = KafkaProducer(
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS.split(','),
                api_version=(2, 8, 0),  # Explicit API version for compatibility
                value_serializer=lambda v: json.dumps(v, default=str).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None,
                acks='all',
                retries=3,
                compression_type='gzip',
                max_block_ms=5000
            )
            logger.info(f"Kafka producer initialized → {KAFKA_BOOTSTRAP_SERVERS}")
            return producer
        except Exception as e:
            logger.error(f"Failed to initialize Kafka producer: {e}")
            raise
    
    def _process_message(self, message):
        """Process a single Kafka message"""
        try:
            topic = message.topic
            value = message.value
            key = message.key
            
            self.stats['events_processed'] += 1
            self.stats['last_event_at'] = datetime.now(timezone.utc).isoformat()
            
            logger.info(f"📨 Received event from {topic}")
            
            # Route to appropriate processor
            if topic == TOPIC_BRONZE_MONGODB:
                self._process_mongodb_event(value)
            elif topic == TOPIC_BRONZE_S3:
                self._process_s3_event(value)
            else:
                logger.warning(f"Unknown topic: {topic}")
                
        except Exception as e:
            self.stats['errors'] += 1
            logger.error(f"Error processing message: {e}", exc_info=True)
    
    def _process_mongodb_event(self, event: Dict):
        """Process MongoDB CDC event - download file and write to Bronze"""
        if not self.mongodb_downloader:
            logger.error("MongoDB downloader not available")
            return
        
        try:
            # Extract file reference from event
            # Event structure: {op, source: {db, collection, ts_ms}, after: {...document}}
            operation = event.get('op', 'read')
            document = event.get('after', {})
            
            # Look for GridFS file_id (adjust field name based on your schema)
            file_id = document.get('file_id') or document.get('_id')
            if not file_id:
                logger.warning("No file_id found in MongoDB event")
                return
            
            # Download file from GridFS
            logger.info(f"📥 Downloading file from MongoDB: {file_id}")
            file_data = self.mongodb_downloader.download_file(str(file_id))
            
            if not file_data:
                logger.error(f"Failed to download file {file_id}")
                return
            
            # Write to MinIO and route
            self._write_and_route(
                source='mongodb',
                file_data=file_data,
                original_event=event
            )
            
        except Exception as e:
            logger.error(f"Error processing MongoDB event: {e}", exc_info=True)
            self.stats['errors'] += 1
    
    def _process_s3_event(self, event: Dict):
        """Process S3 CDC event - download file and write to Bronze"""
        if not self.s3_downloader:
            logger.error("S3 downloader not available")
            return
        
        try:
            # Extract S3 key from event
            # Event structure: {op, source: {bucket, region, ts_ms}, file: {key, etag, size, ...}}
            file_info = event.get('file', {})
            s3_key = file_info.get('key')
            
            if not s3_key:
                logger.warning("No S3 key found in event")
                return
            
            # Download file from S3
            logger.info(f"📥 Downloading file from S3: {s3_key}")
            file_data = self.s3_downloader.download_file(s3_key)
            
            if not file_data:
                logger.error(f"Failed to download file {s3_key}")
                return
            
            # Write to MinIO and route
            self._write_and_route(
                source='s3',
                file_data=file_data,
                original_event=event
            )
            
        except Exception as e:
            logger.error(f"Error processing S3 event: {e}", exc_info=True)
            self.stats['errors'] += 1
    
    def _write_and_route(
        self,
        source: str,
        file_data: Dict[str, Any],
        original_event: Dict
    ):
        """
        Write file to MinIO Bronze and emit routing event.
        
        Args:
          source: 'mongodb' or 's3'
          file_data: {data, filename, content_type, size, metadata}
          original_event: Original CDC event from Kafka
        """
        try:
            # Classify file
            filename = file_data['filename']
            file_type, routing_topic = classify_file(filename)
            
            logger.info(f"📊 File classification: {filename} → {file_type} → {routing_topic}")
            
            # Write to MinIO Bronze
            bronze_key = self.minio_client.write_file(
                source=source,
                file_type=file_type,
                filename=filename,
                data=file_data['data'],
                metadata=file_data.get('metadata', {})
            )
            
            # Update stats
            self.stats['files_written'] += 1
            self.stats['bytes_written'] += file_data['size']
            
            # Build routing event
            routing_event = {
                'source': source,
                'file_type': file_type,
                'bronze_minio_key': bronze_key,
                'original_filename': filename,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'size_bytes': file_data['size'],
                'content_type': file_data['content_type'],
                'routed_to': routing_topic,
                'original_event': original_event  # Include for traceability
            }
            
            # Emit to routing topic
            self.producer.send(
                routing_topic,
                key=bronze_key,
                value=routing_event
            )
            self.producer.flush()
            
            # Update topic-specific stats
            if routing_topic == TOPIC_BRONZE_READY:
                self.stats['routed_ready'] += 1
            else:
                self.stats['routed_media_pending'] += 1
            
            logger.info(
                f"✅ File ingested: {filename} → {bronze_key} → {routing_topic} "
                f"({file_data['size']:,} bytes)"
            )
            
        except Exception as e:
            logger.error(f"Error in write_and_route: {e}", exc_info=True)
            raise
    
    def start(self):
        """Start the emitter"""
        logger.info("=" * 80)
        logger.info("Bronze Ready Emitter - Starting")
        logger.info("=" * 80)
        logger.info(f"Kafka: {KAFKA_BOOTSTRAP_SERVERS}")
        logger.info(f"MinIO: {MINIO_ENDPOINT}/{MINIO_BRONZE_BUCKET}")
        logger.info(f"Topics: {TOPIC_BRONZE_MONGODB}, {TOPIC_BRONZE_S3}")
        logger.info(f"Routing: {TOPIC_BRONZE_READY}, {TOPIC_BRONZE_MEDIA_PENDING}")
        logger.info("=" * 80)
        
        try:
            # Initialize Kafka clients
            self.consumer = self._init_kafka_consumer()
            self.producer = self._init_kafka_producer()
            
            # Initialize MinIO client
            self.minio_client = MinIOBronzeClient()
            
            # Initialize file downloaders
            if MONGODB_AVAILABLE and MONGODB_URI:
                try:
                    self.mongodb_downloader = MongoDBFileDownloader()
                except Exception as e:
                    logger.warning(f"MongoDB downloader disabled: {e}")
            
            if S3_AVAILABLE and S3_CONFIG_PATH.exists():
                try:
                    self.s3_downloader = S3FileDownloader()
                except Exception as e:
                    logger.warning(f"S3 downloader disabled: {e}")
            
            logger.info("✓ All clients initialized")
            logger.info("🚀 Starting message consumption...")
            
            # Main consumption loop
            while not self.stop_event.is_set():
                try:
                    # Poll for messages
                    msg_batch = self.consumer.poll(timeout_ms=1000, max_records=10)
                    
                    if not msg_batch:
                        continue
                    
                    # Process messages
                    for topic_partition, messages in msg_batch.items():
                        for message in messages:
                            if self.stop_event.is_set():
                                break
                            self._process_message(message)
                    
                    # Log stats every 10 messages
                    if self.stats['events_processed'] % 10 == 0 and self.stats['events_processed'] > 0:
                        logger.info(
                            f"📊 Stats: Processed={self.stats['events_processed']}, "
                            f"Written={self.stats['files_written']}, "
                            f"Ready={self.stats['routed_ready']}, "
                            f"Pending={self.stats['routed_media_pending']}, "
                            f"Errors={self.stats['errors']}"
                        )
                
                except KafkaError as e:
                    logger.error(f"Kafka error: {e}")
                    self.stop_event.wait(5)  # Wait before retry
                    
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
        except Exception as e:
            logger.error(f"Fatal error: {e}", exc_info=True)
        finally:
            self.stop()
    
    def stop(self):
        """Stop the emitter and cleanup"""
        logger.info("⏹️  Stopping Bronze Ready Emitter...")
        self.stop_event.set()
        
        if self.consumer:
            try:
                self.consumer.close()
                logger.info("✓ Kafka consumer closed")
            except Exception as e:
                logger.error(f"Error closing consumer: {e}")
        
        if self.producer:
            try:
                self.producer.flush()
                self.producer.close()
                logger.info("✓ Kafka producer closed")
            except Exception as e:
                logger.error(f"Error closing producer: {e}")
        
        if self.mongodb_downloader:
            try:
                self.mongodb_downloader.close()
            except Exception as e:
                logger.error(f"Error closing MongoDB: {e}")
        
        # Log final stats
        logger.info("=" * 80)
        logger.info("Final Statistics:")
        logger.info(f"  Events Processed: {self.stats['events_processed']}")
        logger.info(f"  Files Written: {self.stats['files_written']}")
        logger.info(f"  Bytes Written: {self.stats['bytes_written']:,}")
        logger.info(f"  Routed to Ready: {self.stats['routed_ready']}")
        logger.info(f"  Routed to Media Pending: {self.stats['routed_media_pending']}")
        logger.info(f"  Errors: {self.stats['errors']}")
        logger.info("=" * 80)
    
    def get_stats(self) -> Dict:
        """Get current statistics"""
        return self.stats.copy()


# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    """Main entry point"""
    logger.info("🚀 Bronze Ready Emitter - CDC File Processor")
    emitter = BronzeReadyEmitter()
    emitter.start()


if __name__ == "__main__":
    main()
