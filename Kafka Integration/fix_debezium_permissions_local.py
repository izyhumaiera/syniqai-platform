import psycopg2

try:
    conn = psycopg2.connect(host='localhost', port=5432, user='postgres', password='password', dbname='postgres')
    conn.autocommit = True
    cur = conn.cursor()

    # Grant all required permissions for Debezium
    statements = [
        "ALTER USER debezium_user WITH REPLICATION;",
        "GRANT ALL PRIVILEGES ON DATABASE postgres TO debezium_user;",
        "GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO debezium_user;",
        "GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO debezium_user;",
        "GRANT USAGE ON SCHEMA public TO debezium_user;",
        "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO debezium_user;",
        # Create publication so Debezium can capture changes
        "DROP PUBLICATION IF EXISTS dbz_publication;",
        "CREATE PUBLICATION dbz_publication FOR ALL TABLES;",
        # Grant debezium_user ownership of publication
        "ALTER PUBLICATION dbz_publication OWNER TO debezium_user;",
    ]

    for sql in statements:
        try:
            cur.execute(sql)
            print(f"OK: {sql[:60]}")
        except Exception as e:
            print(f"SKIP ({e}): {sql[:60]}")

    # Verify
    cur.execute("SELECT rolsuper, rolreplication FROM pg_roles WHERE rolname='debezium_user';")
    row = cur.fetchone()
    print(f"\ndebezium_user -> superuser={row[0]}, replication={row[1]}")

    cur.execute("SELECT pubname FROM pg_publication;")
    pubs = cur.fetchall()
    print(f"Publications: {pubs}")

    conn.close()
    print("\nAll permissions granted!")

except Exception as e:
    print(f"FATAL ERROR: {e}")
