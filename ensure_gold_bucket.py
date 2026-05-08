"""
Ensure syniqai-gold MinIO bucket exists for Gold layer structured data
"""

from minio import Minio
from minio.error import S3Error
import sys

def ensure_gold_bucket():
    """Create syniqai-gold bucket if it doesn't exist"""
    try:
        # Initialize MinIO client
        client = Minio(
            "localhost:9000",
            access_key="admin",
            secret_key="password123",
            secure=False
        )
        
        bucket_name = "syniqai-gold"
        
        # Check if bucket exists
        if client.bucket_exists(bucket_name):
            print(f"✅ Bucket '{bucket_name}' already exists!")
            
            # List some contents
            objects = list(client.list_objects(bucket_name, recursive=False, max_keys=10))
            print(f"   Contains {len(objects)} top-level folders/objects")
            
        else:
            # Create the bucket
            client.make_bucket(bucket_name)
            print(f"✅ Created bucket '{bucket_name}' successfully!")
        
        # Also check silver bucket
        if client.bucket_exists("syniqai-silver"):
            print(f"✅ Bucket 'syniqai-silver' exists")
            objects = list(client.list_objects("syniqai-silver", recursive=False, max_keys=20))
            print(f"   Contains {len(objects)} top-level folders:")
            for obj in objects:
                if obj.is_dir:
                    print(f"      - {obj.object_name}")
        
        # Check bronze bucket
        if client.bucket_exists("syniqai-bronze"):
            print(f"✅ Bucket 'syniqai-bronze' exists")
        
        return True
        
    except S3Error as e:
        print(f"❌ MinIO S3 error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    print("Checking/Creating MinIO buckets for Gold layer...")
    print()
    success = ensure_gold_bucket()
    sys.exit(0 if success else 1)
