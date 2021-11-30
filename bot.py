from binance import Client
import secrets
from spot import Spot
import time


def start():
    client = Client(secrets.api_key, secrets.api_secret)
    # wallet = Wallet()
    total = 100  # USDT
    target_percent = 0.01
    spot = Spot(client)

    while True:
        asset = spot.findasset()
        while asset is None:
            print('!!! asset not founds')
            time.sleep(10)
            asset = spot.findasset()

        buy_price = asset['price']
        symbol = asset['symbol']
        target_percent = asset['dx'] * 0.9
        quantity = total / buy_price
        spot.buy(symbol, quantity)
        target_price = buy_price + buy_price * target_percent
        stop_price = buy_price * 0.99
        print(f'buy_price = {buy_price} target_price = {target_price} stop_price = {stop_price}')
        # start_time = time.time()
        num_iter = 60
        cur_iter = 0
        max_price = target_price
        target_price_reached = False
        while True:
            cur_iter += 1
            time.sleep(1)
            result = client.get_symbol_ticker(symbol=symbol)
            current_price = float(result['price'])
            print(f'current_price = {current_price}', end='\r')

            if current_price > max_price:
                max_price = current_price

            if current_price >= target_price:
                target_price_reached = True

            print(f'{cur_iter}/{num_iter}: current_price = {current_price} max_price={max_price} target_price_reached = {target_price_reached}', end='\r')

            # or (target_price_reached and current_price < max_price*0.99) \
            # if current_price <= stop_price \
            #         or (current_price < target_price and cur_iter > num_iter)\
            #         or cur_iter > num_iter:
            if (cur_iter > 20 and current_price <= stop_price) or current_price >= target_price or cur_iter >= num_iter:
                print('')
                spot.sell(symbol, quantity)
                print(f"margin: {quantity * current_price - total}")
                total = quantity * current_price

                break

        print(f"Total:{total}")
        time.sleep(1)


def get_all_ticker():
    client = Client(secrets.api_key, secrets.api_secret)
    info = client.get_ticker()
    # for data in info:
    # print(data['symbol'] + ' = ' + data['priceChangePercent'] + ' %')

    m = [(data['symbol'], data['priceChangePercent'])
         for data in info if float(data['priceChangePercent']) > 5]
    print(m)


if __name__ == "__main__":
    # get_all_ticker()
    start()

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
