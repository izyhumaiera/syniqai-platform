"""
SQLite-persisted Job Tracker for Silver Processing.
Jobs survive backend restarts; completed jobs are cleaned up after TTL.
"""

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional
import threading
import time
import logging

logger = logging.getLogger(__name__)

_DB_PATH = Path(__file__).parent / "silver_jobs.db"


class SilverJobTracker:
    """
    SQLite-backed job tracker — jobs persist across backend restarts.
    Completed/failed jobs are removed after the TTL.
    """

    def __init__(self, ttl_hours: int = 24, db_path: Path = _DB_PATH):
        self.ttl_hours = ttl_hours
        self.db_path = str(db_path)
        self.lock = threading.Lock()
        self._init_db()
        self._start_cleanup_thread()
        logger.info(f"Initialized SilverJobTracker with TTL={ttl_hours}h")

    # ------------------------------------------------------------------ DB
    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS silver_jobs (
                    job_id      TEXT PRIMARY KEY,
                    data        TEXT NOT NULL,
                    started_at  TEXT NOT NULL,
                    status      TEXT NOT NULL
                )
            """)
            conn.commit()

    def _save(self, job: Dict):
        """Upsert one job row (called inside self.lock)."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO silver_jobs (job_id, data, started_at, status) "
                "VALUES (?, ?, ?, ?)",
                (job["job_id"], json.dumps(job),
                 job.get("started_at", datetime.now().isoformat()),
                 job.get("status", "pending"))
            )
            conn.commit()

    def _load_all(self) -> Dict[str, Dict]:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("SELECT data FROM silver_jobs").fetchall()
        return {r["job_id"]: r for r in (json.loads(row[0]) for row in rows)}
    
    # ------------------------------------------------------------ public API
    def create_job(self, table_name: str, source: str,
                   entity: str, bronze_path: str = None) -> str:
        import uuid
        job_id = f"job_{uuid.uuid4().hex[:12]}"
        job = {
            "job_id": job_id,
            "job_type": "silver_processing",
            "table_name": table_name,
            "source": source,
            "entity": entity,
            "bronze_path": bronze_path,
            "status": "pending",
            "progress": 0,
            "message": "Job queued",
            "started_at": datetime.now().isoformat(),
            "completed_at": None,
            "error_message": None,
            "silver_path": None,
            "row_count": None,
            "quality_score": None,
            "cleaning_summary": None,
        }
        with self.lock:
            self._save(job)
        logger.info(f"Created job {job_id} for {table_name}")
        return job_id
    
    def update_status(self, job_id: str, status: str, message: str = None,
                      progress: int = None, error_message: str = None):
        with self.lock:
            job = self._get_one(job_id)
            if job is None:
                logger.warning(f"Job {job_id} not found")
                return
            job["status"] = status
            if message:
                job["message"] = message
            if progress is not None:
                job["progress"] = progress
            if error_message:
                job["error_message"] = error_message
            if status in ("completed", "failed"):
                job["completed_at"] = datetime.now().isoformat()
            self._save(job)
            logger.info(f"Job {job_id}: {status} - {message}")
    
    def update_results(self, job_id: str, status: str = None,
                       silver_path: str = None, row_count: int = None,
                       quality_score: float = None, cleaning_summary: Dict = None,
                       message: str = None, error_message: str = None):
        with self.lock:
            job = self._get_one(job_id)
            if job is None:
                return
            if status:
                job["status"] = status
                if status in ("completed", "failed"):
                    job["completed_at"] = datetime.now().isoformat()
            if message:
                job["message"] = message
            if error_message:
                job["error_message"] = error_message
            if silver_path:
                job["silver_path"] = silver_path
            if row_count is not None:
                job["row_count"] = row_count
            if quality_score is not None:
                job["quality_score"] = quality_score
            if cleaning_summary:
                job["cleaning_summary"] = cleaning_summary
            self._save(job)
    
    def get_job(self, job_id: str) -> Optional[Dict]:
        with self.lock:
            return self._get_one(job_id)

    def _get_one(self, job_id: str) -> Optional[Dict]:
        """Fetch a single job from DB (call inside self.lock)."""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT data FROM silver_jobs WHERE job_id = ?", (job_id,)
            ).fetchone()
        return json.loads(row[0]) if row else None

    def list_jobs(self, limit: int = 50, status: str = None) -> list:
        with sqlite3.connect(self.db_path) as conn:
            if status:
                rows = conn.execute(
                    "SELECT data FROM silver_jobs WHERE status = ? "
                    "ORDER BY started_at DESC LIMIT ?",
                    (status, limit)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT data FROM silver_jobs ORDER BY started_at DESC LIMIT ?",
                    (limit,)
                ).fetchall()
        return [json.loads(r[0]) for r in rows]
    
    def _cleanup_old_jobs(self):
        """Remove jobs older than TTL from SQLite."""
        cutoff = (datetime.now() - timedelta(hours=self.ttl_hours)).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            result = conn.execute(
                "DELETE FROM silver_jobs "
                "WHERE status IN ('completed','failed') AND started_at < ?",
                (cutoff,)
            )
            conn.commit()
            removed = result.rowcount
        if removed:
            logger.info(f"Cleaned up {removed} old silver jobs")
    
    def _start_cleanup_thread(self):
        """Start background thread for periodic cleanup"""
        def cleanup_loop():
            while True:
                time.sleep(3600)  # Run every hour
                try:
                    self._cleanup_old_jobs()
                except Exception as e:
                    logger.error(f"Error in cleanup thread: {e}")
        
        thread = threading.Thread(target=cleanup_loop, daemon=True)
        thread.start()
        logger.info("Started cleanup thread")


# Global job tracker instance
job_tracker = SilverJobTracker(ttl_hours=24)
