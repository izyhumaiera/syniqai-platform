"""
Quick viewer for PostgreSQL tables in syniqai_metadata database
Run: python view_postgres_data.py
"""
import psycopg2
from psycopg2.extras import RealDictCursor

def view_table(table_name, limit=10):
    """View data from a specific table"""
    conn = psycopg2.connect(
        host='localhost',
        port=5432,
        database='syniqai_metadata',
        user='syniqai_user',
        password='syniqai_password'
    )
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # Get table structure
    cur.execute(f"""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = '{table_name}' 
        ORDER BY ordinal_position
    """)
    columns = cur.fetchall()
    
    print(f"\n{'='*80}")
    print(f"TABLE: {table_name}")
    print(f"{'='*80}")
    print("\nCOLUMNS:")
    for col in columns:
        print(f"  • {col['column_name']} ({col['data_type']})")
    
    # Get row count
    cur.execute(f"SELECT COUNT(*) as count FROM {table_name}")
    count = cur.fetchone()['count']
    print(f"\nTOTAL ROWS: {count}")
    
    # Show sample data
    if count > 0:
        cur.execute(f"SELECT * FROM {table_name} LIMIT {limit}")
        rows = cur.fetchall()
        print(f"\nSAMPLE DATA (first {min(limit, count)} rows):")
        for i, row in enumerate(rows, 1):
            print(f"\n  Row {i}:")
            for key, value in row.items():
                # Truncate long values
                str_val = str(value)
                if len(str_val) > 100:
                    str_val = str_val[:100] + "..."
                print(f"    {key}: {str_val}")
    else:
        print("\n  (No data in table yet)")
    
    cur.close()
    conn.close()

if __name__ == "__main__":
    tables = [
        'bronze_assets',
        'routing_config', 
        'pipeline_jobs',
        'data_lineage',
        'data_quality_metrics',
        'gold_lineage',
        'silver_assets',
        'silver_quality_flags'
    ]
    
    print("\n" + "="*80)
    print("SYNIQAI POSTGRESQL DATABASE VIEWER")
    print("Database: syniqai_metadata")
    print("="*80)
    
    for table in tables:
        try:
            view_table(table, limit=3)
        except Exception as e:
            print(f"\n✗ Error viewing {table}: {e}")
    
    # View materialized view
    print(f"\n{'='*80}")
    print("MATERIALIZED VIEW: gold_assets")
    print(f"{'='*80}")
    try:
        conn = psycopg2.connect(
            host='localhost',
            port=5432,
            database='syniqai_metadata',
            user='syniqai_user',
            password='syniqai_password'
        )
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT COUNT(*) as count FROM gold_assets")
        count = cur.fetchone()['count']
        print(f"TOTAL ROWS: {count}")
        
        if count > 0:
            cur.execute("SELECT * FROM gold_assets LIMIT 3")
            rows = cur.fetchall()
            print(f"\nSAMPLE DATA (first 3 rows):")
            for i, row in enumerate(rows, 1):
                print(f"\n  Row {i}:")
                for key, value in row.items():
                    str_val = str(value)
                    if len(str_val) > 100:
                        str_val = str_val[:100] + "..."
                    print(f"    {key}: {str_val}")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"✗ Error: {e}")
    
    print("\n" + "="*80)
    print("✓ Database exploration complete")
    print("="*80)
