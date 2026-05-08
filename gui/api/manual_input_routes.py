"""
Manual Input API Routes - Universal Data Ingestion Interface
Handles 4 input methods: file upload, text/JSON entry, URL fetch, database query
"""
from fastapi import APIRouter, HTTPException, File, UploadFile, Form, BackgroundTasks
from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List, Dict, Any, Literal
import os
import logging
import httpx
import json
import uuid
from pathlib import Path
from datetime import datetime
from io import BytesIO
import mimetypes

# Kafka integration
from kafka import KafkaProducer
from kafka.errors import KafkaError

# Local imports
from storage import MinIOClient
from database import db_manager
from app_config import config

logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize MinIO client
minio_client = MinIOClient()

# Initialize Kafka producer (lazily)
_kafka_producer = None

def get_kafka_producer():
    """Get or create Kafka producer"""
    global _kafka_producer
    if _kafka_producer is None:
        try:
            _kafka_producer = KafkaProducer(
                bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "127.0.0.1:9092"),
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                max_block_ms=5000  # Don't block forever if Kafka is down
            )
            logger.info("✓ Kafka producer initialized for manual input")
        except Exception as e:
            logger.warning(f"Kafka producer not available: {e}")
            _kafka_producer = None
    return _kafka_producer


# ============================================================================
# Pydantic Models
# ============================================================================

class ManualTextRequest(BaseModel):
    """Request for manual text/JSON input"""
    content: str = Field(..., description="Text or JSON content")
    label: str = Field(default="user_input", description="Label for this input")
    route_to: Literal["unstructured", "structured"] = Field(..., description="Routing destination")
    model_override: Optional[str] = Field(None, description="Override model for AI processing")
    domain: Literal["general", "finance", "healthcare"] = Field(default="general", description="Domain bucket")
    content_type: Literal["text", "json"] = Field(default="text", description="Content type")


class ManualURLRequest(BaseModel):
    """Request for URL fetch and ingest"""
    url: str = Field(..., description="Public URL to fetch")
    route_to: Literal["unstructured", "structured"] = Field(..., description="Routing destination")
    model_override: Optional[str] = Field(None, description="Override model for AI processing")
    domain: Literal["general", "finance", "healthcare"] = Field(default="general", description="Domain bucket")


class ManualQueryRequest(BaseModel):
    """Request for database query result ingestion"""
    source_type: Literal["postgresql", "mongodb", "mariadb", "s3"] = Field(..., description="Database type")
    connection_id: str = Field(..., description="Connection identifier")
    query: str = Field(..., description="SQL query or MongoDB filter (JSON string)")
    route_to: Literal["unstructured", "structured"] = Field(..., description="Routing destination")
    model_override: Optional[str] = Field(None, description="Override model for AI processing")
    domain: Literal["general", "finance", "healthcare"] = Field(default="general", description="Domain bucket")


class ManualInputResponse(BaseModel):
    """Response from manual input ingestion"""
    success: bool
    message: str
    ingested_items: List[Dict[str, Any]] = []
    errors: List[str] = []


# ============================================================================
# Helper Functions
# ============================================================================

def detect_file_type(filename: str, content_type: str) -> tuple[str, str]:
    """
    Detect file type and category from filename and content type
    Returns (file_type, category) where category is 'structured' or 'unstructured'
    """
    ext = Path(filename).suffix.lower()
    
    # Structured types
    structured_exts = {'.csv', '.parquet', '.json', '.xlsx', '.xls'}
    if ext in structured_exts:
        return ext[1:], "structured"
    
    # Image types
    if ext in {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff'}:
        return "image", "unstructured"
    
    # Document types
    if ext in {'.pdf', '.doc', '.docx', '.txt', '.rtf', '.odt'}:
        return "document", "unstructured"
    
    # Audio types
    if ext in {'.mp3', '.wav', '.m4a', '.flac', '.ogg', '.aac'}:
        return "audio", "unstructured"
    
    # Video types
    if ext in {'.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv'}:
        return "video", "unstructured"
    
    # Fallback to content type
    if content_type:
        if content_type.startswith('image/'):
            return "image", "unstructured"
        elif content_type.startswith('video/'):
            return "video", "unstructured"
        elif content_type.startswith('audio/'):
            return "audio", "unstructured"
        elif 'pdf' in content_type:
            return "pdf", "unstructured"
    
    # Default
    return "unknown", "unstructured"


def emit_to_kafka(topic: str, message: Dict[str, Any]) -> bool:
    """
    Emit message to Kafka topic
    Returns True if successful, False otherwise
    """
    try:
        producer = get_kafka_producer()
        if not producer:
            logger.warning("Kafka producer not available - message not emitted")
            return False
        
        future = producer.send(topic, value=message)
        producer.flush(timeout=5)
        
        logger.info(f"✓ Emitted to Kafka topic '{topic}': {message.get('bronze_minio_key', 'unknown')}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to emit to Kafka: {e}")
        return False


def upload_to_bronze(content: bytes, file_path: str) -> str:
    """
    Upload content to MinIO Bronze bucket
    Returns the MinIO key (path)
    """
    try:
        minio_client.upload_file_obj(
            bucket_name=config.minio_bronze_bucket,
            object_name=file_path,
            data=BytesIO(content),
            length=len(content)
        )
        logger.info(f"✓ Uploaded to MinIO Bronze: {file_path}")
        return file_path
        
    except Exception as e:
        logger.error(f"Failed to upload to MinIO: {e}")
        raise HTTPException(status_code=500, detail=f"MinIO upload failed: {str(e)}")


# ============================================================================
# API Endpoints
# ============================================================================

@router.post("/ingest/manual/files", response_model=ManualInputResponse)
async def ingest_manual_files(
    files: List[UploadFile] = File(...),
    route_to: List[str] = Form(...),  # One per file
    model_override: List[str] = Form(...),  # One per file, can be "none"
    domain: List[str] = Form(...)  # One per file
):
    """
    Accept multiple file uploads with per-file configuration
    Routes to MinIO Bronze (unstructured) or PostgreSQL (structured)
    """
    ingested_items = []
    errors = []
    
    try:
        for idx, file in enumerate(files):
            try:
                # Read file content
                content = await file.read()
                
                # Get per-file configuration
                file_route = route_to[idx] if idx < len(route_to) else "unstructured"
                file_model = model_override[idx] if idx < len(model_override) and model_override[idx] != "none" else None
                file_domain = domain[idx] if idx < len(domain) else "general"
                
                # Detect file type
                file_type, detected_category = detect_file_type(file.filename, file.content_type or "")
                
                # Generate unique file path
                timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                file_id = str(uuid.uuid4())[:8]
                file_path = f"{file_domain}/manual_input/{file_type}/{timestamp}_{file_id}_{file.filename}"
                
                if file_route == "unstructured":
                    # Upload to MinIO Bronze
                    minio_key = upload_to_bronze(content, file_path)
                    
                    # Emit to Kafka bronze-ready topic
                    kafka_message = {
                        "bronze_minio_key": minio_key,
                        "file_type": file_type,
                        "domain": file_domain,
                        "source_type": "manual_input",
                        "original_filename": file.filename,
                        "size_bytes": len(content),
                        "ingested_at": datetime.utcnow().isoformat(),
                        "model_override": file_model,
                        "user_routed": True
                    }
                    
                    emit_to_kafka("bronze-ready", kafka_message)
                    
                    ingested_items.append({
                        "filename": file.filename,
                        "status": "uploaded_to_bronze",
                        "minio_key": minio_key,
                        "size_bytes": len(content)
                    })
                    
                else:  # structured
                    # TODO: Parse and insert to PostgreSQL
                    # For now, still upload to Bronze but mark as structured
                    minio_key = upload_to_bronze(content, file_path)
                    
                    ingested_items.append({
                        "filename": file.filename,
                        "status": "uploaded_as_structured",
                        "minio_key": minio_key,
                        "note": "Structured data parsing not yet implemented"
                    })
                
            except Exception as e:
                logger.error(f"Failed to ingest file {file.filename}: {e}")
                errors.append(f"{file.filename}: {str(e)}")
        
        return ManualInputResponse(
            success=len(errors) == 0,
            message=f"Ingested {len(ingested_items)} of {len(files)} files",
            ingested_items=ingested_items,
            errors=errors
        )
        
    except Exception as e:
        logger.error(f"File ingestion failed: {e}")
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")


@router.post("/ingest/manual/text", response_model=ManualInputResponse)
async def ingest_manual_text(request: ManualTextRequest):
    """
    Accept raw text or JSON input and ingest
    Routes to MinIO Bronze (unstructured) or PostgreSQL (structured)
    """
    try:
        # Generate unique file path
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        file_id = str(uuid.uuid4())[:8]
        ext = "json" if request.content_type == "json" else "txt"
        filename = f"{request.label}_{timestamp}_{file_id}.{ext}"
        file_path = f"{request.domain}/manual_input/text/{filename}"
        
        # Convert content to bytes
        content_bytes = request.content.encode('utf-8')
        
        if request.route_to == "unstructured":
            # Upload to MinIO Bronze
            minio_key = upload_to_bronze(content_bytes, file_path)
            
            # Emit to Kafka
            kafka_message = {
                "bronze_minio_key": minio_key,
                "file_type": "text",
                "domain": request.domain,
                "source_type": "manual_input",
                "original_filename": filename,
                "size_bytes": len(content_bytes),
                "ingested_at": datetime.utcnow().isoformat(),
                "model_override": request.model_override,
                "user_routed": True
            }
            
            emit_to_kafka("bronze-ready", kafka_message)
            
            return ManualInputResponse(
                success=True,
                message="Text ingested to Bronze",
                ingested_items=[{
                    "filename": filename,
                    "minio_key": minio_key,
                    "size_bytes": len(content_bytes)
                }]
            )
            
        else:  # structured
            # Validate JSON if content_type is json
            if request.content_type == "json":
                try:
                    json.loads(request.content)
                except json.JSONDecodeError as e:
                    raise HTTPException(status_code=400, detail=f"Invalid JSON: {str(e)}")
            
            # TODO: Insert to PostgreSQL
            minio_key = upload_to_bronze(content_bytes, file_path)
            
            return ManualInputResponse(
                success=True,
                message="Structured text ingested (PostgreSQL insert not yet implemented)",
                ingested_items=[{
                    "filename": filename,
                    "minio_key": minio_key,
                    "note": "Structured data parsing pending"
                }]
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Text ingestion failed: {e}")
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")


@router.post("/ingest/manual/url", response_model=ManualInputResponse)
async def ingest_manual_url(request: ManualURLRequest):
    """
    Fetch content from URL server-side and ingest
    Supports images, documents, JSON APIs, etc.
    """
    try:
        # Fetch URL content
        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
            response = await client.get(request.url)
            response.raise_for_status()
            
            content = response.content
            content_type = response.headers.get("content-type", "")
            
            # Extract filename from URL or generate one
            url_path = Path(request.url)
            filename = url_path.name or "downloaded_file"
            
            # Add extension if missing
            if not Path(filename).suffix and content_type:
                ext = mimetypes.guess_extension(content_type.split(';')[0])
                if ext:
                    filename += ext
            
            # Detect file type
            file_type, detected_category = detect_file_type(filename, content_type)
            
            # Generate unique file path
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            file_id = str(uuid.uuid4())[:8]
            file_path = f"{request.domain}/manual_input/{file_type}/{timestamp}_{file_id}_{filename}"
            
            if request.route_to == "unstructured":
                # Upload to MinIO Bronze
                minio_key = upload_to_bronze(content, file_path)
                
                # Emit to Kafka
                kafka_message = {
                    "bronze_minio_key": minio_key,
                    "file_type": file_type,
                    "domain": request.domain,
                    "source_type": "manual_input_url",
                    "original_filename": filename,
                    "source_url": request.url,
                    "size_bytes": len(content),
                    "ingested_at": datetime.utcnow().isoformat(),
                    "model_override": request.model_override,
                    "user_routed": True
                }
                
                emit_to_kafka("bronze-ready", kafka_message)
                
                return ManualInputResponse(
                    success=True,
                    message=f"URL content ingested ({len(content)} bytes)",
                    ingested_items=[{
                        "url": request.url,
                        "filename": filename,
                        "minio_key": minio_key,
                        "size_bytes": len(content)
                    }]
                )
                
            else:  # structured
                # TODO: Parse and insert to PostgreSQL
                minio_key = upload_to_bronze(content, file_path)
                
                return ManualInputResponse(
                    success=True,
                    message="URL content ingested as structured",
                    ingested_items=[{
                        "url": request.url,
                        "minio_key": minio_key,
                        "note": "Structured data parsing pending"
                    }]
                )
        
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"Failed to fetch URL: {str(e)}")
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="URL fetch timeout")
    except Exception as e:
        logger.error(f"URL ingestion failed: {e}")
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")


@router.post("/ingest/manual/query", response_model=ManualInputResponse)
async def ingest_manual_query(request: ManualQueryRequest):
    """
    Execute query against connected database and ingest results
    Supports PostgreSQL, MongoDB, MariaDB, AWS S3
    """
    try:
        # TODO: Implement query execution against different sources
        # For now, return placeholder response
        
        return ManualInputResponse(
            success=False,
            message="Database query ingestion not yet implemented",
            errors=["Query execution feature is under development"]
        )
        
    except Exception as e:
        logger.error(f"Query ingestion failed: {e}")
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")


# ============================================================================
# Health Check
# ============================================================================

@router.get("/ingest/manual/status")
async def get_manual_input_status():
    """Check status of manual input infrastructure"""
    
    # Check MinIO
    minio_ok = False
    try:
        minio_client.client.bucket_exists(config.minio_bronze_bucket)
        minio_ok = True
    except:
        pass
    
    # Check Kafka
    kafka_ok = get_kafka_producer() is not None
    
    return {
        "service": "manual_input",
        "status": "operational" if (minio_ok and kafka_ok) else "degraded",
        "components": {
            "minio": "connected" if minio_ok else "unavailable",
            "kafka": "connected" if kafka_ok else "unavailable"
        }
    }
