"""
AI Processing Control API Routes
Allows users to trigger and monitor AI processing from the UI
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import os
import logging
from datetime import datetime

# Local imports
from storage import MinIOClient
from app_config import config

logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize clients
minio_client = MinIOClient()


# ============================================================================
# Pydantic Models
# ============================================================================

class ProcessingTriggerRequest(BaseModel):
    """Request to trigger AI processing for files"""
    file_keys: List[str] = Field(..., description="List of Bronze MinIO object keys")
    model_override: Optional[str] = Field(None, description="Override AI model (null = use default)")
    priority: str = Field(default="normal", description="Processing priority: high, normal, low")


class ProcessingJobResponse(BaseModel):
    """Response with processing job details"""
    id: str
    file_key: str
    status: str  # pending, processing, success, failed
    model_used: Optional[str]
    started_at: Optional[str]
    completed_at: Optional[str]
    duration_seconds: Optional[float]
    error_message: Optional[str]


class BronzeFileInfo(BaseModel):
    """Bronze file information"""
    object_key: str
    file_type: str
    size_bytes: int
    uploaded_at: str
    source: str


# ============================================================================
# API Endpoints
# ============================================================================

@router.get("/bronze/files")
async def get_bronze_files(limit: int = 100):
    """
    Get list of files in Bronze bucket that haven't been processed yet
    """
    try:
        # List objects from Bronze bucket using StorageManager API
        objects = minio_client.list_objects(
            layer="bronze",
            domain=None,
            prefix=""
        )
        
        files = []
        for obj in objects[:limit]:
            # Detect file type from extension
            ext = obj['object_name'].split('.')[-1].lower() if '.' in obj['object_name'] else 'unknown'
            
            file_type = 'unknown'
            if ext in ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp']:
                file_type = 'image'
            elif ext in ['pdf']:
                file_type = 'pdf'
            elif ext in ['txt', 'doc', 'docx', 'parquet']:
                file_type = 'document'
            elif ext in ['mp3', 'wav', 'm4a']:
                file_type = 'audio'
            elif ext in ['mp4', 'avi', 'mov', 'mkv']:
                file_type = 'video'
                
            # Extract source from path (e.g., "general/mongodb/..." -> "mongodb")
            path_parts = obj['object_name'].split('/')
            source = path_parts[1] if len(path_parts) > 1 else 'CDC'
            
            files.append({
                "object_key": obj['object_name'],
                "file_type": file_type,
                "size_bytes": obj.get('size', 0),
                "uploaded_at": obj.get('last_modified').isoformat() if obj.get('last_modified') else None,
                "source": source
            })
        
        return {"success": True, "files": files, "total": len(files)}
        
    except Exception as e:
        logger.error(f"Failed to list Bronze files: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list Bronze files: {str(e)}")


@router.post("/silver/processing/trigger")
async def trigger_processing(request: ProcessingTriggerRequest, background_tasks: BackgroundTasks):
    """
    Trigger AI processing for selected Bronze files
    Calls ai_processor directly without Kafka
    """
    try:
        import sys
        import threading
        from pathlib import Path
        
        # Import ai_processor module
        ai_processor_dir = Path(__file__).resolve().parent.parent.parent / "ai processing"
        if str(ai_processor_dir) not in sys.path:
            sys.path.insert(0, str(ai_processor_dir))
        
        # Get list of unprocessed files if no specific files requested
        files_to_process = []
        
        if request.file_keys:
            files_to_process = request.file_keys
        else:
            # Get all Bronze files not yet in silver_assets
            import psycopg2
            conn = psycopg2.connect(
                host='localhost',
                port=5432,
                database='syniqai_metadata',
                user='syniqai_user',
                password='syniqai_password'
            )
            cur = conn.cursor()
            
            # Get processed files
            cur.execute("SELECT DISTINCT bronze_minio_key FROM silver_assets")
            processed = {row[0] for row in cur.fetchall()}
            cur.close()
            conn.close()
            
            # List Bronze bucket
            from minio import Minio
            minio_client = Minio('localhost:9000', 'admin', 'password123', secure=False)
            bronze_objects = minio_client.list_objects('syniqai-bronze', recursive=True)
            
            for obj in bronze_objects:
                if obj.object_name not in processed:
                    files_to_process.append(obj.object_name)
        
        # Build messages and trigger processing in background
        def process_files():
            try:
                from ai_processor import AIProcessor
                processor = AIProcessor()
                
                logger.info(f"[MEDIA GATE] Triggered processing for {len(files_to_process)} Bronze files")
                
                for file_key in files_to_process:
                    filename = file_key.split("/")[-1]
                    file_type = filename.rsplit(".", 1)[-1].lower() if "." in filename else "unknown"
                    source = "mongodb" if "/mongodb/" in file_key else "s3"
                    
                    message = {
                        "bronze_minio_key": file_key,
                        "filename": filename,
                        "file_type": file_type,
                        "source": source,
                        "size_bytes": 0
                    }
                    
                    processor.process_message(message)
                    
            except Exception as e:
                logger.error(f"Background processing failed: {e}")
        
        # Start background processing
        thread = threading.Thread(target=process_files, daemon=True)
        thread.start()
        
        return {
            "jobs_created": len(files_to_process),
            "message": f"Processing {len(files_to_process)} files from Bronze"
        }
        
    except Exception as e:
        logger.error(f"Failed to trigger processing: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to trigger processing: {str(e)}")


@router.get("/silver/processing/status")
async def get_processing_status():
    """
    Get AI processor status and queue information.
    Used by AIProcessing.jsx to monitor processing activity.
    """
    try:
        import psutil
        
        # Check if AI processor is running
        processor_running = False
        processor_pid = None
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = proc.info.get('cmdline', [])
                if cmdline and any('ai_processor.py' in str(arg) for arg in cmdline):
                    processor_running = True
                    processor_pid = proc.info['pid']
                    break
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        # Get recent jobs from PostgreSQL
        try:
            import psycopg2
            from psycopg2.extras import RealDictCursor
            
            conn = psycopg2.connect(
                host=os.getenv("POSTGRES_HOST", "localhost"),
                port=os.getenv("POSTGRES_PORT", "5432"),
                database=os.getenv("POSTGRES_DB", "syniqai_metadata"),
                user=os.getenv("POSTGRES_USER", "syniqai_user"),
                password=os.getenv("POSTGRES_PASSWORD", "syniqai_password")
            )
            
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute("""
                SELECT 
                    id,
                    bronze_minio_key as file_key,
                    file_type,
                    ai_model_used,
                    extraction_status as status,
                    processed_at,
                    ai_confidence_score
                FROM silver_assets
                WHERE processed_at IS NOT NULL
                ORDER BY processed_at DESC
                LIMIT 20
            """)
            
            recent_jobs = [dict(job) for job in cursor.fetchall()]
            cursor.close()
            conn.close()
        except Exception as e:
            logger.warning(f"Could not get recent jobs: {e}")
            recent_jobs = []
        
        return {
            "processor": {
                "status": "running" if processor_running else "stopped",
                "pid": processor_pid
            },
            "recent_jobs": recent_jobs,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get processing status: {e}")
        return {
            "processor": {"status": "unknown", "error": str(e)},
            "recent_jobs": [],
            "timestamp": datetime.utcnow().isoformat()
        }


@router.get("/silver/processing/routing-config")
async def get_routing_config():
    """
    Get AI model routing configuration.
    Shows which model is used for each file type.
    """
    return {
        "config": {
            "vision_model": "qwen/qwen3-vl-8b-thinking",
            "text_model": "qwen/qwen3-8b",
            "audio_model": "openai/gpt-audio-mini",
            "video_audio_model": "openai/gpt-audio-mini",
            "routing_rules": {
                "image": {
                    "model": "qwen/qwen3-vl-8b-thinking",
                    "extensions": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp"]
                },
                "video": {
                    "model": "qwen/qwen3-vl-8b-thinking",
                    "extensions": [".mp4", ".avi", ".mov", ".wmv", ".mkv", ".webm"]
                },
                "audio": {
                    "model": "openai/gpt-audio-mini",
                    "extensions": [".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a"]
                },
                "document": {
                    "model": "qwen/qwen3-8b",
                    "extensions": [".pdf", ".doc", ".docx", ".txt"]
                },
                "text": {
                    "model": "qwen/qwen3-8b",
                    "extensions": [".txt", ".csv", ".json", ".log", ".md"]
                }
            }
        },
        "updated_at": datetime.utcnow().isoformat(),
        "source": "ai_processor.py"
    }


@router.get("/silver/processing/jobs")
async def get_processing_jobs(limit: int = 50):
    """
    Get recent processing jobs status
    Queries silver_assets table
    """
    try:
        # Query silver_assets for recent processing jobs
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        conn = psycopg2.connect(
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=os.getenv("POSTGRES_PORT", "5432"),
            database=os.getenv("POSTGRES_DB", "syniqai_metadata"),
            user=os.getenv("POSTGRES_USER", "syniqai_user"),
            password=os.getenv("POSTGRES_PASSWORD", "syniqai_password")
        )
        
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT 
                id,
                bronze_minio_key as file_key,
                extraction_status as status,
                ai_model_used as model_used,
                processed_at as started_at,
                processed_at as completed_at,
                file_type
            FROM silver_assets
            ORDER BY processed_at DESC
            LIMIT %s
        """, (limit,))
        
        rows = cursor.fetchall()
        
        jobs = []
        for row in rows:
            # Map status
            status_map = {
                'success': 'success',
                'failed': 'failed',
                'pending': 'pending',
                None: 'processing'
            }
            
            jobs.append({
                "id": row['id'],
                "file_key": row['file_key'],
                "status": status_map.get(row['status'], 'processing'),
                "model_used": row['model_used'],
                "started_at": row['started_at'].isoformat() if row['started_at'] else None,
                "completed_at": row['completed_at'].isoformat() if row['completed_at'] else None,
                "duration_seconds": None,
                "error_message": None
            })
        
        cursor.close()
        conn.close()
        
        return {
            "jobs": jobs,
            "processor_status": "running"
        }
        
    except Exception as e:
        logger.error(f"Failed to fetch processing jobs: {e}")
        # Return empty list instead of error to avoid breaking UI
        return {
            "jobs": [],
            "processor_status": "unknown"
        }
