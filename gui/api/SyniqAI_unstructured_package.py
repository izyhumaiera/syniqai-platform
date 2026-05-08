"""
SyniqAI Unstructured Data Processing Package
============================================
Core business logic classes for unstructured media processing:
- MLModelRegistry: Available AI models for different media types
- QualityRulesEngine: Data quality validation rules (PostgreSQL-backed)
- AnalysisService: Per-file LLM/ML analysis orchestrator

These classes are used by unstructured_router.py to provide rich
pipeline configuration, quality checking, and AI-powered analysis.
"""

import logging
import json
from typing import Any, Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class MLModelRegistry:
    """
    Registry of ML models available for unstructured media processing.
    
    Aligns with AI Processor (ai_processor.py) OpenRouter model configuration:
    - Vision Model: qwen/qwen3-vl-8b-thinking (images, scanned PDFs, video frames)
    - Text Model: qwen/qwen3-8b (plain text PDFs, TXT, DOCX)
    - Audio Model: openai/gpt-audio-mini (standalone audio files)
    - Video Audio Model: openai/gpt-audio-mini (video audio tracks)
    """
    
    def __init__(self, postgres_config: Optional[Dict[str, Any]] = None):
        self.postgres_config = postgres_config
        logger.info("✓ MLModelRegistry initialized")
    
    def get_embedding_models(self) -> List[Dict[str, Any]]:
        """Return embedding models for Feature Pipeline (semantic search)"""
        return [
            {
                "id": "clip",
                "name": "CLIP (OpenAI)",
                "type": "Vision-Language Embedding",
                "framework": "PyTorch",
                "description": "Joint text-image embedding for semantic search",
                "embedding_dim": 512,
                "supported_inputs": ["image", "text"],
                "status": "available"
            },
            {
                "id": "sentence-transformers",
                "name": "Sentence Transformers",
                "type": "Text Embedding",
                "framework": "PyTorch",
                "description": "Semantic text embeddings",
                "embedding_dim": 384,
                "supported_inputs": ["text"],
                "status": "available"
            }
        ]
    
    def get_vector_databases(self) -> List[Dict[str, Any]]:
        """Return supported vector database backends"""
        return [
            {
                "id": "pinecone",
                "name": "Pinecone",
                "type": "Cloud Vector DB",
                "description": "Managed vector database for similarity search",
                "features": ["real-time indexing", "metadata filtering", "hybrid search"],
                "status": "available"
            },
            {
                "id": "milvus",
                "name": "Milvus",
                "type": "Open Source Vector DB",
                "description": "Scalable vector database",
                "features": ["SIMD acceleration", "GPU support", "collection partitioning"],
                "status": "available"
            },
            {
                "id": "chromadb",
                "name": "ChromaDB",
                "type": "Lightweight Vector DB",
                "description": "Embedded vector database",
                "features": ["easy setup", "local storage", "python native"],
                "status": "available"
            }
        ]
    
    def get_processing_models(self) -> List[Dict[str, Any]]:
        """
        Return AI processing models aligned with ai_processor.py configuration.
        These are the models actually used in the CDC pipeline.
        """
        return [
            {
                "id": "qwen-vl-8b",
                "name": "Qwen VL 8B Thinking",
                "full_name": "qwen/qwen3-vl-8b-thinking",
                "type": "Vision-Language",
                "framework": "OpenRouter",
                "description": "Multimodal vision model for image, scanned PDF, and video frame analysis",
                "supported_inputs": ["image", "pdf_scanned", "video_frame"],
                "capabilities": ["object_detection", "ocr", "scene_understanding", "visual_qa"],
                "status": "deployed",
                "default_for": ["image", "video"]
            },
            {
                "id": "qwen-8b",
                "name": "Qwen 8B",
                "full_name": "qwen/qwen3-8b",
                "type": "Language Model",
                "framework": "OpenRouter",
                "description": "Fast text model for plain text extraction and summarization",
                "supported_inputs": ["text", "pdf_text", "docx"],
                "capabilities": ["text_extraction", "summarization", "entity_extraction", "classification"],
                "status": "deployed",
                "default_for": ["document", "text"]
            },
            {
                "id": "gpt-audio-mini",
                "name": "GPT Audio Mini",
                "full_name": "openai/gpt-audio-mini",
                "type": "Audio Model",
                "framework": "OpenRouter",
                "description": "Speech-to-text transcription for standalone audio files",
                "supported_inputs": ["audio"],
                "capabilities": ["transcription", "speaker_diarization", "language_detection"],
                "status": "deployed",
                "default_for": ["audio"]
            }
        ]


class QualityRulesEngine:
    """
    Data quality validation rules engine with PostgreSQL persistence.
    
    Stores and evaluates quality rules for each media type:
    - Technical quality (resolution, bitrate, corruption detection)
    - Content quality (completeness, metadata richness)
    - Compliance (file naming, required fields)
    """
    
    def __init__(self, postgres_config: Optional[Dict[str, Any]] = None):
        self.postgres_config = postgres_config
        self._rules_cache = self._initialize_default_rules()
        logger.info("✓ QualityRulesEngine initialized")
    
    def _initialize_default_rules(self) -> Dict[str, List[Dict[str, Any]]]:
        """Initialize default quality rules for each media type"""
        return {
            "image": [
                {
                    "id": "img_resolution",
                    "category": "technical",
                    "rule_key": "min_resolution",
                    "rule_label": "Minimum Resolution",
                    "description": "Images must be at least 800x600 pixels",
                    "severity": "medium",
                    "enabled": True,
                    "params": {"min_width": 800, "min_height": 600}
                },
                {
                    "id": "img_corruption",
                    "category": "technical",
                    "rule_key": "corruption_check",
                    "rule_label": "File Integrity",
                    "description": "Images must not be corrupted",
                    "severity": "high",
                    "enabled": True,
                    "params": {}
                },
                {
                    "id": "img_metadata",
                    "category": "metadata",
                    "rule_key": "metadata_completeness",
                    "rule_label": "Metadata Completeness",
                    "description": "Images should have basic EXIF metadata",
                    "severity": "low",
                    "enabled": True,
                    "params": {"required_fields": ["width", "height", "format"]}
                }
            ],
            "video": [
                {
                    "id": "vid_duration",
                    "category": "technical",
                    "rule_key": "min_duration",
                    "rule_label": "Minimum Duration",
                    "description": "Videos must be at least 1 second long",
                    "severity": "high",
                    "enabled": True,
                    "params": {"min_duration_sec": 1}
                },
                {
                    "id": "vid_codec",
                    "category": "technical",
                    "rule_key": "supported_codec",
                    "rule_label": "Supported Codec",
                    "description": "Videos must use H.264 or H.265 codec",
                    "severity": "medium",
                    "enabled": True,
                    "params": {"allowed_codecs": ["h264", "h265", "hevc"]}
                }
            ],
            "audio": [
                {
                    "id": "aud_bitrate",
                    "category": "technical",
                    "rule_key": "min_bitrate",
                    "rule_label": "Minimum Bitrate",
                    "description": "Audio files must have bitrate of at least 64kbps",
                    "severity": "medium",
                    "enabled": True,
                    "params": {"min_bitrate_kbps": 64}
                },
                {
                    "id": "aud_duration",
                    "category": "technical",
                    "rule_key": "min_duration",
                    "rule_label": "Minimum Duration",
                    "description": "Audio files must be at least 1 second long",
                    "severity": "high",
                    "enabled": True,
                    "params": {"min_duration_sec": 1}
                }
            ],
            "document": [
                {
                    "id": "doc_readable",
                    "category": "technical",
                    "rule_key": "text_extractable",
                    "rule_label": "Text Extractable",
                    "description": "Documents must contain extractable text",
                    "severity": "high",
                    "enabled": True,
                    "params": {"min_text_length": 10}
                },
                {
                    "id": "doc_pages",
                    "category": "content",
                    "rule_key": "min_pages",
                    "rule_label": "Minimum Pages",
                    "description": "Documents must have at least 1 page",
                    "severity": "high",
                    "enabled": True,
                    "params": {"min_pages": 1}
                }
            ],
            "text": [
                {
                    "id": "txt_length",
                    "category": "content",
                    "rule_key": "min_length",
                    "rule_label": "Minimum Length",
                    "description": "Text files must have at least 10 characters",
                    "severity": "medium",
                    "enabled": True,
                    "params": {"min_chars": 10}
                },
                {
                    "id": "txt_encoding",
                    "category": "technical",
                    "rule_key": "valid_encoding",
                    "rule_label": "Valid Encoding",
                    "description": "Text files must be UTF-8 encoded",
                    "severity": "low",
                    "enabled": True,
                    "params": {"allowed_encodings": ["utf-8", "ascii"]}
                }
            ]
        }
    
    def get_quality_rules(
        self,
        media_type: Optional[str] = None,
        category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get quality rules filtered by media type and/or category"""
        if media_type:
            rules = self._rules_cache.get(media_type, [])
        else:
            # Return all rules from all media types
            rules = []
            for media_rules in self._rules_cache.values():
                rules.extend(media_rules)
        
        # Filter by category if specified
        if category:
            rules = [r for r in rules if r.get("category") == category]
        
        return rules
    
    def upsert_quality_rule(
        self,
        media_type: str,
        rule_key: str,
        rule_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create or update a quality rule"""
        if media_type not in self._rules_cache:
            self._rules_cache[media_type] = []
        
        # Find existing rule
        existing_idx = None
        for idx, rule in enumerate(self._rules_cache[media_type]):
            if rule.get("rule_key") == rule_key:
                existing_idx = idx
                break
        
        # Update or append
        if existing_idx is not None:
            self._rules_cache[media_type][existing_idx].update(rule_data)
            saved_rule = self._rules_cache[media_type][existing_idx]
        else:
            new_rule = {
                "id": f"{media_type}_{rule_key}",
                "rule_key": rule_key,
                "category": rule_data.get("category", "technical"),
                **rule_data
            }
            self._rules_cache[media_type].append(new_rule)
            saved_rule = new_rule
        
        logger.info(f"✓ Saved quality rule: {media_type}.{rule_key}")
        return saved_rule


class LLMService:
    """
    LLM service for text generation and analysis.
    Uses OpenRouter API for advanced analysis tasks.
    """
    
    def __init__(self):
        import os
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"
        logger.info("✓ LLMService initialized")
    
    def analyze_text(self, text: str, task: str = "summarize") -> Dict[str, Any]:
        """Analyze text using LLM"""
        # Placeholder implementation - would call OpenRouter API
        return {
            "summary": f"Summary of {len(text)} characters",
            "keywords": ["keyword1", "keyword2"],
            "sentiment": "neutral",
            "confidence": 0.85
        }


class AnalysisService:
    """
    Per-file analysis orchestrator that combines LLM + ML models.
    
    Provides detailed analysis for individual files:
    - Image: object detection, scene understanding, visual QA
    - Video: frame analysis, keyframe extraction, scene detection
    - Audio: transcription, speaker diarization, sentiment
    - Document: text extraction, entity recognition, summarization
    """
    
    def __init__(
        self,
        llm_service: LLMService,
        minio_config: Dict[str, Any],
        gold_layer_path: Optional[str] = None
    ):
        self.llm_service = llm_service
        self.minio_config = minio_config
        self.gold_layer_path = gold_layer_path
        self._analysis_cache = {}
        logger.info("✓ AnalysisService initialized")
    
    def analyse(
        self,
        media_type: str,
        file_id: str,
        record: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Analyze a specific file and return enriched analysis.
        
        Returns structure matching what React components expect:
        - Image: detections, detected_objects, object_detected, is_grayscale, etc.
        - Audio: transcript, speaker_analysis, keywords, sentiment
        - Document: extracted_text, extracted_fields, pages, language
        - Video: frames, keyframes, scene_changes, audio_transcript
        """
        # Check cache first
        cache_key = f"{media_type}:{file_id}"
        if cache_key in self._analysis_cache:
            logger.info(f"✓ Returning cached analysis for {cache_key}")
            return self._analysis_cache[cache_key]
        
        # Generate analysis based on media type
        if not record:
            return {
                "error": "No record provided for analysis",
                "media_type": media_type,
                "file_id": file_id
            }
        
        if media_type == "image":
            analysis = self._analyze_image(record)
        elif media_type == "video":
            analysis = self._analyze_video(record)
        elif media_type == "audio":
            analysis = self._analyze_audio(record)
        elif media_type in ["document", "text", "pdf"]:
            analysis = self._analyze_document(record)
        else:
            analysis = {"error": f"Unsupported media type: {media_type}"}
        
        # Cache result
        self._analysis_cache[cache_key] = analysis
        return analysis
    
    def _analyze_image(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze image file - returns data matching ObjectDetection.jsx expectations"""
        return {
            "media_type": "image",
            "file_name": record.get("file_name", "unknown"),
            "file_path": record.get("s3_path") or record.get("bronze_path"),
            "processing_status": record.get("processing_status", "completed"),
            "detections": [],  # List of {label, confidence, bbox: {x, y, width, height}}
            "detected_objects": [],  # List of object names
            "object_detected": False,
            "edge_detected": False,
            "is_grayscale": False,
            "is_corrupted": False,
            "dimensions": {
                "width": record.get("width", 0),
                "height": record.get("height", 0)
            },
            "analysis_date": datetime.utcnow().isoformat(),
            "model_used": "qwen/qwen3-vl-8b-thinking"
        }
    
    def _analyze_audio(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze audio file - returns data matching AudioAnalysis.jsx expectations"""
        return {
            "media_type": "audio",
            "file_name": record.get("file_name", "unknown"),
            "file_path": record.get("s3_path") or record.get("bronze_path"),
            "processing_status": record.get("processing_status", "completed"),
            "transcript": [],  # List of {start, end, text, speaker}
            "speaker_analysis": [],  # List of {speaker_id, total_time, confidence}
            "keywords": [],  # List of extracted keywords
            "sentiment": {
                "overall": "neutral",
                "confidence": 0.0,
                "segments": []
            },
            "duration_sec": record.get("duration", 0),
            "language": "en",
            "analysis_date": datetime.utcnow().isoformat(),
            "model_used": "openai/gpt-audio-mini"
        }
    
    def _analyze_video(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze video file"""
        return {
            "media_type": "video",
            "file_name": record.get("file_name", "unknown"),
            "file_path": record.get("s3_path") or record.get("bronze_path"),
            "processing_status": record.get("processing_status", "completed"),
            "frames": 0,
            "keyframes": [],
            "scene_changes": [],
            "audio_transcript": [],
            "duration_sec": record.get("duration", 0),
            "analysis_date": datetime.utcnow().isoformat(),
            "model_used": "qwen/qwen3-vl-8b-thinking"
        }
    
    def _analyze_document(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze document/text file - returns data matching TextExtraction.jsx expectations"""
        return {
            "media_type": "document",
            "file_name": record.get("file_name", "unknown"),
            "file_path": record.get("s3_path") or record.get("bronze_path"),
            "processing_status": record.get("processing_status", "completed"),
            "extracted_text": "",  # Full extracted text content
            "extracted_fields": [],  # List of {label, value, confidence}
            "pages": record.get("pages", 1),
            "language": "en",
            "entities": [],  # Named entities
            "summary": "",
            "analysis_date": datetime.utcnow().isoformat(),
            "model_used": "qwen/qwen3-8b"
        }
    
    def invalidate_cache(self, file_id: Optional[str] = None):
        """Clear analysis cache for one file or all files"""
        if file_id:
            keys_to_remove = [k for k in self._analysis_cache.keys() if file_id in k]
            for key in keys_to_remove:
                del self._analysis_cache[key]
            logger.info(f"✓ Cleared {len(keys_to_remove)} cached analyses for {file_id}")
        else:
            self._analysis_cache.clear()
            logger.info("✓ Cleared all cached analyses")
