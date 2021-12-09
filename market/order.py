class Order:
    def __init__(self):
        pass

    @classmethod
    def fromdata(cls, data):
        obj = cls()
        obj.update(data)
        return obj

    @classmethod
    def create_virtual(cls, symbol, price, qty):
        obj = cls()
        obj.symbol = symbol
        obj.price = price
        obj.origQty = qty
        obj.status = 'NEW'
        return obj

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
        self.time = data["time"]
        self.summ = self.price * self.origQty
