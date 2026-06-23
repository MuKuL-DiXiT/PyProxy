import socket
import threading
import time
import urllib.request

# =====================================================================
# Configuration & Global State
# =====================================================================

LB_HOST = "localhost"
LB_PORT = 3000
BACKLOG = 10

loadBalancer = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
loadBalancer.bind((LB_HOST, LB_PORT))
loadBalancer.listen(BACKLOG)
print("hey there")

servers = [
    {"host": ("localhost", 8000), "health_url": None, "status": "up"},
    {"host": ("localhost", 8001), "health_url": None, "status": "up"},
    {"host": ("localhost", 8002), "health_url": None, "status": "up"}
]

count = 0
index = 0
quantum = 2

lock = threading.Lock()


# =====================================================================
# Helper Functions & Background Threads
# =====================================================================

def http_get(server):
    """Perform an HTTP GET request to check the server's health status."""
    try:
        url = f"http://{server['host'][0]}:{server['host'][1]}{server['health_url']}"
        res = urllib.request.urlopen(url, timeout=2)
        return res.status == 200
    except:
        return False


def healthChceck():
    """Background loop to monitor health of servers via HTTP or TCP connection."""
    while True:
        for server in servers:
            if server["health_url"] is not None:
                res = http_get(server)
                with lock:
                    server["status"] = "up" if res else "down"
            else:
                try:
                    socket_check = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    socket_check.settimeout(2)
                    socket_check.connect(server["host"])
                    with lock:
                        server["status"] = "up"
                except:
                    with lock:
                        server["status"] = "down"
                finally:
                    socket_check.close()
        time.sleep(2)


# Start health check daemon thread
threading.Thread(target=healthChceck, daemon=True).start()


# =====================================================================
# Connection Handling and Routing
# =====================================================================

def handleClient(client, connector, index):
    """Forward bi-directional traffic between client and selected backend server."""
    connector.connect(servers[index]["host"])
    
    def forward(source, destination):
        try:
            while True:
                data = source.recv(1024)
                if not data:
                    break
                destination.sendall(data)
        except OSError:
            pass
        finally:
            source.close()
            destination.close()
    
    # Start bidirectional forwarding threads
    threading.Thread(target=forward, args=(client, connector), daemon=True).start()
    threading.Thread(target=forward, args=(connector, client), daemon=True).start()


# =====================================================================
# Main Listener Loop
# =====================================================================

while True:
    client, addr = loadBalancer.accept()
    connector = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    with lock:
        if count < quantum and servers[index]["status"] == "up":
            count += 1
        else:
            curr_index = index
            index += 1
            index %= len(servers)
            
            i = 0
            while servers[index]["status"] == "down" and i != len(servers):
                index += 1
                index %= len(servers)
                i += 1
                
            if curr_index != index:
                count = 1
                
            if servers[index]["status"] == "down":
                client.close()
                continue
    
    t1 = threading.Thread(target=handleClient, args=(client, connector, index), daemon=True)
    t1.start()