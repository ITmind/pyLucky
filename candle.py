from typing import List
from datetime import datetime


class Candle:
    def __init__(self, data: List):
        self.opentime_ts = data[0]
        self.opentime = datetime.utcfromtimestamp(self.opentime_ts/1000)
        self.open = float(data[1])
        self.max = float(data[2])
        self.min = float(data[3])
        self.close = float(data[4])
        self.volume = float(data[5])
        self.closetime_ts = data[6]
        self.closetime = datetime.utcfromtimestamp(self.closetime_ts/1000)
        dx = ((self.close - self.open) / self.open) * 100
        self.dx = round(dx, 2)

    def __str__(self) -> str:
        opentime = self.opentime.strftime('%H:%M:%S')
        closetime = self.closetime.strftime('%H:%M:%S')
        return f'{opentime}-{closetime} --- O: {self.open} C: {self.close} Max: {self.max} Min: {self.min} DXP {self.dx}%'
