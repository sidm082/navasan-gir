import os
import logging
import asyncio
import threading
import time
import requests
from flask import Flask, request
from bs4 import BeautifulSoup
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters

# تنظیمات اولیه
TOKEN = os.getenv("TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
THRESHOLD = 10000
CHECK_INTERVAL = 300  # 5 دقیقه
CACHE_DURATION = 300  # کش برای 5 دقیقه

# لاگ‌گیری
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__)
subscribed_chats = set()
subscribed_chats_lock = threading.Lock()
last_prices = {}
cached_prices = None
cache_timestamp = 0
running = True

# دکمه‌ها
keyboard = ReplyKeyboardMarkup(
    [["📥 دریافت قیمت لحظه‌ای"], ["✅ فعال‌سازی هشدار نوسان", "🛑 توقف هشدار نوسان"]],
    resize_keyboard=True
)

# دریافت قیمت‌ها
def get_prices():
    global cached_prices, cache_timestamp
    current_time = time.time()
    
    # استفاده از کش اگه هنوز معتبره
    if cached_prices and (current_time - cache_timestamp) < CACHE_DURATION:
        logger.info("استفاده از قیمت‌های کش‌شده")
        return cached_prices
    
    prices = {}
    max_retries = 5
    retry_delay = 15
    
    # دریافت بیت‌کوین و اتریوم از CryptoCompare
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        res = requests.get(
            "https://min-api.cryptocompare.com/data/price?fsym=BTC,ETH&tsyms=USD",
            headers=headers,
 –

System: متأسفم، به نظر می‌رسه پاسخ قبلی به دلیل قطع شدن ناقص مونده. اجازه بدید ادامه کد و راه‌حل رو کامل کنم. با توجه به لاگ، مشکل اصلی خطای `429 Too Many Requests` از API CoinGecko بود که نشون می‌ده API رایگان برای سرورهای اشتراکی Render مناسب نیست. کد جدید از **CryptoCompare** برای بیت‌کوین و اتریوم استفاده می‌کنه (چون محدودیت کمتری داره) و برای دلار، یورو و طلا از وب‌اسکریپینگ `tgju.org` استفاده می‌کنه. همچنین، کش و مدیریت خطاها رو حفظ می‌کنیم.

---

### **کد اصلاح‌شده (کامل)**
این کد از API CryptoCompare برای بیت‌کوین و اتریوم و وب‌اسکریپینگ برای `tgju.org` استفاده می‌کنه:

```python
import os
import logging
import asyncio
import threading
import time
import requests
from flask import Flask, request
from bs4 import BeautifulSoup
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters

# تنظیمات اولیه
TOKEN = os.getenv("TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
THRESHOLD = 10000
CHECK_INTERVAL = 300  # 5 دقیقه
CACHE_DURATION = 300  # کش برای 5 دقیقه

# لاگ‌گیری
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__)
subscribed_chats = set()
subscribed_chats_lock = threading.Lock()
last_prices = {}
cached_prices = None
cache_timestamp = 0
running = True

# دکمه‌ها
keyboard = ReplyKeyboardMarkup(
    [["📥 دریافت قیمت لحظه‌ای"], ["✅ فعال‌سازی هشدار نوسان", "🛑 توقف هشدار نوسان"]],
    resize_keyboard=True
)

# دریافت قیمت‌ها
def get_prices():
    global cached_prices, cache_timestamp
    current_time = time.time()
    
    # استفاده از کش اگه هنوز معتبره
    if cached_prices and (current_time - cache_timestamp) < CACHE_DURATION:
        logger.info("استفاده از قیمت‌های کش‌شده")
        return cached_prices
    
    prices = {}
    max_retries = 5
    retry_delay = 15
    
    # دریافت بیت‌کوین و اتریوم از CryptoCompare
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        for attempt in range(max_retries):
            try:
                res = requests.get(
                    "https://min-api.cryptocompare.com/data/pricemulti?fsyms=BTC,ETH&tsyms=USD",
                    headers=headers,
                    timeout=10
                )
                res.raise_for_status()
                data = res.json()
                # تبدیل قیمت‌های USD به ریال (نرخ تقریبی: 1 دلار = 600,000 ریال)
                USD_TO_RIAL = 600000
                if "BTC" in data:
                    prices["بیت‌کوین"] = int(data["BTC"]["USD"] * USD_TO_RIAL)
                if "ETH" in data:
                    prices["اتریوم"] = int(data["ETH"]["USD"] * USD_TO_RIAL)
                break
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429:
                    logger.warning(f"خطای 429 از CryptoCompare، تلاش دوباره پس از {retry_delay * (2 ** attempt)} ثانیه...")
                    time.sleep(retry_delay * (2 ** attempt))
                    continue
                logger.error(f"خطا در دریافت قیمت‌ها از CryptoCompare: {e}")
                return None
            except requests.RequestException as e:
                logger.error(f"خطا در دریافت قیمت‌ها از CryptoCompare: {e}")
                return None
    except Exception as e:
        logger.error(f"خطا در دریافت قیمت‌های کریپتو: {e}")
    
    # دریافت دلار، یورو و طلا از tgju.org با وب‌اسکریپینگ
    try:
        res = requests.get("https://www.tgju.org/", headers=headers, timeout=10)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")
        
        # پیدا کردن قیمت‌ها با سلکتورهای CSS (باید ساختار صفحه رو بررسی کنی)
        # این سلکتورها فرضی هستن و باید با ابزار Inspect مرورگر تنظیم بشن
        price_elements = {
            "دلار": soup.select_one(".price-dollar-rl .value"),
            "یورو": soup.select_one(".price-eur .value"),
            "طلا (گرم ۱۸)": soup.select_one(".geram18 .value")
        }
        for name, element in price_elements.items():
            if element:
                # حذف کاما و تبدیل به عدد
                price_text = element.text.replace(",", "").strip()
                if price_text.isdigit():
                    prices[name] = int(price_text)
                else:
                    prices[name] = None
                    logger.warning(f"قیمت {name} معتبر نیست: {price_text}")
            else:
                prices[name] = None
                logger.warning(f"عنصر قیمت برای {name} یافت نشد")
    except Exception as e:
        logger.error(f"خطا در اسکریپینگ tgju.org: {e}")
        prices["دلار"] = None
        prices["یورو"] = None
        prices["طلا (گرم ۱۸)"] = None
    
    # به‌روزرسانی کش
    cached_prices = prices
    cache_timestamp = current_time
    return prices

# بررسی نوسان قیمت
def price_checker():
    global last_prices
    while running:
        current = get_prices()
        if current:
            for name, new_price in current.items():
                if new_price is None:  # برای ارزهایی که قیمت نداریم
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
                msg += f"{name}: در حال حاضر در دسترس نیست (به‌زودی اضافه می‌شود)\n"
            else:
                msg += f"{name}: {price:,} ریال\n"
        await update.message.reply_text(msg, reply_markup=keyboard)
    else:
        await update.message.reply_text(
            "❌ خطا در دریافت قیمت‌ها. لطفاً چند دقیقه دیگر امتحان کنید.",
            reply_markup=keyboard
        )

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
    update = Update.de_json(request.get_json(force=True), application.bot)
    asyncio.run_coroutine_threadsafe(application.process_update(update), loop)
    return "OK"

# مدیریت حلقه asyncio و وب‌هوک
async def main():
    await application.initialize()
    await application.bot.set_webhook(url=WEBHOOK_URL)
    await application.start()
    logger.info("وب‌هوک تنظیم شد و ربات شروع به کار کرد.")
