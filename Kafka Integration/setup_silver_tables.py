"""
Setup Silver Layer Tables for Unstructured Data Processing
"""

import psycopg2

print("=" * 60)
print(" Setting Up Silver Layer Tables")
print("=" * 60)
print()

try:
    # Connect to PostgreSQL
    print("Connecting to PostgreSQL...")
    conn = psycopg2.connect(
        host='localhost',
        port=5432,
        user='postgres',
        password='password',
        dbname='postgres'
    )
    conn.autocommit = True
    cur = conn.cursor()
    print("✅ Connected")
    print()
    
    # Create unstructured_document_metadata table
    print("Creating unstructured_document_metadata table...")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS unstructured_document_metadata (
            id SERIAL PRIMARY KEY,
            file_id VARCHAR(255) UNIQUE,
            file_name TEXT,
            file_path TEXT,
            file_size BIGINT,
            mime_type VARCHAR(100),
            source_system VARCHAR(50),
            processing_status VARCHAR(20),
            model_used VARCHAR(100),
            extracted_text TEXT,
            extracted_text_length INT,
            metadata JSONB,
            entities JSONB,
            sentiment JSONB,
            topics JSONB,
            processed_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        );
    """)
    print("✅ Table created")
    
    # Create indexes
    print("Creating indexes...")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_file_id ON unstructured_document_metadata(file_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_processing_status ON unstructured_document_metadata(processing_status);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_processed_at ON unstructured_document_metadata(processed_at);")
    print("✅ Indexes created")
    print()
    
    # Verify
    cur.execute("SELECT COUNT(*) FROM unstructured_document_metadata;")
    count = cur.fetchone()[0]
    print(f"✅ Table verified: {count} records")
    print()
    
    conn.close()
    
    print("=" * 60)
    print("✅ Silver Layer Database Setup Complete!")
    print("=" * 60)
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
