import config
from routing import routing
import config
class least_connection(routing):
    def get_server(self, client):
        min_connections = float("inf")
        selected_index = -1

        for i, server in enumerate(config.servers):
            if server["status"] == "up" and server["connections"] < min_connections:
                min_connections = server["connections"]
                selected_index = i

        if selected_index == -1:
            client.close()
            raise RuntimeError("All backend servers are down!")

        config.servers[selected_index]["connections"] += 1

        config.index = selected_index