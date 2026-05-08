"""
Dynamic CDC Connector Setup - Reads from config.json
Creates Debezium connectors without hardcoded values
"""
import json
import requests
import sys
from pathlib import Path

# Configuration paths
CONFIG_FILE = Path(__file__).parent / "data ingestion" / "Connector" / "config.json"
KAFKA_CONNECT_URL = "http://localhost:8083"

def load_database_config():
    """Load database configuration from config.json"""
    if not CONFIG_FILE.exists():
        print(f"❌ Config file not found: {CONFIG_FILE}")
        sys.exit(1)
    
    with open(CONFIG_FILE, 'r') as f:
        config = json.load(f)
    
    return config['connection_config']

def create_connector(db_config, table_name=None, connector_name=None):
    """
    Create Debezium CDC connector dynamically
    
    Args:
        db_config: Database configuration dict (from config.json)
        table_name: Table to monitor (default: from config.json)
        connector_name: Custom connector name (default: auto-generated)
    """
    # Load full config to get table name if not provided
    with open(CONFIG_FILE, 'r') as f:
        full_config = json.load(f)
    
    if table_name is None:
        table_name = full_config['extraction_request']['entity']
    
    if connector_name is None:
        connector_name = f"{db_config['host'].replace('.', '_')}-{db_config['database']}-cdc"
    
    # Generate unique slot and publication names
    slot_name = f"debezium_{connector_name.replace('-', '_')}_slot"
    publication_name = f"dbz_{connector_name.replace('-', '_')}_pub"
    
    # Build connector configuration
    connector_config = {
        "name": connector_name,
        "config": {
            "connector.class": "io.debezium.connector.postgresql.PostgresConnector",
            "database.hostname": db_config['host'],
            "database.port": str(db_config['port']),
            "database.user": db_config['user'],
            "database.password": db_config['password'],
            "database.dbname": db_config['database'],
            "database.server.name": f"server_{db_config['host'].replace('.', '_')}",
            "table.include.list": f"public.{table_name}",
            "plugin.name": "pgoutput",
            "slot.name": slot_name,
            "publication.name": publication_name,
            "snapshot.mode": "always",
            "topic.prefix": f"cdc_{db_config['database']}",
            "key.converter": "org.apache.kafka.connect.json.JsonConverter",
            "value.converter": "org.apache.kafka.connect.json.JsonConverter",
            "key.converter.schemas.enable": "false",
            "value.converter.schemas.enable": "false"
        }
    }
    
    print("\n" + "="*70)
    print("  CREATING DEBEZIUM CDC CONNECTOR")
    print("="*70)
    print(f"\nConfiguration:")
    print(f"  Database: {db_config['host']}:{db_config['port']}")
    print(f"  Database Name: {db_config['database']}")
    print(f"  Table: public.{table_name}")
    print(f"  Connector Name: {connector_name}")
    print(f"  Topic Prefix: cdc_{db_config['database']}")
    
    # Check if Kafka Connect is running
    try:
        response = requests.get(f"{KAFKA_CONNECT_URL}/")
        if response.status_code != 200:
            print(f"\n❌ Kafka Connect not accessible at {KAFKA_CONNECT_URL}")
            sys.exit(1)
    except requests.exceptions.ConnectionError:
        print(f"\n❌ Cannot connect to Kafka Connect at {KAFKA_CONNECT_URL}")
        print("   Make sure Kafka Connect is running (run start_kafka_connect.ps1)")
        sys.exit(1)
    
    # Check if connector already exists
    try:
        response = requests.get(f"{KAFKA_CONNECT_URL}/connectors/{connector_name}")
        if response.status_code == 200:
            print(f"\n⚠️  Connector '{connector_name}' already exists")
            choice = input("   Delete and recreate? (y/n): ")
            if choice.lower() == 'y':
                print("   Deleting existing connector...")
                requests.delete(f"{KAFKA_CONNECT_URL}/connectors/{connector_name}")
                print("   ✓ Deleted")
            else:
                print("   Aborted")
                sys.exit(0)
    except:
        pass
    
    # Create connector
    print("\nCreating connector...")
    try:
        response = requests.post(
            f"{KAFKA_CONNECT_URL}/connectors",
            json=connector_config,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code in [200, 201]:
            print("✅ Connector created successfully!")
            
            # Wait and check status
            import time
            time.sleep(3)
            
            status_response = requests.get(f"{KAFKA_CONNECT_URL}/connectors/{connector_name}/status")
            if status_response.status_code == 200:
                status = status_response.json()
                print(f"\nConnector Status:")
                print(f"  State: {status['connector']['state']}")
                if status.get('tasks'):
                    print(f"  Task State: {status['tasks'][0]['state']}")
                
                if status['connector']['state'] == 'RUNNING':
                    print(f"\n🎉 CDC is now active!")
                    print(f"   Topic: cdc_{db_config['database']}.public.{table_name}")
                    print(f"   Next: Start CDC consumer from GUI to see messages")
                else:
                    print(f"\n⚠️  Connector not running. Check logs.")
        else:
            print(f"❌ Failed to create connector")
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.text}")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        sys.exit(1)

def list_connectors():
    """List all existing connectors"""
    try:
        response = requests.get(f"{KAFKA_CONNECT_URL}/connectors")
        if response.status_code == 200:
            connectors = response.json()
            if connectors:
                print("\nExisting Connectors:")
                for conn in connectors:
                    status_resp = requests.get(f"{KAFKA_CONNECT_URL}/connectors/{conn}/status")
                    if status_resp.status_code == 200:
                        status = status_resp.json()
                        state = status['connector']['state']
                        print(f"  - {conn}: {state}")
            else:
                print("\nNo connectors found")
    except Exception as e:
        print(f"Error listing connectors: {e}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Create CDC connector from config.json")
    parser.add_argument("--list", action="store_true", help="List existing connectors")
    parser.add_argument("--table", type=str, help="Table name (default: from config.json)")
    parser.add_argument("--name", type=str, help="Custom connector name")
    
    args = parser.parse_args()
    
    if args.list:
        list_connectors()
    else:
        # Load database config from config.json
        db_config = load_database_config()
        
        # Create connector
        create_connector(db_config, table_name=args.table, connector_name=args.name)
