import asyncio
import pytz
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from db import init_db, add_user,get_all_users
from schedule import schedule
from furri import get_random_furry_image

TOKEN = "8132234913:AAGmrItgHHGqjMAwPJaJAMQj5PTkz5RDWMk"

bot = Bot(token=TOKEN)
dp = Dispatcher()

moscow_tz = pytz.timezone("Europe/Moscow")

def get_day(offset=0) -> str:
    days = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
    today = datetime.now(moscow_tz).date()
    idx = (today.weekday() + offset) % 7
    return days[idx]

def format_schedule(day: str) -> str:
    if day == "Воскресенье":
        return "Выходной!"

    lessons = schedule.get(day, [])
    if not lessons:
        return f"📭 На {day} занятий нет"

    text = f"📅 {day}, группа 10903723.\n"
    for lesson in lessons:
        t = lesson["time"]
        subj = lesson["subject"]
        room = lesson["room"]
        teacher = lesson["teacher"]
        frame = lesson["frame"]
        ltype = lesson.get("type", "")
        if ltype:
            text += f"\n⏰ {t}\n      • ({ltype}) {subj} {teacher} а {room}, корп. {frame}"
        else:
            text += f"\n⏰ {t}\n      • {subj} {teacher} а {room}, корп. {frame}"
    return text


def main_menu():
    today = get_day(0)
    tomorrow = get_day(1)

    kb = [
        [InlineKeyboardButton(text=f"📅 Сегодня ({today})", callback_data="today")],
        [InlineKeyboardButton(text=f"📆 Завтра ({tomorrow})", callback_data="tomorrow")],
        [InlineKeyboardButton(text="📖 Выбрать день недели", callback_data="choose_day")],
        [InlineKeyboardButton(text="🦊 Какой ты фури?", callback_data="furry_test")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def back_to_main_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅ В главное меню", callback_data="back_main")]
        ]
    )

def days_menu(row_size: int = 2):
    days = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота"]
    kb = []

    for i in range(0, len(days), row_size):
        row = [
            InlineKeyboardButton(text=day, callback_data=f"day_{day}")
            for day in days[i:i+row_size]
        ]
        kb.append(row)

    kb.append([InlineKeyboardButton(text="⬅ Назад", callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_user_name(user: types.User) -> str:
    if user.first_name:
        return user.first_name
    elif user.username:
        return f"@{user.username}"
    return "Студент"

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

    await message.answer(text, reply_markup=main_menu(), parse_mode="HTML")


@dp.callback_query()
async def callbacks(call: types.CallbackQuery):
    if call.data == "today":
        day = get_day(0)
        await call.message.edit_text(format_schedule(day), reply_markup=back_to_main_menu())
    elif call.data == "tomorrow":
        day = get_day(1)
        await call.message.edit_text(format_schedule(day), reply_markup=back_to_main_menu())
    elif call.data == "choose_day":
        await call.message.edit_text(
            "📅 <b>Выбери день недели</b>\n\n"
            "Нажми на кнопку ниже, чтобы посмотреть расписание на выбранный день.\n"
            "Все занятия для группы <b>10903723</b>.",
            reply_markup=days_menu(row_size=3),
            parse_mode="HTML"
        )
    elif call.data.startswith("day_"):
        day = call.data.split("_", 1)[1]
        await call.message.edit_text(format_schedule(day), reply_markup=days_menu(row_size=3))
    elif call.data == "back_main":
        name = get_user_name(call.from_user)
        await call.message.edit_text(
            f"🏫 <b>Главное меню</b>\n\n"
            f"Привет, <b>{name}</b>! Здесь ты можешь посмотреть расписание группы <b>10903723</b>.\n"
            f"Выбери нужный пункт ниже 👇",
            reply_markup=main_menu(),
            parse_mode="HTML"
        )
    elif call.data == "furry_test":
        img_url = get_random_furry_image()
        if img_url:
            await call.message.answer_photo(img_url, caption="Ты 🦊")
        else:
            await call.answer("Не удалось загрузить фурри :(", show_alert=True)

async def main():
    init_db()
    await dp.start_polling(bot,skip_updates=True)

if __name__ == "__main__":
    asyncio.run(main())
