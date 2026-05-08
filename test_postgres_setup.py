"""
Test PostgreSQL connection for SyniqAI
"""
import psycopg2

DATABASE_URL = "postgresql://syniqai_user:syniqai_password@localhost:5432/syniqai_metadata"

print("Testing PostgreSQL connection...")
print(f"Connecting to: localhost:5432/syniqai_metadata")
print(f"User: syniqai_user")
print("")

try:
    # Connect
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    # Test query
    cur.execute("SELECT version();")
    version = cur.fetchone()[0]
    print("✓ Connection successful!")
    print(f"✓ PostgreSQL version: {version[:50]}...")
    print("")
    
    # Check tables
    cur.execute("""
        SELECT table_name FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_name LIKE 'silver%'
    """)
    tables = cur.fetchall()
    
    print("✓ Tables found:")
    for table in tables:
        print(f"  • {table[0]}")
    print("")
    
    # Test insert (and rollback)
    cur.execute("""
        INSERT INTO silver_assets (
            source, file_type, bronze_minio_key, silver_minio_key, 
            extraction_status, file_size_bytes
        ) VALUES (
            'test', 'jpg', 'test/file.jpg', 'test/file.json',
            'success', 12345
        ) RETURNING id
    """)
    test_id = cur.fetchone()[0]
    print(f"✓ Test insert successful (id: {test_id})")
    
    # Rollback test data
    conn.rollback()
    print("✓ Test data rolled back (database unchanged)")
    print("")
    
    cur.close()
    conn.close()
    
    print("="*50)
    print("✓✓✓ PostgreSQL is ready for SyniqAI!")
    print("="*50)
    print("")
    print("Next step: Run ai_processor.py")
    
except psycopg2.OperationalError as e:
    print(f"✗ Connection failed: {e}")
    print("")
    print("Possible issues:")
    print("1. Database 'syniqai_metadata' not created")
    print("2. User 'syniqai_user' not created")
    print("3. Wrong password")
    print("4. PostgreSQL not running")
    
except Exception as e:
    print(f"✗ Error: {e}")
    print(f"   Type: {type(e).__name__}")
