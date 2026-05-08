"""
Bronze Ready Emitter - API Routes
==================================
Provides REST API endpoints for monitoring and controlling the bronze_ready_emitter.py service.

Endpoints:
    GET  /api/bronze-ready/status       - Check emitter status
    GET  /api/bronze-ready/stats        - Get routing statistics
    GET  /api/bronze-ready/items        - List items in bronze-ready queue
    GET  /api/bronze-ready/media-pending - List media files awaiting trigger
    POST /api/bronze-ready/trigger      - Manually trigger media file processing
    POST /api/bronze-ready/start        - Start the emitter service
    POST /api/bronze-ready/stop         - Stop the emitter service
"""

import json
import logging
import os
import subprocess
import psutil
import socket
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
READY_TOPIC = "bronze-ready"
MEDIA_PENDING_TOPIC = "bronze-media-pending"
EMITTER_SCRIPT = Path(__file__).parent.parent.parent / "Kafka Integration" / "bronze_ready_emitter.py"
EMITTER_PROCESS_NAME = "bronze_ready_emitter.py"

# Global process tracking
_emitter_process: Optional[subprocess.Popen] = None


# ---------------------------------------------------------------------------
# Request/Response Models
# ---------------------------------------------------------------------------
class TriggerMediaRequest(BaseModel):
    """Request to trigger processing of a media file"""
    object_key: str
    file_type: str
    source: str


class StartEmitterResponse(BaseModel):
    """Response from starting emitter"""
    success: bool
    message: str
    pid: Optional[int] = None


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------
def _kafka_available() -> bool:
    """Check if Kafka is available"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        result = s.connect_ex(("localhost", 9092))
        s.close()
        return result == 0
    except Exception:
        return False


def _get_emitter_process() -> Optional[psutil.Process]:
    """Find the bronze_ready_emitter.py process"""
    try:
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = proc.info.get('cmdline', [])
                if cmdline and any('bronze_ready_emitter.py' in str(arg) for arg in cmdline):
                    return psutil.Process(proc.info['pid'])
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    except Exception as e:
        logger.error(f"Error finding emitter process: {e}")
    return None


def _consume_topic_messages(topic: str, max_messages: int = 100) -> List[Dict[str, Any]]:
    """Consume recent messages from a Kafka topic"""
    messages = []
    try:
        from kafka import KafkaConsumer
        from kafka.errors import KafkaError
        
        consumer = KafkaConsumer(
            topic,
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS.split(','),
            group_id=f'gui-consumer-{topic}-{int(datetime.utcnow().timestamp())}',
            auto_offset_reset='earliest',
            enable_auto_commit=False,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            consumer_timeout_ms=5000  # 5 second timeout
        )
        
        for message in consumer:
            messages.append({
                'key': message.key.decode('utf-8') if message.key else None,
                'value': message.value,
                'partition': message.partition,
                'offset': message.offset,
                'timestamp': datetime.fromtimestamp(message.timestamp / 1000.0).isoformat() if message.timestamp else None
            })
            
            if len(messages) >= max_messages:
                break
        
        consumer.close()
    except Exception as e:
        logger.error(f"Error consuming from topic {topic}: {e}")
    
    return messages


def _publish_to_ready_topic(item: Dict[str, Any]) -> bool:
    """Publish a message to bronze-ready topic (for manual trigger)"""
    try:
        from kafka import KafkaProducer
        
        producer = KafkaProducer(
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS.split(','),
            value_serializer=lambda v: json.dumps(v, default=str).encode('utf-8'),
            key_serializer=lambda k: k.encode('utf-8') if k else None,
            acks='all'
        )
        
        key = item.get('object_key', '')
        future = producer.send(READY_TOPIC, key=key, value=item)
        future.get(timeout=5)
        
        producer.flush()
        producer.close()
        return True
    except Exception as e:
        logger.error(f"Error publishing to {READY_TOPIC}: {e}")
        return False


# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------

@router.get("/status")
async def get_emitter_status():
    """
    Get the status of the bronze ready emitter service.
    
    Returns:
        - running: bool - Whether the emitter process is running
        - pid: int - Process ID (if running)
        - uptime: str - How long it's been running
        - kafka_available: bool - Whether Kafka is reachable
    """
    process = _get_emitter_process()
    
    if process:
        try:
            create_time = datetime.fromtimestamp(process.create_time())
            uptime_seconds = (datetime.now() - create_time).total_seconds()
            uptime_str = f"{int(uptime_seconds // 3600)}h {int((uptime_seconds % 3600) // 60)}m"
            
            return {
                "running": True,
                "pid": process.pid,
                "uptime": uptime_str,
                "uptime_seconds": int(uptime_seconds),
                "cpu_percent": process.cpu_percent(interval=0.1),
                "memory_mb": process.memory_info().rss / (1024 * 1024),
                "kafka_available": _kafka_available()
            }
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    
    return {
        "running": False,
        "pid": None,
        "uptime": None,
        "kafka_available": _kafka_available()
    }


@router.get("/stats")
async def get_emitter_stats():
    """
    Get routing statistics from the emitter.
    
    Note: Currently returns mock data. In production, this should read from
    a shared state file or database that the emitter writes to.
    """
    process = _get_emitter_process()
    
    if not process:
        return {
            "available": False,
            "message": "Emitter is not running"
        }
    
    # TODO: Implement shared state file or Redis for real-time stats
    # For now, return estimated stats based on topic message counts
    try:
        from kafka import KafkaConsumer
        
        # Get message counts from topics
        consumer = KafkaConsumer(
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS.split(','),
            group_id=f'stats-consumer-{int(datetime.utcnow().timestamp())}'
        )
        
        ready_partitions = consumer.partitions_for_topic(READY_TOPIC) or set()
        media_partitions = consumer.partitions_for_topic(MEDIA_PENDING_TOPIC) or set()
        
        consumer.close()
        
        return {
            "available": True,
            "running": True,
            "ready_queue_size": len(ready_partitions) * 10,  # Estimated
            "media_pending_size": len(media_partitions) * 5,  # Estimated
            "total_processed": "N/A",  # Would come from shared state
            "errors": 0
        }
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return {
            "available": False,
            "message": str(e)
        }


@router.get("/items")
async def get_ready_items(limit: int = Query(50, ge=1, le=500)):
    """
    List items in the bronze-ready queue.
    These are files ready for automatic AI processing (PDF, TXT, images).
    """
    if not _kafka_available():
        raise HTTPException(status_code=503, detail="Kafka is not available")
    
    try:
        messages = _consume_topic_messages(READY_TOPIC, max_messages=limit)
        
        # Transform to user-friendly format
        items = []
        for msg in messages:
            value = msg['value']
            items.append({
                'object_key': value.get('object_key', ''),
                'file_type': value.get('file_type', 'unknown'),
                'source': value.get('source', 'unknown'),
                'timestamp': value.get('timestamp', msg['timestamp']),
                'bronze_minio_key': value.get('bronze_minio_key', ''),
                'metadata': value.get('metadata', {}),
                'status': 'ready'
            })
        
        return {
            "success": True,
            "items": items,
            "count": len(items),
            "topic": READY_TOPIC
        }
    except Exception as e:
        logger.error(f"Error fetching ready items: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/media-pending")
async def get_media_pending_items(limit: int = Query(50, ge=1, le=500)):
    """
    List media files (audio/video) awaiting user trigger.
    These require manual approval before processing.
    """
    if not _kafka_available():
        raise HTTPException(status_code=503, detail="Kafka is not available")
    
    try:
        messages = _consume_topic_messages(MEDIA_PENDING_TOPIC, max_messages=limit)
        
        # Transform to user-friendly format
        items = []
        for msg in messages:
            value = msg['value']
            items.append({
                'object_key': value.get('object_key', ''),
                'file_type': value.get('file_type', 'unknown'),
                'source': value.get('source', 'unknown'),
                'timestamp': value.get('timestamp', msg['timestamp']),
                'bronze_minio_key': value.get('bronze_minio_key', ''),
                'metadata': value.get('metadata', {}),
                'status': 'pending',
                'kafka_key': msg['key']
            })
        
        return {
            "success": True,
            "items": items,
            "count": len(items),
            "topic": MEDIA_PENDING_TOPIC
        }
    except Exception as e:
        logger.error(f"Error fetching media pending items: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/trigger")
async def trigger_media_processing(request: TriggerMediaRequest):
    """
    Manually trigger processing of a media file from bronze-media-pending.
    Moves the item to bronze-ready topic.
    """
    if not _kafka_available():
        raise HTTPException(status_code=503, detail="Kafka is not available")
    
    try:
        # Create message for bronze-ready topic
        item = {
            'source': request.source,
            'file_type': request.file_type,
            'object_key': request.object_key,
            'timestamp': datetime.utcnow().isoformat(),
            'triggered_manually': True,
            'triggered_at': datetime.utcnow().isoformat()
        }
        
        success = _publish_to_ready_topic(item)
        
        if success:
            return {
                "success": True,
                "message": f"Media file {request.object_key} triggered for processing",
                "object_key": request.object_key
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to publish to ready topic")
            
    except Exception as e:
        logger.error(f"Error triggering media processing: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/start")
async def start_emitter():
    """
    Start the bronze ready emitter service as a background process.
    """
    global _emitter_process
    
    # Check if already running
    existing = _get_emitter_process()
    if existing:
        return {
            "success": False,
            "message": f"Emitter is already running (PID: {existing.pid})",
            "pid": existing.pid
        }
    
    # Check if script exists
    if not EMITTER_SCRIPT.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Emitter script not found at {EMITTER_SCRIPT}"
        )
    
    # Check Kafka availability
    if not _kafka_available():
        raise HTTPException(
            status_code=503,
            detail="Kafka is not available. Please start Kafka first."
        )
    
    try:
        # Start the emitter as a background process
        log_dir = EMITTER_SCRIPT.parent / "logs"
        log_dir.mkdir(exist_ok=True)
        
        log_file = log_dir / f"bronze_emitter_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        
        if os.name == 'nt':  # Windows
            # Use CREATE_NEW_PROCESS_GROUP to allow graceful shutdown
            _emitter_process = subprocess.Popen(
                ['python', str(EMITTER_SCRIPT)],
                stdout=open(log_file, 'w'),
                stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                cwd=str(EMITTER_SCRIPT.parent)
            )
        else:  # Linux/Mac
            _emitter_process = subprocess.Popen(
                ['python3', str(EMITTER_SCRIPT)],
                stdout=open(log_file, 'w'),
                stderr=subprocess.STDOUT,
                cwd=str(EMITTER_SCRIPT.parent)
            )
        
        # Wait a moment to ensure it started
        import time
        time.sleep(2)
        
        # Verify it's running
        if _emitter_process.poll() is None:
            return {
                "success": True,
                "message": "Bronze Ready Emitter started successfully",
                "pid": _emitter_process.pid,
                "log_file": str(log_file)
            }
        else:
            return {
                "success": False,
                "message": "Emitter process exited immediately. Check logs.",
                "log_file": str(log_file)
            }
            
    except Exception as e:
        logger.error(f"Error starting emitter: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop")
async def stop_emitter():
    """
    Stop the bronze ready emitter service gracefully.
    """
    process = _get_emitter_process()
    
    if not process:
        return {
            "success": False,
            "message": "Emitter is not running"
        }
    
    try:
        # Try graceful shutdown first (SIGTERM)
        process.terminate()
        
        # Wait up to 10 seconds for graceful shutdown
        try:
            process.wait(timeout=10)
            return {
                "success": True,
                "message": "Emitter stopped gracefully",
                "pid": process.pid
            }
        except psutil.TimeoutExpired:
            # Force kill if it doesn't stop
            process.kill()
            return {
                "success": True,
                "message": "Emitter force-stopped (did not respond to graceful shutdown)",
                "pid": process.pid
            }
            
    except Exception as e:
        logger.error(f"Error stopping emitter: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """
    Health check endpoint for the bronze ready system.
    """
    emitter_running = _get_emitter_process() is not None
    kafka_available = _kafka_available()
    
    healthy = emitter_running and kafka_available
    
    return {
        "healthy": healthy,
        "emitter_running": emitter_running,
        "kafka_available": kafka_available,
        "message": "All systems operational" if healthy else "Some services unavailable"
    }
