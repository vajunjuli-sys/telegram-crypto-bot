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
        [KeyboardButton("Search Cheap Flights"), KeyboardButton("Buy Ticket with Crypto")],
        [KeyboardButton("Crypto Mining"), KeyboardButton("Crypto Prices")],
        [KeyboardButton("My Balance"), KeyboardButton("My Orders")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, is_persistent=True)

def get_inline_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("Search Flights", callback_data="flights"),
            InlineKeyboardButton("Buy Ticket", callback_data="buy_ticket")
        ],
        [
            InlineKeyboardButton("Mining Dashboard", callback_data="mining"),
            InlineKeyboardButton("Live Prices", callback_data="prices")
        ],
        [
            InlineKeyboardButton("Balance", callback_data="balance"),
            InlineKeyboardButton("Orders", callback_data="orders")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_crypto_prices():
    return "Live Crypto Prices:\n\nBitcoin (BTC): $67,450.00\nEthereum (ETH): $2,540.00\nSolana (SOL): $172.50"

def get_response_text(key, user_id=None):
    clean_key = str(key).strip().lower()
    
    if "flight" in clean_key or "ფრენ" in clean_key:
        return "Cheap Flights Search: Please send any destination or city.", get_main_keyboard()
    elif "buy" in clean_key or clean_key == "buy_ticket":
        kb = [[InlineKeyboardButton("Pay 0.0018 BTC", callback_data="pay_btc")], [InlineKeyboardButton("Cancel", callback_data="cancel_order")]]
        return "Buy Tickets with Crypto: Select payment method.", InlineKeyboardMarkup(kb)
    elif "mining" in clean_key:
        return "Crypto Mining Dashboard: Status Online", get_main_keyboard()
    elif "price" in clean_key or clean_key == "prices":
        return get_crypto_prices(), get_main_keyboard()
    elif "balance" in clean_key:
        return "Your Account Balance: $0.00", get_main_keyboard()
    elif "order" in clean_key:
        return "Your Orders: No active orders.", get_main_keyboard()

    return "Welcome to MoneyMind Bot! Choose an option below:", get_main_keyboard()

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    save_user(user_id)
    await update.message.reply_text("Welcome to MoneyMind Bot! 🚀", reply_markup=get_main_keyboard())
    await update.message.reply_text("Interactive Control Panel:", reply_markup=get_inline_keyboard())

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    save_user(user_id)
    count = len(load_users())
    await update.message.reply_text(f"Total Users: {count}\nYour ID: {user_id}")

async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    res_text, markup = get_response_text(query.data, update.effective_user.id)
    await query.message.reply_text(res_text, reply_markup=markup)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    save_user(user_id)
    text = update.message.text
    res_text, markup = get_response_text(text, user_id)
    await update.message.reply_text(res_text, reply_markup=markup)

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
    
