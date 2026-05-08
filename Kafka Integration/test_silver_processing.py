"""
Test Silver Unstructured Data Processing
Tests the complete Bronze -> Silver pipeline for unstructured data
"""

import os
import json
import time
from minio import Minio
from kafka import KafkaProducer
import psycopg2

print("=" * 70)
print(" SILVER UNSTRUCTURED DATA PROCESSING TEST")
print("=" * 70)
print()

# Configuration
MINIO_ENDPOINT = 'localhost:9000'
MINIO_ACCESS_KEY = 'admin'
MINIO_SECRET_KEY = 'password123'
KAFKA_BOOTSTRAP = 'localhost:9092'
PG_HOST = 'localhost'
PG_USER = 'postgres'
PG_PASSWORD = 'password'
PG_DB = 'postgres'

# Test 1: Check Bronze Files
print("[1/5] Checking Bronze Layer...")
try:
    minio_client = Minio(
        MINIO_ENDPOINT,
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=False
    )
    
    bronze_objects = list(minio_client.list_objects('syniqai-bronze', recursive=True))
    print(f"✅ Bronze bucket: {len(bronze_objects)} files")
    
    if bronze_objects:
        print("\nSample files:")
        for obj in bronze_objects[:5]:
            print(f"  • {obj.object_name} ({obj.size} bytes)")
    else:
        print("⚠️  No files in bronze - upload a test file first!")
        
except Exception as e:
    print(f"❌ MinIO error: {e}")

print()

# Test 2: Emit Bronze-Ready Event
print("[2/5] Testing Bronze-Ready Event Emission...")
try:
    if bronze_objects:
        # Pick first file
        test_file = bronze_objects[0]
        
        # Create CDC event
        cdc_event = {
            "file_id": test_file.object_name,
            "file_name": test_file.object_name.split('/')[-1],
            "bucket": "syniqai-bronze",
            "key": test_file.object_name,
            "size": test_file.size,
            "event_type": "ObjectCreated:Put",
            "source": "test_script",
            "timestamp": time.time()
        }
        
        # Send to Kafka
        producer = KafkaProducer(
            bootstrap_servers=KAFKA_BOOTSTRAP,
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        
        producer.send('bronze-ready', value=cdc_event)
        producer.flush()
        
        print(f"✅ Sent event to bronze-ready topic:")
        print(f"   File: {test_file.object_name}")
        print(f"   Size: {test_file.size} bytes")
        print()
        print("⏳ AI Processor should pick this up within 5-10 seconds...")
        print("   Watch the AI Processor window for activity")
        
    else:
        print("⚠️  No bronze files to test with")
        
except Exception as e:
    print(f"❌ Kafka error: {e}")

print()

# Test 3: Check AI Processor Status
print("[3/5] Checking if AI Processor is running...")
try:
    import psutil
    ai_processor_running = False
    
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = ' '.join(proc.info.get('cmdline', [])).lower()
            if 'python' in cmdline and 'ai_processor' in cmdline:
                print(f"✅ AI Processor is running (PID: {proc.info['pid']})")
                ai_processor_running = True
                break
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    
    if not ai_processor_running:
        print("❌ AI Processor NOT running!")
        print("   Start it: cd 'Kafka Integration'; python ai_processor.py")
        
except ImportError:
    print("⚠️  psutil not installed - cannot check process")

print()

# Test 4: Monitor Processing (wait a bit)
print("[4/5] Waiting for processing (15 seconds)...")
time.sleep(15)

# Test 5: Check Silver Results
print("\n[5/5] Checking Silver Layer Results...")
try:
    conn = psycopg2.connect(
        host=PG_HOST,
        user=PG_USER,
        password=PG_PASSWORD,
        dbname=PG_DB
    )
    cur = conn.cursor()
    
    # Check table
    cur.execute("SELECT COUNT(*) FROM unstructured_document_metadata;")
    total_count = cur.fetchone()[0]
    
    # Check recent records
    cur.execute("""
        SELECT 
            file_name,
            processing_status,
            model_used,
            extracted_text_length,
            processed_at
        FROM unstructured_document_metadata
        ORDER BY processed_at DESC
        LIMIT 5;
    """)
    
    recent = cur.fetchall()
    
    print(f"✅ Database: {total_count} records in unstructured_document_metadata")
    
    if recent:
        print("\n📊 Recent Processed Files:")
        for row in recent:
            file_name, status, model, text_len, processed = row
            print(f"\n  • File: {file_name}")
            print(f"    Status: {status}")
            print(f"    Model: {model}")
            print(f"    Text Length: {text_len} chars")
            print(f"    Processed: {processed}")
    else:
        print("\n⚠️  No processed records yet")
        print("   This is normal if AI processing just started")
        print("   Wait 30-60 seconds and check again")
    
    # Check Silver MinIO
    silver_objects = list(minio_client.list_objects('syniqai-silver', recursive=True))
    print(f"\n✅ Silver bucket: {silver_objects} files")
    
    if silver_objects:
        print("\nSample Silver files:")
        for obj in silver_objects[:3]:
            print(f"  • {obj.object_name}")
    
    conn.close()
    
except Exception as e:
    print(f"❌ Database/MinIO error: {e}")

print()
print("=" * 70)
print(" TEST COMPLETE")
print("=" * 70)
print()
print("✅ NEXT STEPS:")
print("  1. Check AI Processor window for processing logs")
print("  2. Verify file appears in Silver Layer GUI")
print("  3. Upload more test files via GUI Bronze Explorer")
print()
print("🔍 VERIFY IN GUI:")
print("  • Open: http://localhost:3000")
print("  • Go to: Silver Layer → Unstructured Workspace")
print("  • Tab: Text Extraction")
print("  • You should see processed files with extracted text")
