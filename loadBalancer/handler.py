import socket
import threading
import errno
import config

def handleClient(client, connector, index, request_buffer):
    """Forward bi-directional traffic between client and selected backend server."""
    try:
        connector.connect(config.servers[index]["host"])
        # Replay any buffered request payload
        for data in request_buffer:
            connector.sendall(data)
    except Exception as e:
        with config.lock:
            config.servers[index]["status"] = "down"
        config.q.put((client, request_buffer))
        connector.close()
        return
        
    state = {"retry": False}
    cleanup = {"clean":False}
    
    def forward(source, destination, stc):
        try:
            request_sent = False
            while True:
                data = source.recv(1024)
                request_sent = True
                if not data:
                    break
                # Buffer the request data (client-to-server direction)
                if not stc:
                    request_buffer.append(data)
                destination.sendall(data)
        except OSError as e:
            if e.errno in (errno.ECONNRESET, errno.EPIPE, errno.ETIMEDOUT) and ((not request_sent and stc) or (not stc and request_sent)):
                with config.lock:
                    if not state["retry"]:
                        state["retry"] = True
                        config.servers[index]["status"] = "down"
                        config.q.put((client, request_buffer))
            elif e.errno == errno.EBADF:
                pass
            else:
                raise
        finally:
            with config.lock:
                if not cleanup["clean"]:
                    cleanup["clean"] = True
                    config.servers[index]["connections"] -= 1

            with config.lock:
                is_retry = state["retry"]
            if is_retry:
                if stc:
                    source.close()   # close connector
                else:
                    destination.close()  # close connector
            else:
                source.close()
                destination.close()
    
    # Start bidirectional forwarding threads
    threading.Thread(target=forward, args=(client, connector, 0), daemon=True).start()
    threading.Thread(target=forward, args=(connector, client, 1), daemon=True).start()
