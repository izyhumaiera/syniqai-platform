import psycopg2

conn = psycopg2.connect('postgresql://syniqai_user:syniqai_password@localhost:5432/syniqai_metadata')
cur = conn.cursor()

cur.execute('SELECT COUNT(*) FROM silver_assets')
count = cur.fetchone()[0]
print(f'\nTotal rows in silver_assets: {count}')

cur.execute('''
    SELECT bronze_minio_key, file_type, extraction_status, ai_model_used, processed_at 
    FROM silver_assets 
    ORDER BY processed_at DESC 
    LIMIT 10
''')
rows = cur.fetchall()

if rows:
    print('\nRecent processed files:')
    for r in rows:
        print(f'  - {r[0]}')
        print(f'    Type: {r[1]} | Status: {r[2]} | Model: {r[3]} | Processed: {r[4]}')
else:
    print('\n❌ No files processed yet in silver_assets table!')
    print('   This is why Object Detection tab is empty.')

cur.close()
conn.close()
