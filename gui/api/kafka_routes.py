"""
Kafka health and watermark routes.
Mounted at /api/kafka in backend.py.
"""

import json
import logging
import socket
from pathlib import Path

from fastapi import APIRouter

logger = logging.getLogger(__name__)
router = APIRouter()

KAFKA_HOST = "localhost"
KAFKA_PORT = 9092

# Path to S3 watermarks file written by the CDC consumer
_WATERMARKS_PATH = (
    Path(__file__).parent.parent.parent
    / "Kafka Integration"
    / "watermarks"
    / "s3_watermarks.json"
)


def _kafka_reachable() -> bool:
    """Quick TCP probe — avoids slow kafka-python timeouts."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        result = s.connect_ex((KAFKA_HOST, KAFKA_PORT))
        s.close()
        return result == 0
    except Exception:
        return False


# ── Health ────────────────────────────────────────────────────────────────────

@router.get("/health")
def kafka_health():
    """
    Health check for the Kafka broker.
    S3CDCTab reads: response.data.status ('healthy' | 'error')
                    response.data.message
    """
    if _kafka_reachable():
        return {
            "status": "healthy",
            "message": f"Kafka broker reachable at {KAFKA_HOST}:{KAFKA_PORT}",
            "broker": f"{KAFKA_HOST}:{KAFKA_PORT}",
        }
    return {
        "status": "error",
        "message": f"Cannot connect to Kafka at {KAFKA_HOST}:{KAFKA_PORT}",
        "broker": f"{KAFKA_HOST}:{KAFKA_PORT}",
    }


# ── S3 Watermarks ─────────────────────────────────────────────────────────────

@router.get("/s3/watermarks")
def get_s3_watermarks():
    """Return S3 batch-CDC watermarks from the JSON file on disk."""
    try:
        if _WATERMARKS_PATH.exists():
            with open(_WATERMARKS_PATH, "r") as f:
                watermarks = json.load(f)
        else:
            watermarks = {}
        return {"success": True, "watermarks": watermarks}
    except Exception as e:
        logger.error(f"Failed to read S3 watermarks: {e}")
        return {"success": False, "watermarks": {}, "error": str(e)}


@router.delete("/s3/watermarks")
def reset_s3_watermarks():
    """Delete the S3 watermarks file to force a full re-extraction."""
    try:
        if _WATERMARKS_PATH.exists():
            _WATERMARKS_PATH.unlink()
            return {"success": True, "message": "S3 watermarks reset. Next run will re-extract all objects."}
        return {"success": True, "message": "No watermarks file found — already clean."}
    except Exception as e:
        logger.error(f"Failed to reset S3 watermarks: {e}")
        return {"success": False, "error": str(e)}
