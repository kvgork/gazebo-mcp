# Deployment Guide

Comprehensive guide for deploying the Gazebo MCP Server in development and production environments.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation Methods](#installation-methods)
3. [Configuration](#configuration)
4. [Running the Server](#running-the-server)
5. [Production Deployment](#production-deployment)
6. [Monitoring](#monitoring)
7. [Troubleshooting](#troubleshooting)
8. [Security](#security)

---

## Prerequisites

### System Requirements

**Minimum:**
- Ubuntu 22.04 LTS or newer
- 4 GB RAM
- 2 CPU cores
- 10 GB disk space

**Recommended:**
- Ubuntu 22.04 LTS
- 8 GB RAM
- 4 CPU cores
- 20 GB disk space
- GPU (for Gazebo GUI)

### Software Dependencies

**ROS2:**
- ROS2 Humble or Jazzy
- Gazebo Harmonic (recommended) or Gazebo Classic 11

**Python:**
- Python 3.10 or newer
- pip 23.0 or newer

**Docker (optional):**
- Docker Engine 24.0 or newer
- Docker Compose 2.20 or newer

---

## Installation Methods

### Method 1: Docker (Recommended)

**Advantages:**
- No dependency management
- Isolated environment
- Easy updates
- Production-ready

**Quick Start:**

```bash
# Clone repository:
git clone https://github.com/yourusername/ros2_gazebo_mcp.git
cd ros2_gazebo_mcp

# Start services:
docker-compose up

# Or run in background:
docker-compose up -d

# View logs:
docker-compose logs -f mcp_server

# Stop services:
docker-compose down
```

**Custom Configuration:**

```bash
# Set ROS domain ID:
export ROS_DOMAIN_ID=42
docker-compose up

# Enable monitoring:
docker-compose --profile monitoring up

# Development mode:
docker-compose --profile development up dev
```

---

### Method 2: From Source (Development)

**1. Install ROS2:**

```bash
# Add ROS2 repository:
sudo apt update && sudo apt install -y software-properties-common
sudo add-apt-repository universe
sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key -o /usr/share/keyrings/ros-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $(. /etc/os-release && echo $UBUNTU_CODENAME) main" | sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null

# Install ROS2 Humble:
sudo apt update
sudo apt install -y ros-humble-desktop

# Install Gazebo:
sudo apt install -y ros-humble-gazebo-ros-pkgs
```

**2. Install Python Dependencies:**

```bash
cd ros2_gazebo_mcp

# Install production dependencies:
pip install -r requirements.txt

# Or install with development dependencies:
pip install -r requirements.txt -r requirements-dev.txt
```

**3. Source ROS2:**

```bash
source /opt/ros/humble/setup.bash

# Add to ~/.bashrc for persistence:
echo "source /opt/ros/humble/setup.bash" >> ~/.bashrc
```

**4. Set Python Path:**

```bash
export PYTHONPATH=$PYTHONPATH:$(pwd)/src

# Add to ~/.bashrc:
echo "export PYTHONPATH=\$PYTHONPATH:$(pwd)/src" >> ~/.bashrc
```

**5. Run Tests:**

```bash
pytest tests/test_utils.py -v
```

---

### Method 3: System Package (Production)

**Coming soon:** `.deb` package for Ubuntu

---

## Configuration

### Environment Variables

Create `.env` file in project root:

```bash
# ROS2 Configuration
ROS_DISTRO=humble
ROS_DOMAIN_ID=0

# Logging
LOG_LEVEL=INFO
LOG_FILE=/var/log/gazebo_mcp/server.log

# Performance
MAX_CONCURRENT_OPERATIONS=10
REQUEST_TIMEOUT=30

# Metrics
ENABLE_METRICS=true
METRICS_EXPORT_PATH=/var/metrics/gazebo_mcp.prom
```

### Server Configuration

Create `config/server.yaml`:

```yaml
server:
  name: "Gazebo MCP Server"
  version: "1.0.0"

  # ROS2 settings:
  ros2:
    domain_id: 0
    qos_profile: "sensor_data"

  # Response format defaults:
  defaults:
    response_format: "summary"  # or "filtered"

  # Timeouts (seconds):
  timeouts:
    service_call: 10.0
    topic_subscription: 5.0

  # Metrics:
  metrics:
    enabled: true
    export_interval: 60  # seconds
    prometheus_port: 9090  # optional

  # Logging:
  logging:
    level: "INFO"
    format: "json"  # or "text"
    output: "/var/log/gazebo_mcp/server.log"
```

---

## Running the Server

### Development Mode

**Terminal 1 - Start Gazebo:**
```bash
source /opt/ros/humble/setup.bash
ros2 launch gazebo_ros gazebo.launch.py
```

**Terminal 2 - Start MCP Server:**
```bash
source /opt/ros/humble/setup.bash
export PYTHONPATH=$PYTHONPATH:$(pwd)/src
python3 -m mcp.server.server
```

**Terminal 3 - Test Server:**
```bash
python3 examples/01_basic_connection.py
```

---

### Production Mode (systemd)

**1. Create systemd service file:**

```bash
sudo cp deployment/gazebo-mcp.service /etc/systemd/system/
sudo systemctl daemon-reload
```

**2. Enable and start service:**

```bash
sudo systemctl enable gazebo-mcp
sudo systemctl start gazebo-mcp
```

**3. Check status:**

```bash
sudo systemctl status gazebo-mcp
sudo journalctl -u gazebo-mcp -f
```

---

### Docker Production Deployment

**1. Build production image:**

```bash
docker build --target production -t gazebo-mcp:latest .
```

**2. Run with docker-compose:**

```bash
docker-compose -f docker-compose.prod.yml up -d
```

**3. Configure auto-restart:**

Already configured in `docker-compose.yml`:
```yaml
restart: unless-stopped
```

**4. View logs:**

```bash
docker-compose logs -f mcp_server
```

---

## Production Deployment

### Architecture

**Recommended Setup:**

```
┌─────────────────────────────────────────┐
│         Load Balancer (nginx)           │
│         (if running HTTP mode)          │
└──────────────┬──────────────────────────┘
               │
    ┌──────────▼─────────┐
    │   MCP Server Pod   │
    │  (Docker/systemd)  │
    └──────────┬─────────┘
               │
    ┌──────────▼─────────┐
    │   Gazebo Simulator │
    │   (ROS2 + Gazebo)  │
    └────────────────────┘
               │
    ┌──────────▼─────────┐
    │   Metrics Export   │
    │    (Prometheus)    │
    └────────────────────┘
```

### High Availability

**Multiple MCP Servers:**

```yaml
# docker-compose.ha.yml
version: '3.8'

services:
  mcp_server_1:
    build: .
    # ... configuration ...

  mcp_server_2:
    build: .
    # ... configuration ...

  load_balancer:
    image: nginx:latest
    depends_on:
      - mcp_server_1
      - mcp_server_2
    # ... nginx config ...
```

**Health Checks:**

```python
# Automatic health monitoring:
from mcp.server.server import GazeboMCPServer

server = GazeboMCPServer()
health = server.health_check()

# Returns:
# {
#   "status": "healthy",
#   "uptime": 3600,
#   "gazebo_connected": true,
#   "ros2_ok": true
# }
```

---

## Monitoring

### Metrics Collection

**View current metrics:**

```bash
python3 scripts/show_metrics.py

# Detailed view:
python3 scripts/show_metrics.py --detailed

# Export to Prometheus:
python3 scripts/show_metrics.py --export metrics.prom --format prometheus
```

### Prometheus Integration

**1. Configure Prometheus:**

Create `prometheus.yml`:

```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'gazebo_mcp'
    static_configs:
      - targets: ['localhost:9090']
    file_sd_configs:
      - files:
        - /var/metrics/gazebo_mcp.prom
```

**2. Start Prometheus:**

```bash
docker run -d \
  -p 9090:9090 \
  -v $(pwd)/prometheus.yml:/etc/prometheus/prometheus.yml \
  -v /var/metrics:/var/metrics \
  prom/prometheus
```

### Grafana Dashboards

**Import dashboard:**

1. Access Grafana: `http://localhost:3000`
2. Add Prometheus data source
3. Import dashboard from `deployment/grafana-dashboard.json`

**Key Panels:**
- Tool call rate
- Average response time
- Error rate
- Token efficiency
- Top tools by usage

---

## Troubleshooting

### Common Issues

#### 1. Server Won't Start

**Problem:** `ModuleNotFoundError: No module named 'gazebo_mcp'`

**Solution:**
```bash
export PYTHONPATH=$PYTHONPATH:$(pwd)/src
```

#### 2. Can't Connect to Gazebo

**Problem:** `Failed to connect to Gazebo services`

**Solution:**
```bash
# Check Gazebo is running:
ros2 service list | grep gazebo

# Check ROS_DOMAIN_ID matches:
echo $ROS_DOMAIN_ID

# Restart Gazebo:
ros2 launch gazebo_ros gazebo.launch.py
```

#### 3. Docker Networking Issues

**Problem:** MCP server can't reach Gazebo in Docker

**Solution:**
```bash
# Check both containers are on same network:
docker network inspect ros2_gazebo_mcp_ros2_network

# Ensure ROS_DOMAIN_ID matches:
docker-compose config | grep ROS_DOMAIN_ID
```

#### 4. High Memory Usage

**Problem:** Server consuming excessive memory

**Solution:**
```python
# Use summary format instead of filtered:
result = server.call_tool("gazebo_list_models", {
    "response_format": "summary"  # 95% token savings!
})

# Reset metrics periodically:
from gazebo_mcp.utils.metrics import reset_metrics
reset_metrics()
```

### Logs

**Location:**
- **Development:** Console output
- **systemd:** `sudo journalctl -u gazebo-mcp`
- **Docker:** `docker-compose logs mcp_server`

**Enable debug logging:**

```bash
export LOG_LEVEL=DEBUG
python3 -m mcp.server.server
```

---

## Security

### Network Security

**1. Firewall Rules:**

```bash
# Allow only necessary ROS2 ports:
sudo ufw allow 7400:7499/tcp  # ROS2 DDS
sudo ufw allow 7400:7499/udp

# Block external access to MCP server (stdio mode):
# No ports exposed

# If running HTTP mode:
sudo ufw allow 8080/tcp  # MCP HTTP
```

**2. ROS2 Security:**

Enable ROS2 security (SROS2):

```bash
# Generate security keys:
ros2 security create_keystore demo_keystore
ros2 security create_key demo_keystore /gazebo_mcp_server

# Export keystore:
export ROS_SECURITY_KEYSTORE=demo_keystore
export ROS_SECURITY_ENABLE=true
export ROS_SECURITY_STRATEGY=Enforce
```

### Docker Security

**1. Run as non-root:**

Update Dockerfile:
```dockerfile
RUN useradd -m -u 1000 mcp_user
USER mcp_user
```

**2. Limit capabilities:**

```yaml
# docker-compose.yml
services:
  mcp_server:
    cap_drop:
      - ALL
    cap_add:
      - NET_BIND_SERVICE
    security_opt:
      - no-new-privileges:true
```

**3. Read-only filesystem:**

```yaml
services:
  mcp_server:
    read_only: true
    tmpfs:
      - /tmp
      - /var/log
```

### Secrets Management

**Don't commit secrets!**

Use environment variables or secret management:

```bash
# Export secrets:
export DOCKER_USERNAME="your_username"
export DOCKER_PASSWORD="your_password"

# Or use Docker secrets:
echo "my_password" | docker secret create docker_password -
```

---

## Performance Optimization

### 1. Use Summary Format

```python
# 95-99% token savings:
result = server.call_tool("gazebo_list_models", {
    "response_format": "summary"
})
```

### 2. Cache Results

```python
from functools import lru_cache

@lru_cache(maxsize=100)
def get_model_list():
    return server.call_tool("gazebo_list_models", {})
```

### 3. Connection Pooling

```python
# Reuse ROS2 nodes:
bridge = GazeboBridgeNode()  # Create once
# Use bridge multiple times
```

### 4. Batch Operations

```python
# Spawn multiple models efficiently:
models = ["box1", "box2", "box3"]
for model in models:
    spawn_model(model, ...)  # Single bridge instance
```

---

## Backup and Recovery

### Backup

**What to backup:**
- Configuration files (`config/`, `.env`)
- Custom models (`models/`)
- Custom worlds (`worlds/`)
- Logs (optional)

**Backup script:**

```bash
#!/bin/bash
BACKUP_DIR="/backups/gazebo_mcp_$(date +%Y%m%d)"
mkdir -p $BACKUP_DIR

cp -r config/ $BACKUP_DIR/
cp -r models/ $BACKUP_DIR/
cp -r worlds/ $BACKUP_DIR/
cp .env $BACKUP_DIR/

tar -czf $BACKUP_DIR.tar.gz $BACKUP_DIR
rm -rf $BACKUP_DIR
```

### Recovery

```bash
# Extract backup:
tar -xzf backup.tar.gz

# Restore configuration:
cp -r backup/config/ .
cp backup/.env .

# Restart services:
docker-compose restart
```

---

## Updating

### Docker Updates

```bash
# Pull latest images:
docker-compose pull

# Rebuild:
docker-compose build

# Restart services:
docker-compose up -d
```

### Source Updates

```bash
# Pull latest code:
git pull origin main

# Update dependencies:
pip install -r requirements.txt --upgrade

# Restart service:
sudo systemctl restart gazebo-mcp
```

---

## See Also

- [README.md](../README.md) - Project overview
- [ARCHITECTURE.md](ARCHITECTURE.md) - System architecture
- [METRICS.md](METRICS.md) - Performance monitoring
- [Examples](../examples/README.md) - Usage examples

---

**Last Updated:** 2025-11-16
**Version:** 1.0.0
