import threading
import threading
import socket
loadBalancer = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
loadBalancer.bind(("localhost", 3000))
loadBalancer.listen(10)
print("hey there")

servers = [
    ("localhost", 8000),
    ("localhost", 8001), 
    ("localhost", 8002)
]
count, index, quantum = 0, 0, 2

def handleClient(client, connector, index):
    connector.connect(servers[index])
    def forward(client, connector):
        try:
            while True:
                data = client.recv(1024)
                if not data:
                 break
                connector.send(data)
        except OSError:
            pass
        finally:
            client.close()
            connector.close()
    
    threading.Thread(target = forward, args = (client, connector)).start()
    threading.Thread(target = forward, args = (connector, client)).start()

while True:
    client, addr = loadBalancer.accept()
    connector = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    if count < quantum:
        count+=1
    else:
        count = 1
        index +=1
        index%=len(servers)
    t1 = threading.Thread(target = handleClient, args=(client, connector, index))
    t1.start()

    

