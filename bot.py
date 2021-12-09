import secrets
from market import Spot, Candle
import asyncio
import aiogram.utils.markdown as md
from aiogram.types import ParseMode, KeyboardButton, InputFile

from aiogram import Bot, Dispatcher, types
import logging


class AssistBot:
    my_user_id = 1095144735

    def __init__(self):
        # self.stop = False
        self.bot = Bot(token=secrets.bot_token)
        self.spot = None
        self.chat_id = None
        self.dp = None

    async def start(self):
        self.spot = await Spot.create()
        me = await self.bot.get_me()
        print(f"Hello, I'm {me.first_name}.\nHave a nice Day!")
        await asyncio.gather(
            self.start_polling(),
            self.spot.start_order_alarm(self.order_alarm),
            self.deals_control()
        )

    async def start_polling(self):
        try:
            self.dp = Dispatcher(bot=self.bot)
            self.dp.register_message_handler(self.send_welcome, commands=['start', 'help'],
                                             user_id=AssistBot.my_user_id)
            self.dp.register_message_handler(self.find_command, commands=['find'], user_id=AssistBot.my_user_id)
            self.dp.register_message_handler(self.orders_command, commands=['orders'], user_id=AssistBot.my_user_id)
            self.dp.register_message_handler(self.stop_command, commands=['stop'], user_id=AssistBot.my_user_id)
            self.dp.register_message_handler(self.all_msg_handler)
            self.dp.register_callback_query_handler(self.answer_callback, user_id=AssistBot.my_user_id)
            await self.dp.start_polling()
        finally:
            await self.bot.close()

    async def deals_control(self):
        while True:
            if self.chat_id is None:
                await asyncio.sleep(600)
                continue

            dealsforremove = []
            for deal in self.spot.deals:
                if deal.done:
                    await self.bot.send_message(self.chat_id, str(deal))
                    dealsforremove.append(deal)

            for deal in dealsforremove:
                self.spot.deals.remove(deal)

            await asyncio.sleep(300)

    async def order_alarm(self, message: str):
        if self.chat_id is None:
            return
        await self.bot.send_message(self.chat_id, message)

    async def find_command(self, message: types.Message):
        # self.stop = False
        args = message.get_args().split(' ')

        keyboard_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        keyboard_markup.add(KeyboardButton('/stop'))

        percent = 10
        velocity = 1
        try:
            if len(args) > 0 and args[0] != '':
                percent = float(args[0])
            if len(args) > 1:
                velocity = float(args[1])
        except Exception as err:
            percent = 10
            velocity = 1
            await message.answer(f'parse error. {err}')

        await message.answer(f'Start find for dx> {percent}% and v> {velocity}...', reply_markup=keyboard_markup)

        async for candle in self.spot.find_iter(percent, velocity):
            if isinstance(candle, Candle):
                text = (f'{candle.symbol}\n'
                        f'o: {candle.open} $ c: {candle.close} $\n'
                        f'dx,%: {candle.dx} %\n'
                        f'velocity: {candle.v} p/min')

                keyboard_buy = types.InlineKeyboardMarkup(row_width=2)
                keyboard_buy.clean()
                keyboard_buy.row(
                    types.InlineKeyboardButton('buy/sell +5%', callback_data=f'bs {candle.symbol} 5'),
                    types.InlineKeyboardButton('buy/sell +10%', callback_data=f'bs {candle.symbol} 10')
                )

                await message.answer(text, reply_markup=keyboard_buy)
                with open('testsave.png', 'rb') as photo:
                    await message.answer_photo(photo)

            else:
                await message.answer(candle, reply_markup=types.ReplyKeyboardRemove())

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

        markup = types.ReplyKeyboardRemove()
        await message.reply(
            md.text(
                md.text('Hi ', md.bold(message.from_user.first_name)),
                md.text('Уou are subscribed to change the order status'),
                sep='\n'
            ),
            # reply_markup=keyboard_markup,
            parse_mode=ParseMode.MARKDOWN
        )

    async def answer_callback(self, query: types.CallbackQuery):
        answer_data = query.data.split(sep=' ')
        # always answer callback queries, even if you have nothing to say
        await query.answer(f'You answered with {answer_data!r}')

        if answer_data[0] == 'bs':
            await self.bot.send_message(self.chat_id, f'start deal for {answer_data[1]} with gross {answer_data[2]}%')
            await self.spot.startdeal(answer_data[1], float(answer_data[2]))

    async def all_msg_handler(self, message: types.Message):
        await message.answer(f'{message.from_user.id} {message.text}')


async def main():
    bot = AssistBot()
    await bot.start()


if __name__ == "__main__":
    # asyncio.run(main)
    logging.basicConfig(level=logging.INFO)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
