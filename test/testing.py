"""
Standalone Test Script for AI Processor OpenRouter Integration
================================================================
Tests OpenRouter API calls WITHOUT Kafka, MinIO, or PostgreSQL dependencies.

Usage:
    python test_ai_processor.py

Requirements:
    1. .env file with OPENROUTER_API_KEY in parent directory
    2. Test files selected via file dialog (image, PDF, text)

This script validates that OpenRouter API calls work correctly before
integrating with the full Kafka/MinIO pipeline.
"""

import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv
import tkinter as tk
from tkinter import filedialog

# Add Kafka Integration directory to path for imports
SCRIPT_DIR = Path(__file__).resolve().parent
SYNIQ_DIR = SCRIPT_DIR.parent
KAFKA_INTEGRATION_DIR = SYNIQ_DIR / "Kafka Integration"
sys.path.insert(0, str(KAFKA_INTEGRATION_DIR))

# Load environment variables
env_path = SYNIQ_DIR / ".env"
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
# File Selection Helper
# ============================================================================

def select_file(title: str, filetypes: list) -> str:
    """Open file dialog to select a file"""
    root = tk.Tk()
    root.withdraw()  # Hide the main window
    root.attributes('-topmost', True)  # Bring dialog to front
    
    file_path = filedialog.askopenfilename(
        title=title,
        filetypes=filetypes
    )
    
    root.destroy()
    return file_path


# ============================================================================
# Test Functions
# ============================================================================

def test_image_processing(processor: FileProcessor):
    """Test image processing with vision model"""
    print("\n" + "=" * 80)
    print(f"TEST 1: IMAGE PROCESSING")
    print("=" * 80)
    
    print("\nPlease select an image file (JPG, PNG, GIF, BMP)...")
    image_path = select_file(
        "Select Test Image",
        [("Image files", "*.jpg *.jpeg *.png *.gif *.bmp"), ("All files", "*.*")]
    )
    
    if not image_path:
        print("SKIPPED: No image file selected")
        return
    
    print(f"Selected: {image_path}")
    print(f"Reading image...")
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


def test_pdf_processing(processor: FileProcessor):
    """Test PDF processing (detects text vs scanned)"""
    print("\n" + "=" * 80)
    print(f"TEST 2: PDF PROCESSING")
    print("=" * 80)
    
    print("\nPlease select a PDF file...")
    pdf_path = select_file(
        "Select Test PDF",
        [("PDF files", "*.pdf"), ("All files", "*.*")]
    )
    
    if not pdf_path:
        print("SKIPPED: No PDF file selected")
        return
    
    print(f"Selected: {pdf_path}")
    print(f"Reading PDF...")
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


def test_text_processing(processor: FileProcessor):
    """Test text document processing"""
    print("\n" + "=" * 80)
    print(f"TEST 3: TEXT DOCUMENT PROCESSING")
    print("=" * 80)
    
    print("\nPlease select a text file (TXT, DOCX)...")
    text_path = select_file(
        "Select Test Text File",
        [("Text files", "*.txt *.docx"), ("All files", "*.*")]
    )
    
    if not text_path:
        print("SKIPPED: No text file selected")
        return
    
    print(f"Selected: {text_path}")
    print(f"Reading text file...")
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
    
    print("\n" + "=" * 80)
    print("INTERACTIVE FILE SELECTION")
    print("=" * 80)
    print("You will be prompted to select test files from your file manager.")
    print("Click 'Cancel' to skip any test.")
    print("=" * 80)
    
    # Run tests with file selection dialogs
    try:
        test_image_processing(processor)
        test_pdf_processing(processor)
        test_text_processing(processor)
        
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
