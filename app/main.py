import asyncio
import os
import uuid
import re

from ai import (
    interpret_day_card,
    interpret_three_cards,
    interpret_relationship_spread,
    interpret_career_spread,
    interpret_money_spread
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

from tarot import draw_card, draw_three_cards

from aiogram import Bot, Dispatcher, F
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.filters import CommandStart
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv
from yookassa import Configuration, Payment

load_dotenv("/opt/bots/tarot_bot/.env")

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
awaiting_broadcast_text = set()
pending_broadcast = {}


def markdown_bold_to_html(text):
    return re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", text)


def get_main_keyboard(user_id):
    keyboard = [
        [KeyboardButton(text="🎁 Карта дня"), KeyboardButton(text="🌟 Общий расклад")],
        [KeyboardButton(text="❤️ Отношения"), KeyboardButton(text="💼 Карьера")],
        [KeyboardButton(text="💰 Деньги"), KeyboardButton(text="💎 Баланс")],
        [KeyboardButton(text="📜 История"), KeyboardButton(text="ℹ️ О боте")]
    ]

    if user_id == ADMIN_ID:
        keyboard.append([KeyboardButton(text="⚙️ Админка")])

    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


admin_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="👥 Пользователи")],
        [KeyboardButton(text="📈 Статистика")],
        [KeyboardButton(text="📜 Последние расклады")],
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
        [KeyboardButton(text="🪙 Купить 1 расклад — 99 ₽")],
        [KeyboardButton(text="💎 Купить 5 раскладов — 299 ₽")],
        [KeyboardButton(text="🔮 Купить 10 раскладов — 499 ₽")],
        [KeyboardButton(text="👑 Купить 20 раскладов — 799 ₽")],
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
        [KeyboardButton(text="🎁 Акция: 5 раскладов")],
        [KeyboardButton(text="🔮 Напомнить про карту дня")],
        [KeyboardButton(text="💰 Скидка на расклады")],
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
        "💎 Бесплатный расклад уже использован.\n\n"
        "Доступные тарифы:\n"
        "• 1 расклад — 99 ₽\n"
        "• 5 раскладов — 299 ₽\n\n"
        "Пополните баланс и возвращайтесь за новым раскладом 🔮\n"
        "Пока можешь пользоваться бесплатной картой дня 🎁"
    )


@dp.message(CommandStart())
async def start(message: Message):
    save_user(message.from_user)

    await message.answer(
        "🔮 Арканум\n\n"
        "Добро пожаловать в мир Таро.\n\n"
        "Карты помогут взглянуть на ситуацию с новой стороны, разобраться в чувствах, отношениях, работе и важных жизненных вопросах.\n\n"
        f"💎 Ваш баланс: {get_balance(message.from_user.id)} расклад(ов)\n\n"
        "Выберите интересующий расклад ниже 👇",
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
        f"✅ Начислено {amount} расклад(ов).\n"
        f"Пользователь: {target_user_id}"
    )

    try:
        await bot.send_message(
            chat_id=target_user_id,
            text=(
                f"💎 Тебе начислено {amount} расклад(ов).\n\n"
                "Можешь использовать их в любом платном раскладе."
            )
        )
    except Exception:
        pass


@dp.message(F.text == "🎁 Карта дня")
async def day_card(message: Message):
    save_user(message.from_user)

    existing_card = get_today_card(message.from_user.id)

    if existing_card:
        await message.answer(
            f"🎴 Твоя карта дня уже была вытянута сегодня.\n\n"
            f"{existing_card['name']} ({existing_card['orientation']})\n\n"
            f"{markdown_bold_to_html(existing_card['interpretation'])}\n\n"
            f"Возвращайся завтра за новой картой.",
            parse_mode="HTML"
        )
        return

    card = draw_card()

    await message.answer("🃏 Перемешиваю колоду...")

    interpretation = interpret_day_card(card)

    save_daily_card(message.from_user.id, card, interpretation)

    photo = FSInputFile(f"/opt/bots/tarot_bot/data/cards/{card['image']}")

    await message.answer_photo(
        photo=photo,
        caption=f"🎴 {card['name']} ({card['orientation']})\n\n{interpretation}"
    )


@dp.message(F.text == "💎 Баланс")
async def balance(message: Message):
    save_user(message.from_user)

    balance_count = get_balance(message.from_user.id)

    await message.answer(
        f"💎 Баланс раскладов\n\n"
        f"Доступно: {balance_count} расклад(ов)\n\n"
        f"Для получения одного ответа расходуется 1 расклад с баланса.\n\n"
        f"1 расклад = 1 ответ карт\n\n"
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
        "description": f"Арканум: {count} расклад(ов)",
        "metadata": {
            "user_id": str(user_id),
            "count": str(count)
        }
    }, str(uuid.uuid4()))

    return payment


@dp.message(F.text.contains("Купить 1 расклад"))
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
        "🔮 1 расклад\n\n"
        "Стоимость: 99 ₽\n\n"
        "Нажмите кнопку ниже и выберите удобный способ оплаты: карта, СБП, SberPay или другой доступный способ.",
        reply_markup=keyboard
    )


@dp.message(F.text.contains("Купить 5 раскладов"))
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
        "✨ 5 раскладов\n\n"
        "Стоимость: 299 ₽\n\n"
        "Нажмите кнопку ниже и выберите удобный способ оплаты: карта, СБП, SberPay или другой доступный способ.",
        reply_markup=keyboard
    )




@dp.message(F.text.contains("Купить 10 раскладов"))
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
        "🔮 10 раскладов\n\n"
        "Стоимость: 499 ₽\n\n"
        "Выгодный пакет для нескольких вопросов: отношения, работа, деньги и личные ситуации.\n\n"
        "Нажмите кнопку ниже и выберите удобный способ оплаты.",
        reply_markup=keyboard
    )


@dp.message(F.text.contains("Купить 20 раскладов"))
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
        "👑 20 раскладов\n\n"
        "Стоимость: 799 ₽\n\n"
        "Самый выгодный пакет для тех, кто часто обращается к Аркануму.\n\n"
        "Нажмите кнопку ниже и выберите удобный способ оплаты.",
        reply_markup=keyboard
    )


@dp.message(F.text == "🌟 Общий расклад")
async def three_cards_start(message: Message):
    save_user(message.from_user)
    awaiting_three_card_question.add(message.from_user.id)

    await message.answer(
        "🌟 Напиши свой вопрос для общего расклада.\n\n"
        "Например:\n"
        "• Что мне важно понять сейчас?\n"
        "• Почему ситуация развивается так?\n"
        "• На что обратить внимание?"
    )


@dp.message(F.text == "❤️ Отношения")
async def relationships(message: Message):
    save_user(message.from_user)
    awaiting_relationship_question.add(message.from_user.id)

    await message.answer(
        "❤️ Напиши вопрос для расклада на отношения.\n\n"
        "Например:\n"
        "• Что происходит между нами?\n"
        "• Что он/она чувствует?\n"
        "• Есть ли перспектива у этих отношений?"
    )


@dp.message(F.text == "💼 Карьера")
async def career(message: Message):
    save_user(message.from_user)
    awaiting_career_question.add(message.from_user.id)

    await message.answer(
        "💼 Напиши вопрос для карьерного расклада.\n\n"
        "Например:\n"
        "• Стоит ли менять работу?\n"
        "• Что мешает карьерному росту?\n"
        "• На что обратить внимание в работе?"
    )


@dp.message(F.text == "💰 Деньги")
async def money(message: Message):
    save_user(message.from_user)
    awaiting_money_question.add(message.from_user.id)

    await message.answer(
        "💰 Напиши вопрос для денежного расклада.\n\n"
        "Например:\n"
        "• Что мне важно понять про деньги сейчас?\n"
        "• Что мешает финансовому росту?\n"
        "• На что обратить внимание в расходах?"
    )


@dp.message(F.text == "📜 История")
async def history(message: Message):
    save_user(message.from_user)

    spreads = get_user_spreads(message.from_user.id, limit=5)

    if not spreads:
        await message.answer(
            "📜 История пока пустая.\n\n"
            "Сделай расклад, и он появится здесь."
        )
        return

    text = "📜 Последние расклады:\n\n"

    for spread in spreads:
        text += (
            f"🔮 #{spread['id']} — {spread['spread_type']}\n"
            f"Вопрос: {spread['question']}\n"
            f"Карты: {spread['cards']}\n\n"
        )

    await message.answer(text)


@dp.message(F.text == "ℹ️ О боте")
async def about(message: Message):
    await message.answer(
        "ℹ️ Бот делает развлекательные AI-расклады Таро.\n\n"
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


@dp.message(F.text == "📜 Последние расклады")
async def admin_recent_spreads(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("Нет доступа.")
        return

    spreads = get_recent_spreads(limit=10)

    if not spreads:
        await message.answer("Раскладов пока нет.")
        return

    text = "📜 Последние расклады:\n\n"

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
        await message.answer("📊 Пока нет данных по раскладам.")
        return

    text = "📊 Популярность раскладов:\n\n"

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


@dp.message(F.text == "🎁 Акция: 5 раскладов")
async def promo_five_spreads(message: Message):
    if message.from_user.id != ADMIN_ID:
        return

    pending_broadcast[message.from_user.id] = (
        "🎁 <b>Специальное предложение в Аркануме</b>\n\n"
        "Получите сразу <b>5 раскладов</b> по выгодной цене — 299 ₽.\n\n"
        "🔮 Можно использовать для вопросов про отношения, карьеру, деньги и личные ситуации.\n\n"
        "Нажмите 💎 Баланс, чтобы пополнить запас раскладов."
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
        "🔮 <b>Карта дня уже ждёт вас</b>\n\n"
        "Загляните в Арканум и получите короткую подсказку на сегодня.\n\n"
        "Иногда одна карта помогает увидеть день чуть яснее ✨"
    )

    await message.answer(
        "📣 Предпросмотр акции:\n\n"
        f"{pending_broadcast[message.from_user.id]}\n\n"
        "Отправить?",
        reply_markup=broadcast_confirm_keyboard,
        parse_mode="HTML"
    )


@dp.message(F.text == "💰 Скидка на расклады")
async def promo_discount(message: Message):
    if message.from_user.id != ADMIN_ID:
        return

    pending_broadcast[message.from_user.id] = (
        "💰 <b>Выгодный момент для расклада</b>\n\n"
        "Пакет из <b>5 раскладов</b> сейчас выгоднее, чем покупать по одному.\n\n"
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
        f"📜 Сделали расклад: {funnel['spread_users']}\n"
        f"💰 Совершили покупку: {funnel['paying_users']}\n\n"
        f"📜 Конверсия в расклад: {funnel['conversion_to_spread']}%\n"
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

    text += "\n📜 По раскладам:\n"
    if data["top_spreads"]:
        for i, user in enumerate(data["top_spreads"], start=1):
            name = user["username"] or user["first_name"] or str(user["user_id"])
            text += f"{i}. {name} — {user['spreads_count']} раскл.\n"
    else:
        text += "Пока нет раскладов.\n"

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
    user_id = message.from_user.id

    if not user_has_spread_access(user_id):
        await no_access_message(message)
        return

    question = message.text
    cards = draw_three_cards()

    await message.answer(intro_text)

    for index, card in enumerate(cards, start=1):
        photo = FSInputFile(f"/opt/bots/tarot_bot/data/cards/{card['image']}")

        await message.answer_photo(
            photo=photo,
            caption=f"{index}. {card['name']} ({card['orientation']})"
        )

    await message.answer("✨ Интерпретирую расклад...")

    interpretation = interpret_func(question, cards)

    save_spread(
        user_id=user_id,
        spread_type=spread_type,
        question=question,
        cards=cards,
        answer=interpretation
    )

    charge_user_for_spread(user_id)

    await message.answer(
        f"🔮 {spread_type}\n\n"
        f"Вопрос:\n{question}\n\n"
        f"{markdown_bold_to_html(interpretation)}",
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

    if user_id in awaiting_money_question:
        awaiting_money_question.remove(user_id)
        await process_spread(
            message,
            "Деньги",
            "💰 Вытягиваю карты для денежного расклада...",
            interpret_money_spread
        )
        return

    if user_id in awaiting_career_question:
        awaiting_career_question.remove(user_id)
        await process_spread(
            message,
            "Карьера",
            "💼 Вытягиваю карты для карьерного расклада...",
            interpret_career_spread
        )
        return

    if user_id in awaiting_relationship_question:
        awaiting_relationship_question.remove(user_id)
        await process_spread(
            message,
            "Отношения",
            "❤️ Вытягиваю карты для расклада на отношения...",
            interpret_relationship_spread
        )
        return

    if user_id in awaiting_three_card_question:
        awaiting_three_card_question.remove(user_id)
        await process_spread(
            message,
            "Общий расклад",
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
