import redis
import aiosqlite
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram.types import FSInputFile

router = Router()
clinetpos = redis.Redis(host='localhost', port=6379, db=2, decode_responses=True)

# Хэндлер на команду /start
@router.message(Command(commands=["start"]))
async def cmd_start(message: types.Message):
    builder = ReplyKeyboardBuilder()
    builder.add(types.KeyboardButton(text="📱 Отправить", request_contact=True))
    builder.adjust(2)
    await message.answer(f"Здраствуйте, Вас приветсвует бот навигатор. Я помогу вам в ориентировании на территории мероприятия.\n"
                         f"Для правлиной работы бота, необходимо подключится к открытой WiFi сети мероприятия и авторизоваться с помощью номера телефона.\n"
                         f"Помимо авторизации, необходимо предоставить боту доступ к Вашему номеру телефона в телеграмме. Нажмите на кнопку ниже, чтобы отправить контакт", reply_markup=builder.as_markup(resize_keyboard=True))
#Хэндлер на обработку полученного контакта
@router.message(F.contact)
async def get_contact(message: types.Message):
    contact = message.contact
    builder = ReplyKeyboardBuilder()
    builder.add(types.KeyboardButton(text="🚩Где я нахожусь?"))
    builder.adjust(2)
    async with aiosqlite.connect('TGContacts.db') as db:
        await db.execute('INSERT OR REPLACE INTO Contacts (PhoneNumber, ChatID)'
                                'VALUES (?,?)', (contact.phone_number, message.chat.id))
        await db.commit()
    await message.answer(f"Спасибо, {contact.first_name}.\n"
                         f"Ваш номер {contact.phone_number} был получен\n"
                         f"Теперь Вы сможете получать информацию о посещаемых зонах мероприятия!",
                         reply_markup=builder.as_markup(resize_keyboard=True))
#Хэндлер на определение местоположения
@router.message(F.text == "🚩Где я нахожусь?")
async def productList_handler(message: types.Message):
    apmac = clinetpos.get(message.chat.id)
    if apmac != None:
        async with aiosqlite.connect('Positions.db') as db:
            answer = await db.execute_fetchall('SELECT PosText, PicName FROM Positions WHERE AP_MAC = ?', (apmac,))
            await db.commit()
            if answer[0][1] != None:
                await message.answer_photo(photo=FSInputFile(f"media/{answer[0][1]}"), caption=answer[0][0])
            else:
                await message.answe(photo=FSInputFile(f"media/{answer[0][1]}"), caption=answer[0][0])

    else:
        await message.reply('Не удалось определить Ваше местоположение. Проверьте, предоставили ли Вы доступ к своему номеру телефона'
                            ', совпадает ли номер телефона телеграмм аккаунта с тем который вводился при WiFi авторизации.')
