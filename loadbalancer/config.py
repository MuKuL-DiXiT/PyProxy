import os
import threading
import queue
import yaml
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Default configuration values
LB_HOST = os.getenv("LB_HOST", "localhost")
LB_PORT = int(os.getenv("LB_PORT", "3000"))
BACKLOG = int(os.getenv("LB_BACKLOG", "10"))
quantum = int(os.getenv("LB_QUANTUM", "2"))
strategy_name = "least_connections"
mode = os.getenv("LB_MODE", "http")

# Thread synchronization lock for safe access to shared state
lock = threading.Lock()

# FIFO connection Queue
q = queue.Queue()

# Parse servers list from environment variable if provided
servers_env = os.getenv("LB_SERVERS")
if servers_env:
    servers = []
    for s in servers_env.split(","):
        h, p = s.strip().split(":")
        servers.append({"host": (h.strip(), int(p.strip())), "health_url": None, "status": "up", "connections": 0, "latency": 0})
else:
    # Default backend server pool configuration
    servers = [
        {"host": ("localhost", 8000), "health_url": None, "status": "up", "connections": 0, "latency": 0},
        {"host": ("localhost", 8001), "health_url": None, "status": "up", "connections": 0, "latency": 0},
        {"host": ("localhost", 8002), "health_url": None, "status": "up", "connections": 0, "latency": 0},
        {"host": ("localhost", 8003), "health_url": None, "status": "up", "connections": 0, "latency": 0}
    ]

# Round-robin connection quantum state
count = 0
index = 0

def validate_config():
    """Validate the loaded configuration parameters."""
    if not isinstance(LB_HOST, str) or not LB_HOST.strip():
        raise ValueError("Invalid configuration: LB_HOST must be a non-empty string.")
        
    if not isinstance(LB_PORT, int) or not (1 <= LB_PORT <= 65535):
        raise ValueError(f"Invalid configuration: LB_PORT must be an integer between 1 and 65535, got {LB_PORT}.")
        
    if not isinstance(BACKLOG, int) or BACKLOG <= 0:
        raise ValueError(f"Invalid configuration: BACKLOG must be a positive integer, got {BACKLOG}.")
        
    if not isinstance(quantum, int) or quantum <= 0:
        raise ValueError(f"Invalid configuration: quantum must be a positive integer, got {quantum}.")
        
    if strategy_name not in ("round_robin", "least_connections"):
        raise ValueError(f"Invalid configuration: strategy must be either 'round_robin' or 'least_connections', got '{strategy_name}'.")
        
    if mode not in ("http", "tcp"):
        raise ValueError(f"Invalid configuration: mode must be either 'http' or 'tcp', got '{mode}'.")
        
    if not isinstance(servers, list) or len(servers) == 0:
        raise ValueError("Invalid configuration: servers list cannot be empty.")
        
    for idx, s in enumerate(servers):
        if "host" not in s or not isinstance(s["host"], tuple) or len(s["host"]) != 2:
            raise ValueError(f"Invalid configuration: server {idx} must have a 'host' tuple of (host, port).")
        host_ip, host_port = s["host"]
        if not isinstance(host_ip, str) or not host_ip.strip():
            raise ValueError(f"Invalid configuration: server {idx} host IP/name must be a non-empty string.")
        if not isinstance(host_port, int) or not (1 <= host_port <= 65535):
            raise ValueError(f"Invalid configuration: server {idx} port must be an integer between 1 and 65535, got {host_port}.")
        if s.get("health_url") is not None and not isinstance(s.get("health_url"), str):
            raise ValueError(f"Invalid configuration: server {idx} health_url must be a string or null.")

def load_config(file_path):
    """Load configuration from a YAML file and update global state."""
    global LB_HOST, LB_PORT, BACKLOG, quantum, strategy_name, servers, mode
    
    with open(file_path, "r") as f:
        cfg = yaml.safe_load(f)
        
    if not cfg:
        return

    LB_HOST = cfg.get("LB_HOST", LB_HOST)
    LB_PORT = int(cfg.get("LB_PORT", LB_PORT))
    BACKLOG = int(cfg.get("backlog", BACKLOG))
    quantum = int(cfg.get("quantum", quantum))
    strategy_name = cfg.get("strategy", strategy_name)
    mode = cfg.get("LB_MODE", "tcp")

    if "servers" in cfg:
        servers_list = cfg["servers"]
        new_servers = []
        for s in servers_list:
            new_servers.append({
                "host": (s["host"], int(s["port"])),
                "health_url": s.get("health_url"),
                "status": "up",
                "connections": 0,
                "latency": 0
            })
        servers = new_servers

    validate_config()

# Validate initial config loaded from environment/defaults
validate_config()

