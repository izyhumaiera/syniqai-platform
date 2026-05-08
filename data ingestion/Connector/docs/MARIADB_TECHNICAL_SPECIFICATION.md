# SyniqAI Data Ingestion System
## MariaDB Connector - Technical Specification Document

**Version:** 2.0  
**Date:** February 12, 2026  
**Status:** Production-Ready with Advanced Optimizations

---

## Table of Contents

1. [Introduction](#1-introduction)
   - 1.1 [Executive Summary](#11-executive-summary)
   - 1.2 [The Evolution - From Basic to Production-Grade](#12-the-evolution---from-basic-to-production-grade)
   - 1.3 [Glossary of Terms & Acronyms](#13-glossary-of-terms--acronyms)
2. [System Overview – Product Behaviour & Capabilities](#2-system-overview--product-behaviour--capabilities)
   - 2.1 [How the System Behaves](#21-how-the-system-behaves)
   - 2.2 [Architectural Design Principles](#22-architectural-design-principles)
   - 2.3 [Explicit Non-Goals](#23-explicit-non-goals)
3. [System Architecture](#3-system-architecture)
   - 3.1 [High-Level Architecture](#31-high-level-architecture)
   - 3.2 [Storage Engine Awareness Architecture](#32-storage-engine-awareness-architecture)
4. [Functional Specification](#4-functional-specification)
   - 4.1 [Ingestion Configuration](#41-ingestion-configuration)
   - 4.2 [Intelligent Auto-Tuning Logic](#42-intelligent-auto-tuning-logic)
   - 4.3 [Storage Engine Detection & Risk Assessment](#43-storage-engine-detection--risk-assessment)
   - 4.4 [Advanced Optimizations](#44-advanced-optimizations)
   - 4.5 [Technical Implementation](#45-technical-implementation)
   - 4.6 [Bronze Layer Specification](#46-bronze-layer-specification)
5. [Technical Specification](#5-technical-specification)
   - 5.1 [Technology Stack](#51-technology-stack)
   - 5.2 [Component Breakdown](#52-component-breakdown)
   - 5.3 [Data Flow Architecture](#53-data-flow-architecture)
   - 5.4 [Concurrency & Performance Model](#54-concurrency--performance-model)
   - 5.5 [Schema Handling Strategy](#55-schema-handling-strategy)
6. [Storage Engine Strategy Matrix](#6-storage-engine-strategy-matrix)
   - 6.1 [Engine Capabilities](#61-engine-capabilities)
   - 6.2 [Engine-Specific Optimizations](#62-engine-specific-optimizations)
7. [Security & Data Privacy](#7-security--data-privacy)
   - 7.1 [Credential Management](#71-credential-management)
   - 7.2 [Network & Access Controls](#72-network--access-controls)
   - 7.3 [Data Integrity & Auditability](#73-data-integrity--auditability)
8. [Performance & Metrics](#8-performance--metrics)
   - 8.1 [Key Performance Indicators](#81-key-performance-indicators)
   - 8.2 [Optimization Impact Analysis](#82-optimization-impact-analysis)
9. [Project Timeline](#9-project-timeline)
10. [Conclusion & Roadmap](#10-conclusion--roadmap)
11. [Appendix A: Environmental Setup](#appendix-a-environmental-setup)
12. [Appendix B: Storage Engine Decision Tree](#appendix-b-storage-engine-decision-tree)

---

## 1. Introduction

### 1.1 Executive Summary

The **SyniqAI MariaDB Connector** is an enterprise-grade, storage-engine-aware data ingestion framework engineered to extract large-scale relational data from MariaDB databases with unprecedented efficiency, safety, and intelligence. Unlike generic database connectors, this system is explicitly designed to understand and adapt to MariaDB's diverse storage engine ecosystem—including InnoDB, ColumnStore, MyISAM, Aria, and Memory engines.

The connector implements three breakthrough optimizations:

1. **Smart Chunking via Quantile Sampling** - Eliminates worker idle time on sparse primary key ranges
2. **PyArrow Backend Integration** - Achieves 30-50% memory reduction through columnar processing
3. **Adaptive Throttling** - Prevents production database overload through real-time health monitoring

By combining storage-engine-aware extraction strategies, intelligent parallel processing, automatic parameter tuning, and production-safe throttling mechanisms, the system delivers a **2.5× performance improvement** while maintaining strict memory safety, transactional consistency, and zero data loss guarantees.

**Key Differentiators:**
- **Storage Engine Intelligence**: First-class support for InnoDB MVCC snapshots, ColumnStore parallel scans, and MyISAM locking awareness
- **Self-Tuning**: Automatically calculates optimal chunk sizes and worker counts based on system resources and data characteristics
- **Production-Safe**: Built-in throttling prevents database saturation in shared environments
- **Memory Efficient**: PyArrow backend reduces memory footprint by 40-50%
- **Schema Resilient**: Handles JSON columns, complex types, and schema drift without data loss

### 1.2 The Evolution - From Basic to Production-Grade

The MariaDB connector's development followed a rigorous, failure-informed evolution:

**Phase 1: Foundation (Basic Connectivity)**
- Single-threaded extraction
- Simple range-based chunking
- Standard pandas DataFrame processing
- No engine awareness

**Critical Weaknesses Discovered:**
- **Worker Imbalance**: Tables with deleted rows (sparse PKs) caused idle workers—some processed 200k rows while others finished in seconds
- **Memory Explosion**: Large tables with wide rows consumed 5-6 GB RAM due to pandas object overhead
- **Production Incidents**: High-throughput extraction overwhelmed shared databases, affecting production users
- **Engine-Specific Failures**: MyISAM table locks, ColumnStore projection inefficiencies, and InnoDB snapshot inconsistencies

**Phase 2: Storage Engine Awareness**
- Implemented engine detection via `information_schema.TABLES`
- Created risk matrix categorizing engines by safety characteristics
- Added MVCC snapshot support for InnoDB
- Disabled parallelism for MyISAM/Aria to prevent table locks

**Phase 3: Advanced Optimizations (Current)**
- **Quantile Sampling**: Replaced blind range splitting with data-distribution-aware boundaries
- **PyArrow Integration**: Reduced memory footprint through columnar processing
- **Adaptive Throttling**: Real-time monitoring of database health with automatic backoff
- **ColumnStore Optimization**: Partition-aware extraction for analytical workloads

This evolution reflects a core philosophy: **performance must never compromise stability, data integrity, or production safety**.

### 1.3 Glossary of Terms & Acronyms

| Term | Definition |
|------|------------|
| **Bronze Layer** | Raw, immutable storage layer containing ingested data with full metadata preservation |
| **ColumnStore** | MariaDB's columnar storage engine optimized for analytical queries |
| **Consistent Snapshot** | InnoDB's MVCC mechanism providing non-blocking, point-in-time data views |
| **Chunk** | A bounded batch of rows extracted in a single database fetch operation |
| **Quantile Sampling** | Statistical technique to find actual data distribution boundaries for even workload distribution |
| **MVCC** | Multi-Version Concurrency Control; allows non-blocking reads via row versioning |
| **InnoDB** | MariaDB's default ACID-compliant transactional storage engine with row-level locking |
| **MyISAM** | Legacy non-transactional engine with table-level locking (extraction requires caution) |
| **Aria** | Crash-safe MyISAM alternative with improved recovery but still table-level locking |
| **PyArrow** | Apache Arrow's Python implementation providing columnar memory layout |
| **Run ID** | Unique timestamp-based identifier for each extraction execution |
| **Throttling** | Automatic delay mechanism to prevent database overload based on health metrics |
| **Storage Engine** | MariaDB's pluggable backend determining how tables are physically stored and accessed |
| **Parquet** | Columnar, compressed file format optimized for analytical workloads |
| **Watermark** | Column value (timestamp/ID) used for incremental extraction tracking |

---

## 2. System Overview – Product Behaviour & Capabilities

### 2.1 How the System Behaves

The MariaDB connector follows a **deterministic, stage-gated execution model** with automatic adaptation based on storage engine characteristics and system resources:

**Execution Flow:**

```
┌─────────────────────────────────────────────────────────────────┐
│ Stage 1: Discovery & Planning                                   │
│  ├─ Detect storage engine (InnoDB, ColumnStore, MyISAM, etc.)  │
│  ├─ Identify primary key and assess integer suitability        │
│  ├─ Calculate optimal chunk size and worker count              │
│  ├─ Determine parallel vs. serial execution strategy            │
│  └─ Sample data distribution (quantile boundaries)              │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ Stage 2: Extraction (Engine-Aware)                              │
│  ├─ InnoDB: Acquire consistent snapshot per worker             │
│  ├─ ColumnStore: Use partition-aware parallel scans            │
│  ├─ MyISAM/Aria: Force serial extraction with LOW_PRIORITY     │
│  ├─ Apply adaptive throttling based on DB health               │
│  └─ Stream data using PyArrow backend (30-50% RAM reduction)   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ Stage 3: Persistence & Metadata                                 │
│  ├─ Sanitize complex types (JSON → string[pyarrow])            │
│  ├─ Write Parquet with Snappy compression                      │
│  ├─ Generate metadata with schema snapshot and lineage         │
│  └─ Validate output integrity before completion                │
└─────────────────────────────────────────────────────────────────┘
```

**Core Behavioral Guarantees:**

1. **Engine-Aware Execution**: Strategies automatically adapt to storage engine capabilities
2. **Fail-Fast Philosophy**: Errors are surfaced immediately; partial failures are never silently ignored
3. **Deterministic Outputs**: Each run produces versioned, immutable data + metadata artifacts
4. **Memory Safety**: Auto-tuning prevents out-of-memory conditions on resource-constrained systems
5. **Production Safety**: Adaptive throttling prevents connector from overwhelming shared databases

### 2.2 Architectural Design Principles

**1. Storage Engine as First-Class Concern**
- Not all MariaDB engines are created equal—InnoDB supports MVCC, MyISAM requires table locks
- Extraction strategy must respect engine capabilities to avoid data inconsistencies or production outages

**2. Intelligent Auto-Tuning**
- System resources (CPU cores, available RAM) drive parameter calculation
- No manual tuning required—connector adapts to execution environment

**3. Quantile-Based Workload Distribution**
- Traditional range splitting (`MIN(id)` to `MAX(id)`) fails on sparse PKs
- Quantile sampling ensures even distribution regardless of deletion patterns

**4. Producer-Consumer Decoupling**
- Database I/O (network-bound) separated from disk I/O (storage-bound)
- Bounded queues enforce backpressure to prevent memory exhaustion

**5. Good Neighbor Policy**
- Connector monitors database health (active threads, buffer pool hit ratio)
- Automatically throttles extraction when database is under load

**6. Schema Survival Over Schema Evolution**
- JSON columns are serialized, not exploded
- Schema changes are surfaced explicitly, never applied silently
- Preserves lineage and prevents data loss

### 2.3 Explicit Non-Goals

To maintain focus and clarity, the following are **explicitly excluded** from this system:

❌ **Automatic Array Flattening** - Arrays are preserved to prevent irreversible transformations  
❌ **Implicit Schema Mutation** - Bronze layer maintains source fidelity; transformations happen in Silver  
❌ **Unmonitored High-Throughput Extraction** - Production safety is mandatory, not optional  
❌ **Cross-Engine Transaction Guarantees** - MyISAM/Memory engines lack transactional semantics  
❌ **Real-Time Streaming** - System is optimized for batch ingestion, not CDC/streaming workloads  
❌ **Automatic Failover/Retry** - Failures are surfaced for human intervention; blind retries mask root causes

---

## 3. System Architecture

### 3.1 High-Level Architecture

The MariaDB connector implements a **threaded producer-consumer architecture** with engine-aware orchestration:

```
┌──────────────────────────────────────────────────────────────────────┐
│                    Orchestrator (main.py)                            │
│  • Configuration validation                                           │
│  • Resource assessment (CPU, RAM)                                    │
│  • Execution strategy selection                                      │
└────────────────────────────┬─────────────────────────────────────────┘
                             │
                             ↓
┌──────────────────────────────────────────────────────────────────────┐
│              MariaDB Connector (mariadb_connector.py)                │
│                                                                       │
│  ┌────────────────────────────────────────────────────────┐         │
│  │ ExtractionOptimizer                                     │         │
│  │  • Auto-calculate chunk_size & num_workers             │         │
│  │  • Consider RAM, CPU, table size, network latency      │         │
│  └────────────────────────────────────────────────────────┘         │
│                             │                                         │
│  ┌────────────────────────────────────────────────────────┐         │
│  │ Engine Detection & Risk Assessment                      │         │
│  │  • Query information_schema.TABLES                     │         │
│  │  • Map engine → capabilities (parallel_safe, MVCC, etc)│         │
│  │  • Check primary key suitability                       │         │
│  └────────────────────────────────────────────────────────┘         │
│                             │                                         │
│  ┌────────────────────────────────────────────────────────┐         │
│  │ Quantile Sampler (OPTIMIZATION 1)                      │         │
│  │  • Sample actual data distribution                     │         │
│  │  • Calculate equidistant boundaries                    │         │
│  │  • Fallback to min/max if table too small              │         │
│  └────────────────────────────────────────────────────────┘         │
└──────────────────────────────┬───────────────────────────────────────┘
                               │
                ┌──────────────┴───────────────┐
                ↓                              ↓
┌───────────────────────────┐  ┌──────────────────────────────────┐
│   Parallel Extraction     │  │    Serial Extraction             │
│   (InnoDB, ColumnStore)   │  │    (MyISAM, Aria, Memory)        │
│                           │  │                                  │
│  Thread Pool Executor     │  │  Single Connection               │
│  ├─ Worker 1: START TX   │  │  └─ START TX (if MVCC)          │
│  │   WITH CONSISTENT     │  │     Read in chunks               │
│  │   SNAPSHOT            │  │     Apply throttling             │
│  ├─ Worker 2: Range      │  │     Sanitize & yield             │
│  │   [quantile_0 to      │  │                                  │
│  │    quantile_1]        │  │                                  │
│  ├─ Worker N: ...        │  │                                  │
│  └─ Adaptive Throttling  │  │                                  │
│     (OPTIMIZATION 3)      │  │                                  │
└──────────┬────────────────┘  └─────────┬────────────────────────┘
           │                             │
           └──────────┬──────────────────┘
                      ↓
           ┌─────────────────────────┐
           │   Bounded Queue         │
           │   (maxsize = 2×workers) │
           │   • Backpressure        │
           │   • Memory safety       │
           └──────────┬──────────────┘
                      ↓
           ┌─────────────────────────┐
           │ Sanitization Layer      │
           │ • PyArrow backend       │
           │ • JSON serialization    │
           │ • Type coercion         │
           └──────────┬──────────────┘
                      ↓
           ┌─────────────────────────┐
           │   ParquetSink           │
           │   • Snappy compression  │
           │   • Thread-safe writes  │
           │   • Schema validation   │
           └──────────┬──────────────┘
                      ↓
           ┌─────────────────────────┐
           │   Bronze Layer          │
           │   ├─ data.parquet       │
           │   └─ metadata.json      │
           └─────────────────────────┘
```

### 3.2 Storage Engine Awareness Architecture

The connector's intelligence stems from its **storage engine capability matrix**:

```python
ENGINE_CAPABILITIES = {
    "innodb":      {"parallel_safe": True,  "mvcc": True,  "risk": "low",    "locks": "row"},
    "columnstore": {"parallel_safe": True,  "mvcc": False, "risk": "low",    "locks": "none"},
    "myisam":      {"parallel_safe": False, "mvcc": False, "risk": "high",   "locks": "table"},
    "aria":        {"parallel_safe": False, "mvcc": False, "risk": "medium", "locks": "table"},
    "memory":      {"parallel_safe": False, "mvcc": False, "risk": "high",   "locks": "table"},
}
```

**Decision Logic:**

| Storage Engine | Parallel Enabled? | Snapshot Strategy | Warning Level |
|----------------|-------------------|-------------------|---------------|
| **InnoDB** | ✅ Yes | `START TRANSACTION WITH CONSISTENT SNAPSHOT` | Low |
| **ColumnStore** | ✅ Yes | No snapshot (append-only) | Low |
| **MyISAM** | ❌ No (table lock risk) | None | **HIGH** - Production impact warning |
| **Aria** | ❌ No | None | **MEDIUM** - Locking warning |
| **Memory** | ❌ No | None | **HIGH** - Data volatility warning |

---

## 4. Functional Specification

### 4.1 Ingestion Configuration

#### 4.1.1 Configuration Schema

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `source_type` | String | Yes | Must be `"mariadb"` |
| `connection_config.host` | String | Yes | Hostname or IP address |
| `connection_config.port` | Integer | No | Port (default: 3306) |
| `connection_config.database` | String | Yes | Target database schema |
| `connection_config.user` | String | Yes | Database username |
| `connection_config.password` | String | Yes* | Password (or use secret_handler) |
| `connection_config.ssl_ca` | String | No | Path to SSL CA certificate |
| `extraction_request.entity` | String | Yes | Target table name |
| `extraction_request.mode` | String | Yes | `"full"` or `"incremental"` |
| `extraction_request.enable_parallel` | Boolean | No | Allow parallel extraction (default: true) |
| `extraction_request.flatten_json` | Object | No | JSON column flattening rules |

*Password can be resolved via `secret_handler` for enhanced security.

#### 4.1.2 Sample Configuration

```json
{
  "source_type": "mariadb",
  "connection_config": {
    "host": "192.168.2.114",
    "port": 3300,
    "database": "mariadb_benchmarking",
    "user": "remote_user",
    "password": "${MARIADB_PASSWORD}",
    "ssl_ca": "/path/to/ca-cert.pem"
  },
  "extraction_request": {
    "entity": "user_transactions",
    "mode": "full",
    "enable_parallel": true,
    "avg_row_size": 2048,
    "flatten_json": {
      "metadata_column": ["user_id", "timestamp"]
    }
  }
}
```

### 4.2 Intelligent Auto-Tuning Logic

The **ExtractionOptimizer** class performs runtime resource assessment and automatic parameter calculation:

**Input Variables:**
- `row_count`: Estimated table size from `information_schema.TABLES`
- `avg_row_size_bytes`: Average row width (user-provided or defaults to 1024)
- `is_remote`: Whether database is on a remote host
- `engine_type`: Storage engine (influences parallelism decisions)

**Calculation Algorithm:**

```
Base Chunk Size = min(100 MB / avg_row_size, table_size_ceiling)

Table Size Ceiling:
  • < 1,000 rows       → entire table (no chunking)
  • < 10,000 rows      → 1,000 rows/chunk
  • < 100,000 rows     → 10,000 rows/chunk
  • < 1,000,000 rows   → 50,000 rows/chunk
  • ≥ 1,000,000 rows   → 100,000 rows/chunk

Max Workers Calculation:
  1. By RAM:    (Available RAM × 0.5) / chunk_memory_size
  2. By CPU:    CPU core count
  3. By Efficiency: √(total_chunks) + 1

Final Workers = min(by_RAM, by_CPU, by_efficiency) × network_factor
  • network_factor = 0.75 if remote, 1.0 if local
  • Capped at 16 workers maximum
  • Set to 1 if table < 1,000 rows (no parallel overhead)
```

**Example:**
- Table: 500,000 rows
- Available RAM: 8 GB
- CPU cores: 8
- Remote database

**Result:**
- Chunk size: 50,000 rows
- Workers: 4 (balanced by efficiency factor and network penalty)

### 4.3 Storage Engine Detection & Risk Assessment

**Detection Process:**

1. **Query Engine Type:**
```sql
SELECT ENGINE FROM information_schema.TABLES 
WHERE TABLE_SCHEMA = :db AND TABLE_NAME = :table
```

2. **Map to Capability Matrix:**
```python
caps = ENGINE_CAPABILITIES.get(storage_engine.lower(), ENGINE_CAPABILITIES["unknown"])
```

3. **Assess Primary Key:**
```python
pk_columns = inspector.get_pk_constraint(table_name)
# Check if single-column integer PK (required for range-based parallelism)
```

4. **Log Risk Assessment:**
```
🧐 Table 'orders': Engine=InnoDB | PK=order_id | Risk=LOW
```

**Risk-Based Warnings:**

| Risk Level | Trigger Conditions | System Response |
|------------|-------------------|-----------------|
| **LOW** | InnoDB or ColumnStore | ✅ Proceed with optimal strategy |
| **MEDIUM** | Aria engine | ⚠️ Warn about table-level locks, use serial extraction |
| **HIGH** | MyISAM or Memory | 🚨 Display production impact warning, check for active locks |

**MyISAM Safety Check:**
```python
def _check_myisam_safety(self, entity: str) -> bool:
    # Query SHOW OPEN TABLES to detect active locks
    # Abort if table is currently locked
    # Display prominent warning about table locking
```

### 4.4 Advanced Optimizations

#### 4.4.1 OPTIMIZATION 1: Smart Chunking (Quantile Sampling)

**Problem:**
Traditional range splitting divides PK range equally:
```
Table: id IN (1, 2, 3, ..., 200000, 900000, 900001, ..., 1000000)
         [-------200k rows-------]  [-----100k rows-----]

Classic Split (4 workers):
  Worker 1: id 1 → 250,000      → Processes 200,000 rows
  Worker 2: id 250,001 → 500,000 → Processes 0 rows (gap!)
  Worker 3: id 500,001 → 750,000 → Processes 0 rows (gap!)
  Worker 4: id 750,001 → 1M      → Processes 100,000 rows
```

Result: Workers 2 & 3 idle, uneven load distribution.

**Solution: Quantile Sampling**

```sql
-- Sample actual data distribution
SELECT id FROM table ORDER BY id LIMIT 1 OFFSET 0;      -- Boundary 0
SELECT id FROM table ORDER BY id LIMIT 1 OFFSET 25000;  -- Boundary 1
SELECT id FROM table ORDER BY id LIMIT 1 OFFSET 50000;  -- Boundary 2
SELECT id FROM table ORDER BY id LIMIT 1 OFFSET 75000;  -- Boundary 3
SELECT id FROM table ORDER BY id LIMIT 1 OFFSET 100000; -- Boundary 4
```

Result: Boundaries align with actual data, not PK values.

```
Quantile Split:
  Worker 1: id 1 → 50,000        → Processes 25,000 rows
  Worker 2: id 50,001 → 100,000  → Processes 25,000 rows
  Worker 3: id 100,001 → 150,000 → Processes 25,000 rows
  Worker 4: id 150,001 → 200,000 → Processes 25,000 rows
```

**Performance Impact:**
- Eliminates idle workers on sparse PKs
- Reduces standard deviation of worker completion times by 85%
- 20-30% throughput improvement on tables with >10% deleted rows

#### 4.4.2 OPTIMIZATION 2: PyArrow Backend Integration

**Problem:**
Pandas default object storage uses ~3-5× more memory than raw data due to:
- Python object overhead per cell
- Inefficient string storage
- Non-columnar memory layout

**Solution:**
```python
chunk_df = pd.read_sql(
    query, 
    conn, 
    dtype_backend="pyarrow"  # Use Apache Arrow columnar format
)
```

**Benefits:**

| Metric | Pandas Default | PyArrow Backend | Improvement |
|--------|---------------|-----------------|-------------|
| Memory Usage | 6 GB | 3.2 GB | **47% reduction** |
| Parquet Write Speed | 8.2 sec | 2.7 sec | **3× faster** |
| String Handling | Object | UTF-8 Arrow | Native columnar |
| Null Efficiency | Sentinel values | Bitmap | Compact representation |

**Type Handling:**
```python
# Complex types (dict, list) → JSON strings → PyArrow string type
df[col] = df[col].apply(lambda x: json.dumps(x) if x else None)
df[col] = df[col].astype("string[pyarrow]")
```

#### 4.4.3 OPTIMIZATION 3: Adaptive Throttling

**Problem:**
High-performance extractors can:
- Saturate database connections (Threads_running > 100)
- Evict hot data from InnoDB buffer pool
- Cause query latency spikes for production users

**Solution: Real-Time Health Monitoring**

```python
def _check_database_health(self) -> dict:
    # Monitor 2 critical metrics:
    
    # 1. Active connections
    threads_running = SHOW GLOBAL STATUS LIKE 'Threads_running'
    
    # 2. Buffer pool efficiency
    hit_ratio = (1 - (Innodb_buffer_pool_reads / 
                      Innodb_buffer_pool_read_requests)) × 100
    
    # Calculate throttle
    if threads_running > 50:
        throttle_seconds = min((threads_running - 50) × 0.5, 10)
    
    if hit_ratio < 80%:
        throttle_seconds = max(throttle_seconds, 2.0)
```

**Integration:**
Every worker checks health **before** each query:
```python
health = self._check_database_health()
if health["throttle_seconds"] > 0:
    logger.warning(f"⏳ Throttling {health['throttle_seconds']}s")
    time.sleep(health["throttle_seconds"])
```

**Production Impact:**
- Prevents runaway resource consumption
- Maintains SLA for concurrent users
- Self-regulates based on actual load, not static limits

### 4.5 Technical Implementation

#### 4.5.1 Data Flow Strategy

**READ**
- **Connection Pooling**: SQLAlchemy pool (size=20, max_overflow=10) eliminates TCP handshake overhead
- **Engine-Specific Transactions**:
  - InnoDB: `START TRANSACTION WITH CONSISTENT SNAPSHOT`
  - ColumnStore: No transaction (append-only, lock-free)
  - MyISAM: `LOW_PRIORITY` hint to defer to writes
- **PyArrow Streaming**: Data never fully materialized in memory

**PROCESS**
- **Schema Snapshotting**: Captured before extraction begins
- **JSON Serialization**: Complex types deterministically converted to strings
- **Type Coercion**: PyArrow-aware type handling preserves schema fidelity

**OUTPUT**
- **Parquet Format**: Columnar storage with Snappy compression
- **Metadata Generation**: Lineage, schema, execution stats persisted alongside data
- **Atomic Writes**: Temporary files + rename ensures crash safety

#### 4.5.2 Concurrency Model

**Parallel Execution (InnoDB, ColumnStore):**
```python
ThreadPoolExecutor(max_workers=num_workers)
  ├─ Worker 1: Quantile range [boundary_0, boundary_1)
  ├─ Worker 2: Quantile range [boundary_1, boundary_2)
  └─ Worker N: Quantile range [boundary_N-1, boundary_N)

Bounded Queue (maxsize = num_workers × 2)
  • Automatic backpressure if disk I/O is slow
  • Prevents unbounded memory growth
```

**Serial Execution (MyISAM, Aria, Memory):**
```python
Single connection with chunked iterator:
  for chunk in pd.read_sql(..., chunksize=chunk_size):
      sanitize_and_yield(chunk)
```

#### 4.5.3 Schema Handling Strategy

**Principles:**
1. **Snapshot Before Extraction**: Schema locked at run start
2. **Serialize, Don't Explode**: JSON and arrays preserved as strings
3. **Explicit Type Mapping**:
   - `DECIMAL(p,s)` → `float64` (or string for financial precision mode—future)
   - `JSON` → `string[pyarrow]`
   - `BLOB` → Base64 string (future enhancement)
4. **Drift Detection**: Schema logged in metadata for Silver-layer comparison

### 4.6 Bronze Layer Specification

**Directory Structure:**
```
bronze_layer/
└── user_transactions/
    └── 20260212_143052/          # Run ID (YYYYmmdd_HHMMSS)
        ├── data_00001.parquet
        ├── data_00002.parquet
        ├── ...
        └── metadata.json
```

**Metadata Schema:**
```json
{
  "source_type": "mariadb",
  "entity": "user_transactions",
  "storage_engine": "InnoDB",
  "engine_risk_level": "low",
  "extraction_mode": "full",
  "total_rows": 1045320,
  "total_chunks": 21,
  "avg_rows_per_chunk": 49777,
  "schema_snapshot": [
    {"name": "txn_id", "type": "BIGINT"},
    {"name": "amount", "type": "DECIMAL(10,2)"},
    {"name": "metadata", "type": "JSON"}
  ],
  "optimization_used": "quantile_sampling",
  "num_workers": 4,
  "chunk_size": 50000,
  "execution_time_seconds": 18.7,
  "throughput_rows_per_sec": 55913,
  "extracted_at": "2026-02-12T14:30:52.123456Z",
  "run_id": "20260212_143052"
}
```

**Guarantees:**
- ✅ **Immutable**: Never modified after creation
- ✅ **Versioned**: Each run gets unique timestamp-based ID
- ✅ **Auditable**: Full lineage from source table to output file
- ✅ **Schema-Safe**: Complex types preserved, not corrupted

---

## 5. Technical Specification

### 5.1 Technology Stack

**Runtime Environment:**
- Python 3.10+
- SQLAlchemy 2.0+ (connection pooling, query abstraction)
- PyMySQL (pure-Python MariaDB driver)

**Core Libraries:**

| Library | Version | Purpose |
|---------|---------|---------|
| `pandas` | 2.0+ | DataFrame operations with PyArrow backend |
| `pyarrow` | 12.0+ | Columnar memory layout, Parquet I/O |
| `sqlalchemy` | 2.0+ | Database connection pooling, query execution |
| `pymysql` | 1.0+ | MariaDB protocol implementation |
| `psutil` | 5.9+ | System resource monitoring (CPU, RAM) |
| `threading` | stdlib | Worker thread management |
| `queue` | stdlib | Thread-safe bounded queue for backpressure |
| `json` | stdlib | JSON serialization for complex types |

### 5.2 Component Breakdown

#### A) **ExtractionOptimizer Class**
**Responsibility:** Auto-calculate optimal parameters

**Key Methods:**
```python
def calculate_optimal_params(
    row_count: int,
    avg_row_size_bytes: int,
    is_remote: bool,
    engine_type: str
) -> Tuple[int, int]:
    # Returns: (chunk_size, num_workers)
```

**Logic:**
- Assesses available RAM and CPU cores
- Applies table-size scaling rules
- Considers network latency for remote databases
- Caps workers at 16 to prevent thread explosion

---

#### B) **MariaDBConnector Class**
**Responsibilities:**
- Manage connection lifecycle
- Detect storage engine and capabilities
- Orchestrate parallel or serial extraction
- Apply engine-specific optimizations

**Critical Methods:**

| Method | Purpose |
|--------|---------|
| `_detect_engine_and_pk()` | Query storage engine, assess PK suitability |
| `_get_quantile_boundaries()` | **[NEW]** Sample data distribution for even splits |
| `_check_database_health()` | **[NEW]** Monitor DB load for adaptive throttling |
| `_sanitize_and_flatten()` | PyArrow-aware type handling and JSON serialization |
| `_worker_extract()` | Parallel worker with snapshot + throttling |
| `extract()` | Main orchestration method with auto-optimization |

---

#### C) **Storage Engine Strategy Matrix**
**Embedded Capability Database:**
```python
ENGINE_CAPABILITIES = {
    "innodb": {
        "parallel_safe": True,
        "mvcc": True,
        "risk": "low",
        "locks": "row",
        "optimization_hints": ""
    },
    "columnstore": {
        "parallel_safe": True,
        "mvcc": False,
        "risk": "low",
        "locks": "none",
        "optimization_hints": "/*+ COLUMNAR_SCAN */"
    },
    # ... (full matrix in code)
}
```

**Usage:**
```python
caps = ENGINE_CAPABILITIES[storage_engine]
if caps["parallel_safe"]:
    # Use parallel extraction
if caps["mvcc"]:
    # Acquire consistent snapshot
```

---

#### D) **ParquetSink (Inherited from Base)**
**Responsibilities:**
- Thread-safe Parquet writing
- Compression (Snappy)
- Metadata persistence

---

### 5.3 Data Flow Architecture

```
┌───────────────────────────────────────────────────────────────┐
│ Phase 1: Discovery                                            │
│  1. Connect to MariaDB                                        │
│  2. Validate credentials                                      │
│  3. Query information_schema for engine type                  │
│  4. Estimate row count                                        │
│  5. Calculate optimal chunk_size & num_workers                │
│  6. Sample quantile boundaries (if parallel)                  │
└────────────────────────────┬──────────────────────────────────┘
                             ↓
┌───────────────────────────────────────────────────────────────┐
│ Phase 2: Extraction (Engine-Aware)                           │
│                                                               │
│  IF parallel_safe:                                            │
│    ├─ Spawn N workers via ThreadPoolExecutor                │
│    ├─ Each worker:                                           │
│    │   1. Connect to database (from pool)                   │
│    │   2. START TRANSACTION WITH CONSISTENT SNAPSHOT        │
│    │   3. Check DB health → throttle if needed              │
│    │   4. Execute range query (quantile boundaries)         │
│    │   5. Read with PyArrow backend                         │
│    │   6. Sanitize complex types                            │
│    │   7. Put DataFrame in queue                            │
│    │   8. COMMIT transaction                                │
│    └─ Main thread collects from queue                       │
│                                                               │
│  ELSE (serial):                                               │
│    ├─ Single connection                                      │
│    ├─ START TRANSACTION (if MVCC)                           │
│    ├─ Read in chunks (chunksize=calculated)                 │
│    ├─ Apply PyArrow backend                                 │
│    └─ Yield chunks serially                                 │
└────────────────────────────┬──────────────────────────────────┘
                             ↓
┌───────────────────────────────────────────────────────────────┐
│ Phase 3: Persistence                                          │
│  1. Receive DataFrame chunks                                  │
│  2. Validate schema consistency                               │
│  3. Write to Parquet (Snappy compressed)                      │
│  4. Accumulate metadata (row counts, timing)                  │
│  5. Write metadata.json on completion                         │
└───────────────────────────────────────────────────────────────┘
```

### 5.4 Concurrency & Performance Model

**Parallel Extraction Conditions:**
```python
can_parallelize = (
    meta["is_integer_pk"] and           # Single integer PK exists
    caps["parallel_safe"] and            # Engine supports parallelism
    num_workers > 1 and                  # Auto-calc says use parallelism
    extraction_plan.get("enable_parallel", True)  # User didn't disable
)
```

**Performance Characteristics:**

| Scenario | Chunk Size | Workers | Strategy | Rationale |
|----------|-----------|---------|----------|-----------|
| 500 rows | 500 | 1 | Serial | Avoid thread overhead |
| 50k rows (InnoDB) | 10,000 | 2-4 | Parallel (quantile) | Balanced throughput |
| 5M rows (InnoDB) | 100,000 | 8 | Parallel (quantile) | Maximize throughput |
| 1M rows (MyISAM) | 50,000 | 1 | Serial (LOW_PRIORITY) | Prevent table lock |
| 10M rows (ColumnStore) | 500,000 | 8 | Parallel (partition-aware) | Leverage columnar scan |

**Throttling Thresholds:**
- **Thread Count**: `Threads_running > 50` → throttle
- **Buffer Pool**: Hit ratio `< 80%` → throttle
- **Max Delay**: Capped at 10 seconds per check

### 5.5 Schema Handling Strategy

**Complex Type Mapping:**

| MariaDB Type | Intermediate | Final Parquet Type |
|--------------|--------------|-------------------|
| `INT`, `BIGINT` | `int64` | `INT64` |
| `VARCHAR`, `TEXT` | `string[pyarrow]` | `BYTE_ARRAY (UTF8)` |
| `DECIMAL(p,s)` | `float64` | `DOUBLE` |
| `JSON` | `string[pyarrow]` | `BYTE_ARRAY (UTF8)` |
| `DATETIME` | `datetime64[ns]` | `INT64 (timestamp)` |
| `BLOB` | `bytes` | `BYTE_ARRAY` |

**JSON Flattening (Optional):**
```python
# User config:
"flatten_json": {
    "user_metadata": ["user_id", "signup_date"]
}

# Result:
Original: user_metadata = '{"user_id": 123, "signup_date": "2026-01-01", ...}'
Flattened:
  ├─ user_metadata_user_id = 123
  ├─ user_metadata_signup_date = "2026-01-01"
  └─ user_metadata (original preserved)
```

---

## 6. Storage Engine Strategy Matrix

### 6.1 Engine Capabilities

| Engine | Parallel Safe | MVCC | Locks | Risk Level | Optimization Strategy |
|--------|---------------|------|-------|------------|---------------------|
| **InnoDB** | ✅ Yes | ✅ Yes | Row-level | 🟢 Low | Consistent snapshot per worker |
| **ColumnStore** | ✅ Yes | ❌ No | None | 🟢 Low | Partition-aware, large chunks |
| **MyISAM** | ❌ No | ❌ No | Table-level | 🔴 High | Serial + LOW_PRIORITY hint |
| **Aria** | ❌ No | ❌ No | Table-level | 🟡 Medium | Serial extraction |
| **Memory** | ❌ No | ❌ No | Table-level | 🔴 High | Serial, data volatility warning |

### 6.2 Engine-Specific Optimizations

#### **InnoDB Optimization**
```python
# Per-worker consistent snapshot
conn.execute(text("START TRANSACTION WITH CONSISTENT SNAPSHOT"))

# Ensures:
# 1. All workers see same data version
# 2. Non-blocking reads (MVCC)
# 3. No phantom reads
```

**Query Pattern:**
```sql
SELECT * FROM orders 
WHERE order_id >= :start AND order_id < :end
ORDER BY order_id
```

---

#### **ColumnStore Optimization**
```python
# Detect partitions
partitions = self._get_table_partitions(entity)

# Increase chunk size (ColumnStore loves batch scans)
chunk_size = 500_000

# Apply columnar scan hint
query = "SELECT /*+ COLUMNAR_SCAN */ * FROM table"
```

**Benefits:**
- Leverages columnar compression
- Minimizes decompression overhead
- Partition-aware parallelism

---

#### **MyISAM Safety Protocol**
```python
# Check for active locks
SHOW OPEN TABLES WHERE `Database` = :db AND `Table` = :table AND In_use > 0

# If locked: ABORT with error
# If clear: Proceed with LOW_PRIORITY
```

**Query Pattern:**
```sql
SELECT LOW_PRIORITY * FROM legacy_table LIMIT 50000 OFFSET 0
```

**Production Warning:**
```
⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️
⚠️  MyISAM: Extraction will LOCK table
⚠️  Other users will be BLOCKED during extraction
⚠️  Recommend: Extract during off-peak hours
⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️
```

---

## 7. Security & Data Privacy

### 7.1 Credential Management

**Multi-Tier Resolution:**
```python
1. Secret Handler (preferred)   - Integrates with AWS Secrets Manager, Vault, etc.
2. Environment Variables         - ${MARIADB_PASSWORD}
3. Configuration File            - Encrypted at rest (user responsibility)
4. Interactive Prompt            - getpass.getpass() for dev environments
```

**Never Logged:**
- Passwords
- Connection strings with embedded credentials
- SSL certificate contents

### 7.2 Network & Access Controls

**SSL/TLS Support:**
```python
connect_args = {
    'connect_timeout': 10,
    'ssl': {
        'ca': '/path/to/ca-cert.pem',
        'check_hostname': True
    }
}
```

**Connection String Security:**
```python
# Obfuscated logging
logger.info(f"Connected to {host}:{port}/{database} as {user}@***")
```

**Authentication Methods Supported:**
- `mysql_native_password`
- `caching_sha2_password`
- `sha256_password`
- SSL certificate-based auth

### 7.3 Data Integrity & Auditability

**Metadata Lineage:**
Every extraction records:
- Source database version
- Storage engine type
- Schema snapshot at extraction time
- Exact SQL queries executed
- Execution timestamps (start, end)
- Row counts per chunk
- Worker assignments

**Immutability:**
- Bronze layer files are never modified post-creation
- Run IDs prevent accidental overwrites
- Metadata enables point-in-time reconstruction

**Validation:**
```python
# Post-extraction checks:
1. Row count verification (source vs. Bronze)
2. Schema consistency across chunks
3. No null primary keys in output
4. Metadata file completeness
```

---

## 8. Performance & Metrics

### 8.1 Key Performance Indicators

**Baseline (Pre-Optimization):**
| Metric | 100k Rows | 1M Rows | 10M Rows |
|--------|-----------|---------|----------|
| Runtime | 8.3s | 92.4s | 15.2 min |
| Throughput | 12k rows/s | 10.8k rows/s | 11k rows/s |
| Peak RAM | 2.1 GB | 6.8 GB | **18 GB (crashed)** |
| Worker Balance | N/A (serial) | N/A (serial) | N/A |

**Optimized (Current Version):**
| Metric | 100k Rows | 1M Rows | 10M Rows |
|--------|-----------|---------|----------|
| Runtime | 3.2s | 37.1s | 6.1 min |
| Throughput | 31k rows/s | 27k rows/s | 27.3k rows/s |
| Peak RAM | 0.9 GB | 3.2 GB | 8.4 GB |
| Worker Balance (σ) | N/A | 2.1s | 4.3s |

**Improvements:**
- **2.5× faster** end-to-end runtime
- **2.5× higher** sustained throughput
- **53% lower** peak memory usage
- **Zero** out-of-memory crashes

### 8.2 Optimization Impact Analysis

#### **OPTIMIZATION 1: Quantile Sampling**

**Test Scenario:** 1M row table with 40% deleted rows (sparse PKs)

| Metric | Range Splitting | Quantile Sampling | Improvement |
|--------|-----------------|-------------------|-------------|
| Worker 1 Completion | 8.2s | 9.1s | — |
| Worker 2 Completion | 1.3s | 9.3s | Balanced |
| Worker 3 Completion | 1.1s | 9.0s | Balanced |
| Worker 4 Completion | 7.9s | 9.2s | — |
| **Total Runtime** | **16.4s** | **9.3s** | **43% faster** |
| Std. Dev. | 3.7s | 0.13s | **96% more uniform** |

**Conclusion:** Eliminates idle time, nearly perfect load distribution.

---

#### **OPTIMIZATION 2: PyArrow Backend**

**Test Scenario:** 500k rows, mixed types (int, string, JSON)

| Metric | Pandas Default | PyArrow | Improvement |
|--------|---------------|---------|-------------|
| Read Time | 11.2s | 10.8s | 4% (marginal) |
| Memory Peak | 3.8 GB | 2.1 GB | **45% reduction** |
| Parquet Write | 6.7s | 2.1s | **3.2× faster** |
| **Total Pipeline** | **17.9s** | **12.9s** | **28% faster** |

**Conclusion:** Massive memory savings + faster serialization.

---

#### **OPTIMIZATION 3: Adaptive Throttling**

**Test Scenario:** Shared production database (simulated 60 active threads)

| Metric | No Throttling | With Throttling | Impact |
|--------|--------------|-----------------|---------|
| Connector Throughput | 45k rows/s | 32k rows/s | 29% slower |
| DB Thread Count (Peak) | 78 threads | 54 threads | **31% lower** |
| Production Query P95 | 340ms | 120ms | **65% faster** |
| **Incidents** | 2 timeouts | 0 | **Zero impact** |

**Conclusion:** Trades 29% throughput for zero production incidents.

---

## 9. Project Timeline

```
┌─────────────────────────────────────────────────────────────────┐
│ Phase 1: Foundation (Weeks 1-2)                                 │
│  ├─ Basic connection + credential validation                    │
│  ├─ Storage engine detection                                    │
│  ├─ Simple serial extraction                                    │
│  └─ Parquet output + metadata                                   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ Phase 2: Engine Awareness (Weeks 3-4)                           │
│  ├─ Capability matrix implementation                            │
│  ├─ InnoDB consistent snapshot                                  │
│  ├─ MyISAM safety checks                                        │
│  ├─ Risk-based warnings                                         │
│  └─ Engine-specific SQL hints                                   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ Phase 3: Parallelization (Weeks 5-6)                            │
│  ├─ ThreadPoolExecutor integration                              │
│  ├─ Primary key range splitting                                 │
│  ├─ Bounded queue for backpressure                              │
│  ├─ Connection pooling (SQLAlchemy)                             │
│  └─ Auto-tuning (ExtractionOptimizer)                           │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ Phase 4: Advanced Optimizations (Weeks 7-8) [CURRENT]           │
│  ├─ Quantile sampling for smart chunking                        │
│  ├─ PyArrow backend integration                                 │
│  ├─ Adaptive throttling with health monitoring                  │
│  ├─ ColumnStore partition awareness                             │
│  └─ Comprehensive testing + benchmarking                        │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ Phase 5: Production Hardening (Weeks 9-10) [NEXT]               │
│  ├─ CDC (Change Data Capture) support                           │
│  ├─ Incremental extraction with watermarks                      │
│  ├─ Compression strategies (Zstandard)                          │
│  ├─ Monitoring dashboard integration                            │
│  └─ SLA-based throttling policies                               │
└─────────────────────────────────────────────────────────────────┘
```

---

## 10. Conclusion & Roadmap

### Current State

The SyniqAI MariaDB Connector represents a **production-grade, storage-engine-aware** data ingestion framework that combines intelligent automation with explicit safety guarantees. Through three breakthrough optimizations—quantile sampling, PyArrow integration, and adaptive throttling—the system achieves:

✅ **2.5× performance improvement** over baseline  
✅ **50% memory footprint reduction**  
✅ **Zero production incidents** through adaptive throttling  
✅ **Engine-aware safety** preventing table locks and data inconsistencies

### Future Roadmap

**Q2 2026: CDC & Incremental Ingestion**
- Watermark-based incremental extraction
- Change Data Capture (binlog parsing)
- Upsert/merge logic for incremental updates
- Slowly Changing Dimension (SCD) support

**Q3 2026: Advanced Compression & Storage**
- Zstandard compression (2× better than Snappy)
- Delta encoding for sorted columns
- Partition-aware output (Hive-style partitioning)
- Metadata-driven schema evolution

**Q4 2026: Observability & Governance**
- Prometheus metrics exporter
- Grafana dashboard integration
- Data quality checks (null rates, value distributions)
- PII detection and masking

**2027: Multi-Source Federation**
- Cross-database joins (MariaDB + PostgreSQL)
- Unified lakehouse format (Delta Lake, Iceberg)
- Distributed execution (Ray, Dask)

---

## Appendix A: Environmental Setup

### A.1 System Requirements

**Operating System:**
- Linux (Ubuntu 20.04+, RHEL 8+)
- Windows 10/11
- macOS 12+ (Monterey)

**Runtime:**
- Python 3.10 or higher
- pip 22.0+

**Hardware (Minimum):**
- **RAM**: 4 GB (8 GB recommended)
- **CPU**: 4 logical cores (8+ recommended)
- **Disk**: SSD with 50 GB free space
- **Network**: 100 Mbps for remote databases

**Hardware (Production):**
- **RAM**: 16 GB+ (32 GB for 10M+ row tables)
- **CPU**: 16+ cores for maximum parallelism
- **Disk**: NVMe SSD (3000+ MB/s write throughput)
- **Network**: 1 Gbps+ for high-throughput extraction

### A.2 Python Dependencies

**Installation:**
```bash
pip install pandas>=2.0.0 sqlalchemy>=2.0.0 pymysql>=1.0.0 \
            pyarrow>=12.0.0 psutil>=5.9.0
```

**Dependency Matrix:**

| Package | Version | Purpose |
|---------|---------|---------|
| `pandas` | ≥2.0.0 | DataFrame operations (PyArrow backend required) |
| `sqlalchemy` | ≥2.0.0 | Connection pooling, database abstraction |
| `pymysql` | ≥1.0.0 | Pure-Python MariaDB driver |
| `pyarrow` | ≥12.0.0 | Columnar memory layout, Parquet I/O |
| `psutil` | ≥5.9.0 | System resource monitoring |

**Virtual Environment (Recommended):**
```bash
python -m venv mariadb_connector_env
source mariadb_connector_env/bin/activate  # Linux/Mac
# OR
mariadb_connector_env\Scripts\activate     # Windows

pip install -r requirements.txt
```

### A.3 Environment Variable Configuration

**Required Variables:**
```bash
export MARIADB_HOST="192.168.2.114"
export MARIADB_PORT="3300"
export MARIADB_DATABASE="production_db"
export MARIADB_USER="etl_user"
export MARIADB_PASSWORD="secure_password_here"
```

**Windows (PowerShell):**
```powershell
$env:MARIADB_HOST = "192.168.2.114"
$env:MARIADB_PORT = "3300"
$env:MARIADB_DATABASE = "production_db"
$env:MARIADB_USER = "etl_user"
$env:MARIADB_PASSWORD = "secure_password_here"
```

**SSL Configuration (Optional):**
```bash
export MARIADB_SSL_CA="/path/to/ca-cert.pem"
export MARIADB_SSL_CERT="/path/to/client-cert.pem"
export MARIADB_SSL_KEY="/path/to/client-key.pem"
```

### A.4 MariaDB Server Configuration

**Enable Remote Connections:**

1. **Edit `my.cnf` or `mariadb.conf.d/50-server.cnf`:**
```ini
[mysqld]
bind-address = 0.0.0.0
port = 3306
max_connections = 200
```

2. **Create ETL User:**
```sql
CREATE USER 'etl_user'@'%' IDENTIFIED BY 'secure_password_here';
GRANT SELECT ON production_db.* TO 'etl_user'@'%';
FLUSH PRIVILEGES;
```

3. **Restart MariaDB:**
```bash
sudo systemctl restart mariadb
```

**Firewall Rules:**
```bash
# Ubuntu/Debian (ufw)
sudo ufw allow 3306/tcp

# RHEL/CentOS (firewalld)
sudo firewall-cmd --permanent --add-port=3306/tcp
sudo firewall-cmd --reload
```

### A.5 SSL/TLS Setup (Production)

**Generate Certificates:**
```bash
# On MariaDB server
sudo mysql_ssl_rsa_setup --uid=mysql

# Verify
mysql -u root -p -e "SHOW VARIABLES LIKE 'have_ssl';"
```

**Client Configuration:**
```json
{
  "connection_config": {
    "host": "db.example.com",
    "port": 3306,
    "ssl_ca": "/etc/ssl/certs/ca-cert.pem",
    "ssl_verify_cert": true
  }
}
```

### A.6 Configuration Deployment

**Directory Structure:**
```
project_root/
├── main.py
├── mariadb_connector.py
├── base_connector.py
├── parquet_sink.py
├── config_mariadb.json           # Configuration file
├── requirements.txt
└── bronze_layer/                  # Output directory
    └── (auto-created)
```

**Sample `config_mariadb.json`:**
```json
{
  "source_type": "mariadb",
  "connection_config": {
    "host": "${MARIADB_HOST}",
    "port": 3300,
    "database": "production_db",
    "user": "${MARIADB_USER}",
    "password": "${MARIADB_PASSWORD}"
  },
  "extraction_request": {
    "entity": "user_transactions",
    "mode": "full",
    "enable_parallel": true,
    "flatten_json": {}
  }
}
```

### A.7 Execution

**Run Extraction:**
```bash
python main.py --config config_mariadb.json
```

**Expected Output:**
```
🚀 MariaDB Connector - Production Version with Auto-Tuning
============================================================
✅ Connected to MariaDB 10.11.6-MariaDB (Pool: 20, REPEATABLE READ)
   🔒 SSL Enabled: TLS_AES_256_GCM_SHA384
✅ All required permissions verified

🧐 Table 'user_transactions': Engine=InnoDB | PK=txn_id | Risk=LOW
   📊 Estimated rows: ~1,045,320

============================================================
🧮 EXTRACTION OPTIMIZER
============================================================
   Table: user_transactions
   Engine: INNODB
   Rows: 1,045,320
   Chunk Size: 50,000 rows
   Workers: 8 parallel
   Est. Time: 38-42 seconds
   System: 16 cores, 12.3 GB RAM
============================================================

   📊 Calculating quantile boundaries (sampling 9 points from 1,045,320 rows)...
   ✅ Quantile boundaries: [1, 130665, 261330]...[914655, 1045320] (showing first/last 3)

⚡ PARALLEL MODE (QUANTILE): 8 workers | PK: txn_id
   Range: 1→1045320 (using 9 boundaries)

📦 Chunk: quantile-0 | Worker: ThreadPoolExecutor-0_0
   Engine: InnoDB | Risk: low
   Rows: 130,665 | Strategy: parallel

[... 7 more chunks ...]

============================================================
✅ COMPLETE | Total Rows: 1,045,320
✅ Execution Time: 37.2 seconds
✅ Throughput: 28,107 rows/second
============================================================

📁 Output: bronze_layer/user_transactions/20260212_143052/
   ├─ data_00001.parquet (42.3 MB)
   ├─ data_00002.parquet (41.8 MB)
   └─ metadata.json (3.2 KB)
```

### A.8 Output Verification

**Check Data Files:**
```bash
ls -lh bronze_layer/user_transactions/20260212_143052/
```

**Validate Metadata:**
```bash
cat bronze_layer/user_transactions/20260212_143052/metadata.json | jq .
```

**Expected Fields:**
```json
{
  "source_type": "mariadb",
  "entity": "user_transactions",
  "storage_engine": "InnoDB",
  "optimization_used": "quantile_sampling",
  "total_rows": 1045320,
  "execution_time_seconds": 37.2,
  "schema_snapshot": [...]
}
```

### A.9 Troubleshooting

**Issue: "Import 'pymysql' could not be resolved"**
```bash
pip install pymysql
```

**Issue: "Access denied for user 'etl_user'@'host'"**
```sql
-- On MariaDB server
GRANT SELECT ON database.* TO 'etl_user'@'%';
FLUSH PRIVILEGES;
```

**Issue: "Table is locked"**
```
⚠️ MyISAM engine detected - extraction may lock table
```
**Solution:** Run during maintenance window or convert to InnoDB:
```sql
ALTER TABLE table_name ENGINE=InnoDB;
```

**Issue: "Out of memory"**
**Solution:** System adapts automatically, but verify:
```bash
free -h  # Check available RAM
# If <4 GB, connector will reduce chunk sizes automatically
```

---

## Appendix B: Storage Engine Decision Tree

```
┌─────────────────────────────────────────────────────────────────┐
│ START: Detect Storage Engine                                    │
└────────────────────────────┬────────────────────────────────────┘
                             ↓
                    ┌────────────────┐
                    │ Engine Type?   │
                    └────────┬───────┘
                             |
        ┌────────────────────┼────────────────────┐
        ↓                    ↓                    ↓
   ┌─────────┐        ┌─────────────┐      ┌──────────┐
   │ InnoDB  │        │ ColumnStore │      │ MyISAM   │
   └────┬────┘        └──────┬──────┘      └────┬─────┘
        │                    │                   │
        ↓                    ↓                   ↓
  ┌─────────────┐    ┌──────────────┐    ┌─────────────────┐
  │ ✅ PARALLEL │    │ ✅ PARALLEL  │    │ ❌ SERIAL ONLY  │
  │ Strategy:   │    │ Strategy:    │    │ Strategy:       │
  │ • Quantile  │    │ • Partition  │    │ • LOW_PRIORITY  │
  │   sampling  │    │   aware      │    │ • Check locks   │
  │ • Snapshot  │    │ • Large      │    │ • Off-peak warn │
  │   per worker│    │   chunks     │    │                 │
  │ • Throttle  │    │ • No TX      │    │ Risk: 🔴 HIGH   │
  │             │    │              │    │                 │
  │ Risk: 🟢 LOW│    │ Risk: 🟢 LOW │    └─────────────────┘
  └─────────────┘    └──────────────┘
```

**Decision Criteria:**

| Condition | Action |
|-----------|--------|
| Engine = InnoDB + Integer PK | → Parallel quantile extraction |
| Engine = ColumnStore | → Parallel partition-aware extraction |
| Engine = MyISAM/Aria | → Serial + lock check + warning |
| Table < 1000 rows | → Serial (avoid thread overhead) |
| Available RAM < 4 GB | → Reduce chunk size |
| DB Threads > 50 | → Apply throttling |

---

**Document End**

---

**Version History:**
- v2.0 (Feb 2026): Advanced optimizations, engine awareness, production hardening
- v1.0 (Jan 2026): Initial parallel extraction, basic connection pooling

**Authors:** SyniqAI Data Engineering Team  
**Maintained By:** Platform Infrastructure Group  
**Last Updated:** February 12, 2026
