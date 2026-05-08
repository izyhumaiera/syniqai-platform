"""
Database CDC Test & Status Check
Tests database CDC readiness and provides status
"""

import psycopg2
import socket
import sys
from kafka import KafkaAdminClient
from kafka.errors import NoBrokersAvailable

def check_service(host, port, name):
    """Check if a service is reachable"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except:
        return False

def main():
    print("=" * 70)
    print(" Database CDC Readiness Check")
    print("=" * 70)
    print()
    
    status = {
        "kafka": False,
        "kafka_connect": False,
        "postgresql": False,
        "connectors_installed": False,
        "db_configured": False
    }
    
    # 1. Check Kafka
    print("[1/5] Kafka Broker...")
    status["kafka"] = check_service('localhost', 9092, 'Kafka')
    if status["kafka"]:
        print("   ✅ Kafka broker is running on port 9092")
        try:
            admin = KafkaAdminClient(bootstrap_servers='localhost:9092', request_timeout_ms=5000)
            topics = admin.list_topics()
            print(f"   ℹ️  {len(topics)} topics exist")
            admin.close()
        except Exception as e:
            print(f"   ⚠️  Kafka accessible but: {e}")
    else:
        print("   ❌ Kafka broker not running")
    print()
    
    # 2. Check Kafka Connect
    print("[2/5] Kafka Connect...")
    status["kafka_connect"] = check_service('localhost', 8083, 'Kafka Connect')
    if status["kafka_connect"]:
        print("   ✅ Kafka Connect is running on port 8083")
        try:
            import requests
            resp = requests.get('http://localhost:8083/connector-plugins', timeout=5)
            if resp.status_code == 200:
                plugins = resp.json()
                print(f"   ℹ️  {len(plugins)} connector plugins loaded")
                for plugin in plugins:
                    if 'debezium' in plugin['class'].lower():
                        print(f"   • {plugin['class'].split('.')[-1]}")
        except:
            pass
    else:
        print("   ❌ Kafka Connect not running")
        print("   Start it: cd C:\\kafka\\kafka-4.2.0")
        print("             .\\bin\\windows\\connect-standalone.bat config\\connect-standalone-native.properties")
    print()
    
    # 3. Check PostgreSQL
    print("[3/5] PostgreSQL Database...")
    status["postgresql"] = check_service('localhost', 5432, 'PostgreSQL')
    if status["postgresql"]:
        print("   ✅ PostgreSQL is accessible on port 5432")
        try:
            conn = psycopg2.connect(
                host='localhost',
                port=5432,
                user='postgres',
                password='password',
                dbname='postgres'
            )
            cur = conn.cursor()
            cur.execute("SELECT version();")
            version = cur.fetchone()[0]
            print(f"   ℹ️  {version.split(',')[0]}")
            conn.close()
        except Exception as e:
            print(f"   ⚠️  Connection: {e}")
    else:
        print("   ❌ PostgreSQL not running")
    print()
    
    # 4. Check Debezium Connectors Installation
    print("[4/5] Debezium Connectors...")
    import os
    plugin_dir = "C:\\kafka\\kafka-4.2.0\\plugins"
    pg_connector = os.path.join(plugin_dir, "debezium-connector-postgresql")
    mysql_connector = os.path.join(plugin_dir, "debezium-connector-mysql")
    
    pg_exists = os.path.exists(pg_connector)
    mysql_exists = os.path.exists(mysql_connector)
    status["connectors_installed"] = pg_exists or mysql_exists
    
    if pg_exists:
        print(f"   ✅ PostgreSQL connector: {pg_connector}")
    else:
        print(f"   ❌ PostgreSQL connector not found")
    
    if mysql_exists:
        print(f"   ✅ MySQL connector: {mysql_connector}")
    else:
        print(f"   ❌ MySQL connector not found")
    print()
    
    # 5. Check PostgreSQL CDC Configuration
    print("[5/5] PostgreSQL CDC Configuration...")
    if status["postgresql"]:
        try:
            conn = psycopg2.connect(
                host='localhost',
                port=5432,
                user='postgres',
                password='password',
                dbname='postgres'
            )
            cur = conn.cursor()
            
            # Check WAL level
            cur.execute("SHOW wal_level;")
            wal_level = cur.fetchone()[0]
            
            # Check debezium_user
            cur.execute("SELECT rolreplication FROM pg_roles WHERE rolname='debezium_user';")
            user_row = cur.fetchone()
            
            # Check publications
            cur.execute("SELECT count(*) FROM pg_publication;")
            pub_count = cur.fetchone()[0]
            
            if wal_level == 'logical' and user_row and user_row[0] and pub_count > 0:
                status["db_configured"] = True
                print(f"   ✅ WAL level: {wal_level}")
                print(f"   ✅ debezium_user: exists with replication")
                print(f"   ✅ Publications: {pub_count} configured")
            else:
                print(f"   ⚠️  WAL level: {wal_level} (needs 'logical')")
                if not user_row or not user_row[0]:
                    print(f"   ⚠️  debezium_user: not configured correctly")
                if pub_count == 0:
                    print(f"   ⚠️  Publications: none found")
                print("   Run: python setup_postgresql_cdc.py")
            
            conn.close()
        except Exception as e:
            print(f"   ❌ Could not check: {e}")
    else:
        print("   ⏭️  Skipped (PostgreSQL not running)")
    print()
    
    # Summary
    print("=" * 70)
    print(" Status Summary")
    print("=" * 70)
    print()
    
    ready_count = sum(status.values())
    total_count = len(status)
    
    print(f"Ready: {ready_count}/{total_count} components")
    print()
    
    if ready_count == total_count:
        print("✅ ALL SYSTEMS READY FOR DATABASE CDC!")
        print()
        print("Next steps:")
        print("  1. Create a test table: psql -U postgres")
        print("     CREATE TABLE test_cdc (id SERIAL PRIMARY KEY, data TEXT);")
        print("  2. Create Debezium connector: python create_debezium_connector.py")
        print("  3. Insert test data and watch CDC events in Kafka")
    else:
        print("⚠️  Some components need attention:")
        print()
        if not status["kafka"]:
            print("  [ ] Start Kafka broker")
        if not status["kafka_connect"]:
            print("  [ ] Start Kafka Connect (see Kafka Connect window for errors)")
        if not status["postgresql"]:
            print("  [ ] Start PostgreSQL")
        if not status["connectors_installed"]:
            print("  [ ] Install Debezium connectors (already done)")
        if not status["db_configured"]:
            print("  [ ] Configure PostgreSQL: python setup_postgresql_cdc.py")
    print()
    
    return ready_count == total_count

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
