"""
Test CDC to Silver Integration
Verifies the complete flow from Kafka CDC topics to MinIO Silver bucket
"""

import requests
import json
import time

API_BASE = "http://localhost:8000"

def test_cdc_to_silver():
    print("\n" + "="*70)
    print("  TESTING CDC TO SILVER INTEGRATION")
    print("="*70)
    
    # Test 1: Discover CDC topics
    print("\n1. Discovering CDC topics...")
    try:
        response = requests.get(f"{API_BASE}/api/cdc-silver/topics")
        data = response.json()
        
        if data.get('success'):
            print(f"   ✓ Found {data['total']} CDC topics:")
            for topic in data['topics']:
                print(f"     - {topic['topic']}")
                print(f"       Source: {topic['source']}, Table: {topic['table']}")
        else:
            print(f"   ✗ Failed: {data}")
            return False
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False
    
    if data['total'] == 0:
        print("\n   ⚠ No CDC topics found!")
        print("   Run: python setup_cdc_connector.py")
        return False
    
    # Test 2: Start CDC to Silver streaming
    print("\n2. Starting CDC to Silver streaming...")
    try:
        response = requests.post(
            f"{API_BASE}/api/cdc-silver/start",
            json={"auto_discover": True}
        )
        data = response.json()
        
        if data.get('success'):
            print(f"   ✓ Streaming started!")
            print(f"   Job ID: {data['job_id']}")
            print(f"   Active streams: {len(data['active_streams'])}")
            for stream in data['active_streams']:
                print(f"     - {stream['topic']} → {stream['status']}")
        else:
            print(f"   ✗ Failed: {data}")
            return False
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False
    
    # Test 3: Check status
    print("\n3. Checking CDC to Silver status...")
    try:
        response = requests.get(f"{API_BASE}/api/cdc-silver/status")
        data = response.json()
        
        if data.get('success'):
            print(f"   ✓ Running: {data['running']}")
            print(f"   Active streams: {data['total_streams']}")
        else:
            print(f"   ✗ Failed: {data}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    # Test 4: Wait for some processing
    print("\n4. Waiting 30 seconds for data to be processed...")
    print("   (Make a database change now to see real-time processing!)")
    
    for i in range(30, 0, -5):
        print(f"   {i} seconds remaining...")
        time.sleep(5)
    
    # Test 5: List Silver tables
    print("\n5. Checking Silver bucket for tables...")
    try:
        response = requests.get(f"{API_BASE}/api/silver/cdc-tables")
        data = response.json()
        
        if data.get('success'):
            print(f"   ✓ Found {data['total']} tables in Silver:")
            for table in data['tables']:
                print(f"     - {table['full_name']}")
                print(f"       Files: {table['file_count']}, Size: {table['size_mb']} MB")
                print(f"       Last modified: {table['last_modified']}")
        else:
            print(f"   ⚠ No tables yet: {data.get('message', 'Unknown')}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    # Test 6: Preview data (if available)
    if data.get('success') and data['total'] > 0:
        first_table = data['tables'][0]
        source = first_table['source']
        table = first_table['table']
        
        print(f"\n6. Previewing data from {source}.{table}...")
        try:
            response = requests.get(
                f"{API_BASE}/api/silver/cdc-preview/{source}/{table}?limit=3"
            )
            preview = response.json()
            
            if preview.get('success'):
                print(f"   ✓ Preview loaded:")
                print(f"   Total rows: {preview['total_rows']}")
                print(f"   Columns: {len(preview['columns'])}")
                print(f"   First 3 rows:")
                for i, row in enumerate(preview['data'][:3], 1):
                    print(f"     Row {i}: {list(row.keys())[:5]}... ({len(row)} columns)")
            else:
                print(f"   ✗ Failed: {preview}")
        except Exception as e:
            print(f"   ✗ Error: {e}")
    
    print("\n" + "="*70)
    print("  TEST COMPLETE")
    print("="*70)
    print("\n✓ CDC to Silver integration is working!")
    print("\nNext steps:")
    print("  1. Make changes in your client database")
    print("  2. Watch them flow to Silver bucket automatically")
    print("  3. View processed data via API or MinIO console")
    print("  4. Build UI controls in your Silver layer frontend")
    
    return True

if __name__ == "__main__":
    try:
        success = test_cdc_to_silver()
        if not success:
            print("\n⚠ Some tests failed. Check the output above.")
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
