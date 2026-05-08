"""
CDC to Silver Layer API Routes
REST endpoints for streaming CDC data to Silver layer
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# Will be set by backend.py when initializing
cdc_silver_service = None

def set_cdc_silver_service(service):
    """Set the CDC silver service instance"""
    global cdc_silver_service
    cdc_silver_service = service


class StartCDCSilverRequest(BaseModel):
    topic: Optional[str] = None  # None = process all discovered topics
    auto_discover: bool = True


class StopCDCSilverRequest(BaseModel):
    topic: Optional[str] = None  # None = stop all streams


@router.get("/cdc-silver/topics")
async def discover_cdc_topics():
    """
    Discover available structured CDC topics from Kafka.
    Returns list of topics that can be processed to Silver.
    """
    try:
        if not cdc_silver_service:
            raise HTTPException(status_code=503, detail="CDC Silver service not initialized")
        
        topics = cdc_silver_service.discover_cdc_topics()
        
        # Get table info for each topic
        topics_with_info = []
        for topic in topics:
            table_info = cdc_silver_service.get_table_info_from_topic(topic)
            topics_with_info.append({
                'topic': topic,
                'source': table_info['source'],
                'schema': table_info['schema'],
                'table': table_info['table'],
                'full_name': table_info['full_name']
            })
        
        return {
            "success": True,
            "topics": topics_with_info,
            "total": len(topics_with_info)
        }
        
    except Exception as e:
        logger.error(f"Error discovering CDC topics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cdc-silver/start")
async def start_cdc_to_silver(request: StartCDCSilverRequest):
    """
    Start streaming CDC data to Silver layer.
    
    Args:
        topic: Specific topic to stream (None = all topics)
        auto_discover: Whether to auto-discover topics
    """
    try:
        if not cdc_silver_service:
            raise HTTPException(status_code=503, detail="CDC Silver service not initialized")
        
        job_id = cdc_silver_service.start_cdc_to_silver_stream(topic=request.topic)
        
        if not job_id:
            return {
                "success": False,
                "message": "No CDC topics found to process",
                "hint": "Create a Debezium connector first using setup_cdc_connector.py"
            }
        
        active_streams = cdc_silver_service.get_active_streams()
        
        return {
            "success": True,
            "message": "CDC to Silver streaming started",
            "job_id": job_id,
            "active_streams": active_streams,
            "info": "CDC messages will be processed and stored in MinIO silver bucket"
        }
        
    except Exception as e:
        logger.error(f"Error starting CDC to Silver: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cdc-silver/stop")
async def stop_cdc_to_silver(request: StopCDCSilverRequest):
    """Stop CDC to Silver streaming"""
    try:
        if not cdc_silver_service:
            raise HTTPException(status_code=503, detail="CDC Silver service not initialized")
        
        cdc_silver_service.stop_cdc_streams()
        
        return {
            "success": True,
            "message": "CDC to Silver streaming stopped"
        }
        
    except Exception as e:
        logger.error(f"Error stopping CDC to Silver: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cdc-silver/status")
async def get_cdc_silver_status():
    """Get status of CDC to Silver streams"""
    try:
        if not cdc_silver_service:
            raise HTTPException(status_code=503, detail="CDC Silver service not initialized")
        
        active_streams = cdc_silver_service.get_active_streams()
        
        return {
            "success": True,
            "running": cdc_silver_service.running,
            "active_streams": active_streams,
            "total_streams": len(active_streams)
        }
        
    except Exception as e:
        logger.error(f"Error getting CDC Silver status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/silver/cdc-tables")
async def list_silver_cdc_tables():
    """
    List all tables in Silver layer that came from CDC.
    Reads from MinIO silver bucket.
    """
    try:
        if not cdc_silver_service:
            raise HTTPException(status_code=503, detail="CDC Silver service not initialized")
        
        # List objects in silver bucket
        minio_client = cdc_silver_service.minio
        objects = minio_client.client.list_objects('syniqai-silver', recursive=True)
        
        # Group by source/table
        tables = {}
        for obj in objects:
            # Parse path: source/table/filename.parquet
            parts = obj.object_name.split('/')
            if len(parts) >= 3:
                source = parts[0]
                table = parts[1]
                key = f"{source}.{table}"
                
                if key not in tables:
                    tables[key] = {
                        'source': source,
                        'table': table,
                        'full_name': key,
                        'file_count': 0,
                        'total_size_bytes': 0,
                        'last_modified': obj.last_modified
                    }
                
                tables[key]['file_count'] += 1
                tables[key]['total_size_bytes'] += obj.size
                
                # Update last_modified if newer
                if obj.last_modified > tables[key]['last_modified']:
                    tables[key]['last_modified'] = obj.last_modified
        
        # Convert to list and add formatted size
        table_list = []
        for table_info in tables.values():
            size_mb = table_info['total_size_bytes'] / (1024 * 1024)
            table_info['size_mb'] = round(size_mb, 2)
            table_info['last_modified'] = table_info['last_modified'].isoformat()
            table_list.append(table_info)
        
        # Sort by last_modified (newest first)
        table_list.sort(key=lambda x: x['last_modified'], reverse=True)
        
        return {
            "success": True,
            "tables": table_list,
            "total": len(table_list)
        }
        
    except Exception as e:
        logger.error(f"Error listing Silver CDC tables: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/silver/cdc-preview/{source}/{table}")
async def preview_silver_cdc_table(source: str, table: str, limit: int = 100):
    """
    Preview data from a Silver CDC table.
    Reads most recent file from MinIO.
    
    Args:
        source: Source system (e.g., 'postgres')
        table: Table name
        limit: Number of rows to return
    """
    try:
        if not cdc_silver_service:
            raise HTTPException(status_code=503, detail="CDC Silver service not initialized")
        
        minio_client = cdc_silver_service.minio
        
        # List files for this table
        prefix = f"{source}/{table}/"
        objects = list(minio_client.client.list_objects('syniqai-silver', prefix=prefix))
        
        if not objects:
            return {
                "success": False,
                "message": f"No data found for {source}.{table} in Silver layer"
            }
        
        # Get most recent file
        latest_obj = max(objects, key=lambda x: x.last_modified)
        
        # Read parquet file
        import pandas as pd
        import io
        
        response = minio_client.client.get_object('syniqai-silver', latest_obj.object_name)
        df = pd.read_parquet(io.BytesIO(response.read()))
        
        # Get preview
        preview_df = df.head(limit)
        
        return {
            "success": True,
            "source": source,
            "table": table,
            "total_rows": len(df),
            "preview_rows": len(preview_df),
            "columns": list(df.columns),
            "data": preview_df.to_dict(orient='records'),
            "file": latest_obj.object_name,
            "last_modified": latest_obj.last_modified.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error previewing Silver CDC table: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))
