import socket
import psycopg2
from minio import Minio

def check_port(host, port, service_name):
    """Check if a port is open"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex((host, port))
        sock.close()
        if result == 0:
            print(f"✓ {service_name} is RUNNING on {host}:{port}")
            return True
        else:
            print(f"✗ {service_name} is NOT RUNNING on {host}:{port}")
            return False
    except Exception as e:
        print(f"✗ {service_name} check failed: {e}")
        return False

def check_postgres():
    """Check PostgreSQL connection"""
    try:
        conn = psycopg2.connect(
            host='localhost',
            port=5432,
            database='syniqai_metadata',
            user='syniqai_user',
            password='syniqai_password',
            connect_timeout=3
        )
        conn.close()
        print("✓ PostgreSQL is RUNNING and accessible (syniqai_metadata)")
        return True
    except Exception as e:
        print(f"✗ PostgreSQL is NOT accessible: {e}")
        return False

def check_minio():
    """Check MinIO connection"""
    try:
        client = Minio('localhost:9000', 'admin', 'password123', secure=False)
        buckets = client.list_buckets()
        print(f"✓ MinIO is RUNNING and accessible ({len(buckets)} buckets)")
        return True
    except Exception as e:
        print(f"✗ MinIO is NOT accessible: {e}")
        return False

print("=" * 60)
print("SYNIQAI SERVICE STATUS CHECK")
print("=" * 60)
print()

# Check all services
services_ok = []

print("[1/5] Checking PostgreSQL...")
services_ok.append(check_postgres())
print()

print("[2/5] Checking MinIO API...")
services_ok.append(check_minio())
print()

print("[3/5] Checking MinIO Console...")
services_ok.append(check_port('localhost', 9001, 'MinIO Console'))
print()

print("[4/6] Checking Kafka Broker...")
services_ok.append(check_port('127.0.0.1', 9092, 'Kafka Broker'))
print()

print("[5/6] Checking Kafka Connect (Debezium)...")
services_ok.append(check_port('localhost', 8083, 'Kafka Connect'))
print()

print("[6/6] Checking Kafka UI...")
services_ok.append(check_port('localhost', 8080, 'Kafka UI'))
print()

print("=" * 60)
if all(services_ok):
    print("✓ ALL SERVICES ARE RUNNING")
    print("=" * 60)
    print()
    print("You can access:")
    print("  - MinIO Console: http://localhost:9001 (admin / password123)")
    print("  - Kafka Connect: http://localhost:8083")
    print("  - Kafka UI: http://localhost:8080")
    print("  - PostgreSQL: localhost:5432 (syniqai_user / syniqai_password)")
else:
    print("✗ SOME SERVICES ARE NOT RUNNING")
    print("=" * 60)
    print()
    if not services_ok[0]:
        print("Start PostgreSQL:")
        print("  - Windows: Services → PostgreSQL")
        print()
    if not services_ok[1] or not services_ok[2]:
        print("Start MinIO:")
        print("  - Run: minio.exe server C:\\minio\\data --console-address :9001")
        print()
    if not services_ok[3]:
        print("Start Kafka Broker:")
        print("  - Run: .\\restart_all_native.ps1")
        print()
    if not services_ok[4]:
        print("Start Kafka Connect (Debezium):")
        print("  - Run: .\\start_kafka_connect.ps1")
        print()
    if not services_ok[5]:
        print("Start Kafka UI:")
        print("  - Check if Kafka UI is configured and running")
