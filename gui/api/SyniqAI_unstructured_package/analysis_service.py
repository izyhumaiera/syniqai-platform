"""
Analysis Service
================
Per-file analysis dispatch for the Unstructured Silver Layer.

Orchestrates:
  1. Looks up cached analysis stored in the Silver Iceberg table or MinIO
  2. Falls back to on-demand lightweight analysis using LLMService
  3. Stores results back so subsequent calls are instant

Supported media types:
  audio    → transcript, speaker diarisation, sentiment, keywords
  image    → object detections (from Silver record), dimensions, quality
  video    → frame count, key-frames, quality score
  document → extracted text, structured fields, language, PII flag
  text     → sentiment, keywords, language, entities
"""
from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .llm_service import LLMService

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class AnalysisService:
    """
    Coordinates per-file analysis across ML / LLM services and the data lake.
    """

    def __init__(
        self,
        llm_service: Optional[LLMService] = None,
        minio_config: Optional[Dict[str, Any]] = None,
        gold_layer_path: Optional[str] = None,
    ):
        self._llm = llm_service or LLMService()
        self._minio_cfg = minio_config or {}
        self._gold_path = gold_layer_path
        # In-process analysis cache {cache_key → result_dict}
        self._cache: Dict[str, Dict[str, Any]] = {}

    # ------------------------------------------------------------------
    # Audio analysis
    # ------------------------------------------------------------------

    def get_audio_analysis(
        self,
        file_id: str,
        record: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Return full audio analysis for a given file.

        record is an optional Bronze / Silver record dict; if provided its
        fields are merged into the response (no re-computation needed).
        """
        cache_key = f"audio:{file_id}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        rec = record or {}
        raw_text = rec.get("extracted_text") or rec.get("transcription") or ""
        segments: List[Dict] = rec.get("transcript_segments") or []

        # ---- Transcript -------------------------------------------------
        if raw_text:
            llm_result = self._llm.analyse_transcript(raw_text)
            enriched_segments = self._llm.analyse_speaker_segments(segments)
        else:
            llm_result = {"overall_sentiment": "neutral", "sentiment_score": 0.5,
                          "keywords": [], "summary": "", "language": "en"}
            enriched_segments = segments

        # ---- Speaker analysis ------------------------------------------
        speaker_map: Dict[str, Dict] = {}
        for seg in enriched_segments:
            sp = seg.get("speaker", "Unknown")
            if sp not in speaker_map:
                speaker_map[sp] = {"speaker": sp, "segments": 0, "words": 0,
                                   "sentiments": [], "duration_s": 0}
            speaker_map[sp]["segments"] += 1
            speaker_map[sp]["words"] += len((seg.get("text") or "").split())
            if seg.get("sentiment"):
                speaker_map[sp]["sentiments"].append(seg["sentiment"])
        speaker_list = []
        for sp_data in speaker_map.values():
            sentiments = sp_data["sentiments"]
            dominant = max(set(sentiments), key=sentiments.count) if sentiments else "neutral"
            pct = 100 // max(len(speaker_map), 1)
            speaker_list.append({
                "speaker": sp_data["speaker"],
                "words": sp_data["words"],
                "talkTime": f"{pct}%",
                "sentiment": dominant,
            })

        result = {
            "file_id": file_id,
            "media_type": "audio",
            "duration": rec.get("duration_seconds"),
            "sample_rate": rec.get("sample_rate_hz"),
            "channels": rec.get("channels"),
            "is_silent": rec.get("is_silent"),
            "avg_volume_db": rec.get("average_volume_db"),
            "transcript": enriched_segments,
            "extracted_text": raw_text,
            "speaker_analysis": speaker_list,
            "keywords": llm_result.get("keywords", []),
            "overall_sentiment": llm_result.get("overall_sentiment", "neutral"),
            "sentiment_score": llm_result.get("sentiment_score", 0.5),
            "summary": llm_result.get("summary", ""),
            "language": llm_result.get("language", rec.get("detected_language", "en")),
            "analysed_at": _now_iso(),
            "source": "silver_record" if raw_text else "pending",
        }
        self._cache[cache_key] = result
        return result

    # ------------------------------------------------------------------
    # Image / video analysis
    # ------------------------------------------------------------------

    def get_image_analysis(
        self,
        file_id: str,
        record: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Return image quality metrics and any stored detection results."""
        cache_key = f"image:{file_id}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        rec = record or {}
        detections: List[Dict] = rec.get("detections") or rec.get("detected_objects") or []

        result = {
            "file_id": file_id,
            "media_type": "image",
            "width": rec.get("width"),
            "height": rec.get("height"),
            "format": rec.get("format") or rec.get("file_extension"),
            "size_bytes": rec.get("size_bytes"),
            "blur_score": rec.get("blur_score"),
            "brightness_avg": rec.get("brightness_avg"),
            "is_corrupted": rec.get("is_corrupted", False),
            "processing_status": rec.get("processing_status", "pending"),
            "detections": detections,
            "detection_count": len(detections),
            "analysed_at": _now_iso(),
            "source": "silver_record",
        }
        self._cache[cache_key] = result
        return result

    def get_video_analysis(
        self,
        file_id: str,
        record: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        cache_key = f"video:{file_id}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        rec = record or {}
        result = {
            "file_id": file_id,
            "media_type": "video",
            "duration_seconds": rec.get("duration_seconds"),
            "fps": rec.get("fps"),
            "frame_count": rec.get("frame_count"),
            "codec": rec.get("codec"),
            "resolution": f"{rec.get('width', '?')}×{rec.get('height', '?')}",
            "quality_score": rec.get("quality_score"),
            "keyframes": rec.get("keyframes", []),
            "processing_status": rec.get("processing_status", "pending"),
            "analysed_at": _now_iso(),
            "source": "silver_record",
        }
        self._cache[cache_key] = result
        return result

    # ------------------------------------------------------------------
    # Document / text analysis
    # ------------------------------------------------------------------

    def get_document_analysis(
        self,
        file_id: str,
        record: Optional[Dict[str, Any]] = None,
        doc_type: str = "general",
    ) -> Dict[str, Any]:
        """Return text extraction + structured field analysis for a document."""
        cache_key = f"doc:{file_id}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        rec = record or {}
        raw_text = rec.get("extracted_text") or rec.get("text_preview") or ""

        # Extract structured fields using LLM / rule-based fallback
        fields = self._llm.extract_document_fields(raw_text, doc_type=doc_type)
        lang = rec.get("detected_language") or self._llm.detect_language(raw_text)
        summary = self._llm.summarise(raw_text)

        result = {
            "file_id": file_id,
            "media_type": "document",
            "file_name": rec.get("file_name"),
            "file_extension": rec.get("file_extension"),
            "page_count": rec.get("page_count"),
            "size_bytes": rec.get("size_bytes"),
            "extracted_text": raw_text,
            "text_length": len(raw_text),
            "word_count": len(raw_text.split()) if raw_text else 0,
            "extracted_fields": fields,
            "detected_language": lang,
            "is_corrupted": rec.get("is_corrupted", False),
            "summary": summary,
            "confidence": rec.get("confidence"),
            "processing_status": rec.get("processing_status", "pending"),
            "analysed_at": _now_iso(),
            "source": "silver_record" if raw_text else "pending",
        }
        self._cache[cache_key] = result
        return result

    def get_text_analysis(
        self,
        file_id: str,
        record: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        cache_key = f"text:{file_id}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        rec = record or {}
        raw_text = rec.get("extracted_text") or rec.get("raw_content") or ""
        llm_result = self._llm.analyse_transcript(raw_text) if raw_text else {}
        fields = self._llm.extract_document_fields(raw_text) if raw_text else []

        result = {
            "file_id": file_id,
            "media_type": "text",
            "extracted_text": raw_text,
            "word_count": len(raw_text.split()) if raw_text else 0,
            "overall_sentiment": llm_result.get("overall_sentiment", "neutral"),
            "sentiment_score": llm_result.get("sentiment_score", 0.5),
            "keywords": llm_result.get("keywords", []),
            "extracted_fields": fields,
            "language": llm_result.get("language", "en"),
            "summary": llm_result.get("summary", ""),
            "processing_status": rec.get("processing_status", "pending"),
            "analysed_at": _now_iso(),
            "source": "silver_record" if raw_text else "pending",
        }
        self._cache[cache_key] = result
        return result

    # ------------------------------------------------------------------
    # Generic dispatcher
    # ------------------------------------------------------------------

    def analyse(
        self,
        media_type: str,
        file_id: str,
        record: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Dispatch to the correct per-type analysis method."""
        dispatch = {
            "audio": self.get_audio_analysis,
            "image": self.get_image_analysis,
            "video": self.get_video_analysis,
            "document": self.get_document_analysis,
            "pdf": self.get_document_analysis,
            "text": self.get_text_analysis,
        }
        fn = dispatch.get(media_type)
        if fn is None:
            return {"error": f"Unsupported media_type: {media_type}"}
        return fn(file_id, record)  # type: ignore[call-arg]

    def invalidate_cache(self, file_id: Optional[str] = None) -> None:
        """Clear one or all cached analysis results."""
        if file_id:
            for key in list(self._cache):
                if file_id in key:
                    del self._cache[key]
        else:
            self._cache.clear()
