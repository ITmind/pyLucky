class Symbol:
    def __init__(self, data: dict):
        self.symbol = data['symbol']
        self.quotePrecision = int(data['quotePrecision'])
        for _filter in data['filters']:
            if _filter['filterType'] == 'PRICE_FILTER':
                self.minPrice = float(_filter['minPrice'])
                self.maxPrice = float(_filter['maxPrice'])
                self.tickSize = float(_filter['tickSize'])
            elif _filter['filterType'] == 'LOT_SIZE':
                self.minQty = float(_filter['minQty'])
                self.maxQty = float(_filter['maxQty'])
                self.stepSize = float(_filter['stepSize'])
            elif _filter['filterType'] == 'MIN_NOTIONAL':
                self.minNotional = float(_filter['minNotional'])
