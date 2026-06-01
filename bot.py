import asyncio
import pytz
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from db import init_db, add_user, get_all_users
from schedule import schedule1, schedule2
from furri import get_random_furry_image

from aiogram.client.session.aiohttp import AiohttpSession

session = AiohttpSession(timeout=60)  # вместо дефолтных ~5 секунд


TOKEN = "8132234913:AAGmrItgHHGqjMAwPJaJAMQj5PTkz5RDWMk"
bot = Bot(token=TOKEN, session=session)
dp = Dispatcher()

moscow_tz = pytz.timezone("Europe/Moscow")
DAY_NAMES = {
    "ПН": "Понедельник",
    "ВТ": "Вторник",
    "СР": "Среда",
    "ЧТ": "Четверг",
    "ПТ": "Пятница",
    "СБ": "Суббота",
    "ВС": "Воскресенье"
}


# ---- ДАТА / НЕДЕЛЯ / ДЕНЬ ----

def get_date_with_offset(offset: int = 0) -> datetime.date:
    """Возвращает дату в часовом поясе Moscow с указанным смещением в днях."""
    return (datetime.now(moscow_tz) + timedelta(days=offset)).date()


def get_day_for_date(date_obj: datetime.date) -> str:
    """Возвращает код дня (ПН..ВС) для переданной даты."""
    days = ["ПН", "ВТ", "СР", "ЧТ", "ПТ", "СБ", "ВС"]
    return days[date_obj.weekday()]


def get_day(offset: int = 0) -> str:
    """Совместимость: вернуть код дня с учётом offset (0 = сегодня)."""
    target = get_date_with_offset(offset)
    return get_day_for_date(target)


def get_number_week(target_date: datetime.date = None) -> int:
    """
    Возвращает 1 или 2 — номер недели (в вашей логике: старт 01.09.2025).
    Если target_date не указан — берётся текущая дата в МСК.
    """
    if target_date is None:
        target_date = get_date_with_offset(0)
    start_date = datetime(2025, 9, 1).date()
    delta_days = (target_date - start_date).days
    week_number = delta_days // 7 + 1
    return 1 if week_number % 2 == 1 else 2


def is_first_week(target_date: datetime.date = None) -> bool:
    return get_number_week(target_date) == 1


def get_week_period(target_date: datetime.date) -> tuple:
    """
    Возвращает кортеж (start_date, end_date) для недели, к которой относится target_date.
    Неделя считается с понедельника по воскресенье.
    """
    # weekday(): 0 = Monday, 6 = Sunday
    start_of_week = target_date - timedelta(days=target_date.weekday())
    end_of_week = start_of_week + timedelta(days=6)
    return start_of_week, end_of_week


def get_week_info(target_date: datetime.date = None) -> str:
    """
    Возвращает строку вида:
    'Неделя №2 — dd.mm.YYYY - dd.mm.YYYY'
    где период это дата начала (понедельник) — дата конца (воскресенье).
    """
    if target_date is None:
        target_date = get_date_with_offset(0)
    week_num = get_number_week(target_date)
    start, end = get_week_period(target_date)
    return f"Неделя №{week_num} — {start.strftime('%d.%m.%Y')} - {end.strftime('%d.%m.%Y')}"


def get_next_date_for_day(day_code: str) -> datetime.date:
    """
    Вернёт ближайшую дату >= сегодня, соответствующую day_code.
    Например, если сегодня — воскресенье, и запросили 'ПН' — вернётся следующий понедельник.
    """
    days = ["ПН", "ВТ", "СР", "ЧТ", "ПТ", "СБ", "ВС"]
    target_idx = days.index(day_code)
    today = get_date_with_offset(0)
    today_idx = today.weekday()  # 0..6
    delta = (target_idx - today_idx) % 7
    return today + timedelta(days=delta)


# ---- РАСПИСАНИЕ ----

def get_schedule(day: str, target_date: datetime.date = None) -> list:
    """Вернуть список занятий для заданного дня с учётом недели, рассчитанной от target_date."""
    if is_first_week(target_date):
        return schedule1.get(day, [])
    else:
        return schedule2.get(day, [])


def format_schedule(day: str, target_date: datetime.date = None) -> str:
    """
    Форматирует текст расписания для day (код дня) и целевой даты target_date.
    Если target_date не задан — используется сегодня.
    """
    if target_date is None:
        target_date = get_date_with_offset(0)

    full_day = DAY_NAMES.get(day, day)
    week_info = get_week_info(target_date)

    # Заголовок: день + дата + группа + неделя (период)
    text = f"\n📅 {full_day}, {target_date.strftime('%d.%m.%Y')}, группа 10903723.\n{week_info}\n"

    # Если воскресенье — отметим выходной (но всё равно покажем дату/неделю в заголовке)
    if day == "ВС":
        text += "\nВыходной!"
        return text

    lessons = get_schedule(day, target_date)
    if not lessons:
        text += f"\n📭 На {full_day} занятий нет"
        return text

    for lesson in lessons:
        t = lesson.get("time", "")
        subj = lesson.get("subject", "")
        room = lesson.get("room", "")
        teacher = lesson.get("teacher", "")
        frame = lesson.get("frame", "")
        ltype = lesson.get("type", "")

        if ltype:
            text += f"\n⏰ {t}\n      • ({ltype}) {subj} {teacher}, ауд. {room}, корп. {frame}\n"
        else:
            text += f"\n⏰ {t}\n      • {subj} {teacher}, ауд. {room}, корп. {frame}\n"

    return text


# ---- КНОПКИ / МЕНЮ ----

def reply_menu():
    kb = [
        [KeyboardButton(text="🏠 Главное меню")],
        [KeyboardButton(text="💾 Гугл диск")]
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


# ---- УТИЛИТЫ ----

def get_user_name(user: types.User) -> str:
    if user.first_name:
        return user.first_name
    elif user.username:
        return f"@{user.username}"
    return "Студент"


# ---- ХЭНДЛЕРЫ ----

# @dp.message(Command("all"))
# async def all_users_handler(message: types.Message):
#     users = get_all_users()
#     if not users:
#         await message.answer("В базе пока нет пользователей.")
#         return
#
#     text = "👥 Пользователи в базе:\n\n"
#     for user_id, username in users:
#         text += f"ID: {user_id}, username: @{username if username else 'нет'}\n"
#
#     await message.answer(text)


@dp.message(lambda msg: msg.text == "💾 Гугл диск")
async def send_drive_link(message: types.Message):
    await message.answer(
        "<a href='https://drive.google.com/drive/folders/1Jb8rQLEG9z5uf068cAkeIsRJu0WXljxP'> Ссылка на гугл диск димасика</a>",
        parse_mode="HTML"
    )


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    add_user(message.from_user.id, message.from_user.username)
    name = get_user_name(message.from_user)

    text = (
        f"👋 Привет, <b>{name}</b>!\n\n"
        f"Это бот расписания (<b>cveulxd</b>) 📚\n"
        f"Группа: <b>10903723</b>\n"
        f"{get_week_info()}\n\n"
        f"Выбирай действие ниже 👇"
    )

    await message.answer(
        text,
        reply_markup=main_menu(),
        parse_mode="HTML"
    )
    await message.answer("Для быстрого доступа жми кнопку ниже 👇", reply_markup=reply_menu())


@dp.message(lambda msg: msg.text == "🏠 Главное меню")
async def reply_main_menu(message: types.Message):
    name = get_user_name(message.from_user)
    text = (
        f"🏫 <b>Главное меню</b>\n\n"
        f"Привет, <b>{name}</b>! Здесь ты можешь посмотреть расписание группы <b>10903723</b>.\n"
        f"{get_week_info()}\n\n"
        f"Выбери нужный пункт ниже 👇"
    )

    await message.answer(text, reply_markup=main_menu(), parse_mode="HTML")


@dp.callback_query()
async def callbacks(call: types.CallbackQuery):
    data = call.data
    if data == "today":
        target = get_date_with_offset(0)
        await call.message.edit_text(format_schedule(get_day(0), target_date=target), reply_markup=main_menu())
    elif data == "tomorrow":
        target = get_date_with_offset(1)
        await call.message.edit_text(format_schedule(get_day(1), target_date=target), reply_markup=main_menu())
    elif data == "choose_day":
        await call.message.edit_text(
            "📅 <b>Выбери день недели</b>\n\n"
            "Нажми на кнопку ниже, чтобы посмотреть расписание на выбранный день.\n"
            f"{get_week_info()}\n\n"
            "Все занятия для группы <b>10903723</b>.",
            reply_markup=days_menu(row_size=3),
            parse_mode="HTML"
        )
    elif data.startswith("day_"):
        day = data.split("_", 1)[1]
        target = get_next_date_for_day(day)
        await call.message.edit_text(format_schedule(day, target_date=target), reply_markup=main_menu())
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


# ---- MAIN ----

async def main():
    init_db()
    await dp.start_polling(bot, skip_updates=True)


if __name__ == "__main__":
    asyncio.run(main())
