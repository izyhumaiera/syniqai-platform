"""
Debezium Connector Management Routes
=====================================
REST API endpoints for managing Debezium CDC connectors via Kafka Connect.

Endpoints:
- GET /api/debezium/connectors - List all connectors
- GET /api/debezium/connector/{name}/status - Get connector status
- POST /api/debezium/connector/{name}/restart - Restart connector
- POST /api/debezium/connector/{name}/pause - Pause connector
- POST /api/debezium/connector/{name}/resume - Resume connector
- DELETE /api/debezium/connector/{name} - Delete connector
- POST /api/debezium/connector/postgres/create - Create PostgreSQL connector
- POST /api/debezium/connector/mariadb/create - Create MariaDB connector
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Any, Optional
import logging
import requests
from pathlib import Path
import sys
import json

# Add Kafka Integration path
kafka_integration_path = Path(__file__).parent.parent.parent / "Kafka Integration"
sys.path.append(str(kafka_integration_path))

try:
    from debezium_manager import DebeziumManager, ConnectorConfig
    DEBEZIUM_AVAILABLE = True
except ImportError as e:
    DEBEZIUM_AVAILABLE = False
    print(f" Debezium manager not available: {e}")

logger = logging.getLogger(__name__)

router = APIRouter()

# Kafka Connect configuration
KAFKA_CONNECT_URL = "http://localhost:8083"
KAFKA_BOOTSTRAP_SERVERS = "127.0.0.1:9092"


class ConnectorCreateRequest(BaseModel):
    """Request model for creating a connector"""
    hostname: str
    port: int
    database: str
    user: str = "debezium_user"
    password: str = "debezium_password"
    tables: Optional[List[str]] = None
    snapshot_mode: str = "initial"


def get_debezium_manager() -> DebeziumManager:
    """Get Debezium manager instance"""
    if not DEBEZIUM_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Debezium manager not available. Check if debezium_manager.py exists."
        )
    return DebeziumManager(
        kafka_connect_url=KAFKA_CONNECT_URL,
        kafka_bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS
    )


def check_kafka_connect_health() -> Dict[str, Any]:
    """Check if Kafka Connect is reachable"""
    try:
        response = requests.get(f"{KAFKA_CONNECT_URL}/", timeout=5)
        if response.status_code == 200:
            data = response.json()
            return {
                "available": True,
                "version": data.get("version", "unknown"),
                "commit": data.get("commit", "unknown")
            }
        else:
            return {"available": False, "error": f"HTTP {response.status_code}"}
    except requests.exceptions.RequestException as e:
        return {"available": False, "error": str(e)}


@router.get("/health")
async def get_kafka_connect_health():
    """Check Kafka Connect availability"""
    health = check_kafka_connect_health()
    if not health["available"]:
        raise HTTPException(
            status_code=503,
            detail=f"Kafka Connect not available at {KAFKA_CONNECT_URL}: {health.get('error', 'Unknown error')}"
        )
    return {
        "status": "healthy",
        "kafka_connect_url": KAFKA_CONNECT_URL,
        "version": health.get("version"),
        "commit": health.get("commit")
    }


@router.get("/connectors")
async def list_connectors():
    """List all Debezium connectors"""
    try:
        response = requests.get(f"{KAFKA_CONNECT_URL}/connectors", timeout=10)
        if response.status_code == 200:
            connector_names = response.json()
            
            # Get detailed info for each connector
            connectors = []
            for name in connector_names:
                try:
                    detail_response = requests.get(
                        f"{KAFKA_CONNECT_URL}/connectors/{name}",
                        timeout=5
                    )
                    status_response = requests.get(
                        f"{KAFKA_CONNECT_URL}/connectors/{name}/status",
                        timeout=5
                    )
                    
                    if detail_response.status_code == 200 and status_response.status_code == 200:
                        detail = detail_response.json()
                        status = status_response.json()
                        
                        # Determine connector type from config
                        connector_class = detail.get("config", {}).get("connector.class", "")
                        if "postgresql" in connector_class.lower():
                            conn_type = "PostgreSQL"
                        elif "mysql" in connector_class.lower():
                            conn_type = "MariaDB/MySQL"
                        else:
                            conn_type = "Unknown"
                        
                        connectors.append({
                            "name": name,
                            "type": conn_type,
                            "connector_class": connector_class,
                            "state": status.get("connector", {}).get("state"),
                            "worker_id": status.get("connector", {}).get("worker_id"),
                            "tasks": status.get("tasks", []),
                            "config": detail.get("config", {}),
                            "database": detail.get("config", {}).get("database.hostname", "N/A"),
                            "topic_prefix": detail.get("config", {}).get("topic.prefix", "N/A")
                        })
                except Exception as e:
                    logger.error(f"Error getting details for connector {name}: {e}")
                    connectors.append({
                        "name": name,
                        "type": "Error",
                        "state": "UNKNOWN",
                        "error": str(e)
                    })
            
            return {
                "success": True,
                "count": len(connectors),
                "connectors": connectors
            }
        else:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Failed to list connectors: {response.text}"
            )
    except requests.exceptions.RequestException as e:
        raise HTTPException(
            status_code=503,
            detail=f"Cannot reach Kafka Connect at {KAFKA_CONNECT_URL}: {str(e)}"
        )


@router.get("/connector/{name}/status")
async def get_connector_status(name: str):
    """Get detailed status of a specific connector"""
    try:
        response = requests.get(
            f"{KAFKA_CONNECT_URL}/connectors/{name}/status",
            timeout=10
        )
        if response.status_code == 200:
            return {
                "success": True,
                "connector_name": name,
                "status": response.json()
            }
        elif response.status_code == 404:
            raise HTTPException(status_code=404, detail=f"Connector '{name}' not found")
        else:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Failed to get connector status: {response.text}"
            )
    except requests.exceptions.RequestException as e:
        raise HTTPException(
            status_code=503,
            detail=f"Cannot reach Kafka Connect: {str(e)}"
        )


@router.post("/connector/{name}/restart")
async def restart_connector(name: str):
    """Restart a connector"""
    try:
        response = requests.post(
            f"{KAFKA_CONNECT_URL}/connectors/{name}/restart",
            timeout=10
        )
        if response.status_code in [200, 204]:
            return {
                "success": True,
                "message": f"Connector '{name}' restarted successfully"
            }
        elif response.status_code == 404:
            raise HTTPException(status_code=404, detail=f"Connector '{name}' not found")
        else:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Failed to restart connector: {response.text}"
            )
    except requests.exceptions.RequestException as e:
        raise HTTPException(
            status_code=503,
            detail=f"Cannot reach Kafka Connect: {str(e)}"
        )


@router.post("/connector/{name}/pause")
async def pause_connector(name: str):
    """Pause a connector"""
    try:
        response = requests.put(
            f"{KAFKA_CONNECT_URL}/connectors/{name}/pause",
            timeout=10
        )
        if response.status_code in [200, 202]:
            return {
                "success": True,
                "message": f"Connector '{name}' paused successfully"
            }
        elif response.status_code == 404:
            raise HTTPException(status_code=404, detail=f"Connector '{name}' not found")
        else:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Failed to pause connector: {response.text}"
            )
    except requests.exceptions.RequestException as e:
        raise HTTPException(
            status_code=503,
            detail=f"Cannot reach Kafka Connect: {str(e)}"
        )


@router.post("/connector/{name}/resume")
async def resume_connector(name: str):
    """Resume a paused connector"""
    try:
        response = requests.put(
            f"{KAFKA_CONNECT_URL}/connectors/{name}/resume",
            timeout=10
        )
        if response.status_code in [200, 202]:
            return {
                "success": True,
                "message": f"Connector '{name}' resumed successfully"
            }
        elif response.status_code == 404:
            raise HTTPException(status_code=404, detail=f"Connector '{name}' not found")
        else:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Failed to resume connector: {response.text}"
            )
    except requests.exceptions.RequestException as e:
        raise HTTPException(
            status_code=503,
            detail=f"Cannot reach Kafka Connect: {str(e)}"
        )


@router.delete("/connector/{name}")
async def delete_connector(name: str):
    """Delete a connector"""
    try:
        response = requests.delete(
            f"{KAFKA_CONNECT_URL}/connectors/{name}",
            timeout=10
        )
        if response.status_code in [200, 204]:
            return {
                "success": True,
                "message": f"Connector '{name}' deleted successfully"
            }
        elif response.status_code == 404:
            raise HTTPException(status_code=404, detail=f"Connector '{name}' not found")
        else:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Failed to delete connector: {response.text}"
            )
    except requests.exceptions.RequestException as e:
        raise HTTPException(
            status_code=503,
            detail=f"Cannot reach Kafka Connect: {str(e)}"
        )


@router.post("/connector/postgres/create")
async def create_postgres_connector(request: ConnectorCreateRequest):
    """Create a PostgreSQL Debezium connector"""
    manager = get_debezium_manager()
    
    # Create connector configuration
    config = ConnectorConfig(
        name="postgres-cdc-connector",
        database_type="postgres",
        hostname=request.hostname,
        port=request.port,
        user=request.user,
        password=request.password,
        database_name=request.database,
        server_name="syniq_postgres",
        table_include_list=request.tables or [f"{request.database}.public.*"],
        slot_name="debezium_syniq_slot"
    )
    
    try:
        result = manager.create_postgres_connector(
            config,
            snapshot_mode=request.snapshot_mode,
            plugin_name="pgoutput"
        )
        return {
            "success": True,
            "message": "PostgreSQL connector created successfully",
            "connector": result
        }
    except Exception as e:
        logger.error(f"Failed to create PostgreSQL connector: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create PostgreSQL connector: {str(e)}"
        )


@router.post("/connector/mariadb/create")
async def create_mariadb_connector(request: ConnectorCreateRequest):
    """Create a MariaDB Debezium connector"""
    manager = get_debezium_manager()
    
    # Create connector configuration
    config = ConnectorConfig(
        name="mariadb-cdc-connector",
        database_type="mariadb",
        hostname=request.hostname,
        port=request.port,
        user=request.user,
        password=request.password,
        database_name=request.database,
        server_name="syniq_mariadb",
        table_include_list=request.tables or [f"{request.database}.*"],
        server_id=85472
    )
    
    try:
        result = manager.create_mariadb_connector(
            config,
            snapshot_mode=request.snapshot_mode,
            gtid_mode=True
        )
        return {
            "success": True,
            "message": "MariaDB connector created successfully",
            "connector": result
        }
    except Exception as e:
        logger.error(f"Failed to create MariaDB connector: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create MariaDB connector: {str(e)}"
        )


@router.get("/connector/{name}/topics")
async def get_connector_topics(name: str):
    """Get Kafka topics created by this connector"""
    try:
        # Get connector config to find topic prefix
        response = requests.get(
            f"{KAFKA_CONNECT_URL}/connectors/{name}",
            timeout=10
        )
        if response.status_code == 200:
            config = response.json().get("config", {})
            topic_prefix = config.get("topic.prefix", "")
            
            return {
                "success": True,
                "connector_name": name,
                "topic_prefix": topic_prefix,
                "message": f"Topics will be prefixed with: {topic_prefix}"
            }
        elif response.status_code == 404:
            raise HTTPException(status_code=404, detail=f"Connector '{name}' not found")
        else:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Failed to get connector info: {response.text}"
            )
    except requests.exceptions.RequestException as e:
        raise HTTPException(
            status_code=503,
            detail=f"Cannot reach Kafka Connect: {str(e)}"
        )
