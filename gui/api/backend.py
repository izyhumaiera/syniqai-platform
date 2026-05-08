"""
FastAPI Backend for Gold Layer Dashboard
Provides REST API endpoints for the React frontend
Orchestrates data ingestion, processing, and analytics
"""

# Fix Windows console encoding for Unicode/emoji support
import sys
import os
if os.name == 'nt':  # Windows
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except:
        pass

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import json
import asyncio
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, ValidationError
import logging
from dotenv import load_dotenv
from datetime import datetime, timedelta

# Load environment variables
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_path)

# Configure Java for Spark (CRITICAL: FORCE Java 17 for Spark 3.5+)
if os.name == 'nt':  # Windows
    # Search candidate paths for Java 17 (covers different install locations)
    _java_candidates = [
        os.getenv("JAVA_HOME", ""),                                                         # env var first
        r"C:\Program Files\Eclipse Adoptium\jdk-17.0.18.8-hotspot",                        # system-wide install
        r"C:\Program Files\Eclipse Adoptium\jdk-17.0.14.7-hotspot",
        r"C:\Program Files\Microsoft\jdk-17.0.11.9-hotspot",
        r"C:\Program Files\Java\jdk-17",
    ]
    java_17_path = next((p for p in _java_candidates if p and os.path.exists(p)), None)

    if java_17_path:
        os.environ['JAVA_HOME'] = java_17_path
        os.environ['PATH'] = f"{java_17_path}\\bin;{os.environ.get('PATH', '')}"
        print("[OK] Java 17 configured: " + java_17_path)
    else:
        print("[ERROR] Java 17 not found. Install from https://adoptium.net/temurin/releases/?version=17")
        raise RuntimeError("Java 17 is required for Spark 3.5+")
else:
    if 'JAVA_HOME' not in os.environ:
        print("[WARN] JAVA_HOME not set. Please install Java 17.")
        print("   Download Java 17: https://adoptium.net/temurin/releases/?version=17")

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Silence noisy kafka-python connection-retry logs (these are expected when Kafka is
# temporarily unavailable — the bridge already logs a clean warning on failure)
logging.getLogger("kafka").setLevel(logging.ERROR)
logging.getLogger("kafka.conn").setLevel(logging.ERROR)
logging.getLogger("kafka.client").setLevel(logging.ERROR)

# Log Java configuration status
java_home = os.environ.get('JAVA_HOME', 'NOT SET')
logger.info(f"🔍 JAVA_HOME = {java_home}")
if 'JAVA_HOME' in os.environ:
    logger.info(f"✓ Java is configured and ready for Spark")
else:
    logger.warning(f"⚠️ JAVA_HOME not set - Spark transformations will fail")

# Import new backend infrastructure BEFORE modifying sys.path
from app_config import config
from database import db_manager, rules_repo, quarantine_repo, execution_log_repo, initialize_database
import storage

# Import local modules
from job_tracker import JobTracker
from ingestion_service import IngestionService
from silver_job_tracker import SilverJobTracker, job_tracker as silver_job_tracker
from silver_service import SilverProcessingService
from minio_utils import MinIOClient
from bronze_eda import generate_bronze_eda
from gold_eda_service import GoldEDAService
from kafka_startup_service import get_kafka_startup_service

# Add Gold layer path AFTER importing local modules
gold_layer_path = Path(__file__).parent.parent.parent / "data lakehouse" / "syniq_project"
sys.path.append(str(gold_layer_path))

# Add Kafka Integration path
kafka_integration_path = Path(__file__).parent.parent.parent / "Kafka Integration"
sys.path.append(str(kafka_integration_path))

# Helper function to find Java 17 installation
def _find_java_17() -> Optional[str]:
    """Find Java 17 installation on the system."""
    if os.name == 'nt':  # Windows
        java_home = os.environ.get('JAVA_HOME', '')
        if java_home and os.path.isfile(os.path.join(java_home, 'bin', 'java.exe')):
            return java_home
        # Search common locations
        import glob
        search_bases = [
            os.path.expandvars(r"%LOCALAPPDATA%\Programs\Eclipse Adoptium"),
            r"C:\Program Files\Eclipse Adoptium",
            r"C:\Program Files\Java",
            r"C:\Users\Syarifah\AppData\Local\Programs\Eclipse Adoptium",
        ]
        for base in search_bases:
            for pattern in ("jdk-17*", "jdk17*"):
                for path in glob.glob(os.path.join(base, pattern)):
                    if os.path.isfile(os.path.join(path, 'bin', 'java.exe')):
                        return path
    return None

# Import Gold layer modules
try:
    from ingestion.gold_eda_engine import GoldEDAEngine
    from ingestion.gold_aggregator import GoldAggregator
    from ingestion.gold_report_generator import GoldReportGenerator
except ImportError:
    logger.warning("Gold layer modules not found. API will return mock data.")
    GoldEDAEngine = None
    GoldAggregator = None
    GoldReportGenerator = None

# Import Kafka Integration components (optional - gracefully fails if Kafka unavailable)
try:
    from kafka_routes import router as kafka_router
    from kafka_bridge import get_kafka_bridge
    logger.info("✓ Kafka Integration modules loaded")
    KAFKA_AVAILABLE = True
except ImportError as e:
    logger.warning(f"⚠ Kafka Integration not available: {e}")
    logger.warning("  Ingestion will continue without Kafka streaming")
    kafka_router = None
    get_kafka_bridge = None
    KAFKA_AVAILABLE = False

# Import MongoDB CDC routes
try:
    from mongodb_routes import router as mongodb_router
    logger.info("✓ MongoDB CDC routes loaded")
    MONGODB_CDC_AVAILABLE = True
except ImportError as e:
    logger.warning(f"⚠ MongoDB CDC routes not available: {e}")
    mongodb_router = None
    MONGODB_CDC_AVAILABLE = False

# Import Silver Transformation routes
try:
    from silver_transformation_routes import router as silver_transform_router
    logger.info("✓ Silver Transformation routes loaded")
    SILVER_TRANSFORM_AVAILABLE = True
except ImportError as e:
    logger.warning(f"⚠ Silver Transformation routes not available: {e}")
    silver_transform_router = None
    SILVER_TRANSFORM_AVAILABLE = False

# Import Silver Dashboard routes
try:
    from silver_dashboard_routes import router as silver_dashboard_router
    logger.info("✓ Silver Dashboard routes loaded")
    SILVER_DASHBOARD_AVAILABLE = True
except ImportError as e:
    logger.warning(f"⚠ Silver Dashboard routes not available: {e}")
    silver_dashboard_router = None
    SILVER_DASHBOARD_AVAILABLE = False

# Import Data Lineage routes
try:
    from lineage_routes import router as lineage_router
    logger.info("✓ Data Lineage routes loaded")
    LINEAGE_AVAILABLE = True
except ImportError as e:
    logger.warning(f"⚠ Data Lineage routes not available: {e}")
    lineage_router = None
    LINEAGE_AVAILABLE = False

# Import Kafka Schema History routes
try:
    from kafka_schema_history_routes import router as kafka_schema_history_router
    logger.info("✓ Kafka Schema History routes loaded")
    KAFKA_SCHEMA_HISTORY_AVAILABLE = True
except ImportError as e:
    logger.warning(f"⚠ Kafka Schema History routes not available: {e}")
    kafka_schema_history_router = None
    KAFKA_SCHEMA_HISTORY_AVAILABLE = False

# Import Query Validation routes
try:
    from query_validation_routes import router as query_validation_router
    logger.info("✓ Query Validation routes loaded")
    QUERY_VALIDATION_AVAILABLE = True
except ImportError as e:
    logger.warning(f"⚠ Query Validation routes not available: {e}")
    query_validation_router = None
    QUERY_VALIDATION_AVAILABLE = False

# Import Bronze Data Inspection routes
try:
    from bronze_data_routes import router as bronze_data_router
    logger.info("✓ Bronze Data Inspection routes loaded")
    BRONZE_DATA_AVAILABLE = True
except ImportError as e:
    logger.warning(f"⚠ Bronze Data Inspection routes not available: {e}")
    bronze_data_router = None
    BRONZE_DATA_AVAILABLE = False

# Import Bronze Ready Emitter routes
try:
    from bronze_ready_routes import router as bronze_ready_router
    logger.info("✓ Bronze Ready Emitter routes loaded")
    BRONZE_READY_AVAILABLE = True
except ImportError as e:
    logger.warning(f"⚠ Bronze Ready Emitter routes not available: {e}")
    bronze_ready_router = None
    BRONZE_READY_AVAILABLE = False

# Import CDC Control routes
try:
    from cdc_control_routes import router as cdc_control_router
    logger.info("✓ CDC Control routes loaded")
    CDC_CONTROL_AVAILABLE = True
except ImportError as e:
    logger.warning(f"⚠ CDC Control routes not available: {e}")
    cdc_control_router = None
    CDC_CONTROL_AVAILABLE = False

# Import SQL Query Execution routes
try:
    from sql_query_routes import router as sql_query_router
    logger.info("✓ SQL Query routes loaded")
    SQL_QUERY_AVAILABLE = True
except ImportError as e:
    logger.warning(f"⚠ SQL Query routes not available: {e}")
    sql_query_router = None
    SQL_QUERY_AVAILABLE = False

# Import Quality Rules routes
try:
    from quality_rules_routes import router as quality_rules_router
    logger.info("✓ Quality Rules routes loaded")
    QUALITY_RULES_AVAILABLE = True
except ImportError as e:
    logger.warning(f"⚠ Quality Rules routes not available: {e}")
    quality_rules_router = None
    QUALITY_RULES_AVAILABLE = False

# Import Unstructured Processing routes
try:
    from unstructured_router import router as unstructured_router, setup_unstructured_router
    logger.info("✓ Unstructured Processing routes loaded")
    UNSTRUCTURED_AVAILABLE = True
except ImportError as e:
    logger.warning(f"⚠ Unstructured Processing routes not available: {e}")
    unstructured_router = None
    setup_unstructured_router = None
    UNSTRUCTURED_AVAILABLE = False

# Import Missing Endpoints (additional unstructured endpoints)
try:
    from missing_endpoints import router as missing_endpoints_router
    logger.info("✓ Missing Endpoints routes loaded")
    MISSING_ENDPOINTS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"⚠ Missing Endpoints routes not available: {e}")
    missing_endpoints_router = None
    MISSING_ENDPOINTS_AVAILABLE = False

# Import Gold Transformation routes
try:
    from gold_transformation_routes import router as gold_transform_router
    logger.info("✓ Gold Transformation routes loaded")
    GOLD_TRANSFORM_AVAILABLE = True
except ImportError as e:
    logger.warning(f"⚠ Gold Transformation routes not available: {e}")
    gold_transform_router = None
    GOLD_TRANSFORM_AVAILABLE = False

# Import Reports routes
try:
    from reports_routes import router as reports_router
    logger.info("✓ Reports routes loaded")
    REPORTS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"⚠ Reports routes not available: {e}")
    reports_router = None
    REPORTS_AVAILABLE = False

# Import Test Lineage routes
try:
    from test_lineage import router as test_lineage_router
    logger.info("✓ Test Lineage routes loaded")
    TEST_LINEAGE_AVAILABLE = True
except ImportError as e:
    logger.warning(f"⚠ Test Lineage routes not available: {e}")
    test_lineage_router = None
    TEST_LINEAGE_AVAILABLE = False

# Import Airflow proxy routes
try:
    from airflow_routes import router as airflow_router
    logger.info("✓ Airflow proxy routes loaded")
    AIRFLOW_PROXY_AVAILABLE = True
except ImportError as e:
    logger.warning(f"⚠ Airflow proxy routes not available: {e}")
    airflow_router = None
    AIRFLOW_PROXY_AVAILABLE = False

# Import Manual Input routes (Universal data ingestion)
try:
    from manual_input_routes import router as manual_input_router
    logger.info("✓ Manual Input routes loaded")
    MANUAL_INPUT_AVAILABLE = True
except ImportError as e:
    logger.warning(f"⚠ Manual Input routes not available: {e}")
    manual_input_router = None
    MANUAL_INPUT_AVAILABLE = False

# Import AI Processing Control routes
try:
    from ai_processing_routes import router as ai_processing_router
    logger.info("✓ AI Processing Control routes loaded")
    AI_PROCESSING_AVAILABLE = True
except ImportError as e:
    logger.warning(f"⚠ AI Processing Control routes not available: {e}")
    ai_processing_router = None
    AI_PROCESSING_AVAILABLE = False

# Import Debezium Connector Management routes
try:
    from debezium_routes import router as debezium_router
    logger.info("✓ Debezium Connector Management routes loaded")
    DEBEZIUM_ROUTES_AVAILABLE = True
except ImportError as e:
    logger.warning(f"⚠ Debezium Connector Management routes not available: {e}")
    debezium_router = None
    DEBEZIUM_ROUTES_AVAILABLE = False

# Import CDC to Silver Layer routes
try:
    from cdc_silver_routes import router as cdc_silver_router, set_cdc_silver_service
    logger.info("✓ CDC to Silver Layer routes loaded")
    CDC_SILVER_ROUTES_AVAILABLE = True
except ImportError as e:
    logger.warning(f"⚠ CDC to Silver Layer routes not available: {e}")
    cdc_silver_router = None
    set_cdc_silver_service = None
    CDC_SILVER_ROUTES_AVAILABLE = False

app = FastAPI(
    title="SyniqAI Data Lakehouse API",
    description="REST API for data ingestion, processing, and analytics",
    version="2.0.0"
)

# CORS configuration for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "http://localhost:5173", "http://localhost:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Kafka router if available
if KAFKA_AVAILABLE and kafka_router:
    app.include_router(kafka_router, prefix="/api/kafka", tags=["Kafka"])
    logger.info("✓ Kafka API routes mounted at /api/kafka")

# Mount MongoDB CDC router if available
if MONGODB_CDC_AVAILABLE and mongodb_router:
    app.include_router(mongodb_router, prefix="/api", tags=["MongoDB CDC"])
    logger.info("✓ MongoDB CDC API routes mounted at /api/mongodb")

# Mount Silver Transformation router if available
if SILVER_TRANSFORM_AVAILABLE and silver_transform_router:
    app.include_router(silver_transform_router, prefix="/api", tags=["Silver Transformation"])
    logger.info("✓ Silver Transformation API routes mounted at /api/silver")

# Mount Silver Dashboard router if available
if SILVER_DASHBOARD_AVAILABLE and silver_dashboard_router:
    app.include_router(silver_dashboard_router, prefix="/api/silver", tags=["Silver Dashboard"])
    logger.info("✓ Silver Dashboard API routes mounted at /api/silver")

# Mount Data Lineage router if available
if LINEAGE_AVAILABLE and lineage_router:
    app.include_router(lineage_router, prefix="/api", tags=["Data Lineage"])
    logger.info("✓ Data Lineage API routes mounted at /api/lineage")

# Mount Kafka Schema History router if available
if KAFKA_SCHEMA_HISTORY_AVAILABLE and kafka_schema_history_router:
    app.include_router(kafka_schema_history_router, prefix="/api/bronze", tags=["Bronze Schema History"])
    logger.info("✓ Kafka Schema History API routes mounted at /api/bronze")

# Mount Query Validation router if available
if QUERY_VALIDATION_AVAILABLE and query_validation_router:
    app.include_router(query_validation_router, prefix="/api/query", tags=["Query Validation"])
    logger.info("✓ Query Validation API routes mounted at /api/query")

# Mount Bronze Data Inspection router if available
if BRONZE_DATA_AVAILABLE and bronze_data_router:
    app.include_router(bronze_data_router, prefix="/api/bronze-data", tags=["Bronze Data Inspection"])
    logger.info("✓ Bronze Data Inspection API routes mounted at /api/bronze-data")

# Mount Bronze Ready Emitter router if available
if BRONZE_READY_AVAILABLE and bronze_ready_router:
    app.include_router(bronze_ready_router, prefix="/api/bronze-ready", tags=["Bronze Ready Emitter"])
    logger.info("✓ Bronze Ready Emitter API routes mounted at /api/bronze-ready")

# Mount CDC Control router if available
if CDC_CONTROL_AVAILABLE and cdc_control_router:
    app.include_router(cdc_control_router, prefix="/api/cdc", tags=["CDC Control"])
    logger.info("✓ CDC Control API routes mounted at /api/cdc")

# Mount SQL Query Execution router if available
if SQL_QUERY_AVAILABLE and sql_query_router:
    app.include_router(sql_query_router, prefix="/api", tags=["SQL Query Execution"])
    logger.info("✓ SQL Query Execution API routes mounted at /api/sql")
    print("=" * 70)
    print("🔧 SQL QUERY ROUTES REGISTERED:")
    for route in sql_query_router.routes:
        print(f"   {route.methods} {route.path}")
    print("=" * 70)
else:
    logger.error(f"❌ SQL Query router NOT mounted! SQL_QUERY_AVAILABLE={SQL_QUERY_AVAILABLE}, router={sql_query_router}")

# Mount Quality Rules router if available
if QUALITY_RULES_AVAILABLE and quality_rules_router:
    app.include_router(quality_rules_router, tags=["Quality Rules"])
    logger.info("✓ Quality Rules API routes mounted at /api/quality-rules")
    print("=" * 70)
    print("🛡️ QUALITY RULES ROUTES REGISTERED:")
    for route in quality_rules_router.routes:
        print(f"   {route.methods} {route.path}")
    print("=" * 70)
else:
    logger.error(f"❌ Quality Rules router NOT mounted! QUALITY_RULES_AVAILABLE={QUALITY_RULES_AVAILABLE}")

# Mount Unstructured Processing router if available
if UNSTRUCTURED_AVAILABLE and unstructured_router:
    # Router will be set up during startup event with proper dependencies
    app.include_router(unstructured_router, prefix="/api/silver/unstructured", tags=["Unstructured Silver"])
    logger.info("✓ Unstructured Processing API routes mounted at /api/silver/unstructured")

# Mount Missing Endpoints router if available
if MISSING_ENDPOINTS_AVAILABLE and missing_endpoints_router:
    app.include_router(missing_endpoints_router, tags=["Missing Endpoints"])
    logger.info("✓ Missing Endpoints routes mounted (Media Dashboard, File Browser, Audio Analysis)")

# Mount Gold Transformation router if available
if GOLD_TRANSFORM_AVAILABLE and gold_transform_router:
    app.include_router(gold_transform_router, prefix="/api", tags=["Gold Transformation"])
    logger.info("✓ Gold Transformation API routes mounted at /api/gold")

# Mount Reports router if available
if REPORTS_AVAILABLE and reports_router:
    app.include_router(reports_router, prefix="/api", tags=["Reports"])
    logger.info("✓ Reports API routes mounted at /api/reports")

# Mount Test Lineage router if available
if TEST_LINEAGE_AVAILABLE and test_lineage_router:
    app.include_router(test_lineage_router, prefix="/api", tags=["Test"])
    logger.info("✓ Test Lineage API routes mounted at /api/test")

# Mount Airflow proxy router
if AIRFLOW_PROXY_AVAILABLE and airflow_router:
    app.include_router(airflow_router, prefix="/api/airflow", tags=["Airflow Proxy"])
    logger.info("✓ Airflow proxy routes mounted at /api/airflow")

# Mount Manual Input router (Universal data ingestion)
if MANUAL_INPUT_AVAILABLE and manual_input_router:
    app.include_router(manual_input_router, prefix="/api", tags=["Manual Input"])
    logger.info("✓ Manual Input API routes mounted at /api/ingest/manual")

# Mount AI Processing Control router
if AI_PROCESSING_AVAILABLE and ai_processing_router:
    app.include_router(ai_processing_router, prefix="/api", tags=["AI Processing"])
    logger.info("✓ AI Processing Control API routes mounted at /api/silver/processing")

# Mount Debezium Connector Management router
if DEBEZIUM_ROUTES_AVAILABLE and debezium_router:
    app.include_router(debezium_router, prefix="/api/debezium", tags=["Debezium CDC"])
    logger.info("✓ Debezium Connector Management API routes mounted at /api/debezium")

# Mount CDC to Silver Layer router
if CDC_SILVER_ROUTES_AVAILABLE and cdc_silver_router:
    app.include_router(cdc_silver_router, prefix="/api", tags=["CDC to Silver"])
    logger.info("✓ CDC to Silver Layer API routes mounted at /api/cdc-silver")

# Declare services as global variables to be initialized at startup
# Note: silver_job_tracker is already imported as a singleton above
ingestion_service = None
silver_service = None
gold_eda_service = None
aggregator = None
job_tracker = None
kafka_bridge = None
kafka_startup_service = None
cdc_silver_service = None  # CDC to Silver service

# Initialize database and storage on startup
@app.on_event("startup")
async def startup_event():
    """Initialize backend services on startup"""
    global ingestion_service, silver_service, gold_eda_service, aggregator, job_tracker, kafka_bridge, kafka_startup_service, cdc_silver_service
    
    logger.info("Initializing SyniqAI backend services...")
    
    # Initialize database
    if initialize_database():
        logger.info("✓ PostgreSQL database initialized")
    else:
        logger.warning("⚠ Database initialization failed")
    
    # Initialize storage
    if storage.initialize_storage():
        logger.info("✓ MinIO storage initialized")
    else:
        logger.warning("⚠ Storage initialization failed")
    
    # Start AI Processor automatically
    import subprocess
    import sys
    from pathlib import Path
    
    ai_processor_path = Path(__file__).resolve().parent.parent.parent / "ai processing" / "ai_processor.py"
    if ai_processor_path.exists():
        try:
            subprocess.Popen(
                [sys.executable, str(ai_processor_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0
            )
            logger.info("✓ AI Processor started automatically")
        except Exception as e:
            logger.warning(f"⚠ Failed to start AI Processor: {e}")
    else:
        logger.warning(f"⚠ AI Processor not found at {ai_processor_path}")
    
    # Initialize job trackers
    job_tracker = JobTracker("jobs.db")
    # Note: silver_job_tracker imported as singleton from silver_job_tracker module
    logger.info(f"✓ Using silver_job_tracker singleton (TTL={silver_job_tracker.ttl_hours}h)")
    
    # Initialize MinIO client for silver service (needs the updated read_parquet logic)
    minio_client = MinIOClient(
        endpoint=config.minio.endpoint,
        access_key=config.minio.access_key,
        secret_key=config.minio.secret_key,
        secure=config.minio.secure
    )
    
    # NATIVE KAFKA CONNECTION (NO DOCKER)
    logger.info("🔍 Checking native Kafka broker...")
    kafka_startup_service = None  # Disabled Docker-based startup
    
    # Check if native Kafka broker is running on port 9092
    import socket
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex(('127.0.0.1', 9092))
        sock.close()
        
        if result == 0:
            logger.info("✓ Native Kafka broker detected at 127.0.0.1:9092 (No Docker required)")
        else:
            logger.warning("⚠ Native Kafka broker not detected on port 9092")
            logger.warning("  Start Kafka: cd C:\\kafka\\kafka-4.2.0; .\\bin\\windows\\kafka-server-start.bat .\\config\\server.properties")
    except Exception as e:
        logger.warning(f"⚠ Kafka connection check failed: {e}")
    
    # Initialize Kafka bridge if available (DISABLED for native Kafka CDC)
    kafka_bridge = None  # Disabled - native CDC connectors handle Kafka directly
    logger.info("ℹ Kafka bridge disabled - using native CDC connectors for Kafka publishing")
    
    # Initialize services (pass kafka_startup_service to ingestion_service)
    ingestion_service = IngestionService(
        storage.storage_manager, 
        job_tracker, 
        kafka_bridge=kafka_bridge,
        kafka_startup_service=kafka_startup_service  # NEW!
    )
    silver_service = SilverProcessingService(minio_client, silver_job_tracker)
    gold_eda_service = GoldEDAService(minio_client)
    
    # Initialize CDC to Silver service
    if CDC_SILVER_ROUTES_AVAILABLE:
        try:
            from cdc_silver_service import get_cdc_silver_service
            cdc_silver_service = get_cdc_silver_service(minio_client, silver_job_tracker)
            # Set the service instance in the routes module
            set_cdc_silver_service(cdc_silver_service)
            logger.info("✓ CDC to Silver service initialized")
        except Exception as e:
            logger.warning(f"⚠ Failed to initialize CDC to Silver service: {e}")
            cdc_silver_service = None
    
    # Initialize Gold layer aggregator if available
    bronze_path = gold_layer_path / "bronze"
    silver_path = gold_layer_path / "silver"
    gold_path = gold_layer_path / "gold"
    for path in [bronze_path, silver_path, gold_path]:
        path.mkdir(parents=True, exist_ok=True)
    
    if GoldAggregator:
        aggregator = GoldAggregator(str(silver_path), str(gold_path))
    
    # Setup Unstructured Processing Router if available
    if UNSTRUCTURED_AVAILABLE and setup_unstructured_router:
        try:
            setup_unstructured_router(
                silver_job_tracker=silver_job_tracker,
                config=config,
                gold_layer_path=gold_layer_path
            )
            logger.info("✓ Unstructured Processing Router configured")
        except Exception as e:
            logger.warning(f"⚠ Failed to setup Unstructured Router: {e}")
    
    logger.info("✓ All services initialized")
    logger.info("Backend services ready!")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global kafka_bridge
    
    # Close Kafka bridge gracefully
    if kafka_bridge:
        try:
            kafka_bridge.close()
            logger.info("✓ Kafka bridge closed")
        except Exception as e:
            logger.warning(f"⚠ Error closing Kafka bridge: {e}")

# Pydantic models for request/response
class ConnectionTestRequest(BaseModel):
    source_type: str
    # Database fields
    host: str = None
    port: int = None
    database: str = None
    user: str = None
    password: str = None
    ssl_ca: str = None  # SSL certificate path for cloud databases
    # S3 fields
    s3_bucket: str = None
    s3_prefix: str = None
    aws_access_key: str = None
    aws_secret_key: str = None
    aws_region: str = None
    # MongoDB fields
    mongo_uri: str = None
    collection: str = None
    query: str = None
    flatten_documents: bool = None
    chunk_size: int = None

class IngestionRequest(BaseModel):
    source_type: str
    connection_config: Dict[str, Any]
    extraction_request: Dict[str, Any]
    domain: str = "general"  # Default to general domain
    enable_cdc: bool = False  # Whether to auto-create CDC connector


@app.get("/")
def read_root():
    """Health check endpoint"""
    try:
        minio_status = storage.storage_manager.check_connection()
        job_stats = job_tracker.get_statistics() if job_tracker else {"by_status": {}}
        
        return {
            "status": "operational",
            "service": "SyniqAI Data Lakehouse API",
            "version": "2.0.0",
            "minio_connected": minio_status.get("success", False),
            "minio_buckets": minio_status.get("buckets", []),
            "total_jobs": sum(job_stats.get("by_status", {}).values()),
            "gold_layer_available": GoldAggregator is not None
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "operational",
            "service": "SyniqAI Data Lakehouse API",
            "version": "2.0.0",
            "note": "Some services may be initializing"
        }


# ==================== CONFIGURATION ENDPOINTS ====================

@app.get("/api/config/minio")
def get_minio_config():
    """Get MinIO configuration and status"""
    return minio_client.check_connection()


# ==================== CONNECTION TEST ENDPOINTS ====================

@app.post("/api/connection/test")
async def test_connection(request: ConnectionTestRequest):
    """Test database connection before ingestion"""
    try:
        # Log based on source type
        if request.source_type == 'mongodb':
            logger.info(f"Testing {request.source_type} connection to {request.mongo_uri}")
            logger.info(f"Connection config: mongo_uri={request.mongo_uri}, database={request.database}, collection={request.collection}")
        elif request.source_type == 's3':
            logger.info(f"Testing {request.source_type} connection to bucket={request.s3_bucket}")
        else:
            logger.info(f"Testing {request.source_type} connection to {request.host}:{request.port}")
            logger.info(f"Connection config: host={request.host}, port={request.port}, database={request.database}, user={request.user}, ssl_ca={request.ssl_ca}")
        
        config = request.dict()
        
        # Call ingestion service
        result = ingestion_service.test_connection(request.source_type, config)
        
        if result.get("success"):
            logger.info(f"Connection test successful: {result.get('total_tables', 0)} collections/tables found")
        else:
            logger.error(f"Connection test failed: {result.get('error', 'Unknown error')}")
        
        return result
        
    except ValidationError as ve:
        logger.error(f"Validation error: {ve}", exc_info=True)
        return {
            "success": False,
            "error": str(ve),
            "message": "Validation error: Check your input fields",
            "error_type": "ValidationError"
        }
    except Exception as e:
        logger.error(f"Connection test exception: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "message": "Connection test failed with exception",
            "error_type": type(e).__name__
        }


# ==================== INGESTION ENDPOINTS ====================

@app.post("/api/ingestion/start")
def start_ingestion(request: IngestionRequest, background_tasks: BackgroundTasks):
    """Start data ingestion job"""
    try:
        cdc_status = "with CDC" if request.enable_cdc else "without CDC"
        logger.info(f"🔍 Ingestion request - Source: {request.source_type}, Domain: {request.domain}, CDC: {cdc_status}")
        # Start ingestion in background
        job_id = ingestion_service.start_ingestion(
            request.source_type,
            request.connection_config,
            request.extraction_request,
            request.domain,
            request.enable_cdc  # NEW: Pass CDC flag
        )
        
        return {
            "job_id": job_id,
            "status": "running",
            "source": request.source_type,
            "entity": request.extraction_request.get("entity"),
            "message": "Ingestion started successfully" + (" (CDC enabled)" if request.enable_cdc else "")
        }
    except Exception as e:
        logger.error(f"Ingestion start error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/ingestion/status/{job_id}")
def get_ingestion_status(job_id: str):
    """Get status of an ingestion job"""
    try:
        job = job_tracker.get_job(job_id)
        
        if not job:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        
        # Calculate progress percentage
        progress_percent = 0
        if job.get('total_rows') and job.get('total_rows') > 0:
            progress_percent = (job.get('rows_processed', 0) / job['total_rows']) * 100
        
        return {
            "job_id": job['job_id'],
            "status": job['status'],
            "progress": {
                "rows_processed": job.get('rows_processed', 0),
                "total_rows": job.get('total_rows', 0),
                "progress_percent": round(progress_percent, 1),
                "chunks_written": job.get('chunks_written', 0),
                "duration_seconds": job.get('duration_seconds', 0)
            },
            "minio_location": job.get('minio_location'),
            "error_message": job.get('error_message'),
            "started_at": job.get('started_at'),
            "completed_at": job.get('completed_at')
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/ingestion/logs/{job_id}")
def get_ingestion_logs(job_id: str):
    """Get logs for an ingestion job"""
    try:
        logs = job_tracker.get_logs(job_id)
        return {"job_id": job_id, "logs": logs}
    except Exception as e:
        logger.error(f"Error getting logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/ingestion/jobs")
def list_ingestion_jobs(status: str = None, limit: int = 50):
    """List ingestion jobs"""
    try:
        jobs = job_tracker.list_jobs(status=status, job_type="ingestion", limit=limit)
        return {"jobs": jobs, "total": len(jobs)}
    except Exception as e:
        logger.error(f"Error listing jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/ingestion/connectors/s3")
def get_saved_s3_connectors():
    """Return distinct S3 connector configs from previously run ingestion jobs.
    Allows Feature Pipeline to auto-populate S3 credentials without re-entering them."""
    try:
        jobs = job_tracker.list_jobs(job_type="ingestion", limit=200)
        seen = {}
        for job in jobs:
            cfg = job.get("connection_config") or {}
            # Support both flat and nested formats
            bucket = (
                cfg.get("s3_bucket") or cfg.get("bucket") or
                job.get("s3_bucket") or ""
            )
            key = (
                cfg.get("aws_access_key") or cfg.get("aws_access_key_id") or
                job.get("aws_access_key") or ""
            )
            secret = (
                cfg.get("aws_secret_key") or cfg.get("aws_secret_access_key") or
                job.get("aws_secret_key") or ""
            )
            region = (
                cfg.get("aws_region") or cfg.get("region_name") or
                job.get("aws_region") or "ap-southeast-1"
            )
            source_name = job.get("source_name") or job.get("entity") or bucket
            if bucket and key and bucket not in seen:
                seen[bucket] = {
                    "source_name": source_name,
                    "s3_bucket": bucket,
                    "aws_access_key": key,
                    "aws_secret_key": secret,
                    "aws_region": region.strip(),
                    "s3_prefix": cfg.get("s3_prefix") or cfg.get("prefix") or "",
                }
        # Also include the well-known config from the data ingestion s3_config.json
        import json as _json, os as _os
        config_path = _os.path.join(
            _os.path.dirname(__file__), "..", "..",
            "data ingestion", "Connector", "s3_config.json"
        )
        if _os.path.isfile(config_path):
            try:
                with open(config_path) as f:
                    file_cfg = _json.load(f)
                b = file_cfg.get("s3_bucket", "")
                k = file_cfg.get("aws_access_key", "")
                if b and k and b not in seen:
                    seen[b] = {
                        "source_name": file_cfg.get("source_name", b),
                        "s3_bucket": b,
                        "aws_access_key": k,
                        "aws_secret_key": file_cfg.get("aws_secret_key", ""),
                        "aws_region": file_cfg.get("aws_region", "ap-southeast-1").strip(),
                        "s3_prefix": file_cfg.get("s3_prefix", ""),
                    }
            except Exception:
                pass
        return {"connectors": list(seen.values())}
    except Exception as e:
        logger.error(f"Error fetching S3 connectors: {e}")
        return {"connectors": []}


# ==================== TABLE LISTING ENDPOINTS ====================

@app.get("/api/tables/{layer}")
def list_tables(layer: str):
    """List all tables in a specific layer (bronze/silver/gold)"""
    try:
        if layer not in ["bronze", "silver", "gold"]:
            raise HTTPException(status_code=400, detail="Layer must be bronze, silver, or gold")
        
        tables = []
        
        if layer == "bronze":
            # Get all bronze tables across all domains
            bronze_mgr = storage.get_bronze_manager()
            domains = ["finance", "healthcare", "general"]
            
            for domain in domains:
                try:
                    domain_tables = bronze_mgr.list_tables(domain)
                    for table in domain_tables:
                        tables.append({
                            "name": table["table_name"],
                            "domain": domain,
                            "file_count": table.get("file_count", 0),
                            "total_size": table.get("total_size", 0),
                            "last_modified": table.get("last_modified", "")
                        })
                except Exception as e:
                    logger.warning(f"Error listing {domain} tables: {e}")
                    continue
        
        elif layer == "silver":
            # List silver tables from MinIO silver bucket
            try:
                storage_mgr = storage.storage_manager
                objects = storage_mgr.list_objects("silver")
                for obj in objects:
                    if obj.endswith(".parquet"):
                        # Extract domain and table name from path
                        parts = obj.split("/")
                        if len(parts) >= 2:
                            tables.append({
                                "name": parts[-1].replace(".parquet", ""),
                                "domain": parts[0] if len(parts) > 1 else "unknown",
                                "size": 0,
                                "path": obj
                            })
            except Exception as e:
                logger.warning(f"Error listing silver tables: {e}")
        
        elif layer == "gold":
            # List gold tables
            if gold_eda_service:
                try:
                    gold_tables = gold_eda_service.list_available_tables()
                    tables = [{"name": t, "source": "gold"} for t in gold_tables]
                except Exception as e:
                    logger.warning(f"Error listing gold tables: {e}")
        
        return {"layer": layer, "tables": tables, "total": len(tables)}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing tables: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/tables/{layer}/{source}/{entity}")
def get_table_info(layer: str, source: str, entity: str):
    """Get information about a specific table"""
    try:
        if layer == "bronze":
            bronze_mgr = storage.get_bronze_manager()
            # source is domain here
            info = bronze_mgr.get_table_schema(source, entity)
            return info
        elif layer == "silver":
            # Return silver table info
            return {"layer": "silver", "domain": source, "table": entity}
        elif layer == "gold":
            # Return gold table info
            return {"layer": "gold", "source": source, "table": entity}
        else:
            raise HTTPException(status_code=404, detail=f"Table {source}.{entity} not found in {layer}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting table info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== SILVER LAYER PROCESSING ENDPOINTS ====================

@app.post("/api/silver/process")
def process_to_silver(source: str, entity: str, source_type: str = "postgres"):
    """
    Process a Bronze table to Silver layer.
    
    Args:
        source: Source system name (e.g., 'postgres')
        entity: Entity/table name
        source_type: Type of source (postgres, mongodb, s3, etc.)
    
    Returns:
        Job ID for tracking
    """
    try:
        job_id = silver_service.process_to_silver(source, entity, source_type)
        return {
            "job_id": job_id,
            "status": "queued",
            "message": f"Silver processing started for {source}.{entity}",
            "table_name": f"{source}.{entity}"
        }
    except Exception as e:
        logger.error(f"Error starting silver processing: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/silver/status/{job_id}")
def get_silver_job_status(job_id: str):
    """Get the status of a silver processing job"""
    try:
        job = silver_job_tracker.get_job(job_id)
        
        if not job:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        
        return job
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/silver/jobs")
def list_silver_jobs(status: str = None, limit: int = 50):
    """List silver processing jobs"""
    try:
        jobs = silver_job_tracker.list_jobs(limit=limit, status=status)
        return {
            "jobs": jobs,
            "total": len(jobs)
        }
    except Exception as e:
        logger.error(f"Error listing silver jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/silver/view/{source}/{entity}")
def view_silver_data(source: str, entity: str, page: int = 1, page_size: int = 100):
    """
    View Silver data with preview and statistics.
    
    Args:
        source: Source system name
        entity: Entity/table name
        page: Page number (1-indexed)
        page_size: Rows per page
    
    Returns:
        Data preview with statistics
    """
    try:
        data = silver_service.get_silver_preview(source, entity, page, page_size)
        
        if not data:
            raise HTTPException(
                status_code=404, 
                detail=f"Silver data not found for {source}.{entity}"
            )
        
        return data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error viewing silver data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/silver/tables")
def list_silver_tables(
    search: str = None,
    source_type: str = None,
    format: str = None,
    date_filter: str = 'all',
    sort_by: str = 'last_modified',
    sort_order: str = 'desc',
    page: int = 1,
    page_size: int = 50
):
    """
    List all Silver layer tables with detailed metadata.
    
    Supports filtering, searching, sorting, and pagination.
    """
    try:
        # Get list of Silver tables from MinIO and Iceberg
        table_mapping = _discover_minio_tables()
        
        # Filter for Silver layer tables only
        silver_tables = []
        for table_name, info in table_mapping.items():
            if info['layer'] != 'silver':
                continue
            
            # Apply search filter
            if search and search.lower() not in table_name.lower():
                continue
            
            # Apply source type filter
            if source_type and info.get('source', '') != source_type:
                continue
            
            # Build table metadata
            table_data = {
                'table_name': table_name,
                'source': info.get('source', 'unknown'),
                'entity': info.get('entity', table_name),  # Add entity field
                'source_type': info.get('format', 'parquet'),
                'format': info.get('format', 'parquet'),
                'row_count': 0,
                'total_size': 0,
                'quality_score': 95 if info.get('format') == 'iceberg' else None,
                'is_partitioned': True,
                'last_modified': datetime.now().isoformat(),
                'last_processed': datetime.now().isoformat() if info.get('format') == 'iceberg' else None
            }
            
            # Try to get detailed stats from MinIO
            try:
                parquet_path = f"s3a://{info['bucket']}/{info['object_path']}"
                # Get file stats using boto3 or MinIO client
                # For now, use placeholder values
                table_data['row_count'] = 0
                table_data['total_size'] = 0
            except:
                pass
            
            silver_tables.append(table_data)
        
        # Sort tables
        reverse_sort = (sort_order == 'desc')
        if sort_by == 'table_name':
            silver_tables.sort(key=lambda x: x['table_name'], reverse=reverse_sort)
        elif sort_by == 'row_count':
            silver_tables.sort(key=lambda x: x.get('row_count', 0), reverse=reverse_sort)
        elif sort_by == 'total_size':
            silver_tables.sort(key=lambda x: x.get('total_size', 0), reverse=reverse_sort)
        elif sort_by == 'quality_score':
            silver_tables.sort(key=lambda x: x.get('quality_score', 0), reverse=reverse_sort)
        elif sort_by == 'last_modified':
            silver_tables.sort(key=lambda x: x.get('last_modified') or '', reverse=reverse_sort)
        
        # Pagination
        total_count = len(silver_tables)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_tables = silver_tables[start_idx:end_idx]
        
        return {
            'tables': paginated_tables,
            'total': total_count,
            'page': page,
            'page_size': page_size,
            'total_pages': (total_count + page_size - 1) // page_size
        }
        
    except Exception as e:
        logger.error(f"Error listing Silver tables: {e}")
        # Return mock data for demo
        return {
            'tables': [
                {
                    'table_name': 'user_credit_card_transaction_cleaned',
                    'source': 'finance',
                    'source_type': 'postgres',
                    'format': 'iceberg',
                    'row_count': 237500,
                    'total_size': 48234567,
                    'quality_score': 98,
                    'is_partitioned': True,
                    'last_modified': '2024-01-15T10:30:00Z'
                }
            ],
            'total': 1,
            'page': page,
            'page_size': page_size,
            'total_pages': 1
        }


# ==================== SPARK + ICEBERG SILVER ENDPOINTS ====================

class SparkSilverRequest(BaseModel):
    source: str
    entity: str
    domain: str = "general"
    execution_mode: str = "full"  # 'full' or 'incremental'
    use_spark: bool = True  # Force Spark mode
    watermark_column: Optional[str] = None
    watermark_value: Optional[str] = None
    rules: List[Dict[str, Any]] = []
    custom_sql: Optional[str] = None
    # Unstructured data parameters
    data_type: str = "structured"  # 'structured' or 'unstructured'
    unstructured_type: Optional[str] = None  # 'image', 'video', 'audio', 'text', 'pdf'
    image_transforms: Optional[Dict[str, Any]] = None
    video_transforms: Optional[Dict[str, Any]] = None
    audio_transforms: Optional[Dict[str, Any]] = None
    text_transforms: Optional[Dict[str, Any]] = None
    pdf_transforms: Optional[Dict[str, Any]] = None


@app.get("/api/silver/dataset-size/{source}/{entity}")
def get_dataset_size(source: str, entity: str):
    """
    Get Bronze dataset size to recommend Spark vs Pandas
    
    Returns:
        Dataset size info with recommendation
    """
    try:
        # Get Bronze storage manager
        bronze_mgr = storage.get_bronze_manager()
        
        # Calculate total size
        total_size_bytes = 0
        file_count = 0
        
        try:
            # Try to get size from MinIO
            objects = storage.storage_manager.list_objects(
                f"lakehouse/bronze/{source}/{entity}/",
                recursive=True
            )
            
            for obj in objects:
                total_size_bytes += obj.size if hasattr(obj, 'size') else 0
                file_count += 1
        except Exception as e:
            logger.warning(f"Could not get size from MinIO: {e}")
            # Return conservative estimate
            total_size_bytes = 100 * 1024 * 1024  # 100 MB default
        
        total_size_mb = total_size_bytes / (1024 * 1024)
        total_size_gb = total_size_mb / 1024
        
        # Recommendation logic
        recommend_spark = total_size_mb > 1024  # > 1GB
        
        return {
            "source": source,
            "entity": entity,
            "size_bytes": total_size_bytes,
            "size_mb": round(total_size_mb, 2),
            "size_gb": round(total_size_gb, 2),
            "file_count": file_count,
            "recommend_spark": recommend_spark,
            "recommendation": "Use Spark" if recommend_spark else "Use Pandas",
            "reason": f"Dataset is {total_size_gb:.2f}GB" if recommend_spark else f"Dataset is {total_size_mb:.0f}MB"
        }
    except Exception as e:
        logger.error(f"Error getting dataset size: {e}")
        return {
            "source": source,
            "entity": entity,
            "size_mb": 0,
            "recommend_spark": False,
            "error": str(e)
        }


# ==================== SILVER ASSET DOWNLOAD ENDPOINT ====================

@app.get("/api/silver/download/{asset_id}")
async def download_silver_asset(asset_id: str):
    """
    Get presigned download URL for the original file in Bronze storage.
    
    Users download the RAW file (not the AI-processed JSON from Silver).
    URL expires after 1 hour and forces browser download via Content-Disposition.
    
    Args:
        asset_id: UUID of the silver_asset record
        
    Returns:
        Dict with presigned_url and metadata
        
    Example:
        GET /api/silver/download/123e4567-e89b-12d3-a456-426614174000
        Returns: {
            "presigned_url": "http://localhost:9000/syniqai-bronze/...",
            "filename": "photo.jpg",
            "expires_in_hours": 1
        }
    """
    try:
        # Import silver_store module
        try:
            from silver_store import get_presigned_download_url, get_asset_by_id
        except ImportError as e:
            logger.error(f"Failed to import silver_store: {e}")
            raise HTTPException(
                status_code=500,
                detail="silver_store module not available. Ensure SQLAlchemy and asyncpg are installed."
            )
        
        # Get asset details
        asset = await get_asset_by_id(asset_id)
        if not asset:
            raise HTTPException(status_code=404, detail=f"Asset not found: {asset_id}")
        
        # Generate presigned download URL (1 hour expiry)
        try:
            presigned_url = await get_presigned_download_url(asset_id, expiry_hours=1)
        except ValueError as e:
            # Asset not found or invalid bronze_minio_key
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to generate download URL: {str(e)}")
        
        # Extract filename from bronze_minio_key
        bronze_key = asset.get("bronze_minio_key", "")
        filename = os.path.basename(bronze_key) if bronze_key else "download"
        
        return {
            "success": True,
            "presigned_url": presigned_url,
            "filename": filename,
            "file_type": asset.get("file_type"),
            "file_size_bytes": asset.get("file_size_bytes"),
            "expires_in_hours": 1,
            "expires_at": (datetime.utcnow() + timedelta(hours=1)).isoformat() + "Z",
            "note": "URL will automatically download file when opened in browser"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating download URL for asset {asset_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/silver/assets")
async def list_silver_assets(
    file_type: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 20,
    offset: int = 0
):
    """
    List silver assets with optional filters.
    
    Query params:
        file_type: Filter by file type (image, pdf, txt, etc.)
        status: Filter by extraction_status (pending, success, failed)
        limit: Max results (default: 20)
        offset: Pagination offset (default: 0)
        
    Returns:
        List of assets with metadata
        
    Example:
        GET /api/silver/assets?file_type=image&status=success&limit=10
    """
    try:
        from silver_store import list_assets
    except ImportError as e:
        logger.error(f"Failed to import silver_store: {e}")
        raise HTTPException(
            status_code=500,
            detail="silver_store module not available"
        )
    
    try:
        assets = await list_assets(
            file_type=file_type,
            status=status,
            limit=limit,
            offset=offset
        )
        
        return {
            "success": True,
            "assets": assets,
            "count": len(assets),
            "filters": {
                "file_type": file_type,
                "status": status,
                "limit": limit,
                "offset": offset
            }
        }
        
    except Exception as e:
        logger.error(f"Error listing silver assets: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/silver/stats")
async def get_silver_statistics():
    """
    Get aggregate statistics about silver assets for Media Dashboard.
    
    Returns:
        Stats with silver.total_objects, silver.by_type.{type}.count, silver.total_size_gb
    """
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        conn = psycopg2.connect(
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=os.getenv("POSTGRES_PORT", "5432"),
            database=os.getenv("POSTGRES_DB", "syniqai_metadata"),
            user=os.getenv("POSTGRES_USER", "syniqai_user"),
            password=os.getenv("POSTGRES_PASSWORD", "syniqai_password")
        )
        
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get total count
        cursor.execute("SELECT COUNT(*) as total FROM silver_assets")
        total = cursor.fetchone()['total']
        
        # Get counts by file type
        cursor.execute("""
            SELECT 
                file_type,
                COUNT(*) as count,
                SUM(COALESCE(file_size_bytes, 0)) as total_bytes
            FROM silver_assets
            GROUP BY file_type
        """)
        by_type_rows = cursor.fetchall()
        
        # Get total size
        cursor.execute("SELECT SUM(COALESCE(file_size_bytes, 0)) as total_bytes FROM silver_assets")
        total_size_row = cursor.fetchone()
        total_size_gb = (total_size_row['total_bytes'] or 0) / (1024**3)
        
        # Map file types to media categories
        file_type_mapping = {
            'jpg': 'image', 'jpeg': 'image', 'png': 'image', 'gif': 'image', 
            'bmp': 'image', 'webp': 'image', 'tiff': 'image',
            'pdf': 'document', 'doc': 'document', 'docx': 'document', 
            'txt': 'document', 'csv': 'document',
            'mp3': 'audio', 'wav': 'audio', 'flac': 'audio', 'm4a': 'audio',
            'mp4': 'video', 'avi': 'video', 'mov': 'video', 'mkv': 'video',
        }
        
        # Aggregate by media category
        by_category = {
            'image': {'count': 0, 'size_bytes': 0},
            'document': {'count': 0, 'size_bytes': 0},
            'audio': {'count': 0, 'size_bytes': 0},
            'video': {'count': 0, 'size_bytes': 0},
        }
        
        for row in by_type_rows:
            file_type = (row['file_type'] or '').lower()
            category = file_type_mapping.get(file_type, 'document')  # Default to document
            by_category[category]['count'] += row['count']
            by_category[category]['size_bytes'] += row['total_bytes'] or 0
        
        cursor.close()
        conn.close()
        
        return {
            "success": True,
            "silver": {
                "total_objects": total,
                "by_type": by_category,
                "total_size_gb": total_size_gb
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting silver statistics: {e}")
        # Return empty structure instead of error to avoid breaking UI
        return {
            "success": False,
            "silver": {
                "total_objects": 0,
                "by_type": {},
                "total_size_gb": 0.0
            },
            "error": str(e)
        }


# ==================== END SILVER ASSET ENDPOINTS ====================


@app.post("/api/silver/process-spark")
async def process_to_silver_spark(request: SparkSilverRequest, background_tasks: BackgroundTasks):
    """
    Process Bronze → Silver using Spark + Iceberg
    
    Supports:
    - Large dataset processing (100GB+)
    - ACID transactions
    - Incremental processing with watermarks
    - Data quality rules
    - Custom SQL transformations
    """
    try:
        # Import Spark transformer
        sys.path.insert(0, str(gold_layer_path / "ingestion"))
        from silver_transformer_spark import SilverTransformerSpark
        
        # Create job ID
        job_id = f"spark_{request.domain}_{request.entity}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Track job in silver_job_tracker
        table_name = f"{request.domain}.{request.entity}"
        # Correct Bronze path structure: syniqai-bronze/{domain}/{source_type}/{entity}/
        bronze_path = f"s3a://syniqai-bronze/{request.domain}/{request.source}/{request.entity}/"
        silver_job_tracker.create_job(
            job_id=job_id,
            table_name=table_name,
            source=request.source,
            entity=request.entity,
            bronze_path=bronze_path
        )
        
        # Auto-detect data type from Bronze layer if not explicitly set
        if request.data_type == "structured":
            logger.info(f"🔍 Auto-detecting data type for {request.source}.{request.entity}...")
            try:
                from minio import Minio
                minio = Minio(
                    config.minio.endpoint.replace('http://', '').replace('https://', ''),
                    access_key=config.minio.access_key,
                    secret_key=config.minio.secret_key,
                    secure=config.minio.secure
                )
                
                # Check files in Bronze path
                bronze_prefix = f"{request.domain}/{request.source}/{request.entity}/"
                objects = list(minio.list_objects("syniqai-bronze", prefix=bronze_prefix, recursive=True))
                
                if objects:
                    # Check file extensions
                    file_extensions = {obj.object_name.split('.')[-1].lower() for obj in objects if '.' in obj.object_name}
                    
                    # Unstructured file types
                    image_exts = {'jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff', 'webp'}
                    video_exts = {'mp4', 'avi', 'mov', 'wmv', 'flv', 'mkv', 'webm'}
                    audio_exts = {'mp3', 'wav', 'flac', 'aac', 'ogg', 'm4a'}
                    text_exts = {'txt', 'log'}
                    pdf_exts = {'pdf'}
                    
                    if file_extensions & image_exts:
                        request.data_type = "unstructured"
                        request.unstructured_type = "image"
                        logger.info(f"✅ Auto-detected: unstructured image data")
                    elif file_extensions & video_exts:
                        request.data_type = "unstructured"
                        request.unstructured_type = "video"
                        logger.info(f"✅ Auto-detected: unstructured video data")
                    elif file_extensions & audio_exts:
                        request.data_type = "unstructured"
                        request.unstructured_type = "audio"
                        logger.info(f"✅ Auto-detected: unstructured audio data")
                    elif file_extensions & pdf_exts:
                        request.data_type = "unstructured"
                        request.unstructured_type = "pdf"
                        logger.info(f"✅ Auto-detected: unstructured PDF data")
                    elif file_extensions & text_exts:
                        request.data_type = "unstructured"
                        request.unstructured_type = "text"
                        logger.info(f"✅ Auto-detected: unstructured text data")
                    elif 'parquet' in file_extensions:
                        logger.info(f"✅ Confirmed: structured Parquet data")
                    else:
                        logger.warning(f"⚠️ Unknown file types: {file_extensions}")
            except Exception as e:
                logger.warning(f"⚠️ Auto-detection failed: {e}, assuming structured data")
        
        # Define background task
        def run_spark_transformation():
            # CRITICAL: FORCE Java 17 for subprocess (Windows multiprocessing issue)
            import os
            
            # ALWAYS use Java 17 (required for Spark 3.5+)
            java_17_path = r"C:\Users\Syarifah\AppData\Local\Programs\Eclipse Adoptium\jdk-17.0.18.8-hotspot"
            
            if os.path.exists(java_17_path):
                os.environ['JAVA_HOME'] = java_17_path
                os.environ['PATH'] = f"{java_17_path}\\bin;{os.environ.get('PATH', '')}"
                logger.info(f"✓ [Subprocess] Java 17 configured: {java_17_path}")
            else:
                logger.error(f"❌ [Subprocess] Java 17 not found at {java_17_path}")
                logger.error("   Download Java 17: https://adoptium.net/temurin/releases/?version=17")
                raise RuntimeError("Java 17 is required for Spark 3.5+")
            
            try:
                logger.info(f"🚀 Starting Spark transformation: {request.source}.{request.entity}")
                logger.info(f"   Data type: {request.data_type}, Unstructured type: {request.unstructured_type}")
                
                # Update status to running
                silver_job_tracker.update_status(
                    job_id=job_id,
                    status="running",
                    message="Initializing Spark session...",
                    progress=5
                )
                
                # Initialize Spark transformer
                logger.info("Creating SilverTransformerSpark instance...")
                transformer = SilverTransformerSpark()
                logger.info("✅ SilverTransformerSpark created successfully")
                
                try:
                    # Execute transformation
                    logger.info(f"Executing transform for {request.source}.{request.entity}...")
                    result = transformer.transform(
                        source=request.source,
                        entity=request.entity,
                        domain=request.domain,
                        execution_mode=request.execution_mode,
                        watermark_column=request.watermark_column,
                        watermark_value=request.watermark_value,
                        rules=request.rules,
                        custom_sql=request.custom_sql,
                        data_type=request.data_type,
                        unstructured_type=request.unstructured_type,
                        image_transforms=request.image_transforms,
                        video_transforms=request.video_transforms,
                        audio_transforms=request.audio_transforms,
                        text_transforms=request.text_transforms,
                        pdf_transforms=request.pdf_transforms
                    )
                    logger.info(f"✅ Transform completed with status: {result.get('status')}")
                    
                    # Update job status
                    if result.get("status") == "completed":
                        silver_job_tracker.update_status(
                            job_id=job_id,
                            status="completed",
                            message="Spark transformation completed successfully",
                            progress=100
                        )
                        
                        # Include quarantine metrics in cleaning summary
                        cleaning_summary = result.get("cleaning_summary", {})
                        if "rows_quarantined" not in cleaning_summary and result.get("rows_quarantined"):
                            cleaning_summary["rows_quarantined"] = result.get("rows_quarantined")
                        
                        silver_job_tracker.update_results(
                            job_id=job_id,
                            silver_path=result.get("silver_path"),
                            row_count=result.get("row_count"),
                            quality_score=result.get("quality_score"),
                            cleaning_summary=cleaning_summary
                        )
                    else:
                        silver_job_tracker.update_status(
                            job_id=job_id,
                            status="failed",
                            message=result.get("message", "Transformation failed"),
                            error_message=str(result.get("error"))
                        )
                    
                    logger.info(f"✅ Spark transformation completed: {job_id}")
                    
                finally:
                    # Always cleanup, even if transformation fails
                    logger.info("Cleaning up Spark resources...")
                    transformer.cleanup()
                    logger.info("✅ Cleanup complete")
                
            except Exception as e:
                logger.error(f"❌ Spark transformation failed: {str(e)}")
                logger.error(f"❌ Error type: {type(e).__name__}")
                import traceback
                logger.error(f"❌ Traceback:\n{traceback.format_exc()}")
                
                silver_job_tracker.update_status(
                    job_id=job_id,
                    status="failed",
                    message="Spark transformation failed",
                    error_message=f"{type(e).__name__}: {str(e)}"
                )
        
        # Add to background tasks
        background_tasks.add_task(run_spark_transformation)
        
        return {
            "job_id": job_id,
            "status": "queued",
            "engine": "spark",
            "message": f"Spark processing started for {request.source}.{request.entity}",
            "execution_mode": request.execution_mode,
            "table_name": f"syniq_iceberg.{request.source}.{request.entity}"
        }
        
    except Exception as e:
        logger.error(f"Error starting Spark processing: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/silver/iceberg-tables")
def list_iceberg_tables():
    """
    List all Iceberg tables in Silver layer
    """
    try:
        # Import Spark session
        sys.path.insert(0, str(gold_layer_path))
        from utils.spark_iceberg_config import create_spark_session_with_iceberg
        
        spark = create_spark_session_with_iceberg()
        
        # List tables in syniq_iceberg catalog
        tables_df = spark.sql("SHOW TABLES IN syniq_iceberg")
        tables = [row.asDict() for row in tables_df.collect()]
        
        spark.stop()
        
        return {
            "catalog": "syniq_iceberg",
            "tables": tables,
            "total": len(tables)
        }
        
    except Exception as e:
        logger.error(f"Error listing Iceberg tables: {e}")
        return {
            "catalog": "syniq_iceberg",
            "tables": [],
            "total": 0,
            "error": str(e)
        }


@app.get("/api/silver/iceberg-table/{source}/{entity}/history")
def get_iceberg_table_history(source: str, entity: str):
    """
    Get Iceberg table snapshot history for time-travel queries
    """
    try:
        sys.path.insert(0, str(gold_layer_path))
        from utils.spark_iceberg_config import create_spark_session_with_iceberg
        
        spark = create_spark_session_with_iceberg()
        
        table_name = f"syniq_iceberg.silver_{source}.{entity}"
        
        # Get table history
        history_df = spark.sql(f"SELECT * FROM {table_name}.history")
        history = [row.asDict() for row in history_df.collect()]
        
        spark.stop()
        
        return {
            "table": table_name,
            "snapshots": history,
            "total_snapshots": len(history)
        }
        
    except Exception as e:
        logger.error(f"Error getting table history: {e}")
        return {
            "table": f"syniq_iceberg.silver_{source}.{entity}",
            "snapshots": [],
            "error": str(e)
        }


# ==================== CDC SILVER STREAMING ENDPOINTS ====================

# In-memory tracking for CDC Silver jobs
cdc_silver_jobs = {}

class CDCSilverJobRequest(BaseModel):
    source: str
    table_name: str
    checkpoint_interval: Optional[int] = 30
    max_offsets: Optional[int] = 10000

@app.post("/api/silver/cdc/start")
async def start_cdc_silver_stream(request: CDCSilverJobRequest, background_tasks: BackgroundTasks):
    """
    Start real-time Silver CDC streaming for a Bronze CDC table.
    
    This creates a Spark Structured Streaming job that:
    - Monitors Bronze CDC table for new changes
    - Applies Silver transformations in real-time
    - Writes to Silver Iceberg table with quality checks
    """
    try:
        job_key = f"{request.source}_{request.table_name}"
        
        # Check if already running
        if job_key in cdc_silver_jobs and cdc_silver_jobs[job_key].get('status') == 'running':
            return {
                "success": False,
                "error": f"CDC Silver stream already running for {job_key}",
                "job_id": cdc_silver_jobs[job_key].get('job_id')
            }
        
        # Generate job ID
        job_id = f"cdc_silver_{job_key}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Create job entry
        cdc_silver_jobs[job_key] = {
            "job_id": job_id,
            "source": request.source,
            "table_name": request.table_name,
            "status": "starting",
            "started_at": datetime.now().isoformat(),
            "checkpoint_interval": request.checkpoint_interval,
            "max_offsets": request.max_offsets,
            "records_processed": 0,
            "batches_processed": 0,
            "avg_quality_score": None,
            "last_batch_at": None,
            "error": None
        }
        
        # Start streaming in background
        background_tasks.add_task(
            _run_cdc_silver_stream,
            job_key,
            request.source,
            request.table_name,
            request.checkpoint_interval,
            request.max_offsets
        )
        
        logger.info(f"Started CDC Silver stream: {job_id}")
        
        return {
            "success": True,
            "job_id": job_id,
            "message": f"CDC Silver streaming started for {request.source}.{request.table_name}",
            "checkpoint_interval": request.checkpoint_interval
        }
    
    except Exception as e:
        logger.error(f"Error starting CDC Silver stream: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def _run_cdc_silver_stream(
    job_key: str,
    source: str,
    table_name: str,
    checkpoint_interval: int,
    max_offsets: int
):
    """Background task to run CDC Silver streaming"""
    try:
        # Import processor
        from silver_cdc_processor import SilverCDCProcessor
        
        # Update status
        if job_key in cdc_silver_jobs:
            cdc_silver_jobs[job_key]['status'] = 'running'
        
        # Initialize processor
        processor = SilverCDCProcessor(
            checkpoint_interval=checkpoint_interval,
            max_offsets_per_trigger=max_offsets
        )
        
        # Start streaming (this will block)
        query = processor.process_table_stream(source, table_name)
        
        # Update metrics periodically
        while query.isActive:
            await asyncio.sleep(10)
            
            if job_key in cdc_silver_jobs:
                # Get latest metrics from streaming query
                progress = query.lastProgress
                if progress:
                    cdc_silver_jobs[job_key]['records_processed'] += progress.get('numInputRows', 0)
                    cdc_silver_jobs[job_key]['batches_processed'] += 1
                    cdc_silver_jobs[job_key]['last_batch_at'] = datetime.now().isoformat()
        
        # Query stopped
        if job_key in cdc_silver_jobs:
            cdc_silver_jobs[job_key]['status'] = 'stopped'
            cdc_silver_jobs[job_key]['stopped_at'] = datetime.now().isoformat()
    
    except Exception as e:
        logger.error(f"CDC Silver stream error for {job_key}: {e}")
        if job_key in cdc_silver_jobs:
            cdc_silver_jobs[job_key]['status'] = 'failed'
            cdc_silver_jobs[job_key]['error'] = str(e)

@app.post("/api/silver/cdc/stop")
def stop_cdc_silver_stream(source: str, table_name: str):
    """Stop a running CDC Silver stream"""
    try:
        job_key = f"{source}_{table_name}"
        
        if job_key not in cdc_silver_jobs:
            return {
                "success": False,
                "error": f"No CDC Silver stream found for {job_key}"
            }
        
        # Mark for stopping (actual stop happens in background task)
        cdc_silver_jobs[job_key]['status'] = 'stopping'
        
        logger.info(f"Stopping CDC Silver stream: {job_key}")
        
        return {
            "success": True,
            "message": f"CDC Silver stream stopping for {source}.{table_name}",
            "job_id": cdc_silver_jobs[job_key].get('job_id')
        }
    
    except Exception as e:
        logger.error(f"Error stopping CDC Silver stream: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/silver/cdc/status")
def get_cdc_silver_status():
    """Get status of all CDC Silver streams"""
    try:
        return {
            "success": True,
            "jobs": cdc_silver_jobs,
            "total_jobs": len(cdc_silver_jobs),
            "active_jobs": len([j for j in cdc_silver_jobs.values() if j.get('status') == 'running'])
        }
    
    except Exception as e:
        logger.error(f"Error getting CDC Silver status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/silver/cdc/status/{source}/{table_name}")
def get_cdc_silver_table_status(source: str, table_name: str):
    """Get status of specific CDC Silver stream"""
    try:
        job_key = f"{source}_{table_name}"
        
        if job_key not in cdc_silver_jobs:
            return {
                "success": False,
                "error": f"No CDC Silver stream found for {job_key}",
                "status": "not_running"
            }
        
        return {
            "success": True,
            "job": cdc_silver_jobs[job_key]
        }
    
    except Exception as e:
        logger.error(f"Error getting CDC Silver table status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/silver/cdc/metrics/{source}/{table_name}")
def get_cdc_silver_metrics(source: str, table_name: str):
    """Get real-time quality metrics for CDC Silver stream"""
    try:
        from silver_cdc_processor import SilverCDCProcessor
        
        processor = SilverCDCProcessor()
        metrics = processor.get_metrics(source, table_name)
        processor.cleanup()
        
        return {
            "success": True,
            "metrics": metrics
        }
    
    except Exception as e:
        logger.error(f"Error getting CDC Silver metrics: {e}")
        # Return mock metrics if error
        return {
            "success": True,
            "metrics": {
                "table": f"{source}.{table_name}",
                "total_rows": 0,
                "avg_quality_score": None,
                "recent_rows_1h": 0,
                "last_updated": None,
                "error": str(e)
            }
        }

@app.get("/api/silver/cdc/tables")
def list_cdc_enabled_tables():
    """List all Bronze CDC tables that can have Silver streaming"""
    try:
        # Query Bronze Bronze tables to see which have CDC
        sys.path.insert(0, str(gold_layer_path))
        from utils.spark_iceberg_config import create_spark_session_with_iceberg
        
        spark = create_spark_session_with_iceberg()
        
        # List Bronze tables
        bronze_tables = spark.sql("SHOW TABLES IN syniq_iceberg.bronze").collect()
        
        cdc_tables = []
        for row in bronze_tables:
            table_name = row.tableName
            
            # Check if table has CDC columns (_cdc_timestamp, _cdc_operation, etc.)
            try:
                table_df = spark.read.format("iceberg").table(f"syniq_iceberg.bronze.{table_name}").limit(1)
                columns = table_df.columns
                
                has_cdc = '_cdc_timestamp' in columns or '_cdc_operation' in columns
                
                if has_cdc:
                    # Parse source and table from table_name (format: source_table)
                    parts = table_name.split('_', 1)
                    source = parts[0] if len(parts) > 0 else 'unknown'
                    entity = parts[1] if len(parts) > 1 else table_name
                    
                    cdc_tables.append({
                        "source": source,
                        "table_name": entity,
                        "full_name": table_name,
                        "has_cdc": True,
                        "columns": len(columns)
                    })
            except Exception as e:
                logger.warning(f"Could not check CDC columns for {table_name}: {e}")
        
        spark.stop()
        
        return {
            "success": True,
            "tables": cdc_tables,
            "total": len(cdc_tables)
        }
    
    except Exception as e:
        logger.error(f"Error listing CDC-enabled tables: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== CDC STREAMING MONITORING ENDPOINTS ====================

@app.get("/api/cdc/consumer/status")
def get_cdc_consumer_status():
    """
    Get status of CDC streaming consumer (Native - No Docker).
    Checks if the native Python process is running.
    """
    try:
        import psutil
        from pathlib import Path
        
        status = {
            "running": False,
            "process_id": None,
            "uptime_seconds": None,
            "memory_mb": None,
            "cpu_percent": None,
            "started_at": None,
            "status_text": "Stopped"
        }
        
        # Look for running cdc_consumer_native.py process
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time', 'memory_info']):
            try:
                cmdline = proc.info.get('cmdline', [])
                if cmdline and any('cdc_consumer_native.py' in str(arg) for arg in cmdline):
                    # Found the CDC consumer process
                    status["running"] = True
                    status["process_id"] = proc.info['pid']
                    status["status_text"] = "Running"
                    
                    # Get process details
                    if proc.info.get('create_time'):
                        started_at = datetime.fromtimestamp(proc.info['create_time'])
                        status["started_at"] = started_at.isoformat()
                        status["uptime_seconds"] = int((datetime.now() - started_at).total_seconds())
                    
                    if proc.info.get('memory_info'):
                        status["memory_mb"] = round(proc.info['memory_info'].rss / 1024 / 1024, 1)
                    
                    try:
                        status["cpu_percent"] = round(proc.cpu_percent(interval=0.1), 1)
                    except:
                        pass
                    
                    break
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        return {
            "success": True,
            "consumer": status,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting CDC consumer status: {e}")
        return {
            "success": False,
            "error": str(e),
            "consumer": {"running": False}
        }


@app.get("/api/cdc/consumer/health")
def get_cdc_consumer_health():
    """
    Comprehensive health check for CDC streaming pipeline.
    Checks: Kafka, Debezium, CDC Consumer, Bronze tables.
    """
    try:
        from kafka import KafkaConsumer
        import socket
        
        health = {
            "overall_status": "healthy",
            "checks": {},
            "timestamp": datetime.now().isoformat()
        }
        
        # 1. Check Kafka connectivity
        try:
            # Try to connect on port 9092
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex(('127.0.0.1', 9092))
            sock.close()
            
            health["checks"]["kafka"] = {
                "status": "up" if result == 0 else "down",
                "message": "Kafka broker reachable" if result == 0 else "Cannot connect to Kafka on 127.0.0.1:9092"
            }
        except Exception as e:
            health["checks"]["kafka"] = {
                "status": "down",
                "message": f"Kafka check failed: {str(e)}"
            }
        
        # 2. Check CDC consumer process
        consumer_status = get_cdc_consumer_status()
        if consumer_status["success"] and consumer_status["consumer"]["running"]:
            health["checks"]["cdc_consumer"] = {
                "status": "up",
                "uptime_seconds": consumer_status["consumer"].get("uptime_seconds"),
                "message": f"CDC consumer running (container: {consumer_status['consumer'].get('container_id', 'unknown')})"
            }
        else:
            health["checks"]["cdc_consumer"] = {
                "status": "down",
                "message": "CDC consumer not running"
            }
            health["overall_status"] = "degraded"
        
        # 3. Check MinIO (Iceberg warehouse)
        try:
            import requests
            resp = requests.get("http://localhost:9000/minio/health/live", timeout=2)
            health["checks"]["minio"] = {
                "status": "up" if resp.status_code == 200 else "down",
                "message": "MinIO storage accessible"
            }
        except Exception as e:
            health["checks"]["minio"] = {
                "status": "down",
                "message": f"MinIO check failed: {str(e)}"
            }
            health["overall_status"] = "degraded"
        
        # 4. Check PostgreSQL (Iceberg catalog)
        try:
            import psycopg2
            conn = psycopg2.connect(
                host="localhost",
                port=5432,
                database="syniqai_metadata",
                user="syniqai_user",
                password="syniqai_pass",
                connect_timeout=2
            )
            conn.close()
            health["checks"]["postgresql"] = {
                "status": "up",
                "message": "PostgreSQL catalog accessible"
            }
        except Exception as e:
            health["checks"]["postgresql"] = {
                "status": "down",
                "message": f"PostgreSQL check failed: {str(e)}"
            }
            health["overall_status"] = "degraded"
        
        # Determine overall status
        down_count = sum(1 for check in health["checks"].values() if check["status"] == "down")
        if down_count >= 2:
            health["overall_status"] = "unhealthy"
        elif down_count == 1:
            health["overall_status"] = "degraded"
        
        return {
            "success": True,
            "health": health
        }
        
    except Exception as e:
        logger.error(f"Error performing health check: {e}")
        return {
            "success": False,
            "error": str(e),
            "health": {
                "overall_status": "unknown",
                "checks": {},
                "timestamp": datetime.now().isoformat()
            }
        }


@app.get("/api/cdc/consumer/metrics")
def get_cdc_consumer_metrics():
    """
    Get CDC consumer metrics from Bronze Iceberg tables.
    Shows ingestion rates, table sizes, latest timestamps.
    """
    try:
        sys.path.insert(0, str(gold_layer_path))
        from utils.spark_iceberg_config import create_spark_session_with_iceberg
        
        spark = create_spark_session_with_iceberg()
        
        metrics = {
            "tables": [],
            "total_rows": 0,
            "total_tables": 0,
            "timestamp": datetime.now().isoformat()
        }
        
        # Query Bronze tables
        try:
            bronze_tables = spark.sql("SHOW TABLES IN syniq_iceberg.bronze").collect()
            
            for row in bronze_tables:
                table_name = row.tableName
                
                try:
                    # Get table metrics
                    table_df = spark.read.format("iceberg").table(f"syniq_iceberg.bronze.{table_name}")
                    row_count = table_df.count()
                    
                    # Get latest ingestion timestamp
                    latest_ts = table_df.agg({"ingestion_timestamp": "max"}).collect()[0][0]
                    
                    metrics["tables"].append({
                        "table_name": table_name,
                        "row_count": row_count,
                        "latest_ingestion": latest_ts.isoformat() if latest_ts else None
                    })
                    
                    metrics["total_rows"] += row_count
                    
                except Exception as table_error:
                    logger.warning(f"Could not get metrics for {table_name}: {table_error}")
            
            metrics["total_tables"] = len(metrics["tables"])
            
        except Exception as query_error:
            logger.warning(f"Could not query Bronze tables: {query_error}")
        
        spark.stop()
        
        return {
            "success": True,
            "metrics": metrics
        }
        
    except Exception as e:
        logger.error(f"Error getting CDC consumer metrics: {e}")
        return {
            "success": False,
            "error": str(e),
            "metrics": {
                "tables": [],
                "total_rows": 0,
                "total_tables": 0
            }
        }


@app.get("/api/cdc/consumer/logs")
def get_cdc_consumer_logs(lines: int = 50):
    """
    Get recent CDC consumer log output for debugging.
    """
    try:
        from pathlib import Path
        
        kafka_integration_dir = Path(__file__).parent.parent.parent / "Kafka Integration"
        stdout_log = kafka_integration_dir / "cdc_stdout.log"
        stderr_log = kafka_integration_dir / "cdc_stderr.log"
        
        logs = {
            "stdout": "",
            "stderr": "",
            "stdout_exists": stdout_log.exists(),
            "stderr_exists": stderr_log.exists()
        }
        
        # Read last N lines of stdout
        if stdout_log.exists():
            try:
                with open(stdout_log, 'r') as f:
                    all_lines = f.readlines()
                    logs["stdout"] = "".join(all_lines[-lines:])
            except Exception as e:
                logs["stdout"] = f"Error reading stdout: {e}"
        
        # Read last N lines of stderr  
        if stderr_log.exists():
            try:
                with open(stderr_log, 'r') as f:
                    all_lines = f.readlines()
                    logs["stderr"] = "".join(all_lines[-lines:])
            except Exception as e:
                logs["stderr"] = f"Error reading stderr: {e}"
        
        return {
            "success": True,
            "logs": logs
        }
        
    except Exception as e:
        logger.error(f"Error reading CDC logs: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@app.get("/api/kafka/cdc/messages")
def get_kafka_cdc_messages(limit: int = 20, offset: str = 'latest'):
    """
    Fetch recent CDC messages from ALL CDC topics in Kafka.
    Auto-discovers topics matching CDC patterns.
    Shows INSERT/UPDATE/DELETE operations with affected data.
    
    Args:
        limit: Maximum number of messages to return (default: 20)
        offset: 'latest' (most recent) or 'earliest' (from beginning)
    """
    try:
        from kafka import KafkaConsumer, KafkaAdminClient
        from kafka.errors import KafkaError
        import json
        
        # Auto-discover CDC topics
        try:
            admin_client = KafkaAdminClient(
                bootstrap_servers='127.0.0.1:9092',
                request_timeout_ms=5000
            )
            all_topics = admin_client.list_topics()
            admin_client.close()
            
            # Filter CDC topics (multiple patterns)
            cdc_patterns = ['cdc_', 'client.', 'cdc.']
            cdc_topics = [t for t in all_topics if any(t.startswith(p) for p in cdc_patterns)]
            
            if not cdc_topics:
                return {
                    "success": True,
                    "messages": [],
                    "total": 0,
                    "info": "No CDC topics found in Kafka",
                    "hint": "Create a Debezium connector using setup_cdc_connector.py"
                }
            
            logger.info(f"Found {len(cdc_topics)} CDC topics: {cdc_topics}")
            
        except Exception as e:
            logger.error(f"Failed to discover CDC topics: {e}")
            return {
                "success": False,
                "error": f"Failed to connect to Kafka: {str(e)}"
            }
        
        try:
            # Subscribe to ALL CDC topics
            consumer = KafkaConsumer(
                *cdc_topics,  # Subscribe to all discovered CDC topics
                bootstrap_servers='127.0.0.1:9092',
                auto_offset_reset=offset,
                enable_auto_commit=False,
                consumer_timeout_ms=5000,  # Stop after 5 seconds without messages
                value_deserializer=lambda x: json.loads(x.decode('utf-8')) if x else None
            )
            
            messages = []
            
            # Collect messages from all CDC topics
            for msg in consumer:
                if msg.value is None:
                    continue
                    
                data = msg.value
                
                # Parse Debezium message format
                op = data.get('op', 'unknown')
                
                # Map Debezium operation codes to names
                op_map = {
                    'c': 'INSERT',
                    'u': 'UPDATE',
                    'd': 'DELETE',
                    'r': 'READ'
                }
                operation_name = op_map.get(op, op.upper())
                
                # Extract source information from Debezium message
                source = data.get('source', {})
                database = source.get('db', data.get('source_db', 'unknown'))
                table = source.get('table', data.get('source_table', 'unknown'))
                
                # Extract before/after data (Debezium format)
                before_data = data.get('before')
                after_data = data.get('after')
                
                # Get timestamp (Debezium provides ts_ms in source)
                ts_ms = data.get('ts_ms') or source.get('ts_ms')
                timestamp = datetime.fromtimestamp(ts_ms / 1000).isoformat() if ts_ms else None
                
                # Build message object
                message_obj = {
                    'offset': msg.offset,
                    'partition': msg.partition,
                    'topic': msg.topic,  # Include topic name
                    'operation': op,
                    'operation_name': operation_name,
                    'database': database,
                    'table': table,
                    'timestamp': timestamp,
                    'before': before_data,
                    'after': after_data
                }
                
                messages.append(message_obj)
                
                if len(messages) >= limit:
                    break
            
            consumer.close()
            
            # Reverse messages so newest is first (if reading from earliest)
            if offset == 'earliest':
                messages = messages[-limit:]
                messages.reverse()
            
            return {
                "success": True,
                "messages": messages,
                "total": len(messages),
                "topics": cdc_topics,  # List of all CDC topics scanned
                "topic_count": len(cdc_topics)
            }
            
        except KafkaError as ke:
            logger.error(f"Kafka error: {ke}")
            return {
                "success": False,
                "error": f"Kafka connection error: {str(ke)}",
                "messages": [],
                "total": 0
            }
            
    except Exception as e:
        logger.error(f"Error fetching Kafka CDC messages: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e),
            "messages": [],
            "total": 0
        }


@app.post("/api/cdc/consumer/start")
def start_cdc_consumer():
    """
    Start CDC streaming consumer (Native - No Docker).
    """
    try:
        import subprocess
        from pathlib import Path
        
        # Check if already running
        status = get_cdc_consumer_status()
        if status["success"] and status["consumer"]["running"]:
            return {
                "success": False,
                "message": "CDC consumer is already running",
                "process_id": status["consumer"].get("process_id")
            }
        
        # Get Kafka Integration directory for native CDC consumer script
        kafka_integration_dir = Path(__file__).parent.parent.parent / "Kafka Integration"
        cdc_script = kafka_integration_dir / "cdc_consumer_native.py"
        
        if not cdc_script.exists():
            raise HTTPException(
                status_code=404,
                detail=f"CDC consumer script not found at: {cdc_script}"
            )
        
        logger.info(f"Starting native CDC consumer...")
        
        try:
            # Start native Python CDC consumer in background
            if sys.platform == 'win32':
                # Windows: Start process in new window (minimized)
                process = subprocess.Popen(
                    [sys.executable, str(cdc_script)],
                    cwd=str(kafka_integration_dir),
                    creationflags=subprocess.CREATE_NEW_CONSOLE | subprocess.CREATE_NO_WINDOW,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
            else:
                # Linux/Mac: Start background process
                process = subprocess.Popen(
                    [sys.executable, str(cdc_script)],
                    cwd=str(kafka_integration_dir),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    start_new_session=True
                )
            
            # Give it a moment to start
            import time
            time.sleep(2)
            
            # Check if process is still running
            if process.poll() is None:
                logger.info(f"✓ CDC consumer started successfully (PID: {process.pid})")
                return {
                    "success": True,
                    "message": "CDC consumer started successfully",
                    "process_id": process.pid,
                    "script": str(cdc_script)
                }
            else:
                # Process died immediately
                stdout, stderr = process.communicate()
                error_msg = stderr.decode() if stderr else "Unknown error"
                logger.error(f"CDC consumer failed to start: {error_msg}")
                return {
                    "success": False,
                    "message": "CDC consumer failed to start",
                    "error": error_msg,
                    "hint": "Check if Kafka is running on localhost:9092"
                }
                
        except Exception as e:
            logger.error(f"Failed to start CDC consumer: {e}")
            return {
                "success": False,
                "message": f"Failed to start CDC consumer: {str(e)}",
                "hint": "Make sure Kafka is running on localhost:9092"
            }
        
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        logger.error(f"Error starting CDC consumer: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/cdc/consumer/stop")
def stop_cdc_consumer():
    """
    Stop CDC streaming consumer Docker container.
    """
    try:
        import subprocess
        from pathlib import Path
        
        # Get Kafka Integration directory
        kafka_integration_dir = Path(__file__).parent.parent.parent / "Kafka Integration"
        
        # Check if container is running
        check_result = subprocess.run(
            ['docker', 'ps', '--filter', 'name=syniqai-cdc-consumer', '--format', '{{.ID}}'],
            capture_output=True,
            text=True
        )
        
        container_id = check_result.stdout.strip()
        if not container_id:
            logger.warning("CDC consumer container not running")
            return {
                "success": True,
                "message": "CDC consumer is not running"
            }
        
        # Stop Docker container using docker-compose
        logger.info(f"Stopping CDC consumer container (ID: {container_id})")
        
        result = subprocess.run(
            ['docker-compose', 'stop', 'cdc-consumer'],
            cwd=str(kafka_integration_dir),
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            logger.error(f"docker-compose stop failed: {result.stderr}")
            return {
                "success": False,
                "message": "Failed to stop CDC consumer container",
                "error": result.stderr
            }
        
        logger.info(f"✓ CDC consumer container stopped")
        
        return {
            "success": True,
            "message": "CDC consumer stopped successfully",
            "container_id": container_id
            }
        
    except Exception as e:
        logger.error(f"Error stopping CDC consumer: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== GOLD LAYER EDA ENDPOINTS ====================

@app.get("/api/gold/tables")
def list_silver_tables_for_eda():
    """List all Silver tables available for EDA"""
    try:
        tables = gold_eda_service.list_available_tables()
        return {
            "tables": tables,
            "total": len(tables)
        }
    except Exception as e:
        logger.error(f"Error listing Silver tables: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/gold/eda/generate")
def generate_eda_report(source: str, entity: str):
    """
    Generate comprehensive EDA report for a Silver table.
    
    Args:
        source: Source system name (e.g., 'postgres')
        entity: Entity/table name
    
    Returns:
        EDA report with visualizations
    """
    try:
        result = gold_eda_service.generate_eda_report(source, entity)
        
        if not result.get('success'):
            raise HTTPException(
                status_code=500, 
                detail=result.get('error', 'EDA generation failed')
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating EDA: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/gold/eda/{source}/{entity}")
def get_eda_report(source: str, entity: str):
    """
    Get existing EDA report or generate new one.
    
    Args:
        source: Source system name
        entity: Entity/table name
    
    Returns:
        EDA report
    """
    try:
        # Try to get existing report
        report = gold_eda_service.get_latest_report(source, entity)
        
        if report:
            return {
                "success": True,
                "source": source,
                "entity": entity,
                "table_name": f"{source}.{entity}",
                "report": report,
                "cached": True
            }
        else:
            # Generate new report
            result = gold_eda_service.generate_eda_report(source, entity)
            return result
            
    except Exception as e:
        logger.error(f"Error getting EDA report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/gold/eda/{source}/{entity}/viz")
def get_eda_visualizations(source: str, entity: str):
    """
    Get visualization-ready data for frontend charts.
    
    Args:
        source: Source system name
        entity: Entity/table name
    
    Returns:
        Visualization data
    """
    try:
        viz_data = gold_eda_service.get_visualization_data(source, entity)
        
        if not viz_data:
            raise HTTPException(
                status_code=404,
                detail=f"No EDA data found for {source}.{entity}"
            )
        
        return viz_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting visualization data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/gold/eda/{source}/{entity}/schema")
def get_schema_structure(source: str, entity: str):
    """
    Analyze and return dimensional model schema structure.
    
    Args:
        source: Source system name
        entity: Entity/table name
    
    Returns:
        Schema structure with fact/dimension classification
    """
    try:
        schema_data = gold_eda_service.analyze_schema_structure(source, entity)
        
        if not schema_data:
            raise HTTPException(
                status_code=404,
                detail=f"Could not analyze schema for {source}.{entity}"
            )
        
        return schema_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing schema structure: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== GOLD LAYER - BLOCK 4: MATERIALIZED VIEWS & LINEAGE ====================

@app.get("/api/gold/assets")
async def get_gold_assets(
    file_type: Optional[str] = None,
    limit: int = 20,
    offset: int = 0
):
    """
    Query gold_assets materialized view with pagination.
    Returns only successful Silver extractions promoted to Gold.
    
    Query Parameters:
        file_type: Optional filter by file type (pdf, image, audio, etc.)
        limit: Number of records to return (default: 20, max: 100)
        offset: Offset for pagination (default: 0)
    
    Returns:
        List of Gold assets with metadata
    """
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        # Validate limit
        if limit > 100:
            limit = 100
        if limit < 1:
            limit = 20
        
        # Build query
        query = """
            SELECT
                id,
                source,
                file_type,
                summary,
                content_tags,
                ai_confidence_score,
                silver_minio_key,
                bronze_minio_key,
                processed_at,
                ai_model_used
            FROM gold_assets
        """
        
        params = []
        
        # Add file type filter if provided
        if file_type:
            query += " WHERE file_type = %s"
            params.append(file_type)
        
        # Add ordering and pagination
        query += " ORDER BY processed_at DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])
        
        # Execute query
        conn = psycopg2.connect(os.getenv('DATABASE_URL', 
            'postgresql://syniqai_user:syniqai_pass@localhost:5432/syniqai_metadata'))
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute(query, params)
        assets = cursor.fetchall()
        
        # Get total count for pagination
        count_query = "SELECT COUNT(*) as total FROM gold_assets"
        if file_type:
            count_query += " WHERE file_type = %s"
            cursor.execute(count_query, [file_type])
        else:
            cursor.execute(count_query)
        
        total_count = cursor.fetchone()['total']
        
        cursor.close()
        conn.close()
        
        # Convert to list of dicts and format dates
        result_assets = []
        for asset in assets:
            asset_dict = dict(asset)
            # Convert datetime to ISO string
            if asset_dict.get('processed_at'):
                asset_dict['processed_at'] = asset_dict['processed_at'].isoformat()
            result_assets.append(asset_dict)
        
        return {
            "success": True,
            "assets": result_assets,
            "total": total_count,
            "limit": limit,
            "offset": offset,
            "has_more": (offset + limit) < total_count
        }
        
    except Exception as e:
        logger.error(f"Error querying gold_assets: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/gold/refresh")
async def refresh_gold_view():
    """
    Refresh the gold_assets materialized view.
    This should be called periodically or after significant Silver layer updates.
    
    Returns:
        Refresh statistics including timestamp and asset counts
    """
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        conn = psycopg2.connect(os.getenv('DATABASE_URL', 
            'postgresql://syniqai_user:syniqai_pass@localhost:5432/syniqai_metadata'))
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Call the stored function to refresh
        cursor.execute("SELECT * FROM refresh_gold_view()")
        result = cursor.fetchone()
        
        conn.commit()
        cursor.close()
        conn.close()
        
        # Format result
        return {
            "success": True,
            "refreshed_at": result['refreshed_at'].isoformat(),
            "total_assets": result['total_assets'],
            "new_assets": result['new_assets']
        }
        
    except Exception as e:
        logger.error(f"Error refreshing Gold view: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/gold/lineage/{asset_id}")
async def get_asset_lineage(asset_id: str):
    """
    Get complete data lineage trail for a specific asset.
    Shows all transformation events: bronze_ingested → silver_processed → gold_promoted
    
    Path Parameters:
        asset_id: UUID of the asset
    
    Returns:
        List of lineage events with timestamps and metadata
    """
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        from uuid import UUID
        
        # Validate UUID format
        try:
            UUID(asset_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid asset_id format. Must be UUID.")
        
        conn = psycopg2.connect(os.getenv('DATABASE_URL', 
            'postgresql://syniqai_user:syniqai_pass@localhost:5432/syniqai_metadata'))
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get lineage trail using stored function
        cursor.execute("SELECT * FROM get_lineage_trail(%s::UUID)", (asset_id,))
        lineage_events = cursor.fetchall()
        
        # Get asset metadata
        cursor.execute("""
            SELECT
                id,
                file_type,
                source,
                bronze_minio_key,
                silver_minio_key,
                processed_at
            FROM silver_assets
            WHERE id = %s::UUID
        """, (asset_id,))
        
        asset_metadata = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if not asset_metadata:
            raise HTTPException(status_code=404, detail=f"Asset {asset_id} not found")
        
        # Format lineage events
        formatted_events = []
        for event in lineage_events:
            event_dict = dict(event)
            # Convert datetime to ISO string
            if event_dict.get('event_time'):
                event_dict['event_time'] = event_dict['event_time'].isoformat()
            formatted_events.append(event_dict)
        
        # Format asset metadata
        asset_dict = dict(asset_metadata)
        if asset_dict.get('processed_at'):
            asset_dict['processed_at'] = asset_dict['processed_at'].isoformat()
        
        return {
            "success": True,
            "asset": asset_dict,
            "lineage": formatted_events,
            "total_events": len(formatted_events)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting lineage for asset {asset_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/gold/silver-tables")
async def list_silver_tables_for_gold():
    """
    List all available Silver structured tables for Gold transformation.
    Returns tables from both MinIO Silver bucket and database.
    """
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        from minio import Minio
        
        tables = []
        
        # Method 1: Query silver_assets for unique structured sources
        try:
            conn = psycopg2.connect(os.getenv('DATABASE_URL', 
                'postgresql://syniqai_user:syniqai_password@localhost:5432/syniqai_metadata'))
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Get structured data sources from silver_assets
            cursor.execute("""
                SELECT DISTINCT
                    source,
                    file_type,
                    COUNT(*) as row_count,
                    MIN(processed_at) as first_processed,
                    MAX(processed_at) as last_processed
                FROM silver_assets
                WHERE file_type IN ('csv', 'json', 'parquet', 'excel')
                   OR file_type = 'table'
                GROUP BY source, file_type
                ORDER BY source, file_type
            """)
            
            db_tables = cursor.fetchall()
            
            for row in db_tables:
                # Create a table name from source
                table_name = f"{row['source']}_{row['file_type']}_data"
                tables.append({
                    "name": table_name,
                    "full_name": f"syniqai_silver.{row['source']}.{table_name}",
                    "domain": row['source'],
                    "file_type": row['file_type'],
                    "row_count": row['row_count'],
                    "columns": [],
                    "source": "database",
                    "last_updated": row['last_processed'].isoformat() if row['last_processed'] else None
                })
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            logger.warning(f"Error querying database for Silver tables: {e}")
        
        # Method 2: Scan MinIO syniqai-silver bucket for Iceberg metadata
        try:
            minio_client = Minio(
                "localhost:9000",
                access_key="admin",
                secret_key="password123",
                secure=False
            )
            
            # Check if syniqai-silver bucket exists
            if minio_client.bucket_exists("syniqai-silver"):
                # List prefixes (domains/namespaces)
                objects = minio_client.list_objects("syniqai-silver", prefix="", recursive=False)
                
                domains = set()
                for obj in objects:
                    if obj.is_dir:
                        domain = obj.object_name.rstrip('/')
                        if domain and domain not in ['jpg', 'pdf', 'mp3', 'mp4', 'png']:  # Skip unstructured folders
                            domains.add(domain)
                
                # For each domain, look for table folders
                for domain in domains:
                    tables.append({
                        "name": f"{domain}_structured",
                        "full_name": f"syniqai_silver.{domain}.{domain}_structured",
                        "domain": domain,
                        "file_type": "structured",
                        "row_count": 0,
                        "columns": [],
                        "source": "minio",
                        "last_updated": None
                    })
                    
        except Exception as e:
            logger.warning(f"Error scanning MinIO for Silver tables: {e}")
        
        # If no tables found, return sample/placeholder tables
        if not tables:
            tables = [
                {
                    "name": "finance_structured",
                    "full_name": "syniqai_silver.finance.finance_structured",
                    "domain": "finance",
                    "file_type": "structured",
                    "row_count": 0,
                    "columns": ["transaction_id", "amount", "date", "category"],
                    "source": "placeholder",
                    "last_updated": None,
                    "note": "No structured data found. Upload CSV/Excel files to create Silver structured tables."
                },
                {
                    "name": "general_structured",
                    "full_name": "syniqai_silver.general.general_structured",
                    "domain": "general",
                    "file_type": "structured",
                    "row_count": 0,
                    "columns": [],
                    "source": "placeholder",
                    "last_updated": None,
                    "note": "Placeholder table. Upload structured data to populate."
                }
            ]
        
        return {
            "success": True,
            "tables": tables,
            "total": len(tables),
            "message": f"Found {len(tables)} Silver structured tables"
        }
        
    except Exception as e:
        logger.error(f"Error listing Silver tables: {e}")
        # Return fallback response instead of error
        return {
            "success": True,
            "tables": [
                {
                    "name": "finance_structured",
                    "full_name": "syniqai_silver.finance.finance_structured",
                    "domain": "finance",
                    "file_type": "structured",
                    "row_count": 0,
                    "columns": [],
                    "source": "fallback",
                    "note": "Using fallback table list due to error."
                }
            ],
            "total": 1,
            "message": "Error occurred, showing fallback tables",
            "error": str(e)
        }


# ==================== DASHBOARD & GOLD LAYER ENDPOINTS ====================

@app.get("/api/dashboard-summary")
def get_dashboard_summary(domain: str = None) -> Dict[str, Any]:
    """Get executive dashboard summary, optionally filtered by domain"""
    try:
        # Get Bronze tables based on domain
        bronze_mgr = storage.get_bronze_manager()
        
        if domain:
            # Domain-specific stats
            try:
                bronze_tables = bronze_mgr.list_tables(domain)
                total_bronze = len(bronze_tables)
            except Exception as e:
                logger.warning(f"Error getting bronze tables for {domain}: {e}")
                total_bronze = 0
        else:
            # All domains
            all_domains = ['finance', 'healthcare', 'general']
            total_bronze = 0
            for d in all_domains:
                try:
                    total_bronze += len(bronze_mgr.list_tables(d))
                except:
                    continue
        
        # Mock quality data for now
        return {
            "total_tables": total_bronze,
            "bronze_tables": total_bronze,
            "silver_tables": 0,  # TODO: Implement Silver layer counting
            "gold_tables": 0,    # TODO: Implement Gold layer counting
            "avg_quality_score": 87.5,
            "domain": domain or "all"
        }
    except Exception as e:
        logger.error(f"Error in dashboard-summary: {e}")
        import traceback
        traceback.print_exc()
        return get_mock_dashboard_data()


def get_dashboard_summary_old() -> Dict[str, Any]:
    """Get executive dashboard summary - OLD VERSION"""
    try:
        if aggregator:
            # Get real data from Gold layer
            try:
                tables = aggregator.discover_tables()
                
                # If no tables found, return mock data
                if not tables or len(tables) == 0:
                    print("No tables found in Gold layer, returning mock data")
                    return get_mock_dashboard_data()
                
                total_tables = len(tables)
                total_records = 0
                quality_scores = []
                completeness_scores = []
                
                for source, table in tables:
                    try:
                        silver_file = aggregator.silver_dir / source / f"{table}.parquet"
                        if silver_file.exists():
                            engine = GoldEDAEngine(str(silver_file))
                            quality = engine.analyze_quality()
                            
                            quality_scores.append(quality['overall_quality_score'])
                            completeness_scores.append(quality['completeness_score'])
                            total_records += quality['row_count']
                    except Exception as e:
                        print(f"Error processing {source}.{table}: {e}")
                        continue
                
                # If no valid quality scores, return mock data
                if not quality_scores:
                    print("No valid quality scores found, returning mock data")
                    return get_mock_dashboard_data()
                
                avg_quality = sum(quality_scores) / len(quality_scores)
                avg_completeness = sum(completeness_scores) / len(completeness_scores) if completeness_scores else 0
                
                # Quality distribution
                excellent = sum(1 for score in quality_scores if score >= 90)
                good = sum(1 for score in quality_scores if 75 <= score < 90)
                fair = sum(1 for score in quality_scores if 60 <= score < 75)
                poor = sum(1 for score in quality_scores if score < 60)
                
                return {
                    "totalTables": total_tables,
                    "avgQuality": round(avg_quality, 1),
                    "completeness": round(avg_completeness, 1),
                    "totalRecords": total_records,
                    "qualityDistribution": [
                        { "name": "Excellent", "value": excellent },
                        { "name": "Good", "value": good },
                        { "name": "Fair", "value": fair },
                        { "name": "Poor", "value": poor }
                    ],
                    "tableScores": [
                        {"table": f"{source}.{table}", "score": score}
                        for (source, table), score in zip(tables[:10], quality_scores[:10])
                    ]
                }
            except Exception as e:
                print(f"Error accessing Gold layer: {e}")
                return get_mock_dashboard_data()
        else:
            # Mock data when Gold layer is not available
            return get_mock_dashboard_data()
    except Exception as e:
        print(f"Unexpected error in dashboard-summary: {e}")
        # Return mock data instead of raising exception
        return get_mock_dashboard_data()


def get_mock_dashboard_data():
    """Return mock dashboard data"""
    return {
        "totalTables": 12,
        "avgQuality": 87.5,
        "completeness": 92.3,
        "totalRecords": 156789,
        "qualityDistribution": [
            { "name": "Excellent", "value": 6 },
            { "name": "Good", "value": 4 },
            { "name": "Fair", "value": 2 },
            { "name": "Poor", "value": 0 }
        ],
        "tableScores": [
            {"table": "postgres.customers", "score": 95},
            {"table": "postgres.transactions", "score": 89},
            {"table": "mysql.products", "score": 92},
            {"table": "mysql.orders", "score": 88},
            {"table": "mongodb.logs", "score": 85},
        ]
    }


@app.get("/api/eda/{source}/{table}")
def get_eda_analysis(source: str, table: str) -> Dict[str, Any]:
    """Get detailed EDA analysis for a specific table"""
    try:
        if aggregator:
            silver_file = aggregator.silver_dir / source / f"{table}.parquet"
            
            if not silver_file.exists():
                raise HTTPException(status_code=404, detail=f"Table {source}.{table} not found")
            
            engine = GoldEDAEngine(str(silver_file))
            
            # Get analysis components
            quality = engine.analyze_quality()
            stats = engine.compute_statistics()
            correlations = engine.find_correlations()
            
            return {
                "basic_info": {
                    "row_count": quality['row_count'],
                    "column_count": quality['column_count'],
                    "memory_mb": round(engine.df.memory_usage(deep=True).sum() / (1024**2), 2),
                    "duplicates": quality.get('duplicate_count', 0)
                },
                "data_quality": {
                    "overall_quality_score": quality['overall_quality_score'],
                    "completeness_score": quality['completeness_score'],
                    "missing_value_count": quality['missing_value_count'],
                    "duplicate_percentage": round(quality.get('duplicate_count', 0) / quality['row_count'] * 100, 2)
                },
                "column_analysis": quality['column_quality'],
                "correlations": correlations,
                "insights": engine.generate_insights()
            }
        else:
            # Mock EDA data
            return {
                "basic_info": {
                    "row_count": 45678,
                    "column_count": 12,
                    "memory_mb": 125.4,
                    "duplicates": 23
                },
                "data_quality": {
                    "overall_quality_score": 87.5,
                    "completeness_score": 94.2,
                    "missing_value_count": 145,
                    "duplicate_percentage": 0.05
                },
                "column_analysis": [
                    {"column": "customer_id", "type": "numeric", "non_null": 45678, "null_pct": 0, "unique": 12543},
                    {"column": "amount", "type": "numeric", "non_null": 45533, "null_pct": 0.3, "unique": 8745}
                ],
                "correlations": [
                    {"col1": "amount", "col2": "quantity", "correlation": 0.85}
                ],
                "insights": ["High quality data with 94.2% completeness"]
            }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/quality")
def get_quality_metrics() -> Dict[str, Any]:
    """Get quality metrics for all tables"""
    try:
        if aggregator:
            tables = aggregator.discover_tables()
            quality_data = []
            
            for source, table in tables:
                try:
                    silver_file = aggregator.silver_dir / source / f"{table}.parquet"
                    if silver_file.exists():
                        engine = GoldEDAEngine(str(silver_file))
                        quality = engine.analyze_quality()
                        
                        quality_data.append({
                            "table": f"{source}.{table}",
                            "score": quality['overall_quality_score'],
                            "completeness": quality['completeness_score'],
                            "missing": round((quality['missing_value_count'] / quality['row_count']) * 100, 1),
                            "duplicates": round(quality.get('duplicate_count', 0) / quality['row_count'] * 100, 2)
                        })
                except Exception as e:
                    print(f"Error processing {source}.{table}: {e}")
                    continue
            
            # Generate alerts
            alerts = []
            for item in quality_data:
                if item['score'] < 60:
                    alerts.append({
                        "severity": "[CRITICAL]",
                        "table": item['table'],
                        "issue": f"Quality score below threshold ({item['score']})",
                        "action": "Investigate data source and ingestion process"
                    })
                elif item['missing'] > 20:
                    alerts.append({
                        "severity": "[WARNING]",
                        "table": item['table'],
                        "issue": f"High missing value rate ({item['missing']}%)",
                        "action": "Review data collection process"
                    })
            
            return {
                "quality_data": quality_data,
                "alerts": alerts
            }
        else:
            # Mock quality data
            return {
                "quality_data": [
                    {"table": "postgres.customers", "score": 95, "completeness": 98, "missing": 2, "duplicates": 0.1},
                    {"table": "postgres.transactions", "score": 89, "completeness": 92, "missing": 8, "duplicates": 0.5}
                ],
                "alerts": [
                    {"severity": "[WARNING]", "table": "postgres.transactions", "issue": "Missing values above threshold", "action": "Review data collection"}
                ]
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/quality/alerts")
def get_quality_alerts() -> List[Dict[str, Any]]:
    """Get active quality alerts"""
    try:
        quality_response = get_quality_metrics()
        return quality_response.get("alerts", [])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/tables")
def list_tables() -> List[Dict[str, str]]:
    """List all available tables"""
    try:
        if aggregator:
            tables = aggregator.discover_tables()
            return [
                {"source": source, "table": table, "path": f"{source}.{table}"}
                for source, table in tables
            ]
        else:
            return [
                {"source": "postgres", "table": "customers", "path": "postgres.customers"},
                {"source": "postgres", "table": "transactions", "path": "postgres.transactions"},
                {"source": "mysql", "table": "products", "path": "mysql.products"}
            ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/export")
def export_report(report_type: str = "executive", format: str = "json"):
    """Generate and export a report"""
    try:
        if GoldReportGenerator and aggregator:
            tables = aggregator.discover_tables()
            eda_results = {}
            
            for source, table in tables:
                try:
                    silver_file = aggregator.silver_dir / source / f"{table}.parquet"
                    if silver_file.exists():
                        engine = GoldEDAEngine(str(silver_file))
                        eda_results[f"{source}.{table}"] = {
                            "quality": engine.analyze_quality(),
                            "statistics": engine.compute_statistics(),
                            "correlations": engine.find_correlations()
                        }
                except Exception as e:
                    print(f"Error processing {source}.{table}: {e}")
                    continue
            
            generator = GoldReportGenerator(eda_results)
            
            if format == "json":
                output = generator.generate_json_report()
            elif format == "html":
                output = generator.generate_html_report()
            elif format == "markdown":
                output = generator.generate_markdown_report()
            else:
                raise HTTPException(status_code=400, detail=f"Unsupported format: {format}")
            
            return {"status": "success", "report": output}
        else:
            return {
                "status": "success",
                "report": {"message": "Mock report generated", "tables": 12, "avg_quality": 87.5}
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/ingestion-logs")
def get_ingestion_logs(limit: int = 50):
    """Get recent ingestion logs"""
    # This would integrate with your ingestion logging system
    # For now, returning mock data
    return [
        {"timestamp": "2026-02-23 14:30:25", "table": "postgres.customers", "status": "success", "records": 12543},
        {"timestamp": "2026-02-23 14:25:18", "table": "mysql.products", "status": "success", "records": 5678},
        {"timestamp": "2026-02-23 14:20:42", "table": "mongodb.logs", "status": "success", "records": 89012}
    ]


# ===========================================
# NEW ENDPOINTS: Domain-Based Operations
# ===========================================

@app.get("/api/domains")
def get_available_domains():
    """Get list of available domains"""
    return {
        "domains": [
            {"id": "finance", "name": "Finance", "icon": "$", "description": "Financial data processing"},
            {"id": "healthcare", "name": "Healthcare", "icon": "+", "description": "Healthcare compliance"},
            {"id": "general", "name": "General", "icon": "◈", "description": "General data quality"}
        ]
    }


@app.get("/api/bronze/tables")
def get_all_bronze_tables(
    page: int = 1,
    page_size: int = 1000
):
    """Get all Bronze tables across all domains (for Silver layer processing status)"""
    try:
        from datetime import datetime
        
        bronze_mgr = storage.get_bronze_manager()
        all_tables = []
        
        # Fetch tables from all known domains
        domains = ["finance", "healthcare", "general"]
        for domain in domains:
            try:
                domain_tables = bronze_mgr.list_tables(domain)
                # Add domain info to each table
                for table in domain_tables:
                    table['domain'] = domain
                all_tables.extend(domain_tables)
            except Exception as e:
                print(f"[Bronze] Warning: Failed to fetch tables from domain '{domain}': {e}")
                continue
        
        # Sort by last_modified (most recent first)
        all_tables.sort(key=lambda t: t.get('last_modified', ''), reverse=True)
        
        # Paginate
        total_count = len(all_tables)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_tables = all_tables[start_idx:end_idx]
        
        return {
            "tables": paginated_tables,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_pages": (total_count + page_size - 1) // page_size,
                "total_count": total_count
            }
        }
    except Exception as e:
        print(f"[Bronze] Error fetching all tables: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to fetch Bronze tables: {str(e)}")


@app.get("/api/bronze/tables/{domain}")
def get_bronze_tables(
    domain: str,
    search: str = "",
    source_type: str = "",
    format_filter: str = "",
    size_min: int = 0,
    size_max: int = None,
    date_filter: str = "",  # 24h, 7d, 30d, all
    sort_by: str = "last_modified",  # name, size, last_modified, row_count
    sort_order: str = "desc",  # asc, desc
    page: int = 1,
    page_size: int = 50
):
    """Get all tables in Bronze layer with search, filters, sorting, and pagination"""
    try:
        from datetime import datetime, timedelta
        
        bronze_mgr = storage.get_bronze_manager()
        all_tables = bronze_mgr.list_tables(domain)
        
        # Apply search filter
        if search:
            search_lower = search.lower()
            all_tables = [t for t in all_tables if 
                         search_lower in t["table_name"].lower() or
                         search_lower in t.get("source_type", "").lower()]
        
        # Apply source type filter
        if source_type:
            all_tables = [t for t in all_tables if t.get("source_type") == source_type]
        
        # Apply format filter
        if format_filter:
            all_tables = [t for t in all_tables if t.get("format", "").lower() == format_filter.lower()]
        
        # Apply size filter
        if size_max:
            all_tables = [t for t in all_tables if size_min <= t.get("total_size", 0) <= size_max]
        elif size_min > 0:
            all_tables = [t for t in all_tables if t.get("total_size", 0) >= size_min]
        
        # Apply date filter
        if date_filter and date_filter != "all":
            now = datetime.now()
            hours_map = {"24h": 24, "7d": 168, "30d": 720}
            if date_filter in hours_map:
                cutoff = now - timedelta(hours=hours_map[date_filter])
                all_tables = [t for t in all_tables if 
                             isinstance(t.get("last_modified"), datetime) and 
                             t["last_modified"] >= cutoff]
        
        # Apply sorting
        reverse = (sort_order == "desc")
        if sort_by == "name":
            all_tables.sort(key=lambda x: x.get("table_name", "").lower(), reverse=reverse)
        elif sort_by == "size":
            all_tables.sort(key=lambda x: x.get("total_size", 0), reverse=reverse)
        elif sort_by == "row_count":
            all_tables.sort(key=lambda x: x.get("row_count", 0), reverse=reverse)
        else:  # last_modified
            all_tables.sort(key=lambda x: x.get("last_modified", datetime.min), reverse=reverse)
        
        # Calculate pagination
        total_count = len(all_tables)
        total_pages = (total_count + page_size - 1) // page_size
        start_idx = (page - 1) * page_size
        end_idx = min(start_idx + page_size, total_count)
        paginated_tables = all_tables[start_idx:end_idx]
        
        return {
            "domain": domain,
            "tables": paginated_tables,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_count": total_count,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1
            },
            "filters_applied": {
                "search": search,
                "source_type": source_type,
                "format": format_filter,
                "date_filter": date_filter
            }
        }
    except Exception as e:
        logger.error(f"Error listing Bronze tables for {domain}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/bronze/table/{domain}/{table_name}")
def get_bronze_table_details(
    domain: str, 
    table_name: str,
    page: int = 1,
    page_size: int = 100,
    search: str = ""
):
    """Get schema and sample data for a specific Bronze table with pagination"""
    try:
        # Get bronze manager
        bronze_mgr = storage.get_bronze_manager()
        
        # Get schema (will detect file type automatically)
        schema = bronze_mgr.get_table_schema(domain, table_name)
        
        if schema is None:
            raise HTTPException(status_code=404, detail=f"Table {table_name} not found")
        
        # Check if this is an unstructured file
        if schema.get("file_type") and schema["file_type"] != "structured":
            # Return file metadata for unstructured files
            return {
                "domain": domain,
                "table_name": table_name,
                "file_type": schema["file_type"],
                "metadata": schema,
                "is_structured": False
            }
        
        # For structured data, proceed with normal flow
        # Get ALL data (we'll paginate it)
        sample_df = bronze_mgr.read_table_sample(domain, table_name, max_rows=None)
        
        if sample_df is None:
            raise HTTPException(status_code=404, detail=f"Table {table_name} not found")
        
        # Apply search filter if provided
        filtered_df = sample_df.copy()
        if search:
            # Search across all columns (convert to string for searching)
            mask = filtered_df.astype(str).apply(
                lambda row: row.str.contains(search, case=False, na=False).any(), 
                axis=1
            )
            filtered_df = filtered_df[mask]
        
        # Calculate pagination
        total_rows = len(filtered_df)
        total_pages = (total_rows + page_size - 1) // page_size  # Ceiling division
        page = max(1, min(page, total_pages if total_pages > 0 else 1))  # Clamp page number
        
        # Get paginated data
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_df = filtered_df.iloc[start_idx:end_idx]
        
        # Convert to JSON-safe types
        import pandas as pd
        import numpy as np
        from datetime import datetime, date
        
        def make_json_safe(obj):
            """Convert pandas/numpy types to JSON-safe Python types"""
            if pd.isna(obj) or obj is None:
                return None
            elif isinstance(obj, (np.integer, np.int64, np.int32)):
                return int(obj)
            elif isinstance(obj, (np.floating, np.float64, np.float32)):
                if np.isnan(obj) or np.isinf(obj):
                    return None
                return float(obj)
            elif isinstance(obj, (datetime, date, pd.Timestamp)):
                return obj.isoformat()
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            return obj
        
        # Process schema columns
        if schema and 'columns' in schema:
            for col in schema['columns']:
                for key, value in col.items():
                    col[key] = make_json_safe(value)
            # Make top-level schema values safe too
            for key in ['row_count', 'memory_usage']:
                if key in schema:
                    schema[key] = make_json_safe(schema[key])
        
        # Process sample data
        paginated_df = paginated_df.replace({np.nan: None, np.inf: None, -np.inf: None})
        sample_data = []
        for record in paginated_df.to_dict(orient="records"):
            safe_record = {k: make_json_safe(v) for k, v in record.items()}
            sample_data.append(safe_record)
        
        # Generate EDA insights (only on full dataset, not paginated)
        logger.info(f"Generating EDA analysis for {domain}.{table_name} with {len(sample_df)} rows")
        eda_insights = generate_bronze_eda(sample_df)
        
        return {
            "domain": domain,
            "table_name": table_name,
            "schema": schema,
            "sample_data": sample_data,
            "total_rows": int(len(sample_df)),  # Original total
            "filtered_rows": total_rows,  # After search filter
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "showing_from": start_idx + 1,
            "showing_to": min(end_idx, total_rows),
            "eda": eda_insights  # ✨ NEW: Comprehensive EDA analysis
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting Bronze table details: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/bronze/preview/{domain}/{table_name:path}")
async def preview_file(domain: str, table_name: str):
    """Stream file content for preview (images, PDFs, etc.)"""
    try:
        from fastapi.responses import StreamingResponse
        import mimetypes
        
        bronze_mgr = storage.get_bronze_manager()
        files = bronze_mgr.get_table_files(domain, table_name)
        
        if not files:
            raise HTTPException(status_code=404, detail="File not found")
        
        # Get file from MinIO
        from app_config import MinIOConfig
        minio_config = MinIOConfig.from_env()
        
        file_obj = files[0]
        file_data = storage.storage_manager.client.get_object(
            minio_config.bronze_bucket,
            file_obj["object_name"]
        )
        
        # Determine content type
        content_type = mimetypes.guess_type(table_name)[0] or 'application/octet-stream'
        
        return StreamingResponse(
            file_data,
            media_type=content_type,
            headers={"Content-Disposition": f"inline; filename={table_name}"}
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error previewing file: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/bronze/download/{domain}/{table_name:path}")
async def download_file(domain: str, table_name: str):
    """Generate presigned URL for file download"""
    try:
        from datetime import timedelta
        from app_config import MinIOConfig
        
        bronze_mgr = storage.get_bronze_manager()
        files = bronze_mgr.get_table_files(domain, table_name)
        
        if not files:
            raise HTTPException(status_code=404, detail="File not found")
        
        minio_config = MinIOConfig.from_env()
        file_obj = files[0]
        
        # Generate presigned URL (expires in 1 hour)
        url = storage.storage_manager.client.presigned_get_object(
            minio_config.bronze_bucket,
            file_obj["object_name"],
            expires=timedelta(hours=1)
        )
        
        return {
            "download_url": url,
            "filename": table_name,
            "size_bytes": file_obj["size"]
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating download URL: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ===========================================
# NEW ENDPOINTS: Rules Management
# ===========================================

@app.get("/api/rules/{domain}")
def get_rules_by_domain(domain: str, status: str = "active"):
    """Get all rules for a specific domain"""
    try:
        rules = rules_repo.get_rules_by_domain(domain, status)
        return {"domain": domain, "status": status, "rules": rules, "count": len(rules)}
    except Exception as e:
        logger.error(f"Error getting rules for {domain}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/rules/table/{domain}/{table_name}")
def get_rules_by_table(domain: str, table_name: str):
    """Get all active rules for a specific table"""
    try:
        rules = rules_repo.get_rules_by_table(domain, table_name)
        return {"domain": domain, "table": table_name, "rules": rules, "count": len(rules)}
    except Exception as e:
        logger.error(f"Error getting rules for {domain}/{table_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class RuleCreate(BaseModel):
    rule_name: str
    domain: str
    category: str
    rule_type: str
    description: str
    source_table: str
    target_column: str
    condition_expression: str
    severity: str
    action: str
    execution_order: int = 100
    created_by: str


@app.post("/api/rules")
def create_rule(rule: RuleCreate):
    """Create a new rule"""
    try:
        rule_id = rules_repo.create_rule(rule.dict())
        return {"status": "success", "rule_id": rule_id}
    except Exception as e:
        logger.error(f"Error creating rule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/rules/{rule_id}")
def update_rule(rule_id: str, updates: Dict[str, Any]):
    """Update an existing rule"""
    try:
        success = rules_repo.update_rule(rule_id, updates)
        if success:
            return {"status": "success", "rule_id": rule_id}
        else:
            raise HTTPException(status_code=404, detail="Rule not found")
    except Exception as e:
        logger.error(f"Error updating rule {rule_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/rules/{rule_id}")
def delete_rule(rule_id: str):
    """Archive a rule"""
    try:
        success = rules_repo.delete_rule(rule_id)
        if success:
            return {"status": "success", "rule_id": rule_id}
        else:
            raise HTTPException(status_code=404, detail="Rule not found")
    except Exception as e:
        logger.error(f"Error deleting rule {rule_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===========================================
# NEW ENDPOINTS: Quarantine Management
# ===========================================

@app.get("/api/quarantine/{domain}")
def get_quarantine_records(domain: str, status: str = "pending", limit: int = 100):
    """Get quarantine records for a domain"""
    try:
        records = quarantine_repo.get_quarantine_records(domain, status, limit)
        return {"domain": domain, "status": status, "records": records, "count": len(records)}
    except Exception as e:
        logger.error(f"Error getting quarantine records for {domain}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/quarantine/summary/{domain}")
def get_quarantine_summary(domain: str):
    """Get quarantine summary statistics"""
    try:
        summary = quarantine_repo.get_quarantine_summary(domain)
        return {"domain": domain, "summary": summary}
    except Exception as e:
        logger.error(f"Error getting quarantine summary for {domain}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class QuarantineResolution(BaseModel):
    resolution: str
    resolved_by: str


@app.post("/api/quarantine/{quarantine_id}/resolve")
def resolve_quarantine(quarantine_id: str, resolution: QuarantineResolution):
    """Mark a quarantine record as resolved"""
    try:
        success = quarantine_repo.resolve_quarantine(
            quarantine_id, 
            resolution.resolution, 
            resolution.resolved_by
        )
        if success:
            return {"status": "success", "quarantine_id": quarantine_id}
        else:
            raise HTTPException(status_code=404, detail="Quarantine record not found")
    except Exception as e:
        logger.error(f"Error resolving quarantine {quarantine_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===========================================
# NEW ENDPOINTS: Execution Logs
# ===========================================

@app.get("/api/execution/history/{rule_id}")
def get_execution_history(rule_id: str, limit: int = 50):
    """Get execution history for a specific rule"""
    try:
        history = execution_log_repo.get_execution_history(rule_id, limit)
        return {"rule_id": rule_id, "history": history, "count": len(history)}
    except Exception as e:
        logger.error(f"Error getting execution history for {rule_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/execution/failures/{domain}")
def get_failed_executions(domain: str, hours: int = 24):
    """Get failed rule executions in the last N hours"""
    try:
        failures = execution_log_repo.get_failed_executions(domain, hours)
        return {"domain": domain, "hours": hours, "failures": failures, "count": len(failures)}
    except Exception as e:
        logger.error(f"Error getting failed executions for {domain}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# SQL PREVIEW ENDPOINT - Execute SQL queries for testing and verification
# ============================================================================

class SQLPreviewRequest(BaseModel):
    """SQL preview request model"""
    sql: str
    source: str
    entity: str


@app.get("/api/silver/database-tables")
def list_database_tables():
    """
    List all tables available for querying in MinIO (Bronze and Silver layers).
    These are the tables you can query in SQL preview.
    """
    try:
        table_mapping = _discover_minio_tables()
        
        # Format table list
        tables = []
        for table_name, info in table_mapping.items():
            tables.append({
                "name": table_name,
                "layer": info['layer'],
                "source": info['source'],
                "entity": info['entity'],
                "location": f"{info['bucket']}/{info['object_path']}"
            })
        
        # Sort by layer (bronze first) then name
        tables.sort(key=lambda x: (0 if x['layer'] == 'bronze' else 1, x['name']))
        
        return {
            "storage": "MinIO (Parquet files)",
            "tables": tables,
            "count": len(tables),
            "message": "These tables are queryable via SQL preview. Data is stored as Parquet files in MinIO."
        }
    except Exception as e:
        logger.error(f"Error listing MinIO tables: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list tables: {str(e)}")


@app.post("/api/silver/sql-preview")
def execute_sql_preview(request: SQLPreviewRequest):
    """
    Execute SQL query on MinIO Parquet files using DuckDB.
    Queries Bronze/Silver data stored in MinIO.
    Only SELECT queries are allowed for security.
    """
    import time
    import duckdb
    import tempfile
    import os
    start_time = time.time()
    
    try:
        # Security check: only allow SELECT queries
        sql_upper = request.sql.strip().upper()
        if not sql_upper.startswith('SELECT'):
            raise HTTPException(
                status_code=400, 
                detail="Only SELECT queries are allowed for preview. DROP, DELETE, UPDATE, INSERT are forbidden."
            )
        
        # Additional security checks
        dangerous_keywords = ['DROP', 'DELETE', 'UPDATE', 'INSERT', 'TRUNCATE', 'ALTER', 'CREATE']
        for keyword in dangerous_keywords:
            if keyword in sql_upper:
                raise HTTPException(
                    status_code=400,
                    detail=f"Query contains forbidden keyword: {keyword}. Only SELECT queries are allowed."
                )
        
        logger.info(f"Executing SQL preview on MinIO: {request.sql[:100]}...")
        
        # Discover available tables in MinIO (Bronze and Silver)
        table_mapping = _discover_minio_tables()
        
        if not table_mapping:
            raise HTTPException(
                status_code=404,
                detail="No tables found in MinIO Bronze/Silver layers. Please run data ingestion first."
            )
        
        # Download Parquet files to temp directory and create DuckDB views
        temp_dir = tempfile.mkdtemp(prefix="sql_preview_")
        try:
            conn = duckdb.connect(':memory:')
            
            # Register all tables as views in DuckDB
            for table_name, table_info in table_mapping.items():
                parquet_path = _download_parquet_to_temp(
                    table_info['bucket'],
                    table_info['object_path'],
                    temp_dir,
                    table_name
                )
                
                # Create view in DuckDB
                conn.execute(f"CREATE VIEW {table_name} AS SELECT * FROM read_parquet('{parquet_path}')")
                logger.info(f"Registered table: {table_name} from {table_info['layer']}")
            
            # Execute the user's SQL query
            result = conn.execute(request.sql).fetchall()
            columns = [desc[0] for desc in conn.description]
            
            # Convert to JSON-serializable format
            serialized_rows = []
            for row in result:
                serialized_row = []
                for cell in row:
                    # Handle datetime objects
                    if hasattr(cell, 'isoformat'):
                        serialized_row.append(cell.isoformat())
                    # Handle None/NULL
                    elif cell is None:
                        serialized_row.append(None)
                    else:
                        serialized_row.append(cell)
                serialized_rows.append(serialized_row)
            
            conn.close()
            
        finally:
            # Cleanup temporary files
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
        
        execution_time = time.time() - start_time
        
        logger.info(f"✓ SQL preview executed successfully: {len(serialized_rows)} rows in {execution_time:.3f}s")
        
        return {
            "columns": columns,
            "rows": serialized_rows,
            "rowCount": len(serialized_rows),
            "executionTime": f"{execution_time:.3f}s",
            "sql": request.sql[:200],
            "tablesQueried": list(table_mapping.keys())
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions (validation errors)
        raise
    except Exception as e:
        error_msg = str(e)
        logger.error(f"SQL preview failed: {error_msg}")
        
        # Provide helpful error message for missing tables
        if "table" in error_msg.lower() and ("does not exist" in error_msg.lower() or "not found" in error_msg.lower()):
            available_tables = list(_discover_minio_tables().keys())
            raise HTTPException(
                status_code=404, 
                detail=f"Table not found in MinIO. {error_msg}\n\n" +
                       f"Available tables: {', '.join(available_tables) if available_tables else '(none)'}\n\n" +
                       "To add data:\n" +
                       "1. Go to Bronze layer and run data ingestion\n" +
                       "2. Ingest data from your source database\n" +
                       "3. Data will be stored in MinIO as Parquet files\n" +
                       "4. Then you can query it here"
            )
        else:
            raise HTTPException(status_code=500, detail=f"Query execution failed: {error_msg}")


def _discover_minio_tables() -> Dict[str, Dict]:
    """
    Discover all tables in MinIO Bronze and Silver layers that have data.parquet files.
    Also discovers Iceberg tables in Silver layer.
    Returns dict mapping table names to bucket/object paths.
    """
    from minio_utils import MinIOClient
    
    table_mapping = {}
    minio_client = MinIOClient()
    
    # Check Bronze and Silver layers
    for layer in ['bronze', 'silver']:
        try:
            bucket = f"syniqai-{layer}"
            
            # For Silver layer, also check for Iceberg tables
            if layer == 'silver':
                try:
                    # List objects in iceberg/ prefix
                    iceberg_objects = minio_client.client.list_objects(bucket, prefix='iceberg/', recursive=True)
                    
                    # Track discovered namespaces and tables
                    iceberg_tables = set()
                    for obj in iceberg_objects:
                        # Iceberg structure: iceberg/namespace/tablename/metadata/
                        parts = obj.object_name.split('/')
                        if len(parts) >= 4 and parts[0] == 'iceberg':
                            namespace = parts[1]  # e.g., 'finance'
                            tablename = parts[2]  # e.g., 'transactions_data'
                            table_key = f"{namespace}.{tablename}"
                            
                            if table_key not in iceberg_tables:
                                iceberg_tables.add(table_key)
                                
                                # Create table mapping entry
                                display_name = f"{namespace}_{tablename}"
                                if display_name in table_mapping:
                                    display_name = f"iceberg_{display_name}"
                                
                                table_mapping[display_name] = {
                                    'layer': 'silver',
                                    'source': namespace,
                                    'entity': tablename,
                                    'bucket': bucket,
                                    'object_path': f"iceberg/{namespace}/{tablename}/",
                                    'format': 'iceberg'
                                }
                                logger.info(f"Discovered Iceberg table: {display_name} (silver)")
                
                except Exception as e:
                    logger.warning(f"Could not list Iceberg tables in {bucket}: {e}")
            
            # Standard table discovery (flat parquet structure)
            try:
                tables = minio_client.list_tables(layer)
                for table in tables:
                    # Verify data.parquet actually exists
                    object_path = f"{table['source']}/{table['entity']}/data.parquet"
                    
                    try:
                        # Check if object exists
                        minio_client.client.stat_object(bucket, object_path)
                        
                        # Create table name: entity (or source_entity if duplicate)
                        table_name = table['entity']
                        
                        # If duplicate, prefix with source
                        if table_name in table_mapping:
                            table_name = f"{table['source']}_{table['entity']}"
                        
                        table_mapping[table_name] = {
                            'layer': layer,
                            'source': table['source'],
                            'entity': table['entity'],
                            'bucket': bucket,
                            'object_path': object_path,
                            'format': 'parquet'
                        }
                        logger.info(f"Discovered table: {table_name} ({layer})")
                        
                    except Exception as e:
                        # File doesn't exist, skip this table
                        logger.debug(f"Skipping {table['source']}/{table['entity']} - no data.parquet: {e}")
                        continue
            except Exception as e:
                logger.warning(f"Could not list standard tables in {layer}: {e}")
                    
        except Exception as e:
            logger.warning(f"Could not process {layer} layer: {e}")
    
    return table_mapping


def _download_parquet_to_temp(bucket: str, object_path: str, temp_dir: str, table_name: str) -> str:
    """
    Download Parquet file from MinIO to temporary directory.
    Returns path to downloaded file.
    """
    from minio_utils import MinIOClient
    
    minio_client = MinIOClient()
    temp_file = os.path.join(temp_dir, f"{table_name}.parquet")
    
    try:
        minio_client.client.fget_object(bucket, object_path, temp_file)
        logger.info(f"Downloaded {bucket}/{object_path} to {temp_file}")
        return temp_file
    except Exception as e:
        logger.error(f"Failed to download {bucket}/{object_path}: {e}")
        raise


# ==================== SILVER ASSETS (AI PROCESSING) ENDPOINTS ====================

@app.get("/api/silver/assets")
def get_silver_assets(
    file_type: Optional[str] = None,
    status: Optional[str] = None,
    source: Optional[str] = None,
    limit: int = 20
):
    """
    Query silver_assets table with optional filters
    Used by Media Processing Dashboard
    """
    try:
        # Get database connection string from DATABASE_URL env var
        database_url = os.getenv(
            "DATABASE_URL",
            "postgresql://syniqai_user:syniqai_password@localhost:5432/syniqai_metadata"
        )
        
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        conn = psycopg2.connect(database_url)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Build query with filters
        query = "SELECT * FROM silver_assets WHERE 1=1"
        params = []
        
        if file_type:
            query += " AND file_type = %s"
            params.append(file_type)
        
        if status:
            query += " AND extraction_status = %s"
            params.append(status)
        
        if source:
            query += " AND source = %s"
            params.append(source)
        
        query += " ORDER BY processed_at DESC LIMIT %s"
        params.append(limit)
        
        cur.execute(query, params)
        assets = cur.fetchall()
        
        # Convert to list of dicts with proper types
        result = []
        for asset in assets:
            asset_dict = dict(asset)
            # Convert UUID and datetime to strings
            asset_dict['id'] = str(asset_dict['id'])
            asset_dict['processed_at'] = asset_dict['processed_at'].isoformat() if asset_dict['processed_at'] else None
            result.append(asset_dict)
        
        cur.close()
        conn.close()
        
        return {
            "success": True,
            "assets": result,
            "count": len(result)
        }
    
    except Exception as e:
        logger.error(f"Failed to query silver_assets: {e}")
        return {
            "success": False,
            "error": str(e),
            "assets": []
        }


@app.get("/api/silver/assets/stats")
def get_silver_assets_stats():
    """
    Get statistics for dashboard counters
    Returns counts by file_type
    """
    try:
        database_url = os.getenv(
            "DATABASE_URL",
            "postgresql://syniqai_user:syniqai_password@localhost:5432/syniqai_metadata"
        )
        
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        conn = psycopg2.connect(database_url)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get counts by file type
        cur.execute("""
            SELECT 
                file_type,
                COUNT(*) as count,
                SUM(CASE WHEN extraction_status = 'success' THEN 1 ELSE 0 END) as success_count,
                SUM(CASE WHEN extraction_status = 'failed' THEN 1 ELSE 0 END) as failed_count
            FROM silver_assets
            GROUP BY file_type
        """)
        
        file_type_stats = cur.fetchall()
        
        # Get overall stats
        cur.execute("""
            SELECT 
                COUNT(*) as total_files,
                COUNT(DISTINCT CASE WHEN file_type IN ('jpg', 'jpeg', 'png', 'gif', 'bmp') THEN id END) as images,
                COUNT(DISTINCT CASE WHEN file_type = 'pdf' THEN id END) as documents,
                AVG(ai_confidence_score) as avg_confidence
            FROM silver_assets
        """)
        
        overall = cur.fetchone()
        
        cur.close()
        conn.close()
        
        return {
            "success": True,
            "total_files": overall['total_files'] or 0,
            "images": overall['images'] or 0,
            "videos": 0,  # Not yet implemented
            "audio": 0,   # Not yet implemented
            "documents": overall['documents'] or 0,
            "avg_confidence": float(overall['avg_confidence']) if overall['avg_confidence'] else 0.0,
            "by_file_type": [dict(row) for row in file_type_stats]
        }
    
    except Exception as e:
        logger.error(f"Failed to get silver_assets stats: {e}")
        return {
            "success": False,
            "error": str(e),
            "total_files": 0,
            "images": 0,
            "videos": 0,
            "audio": 0,
            "documents": 0
        }


@app.get("/api/silver/download/{asset_id}")
def download_silver_asset(asset_id: str):
    """
    Generate presigned MinIO URL for downloading the original file
    Looks up bronze_minio_key from PostgreSQL and creates 1-hour presigned URL
    """
    try:
        database_url = os.getenv(
            "DATABASE_URL",
            "postgresql://syniqai_user:syniqai_password@localhost:5432/syniqai_metadata"
        )
        
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        conn = psycopg2.connect(database_url)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get bronze_minio_key
        cur.execute(
            "SELECT bronze_minio_key, file_type FROM silver_assets WHERE id = %s",
            (asset_id,)
        )
        
        asset = cur.fetchone()
        cur.close()
        conn.close()
        
        if not asset:
            raise HTTPException(status_code=404, detail="Asset not found")
        
        bronze_key = asset['bronze_minio_key']
        
        # Generate presigned URL (1 hour expiry)
        from datetime import timedelta
        presigned_url = storage.storage_manager.client.presigned_get_object(
            "syniqai-bronze",
            bronze_key,
            expires=timedelta(hours=1)
        )
        
        return {
            "success": True,
            "download_url": presigned_url,
            "bronze_minio_key": bronze_key,
            "file_type": asset['file_type'],
            "expires_in_seconds": 3600
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate download URL: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Unstructured Data Processing Endpoints (Missing routes added)
# ============================================================================

@app.post("/api/silver/unstructured/process")
async def process_unstructured(background_tasks: BackgroundTasks, asset_id: str = None, file_type: str = None):
    """Process specific unstructured file through AI processing"""
    import uuid
    database_url = os.getenv("DATABASE_URL", "postgresql://syniqai_user:syniqai_password@localhost:5432/syniqai_metadata")
    
    try:
        import psycopg2
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()
        
        # Create job record
        job_id = str(uuid.uuid4())
        cur.execute(
            "INSERT INTO pipeline_jobs (id, job_type, status, file_type) VALUES (%s, %s, %s, %s)",
            (job_id, "unstructured_processing", "processing", file_type)
        )
        conn.commit()
        cur.close()
        conn.close()
        
        return {"job_id": job_id, "status": "processing"}
    except Exception as e:
        logger.error(f"Failed to create processing job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/silver/unstructured/jobs/{job_id}")
def get_unstructured_job(job_id: str):
    """Get unstructured processing job status"""
    database_url = os.getenv("DATABASE_URL", "postgresql://syniqai_user:syniqai_password@localhost:5432/syniqai_metadata")
    
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        conn = psycopg2.connect(database_url)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute(
            "SELECT id as job_id, status, error_message, started_at, completed_at FROM pipeline_jobs WHERE id = %s",
            (job_id,)
        )
        job = cur.fetchone()
        cur.close()
        conn.close()
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        return dict(job)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get job status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/silver/unstructured/preview/image")
def preview_images(limit: int = 20, domain: str = None, entity: str = None):
    """Preview image files from silver assets"""
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        # Use environment variables with proper fallbacks
        conn = psycopg2.connect(
            host=os.getenv('POSTGRES_HOST', 'localhost'),
            port=int(os.getenv('POSTGRES_PORT', 5432)),
            database=os.getenv('POSTGRES_DB', 'syniqai_metadata'),
            user=os.getenv('POSTGRES_USER', 'syniqai_user'),
            password=os.getenv('POSTGRES_PASSWORD', 'syniqai_password')
        )
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Query with debug logging
        query = """SELECT id, bronze_minio_key, silver_minio_key, content_tags, summary, 
                      file_type, extraction_status, processed_at, ai_confidence_score
               FROM silver_assets 
               WHERE file_type IN ('jpg','jpeg','png','gif','bmp','webp','tiff')
               ORDER BY processed_at DESC
               LIMIT %s"""
        
        cur.execute(query, (limit,))
        rows = cur.fetchall()
        logger.info(f"[PREVIEW IMAGE] Found {len(rows)} images in silver_assets table")
        
        cur.close()
        conn.close()
        
        # Transform to match frontend expectations
        records = []
        for row in rows:
            filename = row['bronze_minio_key'].split('/')[-1] if row['bronze_minio_key'] else 'unknown.jpg'
            records.append({
                'file_name': filename,
                'bronze_path': row['bronze_minio_key'],
                's3_path': f"s3a://syniqai-bronze/{row['bronze_minio_key']}",
                'path': row['bronze_minio_key'],
                'processing_status': row['extraction_status'] or 'pending',
                'last_modified': row['processed_at'].isoformat() if row['processed_at'] else None,
                'width': None,  # Not stored in current schema
                'height': None,
                'format': row['file_type'],
                'blur_score': None,
                'brightness_avg': None,
                'confidence': row['ai_confidence_score'],
                'id': row['id'],
                'silver_key': row['silver_minio_key']
            })
        
        logger.info(f"[PREVIEW IMAGE] Returning {len(records)} records to frontend")
        return {'records': records, 'total': len(records), 'success': True}
        
    except Exception as e:
        logger.error(f"Failed to preview images: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/silver/unstructured/models")
def get_ai_models():
    """Get available AI models from routing config"""
    database_url = os.getenv("DATABASE_URL", "postgresql://syniqai_user:syniqai_password@localhost:5432/syniqai_metadata")
    
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        conn = psycopg2.connect(database_url)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("SELECT data_type, model_id FROM routing_config ORDER BY data_type")
        rows = cur.fetchall()
        cur.close()
        conn.close()
        
        # Transform to match frontend expectations
        models = []
        for row in rows:
            data_type = row['data_type']
            model_id = row['model_id']
            
            # Map data types to media types and categories
            media_type_map = {
                'image': {'media_types': ['image'], 'category': 'detection'},
                'video': {'media_types': ['video'], 'category': 'detection'},
                'audio': {'media_types': ['audio'], 'category': 'transcription'},
                'pdf': {'media_types': ['document'], 'category': 'extraction'},
                'text': {'media_types': ['text'], 'category': 'analysis'}
            }
            
            config = media_type_map.get(data_type, {'media_types': [data_type], 'category': 'other'})
            
            models.append({
                'id': model_id,
                'name': model_id,
                'media_types': config['media_types'],
                'category': config['category'],
                'description': f"{data_type.title()} processing model"
            })
        
        return {'models': models}
    except Exception as e:
        logger.error(f"Failed to get models: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/silver/unstructured/analysis/image")
async def analyze_image(file_id: str, domain: str = None, entity: str = None):
    """Get Silver JSON analysis result for image"""
    database_url = os.getenv("DATABASE_URL", "postgresql://syniqai_user:syniqai_password@localhost:5432/syniqai_metadata")
    
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        import json
        from minio import Minio
        
        conn = psycopg2.connect(database_url)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute(
            """SELECT silver_minio_key, content_tags, summary, ai_confidence_score 
               FROM silver_assets WHERE id = %s""", 
            (file_id,)
        )
        asset = cur.fetchone()
        cur.close()
        conn.close()
        
        if not asset:
            raise HTTPException(status_code=404, detail="Asset not found")
        
        # If Silver JSON exists, fetch it from MinIO
        analysis_result = {
            'detected_objects': [],
            'detections': [],
            'object_detected': False,
            'edge_detected': None,
            'is_grayscale': None,
            'is_corrupted': False,
            'confidence': asset['ai_confidence_score'],
            'summary': asset['summary'] or 'No analysis available'
        }
        
        if asset['silver_minio_key']:
            try:
                # Download Silver JSON from MinIO
                minio_client = Minio(
                    'localhost:9000',
                    access_key='admin',
                    secret_key='password123',
                    secure=False
                )
                response = minio_client.get_object('syniqai-silver', asset['silver_minio_key'])
                silver_json = json.loads(response.read())
                
                # Merge with fetched data
                analysis_result.update(silver_json)
                
                # Parse tags if available
                if asset['content_tags']:
                    analysis_result['detected_objects'] = asset['content_tags'][:5]  # Top 5 tags
                    analysis_result['object_detected'] = len(asset['content_tags']) > 0
                    
            except Exception as e:
                logger.warning(f"Could not fetch Silver JSON: {e}")
        
        return analysis_result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/silver/unstructured/thumbnail/{bucket}/{object_path:path}")
async def get_thumbnail(bucket: str, object_path: str):
    """Get image thumbnail from MinIO bucket"""
    try:
        from minio import Minio
        from fastapi.responses import StreamingResponse
        
        minio_client = Minio(
            'localhost:9000',
            access_key='admin',
            secret_key='password123',
            secure=False
        )
        
        # Get object from MinIO
        response = minio_client.get_object(bucket, object_path)
        
        # Detect content type from extension
        ext = object_path.split('.')[-1].lower()
        content_type_map = {
            'jpg': 'image/jpeg', 'jpeg': 'image/jpeg',
            'png': 'image/png', 'gif': 'image/gif',
            'bmp': 'image/bmp', 'webp': 'image/webp'
        }
        content_type = content_type_map.get(ext, 'application/octet-stream')
        
        return StreamingResponse(response, media_type=content_type)
        
    except Exception as e:
        logger.error(f"Failed to get thumbnail: {e}")
        raise HTTPException(status_code=404, detail=f"Thumbnail not found: {str(e)}")


@app.get("/api/silver/unstructured/preview/audio")
def preview_audio(limit: int = 20, domain: str = None, entity: str = None):
    """Preview audio files from silver assets"""
    database_url = os.getenv("DATABASE_URL", "postgresql://syniqai_user:syniqai_password@localhost:5432/syniqai_metadata")
    
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        conn = psycopg2.connect(database_url)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute(
            """SELECT id, bronze_minio_key, silver_minio_key, content_tags, summary, file_type
               FROM silver_assets 
               WHERE file_type IN ('mp3','wav')
               ORDER BY processed_at DESC
               LIMIT %s""",
            (limit,)
        )
        assets = cur.fetchall()
        cur.close()
        conn.close()
        
        return [dict(a) for a in assets]
    except Exception as e:
        logger.error(f"Failed to preview audio: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/silver/unstructured/analysis/audio")
async def analyze_audio(asset_id: str):
    """Get Silver JSON analysis result for audio"""
    database_url = os.getenv("DATABASE_URL", "postgresql://syniqai_user:syniqai_password@localhost:5432/syniqai_metadata")
    
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        import json
        
        conn = psycopg2.connect(database_url)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("SELECT silver_minio_key FROM silver_assets WHERE id = %s", (asset_id,))
        asset = cur.fetchone()
        cur.close()
        conn.close()
        
        if not asset or not asset['silver_minio_key']:
            raise HTTPException(status_code=404, detail="Silver analysis not found")
        
        # Download Silver JSON from MinIO
        silver_data = storage.storage_manager.get_object("silver", asset['silver_minio_key'])
        return json.loads(silver_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get audio analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/silver/unstructured/rules")
def get_quality_rules():
    """Get distinct quality metric names as rules"""
    database_url = os.getenv("DATABASE_URL", "postgresql://syniqai_user:syniqai_password@localhost:5432/syniqai_metadata")
    
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        conn = psycopg2.connect(database_url)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("SELECT DISTINCT metric_name FROM data_quality_metrics ORDER BY metric_name")
        rules = cur.fetchall()
        cur.close()
        conn.close()
        
        return [{"rule_name": r['metric_name']} for r in rules]
    except Exception as e:
        logger.error(f"Failed to get rules: {e}")
        return []  # Return empty list if table is empty


@app.get("/api/silver/unstructured/quality/datasets")
def get_quality_datasets():
    """Get quality summary grouped by file type"""
    database_url = os.getenv("DATABASE_URL", "postgresql://syniqai_user:syniqai_password@localhost:5432/syniqai_metadata")
    
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        conn = psycopg2.connect(database_url)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute(
            """SELECT file_type, 
                      COUNT(*) as total_count,
                      AVG(ai_confidence_score) as avg_confidence,
                      SUM(CASE WHEN extraction_status = 'success' THEN 1 ELSE 0 END) as success_count,
                      SUM(CASE WHEN extraction_status = 'failed' THEN 1 ELSE 0 END) as failed_count
               FROM silver_assets
               GROUP BY file_type
               ORDER BY total_count DESC"""
        )
        datasets = cur.fetchall()
        cur.close()
        conn.close()
        
        return [dict(d) for d in datasets]
    except Exception as e:
        logger.error(f"Failed to get quality datasets: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/silver/unstructured/tables")
def list_unstructured_tables():
    """List all silver assets (same as /api/silver/assets)"""
    database_url = os.getenv("DATABASE_URL", "postgresql://syniqai_user:syniqai_password@localhost:5432/syniqai_metadata")
    
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        conn = psycopg2.connect(database_url)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute(
            """SELECT id, source, file_type, bronze_minio_key, silver_minio_key,
                      ai_model_used, extraction_status, processed_at, summary
               FROM silver_assets
               ORDER BY processed_at DESC
               LIMIT 100"""
        )
        assets = cur.fetchall()
        cur.close()
        conn.close()
        
        return [dict(a) for a in assets]
    except Exception as e:
        logger.error(f"Failed to list assets: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/quality-summary")
def get_quality_summary():
    """Get overall quality summary from silver_assets"""
    database_url = os.getenv("DATABASE_URL", "postgresql://syniqai_user:syniqai_password@localhost:5432/syniqai_metadata")
    
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        conn = psycopg2.connect(database_url)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute(
            """SELECT 
                 COUNT(*) as total_assets,
                 AVG(ai_confidence_score) as avg_confidence,
                 SUM(CASE WHEN extraction_status = 'failed' THEN 1 ELSE 0 END) as failed_count,
                 SUM(CASE WHEN extraction_status = 'success' THEN 1 ELSE 0 END) as success_count
               FROM silver_assets"""
        )
        summary = cur.fetchone()
        cur.close()
        conn.close()
        
        return dict(summary) if summary else {"total_assets": 0, "avg_confidence": 0, "failed_count": 0, "success_count": 0}
    except Exception as e:
        logger.error(f"Failed to get quality summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/ingestion-status")
def get_ingestion_status():
    """Get ingestion status from pipeline_jobs"""
    database_url = os.getenv("DATABASE_URL", "postgresql://syniqai_user:syniqai_password@localhost:5432/syniqai_metadata")
    
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        from datetime import datetime, timedelta
        
        conn = psycopg2.connect(database_url)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Active jobs
        cur.execute("SELECT COUNT(*) as count FROM pipeline_jobs WHERE status IN ('pending', 'processing')")
        active = cur.fetchone()
        
        # Completed today
        today = datetime.now().date()
        cur.execute(
            "SELECT COUNT(*) as count FROM pipeline_jobs WHERE status = 'completed' AND DATE(completed_at) = %s",
            (today,)
        )
        completed = cur.fetchone()
        
        # Failed today
        cur.execute(
            "SELECT COUNT(*) as count FROM pipeline_jobs WHERE status = 'failed' AND DATE(started_at) = %s",
            (today,)
        )
        failed = cur.fetchone()
        
        cur.close()
        conn.close()
        
        return {
            "active_jobs": active['count'] if active else 0,
            "completed_today": completed['count'] if completed else 0,
            "failed_today": failed['count'] if failed else 0
        }
    except Exception as e:
        logger.error(f"Failed to get ingestion status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend:app", host="0.0.0.0", port=8000, reload=True)
