import sys
import threading
import socket
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

port = int(sys.argv[1])
server.bind(("localhost", port))
server.listen()

while True:
    client, addr = server.accept()
    client.sendall(str(port).encode())
    client.close()
