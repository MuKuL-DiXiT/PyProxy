import os
import threading
import queue
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


LB_HOST = os.getenv("LB_HOST", "localhost")
LB_PORT = int(os.getenv("LB_PORT", "3000"))
BACKLOG = int(os.getenv("LB_BACKLOG", "10"))

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
        servers.append({"host": (h.strip(), int(p.strip())), "health_url": None, "status": "up"})
else:
    # Default backend server pool configuration
    servers = [
        {"host": ("localhost", 8000), "health_url": None, "status": "up", "connections": 0, "latency":0},
        {"host": ("localhost", 8001), "health_url": None, "status": "up", "connections": 0, "latency":0},
        {"host": ("localhost", 8002), "health_url": None, "status": "up", "connections": 0, "latency":0},
        {"host": ("localhost", 8003), "health_url": None, "status": "up", "connections": 0, "latency":0}
    ]

# Round-robin connection quantum state
count = 0
index = 0
quantum = int(os.getenv("LB_QUANTUM", "2"))
