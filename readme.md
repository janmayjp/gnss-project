# 🛰️ GNSS Real-Time Anomaly Detection System

A complete end-to-end system for real-time GNSS data processing, anomaly detection, and visualization using Apache Kafka, Apache Spark Streaming, and Streamlit.

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [System Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)
- [Production Deployment](#production)
- [Contributing](#contributing)

## 🎯 Overview

This system processes live GNSS NMEA data streams from sources like AUSCORS NTRIP services and detects anomalies in real-time including:

- **Signal Drops**: SNR below configurable threshold
- **Position Drift**: Unexpected position changes
- **Satellite Loss**: Insufficient satellites in view

The detected anomalies are stored for analysis and displayed on an interactive real-time dashboard.

## ✨ Features

- ✅ **Real-time NMEA Parsing**: Supports GGA, GSV, GSA, and RMC messages
- ✅ **NTRIP Integration**: Direct connection to AUSCORS correction streams
- ✅ **Kafka Streaming**: Scalable message broker for data ingestion
- ✅ **Spark Processing**: Distributed stream processing with windowed operations
- ✅ **Anomaly Detection**: Multiple detection algorithms with configurable thresholds
- ✅ **Interactive Dashboard**: Real-time visualization with Streamlit
- ✅ **Multiple Storage Formats**: CSV and Parquet output
- ✅ **Map Visualization**: Geographic tracking with Folium
- ✅ **Comprehensive Logging**: Detailed logging for debugging

## 🏗️ System Architecture {#architecture}

```
┌─────────────┐      ┌──────────────┐      ┌─────────────┐
│   AUSCORS   │ RTCM │   RTKLIB/    │ NMEA │   Python    │
│   NTRIP     │─────>│   Custom     │─────>│   Parser    │
│   Stream    │      │   Client     │      │             │
└─────────────┘      └──────────────┘      └──────┬──────┘
                                                   │
                                                   ▼
                                        ┌──────────────────┐
                                        │ Kafka Producer   │
                                        │ (gnss_topic)     │
                                        └────────┬─────────┘
                                                 │
                                                 ▼
                                        ┌──────────────────┐
                                        │ Apache Kafka     │
                                        └────────┬─────────┘
                                                 │
                                                 ▼
                                        ┌──────────────────┐
                                        │ Spark Streaming  │
                                        │ • Signal Drop    │
                                        │ • Drift Detect   │
                                        │ • Sat Loss       │
                                        └────┬─────────┬───┘
                                             │         │
                            ┌────────────────┘         └────────────┐
                            ▼                                       ▼
                  ┌──────────────────┐                  ┌──────────────────┐
                  │ CSV/Parquet      │                  │   Streamlit      │
                  │ Storage          │                  │   Dashboard      │
                  └──────────────────┘                  └──────────────────┘
```

## 📦 Prerequisites {#prerequisites}

### Hardware Requirements
- **Processor**: Apple M2 Pro or compatible ARM64/x64 processor
- **RAM**: 8GB minimum, 16GB recommended
- **Storage**: 10GB free space
- **Network**: Stable internet for NTRIP streams

### Software Requirements
- macOS 12.0+ (Monterey or later)
- Homebrew package manager
- Python 3.9 or higher
- Java 11 (for Kafka and Spark)
- Active AUSCORS account (for real GNSS data)

## 🔧 Installation {#installation}

### Step 1: Clone Repository

```bash
# Create project directory
mkdir -p ~/gnss-project
cd ~/gnss-project

# Initialize git (optional)
git init
```

### Step 2: Install System Dependencies

```bash
# Install Homebrew (if not installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Java 11
brew install openjdk@11

# Add Java to PATH
echo 'export PATH="/opt/homebrew/opt/openjdk@11/bin:$PATH"' >> ~/.zshrc
echo 'export JAVA_HOME="/opt/homebrew/opt/openjdk@11"' >> ~/.zshrc
source ~/.zshrc

# Verify Java installation
java -version
# Should output: openjdk version "11.x.x"

# Install Python 3.11
brew install python@3.11

# Install Kafka
brew install kafka

# Install Spark
brew install apache-spark

# Add Spark to PATH
echo 'export SPARK_HOME="/opt/homebrew/opt/apache-spark/libexec"' >> ~/.zshrc
echo 'export PATH="$SPARK_HOME/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

### Step 3: Create Project Structure

```bash
cd ~/gnss-project

# Create directories
mkdir -p data producer consumer dashboard utils config results logs tests

# Create Python files
touch producer/__init__.py producer/kafka_producer.py
touch consumer/__init__.py consumer/spark_streaming.py
touch dashboard/__init__.py dashboard/app.py
touch utils/__init__.py utils/nmea_parser.py utils/ntrip_client.py
touch config/settings.yaml
touch .env requirements.txt README.md
```

### Step 4: Install Python Dependencies

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Create requirements.txt
cat > requirements.txt << 'EOF'
# Kafka
kafka-python==2.0.2

# Spark
pyspark==3.5.0

# Data Processing
pandas==2.1.3
numpy==1.26.2

# NMEA Parsing
pynmea2==1.19.0

# Visualization
streamlit==1.28.2
plotly==5.18.0
folium==0.15.0
streamlit-folium==0.15.1

# Configuration
pyyaml==6.0.1
python-dotenv==1.0.0

# Logging
colorlog==6.8.0

# Storage
pyarrow==14.0.1
EOF

# Install dependencies
pip install -r requirements.txt
```

### Step 5: Configure the System

Create `config/settings.yaml`:

```yaml
# GNSS System Configuration

ntrip:
  caster: gnss.ga.gov.au
  port: 2101
  mountpoint: "MOBS00AUS0"
  username: "your_username"
  password: "your_password"
  latitude: -33.865
  longitude: 151.209

kafka:
  bootstrap_servers: "localhost:9092"
  topic: "gnss_topic"
  group_id: "gnss_consumer_group"
  auto_offset_reset: "latest"

spark:
  app_name: "GNSS_Anomaly_Detection"
  master: "local[*]"
  batch_interval: 2
  checkpoint_dir: "./checkpoints"

anomaly_detection:
  snr_threshold: 20.0
  drift_threshold: 0.0001
  min_satellites: 5
  moving_avg_window: 10

storage:
  output_dir: "./results"
  csv_enabled: true
  parquet_enabled: true

dashboard:
  port: 8501
  refresh_interval: 2
  map_zoom: 15
```

Create `.env` file:

```bash
# NTRIP Credentials
NTRIP_USERNAME=your_auscors_username
NTRIP_PASSWORD=your_auscors_password

# Kafka
KAFKA_BOOTSTRAP_SERVERS=localhost:9092

# Logging
LOG_LEVEL=INFO
```

**⚠️ Important**: Replace `your_username` and `your_password` with your actual AUSCORS credentials.

## 🚀 Usage {#usage}

### Starting the System

The system requires 4 components to run simultaneously. Open 4 terminal windows:

#### Terminal 1: Start Zookeeper

```bash
cd ~/gnss-project
source venv/bin/activate

# Start Zookeeper
zookeeper-server-start /opt/homebrew/etc/kafka/zookeeper.properties
```

#### Terminal 2: Start Kafka

```bash
cd ~/gnss-project
source venv/bin/activate

# Start Kafka broker
kafka-server-start /opt/homebrew/etc/kafka/server.properties
```

Wait 10-15 seconds for Kafka to fully start, then create the topic:

```bash
# Create Kafka topic
kafka-topics --create \
  --bootstrap-server localhost:9092 \
  --replication-factor 1 \
  --partitions 3 \
  --topic gnss_topic
```

Verify topic creation:

```bash
kafka-topics --list --bootstrap-server localhost:9092
```

#### Terminal 3: Start Spark Consumer

```bash
cd ~/gnss-project
source venv/bin/activate

# Start Spark streaming consumer
python consumer/spark_streaming.py
```

You should see:
```
✓ Spark session created
✓ Kafka stream configured
✓ Stream processing started
Monitoring for anomalies...
```

#### Terminal 4: Start Kafka Producer

**Option A: Test Mode (Recommended for first run)**

```bash
cd ~/gnss-project
source venv/bin/activate

# Start producer with test data
python producer/kafka_producer.py --source test --delay 2
```

**Option B: File Mode**

```bash
# Process NMEA file
python producer/kafka_producer.py \
  --source file \
  --file data/sample_nmea.txt \
  --delay 1
```

**Option C: TCP Mode (for RTKLIB output)**

```bash
# Read from RTKLIB TCP stream
python producer/kafka_producer.py \
  --source tcp \
  --host localhost \
  --port 9000
```

#### Terminal 5: Start Dashboard

```bash
cd ~/gnss-project
source venv/bin/activate

# Start Streamlit dashboard
streamlit run dashboard/app.py
```

The dashboard will open automatically in your browser at `http://localhost:8501`

### Stopping the System

Stop components in reverse order:

1. **Ctrl+C** in Dashboard terminal
2. **Ctrl+C** in Producer terminal
3. **Ctrl+C** in Spark Consumer terminal
4. **Ctrl+C** in Kafka terminal
5. **Ctrl+C** in Zookeeper terminal

### Quick Start Script

Create `run_system.sh`:

```bash
#!/bin/bash

# GNSS System Startup Script

echo "🚀 Starting GNSS Anomaly Detection System..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Run installation first."
    exit 1
fi

source venv/bin/activate

# Function to cleanup on exit
cleanup() {
    echo "🛑 Shutting down services..."
    jobs -p | xargs kill 2>/dev/null
    exit 0
}

trap cleanup EXIT INT TERM

# Start Zookeeper
echo "📦 Starting Zookeeper..."
zookeeper-server-start /opt/homebrew/etc/kafka/zookeeper.properties &
sleep 5

# Start Kafka
echo "📦 Starting Kafka..."
kafka-server-start /opt/homebrew/etc/kafka/server.properties &
sleep 10

# Create topic if not exists
kafka-topics --create --if-not-exists \
  --bootstrap-server localhost:9092 \
  --replication-factor 1 \
  --partitions 3 \
  --topic gnss_topic 2>/dev/null

# Start Spark Consumer
echo "⚡ Starting Spark Consumer..."
python consumer/spark_streaming.py &
sleep 5

# Start Producer (test mode)
echo "📡 Starting Producer..."
python producer/kafka_producer.py --source test --delay 2 &
sleep 3

# Start Dashboard
echo "📊 Starting Dashboard..."
streamlit run dashboard/app.py

# Wait for all background jobs
wait
```

Make it executable:

```bash
chmod +x run_system.sh
```

Run the entire system:

```bash
./run_system.sh
```

## 🧪 Testing {#testing}

### Test 1: Verify Kafka Connection

```bash
# Terminal 1: Start consumer test
kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic gnss_topic \
  --from-beginning
```

```bash
# Terminal 2: Send test message
echo '{"test": "message"}' | kafka-console-producer \
  --bootstrap-server localhost:9092 \
  --topic gnss_topic
```

You should see the test message appear in Terminal 1.

### Test 2: NMEA Parser

Create `tests/test_parser.py`:

```python
import sys
sys.path.append('..')

from utils.nmea_parser import NMEAParser
import json

def test_parser():
    parser = NMEAParser()
    
    # Sample NMEA messages
    messages = [
        "$GPGGA,092750.000,5321.6802,N,00630.3372,W,1,8,1.03,61.7,M,55.2,M,,*76",
        "$GPGSV,3,1,11,03,03,111,00,04,15,270,00,06,01,010,00,13,06,292,00*74",
        "$GPGSV,3,2,11,14,25,170,00,16,57,208,39,18,67,296,40,19,40,246,00*74",
        "$GPRMC,092750.000,A,5321.6802,N,00630.3372,W,0.02,31.66,280511,,,A*43"
    ]
    
    for msg in messages:
        result = parser.parse_message(msg)
        print(f"Parsed: {msg[:20]}...")
    
    json_messages = parser.to_json_messages()
    print(f"\nGenerated {len(json_messages)} JSON messages")
    print(json.dumps(json_messages[0], indent=2))

if __name__ == "__main__":
    test_parser()
```

Run test:

```bash
cd tests
python test_parser.py
```

### Test 3: Sample Data Generation

Create sample NMEA file `data/sample_nmea.txt`:

```
$GPGGA,120000.000,3351.9000,S,15112.5400,E,1,08,1.0,50.0,M,0.0,M,,*6C
$GPGSV,3,1,10,02,45,235,42,05,30,110,38,12,15,055,35,15,60,290,45*7A
$GPGSV,3,2,10,17,25,180,40,19,55,320,43,20,10,070,30,24,40,260,42*77
$GPGSV,3,3,10,25,20,155,38,28,35,200,41*77
$GPRMC,120000.000,A,3351.9000,S,15112.5400,E,0.50,180.0,020525,,,A*7E
$GPGGA,120001.000,3351.9001,S,15112.5401,E,1,08,1.0,50.1,M,0.0,M,,*6E
$GPGSV,3,1,10,02,45,235,41,05,30,110,37,12,15,055,34,15,60,290,44*7C
```

Test with file producer:

```bash
python producer/kafka_producer.py --source file --file data/sample_nmea.txt --delay 1
```

## 🔧 Troubleshooting {#troubleshooting}

### Common Issues and Solutions

#### Issue 1: Kafka Connection Refused

**Error**: `kafka.errors.NoBrokersAvailable: NoBrokersAvailable`

**Solutions**:
```bash
# 1. Check if Kafka is running
ps aux | grep kafka

# 2. Check Kafka logs
tail -f /opt/homebrew/var/log/kafka/server.log

# 3. Restart Kafka
kafka-server-stop
sleep 5
kafka-server-start /opt/homebrew/etc/kafka/server.properties
```

#### Issue 2: Spark Java Version Mismatch

**Error**: `java.lang.UnsupportedClassVersionError`

**Solution**:
```bash
# Verify Java version
java -version

# Should be Java 11. If not, switch:
export JAVA_HOME="/opt/homebrew/opt/openjdk@11"
export PATH="$JAVA_HOME/bin:$PATH"
```

#### Issue 3: Port Already in Use

**Error**: `Address already in use: bind`

**Solutions**:
```bash
# Find process using port 9092 (Kafka)
lsof -i :9092

# Kill the process
kill -9 <PID>

# For Streamlit (port 8501)
lsof -i :8501
kill -9 <PID>
```

#### Issue 4: No Data in Dashboard

**Checklist**:
1. ✅ Kafka is running: `kafka-topics --list --bootstrap-server localhost:9092`
2. ✅ Producer is running and sending messages
3. ✅ Consumer is processing: Check console output
4. ✅ Results directory has files: `ls -la results/anomalies_csv/`

#### Issue 5: NTRIP Connection Failed

**Error**: Connection refused or authentication failed

**Solutions**:
```bash
# 1. Test credentials
curl -u username:password http://gnss.ga.gov.au:2101/

# 2. Check network connectivity
ping gnss.ga.gov.au

# 3. Verify mountpoint availability
# Use NTRIP client to get sourcetable

# 4. Update config/settings.yaml with correct credentials
```

#### Issue 6: M2 Mac Compatibility

**Issue**: Some packages may not have ARM64 builds

**Solution**:
```bash
# Install Rosetta 2 (for Intel compatibility)
softwareupdate --install-rosetta

# Run Python under Rosetta if needed
arch -x86_64 python3 -m pip install <package>
```

### Logging and Debugging

Enable debug logging:

```bash
# Set environment variable
export LOG_LEVEL=DEBUG

# Or in .env file
echo "LOG_LEVEL=DEBUG" >> .env
```

Check log files:

```bash
# Producer logs
tail -f logs/producer.log

# Consumer logs  
tail -f logs/consumer.log

# Kafka logs
tail -f /opt/homebrew/var/log/kafka/server.log
```

## 🏭 Production Deployment {#production}

### Scaling Considerations

#### 1. Kafka Cluster Setup

For production, use a multi-broker Kafka cluster:

```properties
# server.properties for Broker 1
broker.id=1
listeners=PLAINTEXT://localhost:9092
log.dirs=/var/kafka-logs-1

# server.properties for Broker 2
broker.id=2
listeners=PLAINTEXT://localhost:9093
log.dirs=/var/kafka-logs-2

# server.properties for Broker 3
broker.id=3
listeners=PLAINTEXT://localhost:9094
log.dirs=/var/kafka-logs-3
```

Update configuration:

```yaml
kafka:
  bootstrap_servers: "broker1:9092,broker2:9093,broker3:9094"
  replication_factor: 3
  partitions: 6
```

#### 2. Spark Cluster Deployment

Deploy Spark in standalone cluster mode:

```bash
# Start master
$SPARK_HOME/sbin/start-master.sh

# Start workers
$SPARK_HOME/sbin/start-worker.sh spark://master-host:7077
```

Update Spark config:

```yaml
spark:
  master: "spark://master-host:7077"
  executor_memory: "4g"
  executor_cores: 2
  num_executors: 4
```

#### 3. Database Integration

Replace CSV/Parquet with time-series database:

```python
# Install InfluxDB client
pip install influxdb-client

# Update consumer to write to InfluxDB
from influxdb_client import InfluxDBClient

client = InfluxDBClient(url="http://localhost:8086", 
                        token="your-token", 
                        org="your-org")
```

#### 4. Monitoring and Alerting

Set up Prometheus + Grafana:

```yaml
# docker-compose.yml
version: '3'
services:
  prometheus:
    image: prom/prometheus
    ports:
      - "9090:9090"
  
  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
```

#### 5. Load Balancing

Use NGINX for dashboard load balancing:

```nginx
upstream streamlit_backend {
    server 127.0.0.1:8501;
    server 127.0.0.1:8502;
    server 127.0.0.1:8503;
}

server {
    listen 80;
    location / {
        proxy_pass http://streamlit_backend;
    }
}
```

### Security Best Practices

1. **Encrypt NTRIP connections**: Use HTTPS/TLS
2. **Secure Kafka**: Enable SASL/SSL authentication
3. **Firewall rules**: Restrict access to Kafka/Spark ports
4. **Secrets management**: Use AWS Secrets Manager or HashiCorp Vault
5. **Regular updates**: Keep all dependencies updated

### Performance Optimization

```yaml
# Optimized Kafka settings
kafka:
  compression.type: "lz4"
  batch.size: 32768
  linger.ms: 10
  buffer.memory: 67108864

# Optimized Spark settings
spark:
  sql.shuffle.partitions: 200
  streaming.backpressure.enabled: true
  streaming.kafka.maxRatePerPartition: 1000
```

## 📊 Sample Output

### Producer Output
```
2025-11-04 10:30:15 - INFO - ✓ Kafka producer initialized: localhost:9092
2025-11-04 10:30:15 - INFO - Generating synthetic GNSS test data
2025-11-04 10:30:17 - INFO - Sent 10 messages | Latest: G12 | SNR: 42.3 dB
2025-11-04 10:30:19 - INFO - Sent 20 messages | Latest: G27 | SNR: 18.7 dB
```

### Consumer Output
```
✓ Spark session created
✓ Kafka stream configured
✓ Stream processing started
Monitoring for anomalies...
  - Signal drop threshold: SNR < 20.0 dB
  - Satellite loss threshold: < 5 satellites
  - Position drift threshold: > 0.0001°

-------------------------------------------
Batch: 1
-------------------------------------------
+-------------------+------------+------+---------+------------------+
|          timestamp|satellite_id|   snr|num_sats|     anomaly_type |
+-------------------+------------+------+---------+------------------+
|2025-11-04 10:30:17|        G05 | 18.2 |       9|      SIGNAL_DROP |
+-------------------+------------+------+---------+------------------+
```

## 📚 Additional Resources

- [RTKLIB Documentation](http://www.rtklib.com/)
- [Apache Kafka Documentation](https://kafka.apache.org/documentation/)
- [Apache Spark Streaming Guide](https://spark.apache.org/docs/latest/streaming-programming-guide.html)
- [Streamlit Documentation](https://docs.streamlit.io/)
- [AUSCORS User Guide](https://gnss.ga.gov.au/auscors)
- [NMEA 0183 Protocol Specification](https://www.nmea.org/content/STANDARDS/NMEA_0183_Standard)

## 🤝 Contributing

Contributions are welcome! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License.

## ✉️ Contact

For questions or support, please open an issue on GitHub.

---

**Built with ❤️ for GNSS data processing and anomaly detection**
