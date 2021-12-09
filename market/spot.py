import time
from datetime import datetime
from math import floor
from binance import AsyncClient, exceptions
import asyncio
import secrets
from functools import wraps
from .order import Order
from .symbol import Symbol
from .deal import Deal
from .candle import Candle
import mplfinance as mpf
import pandas as pd


def checkweight(func):
    @wraps(func)
    def wrapper(*args):
        self = args[0]
        if self.used_weight > Spot.weight_limit:
            print("weight is expiried")
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
        self.symbols: dict = {}
        self.deals = []

    @classmethod
    async def create(cls):
        self = Spot()
        self.client = await AsyncClient.create(secrets.api_key, secrets.api_secret)
        # инициализируем все валюты
        exchange_info = await self.client.get_exchange_info()
        self.symbols = {s['symbol']: Symbol(s) for s in exchange_info['symbols']}
        return self

    async def sell(self, symbol: str, quantity: float):
        print(f"Sell {symbol} of {quantity}")
        # order = self.client.order_market_sell(
        #     symbol=symbol,
        #     quantity=quantity)

    async def buy(self, symbol: str, quantity: float):
        new_order_info = await self.client.create_test_order(symbol=symbol,
                                                             side=AsyncClient.SIDE_BUY,
                                                             type=AsyncClient.ORDER_TYPE_MARKET,
                                                             quantity=quantity,
                                                             newOrderRespType=AsyncClient.ORDER_RESP_TYPE_RESULT)
        # print(new_order_info)
        # new_order = Order.fromdata(new_order_info)

        # return new_order
        price = await self.get_current_price(symbol)
        print(f"Buy {symbol} q: {quantity} p:{price}")
        return Order.create_virtual(symbol, price, quantity)

    async def startdeal(self, symbol, profit_percentage):
        deal = Deal(self, self.symbols[symbol], 100, profit_percentage)
        self.deals.append(deal)
        await deal.start()

    @checkweight
    async def get_current_price(self, symbol):
        info = await self.client.get_symbol_ticker(symbol=symbol)
        return float(info['price'])

    def get_all_ticker(self):
        info = self.client.get_ticker()
        all_ticker = [{'symbol': data['symbol'], 'priceChangePercent': float(data['priceChangePercent'])}
                      for data in info if float(data['priceChangePercent']) >= 5
                      and data['symbol'].endswith('USDT')]
        all_ticker.sort(key=lambda x: x['priceChangePercent'], reverse=True)
        return all_ticker

    def stop(self):
        self.execute = False

    async def find_iter(self, up_percent, velocity=1):
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
                                                          limit=24)
                except exceptions.BinanceAPIException as err:
                    yield "ERROR: \n" + err.message
                    continue

                self.used_weight = int(self.client.response.headers['x-mbx-used-weight-1m'])
                # print(f'used weight in min is {used_weight}')

                if len(klines) == 0:
                    continue

                kdata = [Candle.fromdata(symbol, k) for k in klines]
                # is_pass = False
                # dx_acc = 0
                #
                # # предпоследния свеча должна быть по dx меньше чем заданное значение поиска! иначе мы купим на самом верху
                # for i, candle in enumerate(kdata):
                #     if dx_acc > candle.dx:
                #         is_pass = True
                #         break
                #     dx_acc = candle.dx
                #
                # if is_pass:
                #     continue

                kslice = klines[-3:]
                first = Candle.fromdata(symbol, kslice[0])
                last = Candle.fromdata(symbol, kslice[len(kslice) - 1])

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

                if dx_percent > up_percent and v > velocity:
                    self.used_symbols.add(symbol)
                    result = Candle(symbol)
                    result.open = first.open
                    result.close = last.close
                    result.dx = dx_percent
                    result.v = v

                    self.plot(kdata)
                    yield result
                await asyncio.sleep(0.2)

            await asyncio.sleep(60)
            minute_now = datetime.now().minute
            if minute_now == 0:
                self.used_symbols.clear()

        yield "Stop find"
        # await self.client.close_connection()

    def plot(self, kdata: list[Candle]):
        data = [[k.opentime, k.open, k.max, k.min, k.close] for k in kdata]
        df = pd.DataFrame(data)
        df.columns = ['opentime', 'Open', 'High', 'Low', 'Close']
        # dt_index = pd.date_range("2013-02-01", periods=2, freq="D")
        # df["dt_index"] = dt_index
        df = df.set_index('opentime')
        mpf.plot(df, type='candle', style='yahoo', savefig='testsave.png')

    async def start_order_alarm(self, callback):
        self.order_update_func = callback
        await self.get_open_orders()
        while self.order_update_func is not None:
            await asyncio.sleep(60)
            for order in self.orders:
                if await self.update_order_status(order):
                    await self.order_update_func(
                        f'Order {order.symbol}:{order.orderId} P:{order.price} Q:{order.origQty} in status {order.status}')

    @checkweight
    async def get_open_orders(self):
        self.orders = [Order.fromdata(o) for o in await self.client.get_open_orders()]
        return self.orders

    @checkweight
    async def update_order_status(self, order: Order):
        data = await self.client.get_order(symbol=order.symbol, orderId=order.orderId)
        if data['status'] != order.status:
            order.update(data)
            return True
        return False
