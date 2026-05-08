#!/usr/bin/env python3
"""
Insert a test record to verify end-to-end CDC pipeline
"""
import psycopg2
from datetime import datetime

DB_CONFIG = {
    'host': '192.168.2.114',
    'port': 5432,
    'database': 'postgres',
    'user': 'debezium_user',
    'password': 'debezium_password'
}

try:
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    # Get next ID
    cursor.execute("SELECT COALESCE(MAX(loan_id), 100) + 1 FROM loan_applications")
    next_id = cursor.fetchone()[0]
    
    # Insert test record
    cursor.execute("""
        INSERT INTO loan_applications (
            loan_id, applicant_name, applicant_email, loan_amount, interest_rate, 
            loan_term_months, application_date, application_status
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        next_id,
        f'CDC Test {next_id}',
        f'cdctest{next_id}@test.com',
        25000.00,
        4.5,
        24,
        datetime.now(),
        'pending'
    ))
    
    conn.commit()
    
    print(f"✅ Inserted loan_id={next_id}")
    print(f"   Applicant: CDC Test {next_id}")
    print(f"   Amount: $25,000.00")
    print(f"\n📊 Check results:")
    print(f"   1. Kafka Topics: kafka-topics.bat --bootstrap-server localhost:9092 --list")
    print(f"   2. CDC Consumer logs: Check logs folder in Kafka Integration directory")
    print(f"   3. MinIO: http://localhost:9001 → bronze bucket → postgres folder")
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"✗ Error: {e}")
