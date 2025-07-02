from flask import Flask, request
from telegram import Update, Bot, ReplyKeyboardMarkup
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, Filters
import requests
import threading
import time

TOKEN = os.getenv("TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")
THRESHOLD = 10000
CHECK_INTERVAL = 60

bot = Bot(token=TOKEN)
app = Flask(name)
dispatcher = Dispatcher(bot, None, use_context=True)

subscribed_chats = set()
last_prices = {}

# === دکمه‌های کیبورد ===
keyboard = ReplyKeyboardMarkup(
    [
        ["📥 دریافت قیمت لحظه‌ای"],
        ["✅ فعال‌سازی هشدار نوسان", "🛑 توقف هشدار نوسان"]
    ],
    resize_keyboard=True
)

# === گرفتن قیمت‌ها ===
def get_prices():
    try:
        res = requests.get("https://api.tgju.org/v1/price/latest")
        data = res.json()["data"]
        return {
            "دلار": int(data["price_dollar_rl"]["p"]),
            "یورو": int(data["price_eur"]["p"]),
            "طلا (گرم ۱۸)": int(data["geram18"]["p"]),
            "بیت‌کوین": int(data["crypto-bitcoin"]["p"]),
            "اتریوم": int(data["crypto-ethereum"]["p"]),
        }
    except Exception as e:
        print("❌ خطا در دریافت قیمت:", e)
        return None

# === بررسی نوسان ===
def price_checker():
    global last_prices
    while True:
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
    for chat_id in subscribed_chats:
        try:
            bot.send_message(chat_id=chat_id, text=msg)
        except:
            pass

# === فرمان‌ها ===
def start(update, context):
    chat_id = update.effective_chat.id
    subscribed_chats.add(chat_id)
    update.message.reply_text(
        "✅ هشدار نوسان قیمت فعال شد.\n"
        "در صورت نوسان بالای ۲۰,۰۰۰ ریال در هر ارز، به شما اطلاع داده خواهد شد.",
        reply_markup=keyboard
    )

def stop(update, context):
    chat_id = update.effective_chat.id
    if chat_id in subscribed_chats:
        subscribed_chats.remove(chat_id)
        update.message.reply_text("🛑 هشدار قیمت غیرفعال شد.", reply_markup=keyboard)
    else:
        update.message.reply_text("شما عضو هشدار نبودید.", reply_markup=keyboard)

def now(update, context):
    prices = get_prices()
    if prices:
        msg = "💹 قیمت لحظه‌ای:\n"
        for name, price in prices.items():
            msg += f"{name}: {price:,} ریال\n"
        update.message.reply_text(msg, reply_markup=keyboard)
    else:
        update.message.reply_text("❌ خطا در دریافت قیمت‌ها.", reply_markup=keyboard)

# === پاسخ به دکمه‌ها ===
def handle_buttons(update, context):
    text = update.message.text
    if text == "📥 دریافت قیمت لحظه‌ای":
        now(update, context)
    elif text == "✅ فعال‌سازی هشدار نوسان":
        start(update, context)
    elif text == "🛑 توقف هشدار نوسان":
        stop(update, context)

# === اتصال فرمان‌ها ===
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CommandHandler("stop", stop))
dispatcher.add_handler(CommandHandler("now", now))
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_buttons))

# === وب‌هوک ===
@app.route("/webhook", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "OK"

# === اجرا ===
if name == "main":
    bot.set_webhook(url=WEBHOOK_URL)
    threading.Thread(target=price_checker, daemon=True).start()
    app.run(host="0.0.0.0", port=8443)
