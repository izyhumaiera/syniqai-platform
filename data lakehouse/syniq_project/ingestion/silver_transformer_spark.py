"""
Silver Transformer - Spark + Iceberg Implementation
Replaces Pandas-based transformation for large datasets (>1GB)

Features:
- Distributed processing with Apache Spark
- ACID transactions with Iceberg tables
- Schema evolution and time-travel
- Incremental processing with watermarks
- Data quality validation
- Quarantine management
"""
import os
import json
import logging
import io
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import (
    col, trim, upper, lower, when, lit, isnan, isnull, 
    count, sum as spark_sum, coalesce, regexp_replace, to_timestamp,
    current_timestamp, md5, concat_ws, year, month, dayofmonth
)
from pyspark.sql.types import (
    StructType, StructField, StringType, DoubleType, IntegerType, 
    TimestampType, BooleanType, LongType, ArrayType
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SilverTransformerSpark:
    """
    Spark-based Silver layer transformation engine
    Processes Bronze data → Silver with quality checks using distributed computing
    """
    
    def __init__(self, spark: SparkSession = None, minio_config: Dict[str, Any] = None):
        """
        Initialize Spark transformer.

        Spark session is lazy — it is only created when a *structured* data
        transformation is requested.  Unstructured pipelines (image, audio,
        video, text, PDF) run entirely in Python and never need the JVM.
        """
        self.spark = spark          # may stay None for unstructured jobs
        self.minio_config = minio_config or self._load_minio_config()
        self._spark_initialised = spark is not None

        # Configuration
        self.catalog_name = "syniq_iceberg"
        self.silver_bucket = "syniqai-bronze"
        self.quarantine_bucket = "syniqai-bronze"

        if self.spark is not None:
            logger.info(f"✅ SilverTransformerSpark initialized with Spark {self.spark.version}")
        else:
            logger.info("✅ SilverTransformerSpark initialized (Spark lazy — will start on first structured job)")

    def _ensure_spark(self):
        """Start the Spark session on demand (structured jobs only)."""
        if self.spark is None:
            self.spark = self._create_spark_session()
            self._spark_initialised = True
    
    def _load_minio_config(self) -> Dict[str, Any]:
        """Load MinIO configuration from config file"""
        try:
            from utils.config_loader import load_config
            from pathlib import Path
            config_path = Path(__file__).parent.parent / "config" / "minio_config.yaml"
            config = load_config(str(config_path))
            return config.get('minio', {})
        except Exception as e:
            logger.warning(f"Could not load MinIO config: {e}")
            # Fallback to actual MinIO credentials
            return {
                'endpoint': 'http://localhost:9000',
                'access_key': 'admin',
                'secret_key': 'password123'
            }
    
    def _create_spark_session(self) -> SparkSession:
        """Create Spark session with Iceberg configuration"""
        try:
            from utils.spark_iceberg_config import create_spark_session_with_iceberg
            logger.info("Creating Spark session with Iceberg...")
            spark = create_spark_session_with_iceberg(
                app_name="SilverTransformer",
                minio_config=self.minio_config
            )
            logger.info(f"✅ Spark session ready: {spark.version}")
            return spark
        except Exception as e:
            logger.error(f"Failed to create Spark session: {e}")
            raise
    
    def cleanup(self):
        """Cleanup Spark resources (no-op for unstructured jobs that never started Spark)."""
        try:
            if self.spark is not None:
                logger.info("Cleaning up Spark resources...")
                self.spark.catalog.clearCache()
                logger.info("✅ Spark resources cleaned")
        except Exception as e:
            logger.warning(f"Error during cleanup: {e}")
    
    def transform(
        self,
        source: str,
        entity: str,
        domain: str = "general",
        execution_mode: str = "full",
        watermark_column: str = None,
        watermark_value: str = None,
        rules: List[Dict[str, Any]] = None,
        custom_sql: str = None,
        data_type: str = "structured",
        unstructured_type: str = None,
        image_transforms: Dict[str, Any] = None,
        video_transforms: Dict[str, Any] = None,
        audio_transforms: Dict[str, Any] = None,
        text_transforms: Dict[str, Any] = None,
        pdf_transforms: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Transform Bronze data to Silver using Spark
        
        Args:
            source: Source system (e.g., 'postgres', 'mysql')
            entity: Entity name (e.g., 'customers', 'transactions')
            domain: Domain for rule filtering
            execution_mode: 'full' or 'incremental'
            watermark_column: Column for incremental processing
            watermark_value: Last processed watermark value
            rules: List of data quality rules to apply
            custom_sql: Optional custom SQL transformation
            data_type: 'structured' or 'unstructured'
            unstructured_type: 'image', 'video', 'audio', 'text', 'pdf'
            image_transforms: Image transformation options
            video_transforms: Video transformation options
            audio_transforms: Audio transformation options
            text_transforms: Text transformation options
            pdf_transforms: PDF transformation options
        
        Returns:
            Transformation result with metrics
        """
        start_time = datetime.now()
        job_id = f"silver_{source}_{entity}_{start_time.strftime('%Y%m%d_%H%M%S')}"
        
        logger.info(f"🚀 Starting Silver transformation: {source}.{entity}")
        logger.info(f"   Mode: {execution_mode}, Domain: {domain}, Data Type: {data_type}")
        
        try:
            # Handle unstructured data differently
            if data_type == "unstructured":
                return self._transform_unstructured(
                    source, entity, domain, unstructured_type,
                    image_transforms, video_transforms, audio_transforms,
                    text_transforms, pdf_transforms,
                    job_id, start_time
                )
            
            # Step 1: Read from Bronze (structured data) — start Spark now
            self._ensure_spark()
            bronze_df = self._read_bronze(source, entity, domain, execution_mode, watermark_column, watermark_value)
            initial_count = bronze_df.count()
            logger.info(f"✅ Read {initial_count:,} rows from Bronze")
            
            # Step 2: Apply data quality rules
            clean_df, quarantine_df, quality_metrics = self._apply_quality_rules(
                bronze_df, source, entity, rules or []
            )
            
            # Step 3: Apply custom SQL transformation if provided
            if custom_sql:
                clean_df = self._apply_custom_sql(clean_df, custom_sql, source, entity)
            
            # Step 4: Remove duplicates
            clean_df, duplicates_removed = self._remove_duplicates(clean_df)
            
            # Step 5: Standardize data types and formats
            clean_df = self._standardize_data(clean_df)
            
            # Step 6: Add metadata columns
            clean_df = self._add_metadata_columns(clean_df, source, entity, job_id)
            
            final_count = clean_df.count()
            quarantine_count = quarantine_df.count() if quarantine_df else 0
            
            logger.info(f"📊 Transformation complete:")
            logger.info(f"   Processed: {final_count:,} rows")
            logger.info(f"   Quarantined: {quarantine_count:,} rows")
            logger.info(f"   Duplicates removed: {duplicates_removed:,}")
            
            # Step 7: Write to Silver as Iceberg table
            silver_table = self._write_to_silver(
                clean_df, source, entity, execution_mode, watermark_column
            )
            
            # Step 8: Write quarantine data
            if quarantine_count > 0:
                self._write_quarantine(quarantine_df, source, entity, job_id)
            
            # Step 9: Calculate final metrics
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            result = {
                "job_id": job_id,
                "status": "completed",
                "source": source,
                "entity": entity,
                "domain": domain,
                "execution_mode": execution_mode,
                "silver_table": silver_table,
                "metrics": {
                    "initial_rows": initial_count,
                    "final_rows": final_count,
                    "rows_quarantined": quarantine_count,
                    "duplicates_removed": duplicates_removed,
                    "processing_time_seconds": duration,
                    "throughput_rows_per_second": int(initial_count / duration) if duration > 0 else 0
                },
                "quality_metrics": quality_metrics,
                "watermark": {
                    "column": watermark_column,
                    "last_value": self._get_max_watermark(clean_df, watermark_column) if watermark_column else None
                },
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat()
            }
            
            logger.info(f"✅ Silver transformation completed in {duration:.2f}s")
            return result
            
        except Exception as e:
            logger.error(f"❌ Silver transformation failed: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            
            return {
                "job_id": job_id,
                "status": "failed",
                "source": source,
                "entity": entity,
                "error": str(e),
                "start_time": start_time.isoformat(),
                "end_time": datetime.now().isoformat()
            }
    
    def _transform_unstructured(
        self,
        source: str,
        entity: str,
        domain: str,
        unstructured_type: str,
        image_transforms: Dict[str, Any],
        video_transforms: Dict[str, Any],
        audio_transforms: Dict[str, Any],
        text_transforms: Dict[str, Any],
        pdf_transforms: Dict[str, Any],
        job_id: str,
        start_time: datetime
    ) -> Dict[str, Any]:
        """Transform unstructured data (images, videos, audio, text, pdf).

        All binary processing is done in pure Python on the driver — we never
        create a Spark DataFrame containing a BinaryType column because that
        causes Python worker crashes on Windows/PySpark-4.x.
        """
        logger.info(f"🖼️ Transforming unstructured data: {unstructured_type}")
        
        try:
            # Step 1: Load raw file data as plain Python dicts (no Spark involved).
            # Returns (List[Dict], int) — dicts have keys: path, file_name,
            # file_extension, file_size_bytes, content (bytes).
            raw_files, initial_count = self._read_unstructured_bronze(source, entity, domain, unstructured_type)
            logger.info(f"✅ Found {initial_count:,} {unstructured_type} files")
            
            # Step 2: Apply transformations locally — all functions accept
            # List[Dict] and return List[Dict] with extracted features.
            # No binary content is ever put into a Spark DataFrame.
            if unstructured_type == "image" and image_transforms:
                result_rows = self._apply_image_transforms(raw_files, image_transforms)
            elif unstructured_type == "video" and video_transforms:
                result_rows = self._apply_video_transforms(raw_files, video_transforms)
            elif unstructured_type == "audio" and audio_transforms:
                result_rows = self._apply_audio_transforms(raw_files, audio_transforms)
            elif unstructured_type == "text" and text_transforms:
                result_rows = self._apply_text_transforms(raw_files, text_transforms)
            elif unstructured_type == "pdf" and pdf_transforms:
                result_rows = self._apply_pdf_transforms(raw_files, pdf_transforms)
            else:
                # No transforms — build basic metadata rows from raw files
                result_rows = [
                    {
                        "path": r["path"],
                        "file_name": r["file_name"],
                        "file_extension": r["file_extension"],
                        "file_size_bytes": r["file_size_bytes"],
                        "is_corrupted": False,
                        "error_message": None,
                    }
                    for r in raw_files
                ]

            # Step 3: Add job metadata to every result row (pure Python)
            now_str = datetime.now().isoformat()
            for row in result_rows:
                row["_processing_timestamp"] = now_str
                row["_job_id"] = job_id
                row["_data_type"] = unstructured_type

            final_count = len(result_rows)
            logger.info(f"✅ Transformed {final_count:,} files")

            # Step 4: Write metadata directly to MinIO Silver as Parquet.
            # No Spark, no pandas needed — pyarrow writes columnar Parquet
            # straight to MinIO. The binary files themselves stay in Bronze;
            # Silver only holds the extracted metadata (dimensions, duration, etc.)
            silver_path = self._write_unstructured_to_silver(result_rows, source, entity, unstructured_type)
            
            # Calculate metrics
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            result = {
                "job_id": job_id,
                "status": "completed",
                "source": source,
                "entity": entity,
                "domain": domain,
                "data_type": "unstructured",
                "unstructured_type": unstructured_type,
                "silver_table": silver_path,
                "row_count": final_count,
                "duration": duration,
                "metrics": {
                    "initial_files": initial_count,
                    "processed_files": final_count,
                    "processing_time_seconds": duration
                },
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat()
            }
            
            logger.info(f"✅ Unstructured transformation completed in {duration:.2f}s")
            return result
            
        except Exception as e:
            logger.error(f"❌ Unstructured transformation failed: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            
            return {
                "job_id": job_id,
                "status": "failed",
                "source": source,
                "entity": entity,
                "error": str(e),
                "start_time": start_time.isoformat(),
                "end_time": datetime.now().isoformat()
            }
    
    def _read_unstructured_bronze(
        self,
        source: str,
        entity: str,
        domain: str,
        unstructured_type: str,
    ):
        """Read unstructured files from Bronze using MinIO client.

        Returns (List[Dict], int) — raw Python dicts with keys:
          path, file_name, file_extension, file_size_bytes, content (bytes).

        Binary content is kept as plain Python bytes on the driver.
        We never create a Spark DataFrame with BinaryType here because
        PySpark 4.x on Windows crashes Python workers whenever a BinaryType
        column is touched (count, collect, createDataFrame then collect, etc.).
        """
        from minio import Minio  # type: ignore

        bronze_prefix = f"{domain}/{source}/{entity}/"
        logger.info(f"📖 Reading unstructured files from MinIO: syniqai-bronze/{bronze_prefix}")

        extension_filters = {
            "image": {"jpg", "jpeg", "png", "gif", "bmp", "tiff", "webp"},
            "video": {"mp4", "avi", "mov", "wmv", "flv", "mkv", "webm"},
            "audio": {"mp3", "wav", "flac", "aac", "ogg", "m4a"},
            "text":  {"txt", "csv", "json", "log"},
            "pdf":   {"pdf"},
        }
        valid_ext = extension_filters.get(unstructured_type, set())

        # Build MinIO client from stored config
        minio_cfg = self.minio_config or {}
        endpoint = (
            minio_cfg.get("endpoint", "http://localhost:9000")
            .replace("http://", "")
            .replace("https://", "")
        )
        secure = minio_cfg.get("endpoint", "http://localhost:9000").startswith("https://")
        minio_client = Minio(
            endpoint=endpoint,
            access_key=minio_cfg.get("access_key", "admin"),
            secret_key=minio_cfg.get("secret_key", "password123"),
            secure=secure,
        )

        rows = []
        try:
            objects = minio_client.list_objects(
                "syniqai-bronze", prefix=bronze_prefix, recursive=True
            )
            for obj in objects:
                fname = obj.object_name.split("/")[-1]
                if not fname:
                    continue
                ext = fname.rsplit(".", 1)[-1].lower() if "." in fname else ""
                if valid_ext and ext not in valid_ext:
                    continue

                # Download binary content on the driver — no Spark worker involved
                response = minio_client.get_object("syniqai-bronze", obj.object_name)
                content = response.read()
                response.close()
                response.release_conn()

                rows.append(
                    {
                        "path": f"s3a://syniqai-bronze/{obj.object_name}",
                        "file_name": fname,
                        "file_extension": ext,
                        "file_size_bytes": int(obj.size or len(content)),
                        "content": content,          # raw bytes, driver-only
                    }
                )
        except Exception as e:
            logger.error(f"Failed to read unstructured Bronze data from MinIO: {e}")
            raise

        if not rows:
            raise ValueError(
                f"No {unstructured_type} files found in syniqai-bronze/{bronze_prefix}. "
                "Ensure files are staged to Bronze before running the Silver pipeline."
            )

        logger.info(f"   Loaded {len(rows)} files from MinIO into driver memory")
        return rows, len(rows)
    
    def _get_file_filter(self, unstructured_type: str) -> str:
        """Get file filter pattern based on unstructured type"""
        # Note: pathGlobFilter doesn't support brace expansion, so we use wildcard
        # and filter by extension in the dataframe
        return "*.*"
    
    def _apply_image_transforms(self, files_data: List[Dict], transforms: Dict[str, Any]) -> List[Dict]:
        """Apply image transformations with actual feature extraction.

        Accepts a list of plain Python dicts (not a Spark DataFrame) to avoid
        PySpark 4.x Python-worker crashes on Windows when handling BinaryType.
        Returns a list of result dicts (metadata only, no binary content).
        """
        logger.info("🖼️ Applying image transformations with feature extraction...")
        logger.info(f"   Processing {len(files_data)} image files locally...")
        
        # Process locally to avoid serialization
        from PIL import Image
        import cv2
        import numpy as np
        
        results = []
        for row_data in files_data:
            try:
                # Load image from binary content
                image = Image.open(io.BytesIO(row_data['content']))
                
                # Basic properties
                width, height = image.size
                color_mode = str(image.mode)
                img_format = str(image.format) if image.format else "UNKNOWN"
                
                # Convert to numpy for analysis
                img_array = np.array(image.convert('RGB'))
                
                # Calculate brightness
                brightness = float(np.mean(img_array))
                
                # Calculate contrast (standard deviation)
                contrast = float(np.std(img_array))
                
                # Calculate blur score using Laplacian variance
                gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
                blur_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())
                
                # Explicitly close image to free memory
                image.close()
                del img_array
                del gray
                
                results.append({
                    "path": str(row_data['path']),
                    "file_name": str(row_data['file_name']),
                    "file_extension": str(row_data['file_extension']),
                    "file_size_bytes": int(row_data['file_size_bytes']),
                    "width": int(width),
                    "height": int(height),
                    "color_mode": str(color_mode),
                    "format": str(img_format),
                    "is_corrupted": False,
                    "brightness_avg": float(brightness),
                    "contrast_score": float(contrast),
                    "blur_score": float(blur_score),
                    "error_message": None,
                    "original_dimensions": f"{width}x{height}",
                    "is_resized": bool(transforms.get("resize", False)),
                    "target_width": int(transforms.get("resizeWidth", 224)) if transforms.get("resize") else None,
                    "target_height": int(transforms.get("resizeHeight", 224)) if transforms.get("resize") else None,
                    "is_format_converted": bool(transforms.get("formatConversion")),
                    "target_format": str(transforms.get("formatConversion")) if transforms.get("formatConversion") else None,
                    "is_normalized": bool(transforms.get("normalizePixels", False)),
                    "is_grayscale": bool(transforms.get("grayscale", False)),
                    "edge_detected": bool(transforms.get("edgeDetection", False)),
                    "object_detected": bool(transforms.get("objectDetection", False)),
                    "processing_status": "success",
                    "bronze_path": str(row_data['path']),
                    "silver_path": None,
                })
                
            except Exception as e:
                logger.warning(f"   Failed to process {row_data.get('file_name', 'unknown')}: {e}")
                results.append({
                    "path": str(row_data['path']),
                    "file_name": str(row_data['file_name']),
                    "file_extension": str(row_data['file_extension']),
                    "file_size_bytes": int(row_data['file_size_bytes']),
                    "width": None,
                    "height": None,
                    "color_mode": None,
                    "format": None,
                    "is_corrupted": True,
                    "brightness_avg": None,
                    "contrast_score": None,
                    "blur_score": None,
                    "error_message": str(e),
                    "original_dimensions": None,
                    "is_resized": False,
                    "target_width": None,
                    "target_height": None,
                    "is_format_converted": False,
                    "target_format": None,
                    "is_normalized": False,
                    "is_grayscale": False,
                    "edge_detected": False,
                    "object_detected": False,
                    "processing_status": "failed",
                    "bronze_path": str(row_data['path']),
                    "silver_path": None,
                })
        
        logger.info("✅ Image feature extraction completed")
        return results
    
    def _apply_video_transforms(self, files_data: List[Dict], transforms: Dict[str, Any]) -> List[Dict]:
        """Apply video transformations with metadata extraction.

        Accepts List[Dict] (plain Python, no Spark) and returns List[Dict].
        """
        logger.info("🎥 Applying video transformations with metadata extraction...")
        logger.info(f"   Processing {len(files_data)} video files locally...")

        results = []
        for row in files_data:
            try:
                import cv2
                import tempfile

                with tempfile.NamedTemporaryFile(
                    suffix="." + row["file_extension"], delete=False
                ) as tmp:
                    tmp.write(row["content"])
                    tmp_path = tmp.name

                try:
                    cap = cv2.VideoCapture(tmp_path)
                    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    fps = cap.get(cv2.CAP_PROP_FPS)
                    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                    duration = frame_count / fps if fps > 0 else 0.0
                    resolution = f"{width}x{height}"
                    cap.release()
                finally:
                    if os.path.exists(tmp_path):
                        os.unlink(tmp_path)

                results.append({
                    "path": str(row["path"]),
                    "file_name": str(row["file_name"]),
                    "file_extension": str(row["file_extension"]),
                    "file_size_bytes": int(row["file_size_bytes"]),
                    "codec": "UNKNOWN",
                    "duration_seconds": float(duration),
                    "fps": float(fps),
                    "width": int(width),
                    "height": int(height),
                    "resolution": str(resolution),
                    "bitrate_kbps": None,
                    "has_audio": None,
                    "audio_codec": None,
                    "audio_channels": None,
                    "frame_count": int(frame_count),
                    "is_corrupted": False,
                    "error_message": None,
                    "is_compressed": bool(transforms.get("compression", False)),
                    "compression_ratio": None,
                    "is_fps_normalized": bool(transforms.get("normalizeFPS", False)),
                    "target_fps": int(transforms.get("targetFPS", 30)) if transforms.get("normalizeFPS") else None,
                    "is_format_converted": bool(transforms.get("formatConversion")),
                    "target_format": str(transforms.get("formatConversion")) if transforms.get("formatConversion") else None,
                    "processing_status": "success",
                    "bronze_path": str(row["path"]),
                    "silver_path": None,
                })
            except Exception as e:
                logger.warning(f"   Failed to process {row.get('file_name', 'unknown')}: {e}")
                results.append({
                    "path": str(row["path"]),
                    "file_name": str(row["file_name"]),
                    "file_extension": str(row["file_extension"]),
                    "file_size_bytes": int(row["file_size_bytes"]),
                    "codec": None, "duration_seconds": None, "fps": None,
                    "width": None, "height": None, "resolution": None,
                    "bitrate_kbps": None, "has_audio": None, "audio_codec": None,
                    "audio_channels": None, "frame_count": None,
                    "is_corrupted": True,
                    "error_message": str(e),
                    "is_compressed": False, "compression_ratio": None,
                    "is_fps_normalized": False, "target_fps": None,
                    "is_format_converted": False, "target_format": None,
                    "processing_status": "failed",
                    "bronze_path": str(row["path"]), "silver_path": None,
                })

        logger.info("✅ Video metadata extraction completed")
        return results

    def _apply_audio_transforms(self, files_data: List[Dict], transforms: Dict[str, Any]) -> List[Dict]:
        """Apply audio transformations with metadata extraction.

        Accepts List[Dict] (plain Python, no Spark) and returns List[Dict].
        """
        logger.info("🎧 Applying audio transformations with metadata extraction...")
        logger.info(f"   Processing {len(files_data)} audio files locally...")

        results = []
        for row in files_data:
            try:
                import librosa
                import numpy as np
                import tempfile

                with tempfile.NamedTemporaryFile(
                    suffix="." + row["file_extension"], delete=False
                ) as tmp:
                    tmp.write(row["content"])
                    tmp_path = tmp.name

                try:
                    y, sr = librosa.load(tmp_path, sr=None, mono=False)

                    if y.ndim > 1:
                        channels = y.shape[0]
                        y_mono = np.mean(y, axis=0)
                    else:
                        channels = 1
                        y_mono = y

                    duration = len(y_mono) / sr
                    rms = librosa.feature.rms(y=y_mono)[0]
                    avg_volume_db = float(20 * np.log10(np.mean(rms) + 1e-10))
                    peak_volume_db = float(20 * np.log10(np.max(np.abs(y_mono)) + 1e-10))
                    silence_threshold = 0.01
                    is_silent = bool(np.max(np.abs(y_mono)) < silence_threshold)
                    silence_pct = float(np.sum(np.abs(y_mono) < silence_threshold) / len(y_mono) * 100)
                finally:
                    if os.path.exists(tmp_path):
                        os.unlink(tmp_path)

                tc = int(1 if transforms.get("channelConfig") == "mono" else 2) if transforms.get("channelConfig") else None
                results.append({
                    "path": str(row["path"]),
                    "file_name": str(row["file_name"]),
                    "file_extension": str(row["file_extension"]),
                    "file_size_bytes": int(row["file_size_bytes"]),
                    "codec": "UNKNOWN",
                    "duration_seconds": float(duration),
                    "sample_rate_hz": int(sr),
                    "bit_rate_kbps": None,
                    "channels": int(channels),
                    "bits_per_sample": None,
                    "average_volume_db": avg_volume_db,
                    "peak_volume_db": peak_volume_db,
                    "is_silent": is_silent,
                    "silence_percentage": silence_pct,
                    "is_corrupted": False,
                    "error_message": None,
                    "is_format_converted": bool(transforms.get("formatConversion")),
                    "target_format": str(transforms.get("formatConversion")) if transforms.get("formatConversion") else None,
                    "is_normalized": bool(transforms.get("normalizeVolume", False)),
                    "is_channel_converted": bool(transforms.get("channelConfig")),
                    "target_channels": tc,
                    "processing_status": "success",
                    "bronze_path": str(row["path"]),
                    "silver_path": None,
                })
            except Exception as e:
                logger.warning(f"   Failed to process {row.get('file_name', 'unknown')}: {e}")
                results.append({
                    "path": str(row["path"]),
                    "file_name": str(row["file_name"]),
                    "file_extension": str(row["file_extension"]),
                    "file_size_bytes": int(row["file_size_bytes"]),
                    "codec": None, "duration_seconds": None, "sample_rate_hz": None,
                    "bit_rate_kbps": None, "channels": None, "bits_per_sample": None,
                    "average_volume_db": None, "peak_volume_db": None,
                    "is_silent": None, "silence_percentage": None,
                    "is_corrupted": True, "error_message": str(e),
                    "is_format_converted": False, "target_format": None,
                    "is_normalized": False, "is_channel_converted": False, "target_channels": None,
                    "processing_status": "failed",
                    "bronze_path": str(row["path"]), "silver_path": None,
                })

        logger.info("✅ Audio metadata extraction completed")
        return results

    def _apply_text_transforms(self, files_data: List[Dict], transforms: Dict[str, Any]) -> List[Dict]:
        """Apply text file transformations with NLP analysis.

        Accepts List[Dict] (plain Python, no Spark) and returns List[Dict].
        """
        logger.info("📄 Applying text transformations with NLP analysis...")
        logger.info(f"   Processing {len(files_data)} text files locally...")

        results = []
        for row in files_data:
            try:
                import re
                from collections import Counter

                try:
                    text = row["content"].decode("utf-8")
                    encoding = "UTF-8"
                except Exception:
                    try:
                        text = row["content"].decode("latin-1")
                        encoding = "latin-1"
                    except Exception:
                        text = str(row["content"])
                        encoding = "unknown"

                line_count = len(text.split("\n"))
                words = re.findall(r"\w+", text)
                word_count = len(words)
                char_count = len(text)
                text_preview = text[:1000]

                try:
                    from langdetect import detect  # type: ignore
                    detected_language = detect(text[:1000]) if text else None
                except Exception:
                    detected_language = None

                try:
                    from textblob import TextBlob  # type: ignore
                    blob = TextBlob(text[:5000])
                    sentiment_score = float(blob.sentiment.polarity)
                    sentiment_label = (
                        "positive" if sentiment_score > 0.1
                        else "negative" if sentiment_score < -0.1
                        else "neutral"
                    )
                except Exception:
                    sentiment_score = None
                    sentiment_label = None

                try:
                    stopwords = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for"}
                    filtered = [w.lower() for w in words if w.lower() not in stopwords and len(w) > 3]
                    keywords = [w for w, _ in Counter(filtered).most_common(10)]
                except Exception:
                    keywords = []

                results.append({
                    "path": str(row["path"]),
                    "file_name": str(row["file_name"]),
                    "file_extension": str(row["file_extension"]),
                    "file_size_bytes": int(row["file_size_bytes"]),
                    "encoding": encoding,
                    "line_count": int(line_count),
                    "word_count": int(word_count),
                    "char_count": int(char_count),
                    "text_content": text if len(text) < 1024 * 1024 else None,
                    "text_preview": text_preview,
                    "detected_language": detected_language,
                    "sentiment_score": sentiment_score,
                    "sentiment_label": sentiment_label,
                    "keywords": keywords,
                    "is_corrupted": False,
                    "error_message": None,
                    "processing_status": "success",
                    "bronze_path": str(row["path"]),
                })
            except Exception as e:
                logger.warning(f"   Failed to process {row.get('file_name', 'unknown')}: {e}")
                results.append({
                    "path": str(row["path"]),
                    "file_name": str(row["file_name"]),
                    "file_extension": str(row["file_extension"]),
                    "file_size_bytes": int(row["file_size_bytes"]),
                    "encoding": None, "line_count": None, "word_count": None,
                    "char_count": None, "text_content": None, "text_preview": None,
                    "detected_language": None, "sentiment_score": None,
                    "sentiment_label": None, "keywords": [],
                    "is_corrupted": True, "error_message": str(e),
                    "processing_status": "failed",
                    "bronze_path": str(row["path"]),
                })

        logger.info("✅ Text analysis completed")
        return results

    def _apply_pdf_transforms(self, files_data: List[Dict], transforms: Dict[str, Any]) -> List[Dict]:
        """Apply PDF transformations with text extraction.

        Accepts List[Dict] (plain Python, no Spark) and returns List[Dict].
        """
        logger.info("📑 Applying PDF transformations with text extraction...")
        logger.info(f"   Processing {len(files_data)} PDF files locally...")

        results = []
        for row in files_data:
            try:
                import re
                from collections import Counter
                import pdfplumber  # type: ignore

                with pdfplumber.open(io.BytesIO(row["content"])) as pdf:
                    metadata = pdf.metadata or {}
                    page_count = len(pdf.pages)
                    author = metadata.get("/Author") or metadata.get("Author")
                    creator = metadata.get("/Creator") or metadata.get("Creator")
                    pdf_version = f"PDF {metadata.get('/Version', 'Unknown')}"
                    full_text = "\n".join(
                        (page.extract_text() or "") for page in pdf.pages
                    )
                    has_images = any(len(page.images) > 0 for page in pdf.pages)
                    has_tables = any(bool(page.extract_tables()) for page in pdf.pages)

                text_preview = full_text[:1000]
                words = re.findall(r"\w+", full_text)
                word_count = len(words)

                try:
                    from langdetect import detect  # type: ignore
                    detected_language = detect(full_text[:1000]) if full_text else None
                except Exception:
                    detected_language = None

                try:
                    stopwords = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for"}
                    filtered = [w.lower() for w in words if w.lower() not in stopwords and len(w) > 3]
                    keywords = [w for w, _ in Counter(filtered).most_common(10)]
                except Exception:
                    keywords = []

                results.append({
                    "path": str(row["path"]),
                    "file_name": str(row["file_name"]),
                    "file_extension": str(row["file_extension"]),
                    "file_size_bytes": int(row["file_size_bytes"]),
                    "page_count": int(page_count),
                    "author": str(author) if author else None,
                    "creator": str(creator) if creator else None,
                    "pdf_version": str(pdf_version),
                    "extracted_text": full_text if len(full_text) < 1024 * 1024 else None,
                    "text_preview": text_preview,
                    "has_images": bool(has_images),
                    "has_tables": bool(has_tables),
                    "word_count": int(word_count),
                    "detected_language": detected_language,
                    "keywords": keywords,
                    "is_corrupted": False,
                    "ocr_applied": False,
                    "error_message": None,
                    "processing_status": "success",
                    "bronze_path": str(row["path"]),
                })
            except Exception as e:
                logger.warning(f"   Failed to process {row.get('file_name', 'unknown')}: {e}")
                results.append({
                    "path": str(row["path"]),
                    "file_name": str(row["file_name"]),
                    "file_extension": str(row["file_extension"]),
                    "file_size_bytes": int(row["file_size_bytes"]),
                    "page_count": None, "author": None, "creator": None,
                    "pdf_version": None, "extracted_text": None, "text_preview": None,
                    "has_images": None, "has_tables": None, "word_count": None,
                    "detected_language": None, "keywords": [],
                    "is_corrupted": True, "ocr_applied": False, "error_message": str(e),
                    "processing_status": "failed",
                    "bronze_path": str(row["path"]),
                })

        logger.info("✅ PDF analysis completed")
        return results

    def _write_unstructured_to_silver(
        self,
        rows: List[Dict],
        source: str,
        entity: str,
        unstructured_type: str,
    ) -> str:
        """Write extracted metadata to MinIO Silver bucket as Parquet.

        Uses pyarrow directly — no Spark, no pandas, no JVM.

        The unstructured binary files themselves stay in Bronze.
        Silver only holds the metadata table (dimensions, duration, etc.)
        so dashboards can query it without touching the raw files.

        Returns the MinIO path where the Parquet was written.
        """
        import io as _io
        import pyarrow as pa
        import pyarrow.parquet as pq
        from minio import Minio  # type: ignore

        silver_path = f"syniqai-silver/unstructured/{source}/{entity}/"
        object_name = f"unstructured/{source}/{entity}/metadata.parquet"

        logger.info(f"💾 Writing {len(rows)} metadata rows → MinIO {silver_path}")

        # Build pyarrow table from the list of dicts.
        # pyarrow infers types column-by-column; all-None columns become null type
        # which is perfectly fine for Parquet.
        table = pa.Table.from_pydict(
            {key: [row.get(key) for row in rows] for key in rows[0].keys()}
        )

        # Serialise to an in-memory buffer then upload
        buf = _io.BytesIO()
        pq.write_table(table, buf, compression="snappy")
        buf.seek(0)
        parquet_bytes = buf.getvalue()

        # Upload to MinIO Silver bucket
        minio_cfg = self.minio_config or {}
        endpoint = (
            minio_cfg.get("endpoint", "http://localhost:9000")
            .replace("http://", "")
            .replace("https://", "")
        )
        secure = minio_cfg.get("endpoint", "http://localhost:9000").startswith("https://")
        minio_client = Minio(
            endpoint=endpoint,
            access_key=minio_cfg.get("access_key", "admin"),
            secret_key=minio_cfg.get("secret_key", "password123"),
            secure=secure,
        )

        # Ensure the Silver bucket exists
        if not minio_client.bucket_exists("syniqai-silver"):
            minio_client.make_bucket("syniqai-silver")

        minio_client.put_object(
            bucket_name="syniqai-silver",
            object_name=object_name,
            data=_io.BytesIO(parquet_bytes),
            length=len(parquet_bytes),
            content_type="application/octet-stream",
        )

        full_path = f"minio://syniqai-silver/{object_name}"
        logger.info(f"   ✅ Written {len(rows)} rows as Parquet → {full_path}")
        return full_path

    
    def _read_bronze(
        self,
        source: str,
        entity: str,
        domain: str,
        execution_mode: str,
        watermark_column: Optional[str],
        watermark_value: Optional[str]
    ) -> DataFrame:
        """Read data from Bronze layer"""
        # MinIO path structure: syniqai-bronze/{domain}/{source_type}/{entity}/
        # source = source_type (postgres, s3, mariadb, etc.)
        bronze_path = f"s3a://syniqai-bronze/{domain}/{source}/{entity}/"
        
        logger.info(f"📖 Reading from Bronze: {bronze_path}")
        
        try:
            # Use pathGlobFilter to only read .parquet files, exclude _metadata.json
            df = self.spark.read \
                .option("pathGlobFilter", "*.parquet") \
                .option("recursiveFileLookup", "true") \
                .parquet(bronze_path)
            
            # Apply incremental filter if specified
            if execution_mode == "incremental" and watermark_column and watermark_value:
                logger.info(f"   Filtering: {watermark_column} > {watermark_value}")
                df = df.filter(col(watermark_column) > watermark_value)
            
            return df
            
        except Exception as e:
            logger.error(f"Failed to read Bronze data: {e}")
            raise
    
    def _apply_quality_rules(
        self,
        df: DataFrame,
        source: str,
        entity: str,
        rules: List[Dict[str, Any]]
    ) -> Tuple[DataFrame, Optional[DataFrame], Dict[str, Any]]:
        """
        Apply data quality rules and separate quarantine records
        
        Returns:
            (clean_df, quarantine_df, metrics)
        """
        initial_count = df.count()
        quality_metrics = {
            "completeness": 100.0,
            "conformity": 100.0,
            "uniqueness": 100.0,
            "validity": 100.0,
            "rules_passed": 0,
            "rules_failed": 0
        }
        
        if not rules:
            logger.info("   No quality rules specified, skipping validation")
            return df, None, quality_metrics
        
        logger.info(f"🔍 Applying {len(rules)} quality rules...")
        
        # Add quality flags column
        df = df.withColumn("_quality_flags", lit(""))
        df = df.withColumn("_should_quarantine", lit(False))
        
        for rule in rules:
            rule_id = rule.get('id') or rule.get('rule_id')
            rule_name = rule.get('name') or rule.get('rule_name')
            rule_type = rule.get('type') or rule.get('rule_type')
            condition = rule.get('condition') or rule.get('condition_expression')
            action = rule.get('action', 'pass')
            
            logger.info(f"   Applying rule: {rule_name} ({rule_type})")
            
            try:
                # Evaluate rule condition
                if rule_type == 'not_null':
                    column_name = rule.get('column') or rule.get('target_column')
                    failed_condition = col(column_name).isNull()
                    
                elif rule_type == 'valid_range':
                    column_name = rule.get('column') or rule.get('target_column')
                    min_val = rule.get('min_value', float('-inf'))
                    max_val = rule.get('max_value', float('inf'))
                    failed_condition = ~((col(column_name) >= min_val) & (col(column_name) <= max_val))
                    
                elif rule_type == 'regex_match':
                    column_name = rule.get('column') or rule.get('target_column')
                    pattern = rule.get('pattern')
                    failed_condition = ~col(column_name).rlike(pattern)
                    
                elif rule_type == 'custom_sql':
                    # Custom SQL condition (must return boolean)
                    failed_condition = ~self.spark.sql(condition)
                    
                else:
                    logger.warning(f"   Unknown rule type: {rule_type}, skipping")
                    continue
                
                # Mark rows that fail this rule
                df = df.withColumn(
                    "_quality_flags",
                    when(failed_condition, concat_ws(",", col("_quality_flags"), lit(rule_id)))
                    .otherwise(col("_quality_flags"))
                )
                
                # Mark for quarantine if action is 'quarantine' or 'reject'
                if action in ['quarantine', 'reject']:
                    df = df.withColumn(
                        "_should_quarantine",
                        when(failed_condition, lit(True)).otherwise(col("_should_quarantine"))
                    )
                    
                # Update metrics
                failed_count = df.filter(failed_condition).count()
                if failed_count > 0:
                    quality_metrics['rules_failed'] += 1
                else:
                    quality_metrics['rules_passed'] += 1
                    
            except Exception as e:
                logger.error(f"   Failed to apply rule {rule_name}: {e}")
                continue
        
        # Separate quarantine records
        quarantine_df = df.filter(col("_should_quarantine") == True)
        clean_df = df.filter(col("_should_quarantine") == False)
        
        # Calculate quality metrics
        final_count = clean_df.count()
        quarantine_count = quarantine_df.count()
        
        if initial_count > 0:
            quality_metrics['completeness'] = (final_count / initial_count) * 100
            quality_metrics['conformity'] = ((initial_count - quarantine_count) / initial_count) * 100
        
        logger.info(f"   ✅ Quality rules applied: {quality_metrics['rules_passed']} passed, {quality_metrics['rules_failed']} failed")
        
        return clean_df, quarantine_df, quality_metrics
    
    def _apply_custom_sql(
        self,
        df: DataFrame,
        custom_sql: str,
        source: str,
        entity: str
    ) -> DataFrame:
        """Apply custom SQL transformation"""
        logger.info("🔧 Applying custom SQL transformation...")
        
        try:
            # Register DataFrame as temp view
            temp_table = f"{source}_{entity}_temp"
            df.createOrReplaceTempView(temp_table)
            
            # Execute custom SQL
            result_df = self.spark.sql(custom_sql)
            
            logger.info(f"   ✅ Custom SQL applied successfully")
            return result_df
            
        except Exception as e:
            logger.error(f"Custom SQL failed: {e}")
            logger.warning("Continuing with original DataFrame")
            return df
    
    def _remove_duplicates(self, df: DataFrame) -> Tuple[DataFrame, int]:
        """Remove duplicate rows"""
        initial_count = df.count()
        
        # Remove duplicates (keep first occurrence)
        dedup_df = df.dropDuplicates()
        
        final_count = dedup_df.count()
        duplicates_removed = initial_count - final_count
        
        if duplicates_removed > 0:
            logger.info(f"♻️  Removed {duplicates_removed:,} duplicate rows")
        
        return dedup_df, duplicates_removed
    
    def _standardize_data(self, df: DataFrame) -> DataFrame:
        """Standardize data types and formats"""
        logger.info("🔄 Standardizing data formats...")
        
        # Trim string columns
        string_columns = [field.name for field in df.schema.fields if isinstance(field.dataType, StringType)]
        for col_name in string_columns:
            df = df.withColumn(col_name, trim(col(col_name)))
        
        # Handle nulls in numeric columns (fill with 0 or appropriate default)
        numeric_types = (IntegerType, DoubleType)
        numeric_columns = [field.name for field in df.schema.fields if isinstance(field.dataType, numeric_types)]
        for col_name in numeric_columns:
            df = df.withColumn(col_name, coalesce(col(col_name), lit(0)))
        
        # Parse and standardize timestamp columns
        timestamp_columns = [field.name for field in df.schema.fields 
                            if 'date' in field.name.lower() or 'time' in field.name.lower()]
        for col_name in timestamp_columns:
            if col_name in [f.name for f in df.schema.fields]:
                try:
                    df = df.withColumn(col_name, to_timestamp(col(col_name)))
                except:
                    pass
        
        return df
    
    def _add_metadata_columns(
        self,
        df: DataFrame,
        source: str,
        entity: str,
        job_id: str
    ) -> DataFrame:
        """Add metadata columns for tracking"""
        return df \
            .withColumn("_source_system", lit(source)) \
            .withColumn("_entity_name", lit(entity)) \
            .withColumn("_ingestion_timestamp", current_timestamp()) \
            .withColumn("_job_id", lit(job_id)) \
            .withColumn("_record_hash", md5(concat_ws("||", *df.columns)))
    
    def _write_to_silver(
        self,
        df: DataFrame,
        source: str,
        entity: str,
        execution_mode: str,
        watermark_column: Optional[str]
    ) -> str:
        """Write data to Silver as Iceberg table"""
        table_name = f"{self.catalog_name}.{source}.{entity}"
        
        logger.info(f"💾 Writing to Silver: {table_name}")
        
        try:
            # Ensure namespace (database) exists
            namespace = f"{self.catalog_name}.{source}"
            try:
                self.spark.sql(f"CREATE NAMESPACE IF NOT EXISTS {namespace}")
                logger.info(f"   ✅ Namespace ensured: {namespace}")
            except Exception as e:
                logger.warning(f"Could not create namespace {namespace}: {e}")
            
            if execution_mode == "full":
                # Full refresh: createOrReplace
                df.writeTo(table_name) \
                    .using("iceberg") \
                    .tableProperty("write.format.default", "parquet") \
                    .tableProperty("write.parquet.compression-codec", "snappy") \
                    .createOrReplace()
                
                logger.info(f"   ✅ Created/replaced Iceberg table")
                
            else:
                # Incremental: append or merge
                df.writeTo(table_name) \
                    .using("iceberg") \
                    .append()
                
                logger.info(f"   ✅ Appended to Iceberg table")
            
            return table_name
            
        except Exception as e:
            logger.error(f"Failed to write to Silver: {e}")
            raise
    
    def _write_quarantine(
        self,
        quarantine_df: DataFrame,
        source: str,
        entity: str,
        job_id: str
    ):
        """Write quarantined records to separate location"""
        quarantine_path = f"s3a://{self.quarantine_bucket}/quarantine/{source}/{entity}/{job_id}/"
        
        logger.info(f"🚨 Writing quarantine data: {quarantine_path}")
        
        try:
            # Add quarantine metadata
            quarantine_df = quarantine_df \
                .withColumn("_quarantine_timestamp", current_timestamp()) \
                .withColumn("_quarantine_job_id", lit(job_id))
            
            # Write as Parquet
            quarantine_df.write \
                .mode("overwrite") \
                .parquet(quarantine_path)
            
            count = quarantine_df.count()
            logger.info(f"   ✅ Wrote {count:,} quarantine records")
            
        except Exception as e:
            logger.error(f"Failed to write quarantine data: {e}")
    
    def _get_max_watermark(self, df: DataFrame, watermark_column: str) -> Optional[str]:
        """Get maximum watermark value from DataFrame"""
        try:
            max_val = df.agg({watermark_column: "max"}).collect()[0][0]
            return str(max_val) if max_val else None
        except:
            return None
    
    def query_silver_table(
        self,
        source: str,
        entity: str,
        limit: int = 100,
        filters: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """
        Query Silver Iceberg table
        
        Args:
            source: Source system
            entity: Entity name
            limit: Maximum rows to return
            filters: Optional filters to apply
        
        Returns:
            List of records as dictionaries
        """
        table_name = f"{self.catalog_name}.{source}.{entity}"
        
        try:
            df = self.spark.table(table_name)
            
            # Apply filters
            if filters:
                for col_name, value in filters.items():
                    df = df.filter(col(col_name) == value)
            
            # Limit and collect
            records = df.limit(limit).toPandas().to_dict('records')
            return records
            
        except Exception as e:
            logger.error(f"Failed to query Silver table: {e}")
            return []
    
    def get_table_stats(self, source: str, entity: str) -> Dict[str, Any]:
        """Get statistics for Silver table"""
        table_name = f"{self.catalog_name}.{source}.{entity}"
        
        try:
            df = self.spark.table(table_name)
            
            stats = {
                "row_count": df.count(),
                "column_count": len(df.columns),
                "columns": df.columns,
                "schema": str(df.schema)
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get table stats: {e}")
            return {}
    
    def cleanup(self):
        """Cleanup resources"""
        if self.spark:
            self.spark.stop()
            logger.info("🛑 Spark session stopped")


# Convenience function for direct usage
def transform_to_silver_spark(
    source: str,
    entity: str,
    domain: str = "general",
    execution_mode: str = "full",
    rules: List[Dict[str, Any]] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Convenience function to transform Bronze → Silver using Spark
    
    Args:
        source: Source system name
        entity: Entity/table name
        domain: Domain for rule filtering
        execution_mode: 'full' or 'incremental'
        rules: List of quality rules
        **kwargs: Additional arguments (watermark_column, watermark_value, custom_sql)
    
    Returns:
        Transformation result dictionary
    """
    transformer = SilverTransformerSpark()
    
    try:
        result = transformer.transform(
            source=source,
            entity=entity,
            domain=domain,
            execution_mode=execution_mode,
            rules=rules,
            **kwargs
        )
        return result
    finally:
        transformer.cleanup()


if __name__ == "__main__":
    # Test the Spark transformer
    logger.info("🧪 Testing SilverTransformerSpark...")
    
    transformer = SilverTransformerSpark()
    
    # Example: Transform a Bronze table
    result = transformer.transform(
        source="postgres",
        entity="customers",
        domain="finance",
        execution_mode="full",
        rules=[
            {
                "id": "COMP-001",
                "name": "Customer ID Not Null",
                "type": "not_null",
                "column": "customer_id",
                "action": "quarantine"
            }
        ]
    )
    
    print(json.dumps(result, indent=2))
    
    transformer.cleanup()
