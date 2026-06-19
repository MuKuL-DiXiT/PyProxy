import threading
import threading
from socket import socket
import socket
proxy = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
proxy.bind(("localhost", 8800))
proxy.listen(5)

def acc(client, server):
    while True: # the thread keeps running and expects incoming and outgoing calls without bloacking other thread
        data = client.recv(1024)
        if not data:
            server.close()
            client.close()
            break
        server.sendall(data)

while True:
    client, addr = proxy.accept() #to constantly accept connections one after another
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.connect(("localhost", 8000))
    t1 = threading.Thread(target=acc, args=(server, client))
    t1.start()
    t2 = threading.Thread(target=acc, args=(client, server))
    t2.start()
    
# same client file used (client.py)