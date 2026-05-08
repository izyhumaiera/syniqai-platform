"""
Test Script for Block 2 AI Models
Tests: Image, Text, and Audio processing (Video skipped per request)
"""
import os
import sys
import json
import time
from pathlib import Path
from kafka import KafkaProducer
from minio import Minio
from datetime import datetime

# Configuration
KAFKA_SERVERS = "localhost:9092"
MINIO_ENDPOINT = "localhost:9000"
MINIO_ACCESS = "admin"
MINIO_SECRET = "password123"
BRONZE_BUCKET = "syniqai-bronze"
BRONZE_READY_TOPIC = "bronze-ready"

# Initialize clients
producer = KafkaProducer(
    bootstrap_servers=KAFKA_SERVERS,
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

minio_client = Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_ACCESS,
    secret_key=MINIO_SECRET,
    secure=False
)

print("=" * 80)
print("BLOCK 2 AI MODEL TESTING")
print("=" * 80)
print("Models to test:")
print("  [+] Image Model: qwen/qwen3-vl-8b-thinking")
print("  [+] Text Model: qwen/qwen3-8b")
print("  [+] Audio Model: openai/gpt-audio-mini")
print("  [-] Video Model: SKIPPED (as requested)")
print("=" * 80)
print()

def upload_to_bronze(file_path: str, file_type: str) -> str:
    """Upload file to Bronze bucket and return MinIO key"""
    filename = Path(file_path).name
    date_str = datetime.now().strftime("%Y-%m-%d")
    minio_key = f"{file_type}/{date_str}/{filename}"
    
    with open(file_path, 'rb') as f:
        data = f.read()
        from io import BytesIO
        minio_client.put_object(
            BRONZE_BUCKET,
            minio_key,
            BytesIO(data),
            length=len(data)
        )
    
    print(f"  [UPLOAD] MinIO: {BRONZE_BUCKET}/{minio_key}")
    return minio_key

def send_to_kafka(filename: str, file_type: str, bronze_key: str):
    """Send message to bronze-ready Kafka topic"""
    message = {
        "filename": filename,
        "file_type": file_type,
        "bronze_minio_key": bronze_key,
        "source": "manual_test",
        "uploaded_at": datetime.now().isoformat()
    }
    
    producer.send(BRONZE_READY_TOPIC, value=message)
    producer.flush()
    print(f"  [KAFKA] Sent to topic: {BRONZE_READY_TOPIC}")
    print(f"  [INFO] Waiting for AI processing...")
    print()

def test_file(file_path: str, file_type: str, test_name: str):
    """Test a single file"""
    print(f"\n{'='*80}")
    print(f"TEST: {test_name}")
    print(f"{'='*80}")
    print(f"File: {file_path}")
    print(f"Type: {file_type}")
    print()
    
    if not os.path.exists(file_path):
        print(f"  [ERROR] File not found: {file_path}")
        print(f"  [INFO] Please provide valid file path")
        return False
    
    try:
        # Upload to MinIO
        bronze_key = upload_to_bronze(file_path, file_type)
        
        # Send to Kafka
        send_to_kafka(Path(file_path).name, file_type, bronze_key)
        
        print(f"  [SUCCESS] Test file queued successfully!")
        print(f"  [INFO] Check the AI processor terminal for processing logs")
        return True
        
    except Exception as e:
        print(f"  [ERROR] {e}")
        return False

def get_file_path(file_description: str) -> str:
    """Prompt user to enter file path"""
    print(f"\n{file_description}")
    file_path = input(f"Enter full file path (or press Enter to skip): ").strip()
    
    # Remove quotes if user copied path with quotes
    file_path = file_path.strip('"').strip("'")
    
    return file_path

def get_file_type(file_path: str) -> str:
    """Extract file extension from path"""
    return Path(file_path).suffix.lstrip('.').lower()

# Main test execution
if __name__ == "__main__":
    print("\nStarting AI Model Tests...")
    print("Make sure ai_processor.py is running in another terminal!")
    print()
    
    test_files = []
    
    # Collect test files from user
    print("=" * 80)
    print("FILE SELECTION")
    print("=" * 80)
    print("You will be prompted to provide file paths for testing.")
    print("You can skip any test by pressing Enter without typing a path.")
    print()
    
    # Test 1: Image
    image_path = get_file_path("[1/4] IMAGE MODEL TEST - Enter path to an image file (jpg, png, gif):")
    if image_path and os.path.exists(image_path):
        test_files.append((image_path, get_file_type(image_path), "IMAGE MODEL - Vision OCR & Analysis"))
    
    # Test 2: Text Document
    text_path = get_file_path("[2/4] TEXT MODEL TEST - Enter path to a text document (txt, docx):")
    if text_path and os.path.exists(text_path):
        test_files.append((text_path, get_file_type(text_path), "TEXT MODEL - Document Summarization"))
    
    # Test 3: PDF
    pdf_path = get_file_path("[3/4] TEXT/VISION MODEL TEST - Enter path to a PDF file:")
    if pdf_path and os.path.exists(pdf_path):
        test_files.append((pdf_path, get_file_type(pdf_path), "PDF MODEL - Plain/Scanned PDF Analysis"))
    
    # Test 4: Audio
    audio_path = get_file_path("[4/4] AUDIO MODEL TEST - Enter path to an audio file (mp3, wav):")
    if audio_path and os.path.exists(audio_path):
        test_files.append((audio_path, get_file_type(audio_path), "AUDIO MODEL - Transcription"))
    
    if not test_files:
        print("\n[ERROR] No valid files provided. Exiting.")
        sys.exit(1)
    
    print(f"\n{'='*80}")
    print(f"READY TO TEST {len(test_files)} FILE(S)")
    print("="*80)
    for i, (path, ftype, name) in enumerate(test_files, 1):
        print(f"{i}. {Path(path).name} ({ftype}) - {name}")
    print()
    
    input("Press Enter to start testing...")
    print()
    
    # Run tests
    successful = 0
    failed = 0
    
    for file_path, file_type, test_name in test_files:
        success = test_file(file_path, file_type, test_name)
        if success:
            successful += 1
        else:
            failed += 1
        time.sleep(2)  # Wait between tests
    
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print(f"Total Tests: {len(test_files)}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    print()
    print("Next Steps:")
    print("1. Watch the AI processor terminal for processing logs")
    print("2. Each log will show:")
    print("   - Start time")
    print("   - Model used")
    print("   - Processing time (seconds)")
    print("   - Success/failure status")
    print()
    print("3. Check the UI at http://localhost:5173")
    print("   - Go to 'Silver Layer' or 'Media Dashboard'")
    print("   - View processed files and results")
    print()
    print("4. Take screenshots of:")
    print("   - Terminal output (with timing)")
    print("   - UI showing processed files")
    print("="*80)
    
    producer.close()
