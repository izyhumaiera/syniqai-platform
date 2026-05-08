import sys
import os

print("=" * 60)
print("SYNIQ Infrastructure Connection Test")
print("=" * 60)

# Test 1: Kafka Connection
print("\n[1/3] Testing Kafka Connection...")
try:
    from kafka import KafkaAdminClient
    from kafka.errors import KafkaError
    
    client = KafkaAdminClient(
        bootstrap_servers='127.0.0.1:9092',
        request_timeout_ms=5000
    )
    topics = client.list_topics()
    print(f"✓ Kafka Connected - {len(topics)} topics found")
    client.close()
except Exception as e:
    print(f"✗ Kafka Error: {e}")
    

# Test 2: MinIO Connection
print("\n[2/3] Testing MinIO Connection...")
try:
    from minio import Minio
    from minio.error import S3Error
    
    client = Minio(
        "localhost:9000",
        access_key="admin",
        secret_key="password123",
        secure=False
    )
    
    # Test connection
    buckets = client.list_buckets()
    print(f"✓ MinIO Connected - {len(buckets)} buckets found")
    
    # Create required buckets if they don't exist
    required_buckets = ['syniqai-bronze', 'syniqai-silver', 'syniqai-gold']
    for bucket_name in required_buckets:
        if not client.bucket_exists(bucket_name):
            client.make_bucket(bucket_name)
            print(f"  + Created bucket: {bucket_name}")
        else:
            print(f"  ✓ Bucket exists: {bucket_name}")
            
except Exception as e:
    print(f"✗ MinIO Error: {e}")

# Test 3: Spark Availability
print("\n[3/3] Testing Spark Availability...")
spark_home = os.getenv('SPARK_HOME', 'C:\\syniq\\spark\\spark-3.5.8')
spark_submit = os.path.join(spark_home, 'bin', 'spark-submit.cmd')

if os.path.exists(spark_submit):
    print(f"✓ Spark Found at: {spark_home}")
else:
    print(f"✗ Spark not found at: {spark_home}")

print("\n" + "=" * 60)
print("Connection Test Complete!")
print("=" * 60)
