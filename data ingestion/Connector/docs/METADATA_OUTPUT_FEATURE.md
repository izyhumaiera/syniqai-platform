# MariaDB Cloud: Metadata + Data Output Feature

## 🎯 What Was Added

Enhanced MariaDB Cloud connector to **automatically save both metadata and data** during extraction.

---

## ✨ New Method: `extract_with_metadata()`

### **Location**
`mariadbcloud_conn.py` → `MariaDBCloudConnector` class

### **Purpose**
Single method that extracts data and saves:
1. **data.parquet** - Actual extracted data (Parquet format, Snappy compression)
2. **metadata.json** - Comprehensive extraction metadata

### **Signature**
```python
def extract_with_metadata(
    self, 
    extraction_request: Dict[str, Any], 
    output_dir: str = "bronze_layer"
) -> Dict[str, Any]:
```

### **Returns**
```python
{
    "success": True/False,
    "table": "table_name",
    "row_count": 1234,
    "data_file": "path/to/data.parquet",
    "metadata_file": "path/to/metadata.json",
    "file_size_kb": 123.45,
    "extraction_time_seconds": 12.34,
    "error": None  # or error message if failed
}
```

---

## 📁 Output Structure

### **Directory Layout**
```
bronze_layer/                          # Base directory
└── user_credit_card_transaction/      # Table name
    └── 20260213_155030/                # Timestamp (YYYYMMDD_HHMMSS)
        ├── data.parquet                # Extracted data
        └── metadata.json               # Extraction info
```

### **For Multi-Tenant**
```
bronze_data_multi_tenant/
├── analyst_readonly/                   # Tenant 1
│   └── user_credit_card_transaction/
│       └── 20260213_155030/
│           ├── data.parquet
│           └── metadata.json
├── manager_readonly/                   # Tenant 2
│   └── user_credit_card_transaction/
│       └── 20260213_160045/
│           ├── data.parquet
│           └── metadata.json
└── report_readonly/                    # Tenant 3
    └── user_credit_card_transaction/
        └── 20260213_160130/
            ├── data.parquet
            └── metadata.json
```

---

## 📋 Metadata Contents

### **metadata.json Structure**
```json
{
  "source": {
    "type": "mariadb_cloud",
    "host": "serverless-us-west-2.sysp0000.db1.skysql.com",
    "database": "idp_ingestion_db",
    "user": "analyst_readonly",
    "ssl_enabled": true
  },
  "extraction": {
    "timestamp": "2026-02-13T15:50:30.123456",
    "table": "user_credit_card_transaction",
    "mode": "full",
    "row_count": 1234,
    "column_count": 8,
    "columns": ["id", "user_id", "card_number", "amount", "transaction_date", "merchant", "status", "created_at"],
    "batch_count": 3,
    "extraction_time_seconds": 2.45
  },
  "output": {
    "data_file": "bronze_layer/user_credit_card_transaction/20260213_155030/data.parquet",
    "file_format": "parquet",
    "compression": "snappy",
    "file_size_kb": 145.32,
    "file_size_mb": 0.14
  },
  "schema": {
    "id": "int64",
    "user_id": "int64",
    "card_number": "object",
    "amount": "float64",
    "transaction_date": "datetime64[ns]",
    "merchant": "object",
    "status": "object",
    "created_at": "datetime64[ns]"
  },
  "statistics": {
    "rows_per_second": 503.67,
    "mb_per_second": 0.06
  }
}
```

---

## 🚀 Usage Examples

### **1. Standalone Script**
```python
from mariadbcloud_conn import MariaDBCloudConnector

config = {
    "host": "serverless-us-west-2.sysp0000.db1.skysql.com",
    "port": 4020,
    "database": "idp_ingestion_db",
    "user": "analyst_readonly",
    "password": "your_password",
    "ssl_ca": r"C:\path\to\globalsignrootca.pem"
}

connector = MariaDBCloudConnector(config)
connector.connect()

# Extract with metadata
result = connector.extract_with_metadata(
    extraction_request={
        "entity": "user_credit_card_transaction",
        "mode": "full",
        "enable_parallel": False,
        "flatten_json": {}
    },
    output_dir="bronze_layer"
)

if result["success"]:
    print(f"✅ Extracted {result['row_count']:,} rows")
    print(f"📁 Data: {result['data_file']}")
    print(f"📋 Metadata: {result['metadata_file']}")
else:
    print(f"❌ Failed: {result['error']}")

connector.close()
```

### **2. GUI (CustomTkinter)**
The GUI **automatically uses** `extract_with_metadata()` when:
- Connected to MariaDB Cloud (SkySQL)
- Click **"Start Extraction"** in Extraction tab
- Click **"Extract All Tenants"** in Cloud Multi-Tenant tab

**Features:**
- ✅ Real-time logs during extraction
- ✅ Progress updates in console
- ✅ Summary dialog at end with file paths
- ✅ Statistics updated (rows, time, speed)

### **3. Multi-Tenant Ingestion**
```python
# multi_tenant_ingestion.py already uses this pattern!
# Each tenant gets their own folder with metadata + data
```

---

## 🎨 GUI Integration

### **Extraction Tab**
When extracting from MariaDB Cloud:
1. Click **"Start Extraction"**
2. GUI detects MariaDB Cloud connector
3. Uses `extract_with_metadata()` automatically
4. Shows real-time logs
5. Displays summary dialog:
   ```
   ✅ Successfully extracted 1,234 rows
   
   ⏱️ Time: 2.45s
   📁 Data: data.parquet
   📋 Metadata: metadata.json
   📊 Size: 145.32 KB
   
   Check logs for file paths.
   ```

### **Cloud Multi-Tenant Tab**
When extracting all tenants:
1. Load credentials JSON
2. Click **"Extract All Tenants"**
3. Each tenant processed in sequence
4. Shows detailed summary:
   ```
   Results:
   • Successful: 3/3 tenants
   • Total Rows: 3,702
   
   ✅ analyst_readonly: 1,234 rows
   ✅ manager_readonly: 1,234 rows
   ✅ report_readonly: 1,234 rows
   
   📁 Output: bronze_data_multi_tenant/
      Each tenant has:
      • data.parquet (extracted data)
      • metadata.json (extraction info)
   ```

---

## 📊 Comparison: Before vs After

### **Before (Old Way)**
```python
# Only yielded data batches, no metadata saved
for batch_df in connector.extract(request):
    # Manual handling required
    # No automatic metadata
    pass
```

### **After (New Way)**
```python
# Saves data + metadata automatically
result = connector.extract_with_metadata(request, output_dir)

# Everything saved automatically:
# ✅ data.parquet
# ✅ metadata.json
# ✅ Organized directory structure
# ✅ Performance metrics
# ✅ Schema info
```

---

## ✅ Benefits

1. **Automatic Organization**
   - Timestamped folders prevent overwrites
   - Clear directory structure
   - Easy to track extractions

2. **Rich Metadata**
   - Source information (where data came from)
   - Schema info (column names and types)
   - Performance metrics (speed, size)
   - Extraction timestamp

3. **Audit Trail**
   - Who extracted (username in metadata)
   - When extracted (timestamp)
   - What extracted (table name, row count)
   - How long it took (extraction_time_seconds)

4. **Easy Data Governance**
   - Track all extractions
   - Verify data lineage
   - Monitor extraction performance
   - Identify slow tables

5. **Multi-Tenant Ready**
   - Each tenant gets separate folder
   - No data mixing
   - Clear ownership
   - Independent metadata

---

## 🔍 Example Use Cases

### **Use Case 1: Single Table Extraction**
```python
result = connector.extract_with_metadata(
    {"entity": "customers", "mode": "full"},
    output_dir="bronze_layer"
)
# Output: bronze_layer/customers/20260213_155030/
```

### **Use Case 2: Incremental Load**
```python
result = connector.extract_with_metadata(
    {
        "entity": "transactions",
        "mode": "incremental",
        "watermark_column": "updated_at",
        "initial_watermark_value": "2026-02-01"
    },
    output_dir="bronze_layer"
)
# Metadata includes watermark info
```

### **Use Case 3: Multi-Tenant**
```python
for tenant in tenants:
    connector = MariaDBCloudConnector(tenant['config'])
    connector.connect()
    
    result = connector.extract_with_metadata(
        {"entity": "orders", "mode": "full"},
        output_dir=f"bronze_data_multi_tenant/{tenant['name']}"
    )
    
    connector.close()
# Each tenant: separate folder + metadata
```

---

## 📝 Files Modified

| File | Changes |
|------|---------|
| `mariadbcloud_conn.py` | ✅ Added `extract_with_metadata()` method |
| `gui_ctk.py` | ✅ Updated `_run_extraction()` to use new method |
| `gui_ctk.py` | ✅ Updated `_extract_all_tenants()` for metadata |
| `example_cloud_extract_with_metadata.py` | ✅ Created usage example |
| `METADATA_OUTPUT_FEATURE.md` | ✅ This documentation |

---

## 🧪 Testing

### **Test 1: Single Extraction**
```powershell
# Run example script
python example_cloud_extract_with_metadata.py

# Expected output:
# ✅ data.parquet created
# ✅ metadata.json created
# ✅ Proper directory structure
```

### **Test 2: GUI Extraction**
```powershell
# Run GUI
python gui_ctk.py

# Steps:
# 1. Connection tab → Connect to MariaDB Cloud
# 2. Extraction tab → Enter table name
# 3. Click "Start Extraction"
# 4. Check bronze_layer/ folder for output
```

### **Test 3: Multi-Tenant**
```powershell
# Run GUI
python gui_ctk.py

# Steps:
# 1. Cloud Multi-Tenant tab → Load credentials
# 2. Extraction tab → Enter table name
# 3. Cloud tab → "Extract All Tenants"
# 4. Check bronze_data_multi_tenant/ folders
```

---

## 💡 Pro Tips

1. **Check Metadata First**
   - Before processing data, read metadata.json
   - Verify row counts, timestamps, schema

2. **Use Timestamps**
   - Folder names are timestamped
   - Easy to identify latest extraction
   - Safe from overwrites

3. **Monitor Performance**
   - Check `statistics.rows_per_second`
   - Identify slow extractions
   - Optimize chunking if needed

4. **Schema Validation**
   - Use `schema` field to verify data types
   - Detect schema changes over time
   - Validate before processing

5. **Audit Trail**
   - Keep all metadata files
   - Track extraction history
   - Prove compliance

---

## 🎉 Summary

**New Feature:** `extract_with_metadata()` in MariaDB Cloud connector

**What It Does:**
- ✅ Extracts data from MariaDB Cloud
- ✅ Saves data.parquet (compressed)
- ✅ Saves metadata.json (extraction info)
- ✅ Organizes in timestamped folders
- ✅ Provides performance metrics
- ✅ Includes schema information

**Where It's Used:**
- ✅ GUI: Automatic in Extraction tab
- ✅ GUI: Automatic in Cloud Multi-Tenant tab
- ✅ Scripts: Available as method call
- ✅ Multi-Tenant: Built into ingestion script

**Benefits:**
- 📁 Better organization
- 📋 Rich metadata
- 🔍 Easy auditing
- 📊 Performance tracking
- 👥 Multi-tenant ready

**You can now extract data with complete metadata tracking!** 🎉
