import time
from datetime import datetime
from math import floor


class Spot:
    quote_asset: str = 'USDT'

    def __init__(self, client):
        self.client = client
        self.used_symbols = set()

    def findasset(self):
        """ищем растущий актив"""
        print('******FIND*******')

        minutes = datetime.now().minute
        dozens = floor(minutes / 10)
        minutes -= dozens * 10

        while 0 <= minutes < 2 or 3 < minutes < 7 or 8 < minutes <= 9:
            time.sleep(5)
            minutes = datetime.now().minute
            dozens = floor(minutes / 10)
            minutes -= dozens * 10

        print(f"current minutes is {minutes}. Start get all ticker")
        all_ticker = self.get_all_ticker()

        for ticker in all_ticker:

            symbol = ticker['symbol']
            pricechangepercent = ticker['priceChangePercent']

            # уже использовали
            # if symbol in self.used_symbols:
            #     continue

            # print(f'-- check {symbol}')
            d = self.client.get_klines(symbol=symbol, interval=self.client.KLINE_INTERVAL_5MINUTE, limit=2)

            open1 = float(d[0][1])
            close1 = float(d[0][4])
            dx1 = round((close1 / open1 - 1) * 100, 5)
            open_ts = int(d[0][0]) / 1000
            close_ts = int(d[0][6]) / 1000
            # opentime = datetime.utcfromtimestamp(open_ts).strftime('%H:%M:%S')  # %Y-%m-%d %H:%M:%S
            # closetime = datetime.utcfromtimestamp(close_ts).strftime('%H:%M:%S')
            # print(f'{opentime} --- {closetime}')

            open2 = float(d[1][1])
            close2 = float(d[1][4])
            dx2 = round((close2 / open2 - 1) * 100, 5)
            open_ts = int(d[1][0]) / 1000
            close_ts = int(d[1][6]) / 1000
            # opentime = datetime.utcfromtimestamp(open_ts).strftime('%H:%M:%S')  # %Y-%m-%d %H:%M:%S
            # closetime = datetime.utcfromtimestamp(close_ts).strftime('%H:%M:%S')
            # print(f'{opentime} --- {closetime}')

            dx = (dx1 + dx2) / 2

            if dx > 1.5 and dx2 > 0.7:
                print('')
                print(f'open = {open1} close = {close1} dx = {dx1} %')
                print(f'open = {open2} close = {close2} dx = {dx2} %')
                print(f"find {symbol} priceChangePercent = {pricechangepercent}")
                # self.used_symbols.add(symbol)
                info = self.client.get_symbol_ticker(symbol=symbol)

                return {
                    'symbol': info['symbol'],
                    'price': float(info['price']),
                    'dx': dx/100
                }

            time.sleep(0.1)

        # ничего не нашли
        self.used_symbols.clear()
        return None

    def sell(self, symbol: str, quantity: float):
        print(f"Sell {symbol} of {quantity}")
        # order = self.client.order_market_sell(
        #     symbol=symbol,
        #     quantity=quantity)

    def buy(self, symbol: str, quantity: float):
        print(f"Buy {symbol} of {quantity}")
        # order = self.client.order_market_buy(
        #     symbol=symbol,
        #     quantity=quantity)
        pass

    def get_all_ticker(self):
        info = self.client.get_ticker()
        all_ticker = [{'symbol': data['symbol'], 'priceChangePercent': float(data['priceChangePercent'])}
                      for data in info if float(data['priceChangePercent']) >= 5
                      and data['symbol'].endswith('USDT')]
        all_ticker.sort(key=lambda x: x['priceChangePercent'], reverse=True)
        return all_ticker
