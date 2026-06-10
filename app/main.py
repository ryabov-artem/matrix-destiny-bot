import asyncio
import os
import uuid
import re

from ai import (
    interpret_personal_matrix,
    interpret_compatibility
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

awaiting_three_card_question = set()
awaiting_relationship_question = set()
awaiting_career_question = set()
awaiting_money_question = set()
awaiting_personal_matrix_date = set()
awaiting_compatibility_dates = set()
awaiting_broadcast_text = set()
pending_broadcast = {}


def markdown_bold_to_html(text):
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
        [KeyboardButton(text="👥 Пользователи")],
        [KeyboardButton(text="📈 Статистика")],
        [KeyboardButton(text="📜 Последние анализы")],
        [KeyboardButton(text="📊 Популярность")],
        [KeyboardButton(text="📣 Рассылка")],
        [KeyboardButton(text="🎁 Акции")],
        [KeyboardButton(text="📈 Воронка")],
        [KeyboardButton(text="🏆 Топ")],
        [KeyboardButton(text="⬅️ Назад")]
    ],
    resize_keyboard=True
)




shop_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🪙 Купить 1 анализ — 99 ₽")],
        [KeyboardButton(text="💎 Купить 5 анализов — 299 ₽")],
        [KeyboardButton(text="✨ Купить 10 анализов — 499 ₽")],
        [KeyboardButton(text="👑 Купить 20 анализов — 799 ₽")],
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
        [KeyboardButton(text="🎁 Акция: 5 анализов")],
        [KeyboardButton(text="🔮 Напомнить про карту дня")],
        [KeyboardButton(text="💰 Скидка на анализы")],
        [KeyboardButton(text="⬅️ Назад")]
    ],
    resize_keyboard=True
)


def user_has_spread_access(user_id):
    if user_id == ADMIN_ID:
        return True

    if can_use_free_spread(user_id):
        return True

    if get_balance(user_id) > 0:
        return True

    return False


def charge_user_for_spread(user_id):
    if can_use_free_spread(user_id):
        mark_free_spread_used(user_id)
    elif get_balance(user_id) > 0:
        spend_balance(user_id)


async def no_access_message(message: Message):
    await message.answer(
        "💎 Бесплатный анализ уже использован.\n\n"
        "Доступные тарифы:\n"
        "• 1 анализ — 99 ₽\n"
        "• 5 анализов — 299 ₽\n"
        "• 10 анализов — 499 ₽\n"
        "• 20 анализов — 799 ₽\n\n"
        "Пополните баланс и возвращайтесь за новым разбором ✨"
    )


@dp.message(CommandStart())
async def start(message: Message):
    save_user(message.from_user)

    await message.answer(
        "✨ Матрица судьбы\n\n"
        "Добро пожаловать в сервис персональных разборов по системе 22 арканов.\n\n"
        "Бот поможет исследовать предназначение, денежный канал, совместимость, детскую матрицу и кармические задачи через дату рождения.\n\n"
        f"💎 Ваш баланс: {get_balance(message.from_user.id)} анализ(ов)\n\n"
        "Выберите интересующий разбор ниже 👇",
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

    add_balance(target_user_id, amount)

    await message.answer(
        f"✅ Начислено {amount} анализ(ов).\n"
        f"Пользователь: {target_user_id}"
    )

    try:
        await bot.send_message(
            chat_id=target_user_id,
            text=(
                f"💎 Тебе начислено {amount} анализ(ов).\n\n"
                "Можешь использовать их в любом платном анализе."
            )
        )
    except Exception:
        pass


@dp.message(F.text == "💎 Баланс")
async def balance(message: Message):
    save_user(message.from_user)

    balance_count = get_balance(message.from_user.id)

    await message.answer(
        f"💎 Баланс анализов\n\n"
        f"Доступно: {balance_count} анализ(ов)\n\n"
        f"Для получения одного разбора расходуется 1 анализ с баланса.\n\n"
        f"1 анализ = 1 персональный разбор\n\n"
        f"Пополните баланс ниже 👇",
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
        "description": f"Матрица судьбы: {count} анализ(ов)",
        "metadata": {
            "user_id": str(user_id),
            "count": str(count)
        }
    }, str(uuid.uuid4()))

    return payment


@dp.message(F.text.contains("Купить 1 анализ"))
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
        "🪙 1 анализ\n\n"
        "Стоимость: 99 ₽\n\n"
        "Нажмите кнопку ниже и выберите удобный способ оплаты: карта, СБП, SberPay или другой доступный способ.",
        reply_markup=keyboard
    )


@dp.message(F.text.contains("Купить 5 анализов"))
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
        "💎 5 анализов\n\n"
        "Стоимость: 299 ₽\n\n"
        "Нажмите кнопку ниже и выберите удобный способ оплаты: карта, СБП, SberPay или другой доступный способ.",
        reply_markup=keyboard
    )




@dp.message(F.text.contains("Купить 10 анализов"))
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
        "✨ 10 анализов\n\n"
        "Стоимость: 499 ₽\n\n"
        "Выгодный пакет для нескольких вопросов: отношения, работа, деньги и личные ситуации.\n\n"
        "Нажмите кнопку ниже и выберите удобный способ оплаты.",
        reply_markup=keyboard
    )


@dp.message(F.text.contains("Купить 20 анализов"))
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
        "👑 20 анализов\n\n"
        "Стоимость: 799 ₽\n\n"
        "Самый выгодный пакет для тех, кто планирует несколько разборов.\n\n"
        "Нажмите кнопку ниже и выберите удобный способ оплаты.",
        reply_markup=keyboard
    )


@dp.message(F.text == "✨ Личная матрица")
async def matrix_personal(message: Message):
    save_user(message.from_user)
    user_id = message.from_user.id

    if not user_has_spread_access(user_id):
        await no_access_message(message)
        return

    awaiting_personal_matrix_date.add(user_id)

    await message.answer(
        "✨ <b>Личная матрица</b>\n\n"
        "Введите дату рождения в формате:\n\n"
        "<b>ДД.ММ.ГГГГ</b>\n\n"
        "Например: <b>29.05.1995</b>",
        parse_mode="HTML"
    )


@dp.message(F.text == "❤️ Совместимость")
async def matrix_compatibility(message: Message):
    save_user(message.from_user)
    user_id = message.from_user.id

    if not user_has_spread_access(user_id):
        await no_access_message(message)
        return

    awaiting_compatibility_dates.add(user_id)

    await message.answer(
        "❤️ <b>Совместимость</b>\n\n"
        "Введите две даты рождения, каждую с новой строки:\n\n"
        "<b>29.05.1995</b>\n"
        "<b>14.02.1997</b>",
        parse_mode="HTML"
    )


@dp.message(F.text == "👶 Детская матрица")
async def matrix_child(message: Message):
    save_user(message.from_user)
    await message.answer(
        "👶 <b>Детская матрица</b>\n\n"
        "Раздел находится в разработке.\n\n"
        "В версии 1.0 здесь будет мягкий разбор по дате рождения ребёнка:\n"
        "• таланты;\n"
        "• особенности характера;\n"
        "• сильные стороны;\n"
        "• рекомендации родителям.\n\n"
        "Скоро здесь появится полноценный анализ ✨",
        parse_mode="HTML"
    )


@dp.message(F.text == "💰 Денежный канал")
async def matrix_money(message: Message):
    save_user(message.from_user)
    await message.answer(
        "💰 <b>Денежный канал</b>\n\n"
        "Раздел находится в разработке.\n\n"
        "В версии 1.0 здесь будет разбор финансовой энергии по дате рождения:\n"
        "• сильные стороны в деньгах;\n"
        "• ограничения;\n"
        "• повторяющиеся сценарии;\n"
        "• рекомендации для роста.\n\n"
        "Скоро здесь появится полноценный анализ ✨",
        parse_mode="HTML"
    )


@dp.message(F.text == "🎯 Предназначение")
async def matrix_purpose(message: Message):
    save_user(message.from_user)
    await message.answer(
        "🎯 <b>Предназначение</b>\n\n"
        "Раздел находится в разработке.\n\n"
        "В версии 1.0 здесь будет разбор ключевых жизненных задач:\n"
        "• направления реализации;\n"
        "• сильные качества;\n"
        "• внутренние опоры;\n"
        "• точки развития.\n\n"
        "Скоро здесь появится полноценный анализ ✨",
        parse_mode="HTML"
    )


@dp.message(F.text == "🔥 Кармические задачи")
async def matrix_karma(message: Message):
    save_user(message.from_user)
    await message.answer(
        "🔥 <b>Кармические задачи</b>\n\n"
        "Раздел находится в разработке.\n\n"
        "В версии 1.0 здесь будет разбор повторяющихся сценариев и уроков:\n"
        "• кармические задачи;\n"
        "• зоны роста;\n"
        "• внутренние ограничения;\n"
        "• рекомендации для осознанной проработки.\n\n"
        "Скоро здесь появится полноценный анализ ✨",
        parse_mode="HTML"
    )


@dp.message(F.text == "📜 История")
async def history(message: Message):
    save_user(message.from_user)

    spreads = get_user_spreads(message.from_user.id, limit=5)

    if not spreads:
        await message.answer(
            "📜 История пока пустая.\n\n"
            "Сделайте анализ, и он появится здесь."
        )
        return

    text = "📜 Последние анализы:\n\n"

    for spread in spreads:
        text += (
            f"🔮 #{spread['id']} — {spread['spread_type']}\n"
            f"Вопрос: {spread['question']}\n"
            f"Энергии: {spread['cards']}\n\n"
        )

    await message.answer(text)


@dp.message(F.text == "ℹ️ О боте")
async def about(message: Message):
    await message.answer(
        "ℹ️ Бот делает развлекательные AI-разборы по системе 22 арканов.\n\n"
        "Он не предсказывает будущее наверняка и не заменяет профессиональные консультации."
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
        "📈 Статистика\n\n"
        f"👥 Пользователей: {get_users_count()}\n"
        f"🎁 Карт дня: {get_daily_cards_count()}\n"
        f"🔮 Раскладов: {get_spreads_count()}"
    )


@dp.message(F.text == "👥 Пользователи")
async def admin_users(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("Нет доступа.")
        return

    users = get_recent_users(limit=10)

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


@dp.message(F.text == "📜 Последние анализы")
async def admin_recent_spreads(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("Нет доступа.")
        return

    spreads = get_recent_spreads(limit=10)

    if not spreads:
        await message.answer("Раскладов пока нет.")
        return

    text = "📜 Последние анализы:\n\n"

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

    stats = get_spread_type_stats()

    if not stats:
        await message.answer("📊 Пока нет данных по анализам.")
        return

    text = "📊 Популярность анализов:\n\n"

    for item in stats:
        text += f"{item['spread_type']}: {item['count']}\n"

    await message.answer(text)



@dp.message(F.text == "🎁 Акции")
async def admin_promos(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("Нет доступа.")
        return

    await message.answer(
        "🎁 Выбери готовую акцию для рассылки:",
        reply_markup=promo_keyboard
    )


@dp.message(F.text == "🎁 Акция: 5 анализов")
async def promo_five_spreads(message: Message):
    if message.from_user.id != ADMIN_ID:
        return

    pending_broadcast[message.from_user.id] = (
        "🎁 <b>Специальное предложение в Матрице судьбы</b>\n\n"
        "Получите сразу <b>5 анализов</b> по выгодной цене — 299 ₽.\n\n"
        "🔮 Можно использовать для вопросов про отношения, карьеру, деньги и личные ситуации.\n\n"
        "Нажмите 💎 Баланс, чтобы пополнить запас анализов."
    )

    await message.answer(
        "📣 Предпросмотр акции:\n\n"
        f"{pending_broadcast[message.from_user.id]}\n\n"
        "Отправить?",
        reply_markup=broadcast_confirm_keyboard,
        parse_mode="HTML"
    )


@dp.message(F.text == "🔮 Напомнить про карту дня")
async def promo_daily_card(message: Message):
    if message.from_user.id != ADMIN_ID:
        return

    pending_broadcast[message.from_user.id] = (
        "✨ <b>Личная матрица уже ждёт вас</b>\n\n"
        "Откройте Матрицу судьбы и выберите подходящий разбор.\n\n"
        "Иногда одна карта помогает увидеть день чуть яснее ✨"
    )

    await message.answer(
        "📣 Предпросмотр акции:\n\n"
        f"{pending_broadcast[message.from_user.id]}\n\n"
        "Отправить?",
        reply_markup=broadcast_confirm_keyboard,
        parse_mode="HTML"
    )


@dp.message(F.text == "💰 Скидка на анализы")
async def promo_discount(message: Message):
    if message.from_user.id != ADMIN_ID:
        return

    pending_broadcast[message.from_user.id] = (
        "💰 <b>Выгодный момент для анализа</b>\n\n"
        "Пакет из <b>5 анализов</b> сейчас выгоднее, чем покупать по одному.\n\n"
        "🔮 Задайте вопросы, которые давно откладывали: отношения, работа, деньги или личный выбор.\n\n"
        "Нажмите 💎 Баланс и выберите подходящий вариант."
    )

    await message.answer(
        "📣 Предпросмотр акции:\n\n"
        f"{pending_broadcast[message.from_user.id]}\n\n"
        "Отправить?",
        reply_markup=broadcast_confirm_keyboard,
        parse_mode="HTML"
    )



@dp.message(F.text == "📈 Воронка")
async def admin_sales_funnel(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("Нет доступа.")
        return

    funnel = get_sales_funnel()

    await message.answer(
        "📈 Воронка продаж\n\n"
        f"👥 Пользователей всего: {funnel['users_count']}\n"
        f"🔮 Получили карту дня: {funnel['daily_card_users']}\n"
        f"📜 Сделали анализ: {funnel['spread_users']}\n"
        f"💰 Совершили покупку: {funnel['paying_users']}\n\n"
        f"📜 Конверсия в анализ: {funnel['conversion_to_spread']}%\n"
        f"💰 Конверсия в покупку: {funnel['conversion_to_payment']}%"
    )



@dp.message(F.text == "🏆 Топ")
async def admin_top_users(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("Нет доступа.")
        return

    data = get_top_users(10)

    text = "🏆 Топ пользователей\n\n"

    text += "💰 По покупкам:\n"
    if data["top_payers"]:
        for i, user in enumerate(data["top_payers"], start=1):
            name = user["username"] or user["first_name"] or str(user["user_id"])
            text += (
                f"{i}. {name} — {user['total_amount']} ₽ "
                f"({user['payments_count']} платеж., {user['total_spreads']} раскл.)\n"
            )
    else:
        text += "Пока нет покупок.\n"

    text += "\n📜 По анализам:\n"
    if data["top_spreads"]:
        for i, user in enumerate(data["top_spreads"], start=1):
            name = user["username"] or user["first_name"] or str(user["user_id"])
            text += f"{i}. {name} — {user['spreads_count']} раскл.\n"
    else:
        text += "Пока нет анализов.\n"

    await message.answer(text)


@dp.message(F.text == "📣 Рассылка")
async def admin_broadcast_start(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("Нет доступа.")
        return

    awaiting_broadcast_text.add(message.from_user.id)

    await message.answer(
        "📣 Введи текст рассылки.\n\n"
        "Следующее сообщение будет отправлено всем пользователям."
    )


@dp.message(F.text == "✅ Отправить")
async def confirm_broadcast(message: Message):
    if message.from_user.id != ADMIN_ID:
        return

    user_id = message.from_user.id

    if user_id not in pending_broadcast:
        await message.answer("Нет активной рассылки.")
        return

    text_to_send = pending_broadcast.pop(user_id)
    user_ids = get_all_user_ids()

    success = 0
    failed = 0

    await message.answer(f"📣 Начинаю рассылку по {len(user_ids)} пользователям...")

    for target_user_id in user_ids:
        try:
            await bot.send_message(chat_id=target_user_id, text=text_to_send)
            success += 1
        except Exception:
            failed += 1

    await message.answer(
        "📣 Рассылка завершена.\n\n"
        f"✅ Успешно: {success}\n"
        f"❌ Ошибок: {failed}",
        reply_markup=admin_keyboard
    )


@dp.message(F.text == "❌ Отмена")
async def cancel_broadcast(message: Message):
    if message.from_user.id != ADMIN_ID:
        return

    pending_broadcast.pop(message.from_user.id, None)

    await message.answer("❌ Рассылка отменена.", reply_markup=admin_keyboard)


async def process_spread(message: Message, spread_type, intro_text, interpret_func):
    await message.answer(
        "✨ <b>Раздел скоро будет доступен</b>\n\n"
        "Сейчас полноценно работает услуга <b>Личная матрица</b>.\n"
        "Остальные направления подключим поэтапно.",
        parse_mode="HTML"
    )


@dp.message()
async def fallback(message: Message):
    user_id = message.from_user.id

    if user_id in awaiting_broadcast_text:
        awaiting_broadcast_text.remove(user_id)
        pending_broadcast[user_id] = message.text

        await message.answer(
            "📣 Предпросмотр рассылки:\n\n"
            f"{message.text}\n\n"
            "Отправить?",
            reply_markup=broadcast_confirm_keyboard
        )
        return

    if user_id in awaiting_compatibility_dates:
        awaiting_compatibility_dates.remove(user_id)

        dates = [line.strip() for line in message.text.splitlines() if line.strip()]

        if len(dates) != 2:
            await message.answer(
                "⚠️ Нужно ввести ровно две даты, каждую с новой строки.\n\n"
                "Например:\n"
                "29.05.1995\n"
                "14.02.1997"
            )
            awaiting_compatibility_dates.add(user_id)
            return

        try:
            compatibility = calculate_compatibility_matrix(dates[0], dates[1])
        except ValueError as e:
            await message.answer(f"⚠️ {e}\n\nПопробуйте ещё раз.")
            awaiting_compatibility_dates.add(user_id)
            return

        await message.answer("❤️ Рассчитываю совместимость...")

        try:
            interpretation = interpret_compatibility(compatibility)
        except Exception as e:
            await message.answer(f"Не удалось подготовить разбор. Ошибка: {e}")
            return

        save_spread(
            user_id=user_id,
            spread_type="Совместимость",
            question=f"{compatibility['date1']} + {compatibility['date2']}",
            cards=[],
            answer=interpretation
        )

        charge_user_for_spread(user_id)

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
        return

    if user_id in awaiting_personal_matrix_date:
        awaiting_personal_matrix_date.remove(user_id)

        try:
            matrix = calculate_personal_matrix(message.text)
        except ValueError as e:
            await message.answer(f"⚠️ {e}\n\nПопробуйте ещё раз: например, 29.05.1995")
            awaiting_personal_matrix_date.add(user_id)
            return

        await message.answer("✨ Рассчитываю вашу личную матрицу...")

        try:
            interpretation = interpret_personal_matrix(matrix)
        except Exception as e:
            await message.answer(f"Не удалось подготовить разбор. Ошибка: {e}")
            return

        save_spread(
            user_id=user_id,
            spread_type="Личная матрица",
            question=matrix["birth_date"],
            cards=[],
            answer=interpretation
        )

        charge_user_for_spread(user_id)

        await message.answer(
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
        )
        return

    if user_id in awaiting_money_question:
        awaiting_money_question.remove(user_id)
        await process_spread(
            message,
            "Деньги",
            "💰 Вытягиваю карты для денежного анализа...",
            interpret_money_spread
        )
        return

    if user_id in awaiting_career_question:
        awaiting_career_question.remove(user_id)
        await process_spread(
            message,
            "Карьера",
            "💼 Вытягиваю карты для анализа предназначения...",
            interpret_career_spread
        )
        return

    if user_id in awaiting_relationship_question:
        awaiting_relationship_question.remove(user_id)
        await process_spread(
            message,
            "Отношения",
            "❤️ Вытягиваю карты для анализа совместимости...",
            interpret_relationship_spread
        )
        return

    if user_id in awaiting_three_card_question:
        awaiting_three_card_question.remove(user_id)
        await process_spread(
            message,
            "Личная матрица",
            "🃏 Вытягиваю три карты...",
            interpret_three_cards
        )
        return

    await message.answer("Нажми /start чтобы открыть меню.")


async def main():
    init_db()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
