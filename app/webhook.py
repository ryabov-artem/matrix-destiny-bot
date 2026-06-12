import os
import asyncio
import aiosqlite
from aiohttp import web
from aiogram import Bot
from aiogram.client.session.aiohttp import AiohttpSession
from dotenv import load_dotenv
from yookassa import Configuration, Payment

from database import add_balance, get_balance, save_payment

load_dotenv("/opt/bots/matrix_bot/.env")

BOT_TOKEN = os.getenv("BOT_TOKEN")
PROXY_URL = os.getenv("PROXY_URL")
DB_FILE = "/opt/bots/matrix_bot/data/database.db"
YOOKASSA_SHOP_ID = os.getenv("YOOKASSA_SHOP_ID")
YOOKASSA_SECRET_KEY = os.getenv("YOOKASSA_SECRET_KEY")

if YOOKASSA_SHOP_ID and YOOKASSA_SECRET_KEY:
    Configuration.account_id = YOOKASSA_SHOP_ID
    Configuration.secret_key = YOOKASSA_SECRET_KEY


async def init_payments_table():
    async with aiosqlite.connect(DB_FILE) as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS processed_payments (
                payment_id TEXT PRIMARY KEY,
                user_id INTEGER,
                count INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await conn.commit()


async def payment_already_processed(payment_id):
    async with aiosqlite.connect(DB_FILE) as conn:
        cursor = await conn.execute(
            "SELECT payment_id FROM processed_payments WHERE payment_id = ?",
            (payment_id,)
        )
        row = await cursor.fetchone()
        await cursor.close()
    return row is not None


async def mark_payment_processed(payment_id, user_id, count):
    async with aiosqlite.connect(DB_FILE) as conn:
        await conn.execute(
            "INSERT OR IGNORE INTO processed_payments (payment_id, user_id, count) VALUES (?, ?, ?)",
            (payment_id, user_id, count)
        )
        await conn.commit()



async def verify_yookassa_payment(payment_id, user_id, count, amount_rub):
    if not YOOKASSA_SHOP_ID or not YOOKASSA_SECRET_KEY:
        print("YooKassa credentials are empty", flush=True)
        return False

    try:
        payment = await asyncio.to_thread(Payment.find_one, payment_id)
    except Exception as e:
        print(f"YooKassa payment verification error: {e}", flush=True)
        return False

    metadata = payment.metadata or {}

    try:
        real_user_id = int(metadata.get("user_id"))
        real_count = int(metadata.get("count"))
        real_amount = float(payment.amount.value)
    except (TypeError, ValueError):
        print("YooKassa payment verification failed: bad metadata", flush=True)
        return False

    if payment.status != "succeeded":
        print(f"YooKassa payment verification failed: status={payment.status}", flush=True)
        return False

    if not payment.paid:
        print("YooKassa payment verification failed: paid is false", flush=True)
        return False

    if real_user_id != user_id or real_count != count:
        print("YooKassa payment verification failed: metadata mismatch", flush=True)
        return False

    if abs(real_amount - amount_rub) > 0.01:
        print("YooKassa payment verification failed: amount mismatch", flush=True)
        return False

    return True


async def send_telegram_message(user_id, text):
    if not BOT_TOKEN:
        print("BOT_TOKEN is empty", flush=True)
        return

    try:
        session = AiohttpSession(proxy=PROXY_URL)
        bot = Bot(token=BOT_TOKEN, session=session)
        await bot.send_message(chat_id=user_id, text=text)
        await bot.session.close()
        print(f"Telegram notification sent to {user_id}", flush=True)
    except Exception as e:
        print(f"Telegram sendMessage error: {e}", flush=True)


async def yookassa_webhook(request):
    data = await request.json()

    event = data.get("event")
    obj = data.get("object", {})

    if event != "payment.succeeded":
        return web.json_response({"ok": True})

    payment_id = obj.get("id")
    metadata = obj.get("metadata") or {}

    user_id = int(metadata.get("user_id"))
    count = int(metadata.get("count"))
    amount_rub = float((obj.get("amount") or {}).get("value", 0))

    if await payment_already_processed(payment_id):
        return web.json_response({"ok": True, "status": "already_processed"})

    if not await verify_yookassa_payment(payment_id, user_id, count, amount_rub):
        return web.json_response({"ok": False, "error": "payment_verification_failed"}, status=403)

    await add_balance(user_id, count)
    await mark_payment_processed(payment_id, user_id, count)
    await save_payment(payment_id, user_id, amount_rub, count)

    balance = await get_balance(user_id)

    await send_telegram_message(
        user_id,
        f"🎉 Оплата успешно получена!\\n\\n"
        f"💎 Зачислено: {count} разбор(ов)\\n"
        f"🔮 Баланс: {balance} разбор(ов)\\n\\n"
        f"Выберите интересующий разбор:\\n\\n"
        f"✨ Личная матрица\\n"
        f"❤️ Совместимость\\n"
        f"👶 Детская матрица\\n"
        f"💰 Денежный канал\\n"
        f"🎯 Предназначение\\n"
        f"🔥 Кармические задачи"
    )
    await init_payments_table()


app = web.Application()
app.on_startup.append(on_startup)
app.router.add_get("/health", health)
app.router.add_post("/yookassa/webhook", yookassa_webhook)

if __name__ == "__main__":
    web.run_app(app, host="127.0.0.1", port=8082)
