import psycopg2

try:
    conn = psycopg2.connect(host='localhost', port=5432, user='postgres', password='password', dbname='postgres')
    conn.autocommit = True
    cur = conn.cursor()

    # Set WAL level to logical (requires PostgreSQL restart to take effect)
    cur.execute("ALTER SYSTEM SET wal_level = logical;")
    cur.execute("ALTER SYSTEM SET max_replication_slots = 10;")
    cur.execute("ALTER SYSTEM SET max_wal_senders = 10;")
    print("WAL settings updated in postgresql.auto.conf")
    print("These take effect after PostgreSQL restarts.")
    print("")

    # Check current value
    cur.execute("SHOW wal_level;")
    print(f"Current WAL level (before restart): {cur.fetchone()[0]}")

    # Show where config file is so user can restart
    cur.execute("SHOW config_file;")
    print(f"Config file: {cur.fetchone()[0]}")

    cur.execute("SHOW data_directory;")
    print(f"Data directory: {cur.fetchone()[0]}")

    conn.close()

except Exception as e:
    print(f"ERROR: {e}")
