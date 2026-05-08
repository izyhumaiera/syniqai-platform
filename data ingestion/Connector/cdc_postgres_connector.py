"""
cdc_postgres_connector.py
=========================
PostgreSQL Change-Data-Capture (CDC) connector using WAL logical replication.

HOW IT WORKS:
  PostgreSQL WAL (Write-Ahead Log) at wal_level=logical allows Python to
  subscribe to a replication slot and receive every INSERT / UPDATE / DELETE
  in real time — NO polling, NO extra queries.

  This connector uses:
    - psycopg2 LogicalReplicationConnection  (already in your requirements)
    - pgoutput protocol plugin               (built into PostgreSQL ≥ 10)
    - Publication created by debezium_manager prerequisites SQL

  Credentials are read from:
    data ingestion/Connector/config.json  (same file the bulk pipeline uses)
  — nothing is duplicated, nothing is hardcoded.

RELATIONSHIP TO EXISTING PIPELINE:
  ✅  Does NOT modify postgres_connector.py — bulk extraction is untouched.
  ✅  Does NOT modify direct_ingestor.py    — MinIO writes are additive.
  ✅  Reads the SAME config.json            — single source of truth.
  ✅  Produces the SAME event dict format   — {"data": DataFrame, "metadata": {}}
      so it can be fed straight into DirectStreamIngestor or KafkaBridge.

DATABASE PREREQUISITES (run once, already shown in debezium_manager):
  ALTER SYSTEM SET wal_level = logical;  -- restart DB after this
  CREATE PUBLICATION syiniq_pub FOR ALL TABLES;
  SELECT pg_create_logical_replication_slot('syiniq_cdc_slot', 'pgoutput');

Usage:
    from cdc_postgres_connector import CDCPostgresConnector

    cdc = CDCPostgresConnector()          # loads config.json automatically
    cdc.start(callback=my_function)       # my_function(event) called per change

    # Or iterate manually:
    for event in cdc.stream():
        print(event["operation"], event["table"], event["data"])
"""

from __future__ import annotations

import json
import logging
import struct
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Generator, List, Optional

import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths — same root resolution as kafka_bridge.py / debezium_manager.py
# ---------------------------------------------------------------------------
_THIS_DIR      = Path(__file__).resolve().parent          # .../data ingestion/Connector
_CONNECTOR_DIR = _THIS_DIR                                # same directory
_CONFIG_FILE   = _CONNECTOR_DIR / "config.json"

# Publication and slot names (must match debezium_manager prerequisites SQL)
_PUBLICATION_NAME = "syiniq_pub"
_SLOT_NAME        = "syiniq_cdc_slot"


# ===========================================================================
# pgoutput binary protocol decoder
# ===========================================================================

class _PgOutputDecoder:
    """
    Decodes pgoutput logical-replication messages into plain Python dicts.

    pgoutput message types we handle:
      B  = Begin transaction
      C  = Commit transaction
      R  = Relation (table schema — caches column names)
      I  = Insert
      U  = Update
      D  = Delete
    """

    def __init__(self) -> None:
        # relation_id → {"table": str, "schema": str, "columns": [str,...]}
        self._relations: Dict[int, Dict[str, Any]] = {}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _read_int8(data: bytes, pos: int) -> tuple[int, int]:
        return data[pos], pos + 1

    @staticmethod
    def _read_int16(data: bytes, pos: int) -> tuple[int, int]:
        return struct.unpack_from(">h", data, pos)[0], pos + 2

    @staticmethod
    def _read_int32(data: bytes, pos: int) -> tuple[int, int]:
        return struct.unpack_from(">i", data, pos)[0], pos + 4

    @staticmethod
    def _read_int64(data: bytes, pos: int) -> tuple[int, int]:
        return struct.unpack_from(">q", data, pos)[0], pos + 8

    @staticmethod
    def _read_cstring(data: bytes, pos: int) -> tuple[str, int]:
        end = data.index(b"\x00", pos)
        return data[pos:end].decode("utf-8", errors="replace"), end + 1

    # ------------------------------------------------------------------
    # Relation message (R)  — caches table schema
    # ------------------------------------------------------------------

    def _decode_relation(self, data: bytes, pos: int) -> None:
        rel_id, pos  = self._read_int32(data, pos)
        schema,  pos = self._read_cstring(data, pos)
        table,   pos = self._read_cstring(data, pos)
        _replica_id  = data[pos]; pos += 1
        num_cols, pos = self._read_int16(data, pos)

        columns: List[str] = []
        for _ in range(num_cols):
            _flags   = data[pos]; pos += 1
            col_name, pos = self._read_cstring(data, pos)
            _type_id, pos = self._read_int32(data, pos)
            _atttypmod, pos = self._read_int32(data, pos)
            columns.append(col_name)

        self._relations[rel_id] = {
            "schema":  schema,
            "table":   table,
            "columns": columns,
        }
        logger.debug(f"CDCPostgres: cached relation {schema}.{table} id={rel_id}")

    # ------------------------------------------------------------------
    # Tuple decoder (shared by Insert / Update / Delete)
    # ------------------------------------------------------------------

    def _decode_tuple(self, data: bytes, pos: int, columns: List[str]) -> tuple[Dict, int]:
        num_cols, pos = self._read_int16(data, pos)
        row: Dict[str, Any] = {}

        for i in range(num_cols):
            col_name = columns[i] if i < len(columns) else f"col_{i}"
            col_type = chr(data[pos]); pos += 1

            if col_type == "n":           # NULL
                row[col_name] = None
            elif col_type == "u":         # unchanged TOAST value
                row[col_name] = "__unchanged__"
            elif col_type == "t":         # text representation
                col_len, pos = self._read_int32(data, pos)
                raw = data[pos: pos + col_len]; pos += col_len
                raw_str = raw.decode("utf-8", errors="replace")
                # Try to parse JSON strings back to dict/list
                if raw_str and raw_str[0] in ("{", "["):
                    try:
                        row[col_name] = json.loads(raw_str)
                    except json.JSONDecodeError:
                        row[col_name] = raw_str
                else:
                    row[col_name] = raw_str
            else:
                # Binary type — store as hex string
                col_len, pos = self._read_int32(data, pos)
                row[col_name] = data[pos: pos + col_len].hex(); pos += col_len

        return row, pos

    # ------------------------------------------------------------------
    # Public decode entry-point
    # ------------------------------------------------------------------

    def decode(self, payload: bytes) -> Optional[Dict[str, Any]]:
        """
        Decode a single pgoutput message.

        Returns a dict:
            {
                "operation": "INSERT" | "UPDATE" | "DELETE" | "BEGIN" | "COMMIT",
                "schema":    str,
                "table":     str,
                "data":      dict  (new row for INSERT/UPDATE, old row for DELETE),
                "old_data":  dict  (previous row, UPDATE only)
            }

        Returns None for Begin/Commit or unknown messages.
        """
        if not payload:
            return None

        msg_type = chr(payload[0])
        pos = 1

        # ---- Relation (schema cache) ----
        if msg_type == "R":
            self._decode_relation(payload, pos)
            return None

        # ---- Begin ----
        if msg_type == "B":
            return {"operation": "BEGIN", "schema": "", "table": "", "data": {}}

        # ---- Commit ----
        if msg_type == "C":
            return {"operation": "COMMIT", "schema": "", "table": "", "data": {}}

        # ---- Insert ----
        if msg_type == "I":
            rel_id, pos = self._read_int32(payload, pos)
            rel = self._relations.get(rel_id)
            if not rel:
                logger.warning(f"CDCPostgres: Unknown relation id {rel_id} for INSERT")
                return None
            _tag = payload[pos]; pos += 1   # 'N' = new tuple
            row, _ = self._decode_tuple(payload, pos, rel["columns"])
            return {
                "operation": "INSERT",
                "schema":     rel["schema"],
                "table":      rel["table"],
                "data":       row,
                "old_data":   {},
            }

        # ---- Update ----
        if msg_type == "U":
            rel_id, pos = self._read_int32(payload, pos)
            rel = self._relations.get(rel_id)
            if not rel:
                logger.warning(f"CDCPostgres: Unknown relation id {rel_id} for UPDATE")
                return None
            old_row: Dict[str, Any] = {}
            tag = chr(payload[pos]); pos += 1
            if tag in ("O", "K"):           # old / key tuple present
                old_row, pos = self._decode_tuple(payload, pos, rel["columns"])
                _tag = payload[pos]; pos += 1  # consume the 'N' (new) tag
            row, _ = self._decode_tuple(payload, pos, rel["columns"])
            return {
                "operation": "UPDATE",
                "schema":     rel["schema"],
                "table":      rel["table"],
                "data":       row,
                "old_data":   old_row,
            }

        # ---- Delete ----
        if msg_type == "D":
            rel_id, pos = self._read_int32(payload, pos)
            rel = self._relations.get(rel_id)
            if not rel:
                logger.warning(f"CDCPostgres: Unknown relation id {rel_id} for DELETE")
                return None
            _tag = payload[pos]; pos += 1   # 'O' or 'K'
            row, _ = self._decode_tuple(payload, pos, rel["columns"])
            return {
                "operation": "DELETE",
                "schema":     rel["schema"],
                "table":      rel["table"],
                "data":       row,
                "old_data":   {},
            }

        return None


# ===========================================================================
# CDCPostgresConnector
# ===========================================================================

class CDCPostgresConnector:
    """
    PostgreSQL CDC connector — subscribes to WAL logical replication and
    streams every INSERT / UPDATE / DELETE as a Python event dict.

    Credentials are loaded from  data ingestion/Connector/config.json
    — the same file used by the bulk PostgresConnector — nothing hardcoded.

    Event format yielded / passed to callback:
    {
        "operation":   "INSERT" | "UPDATE" | "DELETE",
        "schema":      str,
        "table":       str,
        "data":        dict,        ← new row values
        "old_data":    dict,        ← previous values (UPDATE/DELETE only)
        "source_type": "postgres",
        "lsn":         str,         ← Log Sequence Number (WAL position)
        "captured_at": str,         ← ISO-8601 UTC timestamp
    }
    """

    source_type = "postgres"

    def __init__(
        self,
        config_path: Optional[str] = None,
        publication: str  = _PUBLICATION_NAME,
        slot_name:   str  = _SLOT_NAME,
    ) -> None:
        self._config_path  = Path(config_path) if config_path else _CONFIG_FILE
        self._publication  = publication
        self._slot_name    = slot_name
        self._conn         = None
        self._cur          = None
        self._decoder      = _PgOutputDecoder()
        self._running      = False
        self._thread: Optional[threading.Thread] = None
        self._cfg: Dict[str, Any] = {}
        self._load_config()

    # ------------------------------------------------------------------
    # Config loader — reads same config.json as bulk pipeline
    # ------------------------------------------------------------------

    def _load_config(self) -> None:
        if not self._config_path.exists():
            raise FileNotFoundError(
                f"CDCPostgresConnector: config not found at {self._config_path}\n"
                f"Expected: data ingestion/Connector/config.json"
            )
        with self._config_path.open("r", encoding="utf-8") as f:
            raw = json.load(f)

        self._cfg = raw.get("connection_config", raw)
        logger.info(
            f"CDCPostgresConnector: loaded config — "
            f"{self._cfg.get('host')}:{self._cfg.get('port')}/"
            f"{self._cfg.get('database')}"
        )

    def reload_config(self) -> None:
        """Hot-reload credentials without restarting the stream."""
        self._load_config()
        logger.info("CDCPostgresConnector: config reloaded")

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------

    def _connect(self) -> None:
        try:
            import psycopg2
            from psycopg2.extras import LogicalReplicationConnection
        except ImportError:
            raise ImportError(
                "psycopg2 is required: pip install psycopg2-binary"
            )

        c = self._cfg
        self._conn = psycopg2.connect(
            host     = c["host"],
            port     = int(c.get("port", 5432)),
            database = c["database"],
            user     = c["user"],
            password = c["password"],
            connection_factory = LogicalReplicationConnection,
            connect_timeout    = int(c.get("connect_timeout", 10)),
        )
        self._cur = self._conn.cursor()
        logger.info(
            f"CDCPostgresConnector: replication connection established → "
            f"{c['host']}:{c.get('port', 5432)}/{c['database']}"
        )

    def _ensure_slot(self) -> None:
        """Create the replication slot if it doesn't exist yet."""
        try:
            self._cur.create_replication_slot(
                self._slot_name,
                output_plugin="pgoutput",
            )
            logger.info(f"CDCPostgresConnector: created slot '{self._slot_name}'")
        except Exception as exc:
            # Slot already exists — that's fine
            if "already exists" in str(exc).lower():
                logger.info(f"CDCPostgresConnector: slot '{self._slot_name}' already exists")
            else:
                raise

    def connect(self) -> None:
        """Establish the replication connection and ensure slot + publication exist."""
        self._connect()
        self._ensure_slot()

    def close(self) -> None:
        """Stop streaming and close connection."""
        self._running = False
        try:
            if self._cur:
                self._cur.close()
            if self._conn:
                self._conn.close()
        except Exception:
            pass
        logger.info("CDCPostgresConnector: connection closed")

    # ------------------------------------------------------------------
    # Stream — yields CDC events
    # ------------------------------------------------------------------

    def stream(self) -> Generator[Dict[str, Any], None, None]:
        """
        Generator that yields CDC event dicts.

        Call connect() first, or use start() for background operation.

        Example:
            cdc = CDCPostgresConnector()
            cdc.connect()
            for event in cdc.stream():
                print(event)
        """
        self._running = True

        self._cur.start_replication(
            slot_name    = self._slot_name,
            decode       = False,           # we decode binary ourselves
            options      = {
                "publication_names": self._publication,
                "proto_version":     "1",
            },
        )

        logger.info(
            f"CDCPostgresConnector: streaming WAL changes — "
            f"slot='{self._slot_name}', publication='{self._publication}'"
        )

        LSN_EPOCH = datetime(2000, 1, 1, tzinfo=timezone.utc).timestamp()

        while self._running:
            msg = self._cur.read_message()
            if msg is None:
                # No message — send keepalive and wait
                self._cur.send_feedback()
                time.sleep(0.1)
                continue

            decoded = self._decoder.decode(msg.payload)
            if decoded is None or decoded["operation"] in ("BEGIN", "COMMIT"):
                self._cur.send_feedback(flush_lsn=msg.data_start)
                continue

            # Enrich with pipeline metadata
            ts_usec = struct.unpack_from(">q", msg.payload, 1)[0] if len(msg.payload) > 8 else 0
            event_ts = datetime.fromtimestamp(
                LSN_EPOCH + ts_usec / 1_000_000, tz=timezone.utc
            ).isoformat() if ts_usec else datetime.now(timezone.utc).isoformat()

            decoded["source_type"] = self.source_type
            decoded["lsn"]         = str(msg.data_start)
            decoded["captured_at"] = datetime.now(timezone.utc).isoformat()

            # Acknowledge receipt
            self._cur.send_feedback(flush_lsn=msg.data_start)

            yield decoded

    # ------------------------------------------------------------------
    # as_pipeline_payload — converts event to the standard pipeline format
    # ------------------------------------------------------------------

    @staticmethod
    def to_pipeline_payload(event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert a CDC event into the same payload format used by bulk
        postgres_connector.py  →  {"data": DataFrame, "metadata": dict}

        This means the event can be fed directly into:
          - DirectStreamIngestor.ingest_streaming()
          - KafkaBridge.publish_dataframe()
        """
        row = {**event["data"]}
        row["_cdc_operation"] = event["operation"]
        row["_cdc_captured_at"] = event["captured_at"]
        row["_cdc_lsn"] = event.get("lsn", "")
        if event.get("old_data"):
            row["_cdc_old_data"] = json.dumps(event["old_data"])

        df = pd.DataFrame([row])

        return {
            "data": df,
            "metadata": {
                "source_type":  "postgres",
                "entity":       event["table"],
                "schema":       event.get("schema", "public"),
                "operation":    event["operation"],
                "cdc_mode":     True,
                "row_count":    1,
                "chunk_index":  0,
                "lsn":          event.get("lsn", ""),
                "captured_at":  event["captured_at"],
                "extracted_at": datetime.now(timezone.utc).isoformat(),
            },
        }

    # ------------------------------------------------------------------
    # start / stop — background thread mode
    # ------------------------------------------------------------------

    def start(
        self,
        callback: Callable[[Dict[str, Any]], None],
        on_error: Optional[Callable[[Exception], None]] = None,
        retry_delay: int = 5,
    ) -> threading.Thread:
        """
        Start CDC streaming in a background thread.

        Args:
            callback:    Called with each CDC event dict.
            on_error:    Optional — called on exception (for alerting/logging).
            retry_delay: Seconds to wait before reconnecting on failure.

        Returns:
            The background Thread object.

        Example:
            def handle(event):
                print(event["operation"], event["table"])

            cdc = CDCPostgresConnector()
            t = cdc.start(callback=handle)
        """
        def _run() -> None:
            while self._running:
                try:
                    self.connect()
                    for event in self.stream():
                        if not self._running:
                            break
                        try:
                            callback(event)
                        except Exception as cb_exc:
                            logger.error(f"CDCPostgresConnector: callback error — {cb_exc}")
                    self.close()
                except Exception as exc:
                    logger.error(f"CDCPostgresConnector: stream error — {exc}. Retrying in {retry_delay}s")
                    if on_error:
                        try:
                            on_error(exc)
                        except Exception:
                            pass
                    self.close()
                    if self._running:
                        time.sleep(retry_delay)

        self._running = True
        self._thread  = threading.Thread(
            target    = _run,
            name      = "CDC-Postgres",
            daemon    = True,
        )
        self._thread.start()
        logger.info("CDCPostgresConnector: background thread started")
        return self._thread

    def stop(self) -> None:
        """Stop the background CDC thread."""
        self._running = False
        self.close()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=10)
        logger.info("CDCPostgresConnector: stopped")

    # ------------------------------------------------------------------
    # Convenience: check WAL prerequisites on the database
    # ------------------------------------------------------------------

    def check_prerequisites(self) -> Dict[str, Any]:
        """
        Connect with a standard (non-replication) connection and verify
        that WAL-level and publication are configured correctly.

        Returns a dict with status per prerequisite.
        """
        result: Dict[str, Any] = {
            "wal_level":    {"ok": False, "value": None},
            "publication":  {"ok": False, "name":  self._publication},
            "slot":         {"ok": False, "name":  self._slot_name},
            "errors":       [],
        }
        try:
            import psycopg2

            c = self._cfg
            conn = psycopg2.connect(
                host     = c["host"],
                port     = int(c.get("port", 5432)),
                database = c["database"],
                user     = c["user"],
                password = c["password"],
            )
            cur = conn.cursor()

            # WAL level
            cur.execute("SHOW wal_level;")
            wal = cur.fetchone()[0]
            result["wal_level"]["value"] = wal
            result["wal_level"]["ok"]    = wal == "logical"

            # Publication
            cur.execute(
                "SELECT pubname FROM pg_publication WHERE pubname = %s;",
                (self._publication,),
            )
            result["publication"]["ok"] = bool(cur.fetchone())

            # Replication slot
            cur.execute(
                "SELECT slot_name FROM pg_replication_slots WHERE slot_name = %s;",
                (self._slot_name,),
            )
            result["slot"]["ok"] = bool(cur.fetchone())

            cur.close()
            conn.close()

        except Exception as exc:
            result["errors"].append(str(exc))

        return result
