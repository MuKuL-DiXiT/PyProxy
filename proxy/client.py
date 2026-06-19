import socket
import threading

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect(("localhost", 8800))   # through proxy

def receive_messages():
    while True:
        data = client.recv(1024)

        if not data:
            break

        print("\nServer:", data.decode())

threading.Thread(target=receive_messages).start()

while True:
    msg = input("You: ")
    client.sendall(msg.encode())