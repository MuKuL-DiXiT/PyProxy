class strategy:
    def __init__(self, strategy):
        self.strategy = strategy
    def get_server(self, client):
        self.strategy.get_server(client)