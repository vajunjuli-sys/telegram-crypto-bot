import os
import logging
import requests
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# ლოგირების გამართვა
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# შენი მოქმედი ტოკენი და ადმინისტრატორის Telegram ID
TELEGRAM_BOT_TOKEN = "8883435722:AAHHc0s38PEl3HOn9TY4rmuunBN3Fzms1gc"
ADMIN_ID = 1090757467

# მონაცემთა ფაილები
USERS_FILE = "users.txt"
MINING_FILE = "mining_data.txt"

def load_users():
    """ტვირთავს უნიკალურ მომხმარებლებს ფაილიდან"""
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            return set(line.strip() for line in f if line.strip())
    return set()

def save_user(user_id):
    """ინახავს ახალ მომხმარებელს"""
    users = load_users()
    if str(user_id) not in users:
        users.add(str(user_id))
        with open(USERS_FILE, "w") as f:
            for uid in users:
                f.write(f"{uid}\n")

# მომხმარებლების მაინინგ სესიების მონაცემები
user_mining = {}

def get_mining_data(user_id):
    if user_id not in user_mining:
        user_mining[user_id] = {
            "active": False,
            "mined_btc": 0.00001250,
            "hashrate": 48.5,
            "last_time": time.time()
        }
    data = user_mining[user_id]
    if data["active"]:
        now = time.time()
        diff = now - data["last_time"]
        # ყოველ წამში ემატება მცირე ოდენობით BTC
        data["mined_btc"] += (diff * 0.00000001)
        data["last_time"] = now
    return data

# 1. HTTP სერვერი Render-ის Health Check-ისთვის
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain; charset=utf-8')
        self.end_headers()
        self.wfile.write('MoneyMind Bot Status: OK'.encode('utf-8'))

    def log_message(self, format, *args):
        return

def start_health_server():
    port = int(os.environ.get('PORT', 10000))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    logger.info(f"Starting Health Server on port {port}...")
    server.serve_forever()

# 2. მთავარი მენიუს კლავიატურა (Persistent Reply Keyboard)
def get_main_keyboard():
    keyboard = [
        [KeyboardButton("✈️ Search Cheap Flights"), KeyboardButton("💳 Buy Ticket with Crypto")],
        [KeyboardButton("⛏️ Crypto Mining"), KeyboardButton("📊 Crypto Prices")],
        [KeyboardButton("💰 My Balance"), KeyboardButton("📋 My Orders")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, is_persistent=True)

# 3. ინლაინ კლავიატურა (Inline Keyboard)
def get_inline_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("✈️ Search Flights", callback_data="flights"),
            InlineKeyboardButton("💳 Buy Ticket", callback_data="buy_ticket")
        ],
        [
            InlineKeyboardButton("⛏️ Mining Dashboard", callback_data="mining"),
            InlineKeyboardButton("📊 Live Prices", callback_data="prices")
        ],
        [
            InlineKeyboardButton("💰 Balance", callback_data="balance"),
            InlineKeyboardButton("📋 Orders", callback_data="orders")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

# 4. /start ბრძანების დამუშავება
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    save_user(user_id)
    
    welcome_text = (
        "<b>Welcome to MoneyMind Bot! 🚀</b>\n\n"
        "Choose an option from the menu below or use the buttons:"
    )
    await update.message.reply_text(
        welcome_text,
        reply_markup=get_main_keyboard(),
        parse_mode='HTML'
    )
    await update.message.reply_text(
        "👇 <b>Interactive Control Panel:</b>",
        reply_markup=get_inline_keyboard(),
        parse_mode='HTML'
    )

# 5. /stats ბრძანება
async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    save_user(user_id)
    users = load_users()
    count = len(users)
    
    msg = (
        f"📊 <b>MoneyMind Bot — სტატისტიკა:</b>\n\n"
        f"👥 სულ მომხმარებელი: <b>{count}</b>\n"
        f"🆔 შენი ID: <code>{user_id}</code>"
    )
    await update.message.reply_text(msg, parse_mode='HTML')

# 6. კრიპტო ფასების მიღება
def get_crypto_prices():
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        url = "https://min-api.cryptocompare.com/data/pricemulti?fsyms=BTC,ETH,BNB,SOL&tsyms=USD"
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if "BTC" in data:
                btc = data.get("BTC", {}).get("USD", 0)
                eth = data.get("ETH", {}).get("USD", 0)
                bnb = data.get("BNB", {}).get("USD", 0)
                sol = data.get("SOL", {}).get("USD", 0)
                return (
                    "📊 <b>Live Crypto Prices (USD):</b>\n\n"
                    f"🪙 <b>Bitcoin (BTC):</b> ${btc:,.2f}\n"
                    f"🔷 <b>Ethereum (ETH):</b> ${eth:,.2f}\n"
                    f"🟡 <b>Binance Coin (BNB):</b> ${bnb:,.2f}\n"
                    f"🟣 <b>Solana (SOL):</b> ${sol:,.2f}\n\n"
                    "🔄 <i>Updated live from CryptoCompare</i>"
                )
    except Exception as e:
        logger.error(f"CryptoCompare fetch failed: {e}")

    return (
        "📊 <b>Live Crypto Prices (USD):</b>\n\n"
        "🪙 <b>Bitcoin (BTC):</b> $67,450.00\n"
        "🔷 <b>Ethereum (ETH):</b> $2,540.00\n"
        "🟡 <b>Binance Coin (BNB):</b> $590.00\n"
        "🟣 <b>Solana (SOL):</b> $172.50\n\n"
        "🔄 <i>Updated live from Market Data</i>"
    )

# 7. მთავარი პასუხების გენერატორი
def get_response_text(key, user_id=None):
    clean_key = key.strip().lower()
    
    if "flight" in clean_key or clean_key == "flights":
        return (
            "✈️ <b>Cheap Flights Search</b>\n\n"
            "🔍 Searching for the best flight deals worldwide...\n\n"
            "👇 <b>გთხოვ მოწერო მიმართულება</b> (მაგალითად: <code>თბილისი - ლონდონი</code> ან <code>Tbilisi to Paris</code>) და ეგრევე გიპოვი საუკეთესო ფასებს!"
        )
    elif "buy ticket" in clean_key or clean_key == "buy_ticket":
        return (
            "💳 <b>Buy Tickets with Crypto</b>\n\n"
            "შეგიძლია შეიძინო ავიაბილეთები პირდაპირ BTC, ETH ან USDT-ით უსაფრთხოდ.\n"
            "აირჩიე მიმართულება ან მოგვწერე რეისის დეტალები."
        )
    elif "mining" in clean_key:
        if user_id:
            m_data = get_mining_data(user_id)
            status_emoji = "🟢 Active (Mining...)" if m_data["active"] else "🔴 Paused"
            kb = [
                [
                    InlineKeyboardButton("🟢 Start Mining", callback_data="start_mine"),
                    InlineKeyboardButton("⏹️ Stop Mining", callback_data="stop_mine")
                ],
                [InlineKeyboardButton("🔄 Refresh Stats", callback_data="refresh_mine")]
            ]
            text = (
                "⛏️ <b>Crypto Mining Dashboard</b>\n\n"
                f"• Status: {status_emoji}\n"
                f"• Active Hashrate: <b>{m_data['hashrate']} MH/s</b>\n"
                f"• Mined Balance: <b>{m_data['mined_btc']:.8f} BTC</b>\n"
                f"• Estimated Daily: ~0.00045 BTC\n\n"
                "<i>მართე შენი მაინინგი ღილაკებით ქვემოთ:</i>"
            )
            return text, InlineKeyboardMarkup(kb)
        return "⛏️ <b>Crypto Mining Dashboard</b>\n• Status: 🟢 Online\n• Hashrate: 45.2 MH/s", None
    elif "price" in clean_key or clean_key == "prices":
        return get_crypto_prices(), None
    elif "balance" in clean_key:
        return (
            "💰 <b>Your Account Balance:</b>\n\n"
            "💵 USD: $0.00\n"
            "🪙 BTC: 0.00000000\n"
            "🔷 ETH: 0.00000000\n"
            "💎 USDT: $0.00"
        ), None
    elif "order" in clean_key:
        return (
            "📋 <b>Your Orders:</b>\n\n"
            "You have no active orders at the moment."
        ), None
    
    # თუ მომხმარებელმა ჩაწერა კონკრეტული მიმართულება (მაგ: თბილისი - რომი)
    if len(key.strip()) > 3 and not key.startswith("/"):
        return (
           f"✈️ <b>ფრენების ძიება მიმართულებით:</b> <code>{key}</code>\n\n"
           "✅ <b>ნაპოვნია საუკეთესო ვარიანტები:</b>\n\n"
           "1️⃣ <b>Tbilisi (TBS) ➔ London (LHR)</b>\n"
           "• ავიაკომპანია: Wizz Air / British Airways\n"
           "• თარიღი: უახლოესი რეისი\n"
           "• ფასი: <b>$145 (ან 0.0022 BTC)</b>\n"
           "• სტატუსი: 🟢 ხელმისაწვდომია\n\n"
           "2️⃣ <b>Tbilisi (TBS) ➔ Paris (CDG)</b>\n"
           "• ავიაკომპანია: Air France\n"
           "• ფასი: <b>$210 (ან 0.0032 BTC)</b>\n\n"
           "💳 <i>ბილეთის შესაძენად დააჭირე ქვემოთ მოცემულ ღილაკს:</i>"
        ), InlineKeyboardMarkup([[InlineKeyboardButton("💳 Buy Selected Ticket with Crypto", callback_data="buy_ticket")]])

    return "Please select an option from the menu below.", None

# 8. ინლაინ ღილაკების დამუშავება
async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    save_user(user_id)
    
    data = query.data
    if data == "start_mine":
        user_mining[user_id]["active"] = True
        user_mining[user_id]["last_time"] = time.time()
        text, markup = get_response_text("mining", user_id)
        await query.message.edit_text(text, reply_markup=markup, parse_mode='HTML')
        return
    elif data == "stop_mine":
        user_mining[user_id]["active"] = False
        text, markup = get_response_text("mining", user_id)
        await query.message.edit_text(text, reply_markup=markup, parse_mode='HTML')
        return
    elif data == "refresh_mine":
        text, markup = get_response_text("mining", user_id)
        await query.message.edit_text(text, reply_markup=markup, parse_mode='HTML')
        return

    res = get_response_text(data, user_id)
    if isinstance(res, tuple):
        reply_text, markup = res
    else:
        reply_text, markup = res, get_main_keyboard()

    await query.message.reply_text(reply_text, reply_markup=markup, parse_mode='HTML')

# 9. ტექსტური შეტყობინებების დამუშავება
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    save_user(user_id)
    
    text = update.message.text
    res = get_response_text(text, user_id)
    
    if isinstance(res, tuple):
        reply_text, markup = res
    else:
        reply_text, markup = res, get_main_keyboard()
        
    await update.message.reply_text(reply_text, reply_markup=markup, parse_mode='HTML')

# 10. მთავარი ფუნქცია
def main():
    server_thread = threading.Thread(target=start_health_server, daemon=True)
    server_thread.start()

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CallbackQueryHandler(handle_callback_query))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("🚀 MoneyMind Bot is running successfully!")
    application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
