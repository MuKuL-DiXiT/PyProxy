# Network Proxy and Load Balancer Project

This repository contains implementations of a TCP Proxy and a TCP Load Balancer using Python's standard `socket` and `threading` libraries.

## Repository Structure

```
loadBalancerProject/
├── loadBalancer/
│   ├── client1.py
│   ├── loadbalancer.py
│   └── server.py
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
             /             |             \ (Round-Robin, Quantum = 2)
            v              v              v
      +-----------+  +-----------+  +-----------+
      | Server 1  |  | Server 2  |  | Server 3  |
      |  (:8000)  |  |  (:8001)  |  |  (:8002)  |
      +-----------+  +-----------+  +-----------+
```

### Files & Logic

*   **[loadbalancer.py](file:///Users/mukuldixit/dev/projects/loadBalancerProject/loadBalancer/loadbalancer.py)**:
    *   Binds to `localhost:3000` to receive client connections.
    *   Maintains a pool of target backend servers: `localhost:8000`, `localhost:8001`, and `localhost:8002`.
    *   Implements a custom Round-Robin load distribution algorithm with a capacity quantum of 2. It sends 2 consecutive connections to one server before rotating to the next.
    *   For each accepted connection, it initiates a connection to the selected server and spawns two threads executing the `forward` helper to handle bidirectional stream relay (Client-to-Server and Server-to-Client) concurrently.
*   **[server.py](file:///Users/mukuldixit/dev/projects/loadBalancerProject/loadBalancer/server.py)**:
    *   Accepts a port number via command-line arguments and binds to `localhost:<port>`.
    *   Listens for incoming TCP connections. On acceptance, it writes its own port number back to the socket and immediately terminates the connection.
*   **[client1.py](file:///Users/mukuldixit/dev/projects/loadBalancerProject/loadBalancer/client1.py)**:
    *   Placeholder/empty client configuration file.

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

# Terminal 5: Simulate sequential client requests using Netcat
$ nc localhost 3000
8000
$ nc localhost 3000
8000
$ nc localhost 3000
8001
$ nc localhost 3000
8001
$ nc localhost 3000
8002
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
