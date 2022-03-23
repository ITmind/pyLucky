from __future__ import annotations
from datetime import datetime
from binance import helpers
from typing import List
from functools import reduce
import market


class Candle:
    def __init__(self, asset: market.Symbol):
        self.asset = asset
        self.symbol = asset.symbol
        self.opentime_ts = datetime.now().timestamp() * 1000
        self.open = 0
        self.max = 0
        self.min = 0
        self.close = 0
        self.volume = 0
        self.closetime_ts = datetime.now().timestamp() * 1000
        self._v = 0

    @classmethod
    def fromdata(cls, asset: market.Symbol, data: list) -> Candle:
        """
        :param asset:Symbol
        :param data:List
        :return: Candle

        [0] - opentime_ts
        [1] - open
        [2] - max
        [3] - min
        [4] - close
        [5] - volume
        [6] - closetime_ts
        """
        self = cls(asset)
        self.opentime_ts = data[0]
        self.open = float(data[1])
        self.max = float(data[2])
        self.min = float(data[3])
        self.close = float(data[4])
        self.volume = float(data[5])
        self.closetime_ts = data[6]

        return self

    @classmethod
    def fromcandles(cls, candles: List[Candle]) -> Candle:
        last_index = len(candles) - 1
        self = cls(candles[0].asset)
        self.opentime_ts = candles[0].opentime_ts
        self.open = candles[0].open
        self.max = reduce(lambda acc, x: max(acc, x.max), candles, 0)
        self.min = reduce(lambda acc, x: min(acc, x.min), candles, 0)
        self.close = candles[last_index].close
        self.volume = candles[last_index].volume
        self.closetime_ts = candles[last_index].closetime_ts
        return self

    @property
    def opentime(self) -> datetime:
        return datetime.utcfromtimestamp(self.opentime_ts / 1000)

    @property
    def closetime(self) -> datetime:
        return datetime.utcfromtimestamp(self.closetime_ts / 1000)

    @property
    def dx(self):
        if self.open == 0:
            return 0

        dx = round(self.close - self.open, self.asset.quotePrecision)
        dx_percent = (dx / self.open) * 100
        return round(dx_percent, 2)

    @property
    def v(self) -> float:
        """
        скорость пунты/мин
        :return:
        """

        if self._v != 0:
            return self._v

        minutes_diff = round((self.closetime - self.opentime).total_seconds() / 60.0)
        diff_tick = helpers.round_step_size((self.close - self.open) / self.asset.tickSize,
                                            self.asset.tickSize)
        self._v = round(diff_tick / minutes_diff, 2)
        return self._v

    @v.setter
    def v(self, value):
        self._v = value

    def __str__(self) -> str:
        opentime = self.opentime.strftime('%H:%M:%S')
        closetime = self.closetime.strftime('%H:%M:%S')
        return f'{opentime}-{closetime} --- O: {self.open} C: {self.close} Max: {self.max} Min: {self.min} DXP {self.dx}%'
