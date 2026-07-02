import config
from strategy import strategy
import socket
import threading
import sys
import health
from handler import HTTPProxyHandler, handleClient
from round_robin import round_robin
from least_connections import least_connection
import stats
import argparse
from http.server import HTTPServer, BaseHTTPRequestHandler

# ---------------------------------------------------------
# CLI Arguments Parsing
# ---------------------------------------------------------
parser = argparse.ArgumentParser(description="Load Balancer CLI")
parser.add_argument("--config", required=True, help="Path to the YAML configuration file")
args = parser.parse_args()

print(f"Loading configuration from: {args.config}")
config.load_config(args.config)

# ---------------------------------------------------------
# Daemon Services
# ---------------------------------------------------------
health.start_health_check()
stats.start_stats_server()

# ---------------------------------------------------------
# Server Mode Switch Execution
# ---------------------------------------------------------
if config.mode == 'http':
    try:
        from http.server import ThreadingHTTPServer
    except ImportError:
        from socketserver import ThreadingMixIn
        class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
            pass

    print(f"Starting HTTP Load Balancer on {config.LB_HOST}:{config.LB_PORT}...")
    try:
        load_balancer = ThreadingHTTPServer((config.LB_HOST, config.LB_PORT), HTTPProxyHandler)
        print(f"HTTP Load Balancer listening on http://{config.LB_HOST}:{config.LB_PORT}")
        load_balancer.serve_forever()
    except Exception as e:
        print(f"Failed to start HTTP load balancer on {config.LB_HOST}:{config.LB_PORT}: {e}")
        sys.exit(1)
else:
    # ---------------------------------------------------------
    # TCP Load Balancer Socket Setup
    # ---------------------------------------------------------
    load_balancer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    load_balancer_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        load_balancer_socket.bind((config.LB_HOST, config.LB_PORT))
        load_balancer_socket.listen(config.BACKLOG)
    except Exception as e:
        print(f"Failed to start TCP load balancer on {config.LB_HOST}:{config.LB_PORT}: {e}")
        sys.exit(1)

    print(f"TCP Load Balancer listening on {config.LB_HOST}:{config.LB_PORT}")

    # ---------------------------------------------------------
    # Connection Acceptance Thread
    # ---------------------------------------------------------
    def accept_connections():
        """Continuously accepts incoming client connections and queues them."""
        while True:
            try:
                client_socket, addr = load_balancer_socket.accept()
                config.q.put(client_socket)
            except Exception as e:
                print(f"Error accepting connection: {e}")
                break

    threading.Thread(target=accept_connections, daemon=True).start()

    # ---------------------------------------------------------
    # Dispatcher Loop
    # ---------------------------------------------------------
    while True:
        try:
            # Retrieve client connection from queue (could be a raw socket or a retry tuple)
            item = config.q.get()
            if isinstance(item, tuple):
                client_socket, request_buffer = item
            else:
                client_socket, request_buffer = item, []
                
            connector_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            
            # Select the active backend server using the designated strategy
            with config.lock:
                if getattr(config, 'strategy_name', 'least_connections') == 'round_robin':
                    routing_strategy = round_robin()
                else:
                    routing_strategy = least_connection()
                    
                server_routing = strategy(routing_strategy)
                server_routing.get_server(client_socket)
                        
            # Start a thread to handle client/backend communication
            t1 = threading.Thread(
                target=handleClient,
                args=(client_socket, connector_socket, config.index, request_buffer),
                daemon=True
            )
            t1.start()
            
        except RuntimeError as re:
            print(f"Shutdown: {re}")
            break
        except Exception as e:
            print(f"Unexpected error in dispatcher: {e}")
            break