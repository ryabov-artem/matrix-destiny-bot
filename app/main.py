import asyncio
import os
import uuid
import re

from ai import (
    interpret_personal_matrix,
    interpret_compatibility,
    interpret_money_channel,
    interpret_purpose,
    interpret_karma,
    interpret_child_matrix
)

from database import (
    init_db,
    save_user,
    get_today_card,
    save_daily_card,
    save_spread,
    get_user_spreads,
    get_users_count,
    get_daily_cards_count,
    get_spreads_count,
    get_recent_spreads,
    get_recent_users,
    get_spread_type_stats,
    get_top_users,
    get_recent_payments,
    get_payments_stats,
    get_sales_funnel,
    get_all_user_ids,
    can_use_free_spread,
    mark_free_spread_used,
    get_balance,
    spend_balance,
    add_balance
)

from matrix.calculator import calculate_personal_matrix, calculate_compatibility_matrix

from aiogram import Bot, Dispatcher, F
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv
from yookassa import Configuration, Payment

load_dotenv("/opt/bots/matrix_bot/.env")

BOT_TOKEN = os.getenv("BOT_TOKEN")
PROXY_URL = os.getenv("PROXY_URL")
PROVIDER_TOKEN = os.getenv("PROVIDER_TOKEN")
YOOKASSA_SHOP_ID = os.getenv("YOOKASSA_SHOP_ID")
YOOKASSA_SECRET_KEY = os.getenv("YOOKASSA_SECRET_KEY")
YOOKASSA_RETURN_URL = os.getenv("YOOKASSA_RETURN_URL")

if YOOKASSA_SHOP_ID and YOOKASSA_SECRET_KEY:
    Configuration.account_id = YOOKASSA_SHOP_ID
    Configuration.secret_key = YOOKASSA_SECRET_KEY

ADMIN_ID = 185955220

session = AiohttpSession(proxy=PROXY_URL)
bot = Bot(token=BOT_TOKEN, session=session)
dp = Dispatcher()


class MatrixStates(StatesGroup):
    awaiting_personal_matrix_date = State()
    awaiting_compatibility_dates = State()
    awaiting_child_matrix_date = State()
    awaiting_money_channel_date = State()
    awaiting_purpose_date = State()
    awaiting_karma_date = State()


class AdminStates(StatesGroup):
    awaiting_broadcast_text = State()
    awaiting_broadcast_confirm = State()
    awaiting_balance_grant = State()
    awaiting_balance_writeoff = State()




def markdown_bold_to_html(text):
    text = text.replace("<br>", "\n").replace("<br/>", "\n").replace("<br />", "\n")
    return re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", text)


def get_main_keyboard(user_id):
    keyboard = [
        [KeyboardButton(text="✨ Личная матрица"), KeyboardButton(text="❤️ Совместимость")],
        [KeyboardButton(text="👶 Детская матрица"), KeyboardButton(text="💰 Денежный канал")],
        [KeyboardButton(text="🎯 Предназначение"), KeyboardButton(text="🔥 Кармические задачи")],
        [KeyboardButton(text="💎 Баланс"), KeyboardButton(text="ℹ️ О боте")]
    ]

    if user_id == ADMIN_ID:
        keyboard.append([KeyboardButton(text="⚙️ Админка")])

    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


admin_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="👥 Пользователи"), KeyboardButton(text="📈 Статистика")],
        [KeyboardButton(text="📜 Последние разборы"), KeyboardButton(text="📊 Популярность")],
        [KeyboardButton(text="📣 Рассылка"), KeyboardButton(text="🎁 Акции")],
        [KeyboardButton(text="💰 Платежи")],
        [KeyboardButton(text="📈 Воронка"), KeyboardButton(text="🏆 Топ")],
        [KeyboardButton(text="➕ Начислить баланс"), KeyboardButton(text="➖ Списать баланс")],
        [KeyboardButton(text="⬅️ Назад")]
    ],
    resize_keyboard=True
)




shop_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🪙 Купить 1 разбор — 99 ₽")],
        [KeyboardButton(text="💎 Купить 5 разборов — 299 ₽")],
        [KeyboardButton(text="✨ Купить 10 разборов — 499 ₽")],
        [KeyboardButton(text="👑 Купить 20 разборов — 799 ₽")],
        [KeyboardButton(text="⬅️ Назад")]
    ],
    resize_keyboard=True
)


broadcast_confirm_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="✅ Отправить"), KeyboardButton(text="❌ Отмена")]
    ],
    resize_keyboard=True
)


promo_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🎁 Акция: 5 разборов")],
        [KeyboardButton(text="✨ Напомнить про личную матрицу")],
        [KeyboardButton(text="💰 Скидка на разборы")],
        [KeyboardButton(text="⬅️ Назад")]
    ],
    resize_keyboard=True
)


async def user_has_spread_access(user_id):
    if user_id == ADMIN_ID:
        return True

    if await can_use_free_spread(user_id):
        return True

    if await get_balance(user_id) > 0:
        return True

    return False


async def charge_user_for_spread(user_id):
    if await can_use_free_spread(user_id):
        await mark_free_spread_used(user_id)
    elif await get_balance(user_id) > 0:
        await spend_balance(user_id)


async def no_access_message(message: Message):
    await message.answer(
        "💎 Бесплатный разбор уже использован.\n\n"
        "Доступные тарифы:\n"
        "• 1 разбор — 99 ₽\n"
        "• 5 разборов — 299 ₽\n"
        "• 10 разборов — 499 ₽\n"
        "• 20 разборов — 799 ₽\n\n"
        "Пополните баланс и возвращайтесь за новым разбором ✨"
    )


@dp.message(CommandStart())
async def start(message: Message):
    await save_user(message.from_user)

    await message.answer(
        "✨ <b>Матрица судьбы</b>\n\n"
        "Добро пожаловать!\n\n"
        "Персональные разборы по системе «Матрица судьбы» (22 Аркана).\n\n"
        "<b>Доступно:</b>\n\n"
        "✨ Личная матрица\n"
        "❤️ Совместимость\n"
        "👶 Детская матрица\n"
        "💰 Денежный канал\n"
        "🎯 Предназначение\n"
        "🔥 Кармические задачи\n\n"
        "💎 <b>Для новых пользователей доступен бесплатный разбор.</b>\n\n"
        "Выберите интересующий раздел ниже 👇",
        parse_mode="HTML",
        reply_markup=get_main_keyboard(message.from_user.id)
    )


@dp.message(F.text.startswith("/give"))
async def admin_give_balance(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("Нет доступа.")
        return

    parts = message.text.split()

    if len(parts) != 3:
        await message.answer(
            "Формат команды:\n"
            "/give USER_ID COUNT\n\n"
            "Пример:\n"
            "/give 185955220 5"
        )
        return

    try:
        target_user_id = int(parts[1])
        amount = int(parts[2])
    except ValueError:
        await message.answer("USER_ID и COUNT должны быть числами.")
        return

    if amount <= 0:
        await message.answer("COUNT должен быть больше 0.")
        return

    await add_balance(target_user_id, amount)

    await message.answer(
        f"✅ Начислено {amount} разбор(ов).\n"
        f"Пользователь: {target_user_id}"
    )

    try:
        await bot.send_message(
            chat_id=target_user_id,
            text=(
                f"💎 Оплата успешно получена!\n\n"
                f"На баланс зачислено: {amount} разбор(ов).\n\n"
                f"✨ Выберите интересующий раздел в меню."
            )
        )
    except Exception:
        pass


@dp.message(F.text == "💎 Баланс")
async def balance(message: Message):
    await save_user(message.from_user)

    balance_count = await get_balance(message.from_user.id)

    await message.answer(
        f"💎 Баланс\n\n"
        f"На счету: {balance_count} разбор(ов)\n\n"
        f"Один разбор открывает любой раздел на выбор:\n\n"
        f"✨ Личная матрица\n"
        f"❤️ Совместимость\n"
        f"👶 Детская матрица\n"
        f"💰 Денежный канал\n"
        f"🎯 Предназначение\n"
        f"🔥 Кармические задачи\n\n"
        f"Пополните баланс и откройте новые разборы 👇",
        reply_markup=shop_keyboard
    )




def create_yookassa_payment(user_id: int, count: int, amount_rub: int):
    payment = Payment.create({
        "amount": {
            "value": f"{amount_rub}.00",
            "currency": "RUB"
        },
        "capture": True,
        "confirmation": {
            "type": "redirect",
            "return_url": YOOKASSA_RETURN_URL
        },
        "description": f"Матрица судьбы: {count} разбор(ов)",
        "metadata": {
            "user_id": str(user_id),
            "count": str(count)
        }
    }, str(uuid.uuid4()))

    return payment


@dp.message(F.text.contains("Купить 1 разбор"))
async def buy_one_spread(message: Message):
    if not YOOKASSA_SHOP_ID or not YOOKASSA_SECRET_KEY:
        await message.answer("Оплата временно недоступна. Не найдены данные ЮKassa.")
        return

    try:
        payment = create_yookassa_payment(message.from_user.id, 1, 99)
        url = payment.confirmation.confirmation_url
    except Exception as e:
        await message.answer(f"Не удалось создать платёж. Ошибка: {e}")
        return

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💳 Перейти к оплате", url=url)]
        ]
    )

    await message.answer(
        "🪙 1 разбор\n\n"
        "Стоимость: 99 ₽\n\n"
        "Нажмите кнопку ниже и выберите удобный способ оплаты: карта, СБП, SberPay или другой доступный способ.",
        reply_markup=keyboard
    )


@dp.message(F.text.contains("Купить 5 разборов"))
async def buy_five_spreads(message: Message):
    if not YOOKASSA_SHOP_ID or not YOOKASSA_SECRET_KEY:
        await message.answer("Оплата временно недоступна. Не найдены данные ЮKassa.")
        return

    try:
        payment = create_yookassa_payment(message.from_user.id, 5, 299)
        url = payment.confirmation.confirmation_url
    except Exception as e:
        await message.answer(f"Не удалось создать платёж. Ошибка: {e}")
        return

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💳 Перейти к оплате", url=url)]
        ]
    )

    await message.answer(
        "💎 5 разборов\n\n"
        "Стоимость: 299 ₽\n\n"
        "Нажмите кнопку ниже и выберите удобный способ оплаты: карта, СБП, SberPay или другой доступный способ.",
        reply_markup=keyboard
    )




@dp.message(F.text.contains("Купить 10 разборов"))
async def buy_ten_spreads(message: Message):
    if not YOOKASSA_SHOP_ID or not YOOKASSA_SECRET_KEY:
        await message.answer("Оплата временно недоступна. Не найдены данные ЮKassa.")
        return

    try:
        payment = create_yookassa_payment(message.from_user.id, 10, 499)
        url = payment.confirmation.confirmation_url
    except Exception as e:
        await message.answer(f"Не удалось создать платёж. Ошибка: {e}")
        return

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💳 Перейти к оплате", url=url)]
        ]
    )

    await message.answer(
        "✨ 10 разборов\n\n"
        "Стоимость: 499 ₽\n\n"
        "Выгодный пакет для нескольких вопросов: отношения, работа, деньги и личные ситуации.\n\n"
        "Нажмите кнопку ниже и выберите удобный способ оплаты.",
        reply_markup=keyboard
    )


@dp.message(F.text.contains("Купить 20 разборов"))
async def buy_twenty_spreads(message: Message):
    if not YOOKASSA_SHOP_ID or not YOOKASSA_SECRET_KEY:
        await message.answer("Оплата временно недоступна. Не найдены данные ЮKassa.")
        return

    try:
        payment = create_yookassa_payment(message.from_user.id, 20, 799)
        url = payment.confirmation.confirmation_url
    except Exception as e:
        await message.answer(f"Не удалось создать платёж. Ошибка: {e}")
        return

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💳 Перейти к оплате", url=url)]
        ]
    )

    await message.answer(
        "👑 20 разборов\n\n"
        "Стоимость: 799 ₽\n\n"
        "Самый выгодный пакет для тех, кто планирует несколько разборов.\n\n"
        "Нажмите кнопку ниже и выберите удобный способ оплаты.",
        reply_markup=keyboard
    )


@dp.message(F.text == "✨ Личная матрица")
async def matrix_personal(message: Message, state: FSMContext):
    await save_user(message.from_user)
    user_id = message.from_user.id

    if not await user_has_spread_access(user_id):
        await no_access_message(message)
        return

    await state.set_state(MatrixStates.awaiting_personal_matrix_date)

    await message.answer(
        "✨ <b>Личная матрица</b>\n\n"
        "Введите дату рождения в формате:\n\n"
        "<b>ДД.ММ.ГГГГ</b>",
        parse_mode="HTML"
    )


@dp.message(F.text == "❤️ Совместимость")
async def matrix_compatibility(message: Message, state: FSMContext):
    await save_user(message.from_user)
    user_id = message.from_user.id

    if not await user_has_spread_access(user_id):
        await no_access_message(message)
        return

    await state.set_state(MatrixStates.awaiting_compatibility_dates)

    await message.answer(
        "❤️ <b>Совместимость</b>\n\n"
        "Введите две даты рождения, каждую с новой строки:\n\n"
        "<b>ДД.ММ.ГГГГ</b>\n"
        "<b>ДД.ММ.ГГГГ</b>",
        parse_mode="HTML"
    )


@dp.message(F.text == "👶 Детская матрица")
async def matrix_child(message: Message, state: FSMContext):
    await save_user(message.from_user)
    user_id = message.from_user.id

    if not await user_has_spread_access(user_id):
        await no_access_message(message)
        return

    await state.set_state(MatrixStates.awaiting_child_matrix_date)

    await message.answer(
        "👶 <b>Детская матрица</b>\n\n"
        "Введите дату рождения ребёнка в формате:\n\n"
        "<b>ДД.ММ.ГГГГ</b>",
        parse_mode="HTML"
    )


@dp.message(F.text == "💰 Денежный канал")
async def matrix_money(message: Message, state: FSMContext):
    await save_user(message.from_user)
    user_id = message.from_user.id

    if not await user_has_spread_access(user_id):
        await no_access_message(message)
        return

    await state.set_state(MatrixStates.awaiting_money_channel_date)

    await message.answer(
        "💰 <b>Денежный канал</b>\n\n"
        "Введите дату рождения в формате:\n\n"
        "<b>ДД.ММ.ГГГГ</b>",
        parse_mode="HTML"
    )


@dp.message(F.text == "🎯 Предназначение")
async def matrix_purpose(message: Message, state: FSMContext):
    await save_user(message.from_user)
    user_id = message.from_user.id

    if not await user_has_spread_access(user_id):
        await no_access_message(message)
        return

    await state.set_state(MatrixStates.awaiting_purpose_date)

    await message.answer(
        "🎯 <b>Предназначение</b>\n\n"
        "Введите дату рождения в формате:\n\n"
        "<b>ДД.ММ.ГГГГ</b>",
        parse_mode="HTML"
    )


@dp.message(F.text == "🔥 Кармические задачи")
async def matrix_karma(message: Message, state: FSMContext):
    await save_user(message.from_user)
    user_id = message.from_user.id

    if not await user_has_spread_access(user_id):
        await no_access_message(message)
        return

    await state.set_state(MatrixStates.awaiting_karma_date)

    await message.answer(
        "🔥 <b>Кармические задачи</b>\n\n"
        "Введите дату рождения в формате:\n\n"
        "<b>ДД.ММ.ГГГГ</b>",
        parse_mode="HTML"
    )


@dp.message(F.text == "📜 История")
async def history(message: Message):
    await save_user(message.from_user)

    spreads = await get_user_spreads(message.from_user.id, limit=5)

    if not spreads:
        await message.answer(
            "📜 История пока пустая.\n\n"
            "Сделайте разбор, и он появится здесь."
        )
        return

    text = "📜 Последние разборы:\n\n"

    for spread in spreads:
        text += (
            f"✨ #{spread['id']} — {spread['spread_type']}\n"
            f"Вопрос: {spread['question']}\n"
            f"Данные: {spread['cards']}\n\n"
        )

    await message.answer(text)


@dp.message(F.text == "ℹ️ О боте")
async def about(message: Message):
    await message.answer(
        "ℹ️ <b>О боте</b>\n\n"
        "Этот бот делает AI-разборы по системе <b>Матрица судьбы</b> — это метод на основе <b>22 Аркана</b>.\n\n"
        "Расчёт строится по дате рождения и показывает сочетание энергий, которые используются для мягкой интерпретации личности, отношений, предназначения и других сфер.\n\n"
        "Матрица судьбы — это отдельная система. Она отличается от классической нумерологии, где обычно работают с числом жизненного пути, числом судьбы и другими числовыми показателями.\n\n"
        "Бот предназначен для самоанализа, рефлексии и развлекательных интерпретаций. Он не предсказывает будущее наверняка и не заменяет профессиональные консультации.",
        parse_mode="HTML"
    )


@dp.message(F.text == "⚙️ Админка")
async def admin_panel(message: Message):

    if message.from_user.id != ADMIN_ID:
        await message.answer("Нет доступа.")
        return

    await message.answer("⚙️ Админка", reply_markup=admin_keyboard)


@dp.message(F.text == "⬅️ Назад")
async def back_to_main(message: Message):

    await message.answer(
        "Главное меню",
        reply_markup=get_main_keyboard(message.from_user.id)
    )


@dp.message(F.text == "📈 Статистика")
async def admin_stats(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("Нет доступа.")
        return

    await message.answer(
        "📈 Статистика Matrix\n\n"
        f"👥 Пользователей: {await get_users_count()}\n"
        f"📜 Разборов: {await get_spreads_count()}\n"
        f"💎 Формат: платные разборы по балансу"
    )


@dp.message(F.text == "👥 Пользователи")
async def admin_users(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("Нет доступа.")
        return

    users = await get_recent_users(limit=10)

    if not users:
        await message.answer("Пользователей пока нет.")
        return

    text = "👥 Последние пользователи:\n\n"

    for user in users:
        username = user["username"] or "без username"
        first_name = user["first_name"] or "без имени"

        text += (
            f"ID: {user['user_id']}\n"
            f"Имя: {first_name}\n"
            f"Username: @{username}\n"
            f"Дата: {user['created_at']}\n\n"
        )

    await message.answer(text)


@dp.message(F.text == "📜 Последние разборы")
async def admin_recent_spreads(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("Нет доступа.")
        return

    spreads = await get_recent_spreads(limit=10)

    if not spreads:
        await message.answer("Разборов пока нет.")
        return

    text = "📜 Последние разборы:\n\n"

    for spread in spreads:
        username = spread["username"] or "без username"
        first_name = spread["first_name"] or "без имени"

        text += (
            f"#{spread['id']} — {spread['spread_type']}\n"
            f"Пользователь: {first_name} / @{username}\n"
            f"ID: {spread['user_id']}\n"
            f"Вопрос: {spread['question']}\n"
            f"Дата: {spread['created_at']}\n\n"
        )

    await message.answer(text)


@dp.message(F.text == "📊 Популярность")
async def admin_popularity(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("Нет доступа.")
        return

    stats = await get_spread_type_stats()

    if not stats:
        await message.answer("📊 Пока нет данных по разборам.")
        return

    text = "📊 Популярность разборов:\n\n"

    for item in stats:
        text += f"{item['spread_type']}: {item['count']}\n"

    await message.answer(text)





@dp.message(F.text == "💰 Платежи")
async def admin_payments(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("Нет доступа.")
        return

    stats = await get_payments_stats()
    payments = await get_recent_payments(limit=10)

    text = (
        "💰 <b>Платежи</b>\n\n"
        f"📅 <b>Сегодня</b>\n"
        f"• Платежей: <b>{stats['today_count']}</b>\n"
        f"• Сумма: <b>{stats['today_amount']} ₽</b>\n"
        f"• Разборов куплено: <b>{stats['today_spreads']}</b>\n\n"
        f"📊 <b>Всего</b>\n"
        f"• Платежей: <b>{stats['total_count']}</b>\n"
        f"• Сумма: <b>{stats['total_amount']} ₽</b>\n"
        f"• Разборов куплено: <b>{stats['total_spreads']}</b>\n\n"
    )

    if payments:
        text += "🧾 <b>Последние 10 платежей</b>\n\n"

        for payment in payments:
            username = payment["username"] or "без username"
            first_name = payment["first_name"] or "без имени"

            text += (
                f"👤 {first_name} / @{username}\n"
                f"ID: <code>{payment['user_id']}</code>\n"
                f"Сумма: <b>{payment['amount']} ₽</b>\n"
                f"Разборов: <b>{payment['spreads_added']}</b>\n"
                f"Дата: {payment['created_at']}\n\n"
            )
    else:
        text += "Платежей пока нет."

    await message.answer(text, parse_mode="HTML")


@dp.message(F.text == "🎁 Акции")
async def admin_promos(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("Нет доступа.")
        return

    await message.answer(
        "🎁 Выбери готовую акцию для рассылки:",
        reply_markup=promo_keyboard
    )


@dp.message(F.text == "🎁 Акция: 5 разборов")
async def promo_five_spreads(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return

    broadcast_text = (
        "🎁 <b>Специальное предложение в Матрице судьбы</b>\n\n"
        "Получите сразу <b>5 разборов</b> по выгодной цене — 299 ₽.\n\n"
        "🔮 Можно использовать для вопросов про отношения, карьеру, деньги и личные ситуации.\n\n"
        "Нажмите 💎 Баланс, чтобы пополнить запас разборов."
    )

    await state.clear()
    await state.update_data(broadcast_text=broadcast_text)

    await message.answer(
        "📣 Предпросмотр акции:\n\n"
        f"{broadcast_text}\n\n"
        "Отправить?",
        reply_markup=broadcast_confirm_keyboard,
        parse_mode="HTML"
    )

    await state.set_state(AdminStates.awaiting_broadcast_confirm)


@dp.message(F.text == "✨ Напомнить про личную матрицу")
async def promo_daily_card(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return

    broadcast_text = (
        "✨ <b>Личная матрица уже ждёт вас</b>\n\n"
        "Откройте Матрицу судьбы и выберите подходящий разбор.\n\n"
        "Один разбор может подсветить сильные стороны, отношения и направление движения ✨"
    )

    await state.clear()
    await state.update_data(broadcast_text=broadcast_text)

    await message.answer(
        "📣 Предпросмотр акции:\n\n"
        f"{broadcast_text}\n\n"
        "Отправить?",
        reply_markup=broadcast_confirm_keyboard,
        parse_mode="HTML"
    )

    await state.set_state(AdminStates.awaiting_broadcast_confirm)


@dp.message(F.text == "💰 Скидка на разборы")
async def promo_discount(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return

    broadcast_text = (
        "💰 <b>Выгодный момент для разбора</b>\n\n"
        "Пакет из <b>5 разборов</b> сейчас выгоднее, чем покупать по одному.\n\n"
        "✨ Используйте разборы для:\n"
        "• личной матрицы;\n"
        "• совместимости;\n"
        "• детской матрицы;\n"
        "• денежного канала;\n"
        "• предназначения;\n"
        "• кармических задач.\n\n"
        "Нажмите 💎 Баланс и выберите подходящий пакет."
    )

    await state.clear()
    await state.update_data(broadcast_text=broadcast_text)

    await message.answer(
        "📣 Предпросмотр акции:\n\n"
        f"{broadcast_text}\n\n"
        "Отправить?",
        reply_markup=broadcast_confirm_keyboard,
        parse_mode="HTML"
    )

    await state.set_state(AdminStates.awaiting_broadcast_confirm)



@dp.message(F.text == "📈 Воронка")
async def admin_sales_funnel(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("Нет доступа.")
        return

    funnel = await get_sales_funnel()

    await message.answer(
        "📈 Воронка продаж\n\n"
        f"👥 Пользователей всего: {funnel['users_count']}\n"
        
        f"📜 Пользователей с разборами: {funnel['analysis_users']}\n"
        f"📊 Всего разборов: {funnel['analyses_count']}\n"
        f"💰 Совершили покупку: {funnel['paying_users']}\n"
        f"🧾 Всего платежей: {funnel['payments_count']}\n\n"
        f"📜 Конверсия в разбор: {funnel['conversion_to_analysis']}%\n"
        f"💰 Конверсия в покупку: {funnel['conversion_to_payment']}%"
    )



@dp.message(F.text == "🏆 Топ")
async def admin_top_users(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("Нет доступа.")
        return

    data = await get_top_users(10)

    text = "🏆 Топ пользователей\n\n"

    text += "💰 По покупкам:\n"
    if data["top_payers"]:
        for i, user in enumerate(data["top_payers"], start=1):
            name = user["username"] or user["first_name"] or str(user["user_id"])
            text += (
                f"{i}. {name} — {user['total_amount']} ₽ "
                f"({user['payments_count']} платежей, {user['total_spreads']} разборов)\n"
            )
    else:
        text += "Пока нет покупок.\n"

    text += "\n📜 По разборам:\n"
    if data["top_spreads"]:
        for i, user in enumerate(data["top_spreads"], start=1):
            name = user["username"] or user["first_name"] or str(user["user_id"])
            text += f"{i}. {name} — {user['spreads_count']} разборов\n"
    else:
        text += "Пока нет разборов.\n"

    await message.answer(text)


@dp.message(F.text == "📣 Рассылка")
async def admin_broadcast_start(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        await message.answer("Нет доступа.")
        return

    await state.clear()
    await state.set_state(AdminStates.awaiting_broadcast_text)

    await message.answer(
        "📣 Введи текст рассылки.\n\n"
        "Следующее сообщение будет отправлено всем пользователям."
    )





@dp.message(F.text == "➕ Начислить баланс")
async def admin_balance_grant_start(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        await message.answer("Нет доступа.")
        return
    await state.clear()
    await state.set_state(AdminStates.awaiting_balance_grant)
    await message.answer("Введите USER_ID и количество разборов:\n\nПример:\n185955220 5")


@dp.message(F.text == "➖ Списать баланс")
async def admin_balance_writeoff_start(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        await message.answer("Нет доступа.")
        return
    await state.clear()
    await state.set_state(AdminStates.awaiting_balance_writeoff)
    await message.answer("Введите USER_ID и количество разборов для списания:\n\nПример:\n185955220 5")


@dp.message(AdminStates.awaiting_balance_grant)
async def admin_balance_grant_process(message: Message):
    
    try:
        target_user_id, amount = map(int, message.text.split())
    except Exception:
        await message.answer("Неверный формат. Пример: 185955220 5", reply_markup=admin_keyboard)
        return

    if amount <= 0:
        await message.answer("Количество должно быть больше 0.", reply_markup=admin_keyboard)
        return

    await add_balance(target_user_id, amount)

    await message.answer(
        f"✅ Начислено {amount} разбор(ов).\nПользователь: {target_user_id}",
        reply_markup=admin_keyboard
    )

    try:
        await bot.send_message(
            chat_id=target_user_id,
            text=(
                f"💎 Вам начислено: {amount} разбор(ов).\n\n"
                f"✨ Выберите интересующий раздел в меню."
            )
        )
    except Exception:
        pass


@dp.message(AdminStates.awaiting_balance_writeoff)
async def admin_balance_writeoff_process(message: Message):
    
    try:
        target_user_id, amount = map(int, message.text.split())
    except Exception:
        await message.answer("Неверный формат. Пример: 185955220 5", reply_markup=admin_keyboard)
        return

    if amount <= 0:
        await message.answer("Количество должно быть больше 0.", reply_markup=admin_keyboard)
        return

    current_balance = await get_balance(target_user_id)

    if current_balance < amount:
        await message.answer(
            f"Недостаточно разборов на балансе. Сейчас: {current_balance}",
            reply_markup=admin_keyboard
        )
        return

    for _ in range(amount):
        await spend_balance(target_user_id)

    await message.answer(
        f"✅ Списано {amount} разбор(ов).\nПользователь: {target_user_id}",
        reply_markup=admin_keyboard
    )



@dp.message(MatrixStates.awaiting_personal_matrix_date)
async def process_personal_matrix_date(message: Message, state: FSMContext):
    user_id = message.from_user.id

    try:
        matrix = calculate_personal_matrix(message.text)
    except ValueError as e:
        await message.answer(f"⚠️ {e}\n\nПопробуйте ещё раз в формате ДД.ММ.ГГГГ")
        return

    await message.answer("✨ Рассчитываю вашу личную матрицу...")
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")

    try:
        interpretation = await interpret_personal_matrix(matrix)
    except Exception as e:
        await message.answer(f"Не удалось подготовить разбор. Ошибка: {e}")
        return

    await save_spread(
        user_id=user_id,
        spread_type="Личная матрица",
        question=matrix["birth_date"],
        cards=[],
        answer=interpretation
    )

    await charge_user_for_spread(user_id)

    await message.answer(
        f"✨ <b>Личная матрица</b>\n\n"
        f"📅 Дата рождения: <b>{matrix['birth_date']}</b>\n\n"
        f"🔢 <b>Основные энергии</b>\n\n"
        f"• День — {matrix['base']['day_arcana']}\n"
        f"• Месяц — {matrix['base']['month_arcana']}\n"
        f"• Год — {matrix['base']['year_arcana']}\n"
        f"• Предназначение — {matrix['base']['destiny_arcana']}\n"
        f"• Центр личности — {matrix['base']['center_arcana']}\n\n"
        f"━━━━━━━━━━\n\n"
        f"{markdown_bold_to_html(interpretation)}",
        parse_mode="HTML"
    )

    await state.clear()




@dp.message(MatrixStates.awaiting_compatibility_dates)
async def process_compatibility_dates(message: Message, state: FSMContext):
    user_id = message.from_user.id

    dates = [line.strip() for line in message.text.splitlines() if line.strip()]

    if len(dates) != 2:
        await message.answer(
            "⚠️ Нужно ввести ровно две даты, каждую с новой строки.\n\n"
            "ДД.ММ.ГГГГ\n"
            "ДД.ММ.ГГГГ"
        )
        return

    try:
        compatibility = calculate_compatibility_matrix(dates[0], dates[1])
    except ValueError as e:
        await message.answer(f"⚠️ {e}\n\nПопробуйте ещё раз.")
        return

    await message.answer("❤️ Рассчитываю совместимость...")
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")

    try:
        interpretation = await interpret_compatibility(compatibility)
    except Exception as e:
        await message.answer(f"Не удалось подготовить разбор. Ошибка: {e}")
        return

    await save_spread(
        user_id=user_id,
        spread_type="Совместимость",
        question=f"{compatibility['date1']} + {compatibility['date2']}",
        cards=[],
        answer=interpretation
    )

    await charge_user_for_spread(user_id)

    await message.answer(
        f"❤️ <b>Совместимость</b>\n\n"
        f"👤 Партнер 1: <b>{compatibility['date1']}</b>\n"
        f"👤 Партнер 2: <b>{compatibility['date2']}</b>\n\n"
        f"🔢 <b>Энергии союза</b>\n\n"
        f"• Центр пары — {compatibility['pair']['center_arcana']}\n"
        f"• Предназначение пары — {compatibility['pair']['destiny_arcana']}\n"
        f"• Канал отношений — {compatibility['pair']['relationship_arcana']}\n\n"
        f"━━━━━━━━━━\n\n"
        f"{markdown_bold_to_html(interpretation)}",
        parse_mode="HTML"
    )

    await state.clear()




@dp.message(MatrixStates.awaiting_child_matrix_date)
async def process_child_matrix_date(message: Message, state: FSMContext):
    user_id = message.from_user.id

    try:
        matrix = calculate_personal_matrix(message.text)
    except ValueError as e:
        await message.answer(f"⚠️ {e}\n\nПопробуйте ещё раз в формате ДД.ММ.ГГГГ")
        return

    from datetime import datetime
    birth_date = datetime.strptime(matrix["birth_date"], "%d.%m.%Y").date()
    today = datetime.now().date()
    age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))

    if age > 18:
        await message.answer(
            "⚠️ Для детской матрицы укажите дату рождения ребёнка до 18 лет.\n\n"
            "Для взрослых используйте раздел «✨ Личная матрица»."
        )
        return

    await message.answer("👶 Рассчитываю детскую матрицу...")
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")

    try:
        interpretation = await interpret_child_matrix(matrix)
    except Exception as e:
        await message.answer(f"Не удалось подготовить разбор. Ошибка: {e}")
        return

    await save_spread(
        user_id=user_id,
        spread_type="Детская матрица",
        question=matrix["birth_date"],
        cards=[],
        answer=interpretation
    )

    await charge_user_for_spread(user_id)

    await message.answer(
        f"👶 <b>Детская матрица</b>\n\n"
        f"📅 Дата рождения: <b>{matrix['birth_date']}</b>\n\n"
        f"🔢 <b>Ключевые энергии</b>\n\n"
        f"• Центр личности — {matrix['base']['center_arcana']}\n"
        f"• Таланты — {matrix['channels']['talent_arcana']}\n"
        f"• Отношения — {matrix['channels']['relationship_arcana']}\n"
        f"• Зона комфорта — {matrix['channels']['comfort_zone_arcana']}\n\n"
        f"━━━━━━━━━━\n\n"
        f"{markdown_bold_to_html(interpretation)}",
        parse_mode="HTML"
    )

    await state.clear()




@dp.message(MatrixStates.awaiting_money_channel_date)
async def process_money_channel_date(message: Message, state: FSMContext):
    user_id = message.from_user.id

    try:
        matrix = calculate_personal_matrix(message.text)
    except ValueError as e:
        await message.answer(f"⚠️ {e}\n\nПопробуйте ещё раз в формате ДД.ММ.ГГГГ")
        return

    await message.answer("💰 Рассчитываю денежный канал...")
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")

    try:
        interpretation = await interpret_money_channel(matrix)
    except Exception as e:
        await message.answer(f"Не удалось подготовить разбор. Ошибка: {e}")
        return

    await save_spread(
        user_id=user_id,
        spread_type="Денежный канал",
        question=matrix["birth_date"],
        cards=[],
        answer=interpretation
    )

    await charge_user_for_spread(user_id)

    await message.answer(
        f"💰 <b>Денежный канал</b>\n\n"
        f"📅 Дата рождения: <b>{matrix['birth_date']}</b>\n\n"
        f"🔢 <b>Ключевые энергии</b>\n\n"
        f"• Денежный канал — {matrix['channels']['money_arcana']}\n"
        f"• Таланты — {matrix['channels']['talent_arcana']}\n"
        f"• Предназначение — {matrix['base']['destiny_arcana']}\n"
        f"• Центр личности — {matrix['base']['center_arcana']}\n\n"
        f"━━━━━━━━━━\n\n"
        f"{markdown_bold_to_html(interpretation)}",
        parse_mode="HTML"
    )

    await state.clear()




@dp.message(MatrixStates.awaiting_purpose_date)
async def process_purpose_date(message: Message, state: FSMContext):
    user_id = message.from_user.id

    try:
        matrix = calculate_personal_matrix(message.text)
    except ValueError as e:
        await message.answer(f"⚠️ {e}\n\nПопробуйте ещё раз в формате ДД.ММ.ГГГГ")
        return

    await message.answer("🎯 Рассчитываю предназначение...")
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")

    try:
        interpretation = await interpret_purpose(matrix)
    except Exception as e:
        await message.answer(f"Не удалось подготовить разбор. Ошибка: {e}")
        return

    await save_spread(
        user_id=user_id,
        spread_type="Предназначение",
        question=matrix["birth_date"],
        cards=[],
        answer=interpretation
    )

    await charge_user_for_spread(user_id)

    await message.answer(
        f"🎯 <b>Предназначение</b>\n\n"
        f"📅 Дата рождения: <b>{matrix['birth_date']}</b>\n\n"
        f"🔢 <b>Ключевые энергии</b>\n\n"
        f"• Предназначение — {matrix['base']['destiny_arcana']}\n"
        f"• Центр личности — {matrix['base']['center_arcana']}\n"
        f"• Таланты — {matrix['channels']['talent_arcana']}\n"
        f"• Зона комфорта — {matrix['channels']['comfort_zone_arcana']}\n\n"
        f"━━━━━━━━━━\n\n"
        f"{markdown_bold_to_html(interpretation)}",
        parse_mode="HTML"
    )

    await state.clear()




@dp.message(MatrixStates.awaiting_karma_date)
async def process_karma_date(message: Message, state: FSMContext):
    user_id = message.from_user.id

    try:
        matrix = calculate_personal_matrix(message.text)
    except ValueError as e:
        await message.answer(f"⚠️ {e}\n\nПопробуйте ещё раз в формате ДД.ММ.ГГГГ")
        return

    await message.answer("🔥 Рассчитываю кармические задачи...")
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")

    try:
        interpretation = await interpret_karma(matrix)
    except Exception as e:
        await message.answer(f"Не удалось подготовить разбор. Ошибка: {e}")
        return

    await save_spread(
        user_id=user_id,
        spread_type="Кармические задачи",
        question=matrix["birth_date"],
        cards=[],
        answer=interpretation
    )

    await charge_user_for_spread(user_id)

    await message.answer(
        f"🔥 <b>Кармические задачи</b>\n\n"
        f"📅 Дата рождения: <b>{matrix['birth_date']}</b>\n\n"
        f"🔢 <b>Ключевые энергии</b>\n\n"
        f"• Кармические задачи — {matrix['channels']['karma_arcana']}\n"
        f"• Зона комфорта — {matrix['channels']['comfort_zone_arcana']}\n"
        f"• Отношения — {matrix['channels']['relationship_arcana']}\n"
        f"• Предназначение — {matrix['base']['destiny_arcana']}\n\n"
        f"━━━━━━━━━━\n\n"
        f"{markdown_bold_to_html(interpretation)}",
        parse_mode="HTML"
    )

    await state.clear()



@dp.message(AdminStates.awaiting_broadcast_text, F.text == "❌ Отмена")
async def cancel_broadcast_text_input(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return

    await state.clear()
    await message.answer("❌ Рассылка отменена.", reply_markup=admin_keyboard)


@dp.message(AdminStates.awaiting_broadcast_text)
async def process_broadcast_text(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return

    await state.update_data(broadcast_text=message.text)

    await message.answer(
        "📣 Предпросмотр рассылки:\n\n"
        f"{message.text}\n\n"
        "Отправить?",
        reply_markup=broadcast_confirm_keyboard
    )

    await state.set_state(AdminStates.awaiting_broadcast_confirm)



@dp.message(AdminStates.awaiting_broadcast_confirm, F.text == "✅ Отправить")
async def confirm_broadcast(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return

    data = await state.get_data()
    text_to_send = data.get("broadcast_text")

    if not text_to_send:
        await state.clear()
        await message.answer("Нет активной рассылки.", reply_markup=admin_keyboard)
        return

    user_ids = await get_all_user_ids()
    success = 0
    failed = 0

    await message.answer(f"📣 Начинаю рассылку по {len(user_ids)} пользователям...")

    for target_user_id in user_ids:
        try:
            await bot.send_message(chat_id=target_user_id, text=text_to_send, parse_mode="HTML")
            success += 1
        except Exception:
            failed += 1
        await asyncio.sleep(0.05)

    await state.clear()

    await message.answer(
        "📣 Рассылка завершена.\n\n"
        f"✅ Успешно: {success}\n"
        f"❌ Ошибок: {failed}",
        reply_markup=admin_keyboard
    )


@dp.message(AdminStates.awaiting_broadcast_confirm, F.text == "❌ Отмена")
async def cancel_broadcast(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return

    await state.clear()
    await message.answer("❌ Рассылка отменена.", reply_markup=admin_keyboard)

@dp.message()
async def fallback(message: Message):
    await message.answer("Нажми /start чтобы открыть меню.")


async def main():
    await init_db()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
