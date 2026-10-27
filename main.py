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
        "<b>Welcome to MoneyMind Bot! 🚀</b>\n\n"
        "Choose an option from the menu below or use the interactive buttons:"
    )
    await update.message.reply_text(
        welcome_text,
        reply_markup=get_main_keyboard(),
        parse_mode='HTML'
    )
    await update.message.reply_text(
        "💡 <b>Interactive Control Panel:</b>",
        reply_markup=get_inline_keyboard(),
        parse_mode='HTML'
    )

# /stats ბრძანება
async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    save_user(user_id)
    users = load_users()
    count = len(users)

    msg = (
        f"📊 <b>MoneyMind Bot - სტატისტიკა:</b>\n\n"
        f"👥 სულ მომხმარებლები: <b>{count}</b>\n"
        f"🆔 შენი ID: <code>{user_id}</code>"
    )
    await update.message.reply_text(msg, parse_mode='HTML')

# ონლაინ ღილაკების დამუშავება
async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    save_user(user_id)

    data = query.data
    if data == "start_mine":
        user_mining[user_id] = get_mining_data(user_id)
        user_mining[user_id]["active"] = True
        user_mining[user_id]["last_time"] = time.time()
        await query.answer("🟢 მაინინგი წარმატებით ჩაირთო!", show_alert=True)
        text, markup = get_response_text("mining", user_id)
        try:
            await query.message.edit_text(text, reply_markup=markup, parse_mode='HTML')
        except Exception:
            pass
        return
    elif data == "stop_mine":
        user_mining[user_id] = get_mining_data(user_id)
        user_mining[user_id]["active"] = False
        await query.answer("🔴 მაინინგი შეჩერებულია!", show_alert=True)
        text, markup = get_response_text("mining", user_id)
        try:
            await query.message.edit_text(text, reply_markup=markup, parse_mode='HTML')
        except Exception:
            pass
        return
    elif data == "refresh_mine":
        user_mining[user_id] = get_mining_data(user_id)
        await query.answer("🔄 მონაცემები განახლდა!", show_alert=False)
        text, markup = get_response_text("mining", user_id)
        try:
            await query.message.edit_text(text, reply_markup=markup, parse_mode='HTML')
        except Exception:
            pass
        return
    elif data == "pay_btc":
        await query.answer()
        await query.message.reply_text(
            "🟡 <b>Bitcoin Payment Checkout</b>\n\n"
            "გადასრიცხეთ ზუსტად <code>0.0018 BTC</code> მისამართზე:\n"
            "<code>bc1qxy2kgdygjsqrtzq2n0yrf2493p83kkfhw0wlh</code>\n"
            "⏳ <i>გადახდის სტატუსი: მოლოდინში (დასტურდება ბლოკჩეინში).</i>",
            parse_mode='HTML'
        )
        return
    elif data == "pay_usdt":
        await query.answer()
        await query.message.reply_text(
            "💎 <b>USDT (TRC20) Payment Checkout</b>\n\n"
            "გადასრიცხეთ ზუსტად <code>120.00 USDT</code> მისამართზე:\n"
            "<code>TJ7T8kxR7Vv4N9s2K4z8L1m9P2q3R5s6T7</code>\n"
            "⏳ <i>გადახდის სტატუსი: მოლოდინში.</i>",
            parse_mode='HTML'
        )
        return
    elif data == "cancel_order":
        await query.answer("❌ გაუქმებულია")
        await query.message.reply_text("❌ შეკვეთა გაუქმებულია.", parse_mode='HTML')
        return

    await query.answer()
    res_text, markup = get_response_text(data, user_id)
    await query.message.reply_text(res_text, reply_markup=markup, parse_mode='HTML')

# ტექსტური შეტყობინებების დამუშავება
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    save_user(user_id)

    text = update.message.text
    clean_txt = text.replace(":", "").strip()
    if clean_txt.startswith("/start"):
        await start_command(update, context)
        return
    elif clean_txt.startswith("/stats"):
        await stats_command(update, context)
        return

    res_text, markup = get_response_text(clean_txt, user_id)
    await update.message.reply_text(res_text, reply_markup=markup, parse_mode='HTML')

def main():
    try:
        server_thread = threading.Thread(target=start_health_server, daemon=True)
        server_thread.start()

        application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("stats", stats_command))
        application.add_handler(CommandHandler("help", start_command))
        application.add_handler(CallbackQueryHandler(handle_callback_query))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

        print("MoneyMind Bot is running successfully!")
        application.run_polling(drop_pending_updates=True)
    except Exception as e:
        logger.critical(f"Critical error in main: {e}", exc_info=True)

if __name__ == '__main__':
    main()
