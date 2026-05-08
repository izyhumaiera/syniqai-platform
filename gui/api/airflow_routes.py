"""
Airflow proxy routes — avoids browser CORS issues by forwarding
Airflow REST API calls through the FastAPI backend.

Frontend calls  POST /api/airflow/dags/{dag_id}/dagRuns
Backend proxies POST http://localhost:8082/api/v1/dags/{dag_id}/dagRuns
"""

import os
import logging
from typing import Optional, Any

import httpx
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()

AIRFLOW_BASE = os.getenv("AIRFLOW_BASE_URL", "http://localhost:8082/api/v1")
AIRFLOW_USER = os.getenv("AIRFLOW_USERNAME", "admin")
AIRFLOW_PASS = os.getenv("AIRFLOW_PASSWORD", "admin123")

_AUTH = (AIRFLOW_USER, AIRFLOW_PASS)


def _airflow_url(path: str) -> str:
    return f"{AIRFLOW_BASE}/{path.lstrip('/')}"


def _normalize(obj: Any) -> Any:
    """
    Airflow 2.x returns typed fields as {"__type": "...", "value": "..."}.
    Recursively unwrap them so the frontend receives plain scalars.
    """
    if isinstance(obj, dict):
        if "__type" in obj and "value" in obj:
            return _normalize(obj["value"])
        return {k: _normalize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_normalize(item) for item in obj]
    return obj


async def _get(path: str, params: dict = None):
    url = _airflow_url(path)
    logger.info(f"[Airflow] GET {url} params={params}")
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, auth=_AUTH, params=params)
        logger.info(f"[Airflow] ← {resp.status_code} {url}")
        if resp.status_code != 200:
            logger.error(f"[Airflow] Error body: {resp.text[:500]}")
            raise HTTPException(status_code=resp.status_code,
                                detail=f"Airflow {resp.status_code}: {resp.text[:300]}")
        try:
            return _normalize(resp.json())
        except Exception as json_err:
            logger.error(f"[Airflow] JSON decode failed. Body: {resp.text[:500]}")
            raise HTTPException(status_code=502, detail=f"Airflow returned non-JSON: {resp.text[:200]}")
    except HTTPException:
        raise
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail=f"Cannot connect to Airflow at {AIRFLOW_BASE}. Is it running?")
    except Exception as e:
        logger.exception(f"[Airflow] Unexpected error for GET {url}")
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")


async def _post(path: str, body: Any = None):
    url = _airflow_url(path)
    logger.info(f"[Airflow] POST {url}")
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(url, auth=_AUTH, json=body or {})
        logger.info(f"[Airflow] ← {resp.status_code} {url}")
        if resp.status_code not in (200, 200):
            if not (200 <= resp.status_code < 300):
                logger.error(f"[Airflow] Error body: {resp.text[:500]}")
                raise HTTPException(status_code=resp.status_code,
                                    detail=f"Airflow {resp.status_code}: {resp.text[:300]}")
        try:
            return _normalize(resp.json())
        except Exception:
            logger.error(f"[Airflow] JSON decode failed. Body: {resp.text[:500]}")
            raise HTTPException(status_code=502, detail=f"Airflow returned non-JSON: {resp.text[:200]}")
    except HTTPException:
        raise
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail=f"Cannot connect to Airflow at {AIRFLOW_BASE}. Is it running?")
    except Exception as e:
        logger.exception(f"[Airflow] Unexpected error for POST {url}")
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")


async def _patch(path: str, body: Any = None):
    url = _airflow_url(path)
    logger.info(f"[Airflow] PATCH {url}")
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.patch(url, auth=_AUTH, json=body or {})
        logger.info(f"[Airflow] ← {resp.status_code} {url}")
        if not (200 <= resp.status_code < 300):
            logger.error(f"[Airflow] Error body: {resp.text[:500]}")
            raise HTTPException(status_code=resp.status_code,
                                detail=f"Airflow {resp.status_code}: {resp.text[:300]}")
        try:
            return _normalize(resp.json())
        except Exception:
            logger.error(f"[Airflow] JSON decode failed. Body: {resp.text[:500]}")
            raise HTTPException(status_code=502, detail=f"Airflow returned non-JSON: {resp.text[:200]}")
    except HTTPException:
        raise
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail=f"Cannot connect to Airflow at {AIRFLOW_BASE}. Is it running?")
    except Exception as e:
        logger.exception(f"[Airflow] Unexpected error for PATCH {url}")
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")


# ── DAG Status ────────────────────────────────────────────────────────────────

@router.get("/dags/{dag_id}")
async def get_dag(dag_id: str):
    """Get DAG metadata / status."""
    return await _get(f"dags/{dag_id}")


# ── DAG Runs ──────────────────────────────────────────────────────────────────

@router.get("/dags/{dag_id}/dagRuns")
async def get_dag_runs(dag_id: str, limit: int = Query(default=10, ge=1, le=100)):
    """List recent DAG runs."""
    return await _get(f"dags/{dag_id}/dagRuns", params={"limit": limit})


class TriggerPayload(BaseModel):
    conf: Optional[dict] = None


@router.post("/dags/{dag_id}/dagRuns")
async def trigger_dag(dag_id: str, payload: TriggerPayload = None):
    """Trigger a new DAG run."""
    body = {}
    if payload and payload.conf:
        body["conf"] = payload.conf
    return await _post(f"dags/{dag_id}/dagRuns", body)


# ── Pause / Unpause ───────────────────────────────────────────────────────────

class PatchDagPayload(BaseModel):
    is_paused: bool


@router.patch("/dags/{dag_id}")
async def patch_dag(dag_id: str, payload: PatchDagPayload):
    """Pause or unpause a DAG."""
    return await _patch(f"dags/{dag_id}", {"is_paused": payload.is_paused})
