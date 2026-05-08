"""
Silver Assets Storage Layer
===========================
Production-grade PostgreSQL + MinIO access layer for silver_assets table.

Features:
- Async PostgreSQL access with SQLAlchemy + asyncpg
- Presigned MinIO download URLs (1-hour expiry)
- Connection pooling and error handling
- Type-safe asset model

Usage:
    from silver_store import insert_silver_asset, get_presigned_download_url, list_assets
    
    # Insert new asset
    asset_id = await insert_silver_asset({
        "source": "s3",
        "file_type": "image",
        "bronze_minio_key": "syniqai-bronze/general/s3/image/photo.jpg",
        "silver_minio_key": "syniqai-silver/image/20260329_photo.jpg.json",
        ...
    })
    
    # Get presigned download URL (for original file in Bronze)
    download_url = await get_presigned_download_url(asset_id)
    
    # List assets with filters
    assets = await list_assets(file_type="image", status="success", limit=20)
"""

import os
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from uuid import UUID

# SQLAlchemy async
from sqlalchemy import Column, String, Float, BigInteger, Text, Integer
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID, TIMESTAMP
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.future import select
from sqlalchemy.orm import declarative_base

# MinIO
from minio import Minio
from minio.error import S3Error

# Environment
from dotenv import load_dotenv
from pathlib import Path

# Load .env
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_path)

logger = logging.getLogger(__name__)

# ============================================================================
# Configuration
# ============================================================================

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://syniqai_user:syniqai_password@localhost:5432/syniqai_metadata"
)

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "admin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "password123")
MINIO_SECURE = os.getenv("MINIO_SECURE", "false").lower() == "true"

# ============================================================================
# SQLAlchemy ORM Model
# ============================================================================

Base = declarative_base()

class SilverAsset(Base):
    """SQLAlchemy model for silver_assets table"""
    __tablename__ = "silver_assets"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()")
    source = Column(String(255))
    file_type = Column(String(50))
    bronze_minio_key = Column(String(500), nullable=False)
    silver_minio_key = Column(String(500))
    processed_at = Column(TIMESTAMP(timezone=True))
    ai_model_used = Column(String(255))
    extraction_status = Column(String(50), default="pending")
    ai_confidence_score = Column(Float)
    file_size_bytes = Column(BigInteger)
    content_tags = Column(JSONB)
    summary = Column(Text)
    created_at = Column(TIMESTAMP(timezone=True), server_default="NOW()")
    updated_at = Column(TIMESTAMP(timezone=True), server_default="NOW()")
    
    # Block 2 additions
    model_was_overridden = Column(String(50))  # Note: Might be BOOLEAN in actual schema
    business_domain = Column(String(100))
    manual_ingestion = Column(String(50))  # Note: Might be BOOLEAN in actual schema

    def to_dict(self) -> Dict[str, Any]:
        """Convert ORM object to dictionary"""
        return {
            "id": str(self.id),
            "source": self.source,
            "file_type": self.file_type,
            "bronze_minio_key": self.bronze_minio_key,
            "silver_minio_key": self.silver_minio_key,
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
            "ai_model_used": self.ai_model_used,
            "extraction_status": self.extraction_status,
            "ai_confidence_score": self.ai_confidence_score,
            "file_size_bytes": self.file_size_bytes,
            "content_tags": self.content_tags,
            "summary": self.summary,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "model_was_overridden": self.model_was_overridden,
            "business_domain": self.business_domain,
            "manual_ingestion": self.manual_ingestion,
        }

# ============================================================================
# Database Engine & Session
# ============================================================================

# Create async engine with connection pooling
engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # Set to True for SQL logging
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=3600,  # Recycle connections after 1 hour
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# ============================================================================
# MinIO Client
# ============================================================================

_minio_client: Optional[Minio] = None

def get_minio_client() -> Minio:
    """Get or create MinIO client (singleton pattern)"""
    global _minio_client
    if _minio_client is None:
        _minio_client = Minio(
            MINIO_ENDPOINT,
            access_key=MINIO_ACCESS_KEY,
            secret_key=MINIO_SECRET_KEY,
            secure=MINIO_SECURE
        )
        logger.info(f"✓ MinIO client initialized: {MINIO_ENDPOINT}")
    return _minio_client

# ============================================================================
# Core Functions
# ============================================================================

async def insert_silver_asset(event: Dict[str, Any]) -> str:
    """
    Insert a new silver asset record.
    
    Args:
        event: Dict containing asset metadata (source, file_type, paths, etc.)
        
    Returns:
        str: UUID of the newly created asset
        
    Example:
        asset_id = await insert_silver_asset({
            "source": "s3",
            "file_type": "image",
            "bronze_minio_key": "syniqai-bronze/general/s3/image/photo.jpg",
            "silver_minio_key": "syniqai-silver/image/20260329_photo.jpg.json",
            "ai_model_used": "qwen/qwen3-vl-8b-thinking",
            "extraction_status": "success",
            "processed_at": datetime.utcnow(),
            "file_size_bytes": 245678,
            "ai_confidence_score": 0.95,
            "content_tags": {"objects": ["cat", "sofa"], "scene": "living room"},
            "summary": "A cat sitting on a sofa in a cozy living room",
        })
    """
    async with AsyncSessionLocal() as session:
        try:
            # Create new asset
            new_asset = SilverAsset(
                source=event.get("source"),
                file_type=event.get("file_type"),
                bronze_minio_key=event["bronze_minio_key"],  # Required
                silver_minio_key=event.get("silver_minio_key"),
                processed_at=event.get("processed_at"),
                ai_model_used=event.get("ai_model_used"),
                extraction_status=event.get("extraction_status", "pending"),
                ai_confidence_score=event.get("ai_confidence_score"),
                file_size_bytes=event.get("file_size_bytes"),
                content_tags=event.get("content_tags"),
                summary=event.get("summary"),
                model_was_overridden=event.get("model_was_overridden"),
                business_domain=event.get("business_domain"),
                manual_ingestion=event.get("manual_ingestion"),
            )
            
            session.add(new_asset)
            await session.commit()
            await session.refresh(new_asset)
            
            asset_id = str(new_asset.id)
            logger.info(f"✓ Inserted silver_asset: {asset_id} ({event.get('file_type')}, {event.get('extraction_status')})")
            
            return asset_id
            
        except Exception as e:
            await session.rollback()
            logger.error(f"✗ Failed to insert silver_asset: {e}")
            raise


async def get_presigned_download_url(asset_id: str, expiry_hours: int = 1) -> str:
    """
    Get a presigned download URL for the ORIGINAL file in Bronze storage.
    
    This is what users download - the raw file, not the AI-processed JSON.
    URL expires after expiry_hours (default: 1 hour).
    
    Args:
        asset_id: UUID of the asset
        expiry_hours: URL expiry time in hours (default: 1)
        
    Returns:
        str: Presigned MinIO URL with Content-Disposition: attachment header
        
    Raises:
        ValueError: If asset not found or bronze_minio_key is invalid
        
    Example:
        url = await get_presigned_download_url("123e4567-e89b-12d3-a456-426614174000")
        # Returns: http://localhost:9000/syniqai-bronze/general/s3/image/photo.jpg?X-Amz-...
    """
    async with AsyncSessionLocal() as session:
        try:
            # Query for the asset
            result = await session.execute(
                select(SilverAsset).where(SilverAsset.id == UUID(asset_id))
            )
            asset = result.scalar_one_or_none()
            
            if not asset:
                raise ValueError(f"Asset not found: {asset_id}")
            
            if not asset.bronze_minio_key:
                raise ValueError(f"Asset {asset_id} has no bronze_minio_key")
            
            # Parse bucket and object key from bronze_minio_key
            # Format: "syniqai-bronze/general/s3/image/photo.jpg"
            # We need: bucket="syniqai-bronze", object="general/s3/image/photo.jpg"
            parts = asset.bronze_minio_key.split("/", 1)
            if len(parts) != 2:
                raise ValueError(f"Invalid bronze_minio_key format: {asset.bronze_minio_key}")
            
            bucket_name = parts[0]
            object_name = parts[1]
            
            # Get MinIO client
            minio_client = get_minio_client()
            
            # Check if object exists
            try:
                minio_client.stat_object(bucket_name, object_name)
            except S3Error as e:
                if e.code == "NoSuchKey":
                    raise ValueError(f"File not found in MinIO: {asset.bronze_minio_key}")
                raise
            
            # Generate presigned URL with Content-Disposition header to force download
            presigned_url = minio_client.presigned_get_object(
                bucket_name,
                object_name,
                expires=timedelta(hours=expiry_hours),
                response_headers={
                    "response-content-disposition": f'attachment; filename="{os.path.basename(object_name)}"'
                }
            )
            
            logger.info(f"✓ Generated presigned URL for asset {asset_id} (expires in {expiry_hours}h)")
            return presigned_url
            
        except ValueError:
            # Re-raise ValueError as-is (asset not found, invalid key, etc.)
            raise
        except Exception as e:
            logger.error(f"✗ Failed to generate presigned URL for asset {asset_id}: {e}")
            raise


async def list_assets(
    file_type: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    """
    List silver assets with optional filters.
    
    Args:
        file_type: Filter by file_type (image, pdf, txt, etc.)
        status: Filter by extraction_status (pending, success, failed)
        limit: Maximum number of results (default: 20)
        offset: Offset for pagination (default: 0)
        
    Returns:
        List[Dict]: List of asset dictionaries
        
    Example:
        # Get recent successful image processing
        images = await list_assets(file_type="image", status="success", limit=10)
        
        # Get all pending assets
        pending = await list_assets(status="pending", limit=50)
    """
    async with AsyncSessionLocal() as session:
        try:
            # Build query
            query = select(SilverAsset)
            
            # Apply filters
            if file_type:
                query = query.where(SilverAsset.file_type == file_type)
            if status:
                query = query.where(SilverAsset.extraction_status == status)
            
            # Order by processed_at DESC (most recent first)
            query = query.order_by(SilverAsset.processed_at.desc().nullslast())
            
            # Apply pagination
            query = query.limit(limit).offset(offset)
            
            # Execute
            result = await session.execute(query)
            assets = result.scalars().all()
            
            # Convert to dicts
            assets_list = [asset.to_dict() for asset in assets]
            
            logger.info(f"✓ Listed {len(assets_list)} assets (file_type={file_type}, status={status}, limit={limit})")
            return assets_list
            
        except Exception as e:
            logger.error(f"✗ Failed to list assets: {e}")
            raise


async def get_asset_by_id(asset_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a single asset by ID.
    
    Args:
        asset_id: UUID of the asset
        
    Returns:
        Dict or None: Asset dictionary if found, None otherwise
    """
    async with AsyncSessionLocal() as session:
        try:
            result = await session.execute(
                select(SilverAsset).where(SilverAsset.id == UUID(asset_id))
            )
            asset = result.scalar_one_or_none()
            
            if asset:
                return asset.to_dict()
            return None
            
        except Exception as e:
            logger.error(f"✗ Failed to get asset {asset_id}: {e}")
            raise


async def update_asset_status(
    asset_id: str,
    status: str,
    silver_minio_key: Optional[str] = None,
    error_message: Optional[str] = None,
) -> bool:
    """
    Update asset processing status.
    
    Args:
        asset_id: UUID of the asset
        status: New status (pending, success, failed)
        silver_minio_key: Path to silver JSON result (if success)
        error_message: Error description (if failed)
        
    Returns:
        bool: True if updated, False if not found
    """
    async with AsyncSessionLocal() as session:
        try:
            result = await session.execute(
                select(SilverAsset).where(SilverAsset.id == UUID(asset_id))
            )
            asset = result.scalar_one_or_none()
            
            if not asset:
                return False
            
            asset.extraction_status = status
            asset.processed_at = datetime.utcnow()
            
            if silver_minio_key:
                asset.silver_minio_key = silver_minio_key
            
            if error_message and status == "failed":
                # Store error in summary field (or create a separate error column)
                asset.summary = f"ERROR: {error_message}"
            
            await session.commit()
            logger.info(f"✓ Updated asset {asset_id} status to {status}")
            return True
            
        except Exception as e:
            await session.rollback()
            logger.error(f"✗ Failed to update asset {asset_id}: {e}")
            raise


# ============================================================================
# Utility Functions
# ============================================================================

async def get_asset_statistics() -> Dict[str, Any]:
    """
    Get aggregate statistics about silver assets.
    
    Returns:
        Dict with counts by status, file_type, etc.
    """
    async with AsyncSessionLocal() as session:
        try:
            # Get total count
            total_result = await session.execute(select(SilverAsset))
            total_count = len(total_result.scalars().all())
            
            # Get counts by status
            success_result = await session.execute(
                select(SilverAsset).where(SilverAsset.extraction_status == "success")
            )
            success_count = len(success_result.scalars().all())
            
            failed_result = await session.execute(
                select(SilverAsset).where(SilverAsset.extraction_status == "failed")
            )
            failed_count = len(failed_result.scalars().all())
            
            pending_result = await session.execute(
                select(SilverAsset).where(SilverAsset.extraction_status == "pending")
            )
            pending_count = len(pending_result.scalars().all())
            
            return {
                "total": total_count,
                "success": success_count,
                "failed": failed_count,
                "pending": pending_count,
                "success_rate": (success_count / total_count * 100) if total_count > 0 else 0,
            }
            
        except Exception as e:
            logger.error(f"✗ Failed to get statistics: {e}")
            raise


# ============================================================================
# Health Check
# ============================================================================

async def health_check() -> Dict[str, str]:
    """
    Check database and MinIO connectivity.
    
    Returns:
        Dict with status of each service
    """
    health = {
        "database": "unknown",
        "minio": "unknown",
    }
    
    # Check database
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(select(1))
        health["database"] = "healthy"
    except Exception as e:
        health["database"] = f"unhealthy: {str(e)}"
        logger.error(f"Database health check failed: {e}")
    
    # Check MinIO
    try:
        minio_client = get_minio_client()
        # Try to list buckets
        list(minio_client.list_buckets())
        health["minio"] = "healthy"
    except Exception as e:
        health["minio"] = f"unhealthy: {str(e)}"
        logger.error(f"MinIO health check failed: {e}")
    
    return health


# ============================================================================
# Module Initialization
# ============================================================================

logger.info("✓ silver_store module loaded")
logger.info(f"  - Database: {DATABASE_URL.split('@')[-1] if '@' in DATABASE_URL else 'configured'}")
logger.info(f"  - MinIO: {MINIO_ENDPOINT}")
