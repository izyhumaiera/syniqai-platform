#!/bin/bash

# Kafka Start Script
# This script starts Kafka in KRaft mode

KAFKA_HOME="/mnt/c/kafka/kafka-4.2.0"
CONFIG_FILE="./config/kraft/syniq-server.properties"

echo "======================================="
echo "Starting Kafka KRaft Server"
echo "======================================="
echo ""

cd "$KAFKA_HOME"

# Check if storage is initialized
LOG_DIR=$(grep "^log.dirs=" "$CONFIG_FILE" | cut -d'=' -f2)

if [ -z "$LOG_DIR" ]; then
    LOG_DIR="/tmp/kraft-combined-logs"
fi

if [ ! -f "$LOG_DIR/meta.properties" ]; then
    echo "❌ Error: Kafka storage is not initialized!"
    echo ""
    echo "Please run the initialization script first:"
    echo "  bash /mnt/c/Users/Local\ user/OneDrive\ -\ M\ Telecommunication\ Sdn\ Bhd/Desktop/TASK/Syniq/Kafka\ Integration/initialize_kafka_kraft.sh"
    echo ""
    exit 1
fi

echo "✓ Storage initialized"
echo "Config: $CONFIG_FILE"
echo ""

# Check if Kafka is already running
if pgrep -f "kafka.Kafka" > /dev/null; then
    echo "⚠️  Kafka appears to be already running!"
    echo ""
    read -p "Do you want to stop and restart it? (yes/no): " CONFIRM
    
    if [ "$CONFIRM" = "yes" ]; then
        echo "Stopping Kafka..."
        pkill -f "kafka.Kafka"
        sleep 3
        echo "✓ Kafka stopped"
        echo ""
    else
        echo "Start cancelled."
        exit 0
    fi
fi

echo "Starting Kafka server..."
echo ""
echo "Press Ctrl+C to stop Kafka"
echo ""

./bin/kafka-server-start.sh "$CONFIG_FILE"
