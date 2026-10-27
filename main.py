import os
import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# ლოგირების გამართვა
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# ტოკენი და რენდერის ლინკი
TELEGRAM_BOT_TOKEN = "8916561192:AAGJinMFZH7-l_OIHGE_q1NltVpPHfIfsi4"
RENDER_URL = "https://telegram-crypto-bot-s5lk.onrender.com"
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
    logger.info("Received /start command via Webhook!")
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

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    save_user(user_id)
    text = update.message.text
    logger.info(f"Received message from {user_id}: {text}")
    
    clean = text.strip()
    
    if "Search Cheap Flights" in clean or "ფრენ" in clean:
        reply = "✈️ <b>Cheap Flights Search</b>\n\n🔍 გთხოვ მომწერო სასურველი მიმართულება ან ქალაქი:"
    elif "Buy Ticket with Crypto" in clean or "ყიდვა" in clean or "ბილეთ" in clean:
        reply = "💳 <b>Buy Tickets with Crypto</b>\n\n• აირჩიე გადახდის მეთოდი ბილეთის შესასყიდად:\n- USDT\n- TON\n- BTC"
    elif "Crypto Mining" in clean or "მაინინგ" in clean:
        reply = "⛏️ <b>Crypto Mining Dashboard</b>\n\n• Status: 🟢 Active\n• Hashrate: <b>51.2 MH/s</b>"
    elif "Crypto Prices" in clean or "ფას" in clean or "კურს" in clean:
        reply = "📊 <b>Live Crypto Prices:</b>\n\n• Bitcoin: $67,450\n• Ethereum: $2,540"
    elif "My Balance" in clean or "ბალანს" in clean:
        reply = "💰 <b>Your Balance:</b> $0.00"
    elif "My Orders" in clean or "შეკვეთ" in clean:
        reply = "📦 <b>Your Orders:</b> No active orders."
    else:
        reply = f"✈️ <b>ძიების შედეგი მიმართულებით:</b> <code>{text}</code>\n\n✅ <b>ნაპოვნია ვარიანტები:</b>\n• Direct Flight → $145"

    await update.message.reply_text(reply, reply_markup=get_main_keyboard(), parse_mode='HTML')

def main():
    port = int(os.environ.get('PORT', 10000))
    
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CallbackQueryHandler(handle_callback_query))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info(f"Starting webhook on port {port}...")
    
    # ვებჰუქის გაშვება რენდერის პორტითა და ლინკით
    application.run_webhook(
        listen="0.0.0.0",
        port=port,
        secret_token="moneymind_secret_2026",
        webhook_url=f"{RENDER_URL}/{TELEGRAM_BOT_TOKEN}"
    )

if __name__ == '__main__':
    main()
    
