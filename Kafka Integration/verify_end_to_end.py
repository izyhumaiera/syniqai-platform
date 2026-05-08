"""
End-to-End Data Verification Script
====================================
Verifies data consistency from Bronze → Silver → Gold

Checks:
1. Bronze files in MinIO
2. Silver metadata in PostgreSQL (unstructured_document_metadata)
3. Gold analytics in PostgreSQL (gold_entities, etc.)
4. Data lineage and consistency

Usage:
    python verify_end_to_end.py
"""

import os
import sys
from pathlib import Path
from datetime import datetime
import psycopg2
from minio import Minio
from dotenv import load_dotenv

# Load environment
load_dotenv(Path(__file__).parent / ".env")

# Configuration
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "127.0.0.1:9092")
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "admin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "password123")

POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB", "syniqai")
POSTGRES_USER = os.getenv("POSTGRES_USER", "syniqai_user")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "syniqai_pass")


def print_header(title):
    """Print formatted section header"""
    print()
    print("=" * 70)
    print(f"  {title}")
    print("=" * 70)


def check_bronze_layer():
    """Check Bronze layer files in MinIO"""
    print_header("BRONZE LAYER (MinIO)")
    
    try:
        client = Minio(
            MINIO_ENDPOINT,
            access_key=MINIO_ACCESS_KEY,
            secret_key=MINIO_SECRET_KEY,
            secure=False
        )
        
        # Check bucket exists
        if not client.bucket_exists("syniqai-bronze"):
            print("❌ syniqai-bronze bucket does not exist")
            return 0
        
        print("✅ syniqai-bronze bucket exists")
        
        # Count objects
        objects = list(client.list_objects("syniqai-bronze", recursive=True))
        total_size = sum(obj.size for obj in objects)
        
        print(f"📦 Total files: {len(objects)}")
        print(f"💾 Total size: {total_size / (1024*1024):.2f} MB")
        
        if len(objects) > 0:
            print("\n📁 Recent files:")
            # Show last 5 files
            for obj in sorted(objects, key=lambda x: x.last_modified, reverse=True)[:5]:
                size_mb = obj.size / (1024*1024)
                print(f"   - {obj.object_name} ({size_mb:.2f} MB) - {obj.last_modified}")
        
        return len(objects)
        
    except Exception as e:
        print(f"❌ Error accessing MinIO: {e}")
        return 0


def check_silver_layer():
    """Check Silver layer data in PostgreSQL"""
    print_header("SILVER LAYER (PostgreSQL)")
    
    try:
        conn = psycopg2.connect(
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
            database=POSTGRES_DB,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD
        )
        cursor = conn.cursor()
        
        # Check unstructured_document_metadata table
        cursor.execute("""
            SELECT COUNT(*) FROM unstructured_document_metadata
        """)
        doc_count = cursor.fetchone()[0]
        
        print(f"📄 Unstructured documents: {doc_count}")
        
        if doc_count > 0:
            # Get processing stats
            cursor.execute("""
                SELECT 
                    processing_status,
                    COUNT(*) as count
                FROM unstructured_document_metadata
                GROUP BY processing_status
            """)
            stats = cursor.fetchall()
            
            print("\n📊 Processing Status:")
            for status, count in stats:
                print(f"   - {status}: {count}")
            
            # Show recent documents
            cursor.execute("""
                SELECT 
                    file_name,
                    processing_status,
                    model_used,
                    processed_at
                FROM unstructured_document_metadata
                ORDER BY processed_at DESC
                LIMIT 5
            """)
            recent = cursor.fetchall()
            
            print("\n📝 Recent documents:")
            for file_name, status, model, processed_at in recent:
                print(f"   - {file_name}")
                print(f"     Status: {status} | Model: {model} | {processed_at}")
        
        # Check for Silver MinIO data
        try:
            client = Minio(
                MINIO_ENDPOINT,
                access_key=MINIO_ACCESS_KEY,
                secret_key=MINIO_SECRET_KEY,
                secure=False
            )
            
            if client.bucket_exists("syniqai-silver"):
                objects = list(client.list_objects("syniqai-silver", recursive=True))
                print(f"\n💎 Silver bucket files: {len(objects)}")
        except:
            pass
        
        conn.close()
        return doc_count
        
    except Exception as e:
        print(f"❌ Error accessing PostgreSQL: {e}")
        return 0


def check_gold_layer():
    """Check Gold layer analytics in PostgreSQL"""
    print_header("GOLD LAYER (PostgreSQL Analytics)")
    
    try:
        conn = psycopg2.connect(
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
            database=POSTGRES_DB,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD
        )
        cursor = conn.cursor()
        
        # Check for common gold tables
        gold_tables = [
            "gold_entities",
            "gold_aggregated_metrics",
            "gold_data_quality_summary",
            "gold_document_analytics"
        ]
        
        total_gold_records = 0
        
        for table in gold_tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                total_gold_records += count
                
                if count > 0:
                    print(f"✅ {table}: {count} records")
                else:
                    print(f"⚠️  {table}: 0 records")
            except psycopg2.Error:
                print(f"❌ {table}: table does not exist")
        
        conn.close()
        return total_gold_records
        
    except Exception as e:
        print(f"❌ Error accessing PostgreSQL: {e}")
        return 0


def check_kafka_connectivity():
    """Check Kafka broker connectivity"""
    print_header("KAFKA CONNECTIVITY")
    
    try:
        from kafka import KafkaAdminClient
        from kafka.errors import NoBrokersAvailable
        
        admin_client = KafkaAdminClient(
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            client_id='end-to-end-verifier',
            request_timeout_ms=5000
        )
        
        topics = admin_client.list_topics()
        print(f"✅ Kafka broker connected: {KAFKA_BOOTSTRAP_SERVERS}")
        print(f"📋 Topics available: {len(topics)}")
        
        # Check for required topics
        required_topics = [
            "bronze-ready",
            "silver-ready",
            "bronze-mongodb",
            "bronze-s3"
        ]
        
        print("\n🔍 Required topics:")
        for topic in required_topics:
            if topic in topics:
                print(f"   ✅ {topic}")
            else:
                print(f"   ❌ {topic} - MISSING")
        
        admin_client.close()
        return True
        
    except NoBrokersAvailable:
        print(f"❌ Cannot connect to Kafka broker: {KAFKA_BOOTSTRAP_SERVERS}")
        print("   Make sure Kafka is running on 127.0.0.1:9092")
        return False
    except Exception as e:
        print(f"❌ Kafka error: {e}")
        return False


def main():
    """Run end-to-end verification"""
    print()
    print("=" * 70)
    print("  SyniqAI End-to-End Data Verification")
    print("=" * 70)
    print()
    print(f"⏰ Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Check Kafka first
    kafka_ok = check_kafka_connectivity()
    
    # Check each layer
    bronze_count = check_bronze_layer()
    silver_count = check_silver_layer()
    gold_count = check_gold_layer()
    
    # Summary
    print_header("VERIFICATION SUMMARY")
    
    print(f"🟤 Bronze Layer: {bronze_count} files")
    print(f"🔷 Silver Layer: {silver_count} documents")
    print(f"🟨 Gold Layer: {gold_count} analytics records")
    
    print()
    
    # Data consistency check
    if bronze_count > 0 and silver_count > 0:
        conversion_rate = (silver_count / bronze_count) * 100
        print(f"📊 Bronze → Silver conversion: {conversion_rate:.1f}%")
    
    if silver_count > 0 and gold_count > 0:
        gold_rate = (gold_count / silver_count) * 100
        print(f"📊 Silver → Gold transformation: {gold_rate:.1f}%")
    
    print()
    
    # Overall status
    if kafka_ok and bronze_count > 0 and silver_count > 0 and gold_count > 0:
        print("🎉 END-TO-END PIPELINE: FULLY OPERATIONAL")
        print("   ✅ Data flowing from Bronze → Silver → Gold")
    elif bronze_count > 0 and silver_count > 0:
        print("⚠️  PARTIAL SUCCESS: Bronze and Silver working")
        print("   ⚠️  No Gold layer data - check gold processor")
    elif bronze_count > 0:
        print("⚠️  LIMITED SUCCESS: Bronze layer working")
        print("   ⚠️  No Silver/Gold data - check AI processor")
    else:
        print("❌ PIPELINE ISSUES DETECTED")
        print("   Please check individual layer errors above")
    
    print()
    print("=" * 70)
    print()


if __name__ == "__main__":
    main()
