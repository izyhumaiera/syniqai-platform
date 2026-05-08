"""
CDC to Silver Layer Processing Service
Processes structured CDC data from Kafka topics to MinIO Silver layer
Dynamically reads configuration - NO HARDCODED VALUES
Aligned with Bronze→Silver pipeline using same transformers and quality gates
"""

import os
import sys
import json
import logging
import pandas as pd
import threading
from pathlib import Path
from typing import Dict, Optional, List
from datetime import datetime
from kafka import KafkaConsumer, KafkaAdminClient
from kafka.errors import KafkaError
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_path)

# Import MinIO client and job tracker
from minio_utils import MinIOClient
from silver_job_tracker import SilverJobTracker

# Import SilverTransformer and QualityGate (same as bronze→silver pipeline)
lakehouse_path = Path(__file__).parent.parent.parent / "data lakehouse" / "syniq_project"
sys.path.insert(0, str(lakehouse_path))

try:
    from silver_transformer import SilverTransformer
    from silver_quality_gate import SilverQualityGate
    SILVER_TRANSFORMER_AVAILABLE = True
    logger = logging.getLogger(__name__)
    logger.info("✓ SilverTransformer and QualityGate loaded for CDC pipeline")
except ImportError as e:
    logger = logging.getLogger(__name__)
    logger.warning(f"⚠ Silver transformer not available: {e}")
    SilverTransformer = None
    SilverQualityGate = None
    SILVER_TRANSFORMER_AVAILABLE = False

class CDCToSilverService:
    """
    Service for processing CDC messages from Kafka to Silver layer.
    Auto-discovers CDC topics and processes structured data.
    """
    
    def __init__(self, minio_client: MinIOClient, job_tracker: SilverJobTracker):
        """
        Initialize CDC to Silver service.
        Uses same transformer and quality gates as Bronze→Silver pipeline.
        
        Args:
            minio_client: MinIO client for storage
            job_tracker: Job tracker for monitoring
        """
        self.minio = minio_client
        self.job_tracker = job_tracker
        self.bootstrap_servers = os.getenv('KAFKA_BOOTSTRAP_SERVERS', '127.0.0.1:9092')
        self.silver_bucket = os.getenv('MINIO_SILVER_BUCKET', 'syniqai-silver')
        self.running = False
        self.consumer_threads = {}
        
        # Initialize SilverTransformer with same config as Bronze→Silver pipeline
        config_path = lakehouse_path / "config" / "cleaning_rules.yaml"
        if SILVER_TRANSFORMER_AVAILABLE and config_path.exists():
            self.transformer = SilverTransformer(str(config_path))
            logger.info(f"✓ CDC Silver: Initialized with cleaning_rules.yaml")
        else:
            self.transformer = None
            logger.warning("⚠ CDC Silver: Using basic transformations (transformer not available)")
        
        logger.info(f"Initialized CDCToSilverService - Kafka: {self.bootstrap_servers}, Bucket: {self.silver_bucket}")
    
    def discover_cdc_topics(self) -> List[str]:
        """
        Auto-discover CDC topics from Kafka.
        Filters for structured data topics only.
        
        Returns:
            List of CDC topic names
        """
        try:
            admin_client = KafkaAdminClient(
                bootstrap_servers=self.bootstrap_servers,
                request_timeout_ms=5000
            )
            all_topics = admin_client.list_topics()
            admin_client.close()
            
            # Filter for CDC topics (structured data only)
            # Patterns: cdc_*, client.*, cdc.*
            cdc_patterns = ['cdc_', 'client.', 'cdc.']
            cdc_topics = []
            
            for topic in all_topics:
                for pattern in cdc_patterns:
                    if topic.startswith(pattern):
                        # Exclude unstructured data topics (image, audio, video, document)
                        if not any(x in topic.lower() for x in ['image', 'audio', 'video', 'document', 'media']):
                            cdc_topics.append(topic)
                            break
            
            logger.info(f"Discovered {len(cdc_topics)} structured CDC topics: {cdc_topics}")
            return cdc_topics
            
        except Exception as e:
            logger.error(f"Failed to discover CDC topics: {e}")
            return []
    
    def get_table_info_from_topic(self, topic_name: str) -> Dict:
        """
        Extract database and table information from CDC topic name.
        
        Supports formats:
        - cdc_postgres.public.table_name
        - client.public.table_name
        - cdc.database.schema.table_name
        
        Args:
            topic_name: Kafka topic name
            
        Returns:
            Dict with database, schema, table info
        """
        parts = topic_name.split('.')
        
        if len(parts) >= 3:
            # Format: prefix.schema.table or database.schema.table
            return {
                'source': parts[0].replace('cdc_', '').replace('client', 'postgres'),
                'schema': parts[1] if len(parts) > 2 else 'public',
                'table': parts[-1],
                'full_name': '.'.join(parts[1:])  # schema.table
            }
        elif len(parts) == 2:
            return {
                'source': parts[0].replace('cdc_', ''),
                'schema': 'public',
                'table': parts[1],
                'full_name': parts[1]
            }
        else:
            return {
                'source': 'unknown',
                'schema': 'public',
                'table': topic_name,
                'full_name': topic_name
            }
    
    def start_cdc_to_silver_stream(self, topic: str = None) -> str:
        """
        Start streaming CDC data to Silver layer.
        
        Args:
            topic: Specific topic to stream (None = all discovered topics)
            
        Returns:
            job_id for tracking
        """
        # Discover topics if not specified
        topics_to_process = [topic] if topic else self.discover_cdc_topics()
        
        if not topics_to_process:
            logger.warning("No CDC topics found to process")
            return None
        
        # Create job ID
        job_id = f"cdc_silver_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Start consumer thread for each topic
        for cdc_topic in topics_to_process:
            if cdc_topic not in self.consumer_threads or not self.consumer_threads[cdc_topic].is_alive():
                thread = threading.Thread(
                    target=self._consume_and_process,
                    args=(cdc_topic, job_id),
                    daemon=True
                )
                thread.start()
                self.consumer_threads[cdc_topic] = thread
                logger.info(f"Started CDC consumer for topic: {cdc_topic}")
        
        self.running = True
        return job_id
    
    def _consume_and_process(self, topic: str, job_id: str):
        """
        Consume CDC messages from a topic and process to Silver.
        
        Args:
            topic: Kafka topic name
            job_id: Job ID for tracking
        """
        try:
            # Get table info from topic name
            table_info = self.get_table_info_from_topic(topic)
            logger.info(f"Processing CDC topic: {topic} -> {table_info}")
            
            # Create Kafka consumer
            consumer = KafkaConsumer(
                topic,
                bootstrap_servers=self.bootstrap_servers,
                auto_offset_reset='latest',  # Only new messages
                enable_auto_commit=True,
                group_id=f'silver_processor_{table_info["table"]}',
                value_deserializer=lambda x: json.loads(x.decode('utf-8')) if x else None
            )
            
            batch = []
            batch_size = 100  # Process in batches for efficiency
            last_process_time = datetime.now()
            
            logger.info(f"[CDC->Silver] Listening for messages on {topic}")
            
            for message in consumer:
                if not self.running:
                    break
                
                if message.value is None:
                    continue
                
                # Parse Debezium CDC message
                cdc_data = self._parse_cdc_message(message.value, table_info)
                
                if cdc_data:
                    batch.append(cdc_data)
                
                # Process batch when size reached or timeout
                time_since_last = (datetime.now() - last_process_time).seconds
                if len(batch) >= batch_size or time_since_last > 30:
                    if batch:
                        self._process_batch_to_silver(batch, table_info, job_id)
                        batch = []
                        last_process_time = datetime.now()
            
            consumer.close()
            
        except Exception as e:
            logger.error(f"Error in CDC consumer for {topic}: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def _parse_cdc_message(self, message: Dict, table_info: Dict) -> Optional[Dict]:
        """
        Parse Debezium CDC message to extract data.
        
        Args:
            message: Raw CDC message from Kafka
            table_info: Table metadata
            
        Returns:
            Parsed data dict or None
        """
        try:
            op = message.get('op')
            
            # Handle different operation types
            if op in ['c', 'r']:  # Create or Read (snapshot)
                return message.get('after')
            elif op == 'u':  # Update
                return message.get('after')
            elif op == 'd':  # Delete
                # Store deleted record with _deleted flag
                data = message.get('before', {})
                data['_deleted'] = True
                data['_deleted_at'] = datetime.now().isoformat()
                return data
            else:
                logger.warning(f"Unknown CDC operation: {op}")
                return None
                
        except Exception as e:
            logger.error(f"Error parsing CDC message: {e}")
            return None
    
    def _process_batch_to_silver(self, batch: List[Dict], table_info: Dict, job_id: str):
        """
        Process a batch of CDC records to Silver layer.
        
        Args:
            batch: List of parsed CDC records
            table_info: Table metadata
            job_id: Job ID for tracking
        """
        try:
            if not batch:
                return
            
            logger.info(f"[CDC->Silver] Processing batch of {len(batch)} records for {table_info['table']}")
            
            # Convert to DataFrame
            df = pd.DataFrame(batch)
            
            # Apply basic transformations
            df = self._apply_silver_transformations(df, table_info)
            
            # Add metadata columns
            df['_ingested_at'] = datetime.now().isoformat()
            df['_source_topic'] = f"{table_info['source']}.{table_info['full_name']}"
            df['_cdc_job_id'] = job_id
            
            # Write to Silver bucket in MinIO
            silver_path = self._write_to_silver(df, table_info)
            
            if silver_path:
                logger.info(f"[CDC->Silver] ✓ Wrote {len(df)} records to Silver: {silver_path}")
            else:
                logger.error(f"[CDC->Silver] Failed to write to Silver")
                
        except Exception as e:
            logger.error(f"Error processing batch to Silver: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def _apply_silver_transformations(self, df: pd.DataFrame, table_info: Dict) -> pd.DataFrame:
        """
        Apply standard Silver layer transformations.
        Uses same SilverTransformer and QualityGate as Bronze→Silver pipeline.
        
        Args:
            df: Input DataFrame
            table_info: Table metadata
            
        Returns:
            Transformed DataFrame with quality metrics
        """
        try:
            original_rows = len(df)
            
            # Create virtual bronze location for lineage tracking
            bronze_location = f"cdc/{table_info['source']}/{table_info['table']}"
            source_system = table_info.get('source', 'postgres')
            
            # Use same SilverTransformer as Bronze→Silver pipeline
            if self.transformer:
                logger.info(f"[CDC Transform] Using SilverTransformer (same as Bronze→Silver)")
                cleaned_df = self.transformer.transform(
                    df,
                    source_system=source_system,
                    bronze_location=bronze_location
                )
                cleaning_summary = self.transformer.get_cleaning_summary()
                logger.info(f"[CDC Transform] Cleaning summary: {cleaning_summary}")
            else:
                # Fallback to basic cleaning
                logger.info(f"[CDC Transform] Using basic transformations")
                cleaned_df = self._basic_cleaning(df)
                cleaning_summary = {"basic_cleaning": True}
            
            # Run quality checks (same as Bronze→Silver pipeline)
            quality_issues = self._run_quality_checks(cleaned_df, original_rows)
            
            # Calculate quality score
            quality_score = self._calculate_quality_score(original_rows, len(cleaned_df), quality_issues)
            cleaned_df['_dq_score'] = quality_score
            
            logger.info(f"[CDC Transform] Processed {original_rows} → {len(cleaned_df)} rows, Quality: {quality_score:.1f}%")
            
            return cleaned_df
            
        except Exception as e:
            logger.error(f"Error applying transformations: {e}")
            import traceback
            logger.error(traceback.format_exc())
            # Return original dataframe with basic score on error
            df['_dq_score'] = 50.0
            return df
    
    def _basic_cleaning(self, df: pd.DataFrame) -> pd.DataFrame:
        """Basic cleaning when transformer is not available (same as silver_service.py)"""
        df = df.drop_duplicates()
        df = df.dropna(how='all')
        # Trim string columns
        for col in df.select_dtypes(include=['object']).columns:
            if col not in ['_deleted', '_deleted_at', '_ingested_at', '_source_topic', '_cdc_job_id']:
                try:
                    df[col] = df[col].str.strip()
                except:
                    pass
        return df
    
    def _run_quality_checks(self, df: pd.DataFrame, original_rows: int) -> List[str]:
        """Run quality checks (same as Bronze→Silver pipeline)"""
        issues = []
        
        try:
            if SilverQualityGate:
                qg = SilverQualityGate(df)
                qg.missing_value_detection()
                qg.duplicate_detection()
                qg.data_volume_check(min_rows=max(1, original_rows // 2))
                issues = qg.issues
            else:
                # Basic checks
                if df.isnull().sum().sum() > 0:
                    issues.append("Missing values detected")
                if df.duplicated().sum() > 0:
                    issues.append("Duplicate rows found")
        except Exception as e:
            logger.error(f"Error in quality checks: {e}")
            issues.append(f"Quality check error: {str(e)}")
        
        return issues
    
    def _calculate_quality_score(self, original_rows: int, cleaned_rows: int, issues: List[str]) -> float:
        """Calculate quality score (same logic as Bronze→Silver pipeline)"""
        score = 100.0
        
        # Penalty for row loss
        if original_rows > 0:
            row_loss_pct = ((original_rows - cleaned_rows) / original_rows) * 100
            score -= min(row_loss_pct, 30)  # Max 30% penalty for row loss
        
        # Penalty for issues
        score -= len(issues) * 5  # 5% penalty per issue
        
        return max(0.0, min(100.0, score))  # Clamp between 0-100
    
    def _write_to_silver(self, df: pd.DataFrame, table_info: Dict) -> Optional[str]:
        """
        Write DataFrame to MinIO Silver bucket.
        Uses same structure as Bronze→Silver pipeline (no hardcoded bucket name).
        
        Args:
            df: DataFrame to write
            table_info: Table metadata
            
        Returns:
            Path to written file or None
        """
        try:
            # Generate unique filename with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{table_info['source']}_{table_info['table']}_{timestamp}.parquet"
            
            # Organize by source/table in Silver bucket (same structure as Bronze→Silver)
            source = table_info['source']
            entity = table_info['table']
            
            # Use MinIO client's write_parquet method (same as bronze→silver pipeline)
            try:
                # Try using the standardized write method if available
                success = self.minio.write_parquet(
                    bucket_name=self.silver_bucket,
                    key_prefix=f"{source}/{entity}",
                    df=df,
                    filename=filename
                )
                silver_key = f"{source}/{entity}/{filename}"
            except AttributeError:
                # Fallback to direct client access
                import io
                buffer = io.BytesIO()
                df.to_parquet(buffer, index=False, engine='pyarrow', compression='snappy')
                buffer.seek(0)
                
                silver_key = f"{source}/{entity}/{filename}"
                self.minio.client.put_object(
                    bucket_name=self.silver_bucket,
                    object_name=silver_key,
                    data=buffer,
                    length=buffer.getbuffer().nbytes,
                    content_type='application/octet-stream'
                )
            
            logger.info(f"[CDC Silver] Uploaded to {self.silver_bucket}: {silver_key}")
            return silver_key
            
        except Exception as e:
            logger.error(f"Error writing to Silver bucket: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def stop_cdc_streams(self):
        """Stop all CDC consumer threads"""
        self.running = False
        logger.info("Stopping all CDC to Silver streams")
    
    def get_active_streams(self) -> List[Dict]:
        """Get list of active CDC streams"""
        active = []
        for topic, thread in self.consumer_threads.items():
            if thread.is_alive():
                table_info = self.get_table_info_from_topic(topic)
                active.append({
                    'topic': topic,
                    'table': table_info['full_name'],
                    'source': table_info['source'],
                    'status': 'active'
                })
        return active


# Singleton instance
_cdc_silver_service = None

def get_cdc_silver_service(minio_client: MinIOClient, job_tracker: SilverJobTracker) -> CDCToSilverService:
    """Get or create CDC to Silver service instance"""
    global _cdc_silver_service
    
    if _cdc_silver_service is None:
        _cdc_silver_service = CDCToSilverService(minio_client, job_tracker)
        logger.info("Created CDCToSilverService singleton")
    
    return _cdc_silver_service
