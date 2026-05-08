#!/usr/bin/env python3
"""Quick script to preview CDC data in Silver bucket"""

import requests
import json
import pandas as pd

# Preview the data
response = requests.get('http://localhost:8000/api/silver/cdc-preview/postgres/hosp_raya_patient_record?limit=5')
result = response.json()

if result.get('success'):
    print(f"\n{'='*80}")
    print(f"  CDC DATA IN SILVER BUCKET - postgres.hosp_raya_patient_record")
    print(f"{'='*80}\n")
    print(f"Total Rows: {result.get('total_rows', 0)}")
    print(f"Columns: {len(result.get('columns', []))}")
    print(f"Preview: {result.get('preview_rows', 0)} rows\n")
    
    if result.get('data'):
        df = pd.DataFrame(result['data'])
        
        # Show basic columns
        basic_cols = ['record_id', 'user_id', 'medical_info', '_ingested_at', '_source_topic', '_dq_score']
        display_cols = [col for col in basic_cols if col in df.columns]
        
        print(f"Columns: {', '.join(df.columns.tolist())}\n")
        print("Sample Data:")
        print(df[display_cols].head(3).to_string(index=False))
        
        print(f"\n{'='*80}")
        print(f"✅ CDC to Silver pipeline is working!")
        print(f"Data is being captured from database changes and stored in MinIO.")
        print(f"{'='*80}\n")
    else:
        print("No data in preview")
else:
    print(f"Error: {result}")
