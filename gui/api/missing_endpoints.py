"""
Missing Endpoints for 7 Frontend Tabs
Add these to backend.py after existing @app routes
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import os
import logging
import psycopg2
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)
router = APIRouter()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://syniqai_user:syniqai_password@localhost:5432/syniqai_metadata")

# ============================================================================
# Media Dashboard Endpoints
# ============================================================================

@router.get("/api/silver/assets/stats")
def get_silver_assets_stats():
    """
    Media Dashboard stats - query silver_assets grouped by file_type
    Also count audio/video in Bronze not yet in silver_assets as pending
    """
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Count by file type in silver_assets
        cur.execute("""
            SELECT 
                file_type,
                COUNT(*) as count,
                SUM(COALESCE(
                    (SELECT size FROM minio_objects WHERE object_key = bronze_minio_key LIMIT 1),
                    0
                )) as total_bytes
            FROM silver_assets
            GROUP BY file_type
        """)
        type_counts = {row['file_type']: row for row in cur.fetchall()}
        
        # Count total files
        cur.execute("SELECT COUNT(*) as total FROM silver_assets")
        total_files = cur.fetchone()['total']
        
        # Estimate storage (if no minio_objects table, use dummy calculation)
        total_bytes = sum(row.get('total_bytes', 0) or 0 for row in type_counts.values())
        storage_gb = total_bytes / (1024**3) if total_bytes else 0
        
        cur.close()
        conn.close()
        
        # Count pending media files in Bronze (not in silver_assets)
        pending_media_count = 0
        try:
            from minio import Minio
            mc = Minio('localhost:9000', 'admin', 'password123', secure=False)
            bronze_files = list(mc.list_objects('syniqai-bronze', recursive=True))
            
            # Get processed keys
            conn = psycopg2.connect(DATABASE_URL)
            cur = conn.cursor()
            cur.execute("SELECT bronze_minio_key FROM silver_assets")
            processed = {row[0] for row in cur.fetchall()}
            cur.close()
            conn.close()
            
            # Count unprocessed media
            for obj in bronze_files:
                if obj.object_name not in processed:
                    ext = obj.object_name.split('.')[-1].lower()
                    if ext in ['mp3', 'wav', 'mp4', 'avi', 'mov', 'mkv']:
                        pending_media_count += 1
        except Exception as e:
            logger.warning(f"Could not count pending media: {e}")
        
        return {
            "total_files": total_files,
            "images": sum(c.get('count', 0) for t, c in type_counts.items() if t in ['jpg', 'jpeg', 'png', 'gif', 'bmp']),
            "videos": sum(c.get('count', 0) for t, c in type_counts.items() if t in ['mp4', 'avi', 'mov', 'mkv']),
            "audio_files": sum(c.get('count', 0) for t, c in type_counts.items() if t in ['mp3', 'wav']),
            "documents": sum(c.get('count', 0) for t, c in type_counts.items() if t in ['pdf', 'txt', 'docx']),
            "storage_used_gb": round(storage_gb, 2),
            "pending_media_count": pending_media_count
        }
    except Exception as e:
        logger.error(f"get_silver_assets_stats failed: {e}")
        return {
            "total_files": 0,
            "images": 0,
            "videos": 0,
            "audio_files": 0,
            "documents": 0,
            "storage_used_gb": 0.0,
            "pending_media_count": 0
        }


# ============================================================================
# File Browser Endpoints
# ============================================================================

@router.get("/api/silver/download/{asset_id}")
def download_silver_asset(asset_id: str):
    """
    Generate MinIO presigned URL for bronze_minio_key, 1 hour expiry
    """
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT bronze_minio_key, file_type FROM silver_assets WHERE id = %s", (asset_id,))
        asset = cur.fetchone()
        cur.close()
        conn.close()
        
        if not asset:
            raise HTTPException(status_code=404, detail=f"Asset {asset_id} not found")
        
        from minio import Minio
        from datetime import timedelta
        
        mc = Minio('localhost:9000', 'admin', 'password123', secure=False)
        url = mc.presigned_get_object(
            'syniqai-bronze',
            asset['bronze_minio_key'],
            expires=timedelta(hours=1)
        )
        
        return {
            "asset_id": asset_id,
            "download_url": url,
            "expires_in_seconds": 3600,
            "file_type": asset['file_type']
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"download_silver_asset failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Audio Analysis Endpoints
# ============================================================================

@router.post("/api/silver/unstructured/analysis/audio")
async def analyze_audio(bronze_minio_key: str, filename: str):
    """
    On-demand audio analysis trigger (NOT called automatically)
    Accept bronze_minio_key + filename, call processor.process_message()
    Return transcript_srt, vtt_timestamps, summary
    """
    try:
        import sys
        from pathlib import Path
        
        # Import AI processor
        ai_processor_dir = Path(__file__).resolve().parent.parent.parent / "ai processing"
        if str(ai_processor_dir) not in sys.path:
            sys.path.insert(0, str(ai_processor_dir))
        
        from ai_processor import AIProcessor
        processor = AIProcessor()
        
        message = {
            "bronze_minio_key": bronze_minio_key,
            "filename": filename,
            "file_type": "mp3",
            "source": "audio_analysis",
            "size_bytes": 0
        }
        
        processor.process_message(message)
        
        # Try to fetch Silver JSON
        from datetime import datetime
        date_str = datetime.now().strftime("%Y-%m-%d")
        silver_key = f"mp3/{date_str}/{filename}.json"
        
        try:
            silver_bytes = processor.storage.download_file(
                processor.MINIO_SILVER_BUCKET, silver_key
            )
            import json
            result = json.loads(silver_bytes.decode("utf-8"))
            return {
                "transcript_srt": result.get("transcript", ""),
                "vtt_timestamps": result.get("transcript", ""),
                "summary": result.get("summary", "Audio processed successfully"),
                "confidence": result.get("confidence", 0.0)
            }
        except Exception:
            return {
                "transcript_srt": "",
                "vtt_timestamps": "",
                "summary": "Processing queued - check back later",
                "silver_key": silver_key
            }
            
    except Exception as e:
        logger.error(f"analyze_audio failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
