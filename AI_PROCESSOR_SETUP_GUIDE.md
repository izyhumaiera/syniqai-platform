# SyniqAI Block 2 - AI Processing System Setup Guide

## Overview
This guide helps you set up and run the AI processing worker that processes images, PDFs, and documents using OpenRouter AI.

## Architecture
```
bronze-ready topic → ai_processor.py → OpenRouter API → syniqai-silver/ MinIO
                                    ↓
                            silver_assets PostgreSQL
                                    ↓
                            silver-ready topic
```

---

## Step 1: PostgreSQL Setup (When Admin is Available)

### Connect to PostgreSQL
1. Open **pgAdmin 4**
2. Connect to **PostgreSQL 18** (localhost:5432)
3. Open **Query Tool** (Tools → Query Tool)

### Run the SQL Script
```sql
-- Copy and paste the entire contents of create_silver_tables.sql
-- It will create:
-- - silver_assets table
-- - silver_quality_flags table
-- - Indexes and views
```

Or run from command line:
```powershell
psql -U postgres -d syniqai_metadata -f create_silver_tables.sql
```

---

## Step 2: Get OpenRouter API Key

### Sign Up
1. Go to https://openrouter.ai/
2. Create a free account
3. Go to **Keys** section
4. Click **Create Key**
5. Copy your API key (starts with `sk-or-...`)

### Set Environment Variable
**Windows PowerShell:**
```powershell
$env:OPENROUTER_API_KEY="sk-or-your-api-key-here"
```

Or add to `.env` file in the Syniq root folder:
```
OPENROUTER_API_KEY=sk-or-your-api-key-here
OPENROUTER_MODEL=qwen/qwen3-vl-8b-thinking
```

---

## Step 3: Install Dependencies

```powershell
cd "C:\Users\Local user\OneDrive - M Telecommunication Sdn Bhd\Desktop\TASK\Syniq\Kafka Integration"

pip install -r requirements-ai-processor.txt
```

---

## Step 4: Verify Prerequisites

### Check Kafka is Running
```powershell
Test-NetConnection localhost -Port 9092
```
✓ Should show: **TcpTestSucceeded: True**

### Check MinIO is Running
```powershell
Test-NetConnection localhost -Port 9000
```
✓ Should show: **TcpTestSucceeded: True**

### Check PostgreSQL is Running (When Set Up)
```powershell
Test-NetConnection localhost -Port 5432
```

---

## Step 5: Run the AI Processor

```powershell
cd "C:\Users\Local user\OneDrive - M Telecommunication Sdn Bhd\Desktop\TASK\Syniq\Kafka Integration"

python ai_processor.py
```

### Expected Output:
```
======================================================================
  SyniqAI AI Processing Worker - Block 2
======================================================================
  Kafka: localhost:9092
  MinIO: localhost:9000
  PostgreSQL: localhost:5432/syniqai_metadata
  OpenRouter: ✓ API Key Set
======================================================================

✓ AI Processor initialized
✓ Connected to PostgreSQL
🚀 AI Processor started - listening to bronze-ready
   OpenRouter Model: qwen/qwen3-vl-8b-thinking
```

---

## Step 6: Test the Pipeline

### 1. Check if bronze_ready_emitter is running
The bronze_ready_emitter should already be running from Block 1.

### 2. Add test files to MongoDB or S3
Use your existing data ingestion wizard to upload:
- Images (.jpg, .png)
- PDFs
- Text files (.txt)

### 3. Watch AI Processor Logs
You should see:
```
Processing message: sample.jpg
Processing image: sample.jpg
✓ Uploaded to syniqai-silver/jpg/2026-03-26/sample.jpg.json
✓ Inserted silver_asset: xxxxx-xxxxx-xxxxx
✓ Emitted silver-ready event for sample.jpg
```

---

## Step 7: View Results in Frontend

### Start Frontend (if not running)
```powershell
cd "C:\Users\Local user\OneDrive - M Telecommunication Sdn Bhd\Desktop\TASK\Syniq\gui"
.\start_dev.ps1
```

### Open Dashboard
1. Navigate to: http://localhost:3000
2. Go to: **Silver Processing → Unstructured → Media Processing Dashboard**

You should see:
- **Total Files**: Real count from database
- **Images**: Count of processed images
- **Documents**: Count of processed PDFs/docs
- **Recent Processing Jobs**: List of processed files with status

---

## API Endpoints Available

### Query Silver Assets
```
GET /api/silver/assets?file_type=jpg&status=success&limit=20
```

### Get Dashboard Stats
```
GET /api/silver/assets/stats
```
Returns:
```json
{
  "total_files": 42,
  "images": 25,
  "documents": 17,
  "avg_confidence": 0.92
}
```

### Download Original File
```
GET /api/silver/download/{asset_id}
```
Returns presigned URL for downloading from MinIO Bronze.

---

## Configuration Options

### Environment Variables
```
# Required
OPENROUTER_API_KEY=sk-or-your-key-here

# Optional (with defaults)
OPENROUTER_MODEL=qwen/qwen3-vl-8b-thinking
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=admin
MINIO_SECRET_KEY=password123
DATABASE_URL=postgresql://syniqai_user:syniqai_password@localhost:5432/syniqai_metadata
```

---

## Troubleshooting

### 1. "OPENROUTER_API_KEY not set"
**Solution**: Set the environment variable before running:
```powershell
$env:OPENROUTER_API_KEY="sk-or-your-key-here"
python ai_processor.py
```

### 2. "PostgreSQL connection failed"
**Solution**: 
- If admin hasn't set up database yet, the processor will still run
- It will log: "No PostgreSQL connection - skipping database insert"
- Files still get processed and saved to MinIO
- When database is ready, restart the processor

### 3. "Cannot connect to Kafka"
**Solution**: Start Kafka:
```powershell
cd C:\kafka\kafka-4.2.0
.\bin\windows\kafka-server-start.bat .\config\server.properties
```

### 4. "MinIO connection failed"
**Solution**: Start MinIO:
```powershell
cd C:\syniq\minio
.\start_minio.bat
```

### 5. "NoBrokersAvailable" error
**Solution**: Kafka broker not running or wrong port. Check:
```powershell
Test-NetConnection localhost -Port 9092
```

---

## File Processing Details

### Images (.jpg, .jpeg, .png, .gif, .bmp)
- **Model**: qwen/qwen3-vl-8b-thinking (vision model)
- **Output**: 
  ```json
  {
    "tags": ["mountain", "landscape", "sky"],
    "ocr_text": "extracted text from image",
    "captions": {"main": "A beautiful mountain landscape"},
    "confidence": 0.95
  }
  ```

### PDFs
- **Plain PDFs** (text extractable):
  - Model: qwen/qwen3-8b (text model)
  - Extracts text directly from PDF
  
- **Scanned PDFs** (images):
  - Model: qwen/qwen3-vl-8b-thinking (vision model)
  - Converts to image and applies OCR

- **Output**:
  ```json
  {
    "extracted_text": "full document text...",
    "summary": "brief summary of content",
    "ocr_confidence": 0.88
  }
  ```

### Text Documents (.txt, .docx)
- **Model**: qwen/qwen3-8b
- **Output**:
  ```json
  {
    "extracted_text": "full document text...",
    "summary": "concise summary"
  }
  ```

---

## Dead Letter Queue (DLQ)

If processing fails, messages go to the `dlq-errors` topic:
```json
{
  "original_message": {...},
  "error": "Error description",
  "error_type": "ValueError",
  "traceback": "full stack trace",
  "failed_at": "2026-03-26T10:30:00Z"
}
```

### View DLQ Messages
```powershell
cd C:\kafka\kafka-4.2.0
.\bin\windows\kafka-console-consumer.bat --bootstrap-server localhost:9092 --topic dlq-errors --from-beginning
```

---

## Next Steps

1. **Set up PostgreSQL** (when admin is available)
2. **Get OpenRouter API key** (free at https://openrouter.ai)
3. **Install dependencies**: `pip install -r requirements-ai-processor.txt`
4. **Run ai_processor.py**
5. **Upload test files** via the ingestion wizard
6. **Check the dashboard** to see processed results!

---

## Questions?

- PostgreSQL setup issues → Wait for admin, processor still works without it
- OpenRouter API questions → Check https://openrouter.ai/docs
- Kafka issues → Check if broker is running on port 9092
- MinIO issues → Check if MinIO is running on port 9000

The AI processor is designed to be **resilient** - it will keep running and processing files even if PostgreSQL is not available yet. Files are still saved to MinIO Silver layer and events are emitted to Kafka.
