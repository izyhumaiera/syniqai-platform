"""
ML Model Registry
=================
Catalogue of ML / DL models available for unstructured media processing.

The registry is stored in PostgreSQL (`syniq_ml_models`) so models can be
added, toggled or versioned without restarting the backend.
A rich in-memory default catalogue is seeded on first run.

Each model record exposes:
  id           – unique slug
  name         – display name
  media_types  – list of media types this model handles
  category     – classification | detection | transcription | extraction | embedding
  framework    – PyTorch | ONNX | TensorFlow | OpenAI | HuggingFace …
  version      – semantic version string
  status       – deployed | experimental | deprecated
  description  – short prose description
  inputs       – what the model accepts
  outputs      – what it produces
  accuracy     – reported accuracy / WER / mAP etc. (string)
  speed        – Fast | Medium | Slow
  thumbnail    – emoji thumbnail for UI
  config       – arbitrary JSON for framework-specific params
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default model catalogue
# ---------------------------------------------------------------------------
_DEFAULT_MODELS: List[Dict[str, Any]] = [
    # ---- Image Classification ----
    {
        "id": "img_clf_resnet50",
        "name": "ResNet-50 Classifier",
        "media_types": ["image"],
        "category": "classification",
        "framework": "PyTorch",
        "version": "v1.0",
        "status": "deployed",
        "description": "General-purpose image classification using ResNet-50",
        "inputs": "Any resolution images (RGB)",
        "outputs": "Class labels + confidence scores",
        "accuracy": "76.1% Top-1 (ImageNet)",
        "speed": "Fast",
        "thumbnail": "🏷️",
        "config": {"top_k": 5, "input_size": 224},
    },
    # ---- Object Detection ----
    {
        "id": "obj_det_yolov8",
        "name": "YOLOv8 Object Detector",
        "media_types": ["image", "video"],
        "category": "detection",
        "framework": "ONNX",
        "version": "v1.0",
        "status": "deployed",
        "description": "Real-time object detection — 80 COCO classes",
        "inputs": "Images / Video frames (any resolution)",
        "outputs": "Bounding boxes, class labels, confidence",
        "accuracy": "mAP 53.9% (COCO val)",
        "speed": "Fast",
        "thumbnail": "🎯",
        "config": {"conf_threshold": 0.25, "iou_threshold": 0.45},
    },
    {
        "id": "obj_det_rcnn",
        "name": "Faster R-CNN Detector",
        "media_types": ["image"],
        "category": "detection",
        "framework": "PyTorch",
        "version": "v1.0",
        "status": "deployed",
        "description": "High-accuracy two-stage object detector",
        "inputs": "Images (any resolution)",
        "outputs": "Bounding boxes, masks, class labels",
        "accuracy": "mAP 60.2% (COCO val)",
        "speed": "Medium",
        "thumbnail": "🔍",
        "config": {},
    },
    # ---- Face / OCR ----
    {
        "id": "ocr_tesseract",
        "name": "Tesseract OCR Engine",
        "media_types": ["image", "document"],
        "category": "extraction",
        "framework": "Tesseract",
        "version": "v5.0",
        "status": "deployed",
        "description": "Open-source OCR for image-based text extraction",
        "inputs": "Scanned images, screenshots, PDFs",
        "outputs": "Extracted text + word-level bounding boxes",
        "accuracy": "~97% on clean printout",
        "speed": "Medium",
        "thumbnail": "📝",
        "config": {"lang": "eng", "oem": 3, "psm": 3},
    },
    # ---- Document AI ----
    {
        "id": "doc_ai_pdfplumber",
        "name": "Document AI Extractor",
        "media_types": ["document", "text"],
        "category": "extraction",
        "framework": "pdfplumber / Tesseract",
        "version": "v1.0",
        "status": "deployed",
        "description": "Extract structured text, tables and key fields from PDFs and DOCXs",
        "inputs": "PDF, DOCX, DOC, TIFF scans",
        "outputs": "Extracted text, page count, language, named entities",
        "accuracy": "~94% on structured PDF",
        "speed": "Medium",
        "thumbnail": "📄",
        "config": {"extract_tables": True, "detect_language": True, "pii_redaction": False},
    },
    # ---- Audio / Speech ----
    {
        "id": "asr_whisper",
        "name": "Whisper ASR (Speech-to-Text)",
        "media_types": ["audio"],
        "category": "transcription",
        "framework": "OpenAI Whisper",
        "version": "v3",
        "status": "deployed",
        "description": "Multilingual automatic speech recognition with speaker diarisation",
        "inputs": "Audio files (MP3, WAV, FLAC, AAC, OGG)",
        "outputs": "Transcript + timestamps + detected language + sentiment",
        "accuracy": "WER ~5% (English)",
        "speed": "Medium",
        "thumbnail": "🎙️",
        "config": {"model_size": "base", "language": "auto", "task": "transcribe"},
    },
    # ---- Video ----
    {
        "id": "vid_proc_opencv",
        "name": "Video Frame Processor",
        "media_types": ["video"],
        "category": "extraction",
        "framework": "OpenCV",
        "version": "v1.0",
        "status": "deployed",
        "description": "Extract key-frames, compute quality metrics and detect scenes",
        "inputs": "Video files (MP4, AVI, MOV, MKV)",
        "outputs": "Key-frames, metadata, quality score, scene timestamps",
        "accuracy": "—",
        "speed": "Fast",
        "thumbnail": "🎬",
        "config": {"keyframe_interval": 30, "scene_threshold": 0.3},
    },
    # ---- Embeddings ----
    {
        "id": "emb_clip",
        "name": "CLIP Embeddings (OpenAI)",
        "media_types": ["image", "text"],
        "category": "embedding",
        "framework": "PyTorch / CLIP",
        "version": "ViT-B/32",
        "status": "deployed",
        "description": "Joint image + text embedding model from OpenAI",
        "inputs": "Images (RGB) or text strings",
        "outputs": "512-dimensional embedding vector",
        "accuracy": "Zero-shot ImageNet 63.4%",
        "speed": "Fast",
        "thumbnail": "📐",
        "config": {"dimensions": 512, "modalities": ["image", "text"]},
    },
    {
        "id": "emb_bert",
        "name": "BERT Text Embeddings",
        "media_types": ["text", "document"],
        "category": "embedding",
        "framework": "HuggingFace Transformers",
        "version": "bert-base-uncased",
        "status": "deployed",
        "description": "Contextual text embeddings for semantic search and clustering",
        "inputs": "Text strings (up to 512 tokens)",
        "outputs": "768-dimensional dense vector",
        "accuracy": "—",
        "speed": "Medium",
        "thumbnail": "🔤",
        "config": {"dimensions": 768, "modalities": ["text"]},
    },
    {
        "id": "emb_whisper_audio",
        "name": "Whisper Audio Embeddings",
        "media_types": ["audio"],
        "category": "embedding",
        "framework": "OpenAI Whisper",
        "version": "v3",
        "status": "deployed",
        "description": "Audio feature embeddings extracted from the Whisper encoder",
        "inputs": "Audio files",
        "outputs": "512-dimensional encoder embedding",
        "accuracy": "—",
        "speed": "Medium",
        "thumbnail": "🔊",
        "config": {"dimensions": 512, "modalities": ["audio"]},
    },
    {
        "id": "emb_videomae",
        "name": "VideoMAE Embeddings",
        "media_types": ["video"],
        "category": "embedding",
        "framework": "PyTorch / HuggingFace",
        "version": "v1.0",
        "status": "experimental",
        "description": "Masked autoencoder video embeddings for temporal understanding",
        "inputs": "Video clips (16 frames)",
        "outputs": "768-dimensional temporal embedding",
        "accuracy": "86.1% Kinetics-400",
        "speed": "Slow",
        "thumbnail": "🎞️",
        "config": {"dimensions": 768, "modalities": ["video"]},
    },
]

# ---------------------------------------------------------------------------
# Vector database catalogue
# ---------------------------------------------------------------------------
_VECTOR_DATABASES: List[Dict[str, Any]] = [
    {"id": "minio_flat", "name": "MinIO Flat Index",
     "type": "Built-in", "icon": "🗄️",
     "description": "Stores embeddings as Parquet in MinIO — no external service needed",
     "config": {"bucket": "syniqai-silver", "prefix": "embeddings/"}},
    {"id": "pinecone", "name": "Pinecone",
     "type": "Cloud", "icon": "☁️",
     "description": "Fully-managed cloud vector database",
     "config": {"api_key_env": "PINECONE_API_KEY", "environment_env": "PINECONE_ENV"}},
    {"id": "milvus", "name": "Milvus",
     "type": "Self-hosted", "icon": "🏠",
     "description": "Open-source vector DB for billion-scale similarity search",
     "config": {"host_env": "MILVUS_HOST", "port_env": "MILVUS_PORT"}},
    {"id": "weaviate", "name": "Weaviate",
     "type": "Hybrid", "icon": "🔀",
     "description": "Hybrid vector DB with built-in keyword search",
     "config": {"url_env": "WEAVIATE_URL"}},
    {"id": "qdrant", "name": "Qdrant",
     "type": "Fast", "icon": "⚡",
     "description": "Rust-powered high-performance vector search engine",
     "config": {"host_env": "QDRANT_HOST", "port_env": "QDRANT_PORT"}},
]


class MLModelRegistry:
    """
    ML model catalogue backed by PostgreSQL (`syniq_ml_models`).
    Falls back to the built-in list when the DB is unavailable.
    """

    DDL = """
    CREATE TABLE IF NOT EXISTS syniq_ml_models (
        id          TEXT PRIMARY KEY,
        name        TEXT NOT NULL,
        media_types JSONB NOT NULL DEFAULT '[]',
        category    TEXT NOT NULL,
        framework   TEXT,
        version     TEXT,
        status      TEXT NOT NULL DEFAULT 'deployed',
        description TEXT,
        inputs      TEXT,
        outputs     TEXT,
        accuracy    TEXT,
        speed       TEXT,
        thumbnail   TEXT,
        config      JSONB NOT NULL DEFAULT '{}',
        created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    """

    def __init__(self, postgres_config=None):
        self._cfg = postgres_config
        self._db_ok = False
        self._try_init()

    def _try_init(self) -> None:
        try:
            conn = self._connect()
            with conn:
                with conn.cursor() as cur:
                    cur.execute(self.DDL)
                    cur.execute("SELECT COUNT(*) FROM syniq_ml_models")
                    if cur.fetchone()[0] == 0:
                        self._seed(cur)
            conn.close()
            self._db_ok = True
            logger.info("MLModelRegistry: PostgreSQL-backed model registry initialised")
        except Exception as exc:
            logger.warning(f"MLModelRegistry: DB unavailable ({exc}); using built-in catalogue")

    def _connect(self):
        import psycopg2  # type: ignore
        cfg = self._cfg
        if cfg is None:
            return psycopg2.connect(
                host=os.getenv("POSTGRES_HOST", "localhost"),
                port=int(os.getenv("POSTGRES_PORT", "5432")),
                dbname=os.getenv("POSTGRES_DB", "syniqai_metadata"),
                user=os.getenv("POSTGRES_USER", "syniqai_user"),
                password=os.getenv("POSTGRES_PASSWORD", "syniqai_password"),
            )
        return psycopg2.connect(
            host=cfg.host, port=cfg.port,
            dbname=cfg.database, user=cfg.user, password=cfg.password,
        )

    def _seed(self, cur) -> None:
        for m in _DEFAULT_MODELS:
            cur.execute(
                """
                INSERT INTO syniq_ml_models
                  (id,name,media_types,category,framework,version,status,
                   description,inputs,outputs,accuracy,speed,thumbnail,config)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (id) DO NOTHING
                """,
                (
                    m["id"], m["name"], json.dumps(m["media_types"]),
                    m["category"], m.get("framework"), m.get("version"),
                    m.get("status", "deployed"), m.get("description", ""),
                    m.get("inputs", ""), m.get("outputs", ""),
                    m.get("accuracy", "—"), m.get("speed", "Medium"),
                    m.get("thumbnail", "🤖"), json.dumps(m.get("config", {})),
                ),
            )

    # ------------------------------------------------------------------
    def get_all_models(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Return all models, optionally filtered by status."""
        if self._db_ok:
            try:
                conn = self._connect()
                with conn:
                    with conn.cursor() as cur:
                        where = "WHERE status = %s" if status else ""
                        params = [status] if status else []
                        cur.execute(
                            f"SELECT id,name,media_types,category,framework,version,status,"
                            f"description,inputs,outputs,accuracy,speed,thumbnail,config,updated_at "
                            f"FROM syniq_ml_models {where} ORDER BY category,id",
                            params,
                        )
                        rows = cur.fetchall()
                conn.close()
                return [self._row_to_dict(r) for r in rows]
            except Exception as exc:
                logger.warning(f"MLModelRegistry.get_all_models failed: {exc}")

        models = _DEFAULT_MODELS
        if status:
            models = [m for m in models if m.get("status") == status]
        return [dict(m) for m in models]

    def get_models_for_type(self, media_type: str) -> List[Dict[str, Any]]:
        """Return models that handle the given media type."""
        all_models = self.get_all_models()
        return [m for m in all_models if media_type in (m.get("media_types") or [])]

    def get_embedding_models(self) -> List[Dict[str, Any]]:
        """Return models in the 'embedding' category."""
        return [m for m in self.get_all_models() if m.get("category") == "embedding"]

    def get_vector_databases(self) -> List[Dict[str, Any]]:
        return list(_VECTOR_DATABASES)

    @staticmethod
    def _row_to_dict(r) -> Dict[str, Any]:
        return {
            "id": r[0], "name": r[1],
            "media_types": r[2] if isinstance(r[2], list) else json.loads(r[2] or "[]"),
            "category": r[3], "framework": r[4], "version": r[5], "status": r[6],
            "description": r[7], "inputs": r[8], "outputs": r[9],
            "accuracy": r[10], "speed": r[11], "thumbnail": r[12],
            "config": r[13] if isinstance(r[13], dict) else json.loads(r[13] or "{}"),
            "updated_at": r[14].isoformat() if r[14] else None,
        }
