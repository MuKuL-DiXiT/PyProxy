import socket
import time
import urllib.request
import threading
from loadbalancer import config

def http_get(server):
    """Perform an HTTP GET request to check the server's health status."""
    try:
        url = f"http://{server['host'][0]}:{server['host'][1]}{server['health_url']}"
        res = urllib.request.urlopen(url, timeout=2)
        return res.status == 200
    except:
        return False


def healthCheck():
    """Background loop to monitor health of servers via HTTP or TCP connection."""
    while True:
        for server in config.servers:
            if server["health_url"] is not None:
                res = http_get(server)
                with config.lock:
                    server["status"] = "up" if res else "down"
            else:
                try:
                    socket_check = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    socket_check.settimeout(2)
                    socket_check.connect(server["host"])
                    with config.lock:
                        server["status"] = "up"
                except:
                    with config.lock:
                        server["status"] = "down"
                finally:
                    socket_check.close()
        time.sleep(10)

def start_health_check():
    """Start the health checking daemon thread."""
    t = threading.Thread(target=healthCheck, daemon=True)
    t.start()
    return t
