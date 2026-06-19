import socket
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect(("localhost", 3000))
while True:
    message = input("Enter your message : ")
    client_socket.send(message.encode())
    data = client_socket.recv(1024)
    print(data.decode())
