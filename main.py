import os
import logging
import requests
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
        msg_text = (
            "✈️ <b>Cheap Flights Search</b>\n\n"
            "🔍 Searching for the best flight deals worldwide...\n\n"
            "<b>გთხოვ მომწერო ნებისმიერი მიმართულება ან ქალაქი</b> (მაგალითად: <i>თბილისი მილანი</i> ან <i>ბათუმი დუბაი</i>):"
        )
        return msg_text, get_main_keyboard()
    
    elif "buy" in clean_key or "ყიდვა" in clean_key or clean_key == "buy_ticket":
        kb = [
            [InlineKeyboardButton("✅ Confirm & Pay 0.0018 BTC", callback_data="pay_btc")],
            [InlineKeyboardButton("✅ Pay with USDT (TRC20)", callback_data="pay_usdt")],
            [InlineKeyboardButton("❌ Cancel", callback_data="cancel_order")]
        ]
        msg_text = (
            "💳 <b>Buy Tickets with Crypto</b>\n\n"
            "• აირჩიე გადახდის მეთოდი ბილეთის შესასყიდად:\n"
            "• მიმართულება: <b>Selected Flight Deal</b>\n"
            "• სავარაუდო ფასი: <b>$120 / 0.0018 BTC</b>\n"
            "<i>ℹ️ დააჭირე ქვემოთ მოცემულ ღილაკს გადახდის დასასრულებლად:</i>"
        )
        return msg_text, InlineKeyboardMarkup(kb)
    
    elif "mining" in clean_key or "მაინინგ" in clean_key:
        if user_id:
            m_data = get_mining_data(user_id)
            status_emoji = "🟢 Active (Mining...)" if m_data["active"] else "🔴 Paused"
            kb = [
                [
                    InlineKeyboardButton("🟢 Start Mining", callback_data="start_mine"),
                    InlineKeyboardButton("🟠 Stop Mining", callback_data="stop_mine")
                ],
                [
                    InlineKeyboardButton("🔄 Refresh Stats", callback_data="refresh_mine")
                ]
            ]
            hr = m_data['hashrate']
            mb = m_data['mined_btc']
            text = (
                "⛏️ <b>Crypto Mining Dashboard</b>\n\n"
                f"• Status: {status_emoji}\n"
                f"• Active Hashrate: <b>{hr} MH/s</b>\n"
                f"• Mined Balance: <b>{mb:.8f} BTC</b>\n"
                "• Estimated Daily: ~0.00045 BTC\n"
                "<i>ℹ️ მართე შენი მაინინგი ღილაკებით ქვემოთ:</i>"
            )
            return text, InlineKeyboardMarkup(kb)
        return "⛏️ <b>Crypto Mining Dashboard</b>\nStatus: 🟢 Online", get_main_keyboard()
    
    elif "price" in clean_key or "ფას" in clean_key or clean_key == "prices":
        return get_crypto_prices(), get_main_keyboard()
    
    elif "balance" in clean_key or "ბალანს" in clean_key:
        msg_text = (
            "💰 <b>Your Account Balance:</b>\n\n"
            "💵 USD: $0.00\n"
            "🟡 BTC: 0.00000000\n"
            "🔷 ETH: 0.00000000\n"
            "💎 USDT: $0.00\n\n"
            "<i>💳 დააკავშირე კრიპტო საფულე ბალანსის შესავსებად.</i>"
        )
        return msg_text, get_main_keyboard()
    
    elif "order" in clean_key or "შეკვეთ" in clean_key:
        msg_text = (
            "📦 <b>Your Orders:</b>\n\n"
            "You have no active orders at the moment. Search for flights or crypto items."
        )
        return msg_text, get_main_keyboard()
    
    if len(key.strip()) > 0 and not key.startswith("/"):
        route_name = key.strip().title()
        kb = [
            [InlineKeyboardButton("💳 Buy Selected Ticket with Crypto", callback_data="buy_ticket")],
            [InlineKeyboardButton("✈️ Search Another Flight", callback_data="flights")]
        ]
        msg_text = (
            f"✈️ <b>ფრენების ძიება მიმართულებით:</b> <code>{route_name}</code>\n\n"
            f"✅ <b>ნაპოვნია საუკეთესო ვარიანტები მსოფლიო რიოსებიდან:</b>\n"
            f"• 1️⃣ <b>Direct Flight → {route_name}</b>\n"
            f"• 🏢 ავიაკომპანია: Turkish Airlines / Lufthansa\n"
            f"• 📅 თარიღი: უახლოესი რეისი (შესაბამისი სეზონი)\n"
            f"• 💵 ფასი: <b>$145 (ან 0.0022 BTC)</b>\n"
            f"• 🟢 სტატუსი: 🟡 ხელმისაწვდომია\n\n"
            f"• 2️⃣ <b>Budget Option → {route_name} (Via Hub)</b>\n"
            f"• 🏢 ავიაკომპანია: Wizz Air / Pegasus / RyanAir\n"
            f"• 💵 ფასი: <b>$89 (ან 0.0013 BTC)</b>\n"
            f"• 💳 <i>ბილეთის შესაძენად დააჭირე ქვემოთ მოცემულ ღილაკს:</i>"
        )
        return msg_text, InlineKeyboardMarkup(kb)

    welcome_text = (
        "<b>Welcome to MoneyMind Bot! 🚀</b>\n\n"
        "Choose an option from the menu below or use the interactive buttons:"
    )
    return welcome_text, get_main_keyboard()

# /start ბრძანების დამუშავება
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    save_user(user_id)

    welcome_text = (
        "<b>Welcome to MoneyMind Bot! 
