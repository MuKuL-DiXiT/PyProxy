import socket
import threading
import time

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind(("localhost", 8000))
server.listen(5)

conn, addr = server.accept()

def send_updates():
    count = 1
    while True:
        msg = f"Server Update {count}"
        conn.sendall(msg.encode())
        count += 1
        time.sleep(2)

def receive_messages():
    while True:
        data = conn.recv(1024)

        if not data:
            break

        print("Client:", data.decode())

threading.Thread(target=send_updates).start()
threading.Thread(target=receive_messages).start()