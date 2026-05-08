"""
AI Processing Worker for SyniqAI Block 2 (Revised)
==================================================
Polls MinIO Bronze bucket and processes unstructured files using OpenRouter.

Exact Model Routing:
  - qwen/qwen3-vl-8b-thinking: Images, scanned PDFs, video frames
  - qwen/qwen3-8b: Plain text PDFs, TXT, DOCX
  - openai/gpt-audio-mini: Standalone audio files
  - openai/gpt-4o-audio-preview: Video audio tracks (higher quality)

Architecture:
  MinIO Bronze (poll every 10s) → ai_processor.py → OpenRouter → MinIO Silver + PostgreSQL
  No Kafka involved — direct MinIO polling, direct PostgreSQL writes

OpenRouter Configuration:
  - ALL configuration in .env file (OPENROUTER_API_KEY only)
  - No model names, API keys, or pricing exposed in frontend
  - Admin configures once before system starts

Usage:
  python ai_processor.py
"""

import os
import sys
import json
import base64
import logging
import traceback
import uuid
import time
from datetime import datetime, timezone
from pathlib import Path
from io import BytesIO
from typing import Dict, Any, Optional, List
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add paths for imports
SCRIPT_DIR = Path(__file__).resolve().parent
GUI_DIR = SCRIPT_DIR.parent / "gui"
sys.path.insert(0, str(GUI_DIR / "api"))

# Load environment variables
from dotenv import load_dotenv
env_path = SCRIPT_DIR.parent / ".env"
load_dotenv(env_path)

# Core dependencies
import psycopg2
from psycopg2.extras import Json
import requests
from minio import Minio

# File processing
try:
    from PIL import Image
    import pdfplumber  # For PDF text detection
    from docx import Document as DocxDocument
except ImportError as e:
    logging.warning(f"Optional dependencies not installed: {e}")

# Video/Audio processing
try:
    import ffmpeg
    FFMPEG_AVAILABLE = True
except ImportError:
    FFMPEG_AVAILABLE = False
    logging.warning("ffmpeg-python not available - video/audio processing disabled")

# Import MinIO storage helper
try:
    from storage import StorageManager
    STORAGE_MANAGER_AVAILABLE = True
except ImportError:
    STORAGE_MANAGER_AVAILABLE = False
    logging.warning("storage.py not available - using direct MinIO client")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# Configuration from Environment Variables
# ============================================================================

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "admin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "password123")
MINIO_SECURE = os.getenv("MINIO_SECURE", "false").lower() == "true"
MINIO_BRONZE_BUCKET = os.getenv("MINIO_BRONZE_BUCKET", "syniqai-bronze")
MINIO_SILVER_BUCKET = os.getenv("MINIO_SILVER_BUCKET", "syniqai-silver")

# PostgreSQL configuration
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB", "syniqai_metadata")
POSTGRES_USER = os.getenv("POSTGRES_USER", "syniqai_user")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "syniqai_password")
DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

# OpenRouter configuration (BACKEND ONLY - never exposed in GUI)
# Only OPENROUTER_API_KEY is read from .env - model names are hardcoded per spec
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Exact models 
MODEL_VISION = "qwen/qwen3-vl-8b-thinking"          # Images, scanned PDFs, video frames
MODEL_TEXT = "qwen/qwen3-8b"                         # Plain text PDFs, TXT, DOCX
MODEL_AUDIO = "openai/gpt-audio-mini"                # Standalone audio files
MODEL_VIDEO_AUDIO = "openai/gpt-audio-mini"    # Video audio tracks 

if not OPENROUTER_API_KEY:
    logger.error(" OPENROUTER_API_KEY not set in .env - AI processing will fail!")
    logger.error("   Add OPENROUTER_API_KEY=sk-or-v1-... to your .env file")
    raise RuntimeError("OPENROUTER_API_KEY is required")

logger.info("=" * 80)
logger.info("AI PROCESSOR CONFIGURATION")
logger.info("=" * 80)
logger.info(f"MinIO Endpoint: {MINIO_ENDPOINT}")
logger.info(f"Bronze Bucket: {MINIO_BRONZE_BUCKET}")
logger.info(f"Silver Bucket: {MINIO_SILVER_BUCKET}")
logger.info(f"PostgreSQL: {POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}")
logger.info(f"Vision Model: {MODEL_VISION}")
logger.info(f"Text Model: {MODEL_TEXT}")
logger.info(f"Audio Model: {MODEL_AUDIO}")
logger.info(f"Video Audio Model: {MODEL_VIDEO_AUDIO}")
logger.info("=" * 80)


# ============================================================================
# MinIO Storage Client
# ============================================================================

class StorageClient:
    """MinIO storage client for downloading/uploading files"""
    
    def __init__(self):
        if STORAGE_MANAGER_AVAILABLE:
            self.manager = StorageManager()
            self.manager.initialize()
            self.use_manager = True
        else:
            self.client = Minio(
                MINIO_ENDPOINT,
                access_key=MINIO_ACCESS_KEY,
                secret_key=MINIO_SECRET_KEY,
                secure=MINIO_SECURE
            )
            self.use_manager = False
        logger.info("✓ Storage client initialized")
    
    def download_file(self, bucket: str, key: str) -> bytes:
        """Download file from MinIO and return bytes"""
        try:
            if self.use_manager:
                layer = "bronze" if bucket == MINIO_BRONZE_BUCKET else "silver"
                return self.manager.get_object(layer, key)
            else:
                response = self.client.get_object(bucket, key)
                data = response.read()
                response.close()
                response.release_conn()
                return data
        except Exception as e:
            logger.error(f"Failed to download {bucket}/{key}: {e}")
            raise
    
    def upload_file(self, bucket: str, key: str, data: bytes, content_type: str = "application/json"):
        """Upload file to MinIO"""
        try:
            if self.use_manager:
                layer = "silver" if bucket == MINIO_SILVER_BUCKET else "bronze"
                buffer = BytesIO(data)
                self.manager.put_object(layer, key, buffer, len(data), content_type=content_type)
            else:
                self.client.put_object(
                    bucket,
                    key,
                    BytesIO(data),
                    length=len(data),
                    content_type=content_type
                )
            logger.info(f"✓ Uploaded to {bucket}/{key}")
        except Exception as e:
            logger.error(f"Failed to upload {bucket}/{key}: {e}")
            raise


# ============================================================================
# OpenRouter AI Client
# ============================================================================

class OpenRouterClient:
    """Client for OpenRouter API - routes to exact models based on file type"""
    
    def __init__(self):
        self.api_key = OPENROUTER_API_KEY
        self.api_url = OPENROUTER_API_URL
        
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://syniqai.com",
            "X-Title": "SyniqAI Data Lakehouse"
        }
    
    def call_vision_model(self, image_base64: str, prompt: str) -> Dict[str, Any]:
        """Call vision model (qwen/qwen3-vl-8b-thinking) with base64 image"""
        payload = {
            "model": MODEL_VISION,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 2000,
            "temperature": 0.0
        }
        
        response = requests.post(
            self.api_url,
            headers=self.headers,
            json=payload,
            timeout=120
        )
        response.raise_for_status()
        return response.json()
    
    def call_text_model(self, text: str, prompt: str) -> Dict[str, Any]:
        """Call text model (qwen/qwen3-8b) for text summarization"""
        payload = {
            "model": MODEL_TEXT,
            "messages": [
                {
                    "role": "user",
                    "content": f"{prompt}\n\n{text}"
                }
            ],
            "max_tokens": 1500,
            "temperature": 0.0
        }
        
        response = requests.post(
            self.api_url,
            headers=self.headers,
            json=payload,
            timeout=120
        )
        response.raise_for_status()
        return response.json()
    
    def call_audio_model(self, audio_base64: str, model: str = MODEL_AUDIO) -> Dict[str, Any]:
        """Call audio model for transcription (model varies: standalone vs video)"""
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Transcribe this audio file and provide timestamps in SRT format."},
                        {
                            "type": "audio_url",
                            "audio_url": {
                                "url": f"data:audio/mp3;base64,{audio_base64}"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 3000,
            "temperature": 0.0
        }
        
        response = requests.post(
            self.api_url,
            headers=self.headers,
            json=payload,
            timeout=180
        )
        response.raise_for_status()
        return response.json()


# ============================================================================
# File Type Processors
# ============================================================================

class FileProcessor:
    """Process different file types with AI using exact model routing"""
    
    def __init__(self, storage: StorageClient, openrouter: OpenRouterClient):
        self.storage = storage
        self.ai = openrouter
    
    def process_image(self, file_bytes: bytes, filename: str) -> Dict[str, Any]:
        """
        Process image with vision model (qwen/qwen3-vl-8b-thinking)
        Returns: {tags: [], ocr_text: "", captions: {}, confidence: float}
        """
        start_time = time.time()
        logger.info(f"[IMAGE] Processing: {filename}")
        
        try:
            image_base64 = base64.b64encode(file_bytes).decode('utf-8')
            
            prompt = """Analyze this image carefully and provide:

1. TAGS: List 5-10 descriptive keywords/labels for what you see
2. OCR: Extract ALL visible text exactly as it appears
3. DESCRIPTION: Write a detailed 2-3 sentence description of the image content
4. CONFIDENCE: Your confidence score (0.0 to 1.0) in this analysis

Respond with ONLY valid JSON (no markdown, no explanation):
{
  "tags": ["keyword1", "keyword2", "keyword3"],
  "ocr_text": "all visible text extracted here",
  "captions": {"main": "detailed description here"},
  "confidence": 0.95
}"""
            
            logger.info(f"[OPENROUTER CALL] model={MODEL_VISION} file={filename} file_type=image")
            response = self.ai.call_vision_model(image_base64, prompt)
            logger.info(f"[OPENROUTER SUCCESS] model={MODEL_VISION} file={filename} tokens_used={response.get('usage', {}).get('total_tokens', 'unknown')}")
            result_text = response["choices"][0]["message"]["content"]
            
            # Parse JSON from response
            try:
                if "```json" in result_text:
                    result_text = result_text.split("```json")[1].split("```")[0].strip()
                elif "```" in result_text:
                    result_text = result_text.split("```")[1].split("```")[0].strip()
                
                result = json.loads(result_text)
            except json.JSONDecodeError:
                result = {
                    "tags": [],
                    "ocr_text": result_text,
                    "captions": {"main": result_text[:200]},
                    "confidence": 0.8
                }
            
            elapsed_time = time.time() - start_time
            logger.info(f"[IMAGE] Completed in {elapsed_time:.2f}s - Model: {MODEL_VISION}")
            
            return {
                "success": True,
                "ai_model_used": MODEL_VISION,
                "result": result,
                "extraction_status": "success",
                "processing_time_seconds": round(elapsed_time, 2)
            }
        
        except Exception as e:
            elapsed_time = time.time() - start_time
            logger.error(f"[IMAGE] Failed after {elapsed_time:.2f}s: {e}")
            logger.error(traceback.format_exc())
            return {
                "success": False,
                "error": str(e),
                "extraction_status": "failed",
                "processing_time_seconds": round(elapsed_time, 2)
            }
    
    def process_pdf(self, file_bytes: bytes, filename: str) -> Dict[str, Any]:
        """
        Process PDF - detect if scanned or plain text using pdfplumber
        - Scanned → qwen/qwen3-vl-8b-thinking (vision model)
        - Plain text → qwen/qwen3-8b (text model)
        Returns: {extracted_text: "", summary: "", ocr_confidence: float (optional), page_count: int}
        """
        logger.info(f"Processing PDF: {filename}")
        
        try:
            # Use pdfplumber to detect extractable text
            pdf_buffer = BytesIO(file_bytes)
            
            with pdfplumber.open(pdf_buffer) as pdf:
                page_count = len(pdf.pages)
                extracted_text = ""
                
                # Extract text from all pages
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        extracted_text += page_text + "\n"
                
                extracted_text = extracted_text.strip()
            
            # Determine if scanned or plain text
            if len(extracted_text) > 100:
                # Plain PDF with extractable text → use text model
                logger.info(f"PDF has extractable text ({len(extracted_text)} chars) - using text model")
                return self._process_text_pdf(extracted_text, filename, page_count)
            else:
                # Scanned PDF → use vision model for OCR
                logger.info("Scanned PDF detected - using vision model OCR")
                return self._process_scanned_pdf(file_bytes, filename, page_count)
        
        except Exception as e:
            logger.error(f"PDF processing failed: {e}")
            logger.error(traceback.format_exc())
            return {
                "success": False,
                "error": str(e),
                "extraction_status": "failed"
            }
    
    def _process_text_pdf(self, text: str, filename: str, page_count: int) -> Dict[str, Any]:
        """Process text-based PDF with qwen/qwen3-8b"""
        start_time = time.time()
        logger.info(f"[TEXT PDF] Processing: {filename} ({page_count} pages)")
        
        try:
            prompt = f"""You are a document analysis expert. Analyze this document and provide a structured summary.

Document name: {filename}
Page count: {page_count}

Format your response EXACTLY as follows:

## DOCUMENT TYPE
[Identify the document type: e.g., Laboratory Report, Invoice, Legal Contract, etc.]

## EXECUTIVE SUMMARY
[2-3 sentences capturing the essence of the document]

## KEY INFORMATION
- **Date(s)**: [List all important dates found]
- **Entities**: [List people, organizations, or institutions mentioned]
- **Key Numbers**: [Important values, amounts, or measurements]
- **Reference Numbers**: [Any IDs, case numbers, or tracking codes]

## MAIN FINDINGS / CONTENT
[Structured list of main points, findings, or sections]

## RECOMMENDATIONS / ACTION ITEMS
[Any recommendations, next steps, or required actions mentioned]

## NOTES
[Any additional relevant information, warnings, or context]

Provide clear, concise information using bullet points and structured formatting."""
            
            # Limit to 10k chars to avoid token limits
            logger.info(f"[OPENROUTER CALL] model={MODEL_TEXT} file={filename} file_type=text_pdf pages={page_count}")
            response = self.ai.call_text_model(text[:10000], prompt)
            logger.info(f"[OPENROUTER SUCCESS] model={MODEL_TEXT} file={filename} tokens_used={response.get('usage', {}).get('total_tokens', 'unknown')}")
            summary = response["choices"][0]["message"]["content"].strip()
            
            elapsed_time = time.time() - start_time
            logger.info(f"[TEXT PDF] Completed in {elapsed_time:.2f}s - Model: {MODEL_TEXT}")
            
            return {
                "success": True,
                "ai_model_used": MODEL_TEXT,
                "result": {
                    "extracted_text": text,
                    "summary": summary,
                    "page_count": page_count
                },
                "extraction_status": "success",
                "processing_time_seconds": round(elapsed_time, 2)
            }
        except Exception as e:
            elapsed_time = time.time() - start_time
            logger.error(f"[TEXT PDF] Failed after {elapsed_time:.2f}s: {e}")
            return {
                "success": False,
                "error": str(e),
                "extraction_status": "failed",
                "processing_time_seconds": round(elapsed_time, 2)
            }
    
    def _process_scanned_pdf(self, file_bytes: bytes, filename: str, page_count: int) -> Dict[str, Any]:
        """Process scanned PDF with vision model OCR (qwen/qwen3-vl-8b-thinking)"""
        try:
            # Convert first 3 pages to images for OCR
            try:
                from pdf2image import convert_from_bytes
                images = convert_from_bytes(file_bytes, first_page=1, last_page=min(3, page_count))
            except Exception as e:
                logger.error(f"pdf2image not available or failed: {e}")
                raise ValueError("pdf2image required for scanned PDF OCR - install with: pip install pdf2image")
            
            if not images:
                raise ValueError("Could not convert PDF to image")
            
            # Convert first image to base64
            img_buffer = BytesIO()
            images[0].save(img_buffer, format='PNG')
            img_base64 = base64.b64encode(img_buffer.getvalue()).decode('utf-8')
            
            prompt = """Extract all text from this scanned document page (OCR) and provide a brief summary.
Return ONLY valid JSON format:
{
  "extracted_text": "full text here",
  "summary": "brief summary",
  "ocr_confidence": 0.95
}"""
            
            logger.info(f"[OPENROUTER CALL] model={MODEL_VISION} file={filename} file_type=scanned_pdf page={i+1}/{page_count}")
            response = self.ai.call_vision_model(img_base64, prompt)
            logger.info(f"[OPENROUTER SUCCESS] model={MODEL_VISION} file={filename} page={i+1} tokens_used={response.get('usage', {}).get('total_tokens', 'unknown')}")
            result_text = response["choices"][0]["message"]["content"]
            
            try:
                if "```json" in result_text:
                    result_text = result_text.split("```json")[1].split("```")[0].strip()
                elif "```" in result_text:
                    result_text = result_text.split("```")[1].split("```")[0].strip()
                
                result = json.loads(result_text)
            except json.JSONDecodeError:
                result = {
                    "extracted_text": result_text,
                    "summary": result_text[:500],
                    "ocr_confidence": 0.7
                }
            
            result["page_count"] = page_count
            
            return {
                "success": True,
                "ai_model_used": MODEL_VISION,
                "result": result,
                "extraction_status": "success"
            }
        except Exception as e:
            logger.error(f"Scanned PDF OCR failed: {e}")
            logger.error(traceback.format_exc())
            return {
                "success": False,
                "error": str(e),
                "extraction_status": "failed"
            }
    
    def process_text_document(self, file_bytes: bytes, filename: str, file_type: str) -> Dict[str, Any]:
        """
        Process TXT or DOCX files with qwen/qwen3-8b
        Returns: {extracted_text: "", summary: ""}
        """
        start_time = time.time()
        logger.info(f"[TEXT DOC] Processing: {filename} (type: {file_type})")
        
        try:
            # Extract text based on type
            if file_type == "docx":
                doc = DocxDocument(BytesIO(file_bytes))
                text = "\n".join([para.text for para in doc.paragraphs])
            else:  # txt
                text = file_bytes.decode('utf-8', errors='replace')
            
            # Summarize with AI using text model
            prompt = f"""You are a document analysis expert. Analyze this {file_type.upper()} document and provide a structured summary.

Document: {filename}
Format: {file_type.upper()}

Format your response EXACTLY as follows:

## DOCUMENT TYPE
[Identify the document type: e.g., Meeting Notes, Technical Documentation, Letter, etc.]

## EXECUTIVE SUMMARY
[2-3 sentences capturing the essence of the document]

## KEY INFORMATION
- **Date(s)**: [List all important dates found]
- **Entities**: [List people, organizations, or institutions mentioned]
- **Key Numbers**: [Important values, amounts, or measurements]

## MAIN CONTENT
[Structured list of main points, topics, or sections]

## ACTION ITEMS / RECOMMENDATIONS
[Any tasks, next steps, or recommendations mentioned]

## NOTES
[Any additional relevant information or context]

Provide clear, concise information using bullet points and structured formatting."""
            
            logger.info(f"[OPENROUTER CALL] model={MODEL_TEXT} file={filename} file_type={file_type}")
            response = self.ai.call_text_model(text[:10000], prompt)
            logger.info(f"[OPENROUTER SUCCESS] model={MODEL_TEXT} file={filename} tokens_used={response.get('usage', {}).get('total_tokens', 'unknown')}")
            summary = response["choices"][0]["message"]["content"].strip()
            
            elapsed_time = time.time() - start_time
            logger.info(f"[TEXT DOC] Completed in {elapsed_time:.2f}s - Model: {MODEL_TEXT}")
            
            return {
                "success": True,
                "ai_model_used": MODEL_TEXT,
                "result": {
                    "extracted_text": text,
                    "summary": summary
                },
                "extraction_status": "success",
                "processing_time_seconds": round(elapsed_time, 2)
            }
        
        except Exception as e:
            elapsed_time = time.time() - start_time
            logger.error(f"[TEXT DOC] Failed after {elapsed_time:.2f}s: {e}")
            logger.error(traceback.format_exc())
            return {
                "success": False,
                "error": str(e),
                "extraction_status": "failed",
                "processing_time_seconds": round(elapsed_time, 2)
            }
    
    def process_audio(self, file_bytes: bytes, filename: str) -> Dict[str, Any]:
        """
        Process standalone audio file with openai/gpt-audio-mini
        Returns: {transcript_srt: "", vtt_timestamps: "", summary: ""}
        """
        start_time = time.time()
        logger.info(f"[AUDIO] Processing: {filename}")
        
        try:
            audio_base64 = base64.b64encode(file_bytes).decode('utf-8')
            
            logger.info(f"[OPENROUTER CALL] model={MODEL_AUDIO} file={filename} file_type=audio size_mb={len(file_bytes)/(1024*1024):.1f}")
            response = self.ai.call_audio_model(audio_base64, model=MODEL_AUDIO)
            logger.info(f"[OPENROUTER SUCCESS] model={MODEL_AUDIO} file={filename} tokens_used={response.get('usage', {}).get('total_tokens', 'unknown')}")
            result_text = response["choices"][0]["message"]["content"]
            
            elapsed_time = time.time() - start_time
            logger.info(f"[AUDIO] Completed in {elapsed_time:.2f}s - Model: {MODEL_AUDIO}")
            
            return {
                "success": True,
                "ai_model_used": MODEL_AUDIO,
                "result": {
                    "transcript_srt": result_text,
                    "vtt_timestamps": result_text,
                    "summary": result_text[:500]
                },
                "extraction_status": "success",
                "processing_time_seconds": round(elapsed_time, 2)
            }
        
        except Exception as e:
            elapsed_time = time.time() - start_time
            logger.error(f"[AUDIO] Failed after {elapsed_time:.2f}s: {e}")
            logger.error(traceback.format_exc())
            return {
                "success": False,
                "error": str(e),
                "extraction_status": "failed",
                "processing_time_seconds": round(elapsed_time, 2)
            }
    
    def process_video(self, file_bytes: bytes, filename: str) -> Dict[str, Any]:
        """
        Process video file with hybrid approach:
        - Extract keyframes every 10s → qwen/qwen3-vl-8b-thinking
        - Extract audio track → openai/gpt-4o-audio-preview
        - Merge results
        Returns: {frame_descriptions: [{timestamp, tags, description}], transcript_srt: "", summary: ""}
        """
        logger.info(f"Processing video: {filename}")
        
        if not FFMPEG_AVAILABLE:
            return {
                "success": False,
                "error": "ffmpeg-python not installed",
                "extraction_status": "failed"
            }
        
        try:
            # Save video to temp file for ffmpeg processing
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as temp_video:
                temp_video.write(file_bytes)
                temp_video_path = temp_video.name
            
            # Run parallel processing
            with ThreadPoolExecutor(max_workers=2) as executor:
                future_frames = executor.submit(self._extract_video_frames, temp_video_path, filename)
                future_audio = executor.submit(self._extract_video_audio, temp_video_path, filename)
                
                frames_result = future_frames.result()
                audio_result = future_audio.result()
            
            # Clean up temp file
            try:
                os.unlink(temp_video_path)
            except:
                pass
            
            # Merge results
            result = {
                "frame_descriptions": frames_result.get("frame_descriptions", []),
                "transcript_srt": audio_result.get("transcript_srt", ""),
                "summary": f"Video with {len(frames_result.get('frame_descriptions', []))} keyframes. {audio_result.get('summary', '')}"
            }
            
            return {
                "success": True,
                "ai_model_used": f"{MODEL_VISION} + {MODEL_VIDEO_AUDIO}",
                "result": result,
                "extraction_status": "success"
            }
        
        except Exception as e:
            logger.error(f"Video processing failed: {e}")
            logger.error(traceback.format_exc())
            return {
                "success": False,
                "error": str(e),
                "extraction_status": "failed"
            }
    
    def _extract_video_frames(self, video_path: str, filename: str) -> Dict[str, Any]:
        """Extract keyframes every 10 seconds and process with vision model"""
        try:
            import subprocess
            import tempfile
            
            frame_descriptions = []
            
            # Get video duration
            probe = ffmpeg.probe(video_path)
            duration = float(probe['format']['duration'])
            
            # Extract frames every 10 seconds
            for timestamp in range(0, int(duration), 10):
                with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_frame:
                    temp_frame_path = temp_frame.name
                
                try:
                    # Extract frame at timestamp
                    (
                        ffmpeg
                        .input(video_path, ss=timestamp)
                        .output(temp_frame_path, vframes=1)
                        .overwrite_output()
                        .run(capture_stdout=True, capture_stderr=True)
                    )
                    
                    # Read frame and process with vision model
                    with open(temp_frame_path, 'rb') as f:
                        frame_bytes = f.read()
                    
                    frame_base64 = base64.b64encode(frame_bytes).decode('utf-8')
                    prompt = "Describe this video frame briefly. List key objects, actions, and scene details."
                    
                    logger.info(f"[OPENROUTER CALL] model={MODEL_VISION} file={filename} file_type=video_frame frame={i+1}")
                    response = self.ai.call_vision_model(frame_base64, prompt)
                    logger.info(f"[OPENROUTER SUCCESS] model={MODEL_VISION} file={filename} frame={i+1} tokens_used={response.get('usage', {}).get('total_tokens', 'unknown')}")
                    description = response["choices"][0]["message"]["content"]
                    
                    frame_descriptions.append({
                        "timestamp": timestamp,
                        "tags": [],
                        "description": description
                    })
                    
                finally:
                    try:
                        os.unlink(temp_frame_path)
                    except:
                        pass
            
            return {"frame_descriptions": frame_descriptions}
        
        except Exception as e:
            logger.error(f"Frame extraction failed: {e}")
            return {"frame_descriptions": []}
    
    def _extract_video_audio(self, video_path: str, filename: str) -> Dict[str, Any]:
        """Extract audio track and transcribe with openai/gpt-4o-audio-preview"""
        try:
            import tempfile
            
            # Extract audio track to temp file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as temp_audio:
                temp_audio_path = temp_audio.name
            
            (
                ffmpeg
                .input(video_path)
                .output(temp_audio_path, acodec='libmp3lame', ar='16000')
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True)
            )
            
            # Read audio and transcribe
            with open(temp_audio_path, 'rb') as f:
                audio_bytes = f.read()
            
            audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
            
            # Use higher quality audio model for video
            logger.info(f"[OPENROUTER CALL] model={MODEL_VIDEO_AUDIO} file={filename} file_type=video_audio size_mb={len(audio_bytes)/(1024*1024):.1f}")
            response = self.ai.call_audio_model(audio_base64, model=MODEL_VIDEO_AUDIO)
            logger.info(f"[OPENROUTER SUCCESS] model={MODEL_VIDEO_AUDIO} file={filename} tokens_used={response.get('usage', {}).get('total_tokens', 'unknown')}")
            result_text = response["choices"][0]["message"]["content"]
            
            # Clean up
            try:
                os.unlink(temp_audio_path)
            except:
                pass
            
            return {
                "transcript_srt": result_text,
                "summary": result_text[:500]
            }
        
        except Exception as e:
            logger.error(f"Audio extraction failed: {e}")
            return {
                "transcript_srt": "",
                "summary": ""
            }


# ============================================================================
# PostgreSQL Database Handler
# ============================================================================

class PostgresHandler:
    """Handle PostgreSQL silver_assets table operations"""
    
    def __init__(self):
        self.conn = None
        self.connect()
    
    def connect(self):
        """Connect to PostgreSQL"""
        try:
            self.conn = psycopg2.connect(DATABASE_URL)
            self.conn.autocommit = True
            logger.info("✓ Connected to PostgreSQL")
        except Exception as e:
            logger.error(f"PostgreSQL connection failed: {e}")
            logger.warning("AI Processor will run but won't save to database")
            self.conn = None
    
    def insert_silver_asset(self, asset_data: Dict[str, Any]) -> Optional[str]:
        """Insert processed asset into silver_assets table"""
        if not self.conn:
            logger.warning("No PostgreSQL connection - skipping database insert")
            return None
        
        try:
            cur = self.conn.cursor()
            
            asset_id = str(uuid.uuid4())
            
            query = """
            INSERT INTO silver_assets (
                id, source, file_type, bronze_minio_key, silver_minio_key,
                processed_at, ai_model_used, extraction_status, 
                ai_confidence_score, file_size_bytes, content_tags, summary
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            """
            
            cur.execute(query, (
                asset_id,
                asset_data.get("source"),
                asset_data.get("file_type"),
                asset_data.get("bronze_minio_key"),
                asset_data.get("silver_minio_key"),
                datetime.now(timezone.utc),
                asset_data.get("ai_model_used"),
                asset_data.get("extraction_status"),
                asset_data.get("ai_confidence_score"),
                asset_data.get("file_size_bytes"),
                Json(asset_data.get("content_tags")) if asset_data.get("content_tags") else None,
                asset_data.get("summary")
            ))
            
            cur.close()
            logger.info(f"✓ Inserted silver_asset: {asset_id}")
            return asset_id
        
        except Exception as e:
            logger.error(f"Database insert failed: {e}")
            logger.error(traceback.format_exc())
            return None
    
    def insert_structured_data(self, message: Dict[str, Any]) -> Optional[str]:
        """
        Insert structured data (CSV/JSON/Parquet) directly to PostgreSQL
        No OpenRouter call needed for structured data
        """
        logger.info("Structured data processing not yet implemented")
        return None


# ============================================================================
# Main AI Processor
# ============================================================================

class AIProcessor:
    """Main MinIO polling + AI processing orchestrator"""
    
    def __init__(self):
        logger.info("Initializing AI Processor components...")
        
        self.storage = StorageClient()
        self.openrouter = OpenRouterClient()
        self.processor = FileProcessor(self.storage, self.openrouter)
        self.postgres = PostgresHandler()
        
        logger.info("=" * 80)
        logger.info("✓ AI Processor initialized - Block 2 ready")
        logger.info(f"  MinIO Bronze Bucket: {MINIO_BRONZE_BUCKET}")
        logger.info(f"  MinIO Silver Bucket: {MINIO_SILVER_BUCKET}")
        logger.info(f"  Vision Model: {MODEL_VISION}")
        logger.info(f"  Text Model: {MODEL_TEXT}")
        logger.info(f"  Audio Model: {MODEL_AUDIO}")
        logger.info(f"  Video Audio Model: {MODEL_VIDEO_AUDIO}")
        logger.info(f"  PostgreSQL: {POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}")
        logger.info("=" * 80)
    
    def process_message(self, message: Dict[str, Any]):
        """Process a single bronze-ready message"""
        try:
            filename = message.get("filename", "unknown")
            logger.info(f"\n{'='*80}")
            logger.info(f"Processing: {filename}")
            logger.info(f"{'='*80}")
            
            bronze_key = message.get("bronze_minio_key")
            file_type = message.get("file_type", "unknown").lower()
            source = message.get("source", "unknown")
            
            if not bronze_key:
                raise ValueError("Missing bronze_minio_key in message")
            
            # Download file from Bronze layer
            logger.info(f"Downloading from MinIO: {MINIO_BRONZE_BUCKET}/{bronze_key}")
            file_bytes = self.storage.download_file(MINIO_BRONZE_BUCKET, bronze_key)
            file_size = len(file_bytes)
            logger.info(f"Downloaded {file_size:,} bytes")
            
            # Route based on file type using exact models
            if file_type in ["jpg", "jpeg", "png", "gif", "bmp"]:
                result = self.processor.process_image(file_bytes, filename)
            elif file_type == "pdf":
                result = self.processor.process_pdf(file_bytes, filename)
            elif file_type in ["txt", "docx"]:
                result = self.processor.process_text_document(file_bytes, filename, file_type)
            elif file_type in ["mp3", "wav"]:
                result = self.processor.process_audio(file_bytes, filename)
            elif file_type in ["mp4", "mkv", "avi"]:
                logger.warning(f"VIDEO PROCESSING DISABLED FOR TESTING - Skipping: {filename}")
                return  # Skip video processing as requested
            elif file_type in ["csv", "json", "parquet"]:
                # Structured data - do NOT call OpenRouter
                logger.info("Structured data - inserting directly to PostgreSQL (no AI processing)")
                asset_id = self.postgres.insert_structured_data(message)
                logger.info(f"✓ Structured data processed: {filename}")
                return
            else:
                raise ValueError(f"Unsupported file type: {file_type}")
            
            if not result.get("success"):
                raise Exception(result.get("error", "Processing failed"))
            
            # Save result JSON to Silver layer
            date_str = datetime.now().strftime("%Y-%m-%d")
            silver_key = f"{file_type}/{date_str}/{filename}.json"
            result_json = json.dumps(result.get("result"), indent=2).encode('utf-8')
            self.storage.upload_file(MINIO_SILVER_BUCKET, silver_key, result_json)
            
            # Extract data for PostgreSQL
            ai_result = result.get("result", {})
            processing_time = result.get("processing_time_seconds", 0.0)
            
            asset_data = {
                "source": source,
                "file_type": file_type,
                "bronze_minio_key": bronze_key,
                "silver_minio_key": silver_key,
                "ai_model_used": result.get("ai_model_used"),
                "extraction_status": result.get("extraction_status"),
                "ai_confidence_score": ai_result.get("confidence") or ai_result.get("ocr_confidence"),
                "file_size_bytes": file_size,
                "content_tags": ai_result.get("tags"),
                "summary": ai_result.get("summary") or ai_result.get("captions", {}).get("main")
            }
            
            logger.info(f"TOTAL PROCESSING TIME: {processing_time:.2f} seconds")
            
            # Insert to PostgreSQL
            asset_id = self.postgres.insert_silver_asset(asset_data)
            
            # Refresh Gold materialized view (best-effort)
            try:
                if self.postgres.conn:
                    cur = self.postgres.conn.cursor()
                    cur.execute("REFRESH MATERIALIZED VIEW IF EXISTS gold_assets")
                    cur.close()
                    logger.info("✓ Refreshed gold_assets materialized view")
            except Exception as e:
                logger.debug(f"Gold view refresh skipped: {e}")
            
            logger.info(f"PROCESSING COMPLETE: {filename} | Time: {processing_time:.2f}s | Model: {result.get('ai_model_used')}")
        
        except Exception as e:
            logger.error(f"Processing failed: {e}")
            logger.error(traceback.format_exc())
            
            # Log error to PostgreSQL
            try:
                error_data = {
                    "source": message.get("source", "unknown"),
                    "file_type": message.get("file_type", "unknown"),
                    "bronze_minio_key": message.get("bronze_minio_key"),
                    "silver_minio_key": None,
                    "ai_model_used": None,
                    "extraction_status": "failed",
                    "ai_confidence_score": None,
                    "file_size_bytes": message.get("size_bytes"),
                    "content_tags": None,
                    "summary": f"ERROR: {str(e)[:500]}"
                }
                self.postgres.insert_silver_asset(error_data)
                logger.info("✓ Logged error to PostgreSQL")
            except Exception as db_error:
                logger.error(f"Failed to log error to PostgreSQL: {db_error}")
    
    def _already_processed(self, bronze_key: str) -> bool:
        """Check if file has already been processed"""
        if not self.postgres.conn:
            return False
        try:
            cur = self.postgres.conn.cursor()
            cur.execute(
                "SELECT id FROM silver_assets WHERE bronze_minio_key = %s LIMIT 1",
                (bronze_key,)
            )
            result = cur.fetchone()
            cur.close()
            return result is not None
        except Exception as e:
            logger.error(f"Error checking if processed: {e}")
            return False
    
    def _poll_and_process(self):
        """Poll MinIO Bronze bucket and process new files"""
        try:
            # Get MinIO client (direct or through StorageManager)
            if self.storage.use_manager:
                minio_client = self.storage.manager.client
            else:
                minio_client = self.storage.client
            
            objects = minio_client.list_objects(
                MINIO_BRONZE_BUCKET, recursive=True
            )
            
            processed_count = 0
            skipped_count = 0
            
            for obj in objects:
                bronze_key = obj.object_name
                
                # Skip if already processed
                if self._already_processed(bronze_key):
                    skipped_count += 1
                    continue
                
                # Build message from MinIO object
                filename = bronze_key.split("/")[-1]
                file_type = filename.rsplit(".", 1)[-1].lower() if "." in filename else "unknown"
                source = "mongodb" if "/mongodb/" in bronze_key else "s3"
                
                message = {
                    "bronze_minio_key": bronze_key,
                    "filename": filename,
                    "file_type": file_type,
                    "source": source,
                    "size_bytes": obj.size
                }
                
                logger.info(f"Found new file: {filename}")
                self.process_message(message)
                processed_count += 1
            
            if processed_count > 0:
                logger.info(f"Poll complete: {processed_count} processed, {skipped_count} skipped")
            elif skipped_count > 0:
                logger.debug(f"Poll complete: All {skipped_count} files already processed")
        
        except Exception as e:
            logger.error(f"Poll cycle error: {e}")
            logger.error(traceback.format_exc())
    
    def run(self):
        """Main polling loop"""
        logger.info(" Starting AI Processor - polling MinIO Bronze every 10 seconds...")
        
        try:
            while True:
                self._poll_and_process()
                time.sleep(10)
        except KeyboardInterrupt:
            logger.info("\n Shutting down AI Processor...")


# ============================================================================
# Entry Point
# ============================================================================

if __name__ == "__main__":
    processor = AIProcessor()
    processor.run()
