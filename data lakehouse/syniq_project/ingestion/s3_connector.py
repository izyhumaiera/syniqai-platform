"""
S3Connector
===========
Lists raw media assets from an AWS S3 bucket for the UnstructuredProcessor.

Interface expected by spark_unstructured_processor.py:
    connector = S3Connector(config)
    connector.connect()                          -> bool
    connector.list_assets(media_type, prefix,
                          limit, generate_presigned) -> List[dict]
    connector.disconnect()
"""
from __future__ import annotations

import logging
import mimetypes
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Media-type → file extensions
_MEDIA_EXTENSIONS: Dict[str, tuple] = {
    "image":    (".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff", ".tif"),
    "video":    (".mp4", ".avi", ".mov", ".mkv", ".wmv", ".flv", ".webm", ".m4v"),
    "audio":    (".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a", ".wma"),
    "document": (".pdf", ".docx", ".doc", ".pptx", ".ppt", ".xlsx", ".xls", ".txt"),
    "text":     (".txt", ".md", ".csv", ".json", ".jsonl", ".xml", ".html"),
}


class S3Connector:
    """
    Connects to AWS S3 and lists media assets for the unstructured pipeline.

    Config keys (all accepted from UnstructuredProcessor._s3_config):
        bucket            : S3 bucket name  (required)
        prefix            : key prefix / folder  (optional)
        aws_access_key_id : or 'aws_access_key'
        aws_secret_access_key : or 'aws_secret_key'
        region_name       : or 'aws_region'  (default ap-southeast-1)
    """

    def __init__(self, config: Dict[str, Any]):
        self._config = config or {}
        self._s3 = None
        self._bucket = (
            config.get("bucket")
            or config.get("s3_bucket")
            or ""
        )

    # ------------------------------------------------------------------
    def connect(self) -> bool:
        """Initialise boto3 S3 client. Returns True on success."""
        try:
            import boto3  # type: ignore
            from botocore.config import Config  # type: ignore

            c = self._config
            access_key = c.get("aws_access_key_id") or c.get("aws_access_key") or ""
            secret_key = (
                c.get("aws_secret_access_key")
                or c.get("aws_secret_key")
                or ""
            )
            region = (
                c.get("region_name")
                or c.get("aws_region")
                or "ap-southeast-1"
            )

            kwargs: Dict[str, Any] = {
                "region_name": region,
                "config": Config(
                    retries={"max_attempts": 3, "mode": "standard"},
                    connect_timeout=10,
                    read_timeout=30,
                ),
            }
            if access_key and secret_key:
                kwargs["aws_access_key_id"] = access_key
                kwargs["aws_secret_access_key"] = secret_key

            self._s3 = boto3.client("s3", **kwargs)
            # Quick connectivity check
            self._s3.head_bucket(Bucket=self._bucket)
            logger.info(f"S3Connector: connected to bucket '{self._bucket}'")
            return True

        except Exception as exc:
            logger.error(f"S3Connector.connect() failed: {exc}")
            self._s3 = None
            return False

    # ------------------------------------------------------------------
    def list_assets(
        self,
        media_type: Optional[str] = None,
        prefix: Optional[str] = None,
        limit: int = 500,
        generate_presigned: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        List objects in the bucket that match media_type.

        Returns list of dicts with keys:
            uri, file_name, file_size, media_type, content_type,
            s3_key, s3_bucket, presigned_url (if requested)
        """
        if self._s3 is None:
            logger.error("S3Connector not connected — call connect() first")
            return []

        allowed_exts: Optional[tuple] = None
        if media_type and media_type in _MEDIA_EXTENSIONS:
            allowed_exts = _MEDIA_EXTENSIONS[media_type]

        effective_prefix = prefix or self._config.get("prefix", "")
        paginator = self._s3.get_paginator("list_objects_v2")
        page_config = {"Bucket": self._bucket}
        if effective_prefix:
            page_config["Prefix"] = effective_prefix

        assets: List[Dict[str, Any]] = []
        try:
            for page in paginator.paginate(**page_config):
                for obj in page.get("Contents", []):
                    key: str = obj["Key"]
                    if key.endswith("/"):          # skip folder markers
                        continue

                    ext = Path(key).suffix.lower()
                    if allowed_exts and ext not in allowed_exts:
                        continue

                    content_type, _ = mimetypes.guess_type(key)
                    content_type = content_type or "application/octet-stream"

                    asset: Dict[str, Any] = {
                        "uri": f"s3://{self._bucket}/{key}",
                        "file_name": Path(key).name,
                        "file_size": obj.get("Size", 0),
                        "media_type": media_type or _infer_media_type(ext),
                        "content_type": content_type,
                        "s3_key": key,
                        "s3_bucket": self._bucket,
                        "last_modified": obj.get("LastModified", "").isoformat()
                        if hasattr(obj.get("LastModified", ""), "isoformat")
                        else str(obj.get("LastModified", "")),
                    }

                    if generate_presigned:
                        try:
                            asset["presigned_url"] = self._s3.generate_presigned_url(
                                "get_object",
                                Params={"Bucket": self._bucket, "Key": key},
                                ExpiresIn=3600,
                            )
                        except Exception:
                            asset["presigned_url"] = None

                    assets.append(asset)
                    if len(assets) >= limit:
                        return assets

        except Exception as exc:
            logger.error(f"S3Connector.list_assets() failed: {exc}")

        logger.info(f"S3Connector: found {len(assets)} '{media_type}' assets")
        return assets

    # ------------------------------------------------------------------
    def disconnect(self) -> None:
        """Release the boto3 client."""
        self._s3 = None
        logger.debug("S3Connector: disconnected")


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _infer_media_type(ext: str) -> str:
    for media_type, exts in _MEDIA_EXTENSIONS.items():
        if ext in exts:
            return media_type
    return "unknown"
