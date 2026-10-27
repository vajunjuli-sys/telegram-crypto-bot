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

# ახალი ტოკენი BotFather-დან
TELEGRAM_BOT_TOKEN = "8883435722:AAEZRmUYuboqW5Su3by5lSk7X53jW4UZ6U"
USERS_FILE = "users.txt"

def load_users():
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "r") as f:
                return set(line.strip() for line in f if line.strip())
        except Exception:
            pass
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
        except Exception:
            pass

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
    data = query.data
    
    if data == "flights":
        text = "✈️ <b>Cheap Flights Search</b>\n\n🔍 გთხოვ მომწერო სასურველი მიმართულება ან ქალაქი (მაგ: <i>თბილისი მილანი</i>):"
    elif data == "buy_ticket":
        text = "💳 <b>Buy Tickets with Crypto</b>\n\n• აირჩიე გადახდის მეთოდი ბილეთის შესასყიდად:"
    elif data == "mining":
        text = "⛏️ <b>Crypto Mining Dashboard</b>\n\n• Status: 🟢 Active\n• Hashrate: <b>51.2 MH/s</b>"
    elif data == "prices":
        text = "📊 <b>Live Crypto Prices:</b>\n\nBitcoin: $67,450\nEthereum: $2,540"
    elif data == "balance":
        text = "💰 <b>Your Balance:</b> $0.00"
    elif data == "orders":
        text = "📦 <b>Your Orders:</b> No active orders."
    else:
        text = f"რეჟიმი: {data}"
        
    try:
        await query.message.edit_text(text, reply_markup=get_inline_keyboard(), parse_mode='HTML')
    except Exception:
        await query.message.reply_text(text, reply_markup=get_inline_keyboard(), parse_mode='HTML')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    save_user(user_id)
    text = update.message.text
    logger.info(f"Received message from {user_id}: {text}")
    
    clean = text.lower()
    
    if "flight" in clean or "ფრენ" in clean:
        reply = "✈️ <b>Cheap Flights Search</b>\n\n🔍 გთხოვ მომწერო სასურველი მიმართულება ან ქალაქი (მაგ: <i>თბილისი მილანი</i>):"
    elif "buy" in clean or "ყიდვა" in clean or "ticket" in clean:
        reply = "💳 <b>Buy Tickets with Crypto</b>\n\n• აირჩიე გადახდის მეთოდი ბილეთის შესასყიდად:"
    elif "mining" in clean or "მაინინგ" in clean:
        reply = "⛏️ <b>Crypto Mining Dashboard</b>\n\n• Status: 🟢 Active\n• Hashrate: <b>51.2 MH/s</b>"
    elif "price" in clean or "ფას" in clean:
        reply = "📊 <b>Live Crypto Prices:</b>\n\nBitcoin: $67,450\nEthereum: $2,540"
    elif "balance" in clean or "ბალანს" in clean:
        reply = "💰 <b>Your Balance:</b> $0.00"
    elif "order" in clean or "შეკვეთ" in clean:
        reply = "📦 <b>Your Orders:</b> No active orders."
    else:
        reply = f"✈️ <b>ფრენების ძიება მიმართულებით:</b> <code>{text}</code>\n\n✅ <b>ნაპოვნია ვარიანტები:</b>\n• Direct Flight → $145\n• Budget → $89"

    await update.message.reply_text(reply, reply_markup=get_main_keyboard(), parse_mode='HTML')

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
        
        logger.info("Starting polling with drop_pending_updates=True...")
        application.run_polling(drop_pending_updates=True)
    except Exception as e:
        logger.critical(f"Critical error: {e}", exc_info=True)

if __name__ == '__main__':
    main()
    
