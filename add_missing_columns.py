"""Add missing columns to silver_assets table"""
import psycopg2

conn = psycopg2.connect(
    host='localhost',
    port=5432,
    database='syniqai_metadata',
    user='postgres',
    password='postgres'
)

cursor = conn.cursor()

print("\n=== Adding Missing Columns to silver_assets ===\n")

# Add model_was_overridden
print("Adding model_was_overridden...")
cursor.execute("""
    ALTER TABLE silver_assets 
    ADD COLUMN IF NOT EXISTS model_was_overridden BOOLEAN DEFAULT FALSE;
""")

# Add business_domain
print("Adding business_domain...")
cursor.execute("""
    ALTER TABLE silver_assets 
    ADD COLUMN IF NOT EXISTS business_domain VARCHAR(100);
""")

# Add manual_ingestion  
print("Adding manual_ingestion...")
cursor.execute("""
    ALTER TABLE silver_assets 
    ADD COLUMN IF NOT EXISTS manual_ingestion BOOLEAN DEFAULT FALSE;
""")

conn.commit()

print("\n✓ All columns added!")
print("\nVerifying columns...")
cursor.execute("""
    SELECT column_name FROM information_schema.columns
    WHERE table_name = 'silver_assets'
      AND column_name IN ('model_was_overridden', 'business_domain', 'manual_ingestion');
""")

for row in cursor.fetchall():
    print(f"  ✓ {row[0]}")

cursor.close()
conn.close()

print("\n✓✓✓ Schema update complete!\n")
