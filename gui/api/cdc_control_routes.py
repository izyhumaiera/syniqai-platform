"""
CDC Control Routes - MongoDB & S3 Change Stream Management
===========================================================
Manages real-time change data capture for MongoDB and S3 using custom connectors.

Endpoints:
    POST /api/cdc/mongodb/start    - Start MongoDB change stream
    POST /api/cdc/mongodb/stop     - Stop MongoDB change stream
    GET  /api/cdc/mongodb/status   - Get MongoDB CDC status
    GET  /api/cdc/mongodb/events   - Get recent events from bronze-mongodb topic
    POST /api/cdc/s3/start         - Start S3 polling
    POST /api/cdc/s3/stop          - Stop S3 polling
    GET  /api/cdc/s3/status        - Get S3 CDC status
    GET  /api/cdc/s3/events        - Get recent events from bronze-s3 topic
"""

import json
import logging
import os
import subprocess
import psutil
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "127.0.0.1:9092")
MONGODB_TOPIC = "bronze-mongodb"
S3_TOPIC = "bronze-s3"

# Paths
KAFKA_INTEGRATION_DIR = Path(__file__).parent.parent.parent / "Kafka Integration"
NATIVE_CDC_SCRIPT = KAFKA_INTEGRATION_DIR / "native_cdc_connectors.py"  # NEW: Native CDC (no Docker)
MONGODB_ENV_FILE = KAFKA_INTEGRATION_DIR / ".env.mongodb"

# Global process tracking
_mongodb_process: Optional[subprocess.Popen] = None
_s3_process: Optional[subprocess.Popen] = None


# ---------------------------------------------------------------------------
# Request/Response Models
# ---------------------------------------------------------------------------
class MongoDBStartRequest(BaseModel):
    """Request to start MongoDB CDC"""
    uri: Optional[str] = None
    database: Optional[str] = None
    collection: Optional[str] = None


class S3StartRequest(BaseModel):
    """Request to start S3 CDC"""
    bucket: Optional[str] = None
    region: Optional[str] = "us-east-1"
    access_key_id: Optional[str] = None
    secret_access_key: Optional[str] = None


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------
def _get_process_by_script(script_name: str) -> Optional[psutil.Process]:
    """Find a Python process running the specified script"""
    try:
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = proc.info.get('cmdline', [])
                if cmdline and any(script_name in str(arg) for arg in cmdline):
                    return psutil.Process(proc.info['pid'])
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    except Exception as e:
        logger.error(f"Error finding process {script_name}: {e}")
    return None


def _consume_kafka_topic(topic: str, max_messages: int = 20) -> List[Dict[str, Any]]:
    """Consume recent messages from a Kafka topic"""
    messages = []
    try:
        from kafka import KafkaConsumer
        
        consumer = KafkaConsumer(
            topic,
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS.split(','),
            group_id=f'api-consumer-{topic}-{int(datetime.utcnow().timestamp())}',
            auto_offset_reset='latest',  # Start from recent messages
            enable_auto_commit=False,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            consumer_timeout_ms=3000
        )
        
        # Seek to end minus max_messages
        partitions = consumer.assignment() or consumer.partitions_for_topic(topic)
        if partitions:
            consumer.poll(timeout_ms=1000)  # Trigger assignment
            partitions = consumer.assignment()
            
            # Get end offsets
            end_offsets = consumer.end_offsets(partitions)
            
            # Seek back max_messages
            for partition in partitions:
                end_offset = end_offsets.get(partition, 0)
                start_offset = max(0, end_offset - max_messages)
                consumer.seek(partition, start_offset)
        
        for message in consumer:
            value = message.value
            
            # Determine routing based on file type (if available)
            object_key = value.get('file', {}).get('key') or value.get('after', {}).get('_id', '')
            file_type = _detect_file_type(str(object_key))
            routed_to_topic = 'bronze-media-pending' if file_type in ['audio', 'video'] else 'bronze-ready'
            
            # Extract relevant fields
            msg_data = {
                'timestamp': datetime.fromtimestamp(message.timestamp / 1000.0).isoformat() if message.timestamp else None,
                'operation': value.get('op', 'unknown'),
                'source': value.get('source', {}),
                'bronze_minio_key': _extract_minio_key(value, topic),
                'routed_to_topic': routed_to_topic,
                'file_type': file_type,
                'offset': message.offset,
                'partition': message.partition
            }
            
            #  Add source-specific fields
            if topic == MONGODB_TOPIC:
                msg_data['collection'] = value.get('source', {}).get('collection', 'N/A')
                msg_data['document_id'] = value.get('after', {}).get('_id', 'N/A')
            elif topic == S3_TOPIC:
                msg_data['bucket'] = value.get('source', {}).get('bucket', 'N/A')
                msg_data['object_key'] = value.get('file', {}).get('key', 'N/A')
                msg_data['file_size'] = value.get('file', {}).get('size', 0)
            
            messages.append(msg_data)
            
            if len(messages) >= max_messages:
                break
        
        consumer.close()
    except Exception as e:
        logger.error(f"Error consuming from topic {topic}: {e}")
    
    return messages


def _extract_minio_key(value: Dict, topic: str) -> str:
    """Extract the MinIO bronze key from a CDC event"""
    if topic == MONGODB_TOPIC:
        source = value.get('source', {})
        after = value.get('after', {})
        db = source.get('db', 'unknown')
        collection = source.get('collection', 'unknown')
        doc_id = after.get('_id', 'unknown')
        ts_ms = source.get('ts_ms', int(datetime.utcnow().timestamp() * 1000))
        return f"syniqai-bronze/mongodb/{db}_{collection}/{ts_ms}_{doc_id}.json"
    elif topic == S3_TOPIC:
        source = value.get('source', {})
        file_info = value.get('file', {})
        bucket = source.get('bucket', 'unknown')
        key = file_info.get('key', 'unknown')
        return f"syniqai-bronze/s3/{bucket}/{key}"
    return "N/A"


def _detect_file_type(filename: str) -> str:
    """Detect file type from extension"""
    ext = Path(filename).suffix.lower()
    
    type_map = {
        '.pdf': 'pdf',
        '.txt': 'txt', '.log': 'txt', '.md': 'txt', '.csv': 'txt',
        '.jpg': 'image', '.jpeg': 'image', '.png': 'image', '.gif': 'image',
        '.mp3': 'audio', '.wav': 'audio', '.flac': 'audio', '.m4a': 'audio',
        '.mp4': 'video', '.avi': 'video', '.mov': 'video', '.mkv': 'video',
    }
    
    return type_map.get(ext, 'unknown')


def _load_mongodb_config() -> Dict[str, str]:
    """Load MongoDB config from .env.mongodb"""
    config = {}
    if MONGODB_ENV_FILE.exists():
        from dotenv import load_dotenv
        load_dotenv(MONGODB_ENV_FILE)
        config = {
            'uri': os.getenv('MONGODB_URI', ''),
            'database': os.getenv('MONGODB_DATABASE', ''),
            'collections': os.getenv('MONGODB_COLLECTIONS', '')
        }
    return config


# ---------------------------------------------------------------------------
# MongoDB CDC Endpoints
# ---------------------------------------------------------------------------

@router.post("/mongodb/start")
async def start_mongodb_cdc(request: MongoDBStartRequest):
    """
    Start MongoDB change stream CDC (Native - No Docker).
    Launches native_cdc_connectors.py as a subprocess.
    """
    global _mongodb_process
    
    # Check if already running
    existing = _get_process_by_script("native_cdc_connectors.py")
    if existing and "mongodb" in " ".join(existing.cmdline() or []):
        return {
            "success": False,
            "message": f"MongoDB CDC is already running (PID: {existing.pid})",
            "status": "already_running",
            "pid": existing.pid,
            "started_at": datetime.fromtimestamp(existing.create_time()).isoformat()
        }
    
    # Check if script exists
    if not NATIVE_CDC_SCRIPT.exists():
        raise HTTPException(
            status_code=404,
            detail=f"native_cdc_connectors.py not found at {NATIVE_CDC_SCRIPT}"
        )
    
    try:
        # Load config
        config = _load_mongodb_config()
        uri = request.uri or config.get('uri', '')
        database = request.database or config.get('database', '')
        collection = request.collection or config.get('collections', '').split(',')[0] if config.get('collections') else ''
        
        if not uri:
            raise HTTPException(
                status_code=400,
                detail="MongoDB URI is required (either in request or .env.mongodb)"
            )
        
        # Create log directory
        log_dir = KAFKA_INTEGRATION_DIR / "logs"
        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / f"mongodb_cdc_native_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        
        # Build command - NATIVE CDC with argument
        python_exe = sys.executable
        cmd = [python_exe, str(NATIVE_CDC_SCRIPT), "mongodb"]  # NEW: Pass "mongodb" as argument
        
        # Set environment variables for the subprocess
        env = os.environ.copy()
        if uri:
            env['MONGODB_URI'] = uri
        if database:
            env['MONGODB_DATABASE'] = database
        if collection:
            env['MONGODB_COLLECTIONS'] = collection
        
        # Start process
        with open(log_file, 'w') as log:
            _mongodb_process = subprocess.Popen(
                cmd,
                env=env,
                cwd=str(KAFKA_INTEGRATION_DIR),
                stdout=log,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == 'win32' else 0
            )
        
        logger.info(f"Native MongoDB CDC started: PID={_mongodb_process.pid}, log={log_file}")
        
        return {
            "success": True,
            "message": "MongoDB CDC started successfully (Native - No Docker)",
            "status": "started",
            "pid": _mongodb_process.pid,
            "started_at": datetime.now().isoformat(),
            "log_file": str(log_file),
            "config": {
                "uri": uri[:30] + "..." if len(uri) > 30 else uri,
                "database": database,
                "collection": collection
            }
        }
        
    except Exception as e:
        logger.error(f"Error starting native MongoDB CDC: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/mongodb/stop")
async def stop_mongodb_cdc():
    """Stop MongoDB change stream CDC"""
    process = _get_process_by_script("native_cdc_connectors.py")  # Updated to native CDC
    
    if not process:
        return {
            "success": False,
            "message": "MongoDB CDC is not running",
            "status": "not_running"
        }
    
    try:
        process.terminate()
        try:
            process.wait(timeout=10)
            return {
                "success": True,
                "message": "MongoDB CDC stopped successfully",
                "status": "stopped",
                "pid": process.pid
            }
        except psutil.TimeoutExpired:
            process.kill()
            return {
                "success": True,
                "message": "MongoDB CDC force-stopped",
                "status": "force_stopped",
                "pid": process.pid
            }
    except Exception as e:
        logger.error(f"Error stopping MongoDB CDC: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/mongodb/status")
async def get_mongodb_cdc_status():
    """Get MongoDB CDC status with detailed metrics"""
    process = _get_process_by_script("native_cdc_connectors.py")  # Updated to native CDC
    
    # Check Kafka connection - Simple port check (kafka-python has compatibility issues with Kafka 4.2.0 KRaft)
    kafka_connected = False
    kafka_error = None
    try:
        import socket
        
        # TCP port check
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex(('localhost', 9092))
        sock.close()
        
        if result == 0:
            kafka_connected = True
            logger.debug("✓ Kafka broker port 9092 is reachable")
        else:
            kafka_error = "Port 9092 not reachable"
            logger.warning(f"✗ Kafka port check failed")
    except Exception as e:
        kafka_error = str(e)
        logger.error(f"✗ Kafka connection check error: {e}")
    
    if process:
        try:
            # Check if process is for MongoDB specifically
            cmdline = process.cmdline()
            
            create_time = datetime.fromtimestamp(process.create_time())
            uptime_seconds = (datetime.now() - create_time).total_seconds()
            
            # Get event count from Kafka topic
            events_captured = 0
            last_event_at = None
            try:
                from kafka import KafkaConsumer, TopicPartition
                
                consumer = KafkaConsumer(bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS.split(','))
                partitions = consumer.partitions_for_topic(MONGODB_TOPIC)
                
                if partitions:
                    # Get total messages count
                    topic_partitions = [TopicPartition(MONGODB_TOPIC, p) for p in partitions]
                    end_offsets = consumer.end_offsets(topic_partitions)
                    beginning_offsets = consumer.beginning_offsets(topic_partitions)
                    
                    events_captured = sum(
                        end_offsets.get(tp, 0) - beginning_offsets.get(tp, 0)
                        for tp in topic_partitions
                    )
                    
                    # Get last message timestamp
                    consumer.assign(topic_partitions)
                    for tp in topic_partitions:
                        end_offset = end_offsets.get(tp, 0)
                        if end_offset > 0:
                            consumer.seek(tp, end_offset - 1)
                    
                    # Poll last message
                    records = consumer.poll(timeout_ms=2000, max_records=1)
                    for tp, messages in records.items():
                        if messages:
                            last_msg = messages[0]
                            if last_msg.timestamp:
                                last_event_at = datetime.fromtimestamp(last_msg.timestamp / 1000.0).isoformat()
                
                consumer.close()
            except Exception as e:
                logger.warning(f"Could not fetch events count: {e}")
            
            return {
                "running": True,
                "pid": process.pid,
                "uptime_seconds": int(uptime_seconds),
                "uptime": f"{int(uptime_seconds // 3600)}h {int((uptime_seconds % 3600) // 60)}m",
                "started_at": create_time.isoformat(),
                "events_captured": events_captured,
                "last_event_at": last_event_at,
                "kafka_connected": kafka_connected,
                "kafka_error": kafka_error,
                "kafka_topic": MONGODB_TOPIC,
                "cmdline": " ".join(cmdline) if cmdline else None
            }
        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            logger.warning(f"Process check failed: {e}")
    
    return {
        "running": False,
        "pid": None,
        "events_captured": 0,
        "last_event_at": None,
        "kafka_connected": kafka_connected,
        "kafka_error": kafka_error,
        "kafka_topic": MONGODB_TOPIC
    }


@router.get("/mongodb/events")
async def get_mongodb_events(limit: int = Query(20, ge=1, le=100)):
    """Get recent events from bronze-mongodb topic"""
    try:
        messages = _consume_kafka_topic(MONGODB_TOPIC, max_messages=limit)
        
        return {
            "success": True,
            "topic": MONGODB_TOPIC,
            "events": messages,
            "count": len(messages)
        }
    except Exception as e:
        logger.error(f"Error fetching MongoDB events: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# S3 CDC Endpoints
# ---------------------------------------------------------------------------

@router.post("/s3/start")
async def start_s3_cdc(request: S3StartRequest):
    """Start S3 polling CDC (Native - No Docker)"""
    global _s3_process
    
    # Check if already running
    existing = _get_process_by_script("native_cdc_connectors.py")
    if existing and "s3" in " ".join(existing.cmdline() or []):
        return {
            "success": False,
            "message": f"S3 CDC is already running (PID: {existing.pid})",
            "status": "already_running",
            "pid": existing.pid
        }
    
    # Check if script exists
    if not NATIVE_CDC_SCRIPT.exists():
        raise HTTPException(
            status_code=404,
            detail=f"native_cdc_connectors.py not found at {NATIVE_CDC_SCRIPT}"
        )
    
    try:
        # Create log directory
        log_dir = KAFKA_INTEGRATION_DIR / "logs"
        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / f"s3_cdc_native_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        
        # Build command - NATIVE CDC with argument
        python_exe = sys.executable
        cmd = [python_exe, str(NATIVE_CDC_SCRIPT), "s3"]  # NEW: Pass "s3" as argument
        
        # Set environment variables for S3
        env = os.environ.copy()
        # S3 config is typically loaded from s3_config.json, so no extra env vars needed
        
        # Start process
        with open(log_file, 'w') as log:
            _s3_process = subprocess.Popen(
                cmd,
                env=env,
                cwd=str(KAFKA_INTEGRATION_DIR),
                stdout=log,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == 'win32' else 0
            )
        
        logger.info(f"Native S3 CDC started: PID={_s3_process.pid}, log={log_file}")
        
        return {
            "success": True,
            "message": "S3 CDC started successfully (Native - No Docker)",
            "status": "started",
            "pid": _s3_process.pid,
            "started_at": datetime.now().isoformat(),
            "log_file": str(log_file)
        }
        
    except Exception as e:
        logger.error(f"Error starting native S3 CDC: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/s3/stop")
async def stop_s3_cdc():
    """Stop S3 polling CDC"""
    process = _get_process_by_script("native_cdc_connectors.py")  # Updated to native CDC
    
    if not process or "s3" not in " ".join(process.cmdline() or []):
        return {
            "success": False,
            "message": "S3 CDC is not running",
            "status": "not_running"
        }
    
    try:
        process.terminate()
        try:
            process.wait(timeout=10)
            return {
                "success": True,
                "message": "S3 CDC stopped successfully",
                "status": "stopped",
                "pid": process.pid
            }
        except psutil.TimeoutExpired:
            process.kill()
            return {
                "success": True,
                "message": "S3 CDC force-stopped",
                "status": "force_stopped",
                "pid": process.pid
            }
    except Exception as e:
        logger.error(f"Error stopping S3 CDC: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/s3/status")
async def get_s3_cdc_status():
    """Get S3 CDC status with detailed metrics"""
    process = _get_process_by_script("native_cdc_connectors.py")  # Updated to native CDC
    
    # Check Kafka connection - Simple port check (kafka-python has compatibility issues with Kafka 4.2.0 KRaft)
    kafka_connected = False
    kafka_error = None
    try:
        import socket
        
        # TCP port check
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex(('localhost', 9092))
        sock.close()
        
        if result == 0:
            kafka_connected = True
            logger.debug("✓ Kafka broker port 9092 is reachable")
        else:
            kafka_error = "Port 9092 not reachable"
            logger.warning(f"✗ Kafka port check failed")
    except Exception as e:
        kafka_error = str(e)
        logger.error(f"✗ Kafka connection check error: {e}")
    
    if process and "s3" in " ".join(process.cmdline() or []):
        try:
            create_time = datetime.fromtimestamp(process.create_time())
            uptime_seconds = (datetime.now() - create_time).total_seconds()
            
            # Get event count from Kafka topic
            events_captured = 0
            last_event_at = None
            try:
                from kafka import KafkaConsumer, TopicPartition
                
                consumer = KafkaConsumer(bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS.split(','))
                partitions = consumer.partitions_for_topic(S3_TOPIC)
                
                if partitions:
                    topic_partitions = [TopicPartition(S3_TOPIC, p) for p in partitions]
                    end_offsets = consumer.end_offsets(topic_partitions)
                    beginning_offsets = consumer.beginning_offsets(topic_partitions)
                    
                    events_captured = sum(
                        end_offsets.get(tp, 0) - beginning_offsets.get(tp, 0)
                        for tp in topic_partitions
                    )
                    
                    # Get last message timestamp
                    consumer.assign(topic_partitions)
                    for tp in topic_partitions:
                        end_offset = end_offsets.get(tp, 0)
                        if end_offset > 0:
                            consumer.seek(tp, end_offset - 1)
                    
                    records = consumer.poll(timeout_ms=2000, max_records=1)
                    for tp, messages in records.items():
                        if messages:
                            last_msg = messages[0]
                            if last_msg.timestamp:
                                last_event_at = datetime.fromtimestamp(last_msg.timestamp / 1000.0).isoformat()
                
                consumer.close()
            except Exception as e:
                logger.warning(f"Could not fetch S3 events count: {e}")
            
            return {
                "running": True,
                "pid": process.pid,
                "uptime_seconds": int(uptime_seconds),
                "uptime": f"{int(uptime_seconds // 3600)}h {int((uptime_seconds % 3600) // 60)}m",
                "started_at": create_time.isoformat(),
                "events_captured": events_captured,
                "last_event_at": last_event_at,
                "kafka_connected": kafka_connected,
                "kafka_error": kafka_error,
                "kafka_topic": S3_TOPIC
            }
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    
    return {
        "running": False,
        "pid": None,
        "events_captured": 0,
        "last_event_at": None,
        "kafka_connected": kafka_connected,
        "kafka_error": kafka_error,
        "kafka_topic": S3_TOPIC
    }


@router.get("/s3/events")
async def get_s3_events(limit: int = Query(20, ge=1, le=100)):
    """Get recent events from bronze-s3 topic"""
    try:
        messages = _consume_kafka_topic(S3_TOPIC, max_messages=limit)
        
        return {
            "success": True,
            "topic": S3_TOPIC,
            "events": messages,
            "count": len(messages)
        }
    except Exception as e:
        logger.error(f"Error fetching S3 events: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Combined CDC Events Endpoint
# ---------------------------------------------------------------------------

@router.get("/events")
async def get_cdc_events(
    source: str = Query(..., description="Source: mongodb or s3"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of events to return")
):
    """
    Get recent CDC events from specified source.
    Returns formatted events with routing information.
    
    Each event includes:
      - timestamp: Event timestamp
      - operation: CDC operation (insert/update/delete/create)
      - collection_or_key: MongoDB collection or S3 key
      - file_type: Detected file type
      - bronze_minio_key: Path in MinIO Bronze
      - routed_to: Target topic (bronze-ready or bronze-media-pending)
    """
    if source.lower() == 'mongodb':
        topic = MONGODB_TOPIC
    elif source.lower() == 's3':
        topic = S3_TOPIC
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid source '{source}'. Must be 'mongodb' or 's3'"
        )
    
    try:
        messages = _consume_kafka_topic(topic, max_messages=limit)
        
        # Format messages for frontend display
        formatted_events = []
        for msg in messages:
            event = {
                'timestamp': msg['timestamp'],
                'operation': msg['operation'],
                'file_type': msg['file_type'],
                'bronze_minio_key': msg['bronze_minio_key'],
                'routed_to': msg['routed_to_topic']
            }
            
            # Add source-specific fields
            if source.lower() == 'mongodb':
                event['collection_or_key'] = msg.get('collection', 'N/A')
                event['document_id'] = msg.get('document_id', 'N/A')
            elif source.lower() == 's3':
                event['collection_or_key'] = msg.get('object_key', 'N/A')
                event['file_size'] = msg.get('file_size', 0)
            
            formatted_events.append(event)
        
        return {
            "success": True,
            "source": source,
            "topic": topic,
            "events": formatted_events,
            "count": len(formatted_events)
        }
        
    except Exception as e:
        logger.error(f"Error fetching CDC events for {source}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
