from binance import Client
import random
from datetime import datetime

# client = Client(secrets.api_key, secrets.api_secret)

# print(datetime.now().minute)

percent = 0.5
percent_normal = percent/100
amount = 100
open = 0.62077
close = 0.62256
max = 0.62500
min = 0.61445
result = 0
for i in range(12):

    print(f'O: {open} C: {close} Max: {max} Min: {min}')
    buyprice = round(random.uniform(min, max), 5)
    quantity = round(amount / buyprice, 2)
    print(f'Buy price {buyprice} quantity {quantity}')

    sellprice = round(buyprice*(1 + percent_normal), 5)
    if sellprice >= max:
        sellprice = buyprice - buyprice*percent_normal
    amount = round(quantity * sellprice, 2)
    print(f'Sell price {sellprice} amount {amount}')

    result += amount - 100
    amount = 100

if result >= 0:
    print(f'Win {result}')
else:
    print(f'Lose {result}')

# info = client.get_ticker()
# m = [{'symbol':data['symbol'], 'priceChangePercent':float(data['priceChangePercent'])}
#      for data in info if float(data['priceChangePercent']) >= 5
#      and data['symbol'].endswith('USDT')]
# m.sort(key=lambda x: x['priceChangePercent'], reverse=True)
# print(m)

#
#
# def get_asset():
#     data = client.get_account()
#     myasset = [asset for asset in data['balances'] if float(asset['free']) > 0]
#     #     a = json.dumps(data)
#     #     x = json.loads(a, object_hook=lambda d: SimpleNamespace(**d))
#     print(myasset)
#
#
# # data = client.get_my_trades(symbol='BNBUSDT')
# data = client.get_my_trades(symbol='WAXPUSDT')
# print(data)
# print(binance.helpers.convert_ts_str('1637106495964'))

# get_asset()
# print(client.get_exchange_info())