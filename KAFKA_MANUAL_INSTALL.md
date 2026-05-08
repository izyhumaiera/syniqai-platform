# Quick Kafka Manual Installation Guide

## Your Java is Already Installed! ✓

The script successfully installed OpenJDK 21. Now let's get Kafka installed.

## Option 1: Try the Script Again (Recommended)

The network issue might be temporary:

```powershell
.\install_kafka_native.ps1 -CreateServices
```

## Option 2: Manual Download + Script Install

If the download keeps failing, download manually:

### Step 1: Download Kafka Manually

1. Go to: https://kafka.apache.org/downloads
2. Download **Kafka 3.6.1** - Binary for Scala 2.13
3. Or direct link: https://archive.apache.org/dist/kafka/3.6.1/kafka_2.13-3.6.1.tgz
4. Save to: `C:\kafka\kafka.tgz`

### Step 2: Run Script with SkipDownload

```powershell
# Script will use the file you downloaded
.\install_kafka_native.ps1 -CreateServices -SkipDownload
```

## Option 3: Use Kafka Without Docker (Simplest)

If both fail, here's a manual approach:

```powershell
# 1. Extract manually
cd C:\kafka
tar -xzf kafka.tgz
Rename-Item kafka_2.13-3.6.1 kafka-3.6.1

# 2. Generate cluster ID
cd C:\kafka\kafka-3.6.1
.\bin\windows\kafka-storage.bat random-uuid
# Copy the UUID output

# 3. Format storage (paste your UUID)
.\bin\windows\kafka-storage.bat format -t YOUR-UUID-HERE -c .\config\kraft\server.properties

# 4. Start Kafka
.\bin\windows\kafka-server-start.bat .\config\kraft\server.properties
```

## Quick Test After Setup

```powershell
# Test Kafka
cd C:\kafka\kafka-3.6.1
.\bin\windows\kafka-topics.bat --bootstrap-server localhost:9092 --list
```

## Next: Start Your App

Once Kafka is running:

```powershell
cd "Kafka Integration"
.\start_kafka_native.ps1
```

---

**Recommendation**: Try Option 1 first (script auto-download), then Option 2 if network is slow.
