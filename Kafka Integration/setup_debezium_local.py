import psycopg2

try:
    conn = psycopg2.connect(host='localhost', port=5432, user='postgres', password='password', dbname='postgres')
    conn.autocommit = True
    cur = conn.cursor()

    # Create debezium user if not exists
    cur.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'debezium_user') THEN
                CREATE ROLE debezium_user WITH LOGIN PASSWORD 'debezium_password' REPLICATION;
            END IF;
        END $$;
    """)
    print("debezium_user created/verified")

    # Grant permissions
    cur.execute("GRANT SELECT ON ALL TABLES IN SCHEMA public TO debezium_user;")
    cur.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO debezium_user;")
    cur.execute("GRANT CONNECT ON DATABASE postgres TO debezium_user;")
    cur.execute("GRANT USAGE ON SCHEMA public TO debezium_user;")
    print("Permissions granted")

    # Check WAL level
    cur.execute("SHOW wal_level;")
    wal = cur.fetchone()[0]
    print(f"WAL level: {wal}")
    if wal != 'logical':
        print("WARNING: WAL level must be 'logical' for Debezium CDC")
        print("Run: ALTER SYSTEM SET wal_level = logical;  then restart PostgreSQL")
    else:
        print("WAL level is correct (logical)")

    # List existing tables
    cur.execute("SELECT tablename FROM pg_tables WHERE schemaname='public';")
    tables = [r[0] for r in cur.fetchall()]
    print(f"Tables in public schema: {tables}")

    # Create cdc_test table if not exists
    cur.execute("""
        CREATE TABLE IF NOT EXISTS cdc_test (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100),
            value TEXT,
            created_at TIMESTAMP DEFAULT NOW()
        );
    """)
    print("cdc_test table created/verified")

    conn.close()
    print("\nSetup complete!")

except Exception as e:
    print(f"ERROR: {e}")
    print("Try changing the password in this script to match your PostgreSQL password")
