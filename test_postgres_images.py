import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

host = os.getenv('POSTGRES_HOST', 'localhost')
port = os.getenv('POSTGRES_PORT', 5432)
db = os.getenv('POSTGRES_DB', 'syniqai_metadata')
user = os.getenv('POSTGRES_USER', 'syniqai_user')
password = os.getenv('POSTGRES_PASSWORD', 'syniqai_password')

print(f"\n=== PostgreSQL Connection Test ===")
print(f"Host: {host}:{port}")
print(f"Database: {db}")
print(f"User: {user}")

try:
    conn = psycopg2.connect(
        host=host,
        port=port,
        database=db,
        user=user,
        password=password
    )
    cur = conn.cursor()
    
    # Test query matching backend
    cur.execute("""
        SELECT COUNT(*) FROM silver_assets 
        WHERE file_type IN ('jpg','jpeg','png','gif','bmp','webp','tiff')
    """)
    count = cur.fetchone()[0]
    
    print(f"\n✓ Connection successful!")
    print(f"✓ Found {count} images in silver_assets table")
    
    if count > 0:
        # Get sample records
        cur.execute("""
            SELECT id, bronze_minio_key, file_type, extraction_status 
            FROM silver_assets 
            WHERE file_type IN ('jpg','jpeg','png','gif','bmp','webp','tiff')
            ORDER BY processed_at DESC
            LIMIT 3
        """)
        rows = cur.fetchall()
        print("\nSample records:")
        for row in rows:
            print(f"  - ID: {row[0]}, File: {row[1].split('/')[-1]}, Type: {row[2]}, Status: {row[3]}")
    
    cur.close()
    conn.close()
    print("\n✅ Database query works perfectly!")
    print("❌ But the API endpoint returns 0 records")
    print("\nPossible issues:")
    print("  1. Backend using different database connection")
    print("  2. Exception being caught silently")
    print("  3. Wrong DATABASE_URL environment variable")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
