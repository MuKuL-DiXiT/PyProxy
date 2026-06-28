from routing import routing
import config
class round_robin(routing):
    def get_server(self, client):
        if config.count < config.quantum and config.servers[config.index]["status"] == "up":
                config.count += 1
        else:
            curr_index = config.index
            config.index += 1
            config.index %= len(config.servers)
            
            i = 0
            while config.servers[config.index]["status"] == "down" and i != len(config.servers):
                config.index += 1
                config.index %= len(config.servers)
                i += 1
                
            if curr_index != config.index:
                config.count = 1
                
            if config.servers[config.index]["status"] == "down":
                client.close()
                raise RuntimeError("All backend servers are down!")