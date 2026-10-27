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
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "r") as f:
                return set(line.strip() for line in f if line.strip())
        except Exception as e:
            logger.error(f"Error loading users: {e}")
    return set()

def save_user(user_id):
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

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain; charset=utf-8')
        self.end_headers()
        self.wfile.write(b"OK")
    
    def log_message(self, format, *args):
        return

def get_main_keyboard():
    keyboard = [
        [KeyboardButton("✈️ Search Cheap Flights"), KeyboardButton("💳 Buy Ticket with Crypto")],
        [KeyboardButton("⛏️ Crypto Mining"), KeyboardButton("📊 Crypto Prices")],
        [KeyboardButton("💰 My Balance"), KeyboardButton("📦 My Orders")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, is_persistent=True)

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

def get_crypto_prices():
    return (
        "📊 <b>Live Crypto Prices (USD):</b>\n\n"
        "🟡 <b>Bitcoin (BTC):</b> $67,450.00\n"
        "🔷 <b>Ethereum (ETH):</b> $2,540.00\n"
        "🟠 <b>Binance Coin (BNB):</b> $590.00\n"
        "🟣 <b>Solana (SOL):</b> $172.50\n"
        "<i>🔄 Updated live from Market Data</i>"
    )

def get_response_text(key, user_id=None):
    text = str(key).strip()
    
    if "Flight" in text or "ფრენ" in text:
        return "✈️ <b>Cheap Flights Search</b>\n\n🔍 Searching for the best flight deals worldwide...\n\nგთხოვ მომწერო ნებისმიერი მიმართულება ან ქალაქი (მაგალითად: <i>თბილისი მილანი</i>):", get_main_keyboard()
    elif "Buy Ticket" in text or "ყიდვა" in text:
        kb = [[InlineKeyboardButton("✅ Pay 0.0018 BTC", callback_data="pay_btc")], [InlineKeyboardButton("❌ Cancel", callback_data="cancel_order")]]
        return "💳 <b>Buy Tickets with Crypto</b>\n\n• აირჩიე გადახდის მეთოდი ბილეთის შესასყიდად:", InlineKeyboardMarkup(kb)
    elif "Mining" in text or "მაინინგ" in text:
        return "⛏️ <b>Crypto Mining Dashboard</b>\n\n• Status: 🟢 Active (Mining...)\n• Active Hashrate: <b>51.2 MH/s</b>\n• Mined Balance: <b>0.00001850 BTC</b>", get_main_keyboard()
    elif "Prices" in text or "ფას" in text:
        return get_crypto_prices(), get_main_keyboard()
    elif "Balance" in text or "ბალანს" in text:
        return "💰 <b>Your Account Balance:</b>\n\n💵 USD: $0.00\n🟡 BTC: 0.00000000", get_main_keyboard()
    elif "Orders" in text or "შეკვეთ" in text:
        return "📦 <b>Your Orders:</b>\n\nYou have no active orders at the moment.", get_main_keyboard()

    return f"✈️ <b>ფრენების ძიება მიმართულებით:</b> <code>{key}</code>\n\n✅ <b>ნაპოვნია საუკეთესო ვარიანტები:</b>\n• 1️⃣ Direct Flight → $145 (ან 0.0022 BTC)\n• 2️⃣ Budget Option → $89", get_main_keyboard()

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    save_user(user_id)
    await update.message.reply_text("<b>Welcome to MoneyMind Bot! 🚀</b>", reply_markup=get_main_keyboard(), parse_mode='HTML')
    await update.message.reply_text("💡 <b>Interactive Control Panel:</b>", reply_markup=get_inline_keyboard(), parse_mode='HTML')

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    save_user(user_id)
    count = len(load_users())
    await update.message.reply_text(f"📊 Total Users: <b>{count}</b>\n🆔 Your ID: <code>{user_id}</code>", parse_mode='HTML')

async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    res_text, markup = get_response_text(query.data, update.effective_user.id)
    try:
        await query.message.edit_text(res_text, reply_markup=markup, parse_mode='HTML')
    except Exception:
        await query.message.reply_text(res_text, reply_markup=markup, parse_mode='HTML')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    save_user(user_id)
    text = update.message.text
    res_text, markup = get_response_text(text, user_id)
    await update.message.reply_text(res_text, reply_markup=markup, parse_mode='HTML')

def main():
    try:
        application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("stats", stats_command))
        application.add_handler(CallbackQueryHandler(handle_callback_query))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

        port = int(os.environ.get('PORT', 10000))
        server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
        
        import threading
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()
        
        application.run_polling(drop_pending_updates=True)
    except Exception as e:
        logger.critical(f"Critical error: {e}", exc_info=True)

if __name__ == '__main__':
    main()
    
