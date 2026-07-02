import socket
import threading
import errno
import config
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from http.client import HTTPConnection
from round_robin import round_robin
from least_connections import least_connection
from strategy import strategy

def handleClient(client, connector, index, request_buffer):

    try:
        # Measure latency when connecting to the backend
        start_time = time.time()
        connector.connect(config.servers[index]["host"])
        latency = round((time.time() - start_time) * 1000, 2)
        
        with config.lock:
            config.servers[index]['latency'] = latency
            
        # Replay any buffered request payload (in case this is a retry)
        for data in request_buffer:
            connector.sendall(data)
            
    except Exception as e:
        # Mark server down and queue the client for retry
        with config.lock:
            config.servers[index]["status"] = "down"
        config.q.put((client, request_buffer))
        connector.close()
        return
        
    # Mutable flags wrapped in dicts to allow modification within the inner function closure
    state = {"retry": False}
    cleanup = {"clean": False}
    
    def forward(source, destination, is_server_to_client):
        """Forward raw byte streams bidirectionally between sockets."""
        try:
            request_sent = False
            while True:
                data = source.recv(1024)
                request_sent = True
                if not data:
                    break
                
                # Buffer the request data if we are going from Client -> Server
                if not is_server_to_client:
                    request_buffer.append(data)
                    
                destination.sendall(data)
                
        except OSError as e:
            # Handle standard network errors, initiating retry if server failed prematurely
            if e.errno in (errno.ECONNRESET, errno.EPIPE, errno.ETIMEDOUT) and (
                (not request_sent and is_server_to_client) or 
                (not is_server_to_client and request_sent)
            ):
                with config.lock:
                    if not state["retry"]:
                        state["retry"] = True
                        config.servers[index]["status"] = "down"
                        config.q.put((client, request_buffer))
            elif e.errno == errno.EBADF:
                pass
            else:
                raise
        finally:
            # Safely decrement connection counter
            with config.lock:
                if not cleanup["clean"]:
                    cleanup["clean"] = True
                    config.servers[index]["connections"] -= 1

            # Close the sockets depending on retry status
            with config.lock:
                is_retry = state["retry"]
            if is_retry:
                if is_server_to_client:
                    source.close()     
                else:
                    destination.close() 
            else:
                source.close()
                destination.close()
    
    # bidirectional forwarding threads
    threading.Thread(target=forward, args=(client, connector, False), daemon=True).start()
    threading.Thread(target=forward, args=(connector, client, True), daemon=True).start()

class HTTPProxyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.proxy()
    def do_POST(self):
        self.proxy()
    def do_DELETE(self):
        self.proxy()
    def do_PUT(self):
        self.proxy()
    def do_PATCH(self):
        self.proxy()
    def do_OPTIONS(self):
        self.proxy()
    def do_HEAD(self):
        self.proxy()
        
    def proxy(self):
        try:
            content_length = int(self.headers.get("content-length", 0))
        except (ValueError, TypeError):
            content_length = 0
            
        body = self.rfile.read(content_length) if content_length > 0 else None
        
        max_retries = len(config.servers)
        for attempt in range(max_retries):
            # Select backend using strategy
            try:
                with config.lock:
                    if getattr(config, 'strategy_name', 'least_connections') == 'round_robin':
                        routing_strategy = round_robin()
                    else:
                        routing_strategy = least_connection()
                    
                    server_routing = strategy(routing_strategy)
                    server_routing.get_server(self.request)
                    
                    backend_index = config.index
                    backend = config.servers[backend_index]
            except RuntimeError as e:
                # All backend servers are down or error
                try:
                    self.send_error(503, "Service Unavailable: All backend servers are down")
                except Exception:
                    pass
                return
                
            conn = None
            connections_decremented = False
            try:
                start_time = time.time()
                conn = HTTPConnection(backend['host'][0], backend['host'][1], timeout=10)
                conn.connect()
                latency = round((time.time() - start_time) * 1000, 2)
                with config.lock:
                    backend['latency'] = latency
                    
                new_headers = {}
                headers_to_exclude = {"connection", "keep-alive", "transfer-encoding", 
                                      "te", "trailers", "upgrade", "proxy-authorization"}
                for k, v in self.headers.items():
                    if k.lower() not in headers_to_exclude:
                        new_headers[k] = v
                        
                new_headers["X-Forwarded-For"] = self.client_address[0]
                new_headers["X-Forwarded-Host"] = self.headers.get("Host", "")
                
                conn.request(
                    method = self.command,
                    url = self.path,
                    headers = new_headers,
                    body = body
                )
                response = conn.getresponse()
                
                self.send_response(response.status)
                for key, value in response.getheaders():
                    if key.lower() not in headers_to_exclude:
                        self.send_header(key, value)
                self.end_headers()
                self.wfile.write(response.read())
                
                with config.lock:
                    backend["connections"] -= 1
                    connections_decremented = True
                break
                
            except Exception as e:
                # Mark backend down, decrement active connections, and retry
                with config.lock:
                    backend["status"] = "down"
                    if not connections_decremented:
                        backend["connections"] -= 1
                        connections_decremented = True
                if conn:
                    conn.close()
                continue
            finally:
                if conn:
                    conn.close()
                if not connections_decremented:
                    with config.lock:
                        backend["connections"] -= 1