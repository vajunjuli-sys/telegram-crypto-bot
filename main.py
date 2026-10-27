import os
import logging
import requests
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# ლოგირების გამართვა
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# ტოკენი და ადმინისტრატორის ID
TELEGRAM_BOT_TOKEN = "8883435722:AAHHc0s38PEl3H0n9TY4rmuunBN3Fzms1gc"
ADMIN_ID = 1090757467

# მონაცემთა ფაილი
USERS_FILE = "users.txt"

def load_users():
    """ტვირთავს უნიკალურ მომხმარებლებს ფაილიდან"""
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "r") as f:
                return set(line.strip() for line in f if line.strip())
        except Exception as e:
            logger.error(f"Error loading users: {e}")
    return set()

def save_user(user_id):
    """ინახავს ახალ მომხმარებლებს მყისიერად"""
    if not user_id:
        return
    users = load_users()
    uid_str = str(user_id)
    if uid_str not in users:
        users.add(uid_str)
        try:
            with open(USERS_FILE, "w") as f:
                for uid in users:
                    f.write(f"{uid}\n")
        except Exception as e:
            logger.error(f"Error saving user: {e}")

# მომხმარებლების მაინინგის მონაცემები
user_mining = {}

def get_mining_data(user_id):
    if user_id not in user_mining:
        user_mining[user_id] = {
            "active": True, 
            "mined_btc": 0.00001850,
            "hashrate": 51.2,
            "last_time": time.time()
        }
    data = user_mining[user_id]
    if data["active"]:
        now = time.time()
        diff = now - data["last_time"]
        data["mined_btc"] += (diff * 0.00000003)
        data["last_time"] = now
    return data

# HTTP სერვერი Render-ის Health Check-ისთვის
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain; charset=utf-8')
        self.end_headers()
        self.wfile.write(b"OK")
    
    def log_message(self, format, *args):
        return

def start_health_server():
    port = int(os.environ.get('PORT', 10000))
    try:
        server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
        logger.info(f"Starting Health Server on port {port}...")
        server.serve_forever()
    except Exception as e:
        logger.error(f"Health Server failed to start: {e}")

# მთავარი მენიუს კლავიატურა
def get_main_keyboard():
    keyboard = [
        [KeyboardButton("✈️ Search Cheap Flights"), KeyboardButton("💳 Buy Ticket with Crypto")],
        [KeyboardButton("⛏️ Crypto Mining"), KeyboardButton("📊 Crypto Prices")],
        [KeyboardButton("💰 My Balance"), KeyboardButton("📦 My Orders")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, is_persistent=True)

# ონლაინ კლავიატურა
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
            InlineKeyboardButton("📦 Orders", callback_data="orders")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

# კრიპტო ფასების მიღება
def get_crypto_prices():
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        url = "https://min-api.cryptocompare.com/data/pricemulti?fsyms=BTC,ETH,BNB,SOL&tsyms=USD"
        response = requests.get(url, headers=headers, timeout=4)
        if response.status_code == 200:
            data = response.json()
            if "BTC" in data:
                btc = data.get("BTC", {}).get("USD", 0)
                eth = data.get("ETH", {}).get("USD", 0)
                bnb = data.get("BNB", {}).get("USD", 0)
                sol = data.get("SOL", {}).get("USD", 0)
                return (
                    "📊 <b>Live Crypto Prices (USD):</b>\n\n"
                    f"🟡 <b>Bitcoin (BTC):</b> ${btc:,.2f}\n"
                    f"🔷 <b>Ethereum (ETH):</b> ${eth:,.2f}\n"
                    f"🟠 <b>Binance Coin (BNB):</b> ${bnb:,.2f}\n"
                    f"🟣 <b>Solana (SOL):</b> ${sol:,.2f}\n"
                    "<i>🔄 Updated live from Market Data</i>"
                )
    except Exception as e:
        logger.error(f"CryptoCompare fetch failed: {e}")
    
    return (
        "📊 <b>Live Crypto Prices (USD):</b>\n\n"
        "🟡 <b>Bitcoin (BTC):</b> $67,450.00\n"
        "🔷 <b>Ethereum (ETH):</b> $2,540.00\n"
        "🟠 <b>Binance Coin (BNB):</b> $590.00\n"
        "🟣 <b>Solana (SOL):</b> $172.50\n"
        "<i>🔄 Updated live from Market Data</i>"
    )

# პასუხების გენერატორი
def get_response_text(key, user_id=None):
    clean_key = str(key).strip().lower()
    
    if "flight" in clean_key or "ფრენ" in clean_key or "ბილეთ" in clean_key:
        msg_text
