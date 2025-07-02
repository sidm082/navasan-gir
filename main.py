import os
import logging
import threading
import time
import requests
from flask import Flask, request
from telegram import Update, Bot, ReplyKeyboardMarkup
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, Filters

# تنظیمات اولیه
TOKEN = os.getenv("TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")
THRESHOLD = 10000
CHECK_INTERVAL = 60

# لاگ‌گیری
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

bot = Bot(token=TOKEN)
app = Flask(__name__)
dispatcher = Dispatcher(bot, None, use_context=True)

subscribed_chats = set()
subscribed_chats_lock = threading.Lock()
last_prices = {}
running = True  # پرچم برای توقف ترد

# دکمه‌ها
keyboard = ReplyKeyboardMarkup(
    [["📥 دریافت قیمت لحظه‌ای"], ["✅ فعال‌سازی هشدار نوسان", "🛑 توقف هشدار نوسان"]],
    resize_keyboard=True
)

# دریافت قیمت‌ها
def get_prices():
    try:
        res = requests.get("https://api.tgju.org/v1/price/latest")
        data = res.json()["data"]
        prices = {}
        keys = {
            "price_dollar_rl": "دلار",
            "price_eur": "یورو",
            "geram18": "طلا (گرم ۱۸)",
            "crypto-bitcoin": "بیت‌کوین",
            "crypto-ethereum": "اتریوم"
        }
        for key, name in keys.items():
            if key in data:
                prices[name] = int(data[key]["p"])
            else:
                logger.warning(f"کلید {key} در پاسخ API یافت نشد")
        return prices
    except Exception as e:
        logger.error(f"خطا در دریافت قیمت‌ها: {e}")
        return None

# بررسی نوسان قیمت
def price_checker():
    global last_prices
    while running:
        current = get_prices()
        if current:
            for name, new_price in current.items():
                old_price = last_prices.get(name)
                if old_price is None:
                    last_prices[name] = new_price
                elif abs(new_price - old_price) >= THRESHOLD:
                    last_prices[name] = new_price
                    send_price_alert(name, new_price)
        time.sleep(CHECK_INTERVAL)

def send_price_alert(name, price):
    msg = f"📢 قیمت {name} تغییر کرد!\n📈 قیمت جدید: {price:,} ریال"
    with subscribed_chats_lock:
        for chat_id in subscribed_chats.copy():
            try:
                bot.send_message(chat_id=chat_id, text=msg)
            except Exception as e:
                logger.error(f"خطا در ارسال پیام به {chat_id}: {e}")

# فرمان‌ها
def start(update, context):
    chat_id = update.effective_chat.id
    with subscribed_chats_lock:
        subscribed_chats.add(chat_id)
    update.message.reply_text(
        "✅ هشدار نوسان قیمت فعال شد.\nدر صورت نوسان بالای ۱۰,۰۰۰ ریال به شما اطلاع داده می‌شود.",
        reply_markup=keyboard
    )

def stop(update, context):
    chat_id = update.effective_chat.id
    with subscribed_chats_lock:
        if chat_id in subscribed_chats:
            subscribed_chats.remove(chat_id)
            update.message.reply_text("🛑 هشدار قیمت غیرفعال شد.", reply_markup=keyboard)
        else:
            update.message.reply_text("شما عضو هشدار نبودید.", reply_markup=keyboard)

def now(update, context):
    prices = get_prices()
    if prices:
        msg = "💹 قیمت لحظه‌ای:\n" + "\n".join(f"{name}: {price:,} ریال" for name, price in prices.items())
        update.message.reply_text(msg, reply_markup=keyboard)
    else:
        update.message.reply_text("❌ خطا در دریافت قیمت‌ها.", reply_markup=keyboard)

# پاسخ به دکمه‌ها
def handle_buttons(update, context):
    text = update.message.text
    if text == "📥 دریافت قیمت لحظه‌ای":
        now(update, context)
    elif text == "✅ فعال‌سازی هشدار نوسان":
        start(update, context)
    elif text == "🛑 توقف هشدار نوسان":
        stop(update, context)

# اتصال فرمان‌ها
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CommandHandler("stop", stop))
dispatcher.add_handler(CommandHandler("now", now))
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_buttons))

# وب‌هوک
@app.route("/webhook", methods=["POST"])
def webhook():
    if WEBHOOK_SECRET and request.headers.get("X-Telegram-Bot-Api-Secret-Token") != WEBHOOK_SECRET:
        return "Unauthorized", 403
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "OK"

# اجرا
if __name__ == "__main__":
    bot.set_webhook(url=WEBHOOK_URL)
    threading.Thread(target=price_checker, daemon=True).start()
    app.run(host="0.0.0.0", port=8443)
