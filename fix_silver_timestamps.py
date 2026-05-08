"""
Fix missing timestamp columns in silver_assets table
"""
import psycopg2
import sys

# Database connection
conn_params = {
    'host': 'localhost',
    'port': 5432,
    'database': 'syniqai_metadata',
    'user': 'postgres',  # Using superuser
    'password': 'postgres'  # Update if your password is different
}

print("\n" + "=" * 60)
print("   FIXING SILVER_ASSETS TABLE SCHEMA")
print("=" * 60 + "\n")

try:
    # Connect to database
    print("Connecting to PostgreSQL...")
    conn = psycopg2.connect(**conn_params)
    cursor = conn.cursor()
    print("✓ Connected!\n")
    
    # Add created_at column if missing
    print("Adding created_at column if missing...")
    cursor.execute("""
        ALTER TABLE silver_assets 
        ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW();
    """)
    print("✓ created_at column ready\n")
    
    # Add updated_at column if missing
    print("Adding updated_at column if missing...")
    cursor.execute("""
        ALTER TABLE silver_assets 
        ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();
    """)
    print("✓ updated_at column ready\n")
    
    # Update existing rows
    print("Updating existing rows with timestamps...")
    cursor.execute("""
        UPDATE silver_assets 
        SET created_at = COALESCE(processed_at, NOW()),
            updated_at = COALESCE(processed_at, NOW())
        WHERE created_at IS NULL OR updated_at IS NULL;
    """)
    rows_updated = cursor.rowcount
    print(f"✓ Updated {rows_updated} rows\n")
    
    # Create update trigger function
    print("Creating update trigger...")
    cursor.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ language 'plpgsql';
    """)
    
    # Drop and recreate trigger
    cursor.execute("""
        DROP TRIGGER IF EXISTS update_silver_assets_updated_at ON silver_assets;
    """)
    cursor.execute("""
        CREATE TRIGGER update_silver_assets_updated_at BEFORE UPDATE ON silver_assets
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    """)
    print("✓ Trigger created\n")
    
    # Verify columns exist
    print("Verifying columns...")
    cursor.execute("""
        SELECT column_name, data_type, column_default
        FROM information_schema.columns
        WHERE table_name = 'silver_assets' 
          AND column_name IN ('created_at', 'updated_at')
        ORDER BY column_name;
    """)
    columns = cursor.fetchall()
    for col in columns:
        print(f"  ✓ {col[0]}: {col[1]}")
    
    # Commit changes
    conn.commit()
    
    print("\n" + "=" * 60)
    print("   ✓✓✓ SCHEMA FIX COMPLETE!")
    print("=" * 60)
    print("\nThe silver_assets table now has:")
    print("  - created_at column")
    print("  - updated_at column")
    print("  - automatic updated_at trigger\n")
    print("Your GUI should work now. Refresh the page!\n")
    
except Exception as e:
    print(f"\n✗ Error: {e}", file=sys.stderr)
    sys.exit(1)
    
finally:
    if 'cursor' in locals():
        cursor.close()
    if 'conn' in locals():
        conn.close()
