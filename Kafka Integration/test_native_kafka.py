"""Test native Kafka connection"""
from kafka import KafkaProducer, KafkaConsumer
from kafka.errors import NoBrokersAvailable
import json

print("Testing native Kafka connection at localhost:9092...")

try:
    # Test Producer with explicit API version
    print("\n1. Testing KafkaProducer...")
    producer = KafkaProducer(
        bootstrap_servers=['localhost:9092'],
        api_version=(2, 8, 1),  # Kafka 4.2.0 compatible
        request_timeout_ms=10000,
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )
    
    # Send test message
    future = producer.send('test-native-cdc', {'test': 'hello'})
    record = future.get(timeout=10)
    producer.flush()
    producer.close()
    
    print(f"✓ Producer SUCCESS! Message sent to partition {record.partition}, offset {record.offset}")
    
    # Test Consumer
    print("\n2. Testing KafkaConsumer...")
    consumer = KafkaConsumer(
        'test-native-cdc',
        bootstrap_servers=['localhost:9092'],
        api_version=(2, 8, 1),
        auto_offset_reset='earliest',
        consumer_timeout_ms=5000,
        value_deserializer=lambda m: json.loads(m.decode('utf-8'))
    )
    
    for msg in consumer:
        print(f"✓ Consumer SUCCESS! Received: {msg.value}")
        break
    
    consumer.close()
    
    print("\n" + "="*50)
    print("✓ ✓✓ KAFKA CONNECTION SUCCESSFUL!")
    print("="*50)
    print("Native Kafka at localhost:9092 is working!")
    
except NoBrokersAvailable as e:
    print(f"\n✗ No brokers available: {e}")
    print("\nTroubleshooting:")
    print("1. Check if Kafka is running: Get-Process java | Where Path -like '*kafka*'")
    print("2. Check port 9092: Test-NetConnection localhost -Port 9092")
    print("3. Check Kafka logs in C:\\kafka\\kafka-4.2.0\\logs")
    
except Exception as e:
    print(f"\n✗ Error: {e}")
    print(f"Type: {type(e).__name__}")
