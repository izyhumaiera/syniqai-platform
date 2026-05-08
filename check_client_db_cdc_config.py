"""
Check if client database is configured for CDC (Change Data Capture)
"""
import psycopg2
import sys

# Client database connection
DB_CONFIG = {
    'host': '192.168.2.114',
    'port': 5432,
    'database': 'postgres',
    'user': 'postgres',
    'password': 'password'
}

def check_cdc_config():
    print("\n" + "="*70)
    print("  CHECKING CLIENT DATABASE CDC CONFIGURATION")
    print("="*70 + "\n")
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Check 1: WAL Level
        print("1. Checking WAL Level (must be 'logical')...")
        cursor.execute("SHOW wal_level;")
        wal_level = cursor.fetchone()[0]
        if wal_level == 'logical':
            print(f"   ✓ WAL Level: {wal_level} - CORRECT")
        else:
            print(f"   ✗ WAL Level: {wal_level} - WRONG! Must be 'logical'")
            print("     Fix: Edit postgresql.conf and set: wal_level = logical")
            print("     Then restart PostgreSQL\n")
        
        # Check 2: Max Replication Slots
        print("\n2. Checking Max Replication Slots...")
        cursor.execute("SHOW max_replication_slots;")
        max_slots = cursor.fetchone()[0]
        if int(max_slots) >= 1:
            print(f"   ✓ Max Replication Slots: {max_slots} - OK")
        else:
            print(f"   ✗ Max Replication Slots: {max_slots} - Must be at least 1")
        
        # Check 3: Max WAL Senders
        print("\n3. Checking Max WAL Senders...")
        cursor.execute("SHOW max_wal_senders;")
        max_senders = cursor.fetchone()[0]
        if int(max_senders) >= 1:
            print(f"   ✓ Max WAL Senders: {max_senders} - OK")
        else:
            print(f"   ✗ Max WAL Senders: {max_senders} - Must be at least 1")
        
        # Check 4: User Replication Permission
        print("\n4. Checking User Replication Permission...")
        cursor.execute("""
            SELECT rolname, rolreplication 
            FROM pg_roles 
            WHERE rolname = %s;
        """, (DB_CONFIG['user'],))
        result = cursor.fetchone()
        if result and result[1]:
            print(f"   ✓ User '{DB_CONFIG['user']}' has REPLICATION permission")
        else:
            print(f"   ✗ User '{DB_CONFIG['user']}' DOES NOT have REPLICATION permission")
            print(f"     Fix: ALTER USER {DB_CONFIG['user']} WITH REPLICATION;\n")
        
        # Check 5: Table Exists
        print("\n5. Checking if table exists...")
        cursor.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'hosp_raya_patient_record'
            );
        """)
        table_exists = cursor.fetchone()[0]
        if table_exists:
            cursor.execute("SELECT COUNT(*) FROM hosp_raya_patient_record;")
            count = cursor.fetchone()[0]
            print(f"   ✓ Table 'hosp_raya_patient_record' exists with {count} rows")
        else:
            print(f"   ✗ Table 'hosp_raya_patient_record' DOES NOT exist")
        
        # Check 6: Publication
        print("\n6. Checking Debezium Publication...")
        cursor.execute("""
            SELECT pubname FROM pg_publication 
            WHERE pubname = 'dbz_publication';
        """)
        pub = cursor.fetchone()
        if pub:
            print(f"   ✓ Publication 'dbz_publication' exists")
        else:
            print(f"   ⚠ Publication 'dbz_publication' not found (Debezium will create it)")
        
        # Check 7: Replication Slot
        print("\n7. Checking Replication Slot...")
        cursor.execute("""
            SELECT slot_name, plugin, active 
            FROM pg_replication_slots 
            WHERE slot_name = 'debezium_client_slot';
        """)
        slot = cursor.fetchone()
        if slot:
            print(f"   ✓ Replication Slot 'debezium_client_slot' exists")
            print(f"     Plugin: {slot[1]}, Active: {slot[2]}")
        else:
            print(f"   ⚠ Replication Slot 'debezium_client_slot' not found (Debezium will create it)")
        
        cursor.close()
        conn.close()
        
        print("\n" + "="*70)
        print("  DIAGNOSIS COMPLETE")
        print("="*70)
        
        if wal_level != 'logical':
            print("\n[CRITICAL] Database is NOT configured for CDC!")
            print("You must set wal_level=logical in postgresql.conf and restart PostgreSQL")
            return False
        
        return True
        
    except Exception as e:
        print(f"\n✗ ERROR: Could not connect to database")
        print(f"  {str(e)}")
        print(f"\nConnection details:")
        print(f"  Host: {DB_CONFIG['host']}")
        print(f"  Port: {DB_CONFIG['port']}")
        print(f"  Database: {DB_CONFIG['database']}")
        print(f"  User: {DB_CONFIG['user']}")
        return False

if __name__ == "__main__":
    success = check_cdc_config()
    sys.exit(0 if success else 1)
