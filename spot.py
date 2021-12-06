import time
from datetime import datetime
from math import floor
from binance import AsyncClient, exceptions
from candle import Candle
import asyncio
import secrets
from functools import wraps
from order import Order
from symbol import Symbol
# import finplot as fplt


def checkweight(func):
    @wraps(func)
    def wrapper(*args):
        self = args[0]
        if self.used_weight > Spot.weight_limit:
            return None
        result = func(*args)
        self.used_weight = int(self.client.response.headers['x-mbx-used-weight-1m'])
        return result

    return wrapper


class Spot:
    quote_asset: str = 'USDT'
    # всего ограничение 1200 в минуту, но сделаем меньше, что бы не вычислять веса каждого вызова
    weight_limit: int = 1100

    def __init__(self):
        self.client = None
        self.used_symbols = set()
        self.execute = False
        self.used_weight = 0
        self.order_update_func = None
        self.orders = []
        self.symbols = {}

    @classmethod
    async def create(cls):
        self = Spot()
        self.client = await AsyncClient.create(secrets.api_key, secrets.api_secret)
        # инициализируем все валюты
        exchange_info = await self.client.get_exchange_info()
        self.symbols = {s['symbol']: Symbol(s) for s in exchange_info['symbols']}
        return self

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
                    'dx': dx / 100
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

    def stop(self):
        self.execute = False

    async def find_iter(self, up_percent):
        self.execute = True
        tickers = await self.client.get_all_tickers()
        tickers = [t for t in tickers if t['symbol'].endswith(Spot.quote_asset)
                   and t['symbol'].find('DOWN' + Spot.quote_asset) == -1
                   and t['symbol'].find('UP' + Spot.quote_asset) == -1
                   and float(t['price']) < 100]
        print(f'number of tickers is {len(tickers)}')
        klines = None
        while self.execute:
            for price in tickers:

                if not self.execute:
                    yield "Stop find"
                    return

                symbol = price['symbol']

                if symbol in self.used_symbols or self.used_weight > Spot.weight_limit:
                    continue

                try:
                    klines = await self.client.get_klines(symbol=symbol, interval=self.client.KLINE_INTERVAL_1HOUR,
                                                          limit=3)
                except exceptions.BinanceAPIException as err:
                    yield "ERROR: \n" + err.message

                self.used_weight = int(self.client.response.headers['x-mbx-used-weight-1m'])
                # print(f'used weight in min is {used_weight}')

                if len(klines) == 0:
                    continue

                first = Candle(klines[0])
                last = Candle(klines[len(klines) - 1])
                # последняя свеча должна расти!
                if last.dx <= 0:
                    continue

                # каждая следующая закрылась выше предыдущей. 100% пампинг
                if last.close < first.close:
                    continue

                symbol_info = self.symbols[symbol]
                dx = round(last.max - first.min, symbol_info.quotePrecision)
                dx_percent = (dx / first.min) * 100
                dx_percent = round(dx_percent, 2)

                minutes_diff = (last.closetime - first.opentime).total_seconds() / 60.0
                diff_tick = (last.close - first.open) / symbol_info.tickSize
                v = round(diff_tick / minutes_diff, 2)

                if dx_percent > up_percent:
                    self.used_symbols.add(symbol)
                    # newlist = [Candle(k) for k in klines]
                    # newlist = [[k.open, k.close, k.max, k.min] for k in newlist]
                    # fplt.candlestick_ochl(newlist)
                    # fplt.screenshot('graph.png')
                    print(f'tick = {symbol_info.tickSize} diff_tick = {diff_tick}')
                    yield (f'{symbol}\n'
                           f'open: {first.open} $\n'
                           f'close: {last.close} $\n'
                           f'dx: {dx}\n'
                           f'dx,%: {dx_percent} %\n'
                           f'tickSize: {symbol_info.tickSize}\n'
                           f'velocity: {v} p/min')
                await asyncio.sleep(0.3)

            await asyncio.sleep(60)
            if datetime.now().minute == 30:
                self.used_symbols.clear()

        yield "Stop find"
        # await self.client.close_connection()

    async def start_order_alarm(self, callback):
        self.order_update_func = callback
        await self.get_open_orders()
        while self.order_update_func is not None:
            await asyncio.sleep(60)
            for order in self.orders:
                await self.update_order_status(order)
                if order.status != 'NEW':
                    await self.order_update_func(
                        f'Order {order.symbol}:{order.orderId} P:{order.price} Q:{order.origQty} in status {order.status}')

    @checkweight
    async def get_open_orders(self):
        self.orders = [Order(o) for o in await self.client.get_open_orders()]
        return self.orders

    @checkweight
    async def update_order_status(self, order: Order):
        order.update(await self.client.get_order(symbol=order.symbol, orderId=order.orderId))
