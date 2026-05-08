# Kafka KRaft Setup Guide

## Overview
Kafka KRaft (Kafka Raft) mode eliminates the need for ZooKeeper by using Kafka's internal Raft consensus protocol.

## Issue: "No readable meta.properties files found"
This error occurs when Kafka KRaft storage hasn't been initialized. The storage must be formatted before the first start.

## Quick Start

### 1. Initialize Kafka Storage (First Time Only)
```bash
cd /mnt/c/Users/Local\ user/OneDrive\ -\ M\ Telecommunication\ Sdn\ Bhd/Desktop/TASK/Syniq/Kafka\ Integration
bash initialize_kafka_kraft.sh
```

This script will:
- Generate a cluster UUID
- Format the storage directories
- Prepare Kafka for first startup

**⚠️ Warning:** Re-running this will delete all existing Kafka data!

### 2. Start Kafka
```bash
bash start_kafka.sh
```

Or manually:
```bash
cd /mnt/c/kafka/kafka-4.2.0
./bin/kafka-server-start.sh ./config/kraft/syniq-server.properties
```

### 3. Start Kafka in Background (Daemon Mode)
```bash
cd /mnt/c/kafka/kafka-4.2.0
./bin/kafka-server-start.sh -daemon ./config/kraft/syniq-server.properties
```

## Manual Setup Steps

### Generate UUID
```bash
cd /mnt/c/kafka/kafka-4.2.0
./bin/kafka-storage.sh random-uuid
```

Save the UUID output (e.g., `MkU3OEVBNTcwNTJENDM2Qk`)

### Format Storage
```bash
./bin/kafka-storage.sh format -t <YOUR-UUID> -c ./config/kraft/syniq-server.properties
```

### Start Server
```bash
./bin/kafka-server-start.sh ./config/kraft/syniq-server.properties
```

## Useful Commands

### Check if Kafka is Running
```bash
ps aux | grep kafka.Kafka
```

### Stop Kafka
```bash
pkill -f "kafka.Kafka"
```

Or gracefully:
```bash
cd /mnt/c/kafka/kafka-4.2.0
./bin/kafka-server-stop.sh
```

### View Kafka Logs
```bash
cd /mnt/c/kafka/kafka-4.2.0
tail -f logs/server.log
```

### Create a Test Topic
```bash
cd /mnt/c/kafka/kafka-4.2.0
./bin/kafka-topics.sh --create --topic test-topic --bootstrap-server localhost:9092 --partitions 1 --replication-factor 1
```

### List Topics
```bash
./bin/kafka-topics.sh --list --bootstrap-server localhost:9092
```

### Describe a Topic
```bash
./bin/kafka-topics.sh --describe --topic test-topic --bootstrap-server localhost:9092
```

## Troubleshooting

### Error: "No readable meta.properties files found"
**Solution:** Run the initialization script or format storage manually (see above)

### Error: "Address already in use"
**Solution:** Another Kafka instance is running. Stop it first:
```bash
pkill -f "kafka.Kafka"
# Wait a few seconds
ps aux | grep kafka.Kafka  # Verify it's stopped
```

### Reset Kafka (Delete All Data)
```bash
# Stop Kafka
pkill -f "kafka.Kafka"

# Remove log directories (check log.dirs in your config)
rm -rf /tmp/kraft-combined-logs

# Re-initialize
cd /mnt/c/Users/Local\ user/OneDrive\ -\ M\ Telecommunication\ Sdn\ Bhd/Desktop/TASK/Syniq/Kafka\ Integration
bash initialize_kafka_kraft.sh
```

## Configuration File Location
```
/mnt/c/kafka/kafka-4.2.0/config/kraft/syniq-server.properties
```

## Important Notes
1. **First time setup:** You MUST format storage before starting Kafka
2. **Formatting deletes data:** Only format when initializing or resetting
3. **UUID is permanent:** Keep the same UUID for the cluster lifetime
4. **Log directory:** Check `log.dirs` in your config file to see where data is stored
