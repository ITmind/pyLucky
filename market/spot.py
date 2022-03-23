from __future__ import annotations
from datetime import datetime
from math import floor
from binance import AsyncClient, exceptions, helpers
import asyncio
import mysecrets
from functools import wraps
import market
# from . import Order, Symbol, Deal, Candle
import mplfinance as mpf
import pandas as pd
from typing import Dict, List, Optional


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
    quote_asset: str = 'BUSD'
    # всего ограничение 1200 в минуту, но сделаем меньше, что бы не вычислять веса каждого вызова
    weight_limit: int = 1100

    def __init__(self):
        self.client = None
        self.used_symbols = set()
        self.execute = False
        self.used_weight = 0
        self.order_update_func = None
        self.orders: List[market.Order] = []
        self.symbols: Dict[str, market.Symbol] = {}
        self.deals: Dict[int, market.Deal] = {}

    @classmethod
    async def create(cls):
        self = Spot()
        self.client = await AsyncClient.create(mysecrets.api_key, mysecrets.api_secret)
        # инициализируем все валюты
        exchange_info = await self.client.get_exchange_info()
        self.symbols = {s['symbol']: market.Symbol(s) for s in exchange_info['symbols'] if s['status'] == 'TRADING'
                        and s['symbol'].endswith(Spot.quote_asset)
                        and s['symbol'].find('DOWN' + Spot.quote_asset) == -1
                        and s['symbol'].find('UP' + Spot.quote_asset) == -1
                        }

        print(f'all market symbol is {len(self.symbols)}')
        return self

    async def sell(self, symbol: str, quantity: float):
        print(f'sell {symbol}')
        try:
            new_order_info = await self.client.create_test_order(symbol=symbol,
                                                                 side=AsyncClient.SIDE_SELL,
                                                                 type=AsyncClient.ORDER_TYPE_MARKET,
                                                                 quantity=quantity,
                                                                 newOrderRespType=AsyncClient.ORDER_RESP_TYPE_RESULT)
        except exceptions.BinanceAPIException as err:
            print(f"ERROR: {err.message}")
            return None

        # order = self.client.order_market_sell(
        #     symbol=symbol,
        #     quantity=quantity)

    async def buy(self, symbol: str, quantity: float) -> Optional[market.Order]:
        print(f'buy {symbol}')
        try:
            new_order_info = await self.client.create_test_order(symbol=symbol,
                                                                 side=AsyncClient.SIDE_BUY,
                                                                 type=AsyncClient.ORDER_TYPE_MARKET,
                                                                 quantity=quantity,
                                                                 newOrderRespType=AsyncClient.ORDER_RESP_TYPE_RESULT)
        except exceptions.BinanceAPIException as err:
            print(f"ERROR: {err.message}")
            return None

        # print(new_order_info)
        # new_order = Order.fromdata(new_order_info)

        # return new_order
        price = await self.get_current_price(symbol)
        # print(f"Buy {symbol} q: {quantity} p:{price}")
        return market.Order.create_virtual(symbol, price, quantity)

    async def startdeal(self, symbol: str, param: str):

        deal = None
        if param == 'f':
            deal = market.Deal.create_follow(self, self.symbols[symbol], 100, 5)
        elif param.isdigit():
            deal = market.Deal(self, self.symbols[symbol], 100, float(param))

        if deal is None:
            return

        self.deals[len(self.deals)] = deal
        await deal.start()

    @checkweight
    async def get_current_price(self, symbol):
        info = await self.client.get_symbol_ticker(symbol=symbol)
        return float(info['price'])

    def stop(self):
        self.execute = False

    async def find_iter(self, up_percent, velocity=1):
        self.execute = True
        try:
            tickers = await self.client.get_all_tickers()
        except:
            yield "find error"
            return

        tickers = [t for t in tickers if t['symbol'] in self.symbols
                   and float(t['price']) < 100]
        print(f'number of tickers is {len(tickers)}')
        klines = None
        while self.execute:
            for price in tickers:

                if not self.execute:
                    yield "Stop find"
                    return

                symbol: str = price['symbol']
                if symbol in self.used_symbols or self.used_weight > Spot.weight_limit:
                    continue

                symbol_info = self.symbols.get(symbol)
                if symbol_info is None:
                    # info = await self.client.get_symbol_info(symbol)
                    # self.symbols[symbol] = market.Symbol(info)
                    # symbol_info = self.symbols.get(symbol)
                    # if symbol_info is None:
                    continue

                try:
                    klines = await self.client.get_klines(symbol=symbol, interval=self.client.KLINE_INTERVAL_1HOUR,
                                                          limit=72)
                    klines_5m = await self.client.get_klines(symbol=symbol, interval=self.client.KLINE_INTERVAL_5MINUTE,
                                                             limit=72)

                    klines_btc = await self.client.get_klines(symbol='BTCBUSD',
                                                              interval=self.client.KLINE_INTERVAL_5MINUTE,
                                                              limit=72)

                    self.used_weight = int(self.client.response.headers['x-mbx-used-weight-1m'])
                    if len(klines) == 0:
                        continue
                except exceptions.BinanceAPIException as err:
                    yield "ERROR: \n" + err.message
                    continue

                kdata = [market.Candle.fromdata(symbol_info, k) for k in klines]
                kdata_5m = [market.Candle.fromdata(symbol_info, k) for k in klines_5m]
                kdata_btc = [market.Candle.fromdata(symbol_info, k) for k in klines_btc]

                kslice = kdata[-3:]

                # 1. последняя часовая и две 5 минутная свеча должны расти
                # 2. каждая следующая закрылась выше предыдущей
                if kslice[-1].dx <= 0 or \
                        kdata_5m[-1].dx <= 0 or \
                        kdata_5m[-2].dx <= 0 or \
                        kdata_5m[-1].close < kdata_5m[0].close or \
                        kslice[-1].close < kslice[0].close:
                    continue

                result = market.Candle.fromcandles(kslice)

                if result.dx > up_percent and kslice[-1].v > velocity:
                    self.used_symbols.add(symbol)
                    result.v = kslice[-1].v
                    self.plot(kdata, kdata_5m, kdata_btc, kslice[-1].close * 1.03)
                    yield result

                await asyncio.sleep(0.2)
            await asyncio.sleep(60)

            if datetime.now().minute == 30:
                self.used_symbols.clear()

        yield "Stop find"
        # await self.client.close_connection()

    def plot(self, kdata, kdata_5m, kdata_btc, target_price=None):
        df = Spot.create_df(kdata)
        df5m = Spot.create_df(kdata_5m)
        dfbtc = Spot.create_df(kdata_btc)
        add5m = [mpf.make_addplot(df5m, panel=1, type='candle', ylabel='5m'),
                 mpf.make_addplot(dfbtc, panel=2, type='candle', ylabel='BTC')]

        mpf.plot(df, type='candle', style='yahoo', ylabel='1h', savefig='testsave.png',
                 addplot=add5m, panel_ratios=(1, 1), figratio=(1, 1),
                 hlines=[target_price],
                 datetime_format='%H:%M', tight_layout=True)

    @staticmethod
    def create_df(kdata: Dict[market.Candle]) -> pd.DataFrame:
        data = [[k.opentime, k.open, k.max, k.min, k.close] for k in kdata]
        df = pd.DataFrame(data)
        df.columns = ['opentime', 'Open', 'High', 'Low', 'Close']
        df = df.set_index('opentime')
        return df

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
        try:
            self.orders = [market.Order.fromdata(o) for o in await self.client.get_open_orders()]
        except (exceptions.BinanceRequestException, exceptions.BinanceAPIException):
            self.orders = []
            print('get_open_orders error')

        return self.orders

    @checkweight
    async def update_order_status(self, order: market.Order):
        try:
            data = await self.client.get_order(symbol=order.symbol, orderId=order.orderId)
            if data['status'] != order.status:
                order.update(data)
                return True

        except (exceptions.BinanceRequestException, exceptions.BinanceAPIException):
            self.orders = []
            print('get_open_orders error')

        return False

    @staticmethod
    def calc_time(asset: market.Symbol, current_price: float, velocity: float,
                  profit_percentage: float = 5, target_price: float = None):
        """
        Расчет времени требуемого для достижения заданной цены при текущей скорости
        :param profit_percentage:
        :param asset:
        :param current_price:
        :param velocity:
        :param target_price:
        :return: время в минутах
        """
        if target_price is None:
            target_price = helpers.round_step_size(current_price * (1 + profit_percentage / 100), asset.tickSize)

        t = ((target_price - current_price) / asset.tickSize) / velocity
        return round(t)
