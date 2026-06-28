import sys
import threading
import socket
import time # Import time

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

port = int(sys.argv[1])
server.bind(("localhost", port))
server.listen()

def handle(client):
    time.sleep(3) 
    client.sendall(str(port).encode())
    client.close()

while True:
    client, addr = server.accept()
    threading.Thread(target=handle, args=(client,), daemon=True).start()
