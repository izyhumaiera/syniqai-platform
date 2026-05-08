"""
Unstructured Silver Layer Router
=================================
FastAPI router for unstructured-media transformation jobs.

Endpoints
---------
POST /api/silver/unstructured/process          – start a processing job
PUT  /api/silver/unstructured/rules/{type}     – update transformation rules
GET  /api/silver/unstructured/jobs             – list all jobs
GET  /api/silver/unstructured/jobs/{job_id}    – get one job's status
GET  /api/silver/unstructured/stats            – source connector stats
GET  /api/silver/unstructured/tables           – list Silver Iceberg tables
GET  /api/silver/unstructured/preview/{type}   – preview processed records
POST /api/silver/unstructured/validate         – validate source connectivity

Wired into backend.py via:

    from unstructured_router import router as unstructured_router, setup_unstructured_router
    setup_unstructured_router(silver_job_tracker, config, gold_layer_path, _find_java_17)
    app.include_router(unstructured_router, prefix="/api/silver/unstructured",
                       tags=["Unstructured Silver"])
"""

from __future__ import annotations

import logging
import os
import sys
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# AI Processor Integration (OpenRouter)
# ---------------------------------------------------------------------------
_ai_processor_path = Path(__file__).resolve().parent.parent.parent / "ai processing"
if str(_ai_processor_path) not in sys.path:
    sys.path.insert(0, str(_ai_processor_path))

_ai_processor_instance = None

def _get_ai_processor():
    global _ai_processor_instance
    if _ai_processor_instance is None:
        try:
            from ai_processor import AIProcessor
            _ai_processor_instance = AIProcessor()
            logger.info("✓ AIProcessor (OpenRouter) initialised inside unstructured_router")
        except Exception as e:
            logger.error(f"Failed to init AIProcessor: {e}")
    return _ai_processor_instance

# ---------------------------------------------------------------------------
# SyniqAI Unstructured Package singletons (lazy-init on first use)
# ---------------------------------------------------------------------------
_rules_engine = None
_ml_registry = None
_analysis_service = None


def _ensure_api_path() -> None:
    """Ensure the gui/api directory is on sys.path so SyniqAI_unstructured_package is importable."""
    api_dir = str(Path(__file__).parent)
    if api_dir not in sys.path:
        sys.path.insert(0, api_dir)


def _get_rules_engine():
    global _rules_engine
    if _rules_engine is None:
        _ensure_api_path()
        from SyniqAI_unstructured_package import QualityRulesEngine  # type: ignore
        _rules_engine = QualityRulesEngine(
            postgres_config=getattr(_config, "postgres", None) if _config else None
        )
    return _rules_engine


def _get_ml_registry():
    global _ml_registry
    if _ml_registry is None:
        _ensure_api_path()
        from SyniqAI_unstructured_package import MLModelRegistry  # type: ignore
        _ml_registry = MLModelRegistry(
            postgres_config=getattr(_config, "postgres", None) if _config else None
        )
    return _ml_registry


def _get_analysis_service():
    global _analysis_service
    if _analysis_service is None:
        _ensure_api_path()
        from SyniqAI_unstructured_package import LLMService, AnalysisService  # type: ignore
        _analysis_service = AnalysisService(
            llm_service=LLMService(),
            minio_config=_get_minio_config(),
            gold_layer_path=str(_gold_layer_path) if _gold_layer_path else None,
        )
    return _analysis_service

# ---------------------------------------------------------------------------
# Shared state injected by backend.py at startup
# ---------------------------------------------------------------------------
_silver_job_tracker = None   # SilverJobTracker instance
_config = None               # AppConfig instance (has .minio, .postgres …)
_gold_layer_path: Optional[Path] = None  # path to data lakehouse/syniq_project

# Persistent transformation rules store (in-memory; survives restarts via
# optional disk backing if needed)
_transformation_rules: Dict[str, Dict[str, Any]] = {
    "image": {
        "resize": False, "resizeWidth": 224, "resizeHeight": 224,
        "normalizePixels": False, "grayscale": False,
        "edgeDetection": False, "objectDetection": False,
        "formatConversion": None,
    },
    "video": {
        "normalizeFPS": False, "targetFPS": 30, "compression": False,
        "formatConversion": None,
    },
    "audio": {
        "normalizeVolume": False, "channelConfig": None,
        "formatConversion": None,
    },
    "document": {
        "extractText": True, "detectLanguage": True,
        "sentimentAnalysis": False, "piiRedaction": False,
        "chunkSize": 1024,
    },
    "text": {
        "extractText": True, "detectLanguage": True,
        "sentimentAnalysis": False, "piiRedaction": False,
    },
}

_rules_lock = threading.Lock()


# ---------------------------------------------------------------------------
# Setup function called by backend.py
# ---------------------------------------------------------------------------

def setup_unstructured_router(
    silver_job_tracker,
    config,
    gold_layer_path: Path,
) -> None:
    """Inject shared dependencies from backend.py."""
    global _silver_job_tracker, _config, _gold_layer_path
    _silver_job_tracker = silver_job_tracker
    _config = config
    _gold_layer_path = gold_layer_path
    logger.info("✅ UnstructuredRouter dependencies injected")
    
    try:
        _get_ai_processor()
        logger.info("✓ OpenRouter AI Processor connected to unstructured router")
    except Exception as e:
        logger.warning(f"OpenRouter AI Processor not available at startup: {e}")


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------
router = APIRouter(tags=["Unstructured Silver"])


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class UnstructuredProcessRequest(BaseModel):
    """Request body for POST /process"""
    media_type: str                       # "image" | "video" | "audio" | "document"
    domain: str = "media"
    entity: str = "assets"
    execution_mode: str = "full"          # "full" | "incremental"
    # Source connector configs (optional – merged with server-side env config)
    mongodb_config: Optional[Dict[str, Any]] = None
    s3_config: Optional[Dict[str, Any]] = None
    # Override transform rules for this single run (optional)
    transforms: Optional[Dict[str, Any]] = None
    # Quality rules
    rules: List[Dict[str, Any]] = []
    # If files are already in Bronze, skip staging
    stage_to_bronze: bool = True
    # Max assets to fetch from source connectors
    limit: int = 10_000


class TransformRulesUpdate(BaseModel):
    """Request body for PUT /rules/{type}"""
    rules: Dict[str, Any]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_minio_config() -> Dict[str, Any]:
    """Build minio config from injected AppConfig or fall back to env vars."""
    if _config and hasattr(_config, "minio"):
        m = _config.minio
        return {
            "endpoint": m.endpoint,
            "access_key": m.access_key,
            "secret_key": m.secret_key,
            "secure": getattr(m, "secure", False),
        }
    return {
        "endpoint": os.getenv("MINIO_ENDPOINT", "http://localhost:9000"),
        "access_key": os.getenv("MINIO_ACCESS_KEY", "admin"),
        "secret_key": os.getenv("MINIO_SECRET_KEY", "password123"),
        "secure": False,
    }


def _get_processor_config(
    mongodb_config: Optional[Dict[str, Any]],
    s3_config: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Merge request-provided connector configs with environment-sourced defaults.
    Request values take precedence (allowing per-call overrides from the UI).
    """
    default_mongo = {
        "host": os.getenv("MONGODB_HOST", "localhost"),
        "port": int(os.getenv("MONGODB_PORT", "27017")),
        "database": os.getenv("MONGODB_DATABASE", "media"),
        "user": os.getenv("MONGODB_USER", ""),
        "password": os.getenv("MONGODB_PASSWORD", ""),
    }

    default_s3 = {
        "bucket": os.getenv("S3_RAW_MEDIA_BUCKET", "syniq-raw-media"),
        "aws_access_key_id": os.getenv("AWS_ACCESS_KEY_ID", ""),
        "aws_secret_access_key": os.getenv("AWS_SECRET_ACCESS_KEY", ""),
        "region_name": os.getenv("AWS_DEFAULT_REGION", "us-east-1"),
    }

    merged: Dict[str, Any] = {"minio": _get_minio_config()}

    # Use request-provided config if present, else fall back to env ONLY when
    # the env vars are explicitly set (not just the hardcoded "localhost" fallback).
    # This prevents the pipeline from blindly trying localhost:27017 when no
    # MongoDB was configured in the UI.
    if mongodb_config:
        merged["mongodb"] = {**default_mongo, **mongodb_config}
    elif os.getenv("MONGODB_HOST"):
        # Only use the default if MONGODB_HOST was explicitly set in the environment
        merged["mongodb"] = default_mongo

    if s3_config:
        # Normalize short-form key names used by the UI to boto3-style names
        normalized_s3 = dict(s3_config)
        if "aws_access_key" in normalized_s3 and "aws_access_key_id" not in normalized_s3:
            normalized_s3["aws_access_key_id"] = normalized_s3.pop("aws_access_key")
        if "aws_secret_key" in normalized_s3 and "aws_secret_access_key" not in normalized_s3:
            normalized_s3["aws_secret_access_key"] = normalized_s3.pop("aws_secret_key")
        if "aws_region" in normalized_s3 and "region_name" not in normalized_s3:
            normalized_s3["region_name"] = normalized_s3.pop("aws_region").strip()
        if "s3_bucket" in normalized_s3 and "bucket" not in normalized_s3:
            normalized_s3["bucket"] = normalized_s3.pop("s3_bucket")
        if "s3_prefix" in normalized_s3 and "prefix" not in normalized_s3:
            normalized_s3["prefix"] = normalized_s3.pop("s3_prefix")
        merged["s3"] = {**default_s3, **normalized_s3}
    elif default_s3.get("aws_access_key_id"):
        merged["s3"] = default_s3

    return merged


def _run_lightweight_job(
    job_id: str,
    media_type: str,
    domain: str,
    entity: str,
    processor_config: Dict[str, Any],
    stage_to_bronze: bool,
    limit: int,
    transforms: Optional[Dict[str, Any]] = None,
    rules: Optional[List[Dict[str, Any]]] = None,
) -> None:
    """
    No-Spark fallback pipeline: lists assets from S3 and/or MongoDB,
    applies transform metadata, and stages to MinIO Bronze.
    Used automatically when Java 17 / PySpark is unavailable.
    """
    try:
        import json
        from io import BytesIO

        _silver_job_tracker.update_status(
            job_id=job_id, status="running",
            message="Listing assets (lightweight mode – no Spark)…", progress=20
        )

        s3_cfg = processor_config.get("s3") or {}
        minio_cfg = processor_config.get("minio") or {}
        assets: List[Dict[str, Any]] = []

        if s3_cfg and s3_cfg.get("aws_access_key_id") and s3_cfg.get("bucket"):
            try:
                import boto3
                s3_client = boto3.client(
                    "s3",
                    aws_access_key_id=s3_cfg["aws_access_key_id"],
                    aws_secret_access_key=s3_cfg.get("aws_secret_access_key", ""),
                    region_name=s3_cfg.get("region_name", "us-east-1").strip(),
                )
                bucket = s3_cfg["bucket"]
                prefix = s3_cfg.get("prefix", "")
                paginator = s3_client.get_paginator("list_objects_v2")
                for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
                    for obj in page.get("Contents", []):
                        key = obj["Key"]
                        ext = key.rsplit(".", 1)[-1].lower() if "." in key else ""
                        assets.append({
                            "source": "s3",
                            "bucket": bucket,
                            "key": key,
                            "size_bytes": obj.get("Size", 0),
                            "last_modified": obj["LastModified"].isoformat(),
                            "media_type": media_type,
                            "ext": ext,
                            "domain": domain,
                            "entity": entity,
                            "ingested_at": datetime.utcnow().isoformat(),
                        })
                        if len(assets) >= limit:
                            break
                    if len(assets) >= limit:
                        break
                logger.info(f"Lightweight job {job_id}: discovered {len(assets)} S3 assets")
            except Exception as s3_exc:
                logger.warning(f"S3 listing failed for job {job_id}: {s3_exc}")

        # ---- MongoDB source ----
        mongo_cfg = processor_config.get("mongodb") or {}
        if mongo_cfg and (mongo_cfg.get("host") or mongo_cfg.get("uri")):
            try:
                from pymongo import MongoClient  # type: ignore
                uri = mongo_cfg.get("uri") or "mongodb://{}:{}".format(
                    mongo_cfg["host"], mongo_cfg.get("port", 27017)
                )
                username = mongo_cfg.get("username") or mongo_cfg.get("user", "")
                password = mongo_cfg.get("password", "")
                if username and password and "://" in uri and "@" not in uri:
                    proto, rest = uri.split("://", 1)
                    uri = f"{proto}://{username}:{password}@{rest}"
                db_name = mongo_cfg.get("database", domain)
                collection_name = mongo_cfg.get("collection", entity)
                client = MongoClient(uri, serverSelectionTimeoutMS=5000)
                col = client[db_name][collection_name]
                projection = {
                    "_id": 1, "file_path": 1, "s3_path": 1, "url": 1,
                    "filename": 1, "file_name": 1, "size": 1,
                    "created_at": 1, "updated_at": 1,
                    "media_type": 1, "content_type": 1,
                }
                remaining = limit - len(assets)
                for doc in col.find({}, projection).limit(remaining):
                    fp = (
                        doc.get("file_path") or doc.get("s3_path") or
                        doc.get("url") or doc.get("filename") or
                        doc.get("file_name") or str(doc["_id"])
                    )
                    ext = fp.rsplit(".", 1)[-1].lower() if "." in fp else ""
                    assets.append({
                        "source": "mongodb",
                        "collection": f"{db_name}.{collection_name}",
                        "doc_id": str(doc["_id"]),
                        "file_path": fp,
                        "size_bytes": doc.get("size", 0),
                        "last_modified": str(
                            doc.get("updated_at") or doc.get("created_at") or ""
                        ),
                        "media_type": media_type,
                        "ext": ext,
                        "domain": domain,
                        "entity": entity,
                        "ingested_at": datetime.utcnow().isoformat(),
                    })
                    if len(assets) >= limit:
                        break
                client.close()
                logger.info(
                    f"Lightweight job {job_id}: discovered {len(assets)} MongoDB assets "
                    f"from {db_name}.{collection_name}"
                )
            except Exception as mongo_exc:
                logger.warning(f"MongoDB listing failed for job {job_id}: {mongo_exc}")

        _silver_job_tracker.update_status(
            job_id=job_id, status="running",
            message=f"Staging {len(assets)} asset records to Bronze…", progress=60
        )

        # Stage metadata JSON to MinIO Bronze
        if minio_cfg:
            try:
                from minio import Minio  # type: ignore
                endpoint = minio_cfg["endpoint"].replace("http://", "").replace("https://", "")
                mc = Minio(
                    endpoint,
                    access_key=minio_cfg.get("access_key", ""),
                    secret_key=minio_cfg.get("secret_key", ""),
                    secure=minio_cfg.get("secure", False),
                )
                bronze_bucket = "syniqai-bronze"
                try:
                    if not mc.bucket_exists(bronze_bucket):
                        mc.make_bucket(bronze_bucket)
                except Exception:
                    pass
                meta_payload = {
                    "assets": assets,
                    "transforms_applied": transforms or {},
                    "rules_applied": rules or [],
                    "job_id": job_id,
                    "generated_at": datetime.utcnow().isoformat(),
                }
                meta_bytes = json.dumps(meta_payload, indent=2, default=str).encode("utf-8")
                ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                object_name = f"{domain}/{entity}/{media_type}/metadata_{ts}.json"
                mc.put_object(
                    bronze_bucket, object_name,
                    BytesIO(meta_bytes), len(meta_bytes),
                    content_type="application/json",
                )
                logger.info(f"Lightweight job {job_id}: staged metadata to minio://{bronze_bucket}/{object_name}")
            except Exception as minio_exc:
                logger.warning(f"MinIO staging failed for job {job_id}: {minio_exc}")

        # ---- OpenRouter AI Processing ----
        processor = _get_ai_processor()
        if processor and assets:
            logger.info(f"[OPENROUTER] Starting AI processing for {len(assets)} assets in job {job_id}")
            processed = 0
            failed = 0
            for asset in assets:
                try:
                    if asset.get("source") == "s3":
                        bronze_key = f"{asset['domain']}/s3/{asset['entity']}/{asset['key'].split('/')[-1]}"
                    else:
                        bronze_key = f"{asset['domain']}/mongodb/{asset['entity']}/{asset.get('doc_id', 'unknown')}"
                    ext = asset.get("ext", "").lower()
                    file_type = ext if ext else "txt"
                    if file_type in ["mp3", "wav", "mp4", "avi", "mov", "mkv"]:
                        logger.info(f"[MEDIA GATE] {asset.get('key', '')} ({file_type}) → held, skipping OpenRouter")
                        continue
                    message = {
                        "bronze_minio_key": bronze_key,
                        "filename": asset.get("key", "").split("/")[-1] or asset.get("doc_id", "unknown"),
                        "file_type": file_type,
                        "source": asset.get("source", "unknown"),
                        "size_bytes": asset.get("size_bytes", 0)
                    }
                    processor.process_message(message)
                    processed += 1
                except Exception as asset_exc:
                    logger.error(f"[OPENROUTER] Failed for asset {asset.get('key', '')}: {asset_exc}")
                    failed += 1
            logger.info(f"[OPENROUTER] Job {job_id} complete — processed: {processed}, failed: {failed}")
            _silver_job_tracker.update_status(
                job_id=job_id, status="completed",
                message=f"AI processing complete — {processed} processed, {failed} failed",
                progress=100
            )
        else:
            _silver_job_tracker.update_status(
                job_id=job_id, status="completed",
                message=f"Lightweight pipeline completed – {len(assets)} assets indexed", progress=100
            )

        _silver_job_tracker.update_results(
            job_id=job_id,
            silver_path=f"minio://syniqai-bronze/{domain}/{entity}/{media_type}/",
            row_count=len(assets),
            cleaning_summary={
                "assets_discovered": len(assets),
                "assets_staged": len(assets),
                "mode": "lightweight",
                "media_type": media_type,
                "transforms_applied": list((transforms or {}).keys()),
                "sources": list({a["source"] for a in assets}),
            },
        )

    except Exception as exc:
        import traceback
        logger.error(f"Lightweight job {job_id} failed: {exc}\n{traceback.format_exc()}")
        _silver_job_tracker.update_status(
            job_id=job_id, status="failed",
            message="Lightweight pipeline error",
            error_message=f"{type(exc).__name__}: {exc}",
        )


# ---------------------------------------------------------------------------
# Background task runner
# ---------------------------------------------------------------------------

def _run_unstructured_job(
    job_id: str,
    media_type: str,
    domain: str,
    entity: str,
    execution_mode: str,
    processor_config: Dict[str, Any],
    transforms: Dict[str, Any],
    rules: List[Dict[str, Any]],
    stage_to_bronze: bool,
    limit: int,
) -> None:
    """Background task: runs the full unstructured pipeline and updates tracker.
    
    Note: No Spark/Iceberg. Redirects to _run_lightweight_job with OpenRouter AI processing.
    """
    _run_lightweight_job(
        job_id=job_id,
        media_type=media_type,
        domain=domain,
        entity=entity,
        processor_config=processor_config,
        stage_to_bronze=stage_to_bronze,
        limit=limit,
        transforms=transforms,
        rules=rules,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/process")
async def start_unstructured_processing(
    request: UnstructuredProcessRequest,
    background_tasks: BackgroundTasks,
):
    """
    Start an unstructured-media silver transformation job.

    The job runs in the background.  Poll ``GET /jobs/{job_id}`` for status.
    """
    if _silver_job_tracker is None:
        raise HTTPException(status_code=503, detail="Service not yet initialised")

    valid_types = {"image", "video", "audio", "document", "text", "pdf"}
    if request.media_type not in valid_types:
        raise HTTPException(
            status_code=422,
            detail=f"media_type must be one of {sorted(valid_types)}"
        )

    # Build the job ID
    job_id = (
        f"unstructured_{request.domain}_{request.entity}_"
        f"{request.media_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    )

    # Register in tracker
    bronze_path = (
        f"s3a://syniqai-bronze/{request.domain}/"
        f"{request.s3_config.get('bucket', 's3') if request.s3_config else 'mongodb'}/"
        f"{request.entity}/"
    )
    # Register job directly with our deterministic job_id
    import sqlite3 as _sqlite3, json as _json
    _initial_job = {
        "job_id": job_id,
        "job_type": "silver_processing",
        "table_name": f"{request.domain}.unstructured.{request.media_type}.{request.entity}",
        "source": request.s3_config.get("s3_bucket", "unstructured") if request.s3_config else "mongodb",
        "entity": request.entity,
        "bronze_path": bronze_path,
        "status": "queued",
        "progress": 0,
        "message": "Job queued",
        "started_at": datetime.now().isoformat(),
        "completed_at": None,
        "error_message": None,
        "silver_path": None,
        "row_count": None,
        "quality_score": None,
        "cleaning_summary": None,
    }
    with _silver_job_tracker.lock:
        _silver_job_tracker._save(_initial_job)

    # Resolve transform rules: explicit request overrides > stored server-side rules > defaults
    with _rules_lock:
        base_rules = dict(_transformation_rules.get(request.media_type, {}))
    transforms = {**base_rules, **(request.transforms or {})}

    # Build processor config
    processor_config = _get_processor_config(request.mongodb_config, request.s3_config)

    # Queue background task
    background_tasks.add_task(
        _run_unstructured_job,
        job_id=job_id,
        media_type=request.media_type,
        domain=request.domain,
        entity=request.entity,
        execution_mode=request.execution_mode,
        processor_config=processor_config,
        transforms=transforms,
        rules=request.rules,
        stage_to_bronze=request.stage_to_bronze,
        limit=request.limit,
    )

    return {
        "job_id": job_id,
        "status": "queued",
        "media_type": request.media_type,
        "domain": request.domain,
        "entity": request.entity,
        "message": f"Unstructured {request.media_type} pipeline queued for {request.domain}.{request.entity}",
        "silver_table": (
            f"syniq_iceberg.{request.domain}."
            f"unstructured_{request.media_type}_{request.entity}"
        ),
    }


@router.get("/jobs")
def list_unstructured_jobs(status: Optional[str] = None, limit: int = 50):
    """List unstructured processing jobs."""
    if _silver_job_tracker is None:
        return {"jobs": [], "total": 0}

    all_jobs = _silver_job_tracker.list_jobs(limit=limit * 3, status=status)

    # Filter to only unstructured jobs
    jobs = [j for j in all_jobs if j.get("job_id", "").startswith("unstructured_")]
    return {"jobs": jobs[:limit], "total": len(jobs)}


@router.get("/jobs/{job_id}")
def get_unstructured_job(job_id: str):
    """Get the status of a single unstructured pipeline job."""
    if _silver_job_tracker is None:
        raise HTTPException(status_code=503, detail="Service not yet initialised")

    job = _silver_job_tracker.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    return job


@router.put("/rules/{media_type}")
def update_transformation_rules(media_type: str, body: TransformRulesUpdate):
    """
    Persist transformation rules for a given media type server-side.

    These rules are used as the baseline for all subsequent processing jobs
    unless explicitly overridden in the job request.
    """
    valid_types = {"image", "video", "audio", "document", "text", "pdf"}
    if media_type not in valid_types:
        raise HTTPException(
            status_code=422,
            detail=f"media_type must be one of {sorted(valid_types)}"
        )

    with _rules_lock:
        current = _transformation_rules.setdefault(media_type, {})
        current.update(body.rules)
        snapshot = dict(current)

    return {
        "media_type": media_type,
        "rules": snapshot,
        "updated_at": datetime.now().isoformat(),
    }


@router.get("/rules/{media_type}")
def get_transformation_rules(media_type: str):
    """Return current server-side transformation rules for a media type."""
    with _rules_lock:
        rules = dict(_transformation_rules.get(media_type, {}))
    return {"media_type": media_type, "rules": rules}


@router.get("/rules")
def list_all_transformation_rules():
    """Return all transformation rules for all media types."""
    with _rules_lock:
        snapshot = {k: dict(v) for k, v in _transformation_rules.items()}
    return {"rules": snapshot}


@router.get("/stats")
def get_source_stats():
    """
    Return media counts derived from Silver parquet metadata files
    and completed job history — no live S3 connection required.
    """
    counts = {"image": 0, "video": 0, "audio": 0, "document": 0, "text": 0, "pdf": 0}
    total_size_bytes = 0
    total_files = 0

    # ── Read Silver parquet metadata ────────────────────────────────────────
    try:
        from minio import Minio  # type: ignore
        import pyarrow.parquet as _pq  # type: ignore
        import io as _io

        minio_cfg = _get_minio_config()
        endpoint = (minio_cfg.get("endpoint", "http://localhost:9000")
                    .replace("http://", "").replace("https://", ""))
        secure = minio_cfg.get("endpoint", "").startswith("https://")
        mc = Minio(endpoint=endpoint,
                   access_key=minio_cfg.get("access_key", "admin"),
                   secret_key=minio_cfg.get("secret_key", "password123"),
                   secure=secure)

        if mc.bucket_exists("syniqai-silver"):
            for obj in mc.list_objects("syniqai-silver", prefix="unstructured/", recursive=True):
                if obj.object_name.endswith(".parquet"):
                    try:
                        resp = mc.get_object("syniqai-silver", obj.object_name)
                        buf = _io.BytesIO(resp.read())
                        resp.close(); resp.release_conn()
                        tbl = _pq.read_table(buf, columns=["file_extension", "file_size_bytes"])
                        for ext, size in zip(
                            tbl["file_extension"].to_pylist(),
                            tbl["file_size_bytes"].to_pylist()
                        ):
                            ext = (ext or "").lower()
                            total_files += 1
                            total_size_bytes += int(size or 0)
                            if ext in {"jpg", "jpeg", "png", "gif", "bmp", "tiff", "webp"}:
                                counts["image"] += 1
                            elif ext in {"mp4", "avi", "mov", "wmv", "flv", "mkv", "webm"}:
                                counts["video"] += 1
                            elif ext in {"mp3", "wav", "flac", "aac", "ogg", "m4a"}:
                                counts["audio"] += 1
                            elif ext == "pdf":
                                counts["document"] += 1
                            elif ext in {"txt", "csv", "json", "log"}:
                                counts["text"] += 1
                    except Exception:
                        pass
    except Exception as exc:
        logger.warning(f"Could not read Silver stats from MinIO: {exc}")

    # ── Supplement with completed job history ───────────────────────────────
    if _silver_job_tracker:
        try:
            for job in _silver_job_tracker.list_jobs(limit=200):
                if job.get("status") == "completed":
                    mt = (job.get("cleaning_summary") or {}).get("media_type") or ""
                    rc = job.get("row_count") or 0
                    if mt and rc and counts.get(mt, 0) == 0:
                        counts[mt] = rc
        except Exception:
            pass

    total_size_gb = total_size_bytes / (1024 ** 3)

    return {
        "status": "ok",
        "sources": {
            "silver": {
                "total_objects": total_files,
                "total_size_gb": round(total_size_gb, 3),
                "by_type": {k: {"count": v} for k, v in counts.items()},
            }
        }
    }


@router.get("/models")
def list_ml_models():
    """Return the ML model registry used by the unstructured pipeline."""
    # Try to enrich with job history (counts, last_run)
    job_counts: Dict[str, int] = {}
    if _silver_job_tracker:
        try:
            all_jobs = _silver_job_tracker.list_jobs()
            for job in all_jobs:
                mt = job.get("cleaning_summary", {}).get("media_type") or job.get("entity", "")
                if mt:
                    job_counts[mt] = job_counts.get(mt, 0) + 1
        except Exception:
            pass

    registry = [
        {
            "id": "img_clf",
            "name": "Image Classifier",
            "type": "Image Classification",
            "framework": "PyTorch",
            "version": "v1.0",
            "status": "deployed",
            "thumbnail": "🏷️",
            "inputs": "Images (any resolution)",
            "outputs": "class labels + confidence",
            "predictions": job_counts.get("image", 0),
        },
        {
            "id": "obj_det",
            "name": "Object Detector (YOLOv8)",
            "type": "Object Detection",
            "framework": "ONNX",
            "version": "v1.0",
            "status": "deployed",
            "thumbnail": "🎯",
            "inputs": "Images / Video frames",
            "outputs": "bounding boxes + labels",
            "predictions": job_counts.get("image", 0) + job_counts.get("video", 0),
        },
        {
            "id": "asr",
            "name": "Speech-to-Text (Whisper)",
            "type": "ASR / NLP",
            "framework": "OpenAI Whisper",
            "version": "v1.0",
            "status": "deployed",
            "thumbnail": "🎙️",
            "inputs": "Audio files (mp3/wav/flac)",
            "outputs": "transcript + language + segments",
            "predictions": job_counts.get("audio", 0),
        },
        {
            "id": "doc_ocr",
            "name": "Document OCR & Extractor",
            "type": "Document AI",
            "framework": "Tesseract / pdfplumber",
            "version": "v1.0",
            "status": "deployed",
            "thumbnail": "📄",
            "inputs": "PDF / DOCX / scanned images",
            "outputs": "extracted text + pages + language",
            "predictions": job_counts.get("document", 0) + job_counts.get("pdf", 0),
        },
        {
            "id": "vid_proc",
            "name": "Video Frame Processor",
            "type": "Video Analysis",
            "framework": "OpenCV",
            "version": "v1.0",
            "status": "deployed",
            "thumbnail": "🎬",
            "inputs": "Video files (mp4/avi/mov)",
            "outputs": "keyframes + metadata + quality score",
            "predictions": job_counts.get("video", 0),
        },
    ]
    return {"models": registry, "total": len(registry)}


@router.get("/health")
def get_service_health():
    """Quick health probe for MinIO and pipeline components."""
    services = []

    # MinIO probe
    try:
        from minio import Minio
        minio_cfg = _get_minio_config()
        ep = minio_cfg["endpoint"].replace("http://", "").replace("https://", "")
        mc = Minio(ep, access_key=minio_cfg["access_key"],
                   secret_key=minio_cfg["secret_key"],
                   secure=minio_cfg.get("secure", False))
        mc.list_buckets()
        services.append({"service": "Object Storage (MinIO)", "status": "healthy", "uptime": "—"})
    except Exception as exc:
        services.append({"service": "Object Storage (MinIO)", "status": "unavailable", "uptime": "—", "error": str(exc)})

    # AI Processor probe
    try:
        proc = _get_ai_processor()
        services.append({"service": "AI Processor (OpenRouter)", "status": "healthy" if proc else "unavailable", "uptime": "—"})
    except Exception:
        services.append({"service": "AI Processor (OpenRouter)", "status": "unavailable", "uptime": "—"})

    # Job tracker probe
    if _silver_job_tracker is not None:
        services.append({"service": "Job Tracker", "status": "healthy", "uptime": "—"})
    else:
        services.append({"service": "Job Tracker", "status": "starting", "uptime": "—"})

    overall = "ok" if all(s["status"] == "healthy" for s in services) else "degraded"
    return {"status": overall, "services": services}


@router.get("/tables")
def list_unstructured_silver_tables():
    """
    List available unstructured media datasets by scanning MinIO Bronze bucket.
    Returns discovered entities/prefixes with file counts.
    
    No Spark/Iceberg - queries Bronze directly.
    """
    # MinIO Bronze scan — returns normalized table_name
    try:
        from minio import Minio
        minio_cfg = _get_minio_config()
        ep = minio_cfg["endpoint"].replace("http://", "").replace("https://", "")
        mc = Minio(ep, access_key=minio_cfg["access_key"],
                   secret_key=minio_cfg["secret_key"],
                   secure=minio_cfg.get("secure", False))
        objs = list(mc.list_objects("syniqai-bronze", recursive=True))
        media_prefixes: dict = {}
        for obj in objs:
            parts = obj.object_name.split("/")
            if len(parts) >= 2:
                key = "/".join(parts[:3]) if len(parts) >= 3 else "/".join(parts[:2])
                if key not in media_prefixes:
                    media_prefixes[key] = {"count": 0, "size": 0}
                media_prefixes[key]["count"] += 1
                media_prefixes[key]["size"] += obj.size or 0
        tables = [
            {
                "table_name": prefix.replace("/", "."),
                "prefix": prefix,
                "catalog": "bronze",
                "row_count": info["count"],
                "size_bytes": info["size"],
            }
            for prefix, info in sorted(media_prefixes.items())
        ]
        return {"catalog": "bronze_scan", "tables": tables, "total": len(tables)}
    except Exception as exc:
        logger.error(f"MinIO Bronze scan failed: {exc}")
        return {"catalog": "bronze_scan", "tables": [], "total": 0, "error": str(exc)}


@router.get("/thumbnail/{bucket}/{object_path:path}")
def get_file_thumbnail(bucket: str, object_path: str):
    """Proxy a raw file from MinIO Bronze/Silver back to the browser.

    Used by FileBrowser to display actual image thumbnails instead of
    generic emoji icons.  The browser requests:
      GET /api/silver/unstructured/thumbnail/syniqai-bronze/media/s3/image_files/10.jpg
    and receives the raw image bytes with the correct content-type.
    """
    import mimetypes
    from fastapi.responses import StreamingResponse
    from minio import Minio

    minio_cfg = _get_minio_config()
    ep = minio_cfg["endpoint"].replace("http://", "").replace("https://", "")
    mc = Minio(
        ep,
        access_key=minio_cfg["access_key"],
        secret_key=minio_cfg["secret_key"],
        secure=minio_cfg.get("secure", False),
    )

    try:
        response = mc.get_object(bucket, object_path)
        content_type, _ = mimetypes.guess_type(object_path)
        content_type = content_type or "application/octet-stream"
        # Stream directly to the browser
        return StreamingResponse(
            response,
            media_type=content_type,
            headers={"Cache-Control": "public, max-age=3600"},
        )
    except Exception as exc:
        raise HTTPException(status_code=404, detail=f"Object not found: {exc}")


@router.get("/preview/{media_type}")
def preview_processed_records(
    media_type: str,
    domain: str = "media",
    entity: str = "assets",
    limit: int = 20,
):
    """
    Return a sample of processed records from PostgreSQL silver_assets table
    for the given media type. Used by the React front-end to populate
    FileBrowser, ObjectDetection, AudioAnalysis, and TextExtraction views.
    
    No Spark/Iceberg - queries silver_assets directly.
    """
    valid_types = {"image", "video", "audio", "document", "text", "pdf"}
    if media_type not in valid_types:
        raise HTTPException(
            status_code=422,
            detail=f"media_type must be one of {sorted(valid_types)}"
        )

    # Query PostgreSQL silver_assets table directly
    try:
        import psycopg2
        from pathlib import Path as _Path
        
        conn = psycopg2.connect(
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=int(os.getenv("POSTGRES_PORT", 5432)),
            database=os.getenv("POSTGRES_DB", "syniqai_metadata"),
            user=os.getenv("POSTGRES_USER", "syniqai_user"),
            password=os.getenv("POSTGRES_PASSWORD", "syniqai_password")
        )
        cursor = conn.cursor()
        
        # Map frontend media_type to file extensions (ai_processor stores extensions, not MIME types)
        if media_type == "image":
            file_type_filter = "('jpg','jpeg','png','gif','bmp','webp','tiff')"
        elif media_type == "video":
            file_type_filter = "('mp4','avi','mov','mkv','wmv','webm')"
        elif media_type == "audio":
            file_type_filter = "('mp3','wav','flac','aac','ogg','m4a')"
        elif media_type == "pdf":
            file_type_filter = "('pdf')"
        elif media_type == "document":
            file_type_filter = "('pdf','doc','docx')"
        elif media_type == "text":
            file_type_filter = "('txt','md','csv','json','log')"
        else:
            file_type_filter = f"('{media_type}')"
        
        cursor.execute(f"""
            SELECT 
                sa.id,
                sa.bronze_minio_key,
                sa.silver_minio_key,
                sa.file_type,
                sa.extraction_status,
                sa.processed_at,
                sa.content_tags,
                sa.summary,
                sa.ai_confidence_score,
                sa.file_size_bytes as file_size_bytes,
                sa.processed_at as last_modified
            FROM silver_assets sa
            WHERE sa.file_type IN {file_type_filter}
            ORDER BY sa.processed_at DESC
            LIMIT %s
        """, (limit,))
        
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        
        records = []
        for row in rows:
            asset_id, bronze_key, silver_key, file_type_val, status, processed_at, tags, summary, confidence, size, modified = row
            
            # Extract file name and extension
            file_name = bronze_key.split("/")[-1] if bronze_key else f"asset_{asset_id}"
            ext = _Path(file_name).suffix.lstrip(".") if "." in file_name else ""
            
            records.append({
                "id": asset_id,
                "file_name": file_name,
                "file_extension": ext,
                "file_type": file_type_val,
                "file_size_bytes": size,
                "last_modified": modified.isoformat() if modified else None,
                "processed_at": processed_at.isoformat() if processed_at else None,
                "s3_path": f"s3a://syniqai-silver/{silver_key}" if silver_key else None,
                "bronze_path": bronze_key,
                "silver_path": silver_key,
                "processing_status": status,  # success, failed, pending
                "content_tags": tags,
                "summary": summary,
                "ai_confidence": confidence,
            })
        
        return {
            "media_type": media_type,
            "records": records,
            "total": len(records),
            "source": "postgresql_silver_assets",
        }
        
    except Exception as exc:
        logger.error(f"PostgreSQL preview failed: {exc}")
        import traceback
        logger.error(traceback.format_exc())
        return {
            "media_type": media_type,
            "records": [],
            "total": 0,
            "source": "error",
            "error": str(exc),
        }


@router.post("/validate")
def validate_source_connectivity(
    mongodb_config: Optional[Dict[str, Any]] = None,
    s3_config: Optional[Dict[str, Any]] = None,
):
    """
    Validate that the configured source connectors (MongoDB / S3) are reachable.
    """
    results: Dict[str, Any] = {}

    if mongodb_config:
        try:
            from connectors.mongodb_connector import MongoDBConnector  # type: ignore
            conn = MongoDBConnector(mongodb_config)
            conn.connect()
            results["mongodb"] = {"status": "ok", "database": mongodb_config.get("database")}
            conn.client.close()
        except Exception as exc:
            results["mongodb"] = {"status": "error", "error": str(exc)}

    if s3_config:
        try:
            from connectors.s3_connector import S3Connector  # type: ignore
            conn = S3Connector(s3_config)
            ok = conn.connect()
            if ok:
                stats = conn.get_bucket_stats()
                results["s3"] = {"status": "ok", **stats}
                conn.disconnect()
            else:
                results["s3"] = {"status": "error", "error": "connect() returned False"}
        except Exception as exc:
            results["s3"] = {"status": "error", "error": str(exc)}

    if not results:
        return {"status": "no_connectors_provided", "results": {}}

    overall = "ok" if all(v.get("status") == "ok" for v in results.values()) else "partial"
    return {"status": overall, "results": results}


# ---------------------------------------------------------------------------
# ML Model Registry endpoints
# ---------------------------------------------------------------------------

@router.get("/embedding-models")
def list_embedding_models():
    """Return embedding models available in the ML registry."""
    try:
        reg = _get_ml_registry()
        return {"models": reg.get_embedding_models(), "total": len(reg.get_embedding_models())}
    except Exception as exc:
        logger.warning(f"list_embedding_models failed: {exc}")
        return {"models": [], "total": 0, "error": str(exc)}


@router.get("/vector-databases")
def list_vector_databases():
    """Return supported vector database backends."""
    try:
        reg = _get_ml_registry()
        dbs = reg.get_vector_databases()
        return {"databases": dbs, "total": len(dbs)}
    except Exception as exc:
        logger.warning(f"list_vector_databases failed: {exc}")
        return {"databases": [], "total": 0, "error": str(exc)}


# ---------------------------------------------------------------------------
# Quality Rules endpoints (backed by QualityRulesEngine / PostgreSQL)
# ---------------------------------------------------------------------------

@router.get("/quality/rules")
def get_all_quality_rules(
    media_type: Optional[str] = Query(None, description="Filter by media type"),
    category: Optional[str] = Query(None, description="Filter by category"),
):
    """
    Return quality rules for all (or a specific) media type.
    Rules are persisted in PostgreSQL and fully configurable.
    """
    try:
        engine = _get_rules_engine()
        rules = engine.get_quality_rules(media_type=media_type, category=category)
        return {"rules": rules, "total": len(rules), "media_type": media_type}
    except Exception as exc:
        logger.warning(f"get_all_quality_rules failed: {exc}")
        return {"rules": [], "total": 0, "error": str(exc)}


@router.put("/quality/rules/{media_type}/{rule_key}")
def upsert_quality_rule(media_type: str, rule_key: str, body: Dict[str, Any]):
    """Create or update a single quality rule in PostgreSQL."""
    valid_types = {"image", "video", "audio", "document", "text", "pdf"}
    if media_type not in valid_types:
        raise HTTPException(status_code=422, detail=f"media_type must be one of {sorted(valid_types)}")
    try:
        engine = _get_rules_engine()
        saved = engine.upsert_quality_rule(media_type, rule_key, body)
        return {"saved": saved, "media_type": media_type, "rule_key": rule_key}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/quality/datasets")
def get_quality_datasets():
    """
    Return a quality summary per media type from PostgreSQL silver_assets table.
    Provides file counts, success/failure rates, and average confidence scores.
    
    No Spark/Iceberg - queries silver_assets directly.
    """
    try:
        import psycopg2
        
        conn = psycopg2.connect(
            host="localhost",
            port=5432,
            database="syniqai_metadata",
            user="syniqai_user",
            password="syniqai_password"
        )
        cursor = conn.cursor()
        
        # Aggregate statistics by file_type from silver_assets
        cursor.execute("""
            SELECT 
                file_type,
                COUNT(*) as total_files,
                AVG(ai_confidence_score) as avg_confidence,
                SUM(CASE WHEN extraction_status = 'failed' THEN 1 ELSE 0 END) as failed_count,
                SUM(CASE WHEN extraction_status = 'success' THEN 1 ELSE 0 END) as success_count,
                SUM(CASE WHEN extraction_status = 'pending' THEN 1 ELSE 0 END) as pending_count
            FROM silver_assets
            GROUP BY file_type
            ORDER BY total_files DESC
        """)
        
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        
        engine = _get_rules_engine()
        datasets = []
        
        for row in rows:
            file_type, total, avg_conf, failed, success, pending = row
            
            # Extract media type from file_type (e.g., "image/jpeg" -> "image")
            media_type = file_type.split("/")[0] if "/" in file_type else "unknown"
            if media_type == "application":
                media_type = "document"  # application/pdf -> document
            elif media_type == "text":
                media_type = "text"
            
            rules = engine.get_quality_rules(media_type=media_type)
            
            # Calculate quality score based on success rate
            score = round((success / total * 100) if total > 0 else 100, 1)
            
            datasets.append({
                "id": file_type.replace("/", "_"),
                "name": f"{media_type.capitalize()} ({file_type})",
                "type": media_type.capitalize(),
                "media_type": media_type,
                "files": total,
                "success_count": success,
                "failed_count": failed,
                "pending_count": pending,
                "avg_confidence": round(avg_conf, 2) if avg_conf else None,
                "rule_count": len(rules),
                "score": score,
                "catalog": "postgresql_silver_assets",
            })
        
        return {"datasets": datasets, "total": len(datasets)}
        
    except Exception as exc:
        logger.warning(f"get_quality_datasets failed: {exc}")
        import traceback
        logger.error(traceback.format_exc())
        return {"datasets": [], "total": 0, "error": str(exc)}


@router.get("/quality/issues")
def get_quality_issues(
    media_type: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
):
    """
    Return per-file quality issues derived from failed Silver processing jobs.
    Falls back to scanning MinIO Bronze metadata when Silver is unavailable.
    """
    if _silver_job_tracker is None:
        return {"issues": [], "total": 0}
    try:
        all_jobs = _silver_job_tracker.list_jobs(limit=limit * 4)
        issues = []
        for job in all_jobs:
            if job.get("status") not in ("failed", "running"):
                continue
            mt = job.get("cleaning_summary", {}).get("media_type") or ""
            if media_type and mt != media_type:
                continue
            issues.append({
                "id": job.get("job_id"),
                "file": job.get("table_name") or job.get("entity") or "unknown",
                "issue": job.get("error_message") or job.get("message") or "Processing issue detected",
                "type": mt.capitalize() if mt else "Media",
                "severity": "high" if job.get("status") == "failed" else "medium",
                "detected": job.get("started_at") or job.get("created_at") or "",
                "media_type": mt,
            })
            if len(issues) >= limit:
                break
        return {"issues": issues, "total": len(issues)}
    except Exception as exc:
        logger.warning(f"get_quality_issues failed: {exc}")
        return {"issues": [], "total": 0, "error": str(exc)}


# ---------------------------------------------------------------------------
# Per-file analysis endpoints (LLM + ML via AnalysisService)
# ---------------------------------------------------------------------------

@router.get("/analysis/{media_type}")
def get_media_analysis(
    media_type: str,
    file_id: str = Query("", description="File identifier (name, path or record id)"),
    domain: str = Query("media"),
    entity: str = Query("assets"),
    limit: int = Query(1, le=20),
):
    """
    Return detailed analysis for a specific file.

    Steps:
      1. Fetch the matching record from the Silver preview endpoint
      2. Pass it to AnalysisService which orchestrates LLM + rule analysis
      3. Return enriched dict (transcript, keywords, detections, fields …)
    """
    valid_types = {"image", "video", "audio", "document", "text", "pdf"}
    if media_type not in valid_types:
        raise HTTPException(status_code=422, detail=f"media_type must be one of {sorted(valid_types)}")

    # Fetch the Silver / Bronze record for this file
    try:
        preview = preview_processed_records(
            media_type=media_type,
            domain=domain,
            entity=entity,
            limit=50,
        )
        records = preview.get("records", [])
        # Find matching record by file_id (file_name, s3_path, or any key)
        matching = None
        if file_id:
            for rec in records:
                if (
                    str(rec.get("file_name") or "") == file_id
                    or str(rec.get("doc_id") or "") == file_id
                    or file_id in str(rec.get("s3_path") or "")
                    or file_id in str(rec.get("file_path") or "")
                ):
                    matching = rec
                    break
        if matching is None and records:
            matching = records[0]
    except Exception:
        matching = None

    try:
        processor = _get_ai_processor()
        if processor is None:
            raise HTTPException(status_code=503, detail="AI processor not available")
        if matching is None:
            raise HTTPException(status_code=404, detail=f"No record found for file_id: {file_id}")
        bronze_key = matching.get("bronze_path") or matching.get("s3_path", "").replace("s3a://syniqai-bronze/", "")
        filename = matching.get("file_name", file_id)
        ext = matching.get("file_extension", "").lower()
        message = {
            "bronze_minio_key": bronze_key,
            "filename": filename,
            "file_type": ext,
            "source": domain,
            "size_bytes": matching.get("file_size_bytes", 0)
        }
        processor.process_message(message)
        from datetime import datetime
        date_str = datetime.now().strftime("%Y-%m-%d")
        silver_key = f"{ext}/{date_str}/{filename}.json"
        try:
            silver_bytes = processor.storage.download_file(
                processor.MINIO_SILVER_BUCKET, silver_key
            )
            import json
            return json.loads(silver_bytes.decode("utf-8"))
        except Exception:
            return {"status": "processed", "file": filename, "silver_key": silver_key}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"get_media_analysis (OpenRouter) failed: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/analysis/invalidate")
def invalidate_analysis_cache(file_id: Optional[str] = None):
    """Clear the analysis cache for a specific file or all files."""
    try:
        svc = _get_analysis_service()
        svc.invalidate_cache(file_id=file_id)
        return {"cleared": True, "file_id": file_id}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

