import os
import logging
import asyncio
import threading
import time
import requests
from flask import Flask, request
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters

# تنظیمات اولیه
TOKEN = os.getenv("TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")
THRESHOLD = 10000
CHECK_INTERVAL = 60

# لاگ‌گیری
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__)
subscribed_chats = set()
subscribed_chats_lock = threading.Lock()
last_prices = {}
running = True

# دکمه‌ها
keyboard = ReplyKeyboardMarkup(
    [["📥 دریافت قیمت لحظه‌ای"], ["✅ فعال‌سازی هشدار نوسان", "🛑 توقف هشدار نوسان"]],
    resize_keyboard=True
)

# دریافت قیمت‌ها
def get_prices():
    prices = {}
    try:
        # دریافت قیمت ارزهای دیجیتال از CoinGecko
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        res = requests.get(
            "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum&vs_currencies=usd",
            headers=headers,
            timeout=10
        )
        res.raise_for_status()
        data = res.json()
        
        # تبدیل قیمت‌های USD به ریال (نرخ تقریبی: 1 دلار = 600,000 ریال)
        USD_TO_RIAL = 600000
        if "bitcoin" in data:
            prices["بیت‌کوین"] = int(data["bitcoin"]["usd"] * USD_TO_RIAL)
        if "ethereum" in data:
            prices["اتریوم"] = int(data["ethereum"]["usd"] * USD_TO_RIAL)
        
        # برای دلار، یورو و طلا تا پیدا کردن API مناسب
        prices["دلار"] = None
        prices["یورو"] = None
        prices["طلا (گرم ۱۸)"] = None
        
        return prices
    except requests.RequestException as e:
        logger.error(f"خطا در دریافت قیمت‌ها از CoinGecko: {e}")
        return None

# بررسی نوسان قیمت
def price_checker():
    global last_prices
    while running:
        current = get_prices()
        if current:
            for name, new_price in current.items():
                if new_price is None:  # برای ارزهایی که API نداریم
                    continue
                old_price = last_prices.get(name)
                if old_price is None:
                    last_prices[name] = new_price
                elif abs(new_price - old_price) >= THRESHOLD:
                    last_prices[name] = new_price
                    asyncio.run_coroutine_threadsafe(send_price_alert(name, new_price), loop)
        time.sleep(CHECK_INTERVAL)

async def send_price_alert(name, price):
    msg = f"📢 قیمت {name} تغییر کرد!\n📈 قیمت جدید: {price:,} ریال"
    with subscribed_chats_lock:
        for chat_id in subscribed_chats.copy():
            try:
                await application.bot.send_message(chat_id=chat_id, text=msg)
            except Exception as e:
                logger.error(f"خطا در ارسال پیام به {chat_id}: {e}")

# فرمان‌ها
async def start(update: Update, context):
    chat_id = update.effective_chat.id
    with subscribed_chats_lock:
        subscribed_chats.add(chat_id)
    await update.message.reply_text(
        "✅ هشدار نوسان قیمت فعال شد.\nدر صورت نوسان بالای ۱۰,۰۰۰ ریال به شما اطلاع داده می‌شود.",
        reply_markup=keyboard
    )

async def stop(update: Update, context):
    chat_id = update.effective_chat.id
    with subscribed_chats_lock:
        if chat_id in subscribed_chats:
            subscribed_chats.remove(chat_id)
            await update.message.reply_text("🛑 هشدار قیمت غیرفعال شد.", reply_markup=keyboard)
        else:
            await update.message.reply_text("شما عضو هشدار نبودید.", reply_markup=keyboard)

async def now(update: Update, context):
    prices = get_prices()
    if prices:
        msg = "💹 قیمت لحظه‌ای:\n"
        for name, price in prices.items():
            if price is None:
                msg += f"{name}: در حال حاضر در دسترس نیست\n"
            else:
                msg += f"{name}: {price:,} ریال\n"
        await update.message.reply_text(msg, reply_markup=keyboard)
    else:
        await update.message.reply_text("❌ خطا در دریافت قیمت‌ها. لطفاً بعداً دوباره امتحان کنید.", reply_markup=keyboard)

async def handle_buttons(update: Update, context):
    text = update.message.text
    if text == "📥 دریافت قیمت لحظه‌ای":
        await now(update, context)
    elif text == "✅ فعال‌سازی هشدار نوسان":
        await start(update, context)
    elif text == "🛑 توقف هشدار نوسان":
        await stop(update, context)

# تنظیم Application
application = Application.builder().token(TOKEN).build()

# اتصال فرمان‌ها
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("stop", stop))
application.add_handler(CommandHandler("now", now))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_buttons))

# وب‌هوک
@app.route("/webhook", methods=["POST"])
def webhook():
    if WEBHOOK_SECRET and request.headers.get("X-Telegram-Bot-Api-Secret-Token") != WEBHOOK_SECRET:
        return "Unauthorized", 403
    update = Update.de_json(request.get_json(force=True), application.bot)
    asyncio.run_coroutine_threadsafe(application.process_update(update), loop)
    return "OK"

# مدیریت حلقه asyncio و وب‌هوک
async def main():
    await application.initialize()
    await application.bot.set_webhook(url=WEBHOOK_URL)
    await application.start()
    logger.info("وب‌هوک تنظیم شد و ربات شروع به کار کرد.")

# اجرا
if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    threading.Thread(target=price_checker, daemon=True).start()
    
    # اجرای وب‌هوک و سرور Flask
    try:
        loop.run_until_complete(main())
        app.run(host="0.0.0.0", port=8443)
    finally:
        loop.run_until_complete(application.stop())
        loop.close()
