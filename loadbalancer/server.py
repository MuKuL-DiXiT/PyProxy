import sys
import threading
import socket
import time

def main():
    if len(sys.argv) < 2:
        print("Usage: pyproxy-server <port>")
        sys.exit(1)
        
    port = int(sys.argv[1])
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        server.bind(("localhost", port))
        server.listen()
    except Exception as e:
        print(f"Failed to bind mock server to port {port}: {e}")
        sys.exit(1)

    print(f"Mock server listening on port {port}...")

    def handle(client):
        time.sleep(3) 
        client.sendall(str(port).encode())
        client.close()

    while True:
        try:
            client, addr = server.accept()
            threading.Thread(target=handle, args=(client,), daemon=True).start()
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error accepting/handling connections: {e}")
            break

if __name__ == '__main__':
    main()
