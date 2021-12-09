import asyncio

import binance.helpers

from .order import Order
from .symbol import Symbol
import datetime


class Deal:
    def __init__(self, spot, assets: Symbol, amount: float, profit_percentage: float = 5):
        self.open_order: Order = None
        self.close_order: Order = None
        self.amount: float = amount
        self.profit_percentage: float = profit_percentage
        self.spot: spot = spot
        self.assets: Symbol = assets
        self.gross = amount
        self.done = False  # Выполнена или нет
        self.status = "NEW"

    def __str__(self):
        return f'deal for {self.assets.symbol} in status {self.status} gross {self.gross}'

    async def start(self):
        # buy
        # wait price 60 min
        # sell
        if self.amount < self.assets.minNotional:
            self.done = True
            self.status = "CANCEL by minNotional"
            return

        now_plus_1h = datetime.datetime.now() + datetime.timedelta(hours=1)

        buy_price = await self.spot.get_current_price(self.assets.symbol)
        quantity = self.amount / buy_price
        quantity = max(quantity, self.assets.minQty)
        quantity = binance.helpers.round_step_size(quantity, self.assets.stepSize)

        if quantity < self.assets.minQty:
            self.done = True
            self.status = "CANCEL by minQty"
            return

        self.open_order = await self.spot.buy(self.assets.symbol, quantity)
        target_price = self.open_order.price * (1 + self.profit_percentage / 100)
        print(f'target_price {target_price}')

        sell_price = self.open_order.price
        while datetime.datetime.now() < now_plus_1h:
            sell_price = await self.spot.get_current_price(self.assets.symbol)
            if sell_price >= target_price:
                break
            await asyncio.sleep(1)

        await self.spot.sell(self.assets.symbol, quantity)
        self.gross = round(sell_price * quantity - self.amount, 2)
        print(f'sell_price = {sell_price} gross = {self.gross}')
        self.status = "FILLED"
        self.done = True
