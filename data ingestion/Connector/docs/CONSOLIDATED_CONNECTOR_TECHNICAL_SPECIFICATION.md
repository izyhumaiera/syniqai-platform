# SyniqAI Data Ingestion System
## Consolidated Connector Technical Specification Document
### Enterprise Multi-Source Data Integration Platform

**Version:** 1.0  
**Date:** February 16, 2026  
**Status:** Production-Ready  
**Document Type:** Master Reference

---

## Executive Summary

This document serves as the **definitive technical reference** for the SyniqAI Data Ingestion System's multi-source connector framework. It consolidates specifications for all supported and planned data sources into a unified architectural blueprint, providing engineering teams with a comprehensive guide for implementation, optimization, and troubleshooting.

**Supported Connectors:**
- ✅ **PostgreSQL** - Production-ready with parallel extraction
- ✅ **MariaDB (Self-Hosted)** - Storage engine-aware with advanced optimizations
- ✅ **MariaDB Cloud (SkySQL)** - Cloud-native with security-first design
- 🔜 **MongoDB** - Document-oriented NoSQL (planned)
- 🔜 **AWS S3** - Object storage ingestion (planned)

**System Overview:**
```
┌─────────────────────────────────────────────────────────────────┐
│              SyniqAI Bronze Layer - Ingestion Platform          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ PostgreSQL   │  │   MariaDB    │  │ MariaDB Cloud│         │
│  │  Connector   │  │  Connector   │  │  Connector   │         │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘         │
│         │                  │                  │                  │
│         └──────────────────┴──────────────────┘                 │
│                           │                                      │
│                  ┌────────▼────────┐                            │
│                  │  Base Connector │                            │
│                  │   (Abstract)    │                            │
│                  └────────┬────────┘                            │
│                           │                                      │
│         ┌─────────────────┴─────────────────┐                  │
│         │                                     │                  │
│  ┌──────▼────────┐                  ┌────────▼──────┐          │
│  │    Parquet    │                  │   Metadata    │          │
│  │     Sink      │                  │   Generator   │          │
│  └───────────────┘                  └───────────────┘          │
│                                                                  │
│  Output: bronze_layer/                                          │
│    ├─ {table}/                                                  │
│    │   └─ {timestamp}/                                          │
│    │       ├─ data.parquet                                      │
│    │       └─ metadata.json                                     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Table of Contents

1. [Introduction](#1-introduction)
   - 1.1 [System Purpose & Scope](#11-system-purpose--scope)
   - 1.2 [Architectural Philosophy](#12-architectural-philosophy)
   - 1.3 [Glossary & Terminology](#13-glossary--terminology)

2. [Unified System Architecture](#2-unified-system-architecture)
   - 2.1 [Common Architecture Patterns](#21-common-architecture-patterns)
   - 2.2 [Component Hierarchy](#22-component-hierarchy)
   - 2.3 [Data Flow Pipeline](#23-data-flow-pipeline)
   - 2.4 [Bronze Layer Specification](#24-bronze-layer-specification)

3. [Connector Specifications](#3-connector-specifications)
   - 3.1 [PostgreSQL Connector](#31-postgresql-connector)
   - 3.2 [MariaDB Self-Hosted Connector](#32-mariadb-self-hosted-connector)
   - 3.3 [MariaDB Cloud (SkySQL) Connector](#33-mariadb-cloud-skysql-connector)
   - 3.4 [MongoDB Connector (Planned)](#34-mongodb-connector-planned)
   - 3.5 [AWS S3 Connector (Planned)](#35-aws-s3-connector-planned)

4. [Common Features & Optimizations](#4-common-features--optimizations)
   - 4.1 [Intelligent Auto-Tuning](#41-intelligent-auto-tuning)
   - 4.2 [PyArrow Backend Integration](#42-pyarrow-backend-integration)
   - 4.3 [Parallel Extraction Framework](#43-parallel-extraction-framework)
   - 4.4 [Schema Handling Strategy](#44-schema-handling-strategy)

5. [Technical Implementation](#5-technical-implementation)
   - 5.1 [Technology Stack](#51-technology-stack)
   - 5.2 [Base Connector Interface](#52-base-connector-interface)
   - 5.3 [Extraction Optimizer](#53-extraction-optimizer)
   - 5.4 [Connection Management](#54-connection-management)

6. [Security & Compliance](#6-security--compliance)
   - 6.1 [Credential Management](#61-credential-management)
   - 6.2 [Network Security](#62-network-security)
   - 6.3 [Access Control Models](#63-access-control-models)
   - 6.4 [Audit Trail & Compliance](#64-audit-trail--compliance)

7. [Performance Benchmarks](#7-performance-benchmarks)
   - 7.1 [Connector Comparison Matrix](#71-connector-comparison-matrix)
   - 7.2 [Optimization Impact Analysis](#72-optimization-impact-analysis)
   - 7.3 [Resource Utilization](#73-resource-utilization)

8. [GUI Integration](#8-gui-integration)
   - 8.1 [Unified Interface Design](#81-unified-interface-design)
   - 8.2 [Multi-Connector Workflow](#82-multi-connector-workflow)
   - 8.3 [User Experience Patterns](#83-user-experience-patterns)

9. [Operational Guidelines](#9-operational-guidelines)
   - 9.1 [Deployment Procedures](#91-deployment-procedures)
   - 9.2 [Monitoring & Alerting](#92-monitoring--alerting)
   - 9.3 [Troubleshooting Guide](#93-troubleshooting-guide)

10. [Roadmap & Future Extensions](#10-roadmap--future-extensions)

11. [Appendices](#11-appendices)
    - Appendix A: Configuration Examples
    - Appendix B: API Reference
    - Appendix C: Error Code Index
    - Appendix D: Performance Tuning Guide

---

## 1. Introduction

### 1.1 System Purpose & Scope

The **SyniqAI Data Ingestion System** is an enterprise-grade, multi-source data integration platform designed to extract, transform, and persist data from diverse data sources into a unified Bronze Layer. Unlike generic ETL tools, this system is architected with source-specific intelligence, enabling optimal extraction strategies tailored to each data source's unique characteristics.

**Core Objectives:**

1. **Multi-Source Unification**
   - Single platform supporting relational (PostgreSQL, MariaDB), NoSQL (MongoDB), and object storage (S3)
   - Consistent interface abstracts source-specific complexities
   - Unified metadata model enables cross-source lineage tracking

2. **Production-Grade Reliability**
   - Network resilience with automatic retry logic
   - Memory-safe extraction prevents OOM failures
   - Graceful degradation under resource constraints

3. **Performance Optimization**
   - Intelligent auto-tuning based on system resources
   - Source-specific optimizations (storage engines, index awareness, network latency)
   - Parallel extraction where safe and beneficial

4. **Security & Compliance**
   - Principle of least privilege (read-only access patterns)
   - SSL/TLS encryption for cloud connectors
   - Comprehensive audit trails for regulatory compliance

5. **Operational Excellence**
   - Unified GUI for all connectors
   - Extensive logging and monitoring
   - Self-documenting metadata with full lineage

**Scope of This Document:**

This document covers:
✅ Architectural design patterns common to all connectors  
✅ Detailed specifications for each implemented connector  
✅ Performance characteristics and optimization strategies  
✅ Security models and compliance mechanisms  
✅ Operational guidelines and troubleshooting  
✅ Future roadmap with MongoDB and AWS S3 placeholders

This document does **not** cover:
❌ Silver/Gold layer transformations (separate system)  
❌ Real-time streaming ingestion (batch-focused)  
❌ Schema registry management (handled externally)  
❌ Data quality rules engine (separate component)

### 1.2 Architectural Philosophy

The SyniqAI connector framework is built on six foundational principles:

#### 1. **Source-Aware Intelligence**

Each connector is purpose-built with deep knowledge of its target system:

| Principle | PostgreSQL Example | MariaDB Example | Cloud Example |
|-----------|-------------------|-----------------|---------------|
| **Parallelism** | Table partitioning awareness | Storage engine detection (InnoDB vs MyISAM) | Serverless connection limits |
| **Consistency** | Snapshot isolation | MVCC consistent snapshots | Cross-region latency |
| **Optimization** | Index-aware chunking | Quantile sampling for sparse PKs | Large chunks to reduce roundtrips |

```python
# Bad: Generic one-size-fits-all approach
def extract(table):
    return pd.read_sql(f"SELECT * FROM {table}", conn)

# Good: Source-aware intelligence
def extract(table):
    if source == "mariadb":
        engine = detect_storage_engine(table)
        if engine == "MyISAM":
            # Force serial to prevent table locks
            return serial_extract(table)
        elif engine == "InnoDB":
            # Parallel with consistent snapshot
            return parallel_extract_with_snapshot(table)
```

#### 2. **Fail-Fast with Rich Context**

Errors are explicit, immediate, and actionable:

```python
# Bad: Silent failure or generic error
try:
    conn = connect(config)
except Exception as e:
    logger.error(f"Connection failed: {e}")

# Good: Rich context with troubleshooting steps
try:
    conn = connect(config)
except SSLError as e:
    logger.error(
        f"❌ SSL Certificate Validation Failed\n"
        f"   Certificate: {config['ssl_ca']}\n"
        f"   Error: {e}\n\n"
        f"🔧 TROUBLESHOOTING:\n"
        f"   1. Verify certificate path exists\n"
        f"   2. Check certificate not expired: openssl x509 -in cert.pem -noout -dates\n"
        f"   3. Re-download from: {CERT_DOWNLOAD_URL}\n"
    )
    raise
```

#### 3. **Memory Safety by Design**

The system proactively prevents out-of-memory conditions:

```python
# Adaptive chunk sizing based on available RAM
available_gb = psutil.virtual_memory().available / (1024**3)

if available_gb < 2.0:
    chunk_size = 10_000  # Conservative for low-memory systems
elif available_gb < 8.0:
    chunk_size = 50_000  # Standard
else:
    chunk_size = 100_000  # Aggressive for high-memory systems

logger.info(f"💾 Available RAM: {available_gb:.1f}GB → Chunk size: {chunk_size:,}")
```

#### 4. **Deterministic & Reproducible**

Every extraction produces identical results given the same inputs:

- **Versioned Outputs**: Each run gets unique timestamp-based Run ID
- **Schema Snapshots**: Captured at extraction start, persisted in metadata
- **Idempotent**: Re-running same extraction produces identical data (for full mode)

#### 5. **Production-Safe Extraction**

Connectors never overwhelm source systems:

| Safety Mechanism | PostgreSQL | MariaDB | MariaDB Cloud |
|------------------|-----------|---------|---------------|
| **Connection Pooling** | Size: 20, Overflow: 30 | Size: 20, Overflow: 10 | Size: 3, Overflow: 2 |
| **Adaptive Throttling** | N/A (local) | DB health monitoring | N/A (managed service) |
| **Parallelism Limits** | Up to 16 workers | Up to 16 (InnoDB only) | Max 2 workers (serverless) |
| **Table Locking** | N/A (MVCC) | MyISAM detection + warning | N/A (InnoDB only) |

#### 6. **Schema Preservation Over Evolution**

The Bronze Layer maintains **source fidelity**:

```python
# Bronze Layer: Preserve source truth
{
    "user_metadata": '{"user_id": 123, "preferences": {...}}',  # JSON as string
    "tags": ["premium", "verified"],                           # Array preserved
    "balance": "12345.67"                                       # Decimal as string (optional)
}

# Silver Layer: Transform for analytics (separate system)
{
    "user_id": 123,                    # Extracted from JSON
    "is_premium": true,                # Derived from tags
    "balance_usd": 12345.67           # Parsed to float
}
```

### 1.3 Glossary & Terminology

| Term | Definition |
|------|------------|
| **Bronze Layer** | Raw, immutable storage tier preserving source data exactly as extracted |
| **Connector** | Source-specific extraction module (PostgreSQL, MariaDB, etc.) |
| **Run ID** | Unique timestamp identifier for each extraction execution (format: `YYYYmmdd_HHMMSS`) |
| **Chunk** | Bounded batch of rows extracted in a single database query (e.g., 50,000 rows) |
| **Worker** | Parallel extraction thread processing a specific data range |
| **Quantile Sampling** | Statistical technique to determine data distribution boundaries for even workload distribution |
| **PyArrow** | Apache Arrow's Python library providing columnar memory layout (30-50% RAM reduction) |
| **MVCC** | Multi-Version Concurrency Control; non-blocking read mechanism in PostgreSQL/InnoDB |
| **Parquet** | Columnar, compressed file format optimized for analytical queries |
| **Metadata** | JSON file accompanying each extraction with schema, lineage, and execution statistics |
| **Extraction Optimizer** | Component that auto-calculates optimal chunk size and worker count |
| **Storage Engine** | MariaDB's pluggable backend (InnoDB, MyISAM, ColumnStore, etc.) |
| **Serverless** | Auto-scaling cloud database infrastructure (e.g., MariaDB SkySQL) |
| **SSL/TLS** | Secure Sockets Layer / Transport Layer Security for encrypted connections |
| **Read-Only User** | Database account with SELECT-only permissions (principle of least privilege) |
| **Snapshot Isolation** | Transaction isolation level providing point-in-time consistent view |
| **Connection Pool** | Reusable database connections avoiding TCP handshake overhead |
| **Exponential Backoff** | Retry strategy where delay doubles each attempt (2s, 4s, 8s, ...) |
| **Schema Drift** | Changes to source table schema over time (columns added/removed/renamed) |
| **Watermark** | Column value (timestamp/ID) used for incremental extraction tracking |
| **Service Account** | Non-human database user created for automated systems |

---

## 2. Unified System Architecture

### 2.1 Common Architecture Patterns

All connectors in the SyniqAI system adhere to a unified architectural pattern, ensuring consistency, maintainability, and extensibility.

#### 2.1.1 Three-Layer Extraction Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│ Layer 1: Orchestration & Planning                               │
│  • Configuration validation                                      │
│  • Credential resolution (SecretManager)                         │
│  • Resource assessment (RAM, CPU)                                │
│  • Extraction strategy selection (parallel vs serial)           │
│  • Parameter optimization (chunk size, workers)                  │
└────────────────────────────┬────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│ Layer 2: Extraction Execution                                    │
│  • Connection management (pooling)                               │
│  • Source-specific optimizations                                 │
│  • Data streaming (memory-efficient)                             │
│  • Error handling & retry logic                                  │
│  • Schema capture & validation                                   │
└────────────────────────────┬────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│ Layer 3: Persistence & Metadata                                  │
│  • Parquet serialization (Snappy compression)                    │
│  • Metadata generation (lineage, schema, stats)                  │
│  • Atomic writes (temp file + rename)                            │
│  • Output validation                                             │
└─────────────────────────────────────────────────────────────────┘
```

#### 2.1.2 Producer-Consumer Pattern

All connectors implement a **bounded queue** producer-consumer model:

```python
┌─────────────────────────────────────────────────────────────────┐
│                 PRODUCER (Extraction Workers)                    │
│                                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │ Worker 1 │  │ Worker 2 │  │ Worker 3 │  │ Worker N │       │
│  │ Range A  │  │ Range B  │  │ Range C  │  │ Range N  │       │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘       │
│       │             │             │             │               │
│       └─────────────┴─────────────┴─────────────┘               │
│                           ↓                                      │
│              ┌────────────────────────┐                          │
│              │   Bounded Queue        │                          │
│              │   maxsize = workers×2  │                          │
│              │   (Backpressure)       │                          │
│              └────────────┬───────────┘                          │
│                           ↓                                      │
│                 CONSUMER (Writer Thread)                         │
│                                                                  │
│                  ┌─────────────────┐                             │
│                  │  Parquet Writer │                             │
│                  │  • Sanitize     │                             │
│                  │  • Serialize    │                             │
│                  │  • Write to disk│                             │
│                  └─────────────────┘                             │
└─────────────────────────────────────────────────────────────────┘
```

**Benefits:**
- **Backpressure**: Queue size limits prevent memory exhaustion if disk I/O is slow
- **Decoupling**: Database I/O (network-bound) runs independently from disk I/O (storage-bound)
- **Fault Isolation**: Worker failure doesn't crash entire extraction

#### 2.1.3 Adaptive Parameter Optimization

The **ExtractionOptimizer** dynamically calculates optimal parameters:

```python
class ExtractionOptimizer:
    def calculate_optimal_params(
        self,
        row_count: int,
        avg_row_size_bytes: int = 1024,
        is_remote: bool = False,
        engine_type: str = "default"
    ) -> Tuple[int, int]:
        """
        Returns: (optimal_chunk_size, optimal_num_workers)
        
        Inputs:
          • row_count: Table size from information_schema
          • avg_row_size_bytes: Average row width (user hint or default)
          • is_remote: True if database on different host (network latency)
          • engine_type: Storage engine (for MariaDB-specific logic)
        
        Algorithm:
          1. Calculate base chunk size (100MB / row_size)
          2. Apply table-size scaling:
             - < 1,000 rows: entire table (no chunking)
             - < 10,000 rows: 1,000 rows/chunk
             - < 100,000 rows: 10,000 rows/chunk
             - < 1M rows: 50,000 rows/chunk
             - ≥ 1M rows: 100,000 rows/chunk
          
          3. Calculate max workers by:
             a) RAM constraint: (available_RAM × 0.5) / chunk_memory
             b) CPU constraint: CPU core count
             c) Efficiency: sqrt(total_chunks) + 1
             → Take minimum of all three
          
          4. Apply penalties:
             - Remote database: workers × 0.75 (network latency)
             - Small table (< 1,000 rows): workers = 1 (avoid overhead)
          
          5. Cap at global maximum (default: 16 workers)
        """
        # Implementation in each connector
```

**Example Output:**

| Table Size | Available RAM | CPU Cores | Remote? | → Chunk Size | → Workers |
|------------|--------------|-----------|---------|-------------|----------|
| 500 rows | 8 GB | 8 | No | 500 | 1 |
| 50,000 rows | 4 GB | 4 | Yes | 10,000 | 2 |
| 500,000 rows | 16 GB | 8 | No | 50,000 | 8 |
| 5,000,000 rows | 8 GB | 8 | Yes | 100,000 | 4 |

### 2.2 Component Hierarchy

```
┌──────────────────────────────────────────────────────────────────┐
│                      Base Components (Abstract)                   │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  BaseConnector (Abstract Class)                                   │
│    ├─ connect() : void                                           │
│    ├─ validate_credentials() : void                              │
│    ├─ extract(plan) : Iterator[Dict]                             │
│    ├─ close() : void                                             │
│    └─ _sanitize_complex_types(df) : DataFrame                    │
│                                                                   │
│  ExtractionOptimizer                                              │
│    └─ calculate_optimal_params(...) : (chunk_size, workers)      │
│                                                                   │
│  ParquetSink                                                      │
│    ├─ write_batch(df, metadata) : void                           │
│    └─ finalize(run_id) : void                                    │
│                                                                   │
│  SecretManager                                                    │
│    └─ resolve(config) : str                                      │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘
                              ↓ Inherits
┌──────────────────────────────────────────────────────────────────┐
│                  Connector Implementations                        │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  PostgresConnector(BaseConnector)                                 │
│    ├─ source_type = "postgres"                                   │
│    ├─ Uses psycopg2 driver                                       │
│    ├─ Parallel: Partition-based range splitting                  │
│    └─ Optimization: Server-side cursors                          │
│                                                                   │
│  MariaDBConnector(BaseConnector)                                  │
│    ├─ source_type = "mariadb"                                    │
│    ├─ Uses pymysql driver                                        │
│    ├─ Storage engine awareness (InnoDB, MyISAM, ColumnStore)     │
│    ├─ Optimization: Quantile sampling, adaptive throttling       │
│    └─ MVCC: Consistent snapshot per worker                       │
│                                                                   │
│  MariaDBCloudConnector(MariaDBConnector)                          │
│    ├─ source_type = "mariadb_cloud"                              │
│    ├─ Inherits from MariaDBConnector                             │
│    ├─ Cloud-specific: Mandatory SSL/TLS, retry logic             │
│    ├─ Optimization: Reduced parallelism (max 2 workers)          │
│    └─ Security: Read-only validation, audit trail                │
│                                                                   │
│  [FUTURE] MongoDBConnector(BaseConnector)                         │
│    ├─ source_type = "mongodb"                                    │
│    ├─ Uses pymongo driver                                        │
│    ├─ Document-oriented extraction                               │
│    └─ Optimization: Aggregation pipeline, cursor-based           │
│                                                                   │
│  [FUTURE] S3Connector(BaseConnector)                              │
│    ├─ source_type = "aws_s3"                                     │
│    ├─ Uses boto3 client                                          │
│    ├─ Object-based extraction                                    │
│    └─ Optimization: Parallel downloads with byte-range requests  │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘
```

### 2.3 Data Flow Pipeline

#### 2.3.1 End-to-End Flow

```
┌────────────────────────────────────────────────────────────────────┐
│ START: User initiates extraction via GUI or CLI                    │
└───────────────────────────────┬────────────────────────────────────┘
                                ↓
┌────────────────────────────────────────────────────────────────────┐
│ STEP 1: Configuration & Validation                                 │
│  • Load config (JSON or form inputs)                               │
│  • Resolve secrets (SecretManager)                                 │
│  • Validate required fields                                        │
│  • Select appropriate connector                                    │
└───────────────────────────────┬────────────────────────────────────┘
                                ↓
┌────────────────────────────────────────────────────────────────────┐
│ STEP 2: Connection Establishment                                   │
│  • Create connection pool (SQLAlchemy engine)                      │
│  • Test connectivity (SELECT 1)                                    │
│  • Validate credentials                                            │
│  • [Cloud only] Verify SSL/TLS certificate                         │
│  • [Cloud only] Measure network latency                            │
└───────────────────────────────┬────────────────────────────────────┘
                                ↓
┌────────────────────────────────────────────────────────────────────┐
│ STEP 3: Extraction Planning                                        │
│  • Query table metadata (row count, columns, data types)           │
│  • [MariaDB] Detect storage engine (InnoDB, MyISAM, etc.)          │
│  • Calculate optimal parameters (chunk size, workers)              │
│  • Determine strategy (parallel vs serial)                         │
│  • [Parallel] Sample quantile boundaries                           │
│  • Capture schema snapshot                                         │
└───────────────────────────────┬────────────────────────────────────┘
                                ↓
┌────────────────────────────────────────────────────────────────────┐
│ STEP 4: Data Extraction (Parallel or Serial)                       │
│                                                                     │
│  IF Parallel (InnoDB, PostgreSQL, etc.):                           │
│    ├─ Spawn N workers (ThreadPoolExecutor)                        │
│    ├─ Each worker:                                                 │
│    │   • Connect from pool                                         │
│    │   • [MVCC] START TRANSACTION WITH CONSISTENT SNAPSHOT         │
│    │   • Execute range query (quantile boundaries)                 │
│    │   • [Cloud] Retry on timeout (exponential backoff)            │
│    │   • Stream results with PyArrow backend                       │
│    │   • Sanitize complex types (JSON → string)                    │
│    │   • Put DataFrame in bounded queue                            │
│    │   • COMMIT transaction                                        │
│    └─ Main thread collects from queue                             │
│                                                                     │
│  ELSE Serial (MyISAM, small tables, etc.):                         │
│    ├─ Single connection                                            │
│    ├─ Read in chunks (server-side cursor)                         │
│    ├─ Stream with PyArrow backend                                 │
│    └─ Yield chunks directly                                        │
│                                                                     │
└───────────────────────────────┬────────────────────────────────────┘
                                ↓
┌────────────────────────────────────────────────────────────────────┐
│ STEP 5: Persistence (ParquetSink)                                  │
│  • Receive DataFrame chunks from queue                             │
│  • Validate schema consistency across chunks                       │
│  • Write to temporary Parquet file                                 │
│  • Apply Snappy compression                                        │
│  • Atomic rename (temp → final)                                    │
│  • Accumulate statistics (row counts, timing)                      │
└───────────────────────────────┬────────────────────────────────────┘
                                ↓
┌────────────────────────────────────────────────────────────────────┐
│ STEP 6: Metadata Generation                                        │
│  • Create comprehensive metadata JSON:                             │
│    - Source information (type, host, database, user)              │
│    - Extraction details (mode, timestamp, run_id)                 │
│    - Schema snapshot (columns, types)                             │
│    - Statistics (row_count, file_size, throughput)                │
│    - Optimization used (parallel/serial, chunk_size, workers)     │
│    - [Cloud] Network metrics (latency, retries, timeouts)         │
│    - [MariaDB] Storage engine, risk level                         │
│  • Write metadata.json to same directory as data.parquet          │
└───────────────────────────────┬────────────────────────────────────┘
                                ↓
┌────────────────────────────────────────────────────────────────────┐
│ STEP 7: Validation & Cleanup                                       │
│  • Verify output file exists                                       │
│  • Validate row count matches expected                             │
│  • Close all connections                                           │
│  • Dispose connection pool                                         │
│  • Log completion summary                                          │
└───────────────────────────────┬────────────────────────────────────┘
                                ↓
┌────────────────────────────────────────────────────────────────────┐
│ END: Extraction complete                                           │
│  Output:                                                           │
│    bronze_layer/                                                   │
│      └─ {table_name}/                                              │
│          └─ {YYYYmmdd_HHMMSS}/                                     │
│              ├─ data.parquet                                       │
│              └─ metadata.json                                      │
└────────────────────────────────────────────────────────────────────┘
```

### 2.4 Bronze Layer Specification

The Bronze Layer is the **raw data repository** where all extracted data is stored in its original form with minimal transformations.

#### 2.4.1 Directory Structure

```
bronze_layer/
├── {table_name_1}/
│   ├── 20260215_093045/          # Run ID: YYYYmmdd_HHMMSS
│   │   ├── data.parquet
│   │   └── metadata.json
│   ├── 20260215_150322/
│   │   ├── data.parquet
│   │   └── metadata.json
│   └── 20260216_081156/
│       ├── data.parquet
│       └── metadata.json
│
├── {table_name_2}/
│   └── 20260216_093012/
│       ├── data.parquet
│       └── metadata.json
│
└── ...
```

**Design Principles:**
1. **Immutability**: Files never modified after creation
2. **Versioning**: Each extraction gets unique timestamp-based directory
3. **Auditability**: Complete lineage from source to Bronze
4. **Idempotency**: Re-running same extraction overwrites previous (for full mode)

#### 2.4.2 Metadata Schema (Universal)

Every extraction generates a `metadata.json` file with the following structure:

```json
{
  "run_id": "20260216_093045",
  "extraction_timestamp": "2026-02-16T09:30:45.123456Z",
  
  "source": {
    "type": "postgres|mariadb|mariadb_cloud|mongodb|aws_s3",
    "host": "database.example.com",
    "database": "production_db",
    "entity": "users",
    "user": "readonly_user",
    
    // Connector-specific fields
    "storage_engine": "InnoDB",           // MariaDB only
    "ssl_enabled": true,                  // Cloud only
    "region": "us-east-1"                 // Cloud only
  },
  
  "extraction": {
    "mode": "full|incremental",
    "strategy": "parallel|serial",
    "row_count": 1045320,
    "column_count": 15,
    "batch_count": 21,
    
    "optimization": {
      "method": "quantile_sampling|range_splitting|cursor",
      "chunk_size": 50000,
      "num_workers": 8,
      "parallelism_enabled": true
    },
    
    "timing": {
      "extraction_time_seconds": 37.2,
      "throughput_rows_per_sec": 28107,
      "throughput_mb_per_sec": 12.4
    }
  },
  
  "schema_snapshot": [
    {
      "name": "user_id",
      "type": "BIGINT",
      "nullable": false,
      "primary_key": true
    },
    {
      "name": "email",
      "type": "VARCHAR(255)",
      "nullable": false
    },
    {
      "name": "metadata",
      "type": "JSON",
      "nullable": true
    }
  ],
  
  "output": {
    "data_file": "data.parquet",
    "file_format": "parquet",
    "compression": "snappy",
    "file_size_kb": 12453.2,
    "file_size_mb": 12.16
  },
  
  // Connector-specific sections
  "mariadb_metadata": {
    "storage_engine": "InnoDB",
    "engine_risk_level": "low",
    "mvcc_snapshot_used": true,
    "adaptive_throttling": {
      "enabled": true,
      "throttle_events": 3,
      "max_throttle_seconds": 5.0
    }
  },
  
  "cloud_metadata": {
    "network_metrics": {
      "average_latency_ms": 78.3,
      "min_latency_ms": 52.1,
      "max_latency_ms": 134.7,
      "retry_count": 1,
      "timeout_count": 0
    },
    "security_audit": {
      "permission_tests": {
        "SELECT": "✅ Allowed",
        "INSERT": "✅ Blocked",
        "UPDATE": "✅ Blocked",
        "DELETE": "✅ Blocked"
      }
    }
  }
}
```

---

## 3. Connector Specifications

### 3.1 PostgreSQL Connector

#### 3.1.1 Overview

**Technology:** PostgreSQL 9.6+  
**Driver:** psycopg2 (C extension for performance)  
**Status:** ✅ Production-Ready  
**Key Features:**
- Partition-aware parallel extraction
- Server-side cursors for memory efficiency
- Decimal normalization (avoids Parquet schema conflicts)
- Index-aware chunking

#### 3.1.2 Connection Configuration

```json
{
  "source_type": "postgres",
  "connection_config": {
    "host": "localhost",
    "port": 5432,
    "database": "production_db",
    "user": "readonly_user",
    "password": "${POSTGRES_PASSWORD}",
    "ssl_mode": "require"  // Optional: disable, allow, prefer, require, verify-ca, verify-full
  },
  "extraction_request": {
    "entity": "users",
    "mode": "full",
    "partition_column": "user_id",  // Integer PK for parallel extraction
    "num_workers": 8,
    "chunk_size": 50000
  }
}
```

#### 3.1.3 Architecture & Optimizations

**Connection Pooling:**
```python
SQLAlchemy Engine Configuration:
  pool_size = 20              # Base pool
  max_overflow = 30           # Dynamic overflow
  pool_pre_ping = True        # Health check before use
  pool_recycle = 3600         # Recycle connections every hour
  connect_timeout = 10        # Connection establishment timeout
```

**Parallel Extraction Strategy:**

1. **Range Splitting**: Divides primary key range into equal segments
   ```python
   min_id, max_id = get_min_max("users", "user_id")
   total_range = max_id - min_id + 1
   step = math.ceil(total_range / num_workers)
   
   # Worker assignments:
   Worker 1: user_id >= 1    AND user_id < 125001
   Worker 2: user_id >= 125001 AND user_id < 250001
   ...
   Worker 8: user_id >= 875001 AND user_id <= 1000000
   ```

2. **Server-Side Cursors**: Prevents loading entire result set into memory
   ```python
   cursor = conn.cursor(name=f"extraction_cursor_{worker_id}")
   cursor.itersize = chunk_size  # Fetch in batches
   cursor.execute(query)
   
   while True:
       rows = cursor.fetchmany(chunk_size)
       if not rows:
           break
       # Process chunk
   ```

3. **Decimal Normalization**: Converts NUMERIC/DECIMAL to DOUBLE PRECISION
   ```sql
   -- Problem: Parquet doesn't handle arbitrary precision well
   SELECT account_balance FROM transactions;  -- NUMERIC(20,4)
   
   -- Solution: Cast to double precision
   SELECT account_balance::double precision FROM transactions;
   ```

**Performance Characteristics:**

| Table Size | Workers | Chunk Size | Avg Throughput | Notes |
|------------|---------|-----------|----------------|-------|
| 100k rows | 2 | 10,000 | 31k rows/sec | Small table, low overhead |
| 1M rows | 8 | 50,000 | 27k rows/sec | Optimal parallelism |
| 10M rows | 8 | 100,000 | 27.3k rows/sec | Sustained performance |

#### 3.1.4 Error Handling

| Error Type | Detection | Response |
|------------|-----------|----------|
| **Connection Timeout** | `connect_timeout` exceeded | Immediate failure with connection details |
| **Query Timeout** | `statement_timeout` exceeded | Log slow query, abort extraction |
| **Serialization Error** | Concurrent modification | Retry with new snapshot (if MVCC) |
| **Partition Column Invalid** | Non-integer or missing | Fallback to serial extraction |
| **Out of Memory** | `psutil` detects low RAM | Reduce chunk size dynamically |

#### 3.1.5 Known Limitations

⚠️ **Partition Column Requirement**: Parallel extraction requires single integer primary key  
⚠️ **Large Object Support**: BYTEA columns may cause memory pressure  
⚠️ **Schema Changes**: Concurrent DDL may cause extraction failure

---

### 3.2 MariaDB Self-Hosted Connector

#### 3.2.1 Overview

**Technology:** MariaDB 10.5+  
**Driver:** PyMySQL (pure Python)  
**Status:** ✅ Production-Ready with Advanced Optimizations  
**Key Features:**
- Storage engine awareness (InnoDB, MyISAM, ColumnStore, Aria, Memory)
- Quantile sampling for sparse primary keys
- Adaptive throttling based on database health
- MVCC consistent snapshots (InnoDB)

#### 3.2.2 Connection Configuration

```json
{
  "source_type": "mariadb",
  "connection_config": {
    "host": "192.168.2.114",
    "port": 3300,
    "database": "production_db",
    "user": "readonly_user",
    "password": "${MARIADB_PASSWORD}",
    "ssl_ca": "/path/to/ca-cert.pem"  // Optional
  },
  "extraction_request": {
    "entity": "orders",
    "mode": "full",
    "enable_parallel": true,
    "avg_row_size": 2048  // Optional hint for optimizer
  }
}
```

#### 3.2.3 Storage Engine Strategy Matrix

| Storage Engine | Parallel Safe? | MVCC Support | Locking | Risk Level | Strategy |
|----------------|---------------|--------------|---------|------------|----------|
| **InnoDB** | ✅ Yes | ✅ Yes | Row-level | 🟢 Low | Parallel with snapshot |
| **ColumnStore** | ✅ Yes | ❌ No | None | 🟢 Low | Parallel, large chunks |
| **MyISAM** | ❌ No | ❌ No | Table-level | 🔴 High | Serial + LOW_PRIORITY |
| **Aria** | ❌ No | ❌ No | Table-level | 🟡 Medium | Serial extraction |
| **Memory** | ❌ No | ❌ No | Table-level | 🔴 High | Serial + volatility warning |

**Engine Detection:**
```sql
SELECT ENGINE 
FROM information_schema.TABLES 
WHERE TABLE_SCHEMA = 'production_db' 
  AND TABLE_NAME = 'orders';
```

#### 3.2.4 Advanced Optimizations

**OPTIMIZATION 1: Quantile Sampling (Smart Chunking)**

**Problem:** Traditional range splitting fails on sparse primary keys

```
Example Table: orders (id: 1, 2, 3, ..., 200000, [deleted 500k rows], 900000, ..., 1000000)

Classic Range Split (4 workers):
  Worker 1: id 1 → 250,000      → 200,000 rows (100% busy)
  Worker 2: id 250,001 → 500,000 → 0 rows (0% busy - IDLE!)
  Worker 3: id 500,001 → 750,000 → 0 rows (0% busy - IDLE!)
  Worker 4: id 750,001 → 1M      → 100,000 rows (100% busy)

Result: 2 workers idle, uneven completion times
```

**Solution:** Sample actual data distribution

```sql
-- Sample 9 quantile boundaries for 8 workers
SELECT id FROM orders ORDER BY id LIMIT 1 OFFSET 0;       -- Boundary 0
SELECT id FROM orders ORDER BY id LIMIT 1 OFFSET 12500;   -- Boundary 1 (1/8)
SELECT id FROM orders ORDER BY id LIMIT 1 OFFSET 25000;   -- Boundary 2 (2/8)
...
SELECT id FROM orders ORDER BY id LIMIT 1 OFFSET 100000;  -- Boundary 8 (end)

Result boundaries: [1, 25000, 50000, 75000, 100000, 125000, 150000, 175000, 200000]

Quantile Split:
  Worker 1: id 1 → 25,000        → ~12,500 rows (balanced)
  Worker 2: id 25,001 → 50,000   → ~12,500 rows (balanced)
  Worker 3: id 50,001 → 75,000   → ~12,500 rows (balanced)
  Worker 4: id 75,001 → 100,000  → ~12,500 rows (balanced)
  ...

Result: Perfect load distribution, no idle workers
```

**Impact:**
- Eliminates idle workers on sparse PKs
- Reduces standard deviation of worker completion times by 85%
- 20-30% throughput improvement on tables with >10% deleted rows

**OPTIMIZATION 2: PyArrow Backend Integration**

```python
# Standard pandas (object dtype)
chunk_df = pd.read_sql(query, conn)
# Memory usage: ~5-6 GB for 1M rows with mixed types

# PyArrow backend (columnar memory)
chunk_df = pd.read_sql(query, conn, dtype_backend="pyarrow")
# Memory usage: ~2.5-3 GB for same data (45-50% reduction)
```

**Benefits:**
- 30-50% memory reduction
- 3× faster Parquet serialization
- Native handling of complex types

**OPTIMIZATION 3: Adaptive Throttling**

**Monitors database health in real-time:**

```python
def _check_database_health(self):
    with self.engine.connect() as conn:
        # Metric 1: Active connections
        threads_running = conn.execute(
            text("SHOW GLOBAL STATUS LIKE 'Threads_running'")
        ).fetchone()[1]
        
        # Metric 2: Buffer pool hit ratio
        reads = conn.execute(
            text("SHOW GLOBAL STATUS LIKE 'Innodb_buffer_pool_reads'")
        ).fetchone()[1]
        
        read_requests = conn.execute(
            text("SHOW GLOBAL STATUS LIKE 'Innodb_buffer_pool_read_requests'")
        ).fetchone()[1]
        
        hit_ratio = (1 - reads / read_requests) * 100 if read_requests > 0 else 100
        
        # Calculate throttle
        throttle_seconds = 0
        
        if threads_running > 50:
            throttle_seconds = min((threads_running - 50) * 0.5, 10)
        
        if hit_ratio < 80:
            throttle_seconds = max(throttle_seconds, 2.0)
        
        return {
            "threads_running": threads_running,
            "buffer_pool_hit_ratio": hit_ratio,
            "throttle_seconds": throttle_seconds
        }
```

**Production Impact:**
- Prevents database saturation in shared environments
- Trades 29% throughput for zero production incidents
- Auto-adapts to database load

#### 3.2.5 InnoDB Consistent Snapshot

**Ensures point-in-time consistency across parallel workers:**

```python
# Each worker executes:
conn.execute(text("START TRANSACTION WITH CONSISTENT SNAPSHOT"))

# Query executes within snapshot
result = conn.execute(text(f"""
    SELECT * FROM orders 
    WHERE order_id >= {start} AND order_id < {end}
"""))

# Commit releases snapshot
conn.execute(text("COMMIT"))
```

**Guarantees:**
- All workers see same data version
- Non-blocking (MVCC allows concurrent writes)
- No phantom reads or inconsistencies

#### 3.2.6 Performance Characteristics

**Baseline vs. Optimized:**

| Table Size | Baseline | Optimized | Improvement |
|------------|----------|-----------|-------------|
| 100k rows | 8.3s | 3.2s | **2.6× faster** |
| 1M rows | 92.4s | 37.1s | **2.5× faster** |
| 10M rows | 15.2 min | 6.1 min | **2.5× faster** |

**Memory Usage:**

| Table Size | Baseline (pandas) | Optimized (PyArrow) | Reduction |
|------------|------------------|---------------------|-----------|
| 1M rows | 6.8 GB | 3.2 GB | **53% lower** |
| 10M rows | 18 GB (crashed) | 8.4 GB | **Zero crashes** |

---

### 3.3 MariaDB Cloud (SkySQL) Connector

#### 3.3.1 Overview

**Technology:** MariaDB SkySQL (Serverless)  
**Driver:** PyMySQL with SSL/TLS  
**Status:** ✅ Production-Ready with Cloud Optimizations  
**Key Features:**
- Mandatory SSL/TLS encryption with certificate validation
- Automatic retry with exponential backoff
- Network latency monitoring
- Multi-tenant architecture (read-only user creation)
- Reduced parallelism for serverless constraints

#### 3.3.2 Connection Configuration

```json
{
  "source_type": "mariadb_cloud",
  "connection_config": {
    "host": "serverless-us-west-2.sysp0000.db1.skysql.com",
    "port": 4020,
    "database": "production_db",
    "user": "idp_reader",  // Read-only service account
    "password": "${SKYSQL_READONLY_PASSWORD}",
    "ssl_ca": "C:/certs/globalsignrootca.pem",  // MANDATORY
    "ssl_verify_cert": true,  // Enforced
    "connect_timeout": 30,
    "read_timeout": 60
  },
  "extraction_request": {
    "entity": "customers",
    "mode": "full",
    "enable_parallel": true  // Max 2 workers automatically enforced
  }
}
```

#### 3.3.3 Cloud vs. Self-Hosted Comparison

| Aspect | Self-Hosted | Cloud (SkySQL) | Rationale |
|--------|------------|----------------|-----------|
| **Network Latency** | 1-10ms | 50-200ms | WAN vs LAN |
| **SSL/TLS** | Optional | **MANDATORY** | Cloud security requirement |
| **Max Workers** | Up to 16 | **Max 2** | Serverless connection limits |
| **Chunk Size** | 50k-100k rows | **100k-200k rows** | Reduce network roundtrips |
| **Connection Pool** | Size: 20 | **Size: 3** | Serverless resource management |
| **Retry Logic** | Not needed | **Required** | Network transients |
| **IP Access** | Direct | **Whitelist required** | Firewall configuration |

#### 3.3.4 Cloud-Specific Optimizations

**OPTIMIZATION 1: Reduced Parallelism**

```python
class CloudExtractionOptimizer(ExtractionOptimizer):
    def calculate_optimal_params(self, row_count, ...):
        # Get base calculations
        base_chunk, base_workers = super().calculate_optimal_params(...)
        
        # Cloud adjustments
        cloud_chunk = int(base_chunk * 2.0)  # Larger chunks
        cloud_chunk = min(cloud_chunk, 200_000)  # Cap at 200k
        
        cloud_workers = min(base_workers, 2)  # Force max 2 workers
        
        # Disable parallelism for small tables
        if row_count < 10_000:
            cloud_workers = 1
        
        return cloud_chunk, cloud_workers
```

**Why Max 2 Workers?**
- Serverless databases have dynamic connection limits
- During auto-scaling, aggressive parallelism causes connection exhaustion
- Conservative approach maintains stability

**OPTIMIZATION 2: Network Latency Monitoring**

```python
def _measure_latency(self, conn):
    start = time.time()
    conn.execute(text("SELECT 1"))
    latency_ms = (time.time() - start) * 1000
    
    if latency_ms > 100:
        logger.warning(
            f"⚠️  High network latency: {latency_ms:.1f}ms\n"
            f"   Expected: 50-100ms\n"
            f"   Check: VPN overhead, network congestion"
        )
    
    return latency_ms
```

**Logged in metadata:**
```json
{
  "network_metrics": {
    "average_latency_ms": 78.3,
    "min_latency_ms": 52.1,
    "max_latency_ms": 134.7
  }
}
```

**OPTIMIZATION 3: Automatic Retry with Exponential Backoff**

```python
max_retries = 3
retry_delay = 2  # seconds

for attempt in range(1, max_retries + 1):
    try:
        engine = create_engine(connection_string, ...)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        
        logger.info("✅ Connected successfully")
        break
        
    except OperationalError as e:
        if "timeout" in str(e) or "connection" in str(e):
            if attempt < max_retries:
                wait_time = retry_delay * (2 ** (attempt - 1))
                logger.warning(f"⚠️  Attempt {attempt} failed, retry in {wait_time}s")
                time.sleep(wait_time)
            else:
                logger.error("❌ Max retries reached")
                raise
```

**Retry Schedule:**
- Attempt 1: Immediate
- Attempt 2: Wait 2 seconds
- Attempt 3: Wait 4 seconds
- Total max wait: 6 seconds

**OPTIMIZATION 4: Large Chunk Strategy**

**Network Cost Analysis:**

| Chunk Size | Roundtrips (1M rows) | Network Time (80ms latency) |
|------------|---------------------|----------------------------|
| 10,000 rows | 100 | 8.0 seconds |
| 50,000 rows | 20 | 1.6 seconds |
| 100,000 rows | 10 | 0.8 seconds |
| 200,000 rows | 5 | 0.4 seconds |

**Result:** Larger chunks save significant network time

#### 3.3.5 Multi-Tenant Architecture

**Two-Laptop Simulation:**

```
LAPTOP A (Client - Database Owner)
  ├─ Script: laptopA_create_readonly.py
  ├─ Action: Creates read-only user "idp_reader"
  ├─ Permissions: GRANT SELECT ON database.* TO 'idp_reader'@'%'
  └─ Output: readonly_credentials.txt
                    ↓
        [Secure Credential Handoff]
                    ↓
LAPTOP B (IDP Platform - Data Ingestion Service)
  ├─ Script: laptopB_idp_ingestion.py
  ├─ Action: Receives credentials, validates permissions
  ├─ Security Tests:
  │   • SELECT: ✅ Allowed
  │   • INSERT: ✅ Blocked (Access Denied)
  │   • UPDATE: ✅ Blocked (Access Denied)
  │   • DELETE: ✅ Blocked (Access Denied)
  └─ Result: Safe extraction with audit trail
```

**Security Benefits:**

| Scenario | With Admin Access | With Read-Only Access |
|----------|------------------|----------------------|
| IDP Compromised | Attacker can DROP TABLE | Attacker can only read |
| Code Bug | Accidental DELETE FROM | Cannot modify data |
| Compliance | ❌ Fails audit | ✅ Meets standards |
| Trust Model | Client must trust IDP fully | Limited trust required |

#### 3.3.6 Performance Characteristics

**Cloud Performance (with optimizations):**

| Table Size | Throughput | Network Overhead | Notes |
|------------|-----------|------------------|-------|
| 100k rows | 12.3k rows/sec | 0.16s | Small table, minimal roundtrips |
| 1M rows | 13.8k rows/sec | 0.8s | Optimal for cloud |
| 10M rows | 13.4k rows/sec | 4.0s | Sustained performance |

**Improvement over Naive Cloud Extraction:**
- **2.0× faster** end-to-end
- **98% reduction** in network roundtrips
- **99.5% reduction** in network overhead time

---

### 3.4 MongoDB Connector (Planned)

#### 3.4.1 Overview

**Technology:** MongoDB 4.0+  
**Driver:** PyMongo  
**Status:** 🔜 Planned (Q2 2026)  
**Target Features:**
- Document-oriented extraction
- Aggregation pipeline support
- Cursor-based streaming
- BSON to JSON conversion
- Index-aware query optimization

#### 3.4.2 Planned Architecture

```python
class MongoDBConnector(BaseConnector):
    source_type = "mongodb"
    
    def connect(self):
        # MongoDB connection string
        self.client = MongoClient(
            host=self.config['host'],
            port=self.config['port'],
            username=self.config['user'],
            password=self.config['password'],
            authSource=self.config['database'],
            ssl=self.config.get('ssl', False),
            tlsCAFile=self.config.get('ssl_ca')
        )
        self.db = self.client[self.config['database']]
    
    def extract(self, extraction_request):
        collection_name = extraction_request['entity']
        collection = self.db[collection_name]
        
        # Cursor-based extraction
        cursor = collection.find({}, batch_size=chunk_size)
        
        batch = []
        for doc in cursor:
            # Convert ObjectId to string
            doc['_id'] = str(doc['_id'])
            batch.append(doc)
            
            if len(batch) >= chunk_size:
                # Flatten nested documents
                df = pd.json_normalize(batch)
                yield {"data": df, "metadata": {...}}
                batch = []
```

#### 3.4.3 Planned Features

**1. Aggregation Pipeline Optimization**
```javascript
// Use aggregation for filtering/projection
db.users.aggregate([
    { $match: { created_at: { $gt: ISODate("2026-01-01") } } },
    { $project: { password: 0 } },  // Exclude sensitive fields
    { $limit: chunk_size }
])
```

**2. Index-Aware Query Planning**
```python
# Check available indexes
indexes = collection.index_information()

# Use covered queries where possible
if 'user_id_1' in indexes:
    # Query uses index, faster
    cursor = collection.find({}, {'user_id': 1, '_id': 0})
```

**3. BSON Type Handling**
```python
# Convert MongoDB-specific types
ObjectId → string
ISODate → datetime64
Decimal128 → float64
Binary → base64 string
```

#### 3.4.4 Challenges & Considerations

⚠️ **Schema Variability**: Documents in same collection may have different fields  
⚠️ **Nested Documents**: Need flattening strategy (configurable depth)  
⚠️ **Large Arrays**: May cause memory pressure  
⚠️ **No MVCC**: Cursor may see inconsistent state during concurrent writes

#### 3.4.5 Planned Configuration

```json
{
  "source_type": "mongodb",
  "connection_config": {
    "host": "mongodb.example.com",
    "port": 27017,
    "database": "production",
    "user": "readonly_user",
    "password": "${MONGO_PASSWORD}",
    "auth_source": "admin",
    "ssl": true,
    "ssl_ca": "/path/to/ca.pem"
  },
  "extraction_request": {
    "entity": "users",
    "mode": "full",
    "batch_size": 10000,
    "flatten_nested": true,
    "max_nesting_depth": 2,
    "exclude_fields": ["password", "secret_token"]
  }
}
```

---

### 3.5 AWS S3 Connector (Planned)

#### 3.5.1 Overview

**Technology:** AWS S3  
**Driver:** Boto3  
**Status:** 🔜 Planned (Q3 2026)  
**Target Features:**
- Object-based extraction (CSV, JSON, Parquet)
- Parallel downloads with byte-range requests
- S3 Select for in-place filtering
- Automatic file format detection
- Incremental extraction (new objects only)

#### 3.5.2 Planned Architecture

```python
class S3Connector(BaseConnector):
    source_type = "aws_s3"
    
    def connect(self):
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=self.config['access_key_id'],
            aws_secret_access_key=self.config['secret_access_key'],
            region_name=self.config['region']
        )
    
    def extract(self, extraction_request):
        bucket = extraction_request['bucket']
        prefix = extraction_request.get('prefix', '')
        
        # List objects
        paginator = self.s3_client.get_paginator('list_objects_v2')
        page_iterator = paginator.paginate(
            Bucket=bucket,
            Prefix=prefix
        )
        
        for page in page_iterator:
            for obj in page.get('Contents', []):
                key = obj['Key']
                
                # Download object
                response = self.s3_client.get_object(
                    Bucket=bucket,
                    Key=key
                )
                
                # Parse based on file extension
                if key.endswith('.csv'):
                    df = pd.read_csv(response['Body'])
                elif key.endswith('.json'):
                    df = pd.read_json(response['Body'])
                elif key.endswith('.parquet'):
                    df = pd.read_parquet(response['Body'])
                
                yield {"data": df, "metadata": {...}}
```

#### 3.5.3 Planned Features

**1. Parallel Downloads with Byte-Range Requests**
```python
# Download large file in parallel chunks
file_size = s3_client.head_object(Bucket=bucket, Key=key)['ContentLength']
chunk_size = 10 * 1024 * 1024  # 10 MB

def download_range(start, end):
    response = s3_client.get_object(
        Bucket=bucket,
        Key=key,
        Range=f'bytes={start}-{end}'
    )
    return response['Body'].read()

# Parallel download
with ThreadPoolExecutor(max_workers=8) as executor:
    ranges = [(i, min(i + chunk_size, file_size)) 
              for i in range(0, file_size, chunk_size)]
    chunks = list(executor.map(lambda r: download_range(*r), ranges))

# Reconstruct file
file_data = b''.join(chunks)
```

**2. S3 Select (Server-Side Filtering)**
```python
# Filter CSV on S3 without downloading entire file
response = s3_client.select_object_content(
    Bucket=bucket,
    Key=key,
    ExpressionType='SQL',
    Expression="SELECT * FROM s3object WHERE age > 25",
    InputSerialization={'CSV': {"FileHeaderInfo": "Use"}},
    OutputSerialization={'CSV': {}}
)

# Stream results
for event in response['Payload']:
    if 'Records' in event:
        data = event['Records']['Payload'].decode('utf-8')
        # Process filtered data
```

**3. Incremental Extraction (New Objects Only)**
```python
# Track last extraction timestamp
last_modified_cutoff = datetime(2026, 2, 15, 12, 0, 0)

# List only new objects
for obj in s3_client.list_objects_v2(Bucket=bucket, Prefix=prefix)['Contents']:
    if obj['LastModified'] > last_modified_cutoff:
        # Extract new object
        extract_object(obj)
```

#### 3.5.4 Challenges & Considerations

⚠️ **Cost Management**: S3 GET requests are billable (optimize with pagination)  
⚠️ **Large Files**: Multi-GB files may require streaming or chunked download  
⚠️ **File Format Variety**: Need robust format detection and parsing  
⚠️ **Schema Consistency**: CSV files may have inconsistent headers across objects

#### 3.5.5 Planned Configuration

```json
{
  "source_type": "aws_s3",
  "connection_config": {
    "aws_access_key_id": "${AWS_ACCESS_KEY_ID}",
    "aws_secret_access_key": "${AWS_SECRET_ACCESS_KEY}",
    "region": "us-east-1"
  },
  "extraction_request": {
    "bucket": "production-data",
    "prefix": "logs/2026/02/",
    "file_pattern": "*.csv",
    "mode": "incremental",
    "watermark_field": "last_modified",
    "watermark_value": "2026-02-15T12:00:00Z",
    "parallel_downloads": true,
    "max_workers": 8
  }
}
```

---

## 4. Common Features & Optimizations

### 4.1 Intelligent Auto-Tuning

All connectors inherit auto-tuning logic from **ExtractionOptimizer** base class.

#### 4.1.1 Algorithm Overview

```python
def calculate_optimal_params(
    row_count: int,
    avg_row_size_bytes: int = 1024,
    is_remote: bool = False,
    engine_type: str = "default"
) -> Tuple[int, int]:
    """
    Returns: (optimal_chunk_size, optimal_num_workers)
    """
    
    # STEP 1: Calculate base chunk size (target 100 MB per chunk)
    target_chunk_memory = 100 * 1024 * 1024  # 100 MB
    base_chunk_size = target_chunk_memory // avg_row_size_bytes
    
    # STEP 2: Apply table-size scaling
    if row_count < 1_000:
        chunk_size = row_count  # Entire table
    elif row_count < 10_000:
        chunk_size = 1_000
    elif row_count < 100_000:
        chunk_size = 10_000
    elif row_count < 1_000_000:
        chunk_size = 50_000
    else:
        chunk_size = 100_000
    
    chunk_size = min(chunk_size, base_chunk_size)
    
    # STEP 3: Calculate max workers
    total_chunks = math.ceil(row_count / chunk_size)
    
    # By RAM constraint
    if psutil:
        available_gb = psutil.virtual_memory().available / (1024**3)
        chunk_memory = chunk_size * avg_row_size_bytes
        max_workers_by_ram = int((available_gb * 0.5 * 1024**3) / chunk_memory)
    else:
        max_workers_by_ram = 8
    
    # By CPU constraint
    max_workers_by_cpu = psutil.cpu_count(logical=True) if psutil else 4
    
    # By efficiency (diminishing returns)
    max_workers_by_efficiency = int(math.sqrt(total_chunks)) + 1
    
    # Take minimum
    num_workers = min(
        max_workers_by_ram,
        max_workers_by_cpu,
        max_workers_by_efficiency,
        16  # Global maximum
    )
    
    # STEP 4: Apply penalties
    if is_remote:
        num_workers = int(num_workers * 0.75)  # Network latency penalty
    
    if row_count < 1_000:
        num_workers = 1  # Avoid thread overhead on tiny tables
    
    # Ensure at least 1 worker
    num_workers = max(1, num_workers)
    
    return chunk_size, num_workers
```

#### 4.1.2 Examples

**Example 1: Small Table (Local)**
```
Inputs:
  row_count = 500
  avg_row_size = 1024
  is_remote = False

Calculation:
  chunk_size = 500 (entire table)
  num_workers = 1 (avoid overhead)

Result: Single-threaded extraction
```

**Example 2: Medium Table (Remote)**
```
Inputs:
  row_count = 500,000
  avg_row_size = 2048
  is_remote = True
  available_RAM = 8 GB
  CPU_cores = 8

Calculation:
  base_chunk_size = 100MB / 2048 = 51,200
  table_scaling = 50,000 (< 1M rows)
  chunk_size = min(51,200, 50,000) = 50,000
  
  total_chunks = 500,000 / 50,000 = 10
  
  max_workers_by_ram = (8 * 0.5 * 1024^3) / (50,000 * 2048) = 40
  max_workers_by_cpu = 8
  max_workers_by_efficiency = sqrt(10) + 1 = 4
  
  num_workers = min(40, 8, 4, 16) = 4
  
  Remote penalty: 4 * 0.75 = 3

Result: 3 workers, 50,000 rows/chunk
```

**Example 3: Large Table (Cloud)**
```
Inputs:
  row_count = 5,000,000
  avg_row_size = 1024
  is_remote = True (cloud)
  connector_type = "mariadb_cloud"

Calculation:
  base_chunk_size = 100MB / 1024 = 102,400
  table_scaling = 100,000 (≥ 1M rows)
  chunk_size = min(102,400, 100,000) = 100,000
  
  CloudExtractionOptimizer overrides:
    cloud_chunk_size = 100,000 * 2.0 = 200,000
    cloud_workers = min(base_workers, 2) = 2

Result: 2 workers, 200,000 rows/chunk (cloud-optimized)
```

### 4.2 PyArrow Backend Integration

All connectors use PyArrow as the data backend for significant performance benefits.

#### 4.2.1 Implementation

```python
# Standard pandas (object dtype)
chunk_df = pd.read_sql(query, conn)

# PyArrow backend (columnar memory)
chunk_df = pd.read_sql(query, conn, dtype_backend="pyarrow")
```

#### 4.2.2 Benefits

| Metric | Pandas (Object) | PyArrow (Columnar) | Improvement |
|--------|----------------|-------------------|-------------|
| **Memory Usage** | 6.0 GB | 3.2 GB | 47% reduction |
| **Parquet Write Speed** | 8.2 sec | 2.7 sec | 3× faster |
| **String Efficiency** | Object overhead | UTF-8 native | Compact |
| **Null Handling** | Sentinel values | Bitmap | Efficient |

#### 4.2.3 Type Handling

```python
# Complex types → JSON strings → PyArrow string type
if isinstance(sample_value, (dict, list)):
    df[col] = df[col].apply(lambda x: json.dumps(x) if x else None)
    df[col] = df[col].astype("string[pyarrow]")
```

### 4.3 Parallel Extraction Framework

#### 4.3.1 When to Use Parallel Extraction

| Condition | Parallel? | Reason |
|-----------|-----------|--------|
| Table < 1,000 rows | ❌ No | Thread overhead > benefit |
| No integer PK | ❌ No | Cannot split ranges reliably |
| MyISAM engine | ❌ No | Table-level locking risk |
| Cloud serverless | ⚠️ Limited (max 2) | Connection pool constraints |
| InnoDB / PostgreSQL | ✅ Yes | MVCC allows safe parallelism |

#### 4.3.2 Parallel Execution Pattern

```python
# Spawn worker threads
executor = ThreadPoolExecutor(max_workers=num_workers, thread_name_prefix="Worker")

# Create bounded queue for backpressure
internal_queue = queue.Queue(maxsize=num_workers * 2)

# Submit worker tasks
futures = []
for i in range(num_workers):
    future = executor.submit(
        _worker_extract,
        task_config={
            "start": start_boundary,
            "end": end_boundary,
            "chunk_size": chunk_size
        },
        queue=internal_queue,
        schema_snapshot=schema_snapshot
    )
    futures.append(future)

# Main thread collects results
completed_workers = 0
while completed_workers < num_workers:
    item = internal_queue.get(timeout=5)
    
    if item is None:
        completed_workers += 1  # Worker finished
    elif isinstance(item, Exception):
        executor.shutdown(cancel_futures=True)
        raise item
    else:
        yield item  # DataFrame batch

executor.shutdown(wait=True)
```

### 4.4 Schema Handling Strategy

#### 4.4.1 Principles

1. **Snapshot at Start**: Schema captured before extraction begins
2. **Preserve Source Truth**: Complex types serialized, not transformed
3. **Explicit Drift Detection**: Schema changes logged, not auto-applied

#### 4.4.2 Schema Snapshot

```python
inspector = inspect(engine)
schema_snapshot = []

for column in inspector.get_columns(table_name):
    schema_snapshot.append({
        "name": column['name'],
        "type": str(column['type']),
        "nullable": column['nullable'],
        "primary_key": column.get('primary_key', False)
    })

# Stored in metadata.json
metadata["schema_snapshot"] = schema_snapshot
```

#### 4.4.3 Complex Type Handling

| Source Type | Bronze Layer | Silver Layer (Future) |
|-------------|-------------|----------------------|
| **JSON** | String (JSON serialized) | Flattened columns |
| **Array** | String (JSON serialized) | Exploded rows |
| **Decimal** | Float64 or String | Float64 (precision rules) |
| **BLOB** | Base64 string | Binary (if needed) |
| **Nested Objects** | JSON string | Struct type |

---

## 5. Technical Implementation

### 5.1 Technology Stack

#### 5.1.1 Core Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| **pandas** | ≥2.0.0 | DataFrame operations (with PyArrow backend) |
| **pyarrow** | ≥12.0.0 | Columnar memory layout, Parquet I/O |
| **sqlalchemy** | ≥2.0.0 | Database abstraction, connection pooling |
| **psycopg2** | ≥2.9.0 | PostgreSQL driver (C extension) |
| **pymysql** | ≥1.0.0 | MariaDB driver (pure Python) |
| **psutil** | ≥5.9.0 | System resource monitoring |
| **customtkinter** | ≥5.0.0 | Modern GUI framework |

#### 5.1.2 Optional Dependencies (Future)

| Package | Version | Purpose |
|---------|---------|---------|
| **pymongo** | ≥4.0.0 | MongoDB driver |
| **boto3** | ≥1.26.0 | AWS S3 client |
| **motor** | ≥3.0.0 | Async MongoDB driver |

### 5.2 Base Connector Interface

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, Iterator

class BaseConnector(ABC):
    """
    Abstract base class for all data source connectors
    """
    source_type: str = "base"  # Override in subclass
    
    def __init__(self, connection_config: Dict[str, Any]):
        self.connection_config = connection_config
        self.engine = None
    
    @abstractmethod
    def connect(self) -> None:
        """Establish connection to data source"""
        pass
    
    @abstractmethod
    def validate_credentials(self) -> None:
        """Verify connection and permissions"""
        pass
    
    @abstractmethod
    def extract(self, extraction_plan: Dict[str, Any]) -> Iterator[Dict[str, Any]]:
        """
        Extract data in batches
        
        Args:
            extraction_plan: Configuration dict with:
                - entity: Table/collection name
                - mode: "full" or "incremental"
                - chunk_size: Rows per batch
                - num_workers: Parallel workers
        
        Yields:
            Dict with:
                - data: pd.DataFrame
                - metadata: Dict with lineage info
        """
        pass
    
    @abstractmethod
    def close(self) -> None:
        """Clean up connections and resources"""
        pass
    
    def _sanitize_complex_types(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Convert complex types (dict, list) to JSON strings
        Shared across all connectors
        """
        object_cols = df.select_dtypes(include=['object']).columns
        
        for col in object_cols:
            valid_sample = df[col].dropna()
            if valid_sample.empty:
                continue
            
            if isinstance(valid_sample.iloc[0], (dict, list)):
                df[col] = [json.dumps(x) if x is not None else None 
                          for x in df[col]]
                df[col] = df[col].astype("string[pyarrow]")
        
        return df
```

### 5.3 Extraction Optimizer

```python
import psutil
import math
from typing import Tuple

class ExtractionOptimizer:
    """
    Calculates optimal chunk size and worker count
    Shared across all connectors (can be overridden)
    """
    
    def __init__(self):
        self.global_max_workers = 16
    
    def calculate_optimal_params(
        self,
        row_count: int,
        avg_row_size_bytes: int = 1024,
        is_remote: bool = False,
        engine_type: str = "default"
    ) -> Tuple[int, int]:
        """
        Returns: (chunk_size, num_workers)
        
        Full algorithm documented in Section 4.1
        """
        # Implementation shown in 4.1.1
        pass
```

### 5.4 Connection Management

#### 5.4.1 Connection Pooling (SQLAlchemy)

```python
from sqlalchemy import create_engine

# PostgreSQL
engine = create_engine(
    connection_string,
    pool_size=20,           # Base pool
    max_overflow=30,        # Additional connections when needed
    pool_pre_ping=True,     # Health check before use
    pool_recycle=3600,      # Recycle connections every hour
    connect_args={
        'connect_timeout': 10
    }
)

# MariaDB (Self-Hosted)
engine = create_engine(
    connection_string,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=3600,
    connect_args={
        'connect_timeout': 10,
        'read_timeout': 30
    }
)

# MariaDB Cloud
engine = create_engine(
    connection_string,
    pool_size=3,            # Reduced for serverless
    max_overflow=2,
    pool_recycle=900,       # 15 min (shorter for cloud)
    connect_args={
        'connect_timeout': 30,  # Longer for network latency
        'read_timeout': 60,
        'ssl': {
            'ca': ssl_ca_path,
            'check_hostname': True
        }
    }
)
```

---

## 6. Security & Compliance

### 6.1 Credential Management

#### 6.1.1 SecretManager Integration

```python
class SecretManager:
    """
    Resolves credentials from multiple sources
    Priority: Environment Variables > Secret Handler > Config File
    """
    
    @staticmethod
    def resolve(config: Dict[str, Any]) -> str:
        password = config.get("password")
        
        # Check if environment variable placeholder
        if password and password.startswith("${") and password.endswith("}"):
            env_var = password[2:-1]
            password = os.getenv(env_var)
            
            if not password:
                raise ValueError(
                    f"Environment variable {env_var} not found\n"
                    f"Set with: export {env_var}=your_password"
                )
        
        return password
```

#### 6.1.2 Configuration Security

**Best Practices:**
✅ Store passwords in environment variables  
✅ Use `.gitignore` to exclude config files  
✅ Rotate credentials regularly  
✅ Use read-only database accounts  
❌ Never commit passwords to Git  
❌ Never log credentials in plain text

### 6.2 Network Security

#### 6.2.1 SSL/TLS Support

| Connector | SSL Support | Certificate Validation |
|-----------|------------|----------------------|
| PostgreSQL | Optional (`ssl_mode` parameter) | Configurable |
| MariaDB (Self-Hosted) | Optional (`ssl_ca` parameter) | Optional |
| MariaDB Cloud | **MANDATORY** | **Enforced** (check_hostname=True) |
| MongoDB (Planned) | Optional | Configurable |
| AWS S3 (Planned) | Always (HTTPS) | N/A (managed by AWS) |

#### 6.2.2 Firewall Configuration

**Cloud Connectors:**
- Verify IP whitelist in cloud provider portal
- Use VPN for secure access from dynamic IPs
- Consider bastion hosts for production

**Self-Hosted:**
- Configure firewall rules (`ufw`, `firewalld`)
- Use SSH tunneling for remote access
- Restrict access to specific IP ranges

### 6.3 Access Control Models

#### 6.3.1 Principle of Least Privilege

**PostgreSQL:**
```sql
-- Create read-only role
CREATE ROLE idp_reader WITH LOGIN PASSWORD 'secure_password';

-- Grant SELECT only
GRANT CONNECT ON DATABASE production_db TO idp_reader;
GRANT USAGE ON SCHEMA public TO idp_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO idp_reader;

-- Auto-grant on future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA public 
GRANT SELECT ON TABLES TO idp_reader;
```

**MariaDB:**
```sql
-- Create read-only user
CREATE USER 'idp_reader'@'%' IDENTIFIED BY 'secure_password';

-- Grant SELECT only
GRANT SELECT ON production_db.* TO 'idp_reader'@'%';

FLUSH PRIVILEGES;
```

#### 6.3.2 Permission Validation

**Automated Security Testing (MariaDB Cloud):**
```python
def _validate_readonly_permissions(self):
    """Test that user can only SELECT"""
    with self.engine.connect() as conn:
        # Test SELECT (should succeed)
        try:
            conn.execute(text("SELECT COUNT(*) FROM customers"))
            logger.info("✅ SELECT: Allowed")
        except:
            logger.error("❌ SELECT failed")
            raise
        
        # Test INSERT (should fail)
        try:
            conn.execute(text("INSERT INTO customers VALUES (...)"))
            logger.error("🚨 SECURITY RISK: INSERT allowed!")
            raise SecurityError("User has write permissions")
        except OperationalError:
            logger.info("✅ INSERT: Blocked correctly")
        
        # Similar tests for UPDATE, DELETE
```

### 6.4 Audit Trail & Compliance

#### 6.4.1 Comprehensive Metadata Logging

Every extraction generates:
- Source information (host, database, user)
- Extraction timestamp (ISO 8601 format)
- Schema snapshot at extraction time
- Row counts and data statistics
- Execution parameters (chunk size, workers)
- Error logs (if any)

#### 6.4.2 Security Audit Trail (Cloud)

```json
{
  "security_audit": {
    "timestamp": "2026-02-16T14:30:00Z",
    "user_tested": "idp_reader",
    "permission_tests": {
      "SELECT": {
        "result": "✅ Allowed",
        "test_query": "SELECT COUNT(*) FROM customers",
        "rows_found": 1045320
      },
      "INSERT": {
        "result": "✅ Blocked",
        "error": "Access denied for user 'idp_reader'@'%'"
      },
      "UPDATE": {
        "result": "✅ Blocked",
        "error": "Access denied..."
      },
      "DELETE": {
        "result": "✅ Blocked",
        "error": "Access denied..."
      }
    },
    "audit_passed": true
  }
}
```

---

## 7. Performance Benchmarks

### 7.1 Connector Comparison Matrix

**Test Environment:**
- Hardware: 16 CPU cores, 32 GB RAM, NVMe SSD
- Network: 1 Gbps LAN (self-hosted), 100 Mbps WAN (cloud)
- Table Size: 1,000,000 rows, average row size 1 KB

| Connector | Throughput (rows/sec) | Memory Peak | Workers | Chunk Size | Notes |
|-----------|----------------------|-------------|---------|-----------|-------|
| **PostgreSQL** | 27,000 | 3.2 GB | 8 | 50,000 | Optimal |
| **MariaDB (InnoDB)** | 28,100 | 3.2 GB | 8 | 50,000 | With quantile sampling |
| **MariaDB (MyISAM)** | 15,200 | 2.1 GB | 1 | 50,000 | Serial (avoid table lock) |
| **MariaDB Cloud** | 13,800 | 2.8 GB | 2 | 100,000 | Cloud-optimized |

### 7.2 Optimization Impact Analysis

#### 7.2.1 Quantile Sampling (MariaDB)

**Test:** 1M row table with 40% deleted rows (sparse PKs)

| Metric | Range Splitting | Quantile Sampling | Improvement |
|--------|----------------|-------------------|-------------|
| Worker 1 Completion | 8.2s | 9.1s | — |
| Worker 2 Completion | 1.3s | 9.3s | Balanced |
| Worker 3 Completion | 1.1s | 9.0s | Balanced |
| Worker 4 Completion | 7.9s | 9.2s | — |
| **Total Runtime** | 16.4s | 9.3s | **43% faster** |
| **Std. Deviation** | 3.7s | 0.13s | **96% more uniform** |

#### 7.2.2 PyArrow Backend (All Connectors)

**Test:** 500k rows, mixed types (int, string, JSON)

| Metric | Pandas (Object) | PyArrow | Improvement |
|--------|----------------|---------|-------------|
| Read Time | 11.2s | 10.8s | 4% faster |
| Memory Peak | 3.8 GB | 2.1 GB | **45% reduction** |
| Parquet Write | 6.7s | 2.1s | **3.2× faster** |
| **Total Pipeline** | 17.9s | 12.9s | **28% faster** |

#### 7.2.3 Adaptive Throttling (MariaDB)

**Test:** Shared production database (simulated 60 active threads)

| Metric | No Throttling | With Throttling | Impact |
|--------|--------------|-----------------|---------|
| Connector Throughput | 45k rows/s | 32k rows/s | 29% slower |
| DB Thread Count (Peak) | 78 threads | 54 threads | **31% lower** |
| Production Query P95 | 340ms | 120ms | **65% faster** |
| **Incidents** | 2 timeouts | 0 | **Zero impact** |

### 7.3 Resource Utilization

#### 7.3.1 Memory Usage by Table Size

| Table Size | PostgreSQL | MariaDB (InnoDB) | MariaDB Cloud | Notes |
|------------|-----------|-----------------|---------------|-------|
| 100k rows | 0.9 GB | 0.9 GB | 0.8 GB | Small table |
| 1M rows | 3.2 GB | 3.2 GB | 2.8 GB | Standard |
| 10M rows | 8.4 GB | 8.4 GB | 7.1 GB | Large chunks |

#### 7.3.2 Network Impact (Cloud vs Self-Hosted)

**1M row table extraction:**

| Component | Self-Hosted | Cloud | Difference |
|-----------|------------|-------|-----------|
| Query Execution | 30.0s | 31.2s | +1.2s (4%) |
| Network Transfer | 5.0s | 18.3s | +13.3s (266%) |
| Network Latency | 0.1s | 0.8s | +0.7s (700%) |
| Serialization | 2.0s | 2.0s | 0s |
| **Total** | **37.1s** | **72.3s** | **+35.2s (95%)** |

**Key Insight:** Network latency dominates cloud extraction time

---

## 8. GUI Integration

### 8.1 Unified Interface Design

The SyniqAI system provides a single, modern GUI built with CustomTkinter that supports all connectors.

#### 8.1.1 Interface Layout

```
┌──────────────────────────────────────────────────────────────────┐
│ SyniqAI Bronze Layer - Enterprise Data Extraction Platform       │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  [🔌 Connection] [📊 Extraction] [📈 Monitoring] [☁️ Cloud]      │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ 🔌 Connection Tab                                            ││
│  │                                                              ││
│  │  Database Type:  ( ) PostgreSQL  ( ) MariaDB  (•) Cloud     ││
│  │                                                              ││
│  │  Host: [serverless-us-west-2.sysp0000...    ]               ││
│  │  Port: [4020]           Database: [production_db]           ││
│  │  User: [idp_reader]     Password: [••••••••••••••]          ││
│  │  SSL: [C:\certs\globalsignrootca.pem]         [Browse...]   ││
│  │                                                              ││
│  │  [🔌 Connect]  [✅ Test Connection]  [🔌 Disconnect]        ││
│  │                                                              ││
│  │  Connection Status: ⚫ DISCONNECTED                          ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ 📊 Extraction Tab                                            ││
│  │                                                              ││
│  │  Table Name: [customers                     ]               ││
│  │  Mode: (•) Full  ( ) Incremental                            ││
│  │                                                              ││
│  │  Optimization: [🤖 Auto]  [✋ Manual]                        ││
│  │  Chunk Size: [100000]  Workers: [2]                         ││
│  │                                                              ││
│  │  [🔍 Analyze Table]  [▶️ Start Extraction]  [⏹️ Stop]       ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ Execution Console                                            ││
│  │                                                              ││
│  │  2026-02-16 09:30:45 | ✅ Connected to SkySQL               ││
│  │  2026-02-16 09:30:47 | 📊 Table 'customers': 1,045,320 rows ││
│  │  2026-02-16 09:30:48 | 🧮 Optimal: 100k chunk × 2 workers   ││
│  │  2026-02-16 09:30:50 | ⚡ Extracting...                     ││
│  │  2026-02-16 09:31:32 | ✅ Complete: 1,045,320 rows in 42s   ││
│  │                                                              ││
│  │  [████████████████████████████████████] 100%                ││
│  └─────────────────────────────────────────────────────────────┘│
└──────────────────────────────────────────────────────────────────┘
```

### 8.2 Multi-Connector Workflow

#### 8.2.1 Connector Selection

```python
# Connector mapping in GUI
CONNECTOR_MAP = {
    "postgres": PostgresConnector,
    "mariadb": MariaDBConnector,
    "mariadb_cloud": MariaDBCloudConnector,
    # Future:
    # "mongodb": MongoDBConnector,
    # "aws_s3": S3Connector
}

# Dynamic connector instantiation
def _connect(self):
    source_type = self.source_type_var.get()
    ConnectorClass = CONNECTOR_MAP[source_type]
    
    config = self._get_current_config()
    self.connector = ConnectorClass(config)
    self.connector.connect()
```

#### 8.2.2 Auto/Manual Mode Toggle

```python
# Auto optimization
if self.auto_optimize.get():
    chunk_size, num_workers = optimizer.calculate_optimal_params(
        row_count=table_row_count,
        is_remote=(source_type in ["mariadb_cloud"]),
        engine_type=engine_type
    )
    self.chunk_entry.set(chunk_size)
    self.workers_entry.set(num_workers)
    self._log(f"🤖 Auto-optimized: {chunk_size:,} × {num_workers} workers")

# Manual override
else:
    chunk_size = int(self.chunk_entry.get())
    num_workers = int(self.workers_entry.get())
    self._log(f"✋ Manual mode: {chunk_size:,} × {num_workers} workers")
```

### 8.3 User Experience Patterns

#### 8.3.1 Real-Time Feedback

- **Connection Status Badge**: Visual indicator (⚫ DISCONNECTED / 🟢 CONNECTED)
- **Progress Bar**: Indeterminate during extraction
- **Console Logs**: Color-coded messages (INFO, SUCCESS, WARNING, ERROR)
- **Metrics Panel**: Live updates (rows extracted, throughput, ETA)

#### 8.3.2 Error Handling

```python
try:
    self.connector.connect()
    self._update_status_badge("🟢 CONNECTED", "green")
    self._log("✅ Connected successfully", "SUCCESS")
    
except SSLError as e:
    self._log(f"❌ SSL Error: {e}", "ERROR")
    messagebox.showerror(
        "SSL Certificate Error",
        f"Certificate validation failed.\n\n"
        f"Certificate: {config['ssl_ca']}\n\n"
        f"Solution:\n"
        f"1. Verify certificate path exists\n"
        f"2. Re-download from cloud provider portal"
    )
    
except OperationalError as e:
    self._log(f"❌ Connection Error: {e}", "ERROR")
    messagebox.showerror(
        "Connection Failed",
        f"Could not connect to database.\n\n"
        f"Possible causes:\n"
        f"• Incorrect host/port\n"
        f"• Invalid credentials\n"
        f"• Firewall blocking connection"
    )
```

---

## 9. Operational Guidelines

### 9.1 Deployment Procedures

#### 9.1.1 Environment Setup

**1. Install Dependencies**
```bash
# Create virtual environment
python -m venv syniqai_env
source syniqai_env/bin/activate  # Linux/Mac
# OR
syniqai_env\Scripts\activate  # Windows

# Install packages
pip install pandas>=2.0.0 pyarrow>=12.0.0 sqlalchemy>=2.0.0 \
            psycopg2>=2.9.0 pymysql>=1.0.0 psutil>=5.9.0 \
            customtkinter>=5.0.0
```

**2. Configure Environment Variables**
```bash
# PostgreSQL
export POSTGRES_PASSWORD="your_password"

# MariaDB
export MARIADB_PASSWORD="your_password"

# MariaDB Cloud
export SKYSQL_READONLY_PASSWORD="your_password"
```

**3. Download SSL Certificates (if cloud)**
```bash
# MariaDB Cloud
wget https://supplychain.mariadb.com/skysql-chain.pem -O globalsignrootca.pem
```

#### 9.1.2 Configuration Files

**config_postgres.json:**
```json
{
  "source_type": "postgres",
  "connection_config": {
    "host": "localhost",
    "port": 5432,
    "database": "production_db",
    "user": "readonly_user",
    "password": "${POSTGRES_PASSWORD}"
  },
  "extraction_request": {
    "entity": "users",
    "mode": "full"
  }
}
```

#### 9.1.3 Execution

**CLI Mode:**
```bash
python main.py --config config_postgres.json
```

**GUI Mode:**
```bash
python gui_ctk.py
```

### 9.2 Monitoring & Alerting

#### 9.2.1 Key Metrics to Monitor

| Metric | Target | Alert Threshold |
|--------|--------|----------------|
| **Extraction Time** | < 5 min for 1M rows | > 10 min |
| **Throughput** | > 20k rows/sec | < 10k rows/sec |
| **Memory Usage** | < 50% available RAM | > 80% available RAM |
| **Error Rate** | 0% | > 1% |
| **Cloud Latency** | < 100ms | > 200ms |

#### 9.2.2 Log Analysis

**Success Pattern:**
```
✅ Connected to [database]
📊 Table '[table]': [row_count] rows
🧮 Optimal: [chunk_size] × [workers] workers
⚡ Extracting...
✅ Complete: [row_count] rows in [time]s
```

**Failure Pattern:**
```
❌ Connection failed: [error]
🔧 TROUBLESHOOTING:
   1. [step 1]
   2. [step 2]
```

### 9.3 Troubleshooting Guide

#### 9.3.1 Common Issues & Solutions

**Issue 1: "Out of Memory" Error**

**Symptoms:**
```
MemoryError: Unable to allocate [size] for array
```

**Solutions:**
1. System has insufficient RAM
   ```bash
   # Check available RAM
   free -h  # Linux
   # Reduce chunk size
   extraction_request["chunk_size"] = 10000
   ```

2. Reduce parallelism
   ```python
   extraction_request["num_workers"] = 1
   ```

3. Use manual mode with conservative settings

---

**Issue 2: "Connection Timeout"**

**Symptoms:**
```
OperationalError: (2003, "Can't connect to MySQL server...")
```

**Solutions:**
1. Check network connectivity
   ```bash
   ping database.example.com
   telnet database.example.com 5432
   ```

2. Verify firewall rules
   ```bash
   # Linux
   sudo ufw status
   # Check if port is open
   sudo netstat -tuln | grep 5432
   ```

3. Increase timeout
   ```python
   connection_config["connect_timeout"] = 30
   ```

---

**Issue 3: "SSL Certificate Validation Failed" (Cloud)**

**Symptoms:**
```
SSLError: [SSL: CERTIFICATE_VERIFY_FAILED]
```

**Solutions:**
1. Re-download certificate
   ```bash
   wget https://supplychain.mariadb.com/skysql-chain.pem -O cert.pem
   ```

2. Verify certificate path
   ```python
   import os
   print(os.path.exists(config["ssl_ca"]))  # Should be True
   ```

3. Check certificate expiration
   ```bash
   openssl x509 -in cert.pem -noout -dates
   ```

---

**Issue 4: "Permission Denied"**

**Symptoms:**
```
ProgrammingError: (1142, "SELECT command denied to user...")
```

**Solutions:**
1. Verify grants
   ```sql
   SHOW GRANTS FOR 'readonly_user'@'%';
   ```

2. Re-grant permissions
   ```sql
   GRANT SELECT ON database.* TO 'readonly_user'@'%';
   FLUSH PRIVILEGES;
   ```

3. Check database name
   ```python
   # Ensure config["database"] matches granted database
   ```

---

**Issue 5: "Worker Imbalance" (Sparse PKs)**

**Symptoms:**
```
Worker 1: 200,000 rows in 15s
Worker 2: 100 rows in 1s (90% idle)
```

**Solution:**
Enable quantile sampling (MariaDB only)
```python
# Automatically enabled for MariaDB InnoDB
# Check logs for:
"📊 Calculating quantile boundaries..."
```

---

## 10. Roadmap & Future Extensions

### 10.1 Q2 2026: MongoDB Connector

**Deliverables:**
- ✅ Document-oriented extraction with cursor streaming
- ✅ Aggregation pipeline support for filtering/projection
- ✅ BSON to JSON conversion with type mapping
- ✅ Index-aware query optimization
- ✅ Nested document flattening (configurable depth)

**Target Performance:**
- 15-20k documents/sec for typical workloads
- Memory usage < 3 GB for 1M documents

### 10.2 Q3 2026: AWS S3 Connector

**Deliverables:**
- ✅ Object-based extraction (CSV, JSON, Parquet)
- ✅ Parallel downloads with byte-range requests
- ✅ S3 Select for server-side filtering
- ✅ Automatic file format detection
- ✅ Incremental extraction (new objects only)

**Target Performance:**
- 100 MB/s download throughput (8 parallel workers)
- Support files up to 5 GB

### 10.3 Q4 2026: Advanced Features

**CDC (Change Data Capture):**
- Real-time change tracking for PostgreSQL (logical replication)
- MariaDB binlog parsing for incremental updates
- Upsert/merge logic in Bronze Layer

**Data Quality Checks:**
- Null ratio detection
- Value distribution analysis
- Anomaly detection (outliers, data drift)
- Schema evolution alerts

**Compression Strategies:**
- Zstandard compression (2× better than Snappy)
- Delta encoding for sorted columns
- Dictionary encoding for low-cardinality columns

### 10.4 2027: Enterprise Features

**Distributed Execution:**
- Ray or Dask integration for horizontal scaling
- Multi-node parallel extraction
- Cluster resource management

**Unified Lakehouse Format:**
- Delta Lake support for ACID transactions
- Apache Iceberg for time travel queries
- Hudi integration for incremental processing

**Observability:**
- Prometheus metrics exporter
- Grafana dashboard integration
- Real-time extraction monitoring
- SLA-based alerting

---

## 11. Appendices

### Appendix A: Configuration Examples

#### A.1 PostgreSQL - Full Extraction

```json
{
  "source_type": "postgres",
  "connection_config": {
    "host": "localhost",
    "port": 5432,
    "database": "production_db",
    "user": "readonly_user",
    "password": "${POSTGRES_PASSWORD}",
    "ssl_mode": "require"
  },
  "extraction_request": {
    "entity": "users",
    "mode": "full",
    "partition_column": "user_id",
    "num_workers": 8,
    "chunk_size": 50000
  }
}
```

#### A.2 MariaDB - InnoDB with Quantile Sampling

```json
{
  "source_type": "mariadb",
  "connection_config": {
    "host": "192.168.2.114",
    "port": 3300,
    "database": "production_db",
    "user": "readonly_user",
    "password": "${MARIADB_PASSWORD}"
  },
  "extraction_request": {
    "entity": "orders",
    "mode": "full",
    "enable_parallel": true,
    "avg_row_size": 2048
  }
}
```

#### A.3 MariaDB Cloud - Serverless with SSL

```json
{
  "source_type": "mariadb_cloud",
  "connection_config": {
    "host": "serverless-us-west-2.sysp0000.db1.skysql.com",
    "port": 4020,
    "database": "production_db",
    "user": "idp_reader",
    "password": "${SKYSQL_READONLY_PASSWORD}",
    "ssl_ca": "C:/certs/globalsignrootca.pem",
    "ssl_verify_cert": true,
    "connect_timeout": 30,
    "read_timeout": 60
  },
  "extraction_request": {
    "entity": "customers",
    "mode": "full",
    "enable_parallel": true
  }
}
```

---

### Appendix B: API Reference

#### B.1 BaseConnector Methods

```python
class BaseConnector(ABC):
    def connect(self) -> None
    def validate_credentials(self) -> None
    def extract(self, extraction_plan: Dict) -> Iterator[Dict]
    def close(self) -> None
    def _sanitize_complex_types(self, df: pd.DataFrame) -> pd.DataFrame
```

#### B.2 ExtractionOptimizer Methods

```python
class ExtractionOptimizer:
    def calculate_optimal_params(
        self,
        row_count: int,
        avg_row_size_bytes: int = 1024,
        is_remote: bool = False,
        engine_type: str = "default"
    ) -> Tuple[int, int]
```

#### B.3 Extraction Request Schema

```python
{
    "entity": str,                    # Required: Table/collection name
    "mode": "full" | "incremental",   # Required
    "partition_column": str,          # Optional: For parallel extraction
    "num_workers": int,               # Optional: Override optimizer
    "chunk_size": int,                # Optional: Override optimizer
    "enable_parallel": bool,          # Optional: Default True
    "avg_row_size": int,              # Optional: Hint for optimizer
    "flatten_json": Dict,             # Optional: JSON flattening rules
    "watermark_column": str,          # Required for incremental
    "watermark_value": str            # Required for incremental
}
```

---

### Appendix C: Error Code Index

| Error Code | Description | Common Causes | Solution |
|-----------|-------------|---------------|----------|
| **E001** | Connection Timeout | Network issue, wrong host/port | Check connectivity, verify config |
| **E002** | Authentication Failed | Invalid credentials | Verify username/password |
| **E003** | SSL Certificate Error | Invalid/expired certificate | Re-download certificate |
| **E004** | Permission Denied | Insufficient grants | Grant SELECT permission |
| **E005** | Out of Memory | Large table, insufficient RAM | Reduce chunk size, close apps |
| **E006** | Table Not Found | Wrong table name / database | Verify entity name spelling |
| **E007** | Schema Mismatch | Concurrent DDL during extraction | Re-run extraction |
| **E008** | Serialization Error | Concurrent modifications (MVCC) | Retry with new snapshot |
| **E009** | Network Latency High | Slow network, VPN overhead | Check network, disable VPN |
| **E010** | Worker Imbalance | Sparse primary keys | Enable quantile sampling |

---

### Appendix D: Performance Tuning Guide

#### D.1 Optimization Decision Tree

```
START
  │
  ├─ Is table < 1,000 rows?
  │  └─ YES: Use serial extraction (1 worker)
  │  └─ NO: Continue
  │
  ├─ Is available RAM < 4 GB?
  │  └─ YES: Reduce chunk_size to 10,000
  │  └─ NO: Continue
  │
  ├─ Is database remote (cloud)?
  │  └─ YES: Use 2 workers, large chunks (100k-200k)
  │  └─ NO: Continue
  │
  ├─ Is storage engine MyISAM?
  │  └─ YES: Force serial extraction (prevent table lock)
  │  └─ NO: Continue
  │
  ├─ Is primary key sparse (>10% deleted)?
  │  └─ YES: Enable quantile sampling
  │  └─ NO: Use range splitting
  │
  └─ Use optimizer recommendations
```

#### D.2 Memory Optimization

**Symptoms of Memory Issues:**
- Extraction slows down progressively
- System becomes unresponsive
- "MemoryError" exception

**Solutions (in order of preference):**

1. **Reduce Chunk Size**
   ```python
   extraction_request["chunk_size"] = 10000  # From 50000
   ```

2. **Reduce Parallelism**
   ```python
   extraction_request["num_workers"] = 2  # From 8
   ```

3. **Enable PyArrow Backend** (should be default)
   ```python
   chunk_df = pd.read_sql(query, conn, dtype_backend="pyarrow")
   ```

4. **Close Other Applications**
   - Free up RAM before extraction
   - Use `htop` or Task Manager to identify memory hogs

#### D.3 Network Optimization (Cloud)

**Reduce Network Roundtrips:**

1. **Increase Chunk Size**
   ```python
   extraction_request["chunk_size"] = 200000  # Max for cloud
   ```

2. **Reduce Workers**
   ```python
   extraction_request["num_workers"] = 2  # Cloud optimal
   ```

3. **Use VPN with Caution**
   - VPN adds latency (50-100ms overhead)
   - Disable VPN if possible for extractions

4. **Monitor Latency**
   - Check `network_metrics.average_latency_ms` in metadata
   - Target: < 100ms for cloud databases

---

**Document End**

---

**Version History:**
- v1.0 (Feb 2026): Initial consolidated specification covering PostgreSQL, MariaDB (Self-Hosted), MariaDB Cloud (SkySQL), with placeholders for MongoDB and AWS S3

**Authors:** SyniqAI Data Engineering Team  
**Maintained By:** Platform Infrastructure Group  
**Last Updated:** February 16, 2026

**Contact:**
- Technical Questions: [engineering@syniqai.com]
- Documentation Issues: [docs@syniqai.com]
- Feature Requests: [product@syniqai.com]

---

## Document Metadata

**Classification:** Internal Use  
**Distribution:** Engineering & Product Teams  
**Review Cycle:** Quarterly  
**Next Review:** May 2026

**Related Documents:**
- [PostgreSQL Optimization Best Practices](link)
- [MariaDB Storage Engine Guide](link)
- [Cloud Security Standards](link)
- [Bronze Layer Data Quality Specification](link)

---

*This document serves as the authoritative reference for all data ingestion connectors in the SyniqAI platform. All connector implementations must conform to the specifications, patterns, and best practices outlined herein.*
