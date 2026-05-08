"""
Quick Backend API Diagnostic
Identifies why endpoints are returning 500 errors
"""

import requests
import psycopg2
from minio import Minio

print("=" * 60)
print(" BACKEND API DIAGNOSTIC")
print("=" * 60)
print()

# 1. Test Backend API
print("[1/4] Testing Backend API...")
try:
    response = requests.get("http://localhost:8000/docs", timeout=3)
    if response.status_code == 200:
        print("✅ Backend API is running")
    else:
        print(f"⚠️  Backend API responded with: {response.status_code}")
except Exception as e:
    print(f"❌ Backend API error: {e}")
print()

# 2. Test PostgreSQL
print("[2/4] Testing PostgreSQL...")
try:
    conn = psycopg2.connect(
        host='localhost',
        port=5432,
        user='postgres',
        password='password',
        dbname='postgres'
    )
    cur = conn.cursor()
    
    # Check for required tables
    cur.execute("""
        SELECT tablename 
        FROM pg_tables 
        WHERE schemaname='public' 
        AND (tablename LIKE '%bronze%' OR tablename LIKE '%silver%' OR tablename LIKE '%unstructured%')
        ORDER BY tablename;
    """)
    tables = [row[0] for row in cur.fetchall()]
    
    if tables:
        print(f"✅ PostgreSQL connected - {len(tables)} relevant tables found:")
        for table in tables:
            print(f"   • {table}")
    else:
        print("⚠️  PostgreSQL connected but NO bronze/silver tables found!")
        print("   This may be why API returns 500 errors")
    
    conn.close()
except Exception as e:
    print(f"❌ PostgreSQL error: {e}")
print()

# 3. Test MinIO
print("[3/4] Testing MinIO...")
try:
    client = Minio(
        'localhost:9000',
        access_key='admin',
        secret_key='password123',
        secure=False
    )
    
    buckets = [bucket.name for bucket in client.list_buckets()]
    print(f"✅ MinIO connected - {len(buckets)} buckets found:")
    for bucket in buckets:
        if 'syniqai' in bucket:
            try:
                objects = list(client.list_objects(bucket, recursive=True))
                print(f"   • {bucket}: {len(objects)} objects")
            except:
                print(f"   • {bucket}: (empty or error)")
except Exception as e:
    print(f"❌ MinIO error: {e}")
print()

# 4. Test specific API endpoints
print("[4/4] Testing API Endpoints...")
endpoints = [
    "/api/bronze/files?limit=5",
    "/api/silver/assets?limit=5",
    "/api/dashboard-summary?domain=general",
]

for endpoint in endpoints:
    try:
        url = f"http://localhost:8000{endpoint}"
        response = requests.get(url, timeout=3)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ {endpoint}: OK")
        elif response.status_code == 404:
            print(f"⚠️  {endpoint}: Not Found (endpoint missing)")
        elif response.status_code == 500:
            print(f"❌ {endpoint}: 500 Internal Server Error")
            try:
                error = response.json()
                print(f"   Error: {error.get('detail', 'No details')}")
            except:
                print(f"   Raw response: {response.text[:200]}")
        else:
            print(f"⚠️  {endpoint}: Status {response.status_code}")
    except requests.exceptions.ConnectionError:
        print(f"❌ {endpoint}: Connection refused")
    except Exception as e:
        print(f"❌ {endpoint}: {e}")

print()
print("=" * 60)
print(" DIAGNOSIS COMPLETE")
print("=" * 60)
print()
print("LIKELY CAUSES OF 500 ERRORS:")
print("  1. Missing database tables (check if tables exist above)")
print("  2. Database connection issues")
print("  3. MinIO bucket access errors")
print("  4. Backend code errors (check backend window for Python tracebacks)")
print()
print("SOLUTION:")
print("  • Check the FastAPI backend window for detailed error messages")
print("  • Look for Python exceptions and tracebacks")
print("  • Ensure database tables are created")
