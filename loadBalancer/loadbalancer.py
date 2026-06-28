from strategy import strategy
import socket
import threading
import sys
import config
import health
import handler
from round_robin import round_robin
from least_connections import least_connection

# Bind load balancer port
loadBalancer = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
loadBalancer.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
try:
    loadBalancer.bind((config.LB_HOST, config.LB_PORT))
    loadBalancer.listen(config.BACKLOG)
except Exception as e:
    print(f"Failed to start load balancer on {config.LB_HOST}:{config.LB_PORT}: {e}")
    sys.exit(1)

print(f"Load balancer listening on {config.LB_HOST}:{config.LB_PORT}")

# Start health checking daemon
health.start_health_check()

# Background connection acceptance thread
def accept_connections():
    while True:
        try:
            client, addr = loadBalancer.accept()
            config.q.put(client)
        except Exception as e:
            print(f"Error accepting connection: {e}")
            break

threading.Thread(target=accept_connections, daemon=True).start()

# Main dispatcher loop
while True:
    try:
        item = config.q.get()
        if isinstance(item, tuple):
            client, request_buffer = item
        else:
            client, request_buffer = item, []
            
        connector = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        with config.lock:
            # rr = round_robin()
            lc = least_connection()
            server_routing = strategy(lc)
            server_routing.get_server(client)
            # if config.count < config.quantum and config.servers[config.index]["status"] == "up":
            #     config.count += 1
            # else:
            #     curr_index = config.index
            #     config.index += 1
            #     config.index %= len(config.servers)
                
            #     i = 0
            #     while config.servers[config.index]["status"] == "down" and i != len(config.servers):
            #         config.index += 1
            #         config.index %= len(config.servers)
            #         i += 1
                    
            #     if curr_index != config.index:
            #         config.count = 1
                    
            #     if config.servers[config.index]["status"] == "down":
            #         client.close()
            #         raise RuntimeError("All backend servers are down!")
                    
        t1 = threading.Thread(
            target=handler.handleClient,
            args=(client, connector, config.index, request_buffer),
            daemon=True
        )
        t1.start()
    except RuntimeError as re:
        print(f"Shutdown: {re}")
        break
    except Exception as e:
        print(f"Unexpected error in dispatcher: {e}")
        break