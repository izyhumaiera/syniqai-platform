#!/usr/bin/env python3
"""
Test Native Kafka CDC Setup
Verifies all components for database CDC with native Kafka
"""
import requests
import psycopg2
import sys
from kafka import KafkaAdminClient
from kafka.errors import KafkaError

def test_kafka_broker():
    """Test native Kafka broker connection"""
    print("\n[1/4] Testing Kafka Broker (localhost:9092)...")
    try:
        admin = KafkaAdminClient(
            bootstrap_servers=['localhost:9092'],
            client_id='test-client',
            request_timeout_ms=5000
        )
        topics = admin.list_topics()
        print(f"  ✓ Kafka broker is running")
        print(f"  ✓ Found {len(topics)} topics")
        admin.close()
        return True
    except KafkaError as e:
        print(f"  ✗ Kafka broker not accessible: {e}")
        return False

def test_kafka_connect():
    """Test Kafka Connect availability"""
    print("\n[2/4] Testing Kafka Connect (localhost:8083)...")
    try:
        response = requests.get("http://localhost:8083/", timeout=5)
        if response.status_code == 200:
            print(f"  ✓ Kafka Connect is running")
            
            # Check connector plugins
            plugins_response = requests.get("http://localhost:8083/connector-plugins", timeout=5)
            plugins = plugins_response.json()
            
            postgres_plugin = any('PostgresConnector' in p.get('class', '') for p in plugins)
            mysql_plugin = any('MySqlConnector' in p.get('class', '') for p in plugins)
            
            if postgres_plugin:
                print(f"  ✓ PostgreSQL Debezium connector installed")
            else:
                print(f"  ✗ PostgreSQL Debezium connector NOT found")
                
            if mysql_plugin:
                print(f"  ✓ MySQL Debezium connector installed")
            else:
                print(f"  ✗ MySQL Debezium connector NOT found")
                
            return postgres_plugin or mysql_plugin
        else:
            print(f"  ✗ Kafka Connect returned status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"  ✗ Kafka Connect not running at localhost:8083")
        print(f"  ℹ Start with: .\\start_kafka_connect.ps1")
        return False
    except Exception as e:
        print(f"  ✗ Error checking Kafka Connect: {e}")
        return False

def test_postgresql():
    """Test PostgreSQL configuration for CDC"""
    print("\n[3/4] Testing PostgreSQL CDC Configuration...")
    try:
        conn = psycopg2.connect(
            host='localhost',
            port=5432,
            database='postgres',
            user='postgres',
            password='password'
        )
        cursor = conn.cursor()
        
        # Check WAL level
        cursor.execute("SHOW wal_level;")
        wal_level = cursor.fetchone()[0]
        if wal_level == 'logical':
            print(f"  ✓ WAL level is 'logical' (CDC ready)")
        else:
            print(f"  ✗ WAL level is '{wal_level}' (should be 'logical')")
            print(f"  ℹ Run: ALTER SYSTEM SET wal_level = 'logical'; then restart PostgreSQL")
        
        # Check debezium user
        cursor.execute("SELECT 1 FROM pg_roles WHERE rolname='debezium_user';")
        if cursor.fetchone():
            print(f"  ✓ debezium_user exists")
            
            # Check replication privilege
            cursor.execute("SELECT rolreplication FROM pg_roles WHERE rolname='debezium_user';")
            has_replication = cursor.fetchone()[0]
            if has_replication:
                print(f"  ✓ debezium_user has REPLICATION privilege")
            else:
                print(f"  ✗ debezium_user missing REPLICATION privilege")
                print(f"  ℹ Run: ALTER USER debezium_user WITH REPLICATION;")
        else:
            print(f"  ✗ debezium_user does not exist")
            print(f"  ℹ Run: python fix_debezium_permissions_local.py")
        
        # Check publication
        cursor.execute("SELECT 1 FROM pg_publication WHERE pubname='dbz_syniq_postgres_publication';")
        if cursor.fetchone():
            print(f"  ✓ Publication 'dbz_syniq_postgres_publication' exists")
        else:
            print(f"  ✗ Publication not found")
            print(f"  ℹ Run: CREATE PUBLICATION dbz_syniq_postgres_publication FOR ALL TABLES;")
        
        cursor.close()
        conn.close()
        return wal_level == 'logical'
        
    except psycopg2.OperationalError as e:
        print(f"  ✗ PostgreSQL connection failed: {e}")
        return False
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False

def test_summary(kafka_ok, connect_ok, postgres_ok):
    """Print test summary"""
    print("\n" + "="*80)
    print("                          SUMMARY")
    print("="*80)
    
    if kafka_ok and connect_ok and postgres_ok:
        print("\n✅ ALL COMPONENTS READY FOR DATABASE CDC")
        print("\nNext Steps:")
        print("  1. Create Debezium connector:")
        print("     python -c \"from debezium_manager import get_debezium_manager, ConnectorConfig; ...\"")
        print("  2. Or use the GUI to configure CDC")
        return True
    else:
        print("\n⚠️ SOME COMPONENTS NEED SETUP")
        print("\nRequired Actions:")
        
        if not kafka_ok:
            print("  ✗ Start Kafka broker:")
            print("    cd C:\\kafka\\kafka-4.2.0")
            print("    .\\bin\\windows\\kafka-server-start.bat config\\syniq-server.properties")
        
        if not connect_ok:
            print("  ✗ Setup and start Kafka Connect:")
            print("    .\\setup_kafka_connect_native.ps1")
            print("    .\\start_kafka_connect.ps1")
        
        if not postgres_ok:
            print("  ✗ Configure PostgreSQL for CDC:")
            print("    python fix_debezium_permissions_local.py")
        
        print("\n📖 See NATIVE_KAFKA_CDC_GUIDE.md for detailed instructions")
        return False

if __name__ == "__main__":
    print("="*80)
    print("              NATIVE KAFKA CDC SETUP TEST")
    print("="*80)
    
    kafka_ok = test_kafka_broker()
    connect_ok = test_kafka_connect()
    postgres_ok = test_postgresql()
    
    all_ok = test_summary(kafka_ok, connect_ok, postgres_ok)
    
    sys.exit(0 if all_ok else 1)
