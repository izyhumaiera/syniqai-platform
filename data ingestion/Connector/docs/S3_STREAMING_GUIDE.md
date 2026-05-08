# S3 File Streaming Ingestor

Stream files from AWS S3 to MinIO bronze layer with metadata tracking and quality profiling.

## ✨ Features

- ✅ **Direct Streaming**: AWS S3 → MinIO (no intermediate storage)
- ✅ **Multiple File Types**: CSV, JSON, Parquet, images, videos, documents
- ✅ **Preserve Structure**: Maintains S3 directory hierarchy
- ✅ **Smart Profiling**: Auto-profiles structured files (CSV/JSON/Parquet)
- ✅ **Selective Sync**: Filter by file extensions
- ✅ **Integrated**: Automatic catalog, quality profiling, lineage tracking

---

## 📦 Setup

### 1. Install Dependencies

```bash
pip install boto3
```

### 2. Get AWS Credentials

**Option A: AWS IAM User**
1. Go to AWS Console → IAM → Users
2. Create/select user
3. Security Credentials → Create Access Key
4. Copy Access Key ID and Secret Access Key

**Option B: AWS CLI**
```bash
aws configure
# Keys are stored in ~/.aws/credentials
```

### 3. Configure S3 Connection

Edit `s3_config.json`:

```json
{
  "source_name": "s3_prod",
  "s3_bucket": "your-bucket-name",
  "s3_prefix": "data/",
  "aws_access_key": "AKIAIOSFODNN7EXAMPLE",
  "aws_secret_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
  "aws_region": "us-east-1",
  "file_extensions": null,
  "profile_structured": true
}
```

---

## 🚀 Usage

### Stream All Files

```bash
python s3_file_ingestor.py s3_config.json --mode streaming
```

### Stream with Local Backup

```bash
python s3_file_ingestor.py s3_config.json --mode hybrid
```

---

## 🎯 Configuration Options

### File Type Filtering

**All files:**
```json
{
  "file_extensions": null
}
```

**CSV and JSON only:**
```json
{
  "file_extensions": [".csv", ".json", ".jsonl"]
}
```

**Images only:**
```json
{
  "file_extensions": [".jpg", ".jpeg", ".png", ".gif"]
}
```

**Videos only:**
```json
{
  "file_extensions": [".mp4", ".avi", ".mov", ".mkv"]
}
```

### S3 Prefix (Folder)

**Root of bucket:**
```json
{
  "s3_prefix": ""
}
```

**Specific folder:**
```json
{
  "s3_prefix": "data/uploads/2024/"
}
```

### Structured File Profiling

**Enable (default):**
```json
{
  "profile_structured": true
}
```

This will analyze CSV/JSON/Parquet files and extract:
- Row count
- Column count
- Column names
- Data types

**Disable (for binary files):**
```json
{
  "profile_structured": false
}
```

---

## 📊 Supported File Types

| Category | Extensions | Profiling |
|----------|-----------|-----------|
| **Structured** | .csv, .json, .jsonl, .parquet | ✅ Yes |
| **Text** | .txt, .log | ❌ No |
| **Images** | .jpg, .png, .gif, .bmp | ❌ No |
| **Videos** | .mp4, .avi, .mov, .mkv | ❌ No |
| **Documents** | .pdf, .doc, .docx, .xls, .xlsx | ❌ No |
| **Binary** | All others | ❌ No |

---

## 📈 What Gets Created

After ingestion:

### 1. **Bronze Layer** (MinIO)
```
bronze/
  s3_prod/
    files/
      year=2026/
        month=02/
          day=19/
            data/
              uploads/
                file1.csv
                file2.json
                images/
                  photo1.jpg
                  photo2.png
```

Files are stored with their original directory structure preserved.

### 2. **Catalog Entry**
- Source: S3 bucket name and prefix
- File count, total bytes
- File type breakdown
- Partition keys

### 3. **Quality Profile** (Structured Files Only)
- Row/column counts
- Data types
- Sample data

### 4. **Lineage Record**
- Source: s3://bucket/prefix
- Target: MinIO location
- File types, counts, sizes

---

## 🧪 Testing

### Test with Small Dataset

1. **Create test bucket** or use existing
2. **Upload test files**:
   ```bash
   aws s3 cp test.csv s3://my-bucket/test/
   aws s3 cp data.json s3://my-bucket/test/
   ```

3. **Update s3_config.json**:
   ```json
   {
     "s3_bucket": "my-bucket",
     "s3_prefix": "test/",
     "file_extensions": [".csv", ".json"]
   }
   ```

4. **Run ingestor**:
   ```bash
   python s3_file_ingestor.py s3_config.json --mode streaming
   ```

### Test S3 Connection

```bash
# List bucket contents
aws s3 ls s3://your-bucket/

# List specific prefix
aws s3 ls s3://your-bucket/data/ --recursive
```

---

## 📊 Use Cases

### Use Case 1: Analytics Data Export

**Scenario:** Daily CSV exports from analytics platform stored in S3

```json
{
  "s3_bucket": "analytics-exports",
  "s3_prefix": "daily/2024-02/",
  "file_extensions": [".csv"],
  "profile_structured": true
}
```

### Use Case 2: User-Uploaded Media

**Scenario:** Images and videos from mobile app

```json
{
  "s3_bucket": "user-content",
  "s3_prefix": "uploads/",
  "file_extensions": [".jpg", ".png", ".mp4"],
  "profile_structured": false
}
```

### Use Case 3: JSON Event Logs

**Scenario:** Application logs in JSON format

```json
{
  "s3_bucket": "app-logs",
  "s3_prefix": "events/2024/",
  "file_extensions": [".json", ".jsonl"],
  "profile_structured": true
}
```

### Use Case 4: Data Lake Migration

**Scenario:** Mirror entire S3 data lake to MinIO

```json
{
  "s3_bucket": "data-lake",
  "s3_prefix": "",
  "file_extensions": null,
  "profile_structured": true
}
```

---

## ⚠️ Common Issues

### 1. Access Denied

```
botocore.exceptions.ClientError: An error occurred (403) when calling the HeadBucket operation: Forbidden
```

**Solution:**
- Verify AWS access key and secret key
- Check IAM permissions: User needs `s3:ListBucket`, `s3:GetObject`
- Verify bucket name is correct

### 2. No Such Bucket

```
botocore.exceptions.ClientError: An error occurred (404) when calling the HeadBucket operation: Not Found
```

**Solution:**
- Check bucket name spelling
- Verify bucket exists in the specified region
- Check if you have access to the bucket

### 3. Region Mismatch

```
botocore.exceptions.ClientError: An error occurred (301) when calling the HeadBucket operation: Moved Permanently
```

**Solution:**
- Update `aws_region` in config to match bucket's region
- Check bucket region: `aws s3api get-bucket-location --bucket your-bucket`

### 4. Credentials Not Found

```
botocore.exceptions.NoCredentialsError: Unable to locate credentials
```

**Solution:**
- Add AWS keys to s3_config.json
- Or run `aws configure` to set default credentials

---

## 🔒 Security Best Practices

1. **Use IAM Roles** (if running on EC2/ECS)
2. **Restrict Permissions** (read-only: `s3:GetObject`, `s3:ListBucket`)
3. **Don't commit credentials** (add `*_config.json` to .gitignore)
4. **Use AWS Secrets Manager** for production
5. **Enable S3 bucket encryption** at rest

---

## 📈 Performance Tips

| File Count | Recommendation |
|------------|----------------|
| < 100 files | No special considerations |
| 100-1K files | Use `file_extensions` to filter |
| 1K-10K files | Consider splitting by prefix |
| > 10K files | Run multiple ingestions in parallel with different prefixes |

**Example parallel ingestion:**
```bash
# Terminal 1
python s3_file_ingestor.py s3_config_jan.json --mode streaming &

# Terminal 2
python s3_file_ingestor.py s3_config_feb.json --mode streaming &
```

---

## 🔄 Next Steps

After successful ingestion:

1. **View catalog**:
   ```bash
   cd "../../data lakehouse/syniq_project"
   python main.py catalog list
   ```

2. **Check files in MinIO**:
   - Open browser: http://localhost:9000
   - Login with admin/password123
   - Browse bronze/s3_prod/files/

3. **View lineage**:
   ```bash
   python main.py lineage upstream bronze/s3_prod/files
   ```

---

## 🆚 When to Use S3 vs Direct Ingestion

| Use S3 Ingestor | Use Direct Ingestor (PostgreSQL/MongoDB) |
|-----------------|------------------------------------------|
| Files already in S3 | Data in database |
| Unstructured data (images, videos) | Structured/semi-structured data |
| Batch file uploads | Real-time streaming |
| Pre-exported datasets | Query-based extraction |
| No transformation needed | Need data transformation |

Both are now supported in your data lakehouse! 🎉
