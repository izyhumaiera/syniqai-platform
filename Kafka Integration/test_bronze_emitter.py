"""
Test Bronze Ready Emitter
==========================
Sends test messages to bronze-mongodb and bronze-s3 topics to verify
the bronze_ready_emitter.py routing logic.

Usage:
    python test_bronze_emitter.py
"""

import json
import os
import sys
import time
from datetime import datetime
from kafka import KafkaProducer, KafkaConsumer
from kafka.errors import KafkaError

# Configuration
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
BRONZE_MONGODB_TOPIC = "bronze-mongodb"
BRONZE_S3_TOPIC = "bronze-s3"
READY_TOPIC = "bronze-ready"
MEDIA_PENDING_TOPIC = "bronze-media-pending"

# Test data
MONGODB_TEST_MESSAGES = [
    {
        'op': 'insert',
        'source': {
            'db': 'test_db',
            'collection': 'documents',
            'ts_ms': int(datetime.utcnow().timestamp() * 1000)
        },
        'after': {
            '_id': 'test_doc_001',
            'title': 'Test PDF Document',
            'file_path': 'documents/report.pdf'
        }
    },
    {
        'op': 'insert',
        'source': {
            'db': 'test_db',
            'collection': 'media',
            'ts_ms': int(datetime.utcnow().timestamp() * 1000)
        },
        'after': {
            '_id': 'test_doc_002',
            'title': 'Test Video File',
            'file_path': 'videos/demo.mp4'
        }
    },
    {
        'op': 'insert',
        'source': {
            'db': 'test_db',
            'collection': 'images',
            'ts_ms': int(datetime.utcnow().timestamp() * 1000)
        },
        'after': {
            '_id': 'test_doc_003',
            'title': 'Test Image',
            'file_path': 'images/photo.jpg'
        }
    }
]

S3_TEST_MESSAGES = [
    {
        'op': 'create',
        'source': {
            'bucket': 'test-bucket',
            'region': 'us-east-1',
            'ts_ms': int(datetime.utcnow().timestamp() * 1000)
        },
        'file': {
            'key': 'documents/report.pdf',
            'etag': 'abc123',
            'size': 1024000,
            'last_modified': datetime.utcnow().isoformat(),
            's3_uri': 's3://test-bucket/documents/report.pdf'
        }
    },
    {
        'op': 'create',
        'source': {
            'bucket': 'test-bucket',
            'region': 'us-east-1',
            'ts_ms': int(datetime.utcnow().timestamp() * 1000)
        },
        'file': {
            'key': 'videos/presentation.mp4',
            'etag': 'def456',
            'size': 50240000,
            'last_modified': datetime.utcnow().isoformat(),
            's3_uri': 's3://test-bucket/videos/presentation.mp4'
        }
    },
    {
        'op': 'create',
        'source': {
            'bucket': 'test-bucket',
            'region': 'us-east-1',
            'ts_ms': int(datetime.utcnow().timestamp() * 1000)
        },
        'file': {
            'key': 'audio/podcast.mp3',
            'etag': 'ghi789',
            'size': 8192000,
            'last_modified': datetime.utcnow().isoformat(),
            's3_uri': 's3://test-bucket/audio/podcast.mp3'
        }
    },
    {
        'op': 'create',
        'source': {
            'bucket': 'test-bucket',
            'region': 'us-east-1',
            'ts_ms': int(datetime.utcnow().timestamp() * 1000)
        },
        'file': {
            'key': 'logs/application.log',
            'etag': 'jkl012',
            'size': 204800,
            'last_modified': datetime.utcnow().isoformat(),
            's3_uri': 's3://test-bucket/logs/application.log'
        }
    }
]


def create_producer():
    """Create Kafka producer"""
    return KafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS.split(','),
        value_serializer=lambda v: json.dumps(v, default=str).encode('utf-8'),
        key_serializer=lambda k: k.encode('utf-8') if k else None,
        acks='all',
        retries=3
    )


def create_consumer(topics):
    """Create Kafka consumer"""
    return KafkaConsumer(
        *topics,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS.split(','),
        group_id=f'test-consumer-{int(time.time())}',
        auto_offset_reset='latest',
        value_deserializer=lambda m: json.loads(m.decode('utf-8')),
        consumer_timeout_ms=10000  # Stop after 10s of no messages
    )


def send_test_messages(producer):
    """Send test messages to bronze topics"""
    print("\n" + "=" * 70)
    print("Sending Test Messages")
    print("=" * 70)
    
    # Send MongoDB messages
    print(f"\nSending {len(MONGODB_TEST_MESSAGES)} messages to {BRONZE_MONGODB_TOPIC}...")
    for i, msg in enumerate(MONGODB_TEST_MESSAGES, 1):
        key = msg['after']['_id']
        future = producer.send(BRONZE_MONGODB_TOPIC, key=key, value=msg)
        try:
            future.get(timeout=5)
            print(f"  ✓ [{i}/{len(MONGODB_TEST_MESSAGES)}] Sent: {key} ({msg['after']['file_path']})")
        except KafkaError as e:
            print(f"  ✗ [{i}/{len(MONGODB_TEST_MESSAGES)}] Failed: {e}")
    
    # Send S3 messages
    print(f"\nSending {len(S3_TEST_MESSAGES)} messages to {BRONZE_S3_TOPIC}...")
    for i, msg in enumerate(S3_TEST_MESSAGES, 1):
        key = msg['file']['key']
        future = producer.send(BRONZE_S3_TOPIC, key=key, value=msg)
        try:
            future.get(timeout=5)
            print(f"  ✓ [{i}/{len(S3_TEST_MESSAGES)}] Sent: {key}")
        except KafkaError as e:
            print(f"  ✗ [{i}/{len(S3_TEST_MESSAGES)}] Failed: {e}")
    
    producer.flush()
    print("\n✓ All test messages sent successfully!")


def consume_routed_messages():
    """Consume from output topics to verify routing"""
    print("\n" + "=" * 70)
    print("Consuming Routed Messages (waiting 10 seconds)...")
    print("=" * 70)
    
    consumer = create_consumer([READY_TOPIC, MEDIA_PENDING_TOPIC])
    
    ready_count = 0
    media_pending_count = 0
    
    print("\nListening for routed messages...\n")
    
    try:
        for message in consumer:
            topic = message.topic
            value = message.value
            
            if topic == READY_TOPIC:
                ready_count += 1
                print(f"  ✓ [bronze-ready] {value.get('file_type', '?').upper()}: {value.get('object_key', '?')}")
            elif topic == MEDIA_PENDING_TOPIC:
                media_pending_count += 1
                print(f"  ⏸ [bronze-media-pending] {value.get('file_type', '?').upper()}: {value.get('object_key', '?')}")
            
    except KeyboardInterrupt:
        print("\n\nStopped by user")
    except Exception as e:
        print(f"\n\nConsumer timeout or error: {e}")
    finally:
        consumer.close()
    
    # Summary
    print("\n" + "=" * 70)
    print("Routing Summary")
    print("=" * 70)
    print(f"  ✓ bronze-ready:        {ready_count} messages")
    print(f"  ⏸ bronze-media-pending: {media_pending_count} messages")
    print(f"  Total:                 {ready_count + media_pending_count} messages")
    print("=" * 70)
    
    # Expected results
    print("\nExpected Results:")
    print("  ✓ bronze-ready should have: 4-5 messages (PDFs, TXT, JPG)")
    print("  ⏸ bronze-media-pending should have: 2-3 messages (MP4, MP3)")
    
    # Verification
    if ready_count >= 4 and media_pending_count >= 2:
        print("\n✅ TEST PASSED: Routing working correctly!")
    else:
        print("\n⚠️  TEST WARNING: Unexpected routing results")
        print("    Make sure bronze_ready_emitter.py is running!")


def main():
    """Main test function"""
    print("\n" + "=" * 70)
    print("Bronze Ready Emitter - Test Script")
    print("=" * 70)
    print(f"Kafka Bootstrap Servers: {KAFKA_BOOTSTRAP_SERVERS}")
    print(f"Input Topics: {BRONZE_MONGODB_TOPIC}, {BRONZE_S3_TOPIC}")
    print(f"Output Topics: {READY_TOPIC}, {MEDIA_PENDING_TOPIC}")
    print("=" * 70)
    
    # Check if emitter is running
    print("\n⚠️  IMPORTANT: Make sure bronze_ready_emitter.py is running!")
    print("   Start it with: python bronze_ready_emitter.py")
    print("\nPress Enter to continue or Ctrl+C to exit...")
    try:
        input()
    except KeyboardInterrupt:
        print("\n\nTest cancelled.")
        sys.exit(0)
    
    try:
        # Create producer and send messages
        producer = create_producer()
        send_test_messages(producer)
        producer.close()
        
        # Wait a moment for emitter to process
        print("\nWaiting 3 seconds for emitter to process messages...")
        time.sleep(3)
        
        # Consume routed messages
        consume_routed_messages()
        
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user.")
    except Exception as e:
        print(f"\n\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\nTest completed.")


if __name__ == "__main__":
    main()
