import socket
tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
host = ("127.0.0.1", 3000)
tcp_socket.bind(host)
print("Socket bound successfully")
tcp_socket.listen(5)
connections = {}
while len(connections)<2:
    client_socket, address = tcp_socket.accept()
    print(client_socket)
    connections[address] = client_socket
while True:
    for address, client_socket in connections.items():
        data = client_socket.recv(1024).decode()
        print(data)
        client_socket.send(data.encode())
