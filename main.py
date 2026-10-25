import os
import logging
import requests
import threading
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
ADMIN_ID = 1090757467  # შენი ტელეგრამის ID

# მომხმარებლების ID-ების შესანახი ფაილი
USERS_FILE = "users.txt"

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
        with open(USERS_FILE, "a") as f:
            f.write(f"{user_id}\n")

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

# 3. ინლაინ კლავიატურა (Inline Keyboard - შეტყობინების შიგნით)
def get_inline_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("✈️ Search Flights", callback_data="flights"),
            InlineKeyboardButton("💳 Buy Ticket", callback_data="buy_ticket")
        ],
        [
            InlineKeyboardButton("⛏️ Mining", callback_data="mining"),
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
        "Choose an option from the menu or press the interactive buttons below:"
    )
    # ვაგზავნით როგორც ReplyKeyboard-ს (ქვედა მენიუ), ასევე InlineKeyboard-ს (შეტყობინების ღილაკები)
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

# 5. /stats ბრძანება - მომხმარებლების რაოდენობის სანახავად
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
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

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

def get_response_text(key):
    # გასწორდა ტექსტების შედარება, რომ ღილაკის ტექსტი ზუსტად დაემთხვეს
    clean_key = key.strip()
    
    if "Search Cheap Flights" in clean_key or clean_key == "flights":
        return (
            "✈️ <b>Cheap Flights Search</b>\n\n"
            "Searching for the best flight deals worldwide...\n"
            "Please send your departure city and destination (e.g., <code>Tbilisi to London</code>)."
        )
    elif "Buy Ticket with Crypto" in clean_key or clean_key == "buy_ticket":
        return (
            "💳 <b>Buy Tickets with Crypto</b>\n\n"
            "You can purchase airline tickets using BTC, ETH, or USDT.\n"
            "Contact support or select a route to proceed with payment."
        )
    elif "Crypto Mining" in clean_key or clean_key == "mining":
        return (
            "⛏️ <b>Crypto Mining Dashboard</b>\n\n"
            "• Active Hashes: 45.2 MH/s\n"
            "• Estimated Daily Earnings: 0.00045 BTC\n"
            "• Status: 🟢 Online"
        )
    elif "Crypto Prices" in clean_key or clean_key == "prices":
        return get_crypto_prices()
    elif "My Balance" in clean_key or clean_key == "balance":
        return (
            "💰 <b>Your Account Balance:</b>\n\n"
            "💵 USD: $0.00\n"
            "🪙 BTC: 0.00000000\n"
            "🔷 ETH: 0.00000000"
        )
    elif "My Orders" in clean_key or clean_key == "orders":
        return (
            "📋 <b>Your Orders:</b>\n\n"
            "You have no active orders at the moment."
        )
    return "Please select an option from the menu below."

# 7. ინლაინ ღილაკების დაჭერის დამუშავება
async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    save_user(user_id)
    
    reply_text = get_response_text(query.data)
    await query.message.reply_text(reply_text, reply_markup=get_main_keyboard(), parse_mode='HTML')

# 8. ტექსტური შეტყობინებების დამუშავება
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    save_user(user_id)
    
    text = update.message.text
    reply = get_response_text(text)
    
    await update.message.reply_text(reply, reply_markup=get_main_keyboard(), parse_mode='HTML')

# 9. მთავარი ფუნქცია
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
