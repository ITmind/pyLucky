import secrets
from spot import Spot
import time
import asyncio
import aiogram.utils.markdown as md
from aiogram.types import ParseMode

from datetime import datetime
from aiogram import Bot, Dispatcher, executor, types
import logging

# async def buy(client, amount):
#     print('*** BUY ***')
#     result = await client.get_symbol_ticker(symbol=symblol)
#     current_price = float(result['price'])
#     quantity = round(amount / current_price, 5)
#     print(f'price: {current_price} quantity: {quantity}')
#     return quantity, current_price
#
#
# async def sell(client, targetprice, quantity, stoploss):
#     # 2 минут
#     for i in range(120):
#         result = await client.get_symbol_ticker(symbol=symblol)
#         current_price = float(result['price'])
#         print(f'current_price = {current_price}', end='\r')
#         if current_price >= targetprice or current_price <= stoploss:
#             print('')
#             print('*** SELL ***')
#             amount = current_price * quantity
#             print(f'price: {current_price} amount: {amount}')
#             return amount
#         else:
#             await asyncio.sleep(1)
#     # если не дождались, то продаем по рынку
#     result = await client.get_symbol_ticker(symbol=symblol)
#     current_price = float(result['price'])
#     print('*** SELL ***')
#     amount = current_price * quantity
#     print(f'price: {current_price} amount: {amount}')
#     return amount

class AssistBot:

    def __init__(self):
        self.stop = False
        self.bot = Bot(token=secrets.bot_token)
        self.spot = None
        self.chat_id = None

    async def start(self):
        self.spot = await Spot.create()
        me = await self.bot.get_me()
        print(f"Hello, I'm {me.first_name}.\nHave a nice Day!")
        await asyncio.gather(
            self.start_polling(),
            self.spot.start_order_alarm(self.order_alarm)
        )

    async def start_polling(self):
        try:
            disp = Dispatcher(bot=self.bot)
            disp.register_message_handler(self.send_welcome, commands=['start', 'help'])
            disp.register_message_handler(self.find_command, commands=['find'])
            disp.register_message_handler(self.orders_command, commands=['orders'])
            disp.register_message_handler(self.stop_command, commands=['stop'])
            disp.register_message_handler(self.all_msg_handler)
            disp.register_callback_query_handler(self.answer_callback)
            await disp.start_polling()
        finally:
            await self.bot.close()

    async def order_alarm(self, message: str):
        if self.chat_id is None:
            return
        await self.bot.send_message(self.chat_id, message)

    async def find_command(self, message: types.Message):
        self.stop = False
        percent = 10
        try:
            percent = float(message.get_args())
        except:
            percent = 10

        await message.answer(f'Start find for up {percent}%...')
        async for data in self.spot.find_iter(percent):
            await message.answer(data)

    async def orders_command(self, message: types.Message):
        orders = await self.spot.get_open_orders()
        if orders is None:
            await message.answer("weight limit expiried")

        for order in orders:
            await message.answer(f'{order.symbol} P:{order.price} Q:{order.origQty} S:{order.summ}')

    async def stop_command(self, message: types.Message):
        # await message.answer("Stop")
        self.spot.stop()

    async def send_welcome(self, message: types.Message):
        self.chat_id = message.chat.id
        # Remove keyboard
        keyboard_markup = types.InlineKeyboardMarkup(row_width=3)
        text_and_data = (
            ('Find 10%', 'find10'),
            ('Find 20%', 'find20'),
        )
        row_btns = (types.InlineKeyboardButton(text, callback_data=data) for text, data in text_and_data)
        keyboard_markup.row(*row_btns)

        markup = types.ReplyKeyboardRemove()
        await message.reply(
            md.text(
                md.text('Hi ', md.bold(message.from_user.first_name)),
                md.text('Уou are subscribed to change the order status'),
                sep='\n'
            ),
            reply_markup=keyboard_markup,
            parse_mode=ParseMode.MARKDOWN
        )

    async def answer_callback(self, query: types.CallbackQuery):
        answer_data = query.data
        # always answer callback queries, even if you have nothing to say
        await query.answer(f'You answered with {answer_data!r}')

        percent = 99
        if answer_data == 'find10':
            percent = 10
        elif answer_data == 'find20':
            percent = 20

        await self.bot.send_message(query.from_user.id, f'Start find for up {percent}%...')
        async for data in self.spot.find_iter(percent):
            await self.bot.send_message(query.from_user.id, data)

    async def all_msg_handler(self, message: types.Message):
        await message.answer(message.text)


async def main():
    bot = AssistBot()
    await bot.start()

if __name__ == "__main__":
    # asyncio.run(main)
    logging.basicConfig(level=logging.INFO)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
