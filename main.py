import os
import logging
import requests
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ლოგირების გამართვა
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# შენი მოქმედი ტოკენი
TELEGRAM_BOT_TOKEN = "8883435722:AAHHc0s38PEl3HOn9TY4rmuunBN3Fzms1gc"

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

# 2. მთავარი მენიუს ღილაკები
def get_main_keyboard():
    keyboard = [
        [KeyboardButton("✈️ Search Cheap Flights"), KeyboardButton("💳 Buy Ticket with Crypto")],
        [KeyboardButton("⛏️ Crypto Mining"), KeyboardButton("📊 Crypto Prices")],
        [KeyboardButton("💰 My Balance"), KeyboardButton("📋 My Orders")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# 3. /start ბრძანების დამუშავება
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "<b>Welcome to MoneyMind Bot! 🚀</b>\n\n"
        "Choose an option from the menu below to get started:"
    )
    await update.message.reply_text(welcome_text, reply_markup=get_main_keyboard(), parse_mode='HTML')

# 4. კრიპტო ფასების მიღება Binance API-დან (სწრაფი და საიმედო)
def get_crypto_prices():
    try:
        symbols = {
            "BTCUSDT": "🪙 <b>Bitcoin (BTC):</b>",
            "ETHUSDT": "🔷 <b>Ethereum (ETH):</b>",
            "BNBUSDT": "🟡 <b>Binance Coin (BNB):</b>",
            "SOLUSDT": "🟣 <b>Solana (SOL):</b>"
        }
        
        result_lines = ["📊 <b>Live Crypto Prices (USD):</b>\n"]
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        
        for symbol, name in symbols.items():
            url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                price = float(response.json().get('price', 0))
                result_lines.append(f"{name} ${price:,.2f}")
            else:
                result_lines.append(f"{name} N/A")
                
        result_lines.append("\n🔄 <i>Updated live from Binance</i>")
        return "\n".join(result_lines)

    except Exception as e:
        logger.error(f"Error fetching prices: {e}")
    
    return "⚠️ Could not fetch prices at the moment. Please try again shortly."

# 5. ღილაკების და ტექსტური შეტყობინებების დამუშავება
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if "Search Cheap Flights" in text:
        reply = (
            "✈️ <b>Cheap Flights Search</b>\n\n"
            "Searching for the best flight deals worldwide...\n"
            "Please send your departure city and destination (e.g., <code>Tbilisi to London</code>)."
        )
    elif "Buy Ticket with Crypto" in text:
        reply = (
            "💳 <b>Buy Tickets with Crypto</b>\n\n"
            "You can purchase airline tickets using BTC, ETH, or USDT.\n"
            "Contact support or select a route to proceed with payment."
        )
    elif "Crypto Mining" in text:
        reply = (
            "⛏️ <b>Crypto Mining Dashboard</b>\n\n"
            "• Active Hashes: 45.2 MH/s\n"
            "• Estimated Daily Earnings: 0.00045 BTC\n"
            "• Status: 🟢 Online"
        )
    elif "Crypto Prices" in text:
        reply = get_crypto_prices()
    elif "My Balance" in text:
        reply = (
            "💰 <b>Your Account Balance:</b>\n\n"
            "💵 USD: $0.00\n"
            "🪙 BTC: 0.00000000\n"
            "🔷 ETH: 0.00000000"
        )
    elif "My Orders" in text:
        reply = (
            "📋 <b>Your Orders:</b>\n\n"
            "You have no active orders at the moment."
        )
    else:
        reply = "Please select an option from the menu below."

    await update.message.reply_text(reply, reply_markup=get_main_keyboard(), parse_mode='HTML')

# 6. მთავარი ფუნქცია
def main():
    server_thread = threading.Thread(target=start_health_server, daemon=True)
    server_thread.start()

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("🚀 MoneyMind Bot is running successfully!")
    application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
