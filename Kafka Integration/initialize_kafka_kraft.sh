#!/bin/bash

# Kafka KRaft Initialization Script
# This script initializes Kafka in KRaft mode (combined mode)

set -e

KAFKA_HOME="/mnt/c/kafka/kafka-4.2.0"
CONFIG_FILE="./config/kraft/syniq-server.properties"

echo "======================================="
echo "Kafka KRaft Initialization Script"
echo "======================================="
echo ""

# Change to Kafka directory
cd "$KAFKA_HOME"

# Check if meta.properties already exists
LOG_DIR=$(grep "^log.dirs=" "$CONFIG_FILE" | cut -d'=' -f2)

if [ -z "$LOG_DIR" ]; then
    echo "Warning: Could not find log.dirs in config file"
    LOG_DIR="/tmp/kraft-combined-logs"
fi

echo "Log directory: $LOG_DIR"
echo ""

if [ -f "$LOG_DIR/meta.properties" ]; then
    echo "⚠️  Kafka storage is already initialized!"
    echo ""
    echo "Existing meta.properties found at: $LOG_DIR/meta.properties"
    echo ""
    read -p "Do you want to RESET and reinitialize Kafka? This will DELETE all data! (yes/no): " CONFIRM
    
    if [ "$CONFIRM" != "yes" ]; then
        echo ""
        echo "Initialization cancelled. You can start Kafka with:"
        echo "./bin/kafka-server-start.sh $CONFIG_FILE"
        exit 0
    fi
    
    echo ""
    echo "Removing existing log directories..."
    rm -rf "$LOG_DIR"
    echo "✓ Log directories removed"
fi

# Generate a new cluster UUID
echo "Generating cluster UUID..."
CLUSTER_UUID=$(./bin/kafka-storage.sh random-uuid)
echo "✓ Generated UUID: $CLUSTER_UUID"
echo ""

# Format the storage
echo "Formatting storage with cluster UUID..."
./bin/kafka-storage.sh format -t "$CLUSTER_UUID" -c "$CONFIG_FILE"
echo ""

echo "======================================="
echo "✓ Kafka KRaft initialization complete!"
echo "======================================="
echo ""
echo "Cluster UUID: $CLUSTER_UUID"
echo "Config File: $CONFIG_FILE"
echo "Log Directory: $LOG_DIR"
echo ""
echo "To start Kafka, run:"
echo "  cd $KAFKA_HOME"
echo "  ./bin/kafka-server-start.sh $CONFIG_FILE"
echo ""
echo "Or to start in background:"
echo "  ./bin/kafka-server-start.sh -daemon $CONFIG_FILE"
echo ""
