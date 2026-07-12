# Distributed Network Proxy and Load Balancer Project

A production-ready, highly modular implementation of a high-performance **TCP Proxy** and an **observability-enabled TCP/HTTP Load Balancer** developed using Python's standard `socket`, `threading`, and HTTP libraries. This solution features multi-threaded request dispatching, round-robin (with configurable quantum) and least-connections routing algorithms, transparent mid-flight request failover, background health monitoring, and a real-time HTTP telemetry server.

Additionally, this project is fully containerized, supporting **multi-architecture Docker builds via Docker Manifest lists** to run seamlessly on heterogeneous cloud hardware, including AWS EC2 (x86_64 and Graviton/ARM64 architectures).

---

## Repository Structure

```text
loadBalancerProject/
├── .env.example             # Example environment variable file for override configurations
├── config.yaml              # Core configuration file for backend servers and load balancer
├── Dockerfile               # Slim Dockerfile optimized for multi-architecture deployments
├── requirements.txt         # Project dependencies (python-dotenv, PyYAML)
├── loadbalancer/            # Load Balancer Component
│   ├── config.py            # Configuration loader, validator, and shared state manager
│   ├── handler.py           # Layer 4/Layer 7 forwarding & mid-flight failover handler
│   ├── health.py            # Background target health checking daemon (HTTP / raw TCP)
│   ├── least_connections.py # Least Connections load distribution algorithm
│   ├── loadbalancer.py      # Entry point script coordinating dispatch loop & modes
│   ├── round_robin.py       # Round-Robin load distribution algorithm with quantum rotation
│   ├── routing.py           # Abstract base class for load balancing strategies
│   ├── server.py            # Simulated backend server (multi-threaded, delay-simulated)
│   ├── stats.py             # Observability/Telemetry HTTP server running on port 9090
│   ├── strategy.py          # Strategy Pattern context manager for target selection
│   └── TESTING.md           # Documentation detailing verification runs & failover tests
└── proxy/                   # Standalone TCP Proxy Component
    ├── client.py            # Interactive CLI TCP client
    ├── destination_backend.py # Mock destination backend server
    └── proxy.py             # Bidirectional TCP traffic forwarding proxy
```

---

## 1. Load Balancer Component

The Load Balancer routes traffic to configured backend servers and can operate as a **Layer 4 TCP Load Balancer** or a **Layer 7 HTTP Reverse Proxy**.

### System Architecture

```text
                               +------------------------------------+
                               |          Client Requests           |
                               +------------------------------------+
                                                 |
                                                 v
                               +------------------------------------+
                               |     Load Balancer (Port 3000)      |
                               |  - Mode: TCP (L4) or HTTP (L7)     |
                               +------------------------------------+
                                 /               |                \
         (Background Monitoring) |               |                | (Load Balancing Strategy:
         +-----------------------+               |                |  Least Conn or Round-Robin)
         |                                       v                v
+------------------+                   +------------------+  +------------------+
| Health Daemon    |                   | Backend Server 1 |  | Backend Server 2 |
| - TCP Connect    |                   |    (Port 8000)   |  |    (Port 8001)   |
| - HTTP GET /path |                   +------------------+  +------------------+
+------------------+                            ^                      ^
         |                                      |                      |
         +------ (Live Telemetry Server) -------+----------------------+
         v
+------------------+
| Telemetry API    |
| (Port 9090/json) |
+------------------+
```

### Core Architecture & Features

#### A. Dual-Mode Traffic Handling (Layer 4 vs. Layer 7)
*   **Layer 4 (TCP Mode)**: Configured via `LB_MODE: tcp`. It accepts raw TCP sockets, queues connections in a thread-safe FIFO pipeline ([config.py](file:///Users/mukuldixit/dev/projects/loadBalancerProject/loadbalancer/config.py)), and routes payload bidirectionally using low-level socket forwarding.
*   **Layer 7 (HTTP Mode)**: Configured via `LB_MODE: http`. It spins up an HTTP proxy engine that strips hop-by-hop headers (e.g., `Connection`, `Keep-Alive`, `Transfer-Encoding`), appends upstream geolocation headers (`X-Forwarded-For`, `X-Forwarded-Host`), forwards requests, and streams responses back to clients.

#### B. Load Balancing Algorithms (Strategy Pattern)
*   [least_connections.py](file:///Users/mukuldixit/dev/projects/loadBalancerProject/loadbalancer/least_connections.py): Dynamically selects the server with the lowest count of active client connections.
*   [round_robin.py](file:///Users/mukuldixit/dev/projects/loadBalancerProject/loadbalancer/round_robin.py): Rotates targets sequentially according to a configured quantum (number of requests dispatched to a backend before advancing to the next).

#### C. Mid-Flight Request Failover & Recovery
If a backend server terminates abruptly (returns `TCP RST` or throws a socket exception) during a client connection:
1.  [handler.py](file:///Users/mukuldixit/dev/projects/loadBalancerProject/loadbalancer/handler.py) catches the exception (e.g., `ECONNRESET`, `EPIPE`, `ETIMEDOUT`).
2.  The broken backend server's status is atomically flagged as `"down"`.
3.  The client's socket and all buffered request payload are re-queued back into the FIFO dispatch queue.
4.  The dispatcher retrieves the client socket, selects a healthy backup backend, establishes a connection, and replays the buffered payload.
5.  This failover is **100% transparent** to the client.

#### D. Health Checker Daemon
*   [health.py](file:///Users/mukuldixit/dev/projects/loadBalancerProject/loadbalancer/health.py) runs as a background daemon thread checking target health every 10 seconds.
*   If `health_url` is specified, it performs an HTTP GET request (marking status `up` if HTTP 200). If omitted, it falls back to a raw TCP handshake.

#### E. Observability & Telemetry API
*   [stats.py](file:///Users/mukuldixit/dev/projects/loadBalancerProject/loadbalancer/stats.py) runs a separate HTTP server on port `9090` exposing a JSON endpoint.
*   Querying `GET http://localhost:9090/` returns live metrics for all backends:
    ```json
    {
      "servers": [
        {
          "address": "127.0.0.1:8000",
          "status": "up",
          "connections": 0,
          "latency": 1.24
        }
      ]
    }
    ```

---

## Configuration Management

The system merges configurations from a YAML config file and environment variables loaded from a `.env` file. Environment variables take precedence.

### 1. YAML Configuration (`config.yaml`)
Create a [config.yaml](file:///Users/mukuldixit/dev/projects/loadBalancerProject/config.yaml) file to define the balancer configuration and upstream pools:
```yaml
LB_HOST: "0.0.0.0"
LB_PORT: 3000
LB_MODE: "http"      # Options: http, tcp
backlog: 10          # TCP backlog limit
strategy: "least_connections" # Options: least_connections, round_robin
quantum: 2           # Only applicable for round_robin
servers:
  - host: "localhost"
    port: 8000
    health_url: null # Raw TCP check
  - host: "localhost"
    port: 8001
    health_url: "/healthz" # HTTP GET status check
```

### 2. Environment Variables (`.env`)
Create a `.env` file to override YAML configurations programmatically, particularly useful in containerized or Kubernetes environments:
```ini
LB_HOST=0.0.0.0
LB_PORT=3000
LB_BACKLOG=10
LB_SERVERS=172.31.0.10:8000,172.31.0.11:8001
LB_QUANTUM=2
LB_MODE=http
```

---

## CLI Installation & Execution Guide

You can install this project as a package and use the CLI commands directly.

### Step 1: Install the Package
To install the package in editable mode for local development:
```bash
pip install -e .
```
Or to install the package normally:
```bash
pip install .
```

### Step 2: Spin Up Mock Backend Servers
Start mock backends to simulate load using the `pyproxy-server` CLI command:
```bash
# Terminal 1: Spin up Server 1 on Port 8000
pyproxy-server 8000

# Terminal 2: Spin up Server 2 on Port 8001
pyproxy-server 8001

# Terminal 3: Spin up Server 3 on Port 8002
pyproxy-server 8002
```

### Step 3: Run the Load Balancer
Start the load balancer using the `pyproxy` CLI command, supplying the configuration file via the `--config` argument:
```bash
# Terminal 4: Start Load Balancer
pyproxy --config config.yaml
```

### Step 4: Access Telemetry & Send Requests
```bash
# Query Live Telemetry Server
curl http://localhost:9090/

# Test load balancing distribution (sending concurrent requests)
python -c "import socket, threading, time; [threading.Thread(target=lambda: print(socket.create_connection(('localhost', 3000)).recv(1024).decode().strip())).start() for _ in range(5)]; time.sleep(1)"
```

---

## 2. Standalone TCP Proxy Component

This component handles simple bidirectional forwarding and CLI interactions, bypassing load balancing strategies.

```bash
# Terminal 1: Start Destination Backend
python proxy/destination_backend.py

# Terminal 2: Start TCP Proxy Server
python proxy/proxy.py

# Terminal 3: Start Interactive TCP Client
python proxy/client.py
```

---

## Containerization & Multi-Architecture Builds

To ensure the load balancer runs efficiently in cloud ecosystems utilizing mixed CPU architectures (e.g., standard Intel/AMD `x86_64` instances and AWS Graviton `ARM64` instances), we build a multi-architecture Docker image using **Docker Manifest lists**.

### Step 1: Enable Docker Buildx & Docker Hub Login
Ensure you have Docker buildx configured and are authenticated with your container registry:
```bash
docker buildx create --use
docker login
```

### Step 2: Build & Push Single-Architecture Images
Compile the Docker images for both `amd64` and `arm64` targets separately and push them to your registry:
```bash
# 1. Build and push AMD64 image (x86)
docker build -t your-dockerhub-username/load-balancer:latest-amd64 --platform linux/amd64 .
docker push your-dockerhub-username/load-balancer:latest-amd64

# 2. Build and push ARM64 image (Graviton/ARM)
docker build -t your-dockerhub-username/load-balancer:latest-arm64 --platform linux/arm64 .
docker push your-dockerhub-username/load-balancer:latest-arm64
```

### Step 3: Create & Push the Unified Multi-Arch Manifest
Create a Docker manifest list that binds the architecture-specific tags into a single unified tag:
```bash
# Create the manifest list
docker manifest create your-dockerhub-username/load-balancer:latest \
  your-dockerhub-username/load-balancer:latest-amd64 \
  your-dockerhub-username/load-balancer:latest-arm64

# Annotate architectures in the manifest list
docker manifest annotate your-dockerhub-username/load-balancer:latest your-dockerhub-username/load-balancer:latest-amd64 --os linux --arch amd64
docker manifest annotate your-dockerhub-username/load-balancer:latest your-dockerhub-username/load-balancer:latest-arm64 --os linux --arch arm64

# Push the manifest list
docker manifest push your-dockerhub-username/load-balancer:latest
```

---

## AWS EC2 Deployment Guide

Deploying the multi-architecture image on an EC2 instance allows Docker to automatically resolve and run the binary layout optimized for the underlying EC2 CPU architecture (AMD/Intel or Graviton ARM).

### Step 1: Connect to your EC2 Instance
```bash
ssh -i "your-ec2-key.pem" ec2-user@your-ec2-public-ip
```

### Step 2: Install and Start Docker
For Amazon Linux 2 / Amazon Linux 2023:
```bash
# Update software repositories
sudo yum update -y

# Install Docker
sudo yum install docker -y

# Start Docker service
sudo systemctl start docker
sudo systemctl enable docker

# Add the ec2-user to docker group to execute without sudo
sudo usermod -aG docker ec2-user
```
> [!IMPORTANT]
> Log out of the SSH session and log back in to apply the group privileges.

### Step 3: Create Host Configuration Files
Create the environment and YAML files on the host system:
```bash
# Create yaml config file
cat <<EOF > config.yaml
LB_HOST: "0.0.0.0"
LB_PORT: 3000
LB_MODE: "http"
backlog: 10
strategy: "least_connections"
servers:
  - host: "172.31.20.14" # Private IP of backend 1
    port: 8000
  - host: "172.31.20.15" # Private IP of backend 2
    port: 8000
EOF
```

### Step 4: Run the Multi-Arch Docker Container
Pull and run the container. Docker automatically matches your EC2 instance CPU type (e.g. standard instance or ARM-based Graviton instance) with the correct image using the manifest list:
```bash
docker run -d \
  --name app-load-balancer \
  --restart unless-stopped \
  -p 3000:3000 \
  -p 9090:9090 \
  -v $(pwd)/config.yaml:/app/config.yaml \
  your-dockerhub-username/load-balancer:latest \
  pyproxy --config /app/config.yaml
```

### Step 5: Verify Deployment
Verify that the container is healthy and traffic is balanced:
```bash
# View running containers
docker ps

# Check container logs
docker logs app-load-balancer

# Request live statistics from the host
curl http://localhost:9090/
```

