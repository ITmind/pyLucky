class Order:
    def __init__(self, data):
        self.update(data)

    def update(self, data):
        self.symbol = data['symbol']
        self.orderId = data["orderId"]
        self.clientOrderId = data["clientOrderId"]
        self.price = float(data["price"])
        self.origQty = float(data["origQty"])
        self.executedQty = data["executedQty"]
        self.status = data["status"]
        self.timeInForce = data["timeInForce"]
        self.type = data["type"]
        self.side = data["side"]
        self.stopPrice = float(data["stopPrice"])
        self.icebergQty = float(data["icebergQty"])
        self.time = data["time"]
        self.summ = self.price * self.origQty
