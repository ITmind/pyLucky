from __future__ import annotations
import asyncio
import math

import binance.helpers as helpers
import market
import datetime


class Deal:
    def __init__(self, spot: market.Spot, assets: market.Symbol, amount: float, profit_percentage: float = 5):
        self.id: int = 0
        self.open_order: market.Order = None
        self.close_order: market.Order = None
        self.amount: float = amount
        self.profit_percentage: float = profit_percentage
        self.spot: market.Spot = spot
        self.assets: market.Symbol = assets
        self.gross: float = amount
        self.done: bool = False  # Выполнена или нет
        self.status: str = "NEW"
        self.target_price: float = 0
        self.stop_loss_price: float = 0
        self.current_price: float = 0
        self.type: str = "percent"

    def __str__(self):
        return f'deal for {self.assets.symbol} in status {self.status} gross {self.gross}'

    @classmethod
    def create_follow(cls, spot: market.Spot, assets: market.Symbol, amount: float, profit_percentage: float):
        obj = cls(spot, assets, amount, profit_percentage)
        obj.type = 'follow'
        return obj

    async def start(self):

        if self.amount < self.assets.minNotional:
            self.done = True
            self.status = "CANCEL by minNotional"
            return

        buy_price = await self.spot.get_current_price(self.assets.symbol)
        quantity = self.amount / buy_price
        quantity = max(quantity, self.assets.minQty)
        quantity = helpers.round_step_size(quantity, self.assets.stepSize)

        if quantity < self.assets.minQty:
            self.done = True
            self.status = "CANCEL by minQty"
            return

        self.open_order = await self.spot.buy(self.assets.symbol, quantity)
        if self.open_order is None:
            self.done = True
            self.status = "CANCEL by buy error"
            return

        self.target_price = helpers.round_step_size(self.open_order.price * (1 + self.profit_percentage / 100),
                                                    self.assets.tickSize)
        self.stop_loss_price = helpers.round_step_size(
            self.open_order.price * (1 - (self.profit_percentage / 2) / 100),
            self.assets.tickSize)

        self.current_price = self.open_order.price
        max_price = self.current_price
        lowprice_counter = 0
        last_price = 0
        now_plus_1h = datetime.datetime.now() + datetime.timedelta(hours=1)
        while datetime.datetime.now() < now_plus_1h and not self.done:
            self.current_price = await self.spot.get_current_price(self.assets.symbol)
            self.gross = round(self.current_price * quantity - self.amount, 2)

            if self.current_price < self.stop_loss_price:
                break

            if self.current_price < last_price:
                lowprice_counter += 1
            elif lowprice_counter > 0:
                lowprice_counter -= 1

            # if lowprice_counter == 3:
            #     break

            if self.type == 'follow':

                # Двигаем стоплосс
                if self.current_price > max_price:
                    new_stop = helpers.round_step_size(
                        self.current_price * (1 - (self.profit_percentage / 2) / 100), self.assets.tickSize)
                    if self.stop_loss_price < new_stop:
                        self.stop_loss_price = new_stop
                # не сгораемые суммы: 1%,2%,3% и т.д.
                stop_percent = math.floor((self.current_price - self.open_order.price) / self.open_order.price)
                if stop_percent > 0.01:
                    new_stop = helpers.round_step_size(self.open_order.price * (1 + stop_percent), self.assets.tickSize)
                    if self.stop_loss_price < new_stop:
                        self.stop_loss_price = new_stop

            else:
                if self.current_price >= self.target_price:
                    break

            max_price = max(max_price, self.current_price)
            last_price = self.current_price
            await asyncio.sleep(1)

        await self.spot.sell(self.assets.symbol, quantity)
        # self.gross = round(self.current_price * quantity - self.amount, 2)
        # print(f'sell_price = {self.current_price} gross = {self.gross}')
        self.status = "FILLED"
        self.done = True

    def validate(self):
        pass
