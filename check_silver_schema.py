"""Check silver_assets table schema"""
import psycopg2

conn = psycopg2.connect(
    host='localhost',
    port=5432,
    database='syniqai_metadata',
    user='postgres',
    password='postgres'
)

cursor = conn.cursor()

print("\n=== Current silver_assets Columns ===\n")
cursor.execute("""
    SELECT column_name, data_type, is_nullable
    FROM information_schema.columns
    WHERE table_name = 'silver_assets'
    ORDER BY ordinal_position;
""")

for row in cursor.fetchall():
    print(f"  {row[0]:30s} {row[1]:30s} {'NULL' if row[2] == 'YES' else 'NOT NULL'}")

cursor.close()
conn.close()
