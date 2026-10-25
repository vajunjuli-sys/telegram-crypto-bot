import os
import logging
import requests
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

# ლოგირების ჩართვა
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# შენი ახალი ტოკენი BotFather-დან
TELEGRAM_BOT_TOKEN = "8949326406:AAE-dz8YFEwDgcYQJ8adjjk0ELC3oi0l2Yg"

# Render Web Service Health Check
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain; charset=utf-8')
        self.end_headers()
        self.wfile.write('MoneyMind Bot Status: OK'.encode('utf-8'))

def start_health_server():
    port = int(os.environ.get('PORT', 10000))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    server.serve_forever()

# კლავიატურის ღილაკები
def get_main_keyboard():
    keyboard = [
        [KeyboardButton("✈️ Search Cheap Flights"), KeyboardButton("💳 Buy Ticket with Crypto")],
        [KeyboardButton("⛏️ Crypto Mining"), KeyboardButton("📊 Crypto Prices")],
        [KeyboardButton("💰 My Balance"), KeyboardButton("📋 My Orders")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# /start ბრძანება
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "<b>Welcome to MoneyMind Bot! 🚀</b>\n\n"
        "Choose an option from the menu below to get started:"
    )
    await update.message.reply_text(welcome_text, reply_markup=get_main_keyboard(), parse_mode='HTML')

# კრიპტო ფასების მიღება (CoinGecko API-დან)
def get_crypto_prices():
    try:
        url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,binancecoin,solana,cardano&vs_currencies=usd"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            btc = data.get('bitcoin', {}).get('usd', 'N/A')
            eth = data.get('ethereum', {}).get('usd', 'N/A')
            bnb = data.get('binancecoin', {}).get('usd', 'N/A')
            sol = data.get('solana', {}).get('usd', 'N/A')
            
            return (
                f"📊 <b>Live Crypto Prices (USD):</b>\n\n"
                f"🪙 <b>Bitcoin (BTC):</b> ${btc:,}\n"
                f"🔷 <b>Ethereum (ETH):</b> ${eth:,}\n"
                f"🟡 <b>Binance Coin (BNB):</b> ${bnb:,}\n"
                f"🟣 <b>Solana (SOL):</b> ${sol:,}\n\n"
                f"🔄 <i>Updated just now</i>"
            )
    except Exception as e:
        logger.error(f"Error fetching prices: {e}")
    
    return "⚠️ Could not fetch prices at the moment. Please try again shortly."

# ტექსტური შეტყობინებების დამუშავება
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

def main():
    # ფონური ვებ-სერვერის გაშვება Render-ისთვის
    server_thread = threading.Thread(target=start_health_server, daemon=True)
    server_thread.start()

    # ტელეგრამ ბოტის გაშვება
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("🚀 MoneyMind Bot is running successfully!")
    application.run_polling()

if __name__ == '__main__':
    main()
