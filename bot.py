import mysecrets
import market
import asyncio
import aiogram.utils.markdown as md
from aiogram.types import ParseMode, KeyboardButton

from aiogram import Bot, Dispatcher, types, executor
import logging

my_user_id = 1095144735

bot = Bot(token=mysecrets.bot_token)
dp = Dispatcher(bot=bot)
spot: market.Spot = None
chat_id: str = None


async def deals_control():
    while True:
        if chat_id is None:
            await asyncio.sleep(600)
            continue

        dealsforremove = []
        for i, deal in spot.deals.items():
            if deal.done:
                await bot.send_message(chat_id, str(deal))
                dealsforremove.append(i)

        for i in dealsforremove:
            del spot.deals[i]

        await asyncio.sleep(300)


async def order_alarm(message: str):
    if chat_id is None:
        return
    await bot.send_message(chat_id, message)


@dp.message_handler(commands=['find'], user_id=my_user_id)
async def find_command(message: types.Message):
    # self.stop = False
    args = message.get_args().split(' ')

    keyboard_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard_markup.add(KeyboardButton('/stop'))
    keyboard_markup.add(KeyboardButton('/deals'))

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

    await message.answer(f'Поиск для dx> {percent}% и v> {velocity}...', reply_markup=keyboard_markup)

    async for candle in spot.find_iter(percent, velocity):
        if isinstance(candle, market.Candle):

            t3 = spot.calc_time(spot.symbols[candle.symbol], current_price=candle.close,
                                velocity=candle.v, profit_percentage=3)
            t5 = spot.calc_time(spot.symbols[candle.symbol], current_price=candle.close,
                                velocity=candle.v, profit_percentage=5)
            t10 = spot.calc_time(spot.symbols[candle.symbol], current_price=candle.close,
                                 velocity=candle.v, profit_percentage=10)

            text = md.text(f'{candle.symbol}',
                           f'o: {candle.open} $ c: {candle.close} $',
                           f'dx,%: {candle.dx} %',
                           f'скорость: {candle.v} p/min',
                           f'время до 3% = {t3} мин',
                           f'время до 5% = {t5} мин',
                           f'время до 10% = {t10} мин',
                           sep='\n'
                           )

            keyboard_buy = types.ReplyKeyboardRemove()
            if chat_id is not None:
                keyboard_buy = types.InlineKeyboardMarkup(row_width=2)
                keyboard_buy.clean()
                keyboard_buy.row(
                    types.InlineKeyboardButton('следящий', callback_data=f'bs {candle.symbol} f'),
                    types.InlineKeyboardButton('бесконечный', callback_data=f'bs {candle.symbol} i'),
                )
                keyboard_buy.row(
                    types.InlineKeyboardButton('сделка +3%', callback_data=f'bs {candle.symbol} 3'),
                    types.InlineKeyboardButton('сделка +5%', callback_data=f'bs {candle.symbol} 5'),
                )
                # только если за час достигнем 10
                if t10 < 60:
                    keyboard_buy.row(
                        types.InlineKeyboardButton('сделка +7%', callback_data=f'bs {candle.symbol} 7'),
                        types.InlineKeyboardButton('сделка +10%', callback_data=f'bs {candle.symbol} 10')
                    )

            # await message.answer(text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard_buy)
            with open('testsave.png', 'rb') as photo:
                await message.answer_photo(photo, caption=text, parse_mode=ParseMode.MARKDOWN,
                                           reply_markup=keyboard_buy)

        else:
            await message.answer(candle, reply_markup=types.ReplyKeyboardRemove())


@dp.message_handler(commands=['orders'], user_id=my_user_id)
async def orders_command(message: types.Message):
    orders = await spot.get_open_orders()
    if orders is None:
        await message.answer("weight limit expiried")

    for order in orders:
        await message.answer(f'{order.symbol} P:{order.price} Q:{order.origQty} S:{order.summ}')


@dp.message_handler(commands=['deals'], user_id=my_user_id)
async def orders_command(message: types.Message):
    for i, deal in spot.deals.items():
        text = md.text(
            md.text('Сделка по', md.bold(deal.assets), f' в статусе {deal.status}'),
            f'p: {deal.open_order.price}$ t: {deal.target_price}$ s: {deal.stop_loss_price}$',
            f'c: {deal.current_price}$',
            f'доход: {deal.gross}$',
            sep='\n'
        )

        keyboard_buy = None
        if not deal.done:
            keyboard_buy = types.InlineKeyboardMarkup(row_width=2)
            keyboard_buy.clean()
            keyboard_buy.row(
                types.InlineKeyboardButton('sell', callback_data=f'd stop {i}'),
            )

        await message.answer(text, ParseMode.MARKDOWN, reply_markup=keyboard_buy)


@dp.message_handler(commands=['stop'], user_id=my_user_id)
async def stop_command(message: types.Message):
    # await message.answer("Stop")
    spot.stop()


@dp.message_handler(commands=['start'], user_id=my_user_id)
async def start_command(message: types.Message):
    global chat_id
    chat_id = message.chat.id

    keyboard_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard_markup.add(KeyboardButton('/find'))
    keyboard_markup.add(KeyboardButton('/deals'))

    await message.answer(
        md.text(
            md.text('Привет ', md.bold(message.from_user.first_name)),
            md.text('Вы подписаны на изменения ордеров и сделок'),
            sep='\n'
        ),
        reply_markup=keyboard_markup,
        parse_mode=ParseMode.MARKDOWN
    )


@dp.callback_query_handler(user_id=my_user_id)
async def answer_callback(query: types.CallbackQuery):
    answer_data = query.data.split(sep=' ')
    # always answer callback queries, even if you have nothing to say
    await query.answer(f'You answered with {answer_data!r}')

    if answer_data[0] == 'bs':
        await bot.send_message(chat_id, f'Запуск сделки {answer_data[1]} с доходом {answer_data[2]}%')
        await spot.startdeal(answer_data[1], answer_data[2])
    elif answer_data[0] == 'd':
        if answer_data[1] == 'stop':
            spot.deals[int(answer_data[2])].done = True


@dp.message_handler(user_id=my_user_id)
async def all_msg_handler(message: types.Message):
    await message.answer(f'{message.from_user.id} {message.text}')


async def start():
    global spot
    spot = await market.Spot.create()
    me = await bot.get_me()
    print(f"Hello, I'm {me.first_name}.\nHave a nice Day!")
    # await dp.reset_webhook(True)
    # await dp.skip_updates()
    await asyncio.gather(
        dp.start_polling(),
        spot.start_order_alarm(order_alarm),
        deals_control()
    )


if __name__ == "__main__":
    # asyncio.run(main)
    logging.basicConfig(level=logging.INFO)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(start())
