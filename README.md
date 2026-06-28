# Network Proxy and Load Balancer Project

This repository contains implementations of a TCP Proxy and a TCP Load Balancer using Python's standard `socket` and `threading` libraries.

## Repository Structure

```
loadBalancerProject/
├── loadBalancer/
│   ├── config.py
│   ├── handler.py
│   ├── health.py
│   ├── least_connections.py
│   ├── loadbalancer.py
│   ├── round_robin.py
│   ├── routing.py
│   ├── server.py
│   └── strategy.py
└── proxy/
    ├── client.py
    ├── destination_backend.py
    └── proxy.py
```

---

## 1. Load Balancer Component

### Architecture Diagram

```
               +-----------------------+
               |        Client         |
               +-----------------------+
                           |
                           v
               +-----------------------+
               | Load Balancer (:3000) |
               +-----------------------+
              /            |            \
             /             |             \ (Round-Robin or Least Connections)
            v              v              v
      +-----------+  +-----------+  +-----------+
      | Server 1  |  | Server 2  |  | Server 3  |
      |  (:8000)  |  |  (:8001)  |  |  (:8002)  |
      +-----------+  +-----------+  +-----------+
```

### Files & Logic

*   **[loadbalancer.py](file:///Users/mukuldixit/dev/projects/loadBalancerProject/loadBalancer/loadbalancer.py)**:
    *   Binds to `localhost:3000` to receive client connections and routes them using the strategy pattern.
*   **[strategy.py](file:///Users/mukuldixit/dev/projects/loadBalancerProject/loadBalancer/strategy.py)**:
    *   Implements the Strategy interface context wrapper for selecting routing policies.
*   **[routing.py](file:///Users/mukuldixit/dev/projects/loadBalancerProject/loadBalancer/routing.py)**:
    *   Abstract base class representing a routing algorithm template.
*   **[round_robin.py](file:///Users/mukuldixit/dev/projects/loadBalancerProject/loadBalancer/round_robin.py)**:
    *   Implements the Round-Robin routing policy with a configurable quantum.
*   **[least_connections.py](file:///Users/mukuldixit/dev/projects/loadBalancerProject/loadBalancer/least_connections.py)**:
    *   Implements the Least Connections routing policy.
*   **[handler.py](file:///Users/mukuldixit/dev/projects/loadBalancerProject/loadBalancer/handler.py)**:
    *   Manages the client-server socket forwarding loop, retries on server failures, and thread-safe connection count increments/decrements.
*   **[config.py](file:///Users/mukuldixit/dev/projects/loadBalancerProject/loadBalancer/config.py)**:
    *   Central configuration module containing port definitions, shared state, locks, and backend host pools.
*   **[health.py](file:///Users/mukuldixit/dev/projects/loadBalancerProject/loadBalancer/health.py)**:
    *   Runs a background health-check daemon monitoring backend target availability.
*   **[server.py](file:///Users/mukuldixit/dev/projects/loadBalancerProject/loadBalancer/server.py)**:
    *   A multi-threaded server simulating load by keeping client connections open for a short delay (e.g., 3 seconds) before writing its port and closing.

### Execution Guide

To simulate the load balancer environment, run the backend servers and the balancer in separate terminal instances or tabs:

```bash
# Terminal 1: Start Backend Server 1
$ python loadBalancer/server.py 8000

# Terminal 2: Start Backend Server 2
$ python loadBalancer/server.py 8001

# Terminal 3: Start Backend Server 3
$ python loadBalancer/server.py 8002

# Terminal 4: Start the Load Balancer
$ python loadBalancer/loadbalancer.py

# Terminal 5: Test using concurrent client connections to observe Least Connections load distribution:
$ python -c "import socket, threading, time; [threading.Thread(target=lambda: print(socket.create_connection(('localhost', 3000)).recv(1024).decode().strip())).start() for _ in range(5)]; time.sleep(1)"
8002
8001
8001
8000
8000
```

---

## 2. TCP Proxy Component

### Architecture Diagram

```
+----------+          +----------------+          +---------------------+
|  Client  | <======> | Proxy (:8800)  | <======> | Des. Backend (:8000)|
+----------+          +----------------+          +---------------------+
                      |   Thread 1:    |
                      |   Server->Client
                      |   Thread 2:    |
                      |   Client->Server
                      +----------------+
```

### Files & Logic

*   **[proxy.py](file:///Users/mukuldixit/dev/projects/loadBalancerProject/proxy/proxy.py)**:
    *   Acts as an intermediate proxy listening on `localhost:8800`.
    *   For every connection accepted from a client, it establishes a corresponding connection to the destination backend server at `localhost:8000`.
    *   Spawns two forwarding threads using the `acc` routine to route TCP payload bidirectionally between the backend server and the client. If either socket is closed, the proxy tears down both connections.
*   **[destination_backend.py](file:///Users/mukuldixit/dev/projects/loadBalancerProject/proxy/destination_backend.py)**:
    *   Binds to `localhost:8000` and accepts a single incoming connection.
    *   Spawns a background thread that sends an automated string increment (`Server Update <count>`) to the connected socket every 2 seconds.
    *   Spawns another background thread to read incoming messages and write them to standard output.
*   **[client.py](file:///Users/mukuldixit/dev/projects/loadBalancerProject/proxy/client.py)**:
    *   Connects to the proxy at `localhost:8800`.
    *   Spawns a thread to read and print updates from the socket in real time.
    *   The main thread handles user CLI keyboard input (`input("You: ")`) and transmits it to the proxy.

### Execution Guide

To run the proxy pipeline, execute the components in the following sequence:

```bash
# Terminal 1: Start the Destination Backend Server
$ python proxy/destination_backend.py

# Terminal 2: Start the TCP Proxy Server
$ python proxy/proxy.py

# Terminal 3: Run the TCP Client
$ python proxy/client.py
You: Hello Server

Server Update 1
Server Update 2
You: Test connection

Server Update 3
```
