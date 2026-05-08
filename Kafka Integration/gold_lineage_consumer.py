"""
Gold Lineage Consumer - Block 4
================================
Listens to 'silver-ready' topic and tracks data lineage in PostgreSQL.
Records every Silver processing event and periodically refreshes Gold materialized view.

Features:
- Consumes silver-ready events from Kafka
- Inserts lineage records into gold_lineage table
- Batched materialized view refresh (every 10 inserts)
- Graceful shutdown with commit on exit
- Health monitoring and statistics

Environment Variables Required:
- DATABASE_URL: PostgreSQL connection string
- KAFKA_BOOTSTRAP_SERVERS: Kafka broker address (default: 127.0.0.1:9092)
"""

import os
import json
import time
import signal
import sys
from datetime import datetime
from typing import Dict, Any, Optional
from kafka import KafkaConsumer
import psycopg2
from psycopg2.extras import RealDictCursor

# ============================================================================
# Configuration
# ============================================================================

DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://syniqai_user:syniqai_pass@localhost:5432/syniqai_metadata')
KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', '127.0.0.1:9092')
KAFKA_TOPIC = 'silver-ready'
CONSUMER_GROUP = 'gold-lineage-consumer'
BATCH_SIZE = 10  # Refresh materialized view every N inserts
AUTO_COMMIT_INTERVAL = 5000  # Kafka consumer auto-commit interval in ms

# ============================================================================
# Global State
# ============================================================================

running = True
stats = {
    'total_processed': 0,
    'total_lineage_inserts': 0,
    'total_refreshes': 0,
    'errors': 0,
    'started_at': datetime.now()
}

# ============================================================================
# Signal Handlers
# ============================================================================

def signal_handler(sig, frame):
    """Handle graceful shutdown on CTRL+C"""
    global running
    print("\n\n🛑 Shutdown signal received. Gracefully stopping...")
    running = False

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# ============================================================================
# Database Functions
# ============================================================================

def get_db_connection():
    """Create PostgreSQL connection"""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        raise

def insert_lineage_event(
    conn,
    asset_id: str,
    event_type: str,
    model_used: Optional[str] = None,
    quality_score: Optional[float] = None,
    source_bucket: Optional[str] = None,
    dest_bucket: Optional[str] = None,
    metadata: Optional[Dict] = None
) -> Optional[str]:
    """Insert a lineage event into gold_lineage table"""
    try:
        cursor = conn.cursor()
        
        # Use the stored function for validation
        cursor.execute("""
            SELECT insert_lineage_event(
                %s::UUID,  -- asset_id
                %s,        -- event_type
                %s,        -- model_used
                %s,        -- quality_score
                %s,        -- source_bucket
                %s,        -- dest_bucket
                %s::JSONB  -- metadata
            )
        """, (
            asset_id,
            event_type,
            model_used,
            quality_score,
            source_bucket,
            dest_bucket,
            json.dumps(metadata) if metadata else None
        ))
        
        lineage_id = cursor.fetchone()[0]
        conn.commit()
        cursor.close()
        
        return str(lineage_id)
        
    except Exception as e:
        print(f"❌ Failed to insert lineage event: {e}")
        conn.rollback()
        return None

def refresh_gold_view(conn) -> Dict[str, Any]:
    """Refresh gold_assets materialized view"""
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        print("🔄 Refreshing Gold materialized view...")
        start_time = time.time()
        
        # Use the stored function for refresh
        cursor.execute("SELECT * FROM refresh_gold_view()")
        result = cursor.fetchone()
        
        conn.commit()
        cursor.close()
        
        duration = time.time() - start_time
        
        print(f"✅ Gold view refreshed in {duration:.2f}s")
        print(f"   📊 Total assets: {result['total_assets']}")
        print(f"   ➕ New assets: {result['new_assets']}")
        
        return dict(result)
        
    except Exception as e:
        print(f"❌ Failed to refresh Gold view: {e}")
        conn.rollback()
        return {}

def get_asset_metadata(conn, asset_id: str) -> Optional[Dict]:
    """Fetch asset metadata from silver_assets"""
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
            SELECT
                id,
                file_type,
                source,
                ai_model_used,
                ai_confidence_score,
                silver_minio_key,
                bronze_minio_key
            FROM silver_assets
            WHERE id = %s::UUID
        """, (asset_id,))
        
        result = cursor.fetchone()
        cursor.close()
        
        return dict(result) if result else None
        
    except Exception as e:
        print(f"⚠️  Failed to fetch asset metadata: {e}")
        return None

# ============================================================================
# Message Processing
# ============================================================================

def process_silver_ready_event(conn, message: Dict[str, Any]) -> bool:
    """
    Process a silver-ready event and create lineage record
    
    Expected message format:
    {
        "asset_id": "uuid",
        "file_type": "pdf/image/audio",
        "source": "s3/mongodb",
        "ai_model_used": "model-name",
        "ai_confidence_score": 0.95,
        "silver_path": "syniqai-silver/...",
        "bronze_path": "syniqai-bronze/...",
        "status": "success/failed"
    }
    """
    try:
        asset_id = message.get('asset_id')
        if not asset_id:
            print("⚠️  Missing asset_id in message")
            return False
        
        # Fetch additional metadata from database if needed
        asset_data = get_asset_metadata(conn, asset_id)
        if not asset_data:
            print(f"⚠️  Asset {asset_id} not found in database")
            return False
        
        # Extract event details
        model_used = message.get('ai_model_used') or asset_data.get('ai_model_used')
        quality_score = message.get('ai_confidence_score') or asset_data.get('ai_confidence_score')
        silver_path = message.get('silver_path') or asset_data.get('silver_minio_key')
        bronze_path = message.get('bronze_path') or asset_data.get('bronze_minio_key')
        
        # Determine event type based on status
        status = message.get('status', 'success')
        event_type = 'silver_processed' if status == 'success' else 'silver_failed'
        
        # Build metadata
        metadata = {
            'file_type': asset_data.get('file_type'),
            'source': asset_data.get('source'),
            'status': status,
            'processing_time': message.get('processing_time'),
            'error': message.get('error')
        }
        
        # Insert lineage event
        lineage_id = insert_lineage_event(
            conn=conn,
            asset_id=asset_id,
            event_type=event_type,
            model_used=model_used,
            quality_score=quality_score,
            source_bucket='syniqai-silver/',
            dest_bucket='syniqai-gold/',
            metadata=metadata
        )
        
        if lineage_id:
            stats['total_lineage_inserts'] += 1
            print(f"✅ Lineage event created: {lineage_id[:8]}... for asset {asset_id[:8]}...")
            return True
        else:
            return False
            
    except Exception as e:
        print(f"❌ Error processing message: {e}")
        stats['errors'] += 1
        return False

# ============================================================================
# Main Consumer Loop
# ============================================================================

def print_startup_banner():
    """Print startup information"""
    print("\n" + "="*70)
    print("  🏆 GOLD LINEAGE CONSUMER - Block 4")
    print("="*70)
    print(f"  📍 Kafka Topic: {KAFKA_TOPIC}")
    print(f"  🔌 Kafka Broker: {KAFKA_BOOTSTRAP_SERVERS}")
    print(f"  🗄️  Database: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else 'localhost'}")
    print(f"  👥 Consumer Group: {CONSUMER_GROUP}")
    print(f"  📦 Batch Size: {BATCH_SIZE} (refresh every {BATCH_SIZE} inserts)")
    print("="*70 + "\n")

def print_statistics():
    """Print current statistics"""
    uptime = (datetime.now() - stats['started_at']).total_seconds()
    print("\n" + "-"*70)
    print("📊 STATISTICS")
    print("-"*70)
    print(f"  Uptime:              {uptime:.0f}s")
    print(f"  Messages Processed:  {stats['total_processed']}")
    print(f"  Lineage Inserts:     {stats['total_lineage_inserts']}")
    print(f"  View Refreshes:      {stats['total_refreshes']}")
    print(f"  Errors:              {stats['errors']}")
    print(f"  Success Rate:        {(stats['total_lineage_inserts']/max(stats['total_processed'],1)*100):.1f}%")
    print("-"*70 + "\n")

def main():
    """Main consumer loop"""
    print_startup_banner()
    
    # Connect to database
    print("🔌 Connecting to PostgreSQL...")
    conn = get_db_connection()
    print("✅ Database connected\n")
    
    # Create Kafka consumer
    print("🔌 Connecting to Kafka...")
    consumer = KafkaConsumer(
        KAFKA_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        group_id=CONSUMER_GROUP,
        auto_offset_reset='latest',  # Start from latest (don't replay old messages)
        enable_auto_commit=True,
        auto_commit_interval_ms=AUTO_COMMIT_INTERVAL,
        value_deserializer=lambda m: json.loads(m.decode('utf-8')) if m else None,
        consumer_timeout_ms=1000  # Poll timeout to allow checking 'running' flag
    )
    print(f"✅ Kafka consumer ready (topic: {KAFKA_TOPIC})\n")
    print("👂 Listening for silver-ready events...\n")
    
    # Track batch counter
    batch_counter = 0
    last_stats_time = time.time()
    
    try:
        while running:
            # Poll for messages
            for message in consumer:
                if not running:
                    break
                
                try:
                    event_data = message.value
                    
                    if not event_data:
                        continue
                    
                    stats['total_processed'] += 1
                    
                    print(f"\n📥 Received silver-ready event (offset: {message.offset})")
                    print(f"   Asset: {event_data.get('asset_id', 'unknown')[:8]}...")
                    print(f"   Model: {event_data.get('ai_model_used', 'N/A')}")
                    
                    # Process the event
                    success = process_silver_ready_event(conn, event_data)
                    
                    if success:
                        batch_counter += 1
                        
                        # Check if we need to refresh the materialized view
                        if batch_counter >= BATCH_SIZE:
                            print(f"\n📦 Batch size reached ({BATCH_SIZE}). Triggering refresh...")
                            refresh_gold_view(conn)
                            stats['total_refreshes'] += 1
                            batch_counter = 0
                    
                    # Print stats every 30 seconds
                    if time.time() - last_stats_time > 30:
                        print_statistics()
                        last_stats_time = time.time()
                    
                except Exception as e:
                    print(f"❌ Error processing message: {e}")
                    stats['errors'] += 1
                    continue
            
            # Small sleep to prevent tight loop when no messages
            time.sleep(0.1)
    
    except Exception as e:
        print(f"❌ Fatal error in consumer loop: {e}")
        stats['errors'] += 1
    
    finally:
        # Cleanup on shutdown
        print("\n🧹 Cleaning up...")
        
        # Final refresh if there are pending inserts
        if batch_counter > 0:
            print(f"📦 Final refresh ({batch_counter} pending inserts)...")
            refresh_gold_view(conn)
        
        # Print final statistics
        print_statistics()
        
        # Close connections
        consumer.close()
        conn.close()
        
        print("✅ Gold Lineage Consumer stopped cleanly")
        print("="*70 + "\n")

# ============================================================================
# Entry Point
# ============================================================================

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)
