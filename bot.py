import asyncio
import pytz
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from db import init_db, add_user, get_all_users
from schedule import schedule
from furri import get_random_furry_image



TOKEN = "8132234913:AAGmrItgHHGqjMAwPJaJAMQj5PTkz5RDWMk"

bot = Bot(token=TOKEN)
dp = Dispatcher()

moscow_tz = pytz.timezone("Europe/Moscow")

# Словарь сокращённых и полных названий
DAY_NAMES = {
    "ПН": "Понедельник",
    "ВТ": "Вторник",
    "СР": "Среда",
    "ЧТ": "Четверг",
    "ПТ": "Пятница",
    "СБ": "Суббота",
    "ВС": "Воскресенье"
}


def get_day(offset=0) -> str:
    days = ["ПН", "ВТ", "СР", "ЧТ", "ПТ", "СБ", "ВС"]
    today = datetime.now(moscow_tz).date()
    idx = (today.weekday() + offset) % 7
    return days[idx]

def format_schedule(day: str) -> str:
    """Форматирование расписания для дня"""
    full_day = DAY_NAMES.get(day, day)  # получаем полное название

    if day == "ВС":
        return "Выходной!"

    lessons = schedule.get(day, [])
    if not lessons:
        return f"📭 На {full_day} занятий нет"

    text = f"📅 {full_day}, группа 10903723.\n"
    for lesson in lessons:
        t = lesson["time"]
        subj = lesson["subject"]
        room = lesson["room"]
        teacher = lesson["teacher"]
        frame = lesson["frame"]
        ltype = lesson.get("type", "")

        if ltype:
            text += f"\n⏰ {t}\n      • ({ltype}) {subj} {teacher} а {room}, корп. {frame}\n"
        else:
            text += f"\n⏰ {t}\n      • {subj} {teacher} а {room}, корп. {frame}\n"

    return text


def reply_menu():
    kb = [
        [KeyboardButton(text="🏠 Главное меню")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def main_menu():
    today = get_day(0)
    tomorrow = get_day(1)

    kb = [
        [InlineKeyboardButton(text=f"🗓️ Сегодня ({today})", callback_data="today"),
         InlineKeyboardButton(text=f"🗓️ Завтра ({tomorrow})", callback_data="tomorrow")],
        [InlineKeyboardButton(text="📖 Выбрать день недели", callback_data="choose_day")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def days_menu(row_size: int = 2):
    days = ["ПН", "ВТ", "СР", "ЧТ", "ПТ", "СБ"]
    kb = []
    for i in range(0, len(days), row_size):
        row = [
            InlineKeyboardButton(text=day, callback_data=f"day_{day}")
            for day in days[i:i+row_size]
        ]
        kb.append(row)

    kb.append([InlineKeyboardButton(text="⬅ Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=kb)


# ====================== Вспомогательные ======================

def get_user_name(user: types.User) -> str:
    if user.first_name:
        return user.first_name
    elif user.username:
        return f"@{user.username}"
    return "Студент"


# ====================== Хэндлеры ======================

@dp.message(Command("all"))
async def all_users_handler(message: types.Message):
    users = get_all_users()
    if not users:
        await message.answer("В базе пока нет пользователей.")
        return

    text = "👥 Пользователи в базе:\n\n"
    for user_id, username in users:
        text += f"ID: {user_id}, username: @{username if username else 'нет'}\n"

    await message.answer(text)


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    add_user(message.from_user.id, message.from_user.username)
    name = get_user_name(message.from_user)

    text = (
        f"👋 Привет, <b>{name}</b>!\n\n"
        f"Это бот расписания (<b>cveulxd</b>) 📚\n"
        f"Группа: <b>10903723</b>\n\n"
        f"Выбирай действие ниже 👇"
    )

    await message.answer(
        text,
        reply_markup=main_menu(),  # inline меню
        parse_mode="HTML"
    )

    # отправляем reply клавиатуру
    await message.answer("Для быстрого доступа жми кнопку ниже 👇", reply_markup=reply_menu())

@dp.message(lambda msg: msg.text == "🏠 Главное меню")
async def reply_main_menu(message: types.Message):
    name = get_user_name(message.from_user)
    text = (
        f"🏫 <b>Главное меню</b>\n\n"
        f"Привет, <b>{name}</b>! Здесь ты можешь посмотреть расписание группы <b>10903723</b>.\n"
        f"Выбери нужный пункт ниже 👇"
    )

    await message.answer(text, reply_markup=main_menu(), parse_mode="HTML")

# ====================== Callback-обработчик ======================

@dp.callback_query()
async def callbacks(call: types.CallbackQuery):
    data = call.data

    if data == "today":
        await call.message.edit_text(format_schedule(get_day(0)), reply_markup=main_menu())
    elif data == "tomorrow":
        await call.message.edit_text(format_schedule(get_day(1)), reply_markup=main_menu())
    elif data == "choose_day":
        await call.message.edit_text(
            "📅 <b>Выбери день недели</b>\n\n"
            "Нажми на кнопку ниже, чтобы посмотреть расписание на выбранный день.\n"
            "Все занятия для группы <b>10903723</b>.",
            reply_markup=days_menu(row_size=3),
            parse_mode="HTML"
        )
    elif data.startswith("day_"):
        day = data.split("_", 1)[1]
        await call.message.edit_text(format_schedule(day), reply_markup=main_menu())
    elif data == "back_main":
        name = get_user_name(call.from_user)
        await call.message.edit_text(
            f"🏫 <b>Главное меню</b>\n\n"
            f"Привет, <b>{name}</b>! Здесь ты можешь посмотреть расписание группы <b>10903723</b>.\n"
            f"Выбери нужный пункт ниже 👇",
            reply_markup=main_menu(),
            parse_mode="HTML"
        )
    elif data == "furry_test":
        img_url = get_random_furry_image()
        if img_url:
            await call.message.answer_photo(img_url, caption="Ты 🦊")
        else:
            await call.answer("Не удалось загрузить фурри :(", show_alert=True)


# ====================== Запуск ======================

async def main():
    init_db()
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    asyncio.run(main())
