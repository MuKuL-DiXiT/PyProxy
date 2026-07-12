from loadbalancer import config
import json
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

class handler(BaseHTTPRequestHandler):
    def do_GET(self): 
        try: 
            payload = {
                "servers": [{
                    "address": f"{server['host'][0]}:{server['host'][1]}",
                    "status": server['status'],
                    "connections": server['connections'],
                    "latency": server['latency']
                } for server in config.servers]
            }
            body = json.dumps(payload).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json") 
            self.end_headers()
            self.wfile.write(body)
        except:
            print("something went wrong with the observability metric")
            pass

def start_stats_server():
    # Pass 'handler' to the HTTPServer initialization
    http_server = HTTPServer(("0.0.0.0", 9090), handler)
    t = threading.Thread(target=http_server.serve_forever, daemon=True)
    t.start()  # Call start() to run the thread
