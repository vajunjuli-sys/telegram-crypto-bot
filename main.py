import os
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# ლოგირების გამართვა
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# ტოკენი
TELEGRAM_BOT_TOKEN = "8916561192:AAGJinMFZH7-l_OIHGE_q1NltVpPHfIfsi4"
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
    logger.info("Received /start command!")
    user_id = update.effective_user.id
    save_user(user_id)
    await update.message.reply_text(
        "<b>Welcome to MoneyMind Bot! 🚀</b>\n\n💡 <b>აირჩიე სასურველი სექცია ქვემოთ მოცემული მენიუდან:</b>",
        reply_markup=get_inline_keyboard(),
        parse_mode='HTML'
    )

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
        text = "✈️ <b>Cheap Flights Search</b>\n\n🔍 გთხოვ მომწერო სასურველი მიმართულება ან ქალაქი (მაგ: თბილისი - დუბაი):"
    elif data == "buy_ticket":
        text = "💳 <b>Buy Tickets with Crypto</b>\n\n• აირჩიე გადახდის მეთოდი ბილეთის შესასყიდად:\n- USDT (TRC20)\n- TON\n- BTC"
    elif data == "mining":
        text = "⛏️ <b>Crypto Mining Dashboard</b>\n\n• Status: 🟢 Active\n• Hashrate: <b>51.2 MH/s</b>\n• Unpaid Balance: <b>0.0042 BTC</b>"
    elif data == "prices":
        text = "📊 <b>Live Crypto Prices:</b>\n\n• Bitcoin (BTC): $67,450 (+2.4%)\n• Ethereum (ETH): $2,540 (+1.1%)\n• Toncoin (TON): $5.20"
    elif data == "balance":
        text = "💰 <b>Your Balance:</b>\n\n• USD: $0.00\n• Crypto: 0.000000 BTC"
    elif data == "orders":
        text = "📦 <b>Your Orders:</b>\n\nშენ ჯერ არ გაქვს აქტიური შეკვეთები."
    else:
        text = f"რეჟიმი: {data}"
        
    try:
        await query.message.edit_text(text, reply_markup=get_inline_keyboard(), parse_mode='HTML')
    except Exception:
        await query.message.reply_text(text, reply_markup=get_inline_keyboard(), parse_mode='HTML')

def main():
    port = int(os.environ.get('PORT', 10000))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    
    import threading
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    logger.info(f"Health check HTTP server started on port {port}")

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CallbackQueryHandler(handle_callback_query))

    logger.info("Starting bot polling...")
    application.run_polling(drop_pending_updates=True, allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
    
