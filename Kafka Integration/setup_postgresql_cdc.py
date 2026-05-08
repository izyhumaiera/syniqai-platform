"""
Complete PostgreSQL CDC Setup for Debezium
Configures PostgreSQL for Change Data Capture
"""

import psycopg2
import sys

def configure_postgresql_for_cdc():
    """
    Configure PostgreSQL for Debezium CDC:
    1. Enable WAL (Write-Ahead Logging) at logical level
    2. Create debezium_user with replication privileges
    3. Create publication for CDC
    """
    
    print("=" * 70)
    print(" PostgreSQL CDC Configuration for Debezium")
    print("=" * 70)
    print()
    
    try:
        # Connect as postgres superuser
        print("[1/5] Connecting to PostgreSQL...")
        conn = psycopg2.connect(
            host='localhost',
            port=5432,
            user='postgres',
            password='password',
            dbname='postgres'
        )
        conn.autocommit = True
        cur = conn.cursor()
        print("✅ Connected successfully")
        print()
        
        # Check current WAL level
        print("[2/5] Checking WAL configuration...")
        cur.execute("SHOW wal_level;")
        wal_level = cur.fetchone()[0]
        print(f"   Current wal_level: {wal_level}")
        
        if wal_level != 'logical':
            print("   ⚠️  WAL level is not 'logical' - setting it now...")
            cur.execute("ALTER SYSTEM SET wal_level = 'logical';")
            cur.execute("ALTER SYSTEM SET max_replication_slots = 10;")
            cur.execute("ALTER SYSTEM SET max_wal_senders = 10;")
            print("   ✅ WAL configuration updated")
            print("   ⚠️  IMPORTANT: You must RESTART PostgreSQL service for this to take effect!")
            print("   Run: Restart-Service postgresql-x64-* (in PowerShell as Admin)")
            print()
        else:
            print("   ✅ WAL level is already 'logical'")
            print()
        
        # Create debezium_user if not exists
        print("[3/5] Creating debezium_user...")
        try:
            cur.execute("""
                SELECT 1 FROM pg_roles WHERE rolname='debezium_user';
            """)
            if cur.fetchone():
                print("   ℹ️  User 'debezium_user' already exists")
            else:
                cur.execute("""
                    CREATE USER debezium_user WITH PASSWORD 'debezium_password' REPLICATION LOGIN;
                """)
                print("   ✅ Created user 'debezium_user'")
        except Exception as e:
            print(f"   ⚠️  {e}")
        print()
        
        # Grant permissions
        print("[4/5] Granting permissions...")
        permissions = [
            ("REPLICATION", "ALTER USER debezium_user WITH REPLICATION;"),
            ("CONNECT", "GRANT CONNECT ON DATABASE postgres TO debezium_user;"),
            ("SELECT", "GRANT SELECT ON ALL TABLES IN SCHEMA public TO debezium_user;"),
            ("USAGE", "GRANT USAGE ON SCHEMA public TO debezium_user;"),
            ("DEFAULT", "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO debezium_user;"),
        ]
        
        for desc, sql in permissions:
            try:
                cur.execute(sql)
                print(f"   ✅ {desc}")
            except Exception as e:
                print(f"   ⚠️  {desc}: {e}")
        print()
        
        # Create publication
        print("[5/5] Creating CDC publication...")
        try:
            cur.execute("DROP PUBLICATION IF EXISTS dbz_syniq_publication;")
            cur.execute("CREATE PUBLICATION dbz_syniq_publication FOR ALL TABLES;")
            print("   ✅ Created publication 'dbz_syniq_publication'")
        except Exception as e:
            print(f"   ⚠️  {e}")
        print()
        
        # Verify configuration
        print("=" * 70)
        print(" Configuration Summary")
        print("=" * 70)
        print()
        
        # Check debezium_user privileges
        cur.execute("""
            SELECT rolsuper, rolreplication, rolcanlogin 
            FROM pg_roles WHERE rolname='debezium_user';
        """)
        row = cur.fetchone()
        if row:
            print(f"debezium_user:")
            print(f"  • Replication: {'✅' if row[1] else '❌'}")
            print(f"  • Can Login: {'✅' if row[2] else '❌'}")
        print()
        
        # Check publications
        cur.execute("SELECT pubname FROM pg_publication;")
        pubs = [row[0] for row in cur.fetchall()]
        print(f"Publications: {', '.join(pubs) if pubs else 'None'}")
        print()
        
        # Check tables that will be captured
        cur.execute("""
            SELECT schemaname, tablename 
            FROM pg_tables 
            WHERE schemaname = 'public'
            ORDER BY tablename;
        """)
        tables = cur.fetchall()
        print(f"Tables to capture ({len(tables)}):")
        for schema, table in tables[:10]:  # Show first 10
            print(f"  • {schema}.{table}")
        if len(tables) > 10:
            print(f"  ... and {len(tables) - 10} more")
        print()
        
        conn.close()
        
        print("=" * 70)
        print("✅ PostgreSQL CDC Configuration Complete!")
        print("=" * 70)
        print()
        
        if wal_level != 'logical':
            print("⚠️  NEXT STEP: Restart PostgreSQL service")
            print("   Run in PowerShell (as Admin):")
            print("   Get-Service postgresql-* | Restart-Service")
            print()
        else:
            print("✅ Ready to start Kafka Connect")
            print()
        
        return True
        
    except psycopg2.OperationalError as e:
        print(f"❌ Connection failed: {e}")
        print()
        print("Troubleshooting:")
        print("  1. Is PostgreSQL running?")
        print("  2. Is the password correct? (default: 'password')")
        print("  3. Check connection: psql -U postgres -h localhost")
        print()
        return False
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = configure_postgresql_for_cdc()
    sys.exit(0 if success else 1)
