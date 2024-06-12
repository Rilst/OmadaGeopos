import redis
import aiosqlite
import asyncio
import logging
import json
from logging.handlers import TimedRotatingFileHandler
from aiogram import Bot, Dispatcher
from config_reader import config
import userHandlers
from userHandlers import clinetpos
from aiogram.types import FSInputFile

# Объект бота
bot = Bot(token=config.bot_token.get_secret_value(), parse_mode="HTML")

# Диспетчер
dp = Dispatcher()
dp.include_router(userHandlers.router)

logging.basicConfig(level=logging.INFO)

# получение пользовательского логгера и установка уровня логирования
py_logger = logging.getLogger()
py_logger.setLevel(logging.INFO)

# настройка обработчика и форматировщика в соответствии с нашими нуждами
py_handler = TimedRotatingFileHandler('bot', when="midnight", interval=1)
py_handler.suffix = "%Y_%m_%d.log"
py_formatter = logging.Formatter("%(name)s %(asctime)s %(levelname)s %(message)s")

# добавление форматировщика к обработчику 
py_handler.setFormatter(py_formatter)
# добавление обработчика к логгеру
py_logger.addHandler(py_handler)

async def Send(chatID, photo, Text):
    if photo != None:
        await bot.send_photo(chat_id=chatID, photo=photo, caption=Text)
    else:
        await bot.send_message(chat_id=chatID, text=Text)

async def CreateDatabase():
    async with aiosqlite.connect('TGContacts.db') as db:
        await db.execute('pragma journal_mode=wal')
        await db.execute('CREATE TABLE IF NOT EXISTS Contacts '
                         '(PhoneNumber text NOT NULL UNIQUE, ChatID int NOT NULL, PRIMARY KEY(PhoneNumber))')
        await db.commit()
    async with aiosqlite.connect('Positions.db') as db2:
        await db2.execute('pragma journal_mode=wal')
        await db2.execute('CREATE TABLE IF NOT EXISTS Positions '
                         '(AP_MAC text NOT NULL UNIQUE, PosText text NOT NULL, PicName text, PRIMARY KEY(AP_MAC))')
        await db2.commit()


currentpos = redis.Redis(host='localhost', port=6379, db=1, decode_responses=True)
queue = currentpos.pubsub()
queue.subscribe("ChangePos")

# бесконечный цикл обработки очереди сообщений
async def WaitMessage():
    await CreateDatabase()
    while True:
        await asyncio.sleep(0.1)
        msg = queue.get_message() # извлекаем сообщение
        if msg: # проверяем сообщение на пустоту
            if isinstance(msg["data"], str): # проверяем, какой тип информации хранится в переменной data (msg имеет тип словаря)
                Client = json.loads(msg["data"])
                for phone, apmac in Client.items():
                    async with aiosqlite.connect('TGContacts.db') as db:
                        chatid = await db.execute_fetchall('SELECT ChatID FROM Contacts WHERE PhoneNumber = ?', (phone,))
                        await db.commit()
                        if len(chatid[0][0]) != 0:
                            clinetpos.set(chatid[0][0], apmac, ex=28800)
                            async with aiosqlite.connect('Positions.db') as db2:
                                answer = await db2.execute_fetchall('SELECT PosText, PicName FROM Positions WHERE AP_MAC = ?', (apmac,))
                                await db2.commit()
                                if answer[0][1] != None:
                                    await Send(chatid[0][0], photo=FSInputFile(f"media/{answer[0][1]}"), Text=answer[0][0])
                                else:
                                    await Send(chatid[0][0], photo=None, Text=answer[0][0])

                

loop = asyncio.new_event_loop()
loop.create_task(WaitMessage())
loop.create_task(bot.delete_webhook(drop_pending_updates=True))
loop.create_task(dp.start_polling(bot))
asyncio.set_event_loop(loop)
loop.run_forever()