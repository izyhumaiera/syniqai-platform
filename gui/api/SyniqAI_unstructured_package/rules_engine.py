"""
Quality Rules Engine
====================
Manages quality and transformation rules for every unstructured media type.

Rules are persisted in PostgreSQL table `syniq_unstructured_rules`.
If PostgreSQL is unavailable the engine falls back to an in-process dict
so the rest of the API never fails.

Schema:
  media_type   TEXT  NOT NULL   -- image | video | audio | document | text
  category     TEXT  NOT NULL   -- technical | content | metadata | compliance | transform
  rule_key     TEXT  NOT NULL   -- machine-readable identifier
  rule_label   TEXT  NOT NULL   -- human-readable name
  description  TEXT
  severity     TEXT             -- high | medium | low
  rule_value   JSONB            -- arbitrary rule config / threshold
  enabled      BOOL DEFAULT TRUE
  created_at   TIMESTAMPTZ
  updated_at   TIMESTAMPTZ
  UNIQUE (media_type, rule_key)
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Built-in rule catalogue — used when DB is empty or unavailable
# ---------------------------------------------------------------------------
_DEFAULT_QUALITY_RULES: List[Dict[str, Any]] = [
    # --- Image ---
    {"media_type": "image", "category": "technical", "rule_key": "min_resolution",
     "rule_label": "Minimum Resolution", "description": "Minimum 720p (1280×720) required",
     "severity": "high", "rule_value": {"width": 1280, "height": 720}},
    {"media_type": "image", "category": "technical", "rule_key": "max_file_size_mb",
     "rule_label": "Max File Size", "description": "Image files must be under 50 MB",
     "severity": "low", "rule_value": {"max_mb": 50}},
    {"media_type": "image", "category": "content", "rule_key": "blur_threshold",
     "rule_label": "Blur Detection", "description": "Laplacian variance must be ≥ 100 (clarity check)",
     "severity": "medium", "rule_value": {"min_variance": 100}},
    {"media_type": "image", "category": "metadata", "rule_key": "exif_completeness",
     "rule_label": "EXIF Completeness", "description": "Camera make, model and timestamp must be present",
     "severity": "medium", "rule_value": {"required_fields": ["make", "model", "datetime"]}},
    {"media_type": "image", "category": "compliance", "rule_key": "format_whitelist",
     "rule_label": "Allowed Formats", "description": "Only JPEG, PNG, WEBP, TIFF are accepted",
     "severity": "high", "rule_value": {"allowed": ["jpg", "jpeg", "png", "webp", "tiff"]}},

    # --- Video ---
    {"media_type": "video", "category": "technical", "rule_key": "codec_validation",
     "rule_label": "Video Codec Validation", "description": "Must use H.264 or H.265",
     "severity": "medium", "rule_value": {"allowed_codecs": ["h264", "h265", "hevc"]}},
    {"media_type": "video", "category": "technical", "rule_key": "min_fps",
     "rule_label": "Minimum Frame Rate", "description": "Videos must have ≥ 15 FPS",
     "severity": "medium", "rule_value": {"min_fps": 15}},
    {"media_type": "video", "category": "content", "rule_key": "min_duration_seconds",
     "rule_label": "Minimum Duration", "description": "Video must be at least 1 second",
     "severity": "low", "rule_value": {"min_seconds": 1}},
    {"media_type": "video", "category": "metadata", "rule_key": "has_audio_track",
     "rule_label": "Audio Track Presence", "description": "Video must contain an audio track",
     "severity": "low", "rule_value": {"required": False}},

    # --- Audio ---
    {"media_type": "audio", "category": "technical", "rule_key": "min_sample_rate",
     "rule_label": "Minimum Sample Rate", "description": "Sample rate must be ≥ 16 000 Hz",
     "severity": "high", "rule_value": {"min_hz": 16000}},
    {"media_type": "audio", "category": "content", "rule_key": "silence_detection",
     "rule_label": "Silence Detection", "description": "File must not be entirely silent",
     "severity": "high", "rule_value": {"max_silence_ratio": 0.95}},
    {"media_type": "audio", "category": "content", "rule_key": "noise_threshold_db",
     "rule_label": "Background Noise Level", "description": "Average noise must be below −40 dBFS",
     "severity": "low", "rule_value": {"max_noise_db": -40}},
    {"media_type": "audio", "category": "metadata", "rule_key": "duration_metadata",
     "rule_label": "Duration Metadata", "description": "Duration field must be present in file header",
     "severity": "medium", "rule_value": {}},
    {"media_type": "audio", "category": "technical", "rule_key": "format_whitelist",
     "rule_label": "Allowed Audio Formats", "description": "Only MP3, WAV, FLAC, AAC, OGG accepted",
     "severity": "medium", "rule_value": {"allowed": ["mp3", "wav", "flac", "aac", "ogg", "m4a"]}},

    # --- Document ---
    {"media_type": "document", "category": "technical", "rule_key": "not_corrupted",
     "rule_label": "File Integrity Check", "description": "File must be parseable without errors",
     "severity": "high", "rule_value": {}},
    {"media_type": "document", "category": "content", "rule_key": "min_text_length",
     "rule_label": "Minimum Text Content", "description": "Extracted text must be ≥ 50 characters",
     "severity": "medium", "rule_value": {"min_chars": 50}},
    {"media_type": "document", "category": "metadata", "rule_key": "language_detected",
     "rule_label": "Language Detection", "description": "Document language must be detectable",
     "severity": "low", "rule_value": {}},
    {"media_type": "document", "category": "compliance", "rule_key": "pii_redacted",
     "rule_label": "PII Redaction Check", "description": "PII (SSN, credit card) must be redacted",
     "severity": "high", "rule_value": {"pii_patterns": ["ssn", "credit_card", "passport"]}},
    {"media_type": "document", "category": "metadata", "rule_key": "exif_completeness",
     "rule_label": "EXIF / PDF Metadata", "description": "Author and creation date must be present",
     "severity": "low", "rule_value": {"required_fields": ["author", "creation_date"]}},

    # --- Text ---
    {"media_type": "text", "category": "content", "rule_key": "min_text_length",
     "rule_label": "Minimum Text Length", "description": "Text must contain ≥ 10 characters",
     "severity": "medium", "rule_value": {"min_chars": 10}},
    {"media_type": "text", "category": "content", "rule_key": "language_detected",
     "rule_label": "Language Detectable", "description": "Language must be identifiable",
     "severity": "low", "rule_value": {}},
    {"media_type": "text", "category": "compliance", "rule_key": "pii_check",
     "rule_label": "PII Presence Check", "description": "Flag text containing unredacted PII",
     "severity": "medium", "rule_value": {}},
]

_DEFAULT_TRANSFORM_RULES: Dict[str, Dict[str, Any]] = {
    "image":    {"resize": False, "resizeWidth": 224, "resizeHeight": 224,
                 "normalizePixels": False, "grayscale": False,
                 "edgeDetection": False, "objectDetection": False,
                 "formatConversion": None, "min_resolution": 720,
                 "max_file_size_mb": 50},
    "video":    {"normalizeFPS": False, "targetFPS": 30, "compression": False,
                 "formatConversion": None},
    "audio":    {"normalizeVolume": False, "channelConfig": None,
                 "formatConversion": None},
    "document": {"extractText": True, "detectLanguage": True,
                 "sentimentAnalysis": False, "piiRedaction": False,
                 "chunkSize": 1024},
    "text":     {"extractText": True, "detectLanguage": True,
                 "sentimentAnalysis": False, "piiRedaction": False},
}


class QualityRulesEngine:
    """
    Manages quality + transformation rules backed by PostgreSQL.
    Falls back to built-in defaults when the DB is unreachable.
    """

    DDL = """
    CREATE TABLE IF NOT EXISTS syniq_unstructured_rules (
        id           SERIAL PRIMARY KEY,
        media_type   TEXT    NOT NULL,
        category     TEXT    NOT NULL DEFAULT 'technical',
        rule_key     TEXT    NOT NULL,
        rule_label   TEXT    NOT NULL,
        description  TEXT    NOT NULL DEFAULT '',
        severity     TEXT    NOT NULL DEFAULT 'medium',
        rule_value   JSONB   NOT NULL DEFAULT '{}',
        enabled      BOOL    NOT NULL DEFAULT TRUE,
        created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        UNIQUE (media_type, rule_key)
    );
    """

    def __init__(self, postgres_config=None):
        self._cfg = postgres_config
        self._db_ok = False
        self._cache: Dict[str, List[Dict]] = {}
        self._transform_cache: Dict[str, Dict] = {}
        self._try_init()

    # ------------------------------------------------------------------
    # Initialisation / DB bootstrap
    # ------------------------------------------------------------------

    def _try_init(self) -> None:
        try:
            conn = self._connect()
            with conn:
                with conn.cursor() as cur:
                    cur.execute(self.DDL)
                    # Seed defaults if the table is empty
                    cur.execute("SELECT COUNT(*) FROM syniq_unstructured_rules")
                    count = cur.fetchone()[0]
                    if count == 0:
                        self._seed_defaults(cur)
            conn.close()
            self._db_ok = True
            logger.info("QualityRulesEngine: PostgreSQL-backed rules initialised")
        except Exception as exc:
            logger.warning(f"QualityRulesEngine: DB unavailable ({exc}); using built-in defaults")

    def _connect(self):
        import psycopg2  # type: ignore
        cfg = self._cfg
        if cfg is None:
            return psycopg2.connect(
                host=os.getenv("POSTGRES_HOST", "localhost"),
                port=int(os.getenv("POSTGRES_PORT", "5432")),
                dbname=os.getenv("POSTGRES_DB", "syniqai_metadata"),
                user=os.getenv("POSTGRES_USER", "syniqai_user"),
                password=os.getenv("POSTGRES_PASSWORD", "syniqai_password"),
            )
        return psycopg2.connect(
            host=cfg.host, port=cfg.port,
            dbname=cfg.database, user=cfg.user, password=cfg.password,
        )

    def _seed_defaults(self, cur) -> None:
        for rule in _DEFAULT_QUALITY_RULES:
            cur.execute(
                """
                INSERT INTO syniq_unstructured_rules
                  (media_type, category, rule_key, rule_label, description, severity, rule_value)
                VALUES (%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (media_type, rule_key) DO NOTHING
                """,
                (
                    rule["media_type"], rule["category"],
                    rule["rule_key"], rule["rule_label"],
                    rule.get("description", ""), rule.get("severity", "medium"),
                    json.dumps(rule.get("rule_value", {})),
                ),
            )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_quality_rules(
        self,
        media_type: Optional[str] = None,
        category: Optional[str] = None,
        enabled_only: bool = True,
    ) -> List[Dict[str, Any]]:
        """Return quality rules, optionally filtered by media_type / category."""
        cache_key = f"{media_type}:{category}:{enabled_only}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        if self._db_ok:
            try:
                conn = self._connect()
                with conn:
                    with conn.cursor() as cur:
                        clauses = []
                        params: list = []
                        if media_type:
                            clauses.append("media_type = %s")
                            params.append(media_type)
                        if category:
                            clauses.append("category = %s")
                            params.append(category)
                        if enabled_only:
                            clauses.append("enabled = TRUE")
                        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
                        cur.execute(
                            f"SELECT id,media_type,category,rule_key,rule_label,"
                            f"description,severity,rule_value,enabled,updated_at "
                            f"FROM syniq_unstructured_rules {where} ORDER BY media_type,category,id",
                            params,
                        )
                        rows = cur.fetchall()
                conn.close()
                rules = [
                    {
                        "id": r[0], "media_type": r[1], "category": r[2],
                        "rule_key": r[3], "rule_label": r[4],
                        "description": r[5] or "", "severity": r[6],
                        "rule_value": r[7] if isinstance(r[7], dict) else json.loads(r[7] or "{}"),
                        "enabled": r[8],
                        "updated_at": r[9].isoformat() if r[9] else None,
                    }
                    for r in rows
                ]
                self._cache[cache_key] = rules
                return rules
            except Exception as exc:
                logger.warning(f"QualityRulesEngine.get_quality_rules failed: {exc}")

        # Fallback to in-memory defaults
        rules = _DEFAULT_QUALITY_RULES
        if media_type:
            rules = [r for r in rules if r["media_type"] == media_type]
        if category:
            rules = [r for r in rules if r["category"] == category]
        result = [
            {**r, "id": i + 1, "enabled": True, "updated_at": None}
            for i, r in enumerate(rules)
        ]
        self._cache[cache_key] = result
        return result

    def upsert_quality_rule(self, media_type: str, rule_key: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Create or update a quality rule. Returns the saved rule dict."""
        self._cache.clear()  # invalidate cache
        if self._db_ok:
            try:
                conn = self._connect()
                with conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            """
                            INSERT INTO syniq_unstructured_rules
                              (media_type,category,rule_key,rule_label,description,severity,rule_value,enabled)
                            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                            ON CONFLICT (media_type, rule_key) DO UPDATE SET
                              category    = EXCLUDED.category,
                              rule_label  = EXCLUDED.rule_label,
                              description = EXCLUDED.description,
                              severity    = EXCLUDED.severity,
                              rule_value  = EXCLUDED.rule_value,
                              enabled     = EXCLUDED.enabled,
                              updated_at  = NOW()
                            RETURNING id, updated_at
                            """,
                            (
                                media_type,
                                updates.get("category", "technical"),
                                rule_key,
                                updates.get("rule_label", rule_key),
                                updates.get("description", ""),
                                updates.get("severity", "medium"),
                                json.dumps(updates.get("rule_value", {})),
                                updates.get("enabled", True),
                            ),
                        )
                        row = cur.fetchone()
                conn.close()
                return {**updates, "id": row[0], "updated_at": row[1].isoformat()}
            except Exception as exc:
                logger.warning(f"QualityRulesEngine.upsert failed: {exc}")
        return {**updates, "id": None, "updated_at": datetime.now(timezone.utc).isoformat()}

    def get_transform_rules(self, media_type: str) -> Dict[str, Any]:
        """Return current transformation knobs for media_type."""
        if media_type in self._transform_cache:
            return self._transform_cache[media_type]
        return dict(_DEFAULT_TRANSFORM_RULES.get(media_type, {}))

    def save_transform_rules(self, media_type: str, rules: Dict[str, Any]) -> Dict[str, Any]:
        """Merge and persist transformation rules (uses same DB table, category=transform)."""
        current = self.get_transform_rules(media_type)
        merged = {**current, **rules}
        self._transform_cache[media_type] = merged

        if self._db_ok:
            try:
                conn = self._connect()
                with conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            """
                            INSERT INTO syniq_unstructured_rules
                              (media_type, category, rule_key, rule_label, description, severity, rule_value)
                            VALUES (%s,'transform','transform_config','Transform Configuration','',
                                    'low',%s)
                            ON CONFLICT (media_type, rule_key) DO UPDATE SET
                              rule_value = EXCLUDED.rule_value,
                              updated_at = NOW()
                            """,
                            (media_type, json.dumps(merged)),
                        )
                conn.close()
            except Exception as exc:
                logger.warning(f"save_transform_rules write failed: {exc}")
        return merged

    def evaluate_quality_summary(self, records: List[Dict], media_type: str) -> Dict[str, Any]:
        """
        Lightweight rule evaluation over a list of record dicts.
        Returns per-rule pass/fail counts without Spark.
        """
        rules = self.get_quality_rules(media_type=media_type)
        total = len(records)
        results = []
        for rule in rules:
            key = rule["rule_key"]
            rv = rule.get("rule_value", {})
            passed = total
            failed = 0

            if key == "min_resolution":
                w, h = rv.get("width", 0), rv.get("height", 0)
                failed = sum(
                    1 for r in records
                    if (r.get("width") or 0) < w or (r.get("height") or 0) < h
                )
                passed = total - failed
            elif key == "max_file_size_mb":
                limit = rv.get("max_mb", 50) * 1024 * 1024
                failed = sum(1 for r in records if (r.get("size_bytes") or 0) > limit)
                passed = total - failed
            elif key == "silence_detection":
                failed = sum(1 for r in records if r.get("is_silent"))
                passed = total - failed
            elif key == "not_corrupted":
                failed = sum(1 for r in records if r.get("is_corrupted"))
                passed = total - failed
            elif key == "min_text_length":
                min_chars = rv.get("min_chars", 50)
                failed = sum(1 for r in records if len(r.get("extracted_text", "") or "") < min_chars)
                passed = total - failed

            pass_rate = round(passed / total * 100, 1) if total else 0.0
            results.append({**rule, "passed": passed, "failed": failed, "pass_rate": pass_rate, "total": total})

        return {"media_type": media_type, "total_records": total, "rules": results}
