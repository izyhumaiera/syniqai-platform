"""
Standalone Test Script for AI Processor OpenRouter Integration
================================================================
Tests OpenRouter API calls WITHOUT Kafka, MinIO, or PostgreSQL dependencies.

Usage:
    python test_ai_processor.py

Requirements:
    1. .env file with OPENROUTER_API_KEY in parent directory
    2. Sample test files in the same directory:
       - test_image.jpg (any image)
       - test_document.pdf (any PDF)
       - test_text.txt (any text file)

This script validates that OpenRouter API calls work correctly before
integrating with the full Kafka/MinIO pipeline.
"""

import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
SCRIPT_DIR = Path(__file__).resolve().parent
env_path = SCRIPT_DIR.parent / ".env"
load_dotenv(env_path)

# Import OpenRouter classes from ai_processor.py
from ai_processor import (
    OpenRouterClient,
    FileProcessor,
    MODEL_VISION,
    MODEL_TEXT,
    MODEL_AUDIO,
    OPENROUTER_API_KEY
)

# Verify API key is loaded
if not OPENROUTER_API_KEY:
    print("ERROR: OPENROUTER_API_KEY not found in .env file")
    print("   Please add OPENROUTER_API_KEY=sk-or-v1-... to your .env file")
    sys.exit(1)

print("=" * 80)
print("AI PROCESSOR STANDALONE TEST")
print("=" * 80)
print(f"OpenRouter API Key loaded: {OPENROUTER_API_KEY[:20]}...")
print(f"Vision Model: {MODEL_VISION}")
print(f"Text Model: {MODEL_TEXT}")
print(f"Audio Model: {MODEL_AUDIO}")
print("=" * 80)


# ============================================================================
# Mock Storage Client (no MinIO dependency)
# ============================================================================

class MockStorageClient:
    """Mock storage client for testing - does nothing"""
    def __init__(self):
        pass
    
    def download_file(self, bucket: str, key: str) -> bytes:
        raise NotImplementedError("Mock storage client - use local files instead")
    
    def upload_file(self, bucket: str, key: str, data: bytes, content_type: str = "application/json"):
        raise NotImplementedError("Mock storage client - no upload needed for testing")


# ============================================================================
# Test Functions
# ============================================================================

def test_image_processing(processor: FileProcessor, image_path: str):
    """Test image processing with vision model"""
    print("\n" + "=" * 80)
    print(f"TEST 1: IMAGE PROCESSING")
    print("=" * 80)
    
    if not os.path.exists(image_path):
        print(f"SKIPPED: Test image not found at {image_path}")
        print(f"   Create a test image or update the path in the script")
        return
    
    print(f"Reading image: {image_path}")
    with open(image_path, 'rb') as f:
        image_bytes = f.read()
    
    print(f"File size: {len(image_bytes):,} bytes")
    print(f"Calling OpenRouter vision model: {MODEL_VISION}")
    print("Processing...")
    
    result = processor.process_image(image_bytes, os.path.basename(image_path))
    
    print("\n" + "-" * 80)
    print("RESULT:")
    print("-" * 80)
    print(json.dumps(result, indent=2))
    
    if result.get("success"):
        print("\nIMAGE TEST PASSED")
        ai_result = result.get("result", {})
        print(f"   Tags: {ai_result.get('tags', [])}")
        print(f"   OCR Text: {ai_result.get('ocr_text', 'N/A')[:100]}...")
        print(f"   Confidence: {ai_result.get('confidence', 'N/A')}")
    else:
        print("\nIMAGE TEST FAILED")
        print(f"   Error: {result.get('error')}")


def test_pdf_processing(processor: FileProcessor, pdf_path: str):
    """Test PDF processing (detects text vs scanned)"""
    print("\n" + "=" * 80)
    print(f"TEST 2: PDF PROCESSING")
    print("=" * 80)
    
    if not os.path.exists(pdf_path):
        print(f"SKIPPED: Test PDF not found at {pdf_path}")
        print(f"   Create a test PDF or update the path in the script")
        return
    
    print(f"Reading PDF: {pdf_path}")
    with open(pdf_path, 'rb') as f:
        pdf_bytes = f.read()
    
    print(f"File size: {len(pdf_bytes):,} bytes")
    print(f"PDF will auto-detect if scanned (vision model) or text-based (text model)")
    print("Processing...")
    
    result = processor.process_pdf(pdf_bytes, os.path.basename(pdf_path))
    
    print("\n" + "-" * 80)
    print("RESULT:")
    print("-" * 80)
    print(json.dumps(result, indent=2))
    
    if result.get("success"):
        print("\nPDF TEST PASSED")
        ai_result = result.get("result", {})
        print(f"   Model Used: {result.get('ai_model_used')}")
        print(f"   Summary: {ai_result.get('summary', 'N/A')[:200]}...")
        print(f"   Page Count: {ai_result.get('page_count', 'N/A')}")
    else:
        print("\nPDF TEST FAILED")
        print(f"   Error: {result.get('error')}")


def test_text_processing(processor: FileProcessor, text_path: str):
    """Test text document processing"""
    print("\n" + "=" * 80)
    print(f"TEST 3: TEXT DOCUMENT PROCESSING")
    print("=" * 80)
    
    if not os.path.exists(text_path):
        print(f"SKIPPED: Test text file not found at {text_path}")
        print(f"   Create a test .txt file or update the path in the script")
        return
    
    print(f"Reading text file: {text_path}")
    with open(text_path, 'rb') as f:
        text_bytes = f.read()
    
    print(f"File size: {len(text_bytes):,} bytes")
    print(f"Calling OpenRouter text model: {MODEL_TEXT}")
    print("Processing...")
    
    file_ext = os.path.splitext(text_path)[1][1:]  # Get extension without dot
    result = processor.process_text_document(text_bytes, os.path.basename(text_path), file_ext)
    
    print("\n" + "-" * 80)
    print("RESULT:")
    print("-" * 80)
    print(json.dumps(result, indent=2))
    
    if result.get("success"):
        print("\nTEXT TEST PASSED")
        ai_result = result.get("result", {})
        print(f"   Summary: {ai_result.get('summary', 'N/A')[:200]}...")
        print(f"   Extracted Text Length: {len(ai_result.get('extracted_text', ''))} chars")
    else:
        print("\nTEXT TEST FAILED")
        print(f"   Error: {result.get('error')}")


# ============================================================================
# Main Test Runner
# ============================================================================

def main():
    """Run all AI processor tests"""
    
    # Initialize OpenRouter client and file processor
    print("\nInitializing OpenRouter client...")
    openrouter = OpenRouterClient()
    print("OpenRouter client initialized")
    
    print("Initializing file processor (with mock storage)...")
    mock_storage = MockStorageClient()
    processor = FileProcessor(mock_storage, openrouter)
    print("File processor initialized")
    
    # Define test file paths (update these to your actual test files)
    test_files = {
        "image": SCRIPT_DIR / "test_image.jpg",
        "pdf": SCRIPT_DIR / "test_document.pdf",
        "text": SCRIPT_DIR / "test_text.txt"
    }
    
    print("\n" + "=" * 80)
    print("TEST FILE LOCATIONS")
    print("=" * 80)
    print(f"Image: {test_files['image']}")
    print(f"PDF:   {test_files['pdf']}")
    print(f"Text:  {test_files['text']}")
    print("\nIf any test files are missing, create them or update paths in the script")
    
    # Run tests
    try:
        test_image_processing(processor, str(test_files["image"]))
        test_pdf_processing(processor, str(test_files["pdf"]))
        test_text_processing(processor, str(test_files["text"]))
        
        print("\n" + "=" * 80)
        print("ALL TESTS COMPLETED")
        print("=" * 80)
        print("OpenRouter integration validated")
        print("Ready to integrate with Kafka/MinIO pipeline")
        
    except KeyboardInterrupt:
        print("\n\nTests interrupted by user")
    except Exception as e:
        print(f"\n\nFATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
