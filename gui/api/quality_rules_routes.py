"""
Quality Rules API Routes
Provides endpoints for data quality rule management, execution, and monitoring
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
import uuid

from database import rules_repo, quarantine_repo, execution_log_repo
from quality_check_executor import QualityCheckExecutor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/quality-rules", tags=["quality-rules"])

# Initialize executor
quality_executor = QualityCheckExecutor()


# Pydantic Models
class QualityRule(BaseModel):
    rule_name: str
    domain: str
    category: str  # validation, transformation, masking, referential_integrity, anomaly_detection, compliance, data_quality, schema_validation
    rule_type: str  # not_null, range_check, regex_format, enum_validation, unique, foreign_key, cross_column_logic, sql_expression, data_type_check, anomaly_detection, masking_rule
    description: Optional[str] = None
    target_table: str
    target_columns: List[str] = []  # Array of column names
    condition_expression: str
    severity: str  # CRITICAL, HIGH, WARNING, INFO (uppercase)
    action: str  # quarantine_row, log, block_table
    execution_priority: int = 5  # 1-10 (lower = higher priority)
    created_by: str = "system"


class RuleUpdate(BaseModel):
    rule_name: Optional[str] = None
    description: Optional[str] = None
    condition_expression: Optional[str] = None
    severity: Optional[str] = None
    action: Optional[str] = None
    status: Optional[str] = None
    is_active: Optional[bool] = None


class ExecuteQualityCheckRequest(BaseModel):
    table_name: str
    domain: str = "finance"
    source: str = "postgres"
    limit: Optional[int] = None


# ========== GET ROUTES ==========

@router.get("/tables/{table_name}")
async def get_rules_for_table(table_name: str, domain: str = "finance"):
    """
    Get all active quality rules for a specific table
    """
    try:
        rules = rules_repo.get_rules_by_table(domain, table_name)
        
        return {
            "success": True,
            "table_name": table_name,
            "domain": domain,
            "rule_count": len(rules),
            "rules": rules
        }
    except Exception as e:
        logger.error(f"Error fetching rules for {table_name}: {e}")
        return {
            "success": False,
            "error": str(e),
            "rules": []
        }


@router.get("/tables/{table_name}/execution-history")
async def get_execution_history(table_name: str, domain: str = "finance", limit: int = 10):
    """
    Get quality check execution history for a table
    """
    try:
        logger.info(f"Fetching execution history for table={table_name}, domain={domain}")
        
        # Get execution history directly from the table
        history = execution_log_repo.get_execution_history_by_table(domain, table_name, limit)
        
        logger.info(f"✓ Found {len(history)} execution records for {table_name}")
        if history:
            logger.info(f"Sample record: {history[0]}")
        
        return {
            "success": True,
            "table_name": table_name,
            "domain": domain,
            "history_count": len(history),
            "history": history
        }
    except Exception as e:
        logger.error(f"Error fetching execution history: {e}")
        return {
            "success": False,
            "error": str(e),
            "history": []
        }


@router.get("/tables/{table_name}/quarantine")
async def get_quarantine_records(
    table_name: str,
    domain: str = "finance",
    status: str = "pending",
    limit: int = 100
):
    """
    Get quarantine records for a table
    """
    try:
        records = quarantine_repo.get_quarantine_records(domain, status, limit)
        
        # Filter by table_name
        filtered_records = [r for r in records if r.get('source_table') == table_name]
        
        return {
            "success": True,
            "table_name": table_name,
            "domain": domain,
            "status": status,
            "record_count": len(filtered_records),
            "records": filtered_records
        }
    except Exception as e:
        logger.error(f"Error fetching quarantine records: {e}")
        return {
            "success": False,
            "error": str(e),
            "records": []
        }


@router.get("/quarantine/summary")
async def get_quarantine_summary(domain: str = "finance"):
    """
    Get quarantine summary statistics for a domain
    """
    try:
        summary = quarantine_repo.get_quarantine_summary(domain)
        
        return {
            "success": True,
            "domain": domain,
            "summary": summary
        }
    except Exception as e:
        logger.error(f"Error fetching quarantine summary: {e}")
        return {
            "success": False,
            "error": str(e),
            "summary": {}
        }


# ========== POST ROUTES ==========

@router.post("/tables/{table_name}/execute")
async def execute_quality_check(
    table_name: str,
    request: ExecuteQualityCheckRequest,
    background_tasks: BackgroundTasks
):
    """
    Execute quality checks on a table
    Returns execution results and creates quarantine records for failures
    """
    try:
        logger.info(f"Executing quality check on {table_name}")
        
        # Get rules for this table
        all_rules = rules_repo.get_rules_by_table(request.domain, table_name)
        
        # Filter only active rules for execution
        rules = [rule for rule in all_rules if rule.get('is_active', False)]
        
        if not rules:
            return {
                "success": False,
                "error": f"No active rules found for {table_name}",
                "execution_id": None
            }
        
        # Execute quality checks (synchronous for now, can be async later)
        execution_id = str(uuid.uuid4())
        results = await quality_executor.execute_checks(
            table_name=table_name,
            domain=request.domain,
            source=request.source,
            rules=rules,
            limit=request.limit,
            execution_id=execution_id
        )
        
        return {
            "success": True,
            "execution_id": execution_id,
            "table_name": table_name,
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Error executing quality check: {e}")
        return {
            "success": False,
            "error": str(e),
            "execution_id": None
        }


@router.post("/rules")
async def create_rule(rule: QualityRule):
    """
    Create a new quality rule
    """
    try:
        rule_data = rule.dict()
        rule_id = rules_repo.create_rule(rule_data)
        
        return {
            "success": True,
            "rule_id": rule_id,
            "message": f"Rule '{rule.rule_name}' created successfully"
        }
    except Exception as e:
        logger.error(f"Error creating rule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/rules/{rule_id}")
async def update_rule(rule_id: str, updates: RuleUpdate):
    """
    Update an existing rule
    """
    try:
        update_dict = {k: v for k, v in updates.dict().items() if v is not None}
        
        if not update_dict:
            raise HTTPException(status_code=400, detail="No updates provided")
        
        success = rules_repo.update_rule(rule_id, update_dict)
        
        return {
            "success": success,
            "rule_id": rule_id,
            "message": "Rule updated successfully"
        }
    except Exception as e:
        logger.error(f"Error updating rule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/rules/{rule_id}")
async def delete_rule(rule_id: str):
    """
    Soft delete a rule (archives it)
    """
    try:
        success = rules_repo.delete_rule(rule_id)
        
        return {
            "success": success,
            "rule_id": rule_id,
            "message": "Rule archived successfully"
        }
    except Exception as e:
        logger.error(f"Error deleting rule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/quarantine/{quarantine_id}/resolve")
async def resolve_quarantine(
    quarantine_id: str,
    resolution: str,
    resolved_by: str = "system"
):
    """
    Mark a quarantine record as resolved
    """
    try:
        success = quarantine_repo.resolve_quarantine(
            quarantine_id,
            resolution,
            resolved_by
        )
        
        return {
            "success": success,
            "quarantine_id": quarantine_id,
            "message": "Quarantine record resolved"
        }
    except Exception as e:
        logger.error(f"Error resolving quarantine: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/quarantine/download/{execution_id}")
async def download_quarantine_data(
    execution_id: str,
    domain: str = "finance",
    source: str = "postgres",
    table_name: str = None
):
    """
    Download quarantined records as CSV from MinIO
    """
    try:
        from minio_utils import MinIOClient
        import io
        import pandas as pd
        from fastapi.responses import StreamingResponse
        
        minio_client = MinIOClient()
        quarantine_bucket = "syniqai-quarantine"
        
        # List all files in the execution path
        prefix = f"{domain}/{source}/{table_name}/{execution_id}" if table_name else f"{domain}/{source}"
        
        logger.info(f"Downloading quarantine data from: {quarantine_bucket}/{prefix}")
        
        objects = minio_client.client.list_objects(quarantine_bucket, prefix=prefix, recursive=True)
        
        all_data = []
        for obj in objects:
            if obj.object_name.endswith('.parquet'):
                # Download parquet file
                response = minio_client.client.get_object(quarantine_bucket, obj.object_name)
                data = response.read()
                
                # Read parquet and append to list
                df = pd.read_parquet(io.BytesIO(data))
                df['quarantine_file'] = obj.object_name
                all_data.append(df)
        
        if not all_data:
            return {
                "success": False,
                "error": "No quarantine data found"
            }
        
        # Combine all dataframes
        combined_df = pd.concat(all_data, ignore_index=True)
        
        # Convert to CSV
        csv_buffer = io.StringIO()
        combined_df.to_csv(csv_buffer, index=False)
        csv_buffer.seek(0)
        
        return StreamingResponse(
            iter([csv_buffer.getvalue()]),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=quarantine_{execution_id}.csv"
            }
        )
        
    except Exception as e:
        logger.error(f"Error downloading quarantine data: {e}")
        return {
            "success": False,
            "error": str(e)
        }
