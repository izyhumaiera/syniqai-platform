"""
Test if CDC is capturing changes from client database
"""
import psycopg2
import time
import json
from kafka import KafkaConsumer
from datetime import datetime

# Client database config (from config.json)
DB_CONFIG = {
    'host': '192.168.2.114',
    'port': 5432,
    'database': 'postgres',
    'user': 'postgres',
    'password': 'password'
}

# Kafka config
KAFKA_BOOTSTRAP = '127.0.0.1:9092'
CDC_TOPIC = 'cdc_postgres.public.hosp_raya_patient_record'

print("="*70)
print("  TESTING CDC CAPTURE FROM CLIENT DATABASE")
print("="*70)

# Step 1: Make a change in the database
print("\n1. Connecting to client database...")
try:
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    # Get current record
    cursor.execute("SELECT record_id, medical_info FROM hosp_raya_patient_record WHERE record_id = 101;")
    before = cursor.fetchone()
    
    if before:
        print(f"   ✓ Found record {before[0]}")
        
        # Make an update - just update a simple field to test CDC
        test_value = datetime.now().isoformat()
        print(f"\n2. Making UPDATE with timestamp: {test_value}")
        print(f"   SQL: UPDATE hosp_raya_patient_record SET user_id = user_id WHERE record_id = 101")
        
        # Simple update that will trigger CDC
        cursor.execute("""
            UPDATE hosp_raya_patient_record 
            SET user_id = user_id 
            WHERE record_id = 101;
        """)
        
        conn.commit()
        print("   ✓ UPDATE committed to database")
    else:
        print("   ✗ Record 101 not found")
        cursor.close()
        conn.close()
        exit(1)
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"   ✗ Database error: {e}")
    exit(1)

# Step 2: Wait a moment for Debezium to capture the change
print("\n3. Waiting 3 seconds for Debezium to capture change...")
time.sleep(3)

# Step 3: Check if message appeared in Kafka
print("\n4. Checking Kafka topic for the new UPDATE message...")
print("   (Reading last 10 messages from topic)")
try:
    consumer = KafkaConsumer(
        CDC_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP,
        auto_offset_reset='earliest',  # Read from beginning
        consumer_timeout_ms=5000,
        value_deserializer=lambda x: json.loads(x.decode('utf-8')) if x else None
    )
    
    # Collect last few messages
    messages = []
    for message in consumer:
        if message.value:
            messages.append(message)
    
    consumer.close()
    
    # Check last 10 messages for our UPDATE
    recent = messages[-10:] if len(messages) > 10 else messages
    update_count = sum(1 for m in recent if m.value.get('op') == 'u')
    
    print(f"   ✓ Total messages in topic: {len(messages)}")
    print(f"   ✓ UPDATE operations in last 10: {update_count}")
    
    # Show most recent message
    if recent:
        last = recent[-1]
        print(f"\n   Most recent message:")
        print(f"     Offset: {last.offset}")
        print(f"     Operation: {last.value.get('op')}")
        print(f"     Record ID: {last.value.get('after', {}).get('record_id')}")
        
        if last.value.get('op') == 'u':
            print(f"\n   ✓✓✓ CDC IS WORKING! UPDATE was captured!")
        else:
            print(f"\n   ⚠ Last message is {last.value.get('op')} not UPDATE")
            print(f"     This might be a snapshot (op='r')")
    
except Exception as e:
    print(f"   ✗ Kafka error: {e}")

print("\n" + "="*70)
print("  TEST COMPLETE")
print("="*70)
print("\nTo verify manually:")
print(f"1. Go to Kafka UI: http://localhost:8080")
print(f"2. Check topic: {CDC_TOPIC}")
print("3. Or refresh your GUI at http://localhost:3000")
