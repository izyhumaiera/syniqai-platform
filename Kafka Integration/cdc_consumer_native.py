"""
Native CDC Consumer for Non-Docker Setup
Monitors Kafka topics and provides status for the GUI
"""

import os
import sys
from pathlib import Path
import time
import logging
from datetime import datetime
from kafka import KafkaConsumer, KafkaAdminClient
from kafka.errors import NoBrokersAvailable, KafkaError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Kafka configuration from environment
KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', '127.0.0.1:9092')

# CDC topic patterns - will auto-discover topics matching these patterns
CDC_TOPIC_PATTERNS = [
    'cdc_',      # Debezium CDC topics (e.g., cdc_postgres.public.table)
    'client.',   # Client CDC topics (e.g., client.public.table)
    'bronze-',   # Bronze layer topics
    'silver-',   # Silver layer topics
]

def discover_cdc_topics(bootstrap_servers):
    """Auto-discover CDC topics from Kafka"""
    try:
        admin_client = KafkaAdminClient(
            bootstrap_servers=bootstrap_servers,
            request_timeout_ms=5000,
            api_version_auto_timeout_ms=5000
        )
        all_topics = admin_client.list_topics()
        admin_client.close()
        
        # Filter topics matching CDC patterns
        cdc_topics = []
        for topic in all_topics:
            for pattern in CDC_TOPIC_PATTERNS:
                if topic.startswith(pattern):
                    cdc_topics.append(topic)
                    break
        
        return cdc_topics
    except Exception as e:
        logger.warning(f"Could not auto-discover topics: {e}")
        # Fallback to default topics
        return ['bronze-ready', 'silver-ready']

class NativeCDCConsumer:
    """
    Native CDC Consumer for monitoring Kafka topics.
    Provides status information for the GUI without requiring Docker.
    """
    
    def __init__(self, bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS):
        self.bootstrap_servers = bootstrap_servers
        self.running = False
        self.messages_processed = 0
        self.start_time = datetime.now()
        self.consumer = None
        self.cdc_topics = []  # Will be populated in connect()
        
    def connect(self):
        """Connect to Kafka and subscribe to CDC topics"""
        try:
            logger.info(f"[CONNECT] Connecting to Kafka at {self.bootstrap_servers}...")
            
            # Test connection first
            admin_client = KafkaAdminClient(
                bootstrap_servers=self.bootstrap_servers,
                request_timeout_ms=10000,
                api_version_auto_timeout_ms=10000
            )
            
            # List topics to verify connection
            topics = admin_client.list_topics()
            logger.info(f"[OK] Connected! Found {len(topics)} topics")
            admin_client.close()
            
            # Auto-discover CDC topics
            cdc_topics = discover_cdc_topics(self.bootstrap_servers)
            if not cdc_topics:
                logger.warning("[WARNING] No CDC topics found! Using fallback topics.")
                cdc_topics = ['bronze-ready', 'silver-ready']
            
            logger.info(f"[TOPICS] Found {len(cdc_topics)} CDC topics to monitor:")
            for topic in cdc_topics:
                logger.info(f"   - {topic}")
            
            # Create consumer
            self.consumer = KafkaConsumer(
                *cdc_topics,
                bootstrap_servers=self.bootstrap_servers,
                group_id='native-cdc-monitor',
                auto_offset_reset='latest',
                enable_auto_commit=True,
                value_deserializer=lambda m: m.decode('utf-8') if m else None
            )
            
            self.running = True
            self.cdc_topics = cdc_topics  # Store for status reporting
            logger.info(f"[OK] CDC Consumer started")
            
            return True
            
        except NoBrokersAvailable:
            logger.error("[ERROR] NoBrokersAvailable: Kafka broker not accessible")
            logger.error(f"   Tried connecting to: {self.bootstrap_servers}")
            logger.error("   Make sure Kafka is running on port 9092")
            return False
        except Exception as e:
            logger.error(f"[ERROR] Connection failed: {e}")
            return False
    
    def run(self):
        """Run the consumer loop"""
        if not self.connect():
            logger.error("[ERROR] Failed to connect. Exiting.")
            return
        
        logger.info("[LISTENING] Listening for CDC messages...")
        logger.info("   Press Ctrl+C to stop\n")
        
        try:
            for message in self.consumer:
                self.messages_processed += 1
                
                logger.info(f"[MESSAGE] [{message.topic}] Offset: {message.offset}")
                logger.info(f"   Partition: {message.partition}")
                logger.info(f"   Value: {message.value[:100] if message.value else None}...")
                logger.info(f"   Total processed: {self.messages_processed}\n")
                
        except KeyboardInterrupt:
            logger.info("\n[STOP] Stopping CDC consumer...")
        except Exception as e:
            logger.error(f"[ERROR] Error in consumer loop: {e}")
        finally:
            if self.consumer:
                self.consumer.close()
            self.running = False
            uptime = (datetime.now() - self.start_time).total_seconds()
            logger.info(f"\n[STATS] Final Stats:")
            logger.info(f"   Messages processed: {self.messages_processed}")
            logger.info(f"   Uptime: {uptime:.1f} seconds")
            logger.info("[STOPPED] CDC Consumer stopped")
    
    def get_status(self):
        """Get current status for API"""
        uptime = (datetime.now() - self.start_time).total_seconds()
        return {
            "running": self.running,
            "uptime_seconds": uptime,
            "messages_processed": self.messages_processed,
            "started_at": self.start_time.isoformat(),
            "topics": self.cdc_topics if hasattr(self, 'cdc_topics') else [],
            "type": "native"
        }


def main():
    """Main entry point"""
    print("=" * 60)
    print("Native CDC Consumer (Non-Docker)")
    print("=" * 60)
    print(f"Kafka: {KAFKA_BOOTSTRAP_SERVERS}")
    print(f"Auto-discovering CDC topics...")
    print("=" * 60)
    print()
    
    consumer = NativeCDCConsumer()
    consumer.run()


if __name__ == "__main__":
    main()
