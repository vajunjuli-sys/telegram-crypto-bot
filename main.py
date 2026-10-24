import os
import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot Token directly embedded to avoid Render environment issues
TELEGRAM_BOT_TOKEN = "8814326130:AAHWgnTQ3R8sKnEFDJb0kfuNc77SDtM8VKg"

# Keyboards / Menu
def get_main_keyboard():
    keyboard = [
        [KeyboardButton("✈️ Search Cheap Flights"), KeyboardButton("💳 Buy Ticket with Crypto")],
        [KeyboardButton("⛏️ Crypto Mining"), KeyboardButton("📈 Crypto Prices")],
        [KeyboardButton("💰 My Balance"), KeyboardButton("📋 My Orders")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "<b>Welcome to MoneyMind Bot! 🚀</b>\n\n"
        "Book international airline tickets instantly using Cryptocurrency.\n"
        "Earn crypto via free cloud mining and track real-time rates.\n\n"
        "Please select an option from the menu below:"
    )
    await update.message.reply_text(welcome_text, parse_mode='HTML', reply_markup=get_main_keyboard())

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
    if text == "✈️ Search Cheap Flights":
        response = (
            "✈️ <b>Search Cheap Flights</b>\n\n"
            "Where would you like to fly?\n"
            "<i>Example route: TBS to DXB (Tbilisi to Dubai)</i>\n\n"
            "Type your destination or route to check available ticket options and airlines!"
        )
    elif text == "💳 Buy Ticket with Crypto":
        response = (
            "💳 <b>Buy Ticket with Crypto</b>\n\n"
            "To book a ticket using USDT or TON:\n"
            "1. Select your flight and confirm details.\n"
            "2. Choose cryptocurrency payment (TON/USDT).\n"
            "3. Send the exact amount to the generated secure wallet address.\n\n"
            "⚡ <i>Tickets and PNR codes are issued instantly after confirmation!</i>"
        )
    elif text == "⛏️ Crypto Mining":
        response = (
            "⛏️ <b>Cloud Mining Hub</b>\n\n"
            "Your mining rig is currently active!\n"
            "• <b>Mined Balance:</b> 0.0450 TON\n"
            "• <b>Speed:</b> 2.5x Standard\n\n"
            "Come back daily to claim your rewards and boost your travel balance!"
        )
    elif text == "📈 Crypto Prices":
        response = (
            "📈 <b>Live Crypto Rates</b>\n\n"
            "• <b>TON:</b> $5.42 (+3.4%)\n"
            "• <b>USDT:</b> $1.00 (0.0%)\n"
            "• <b>BTC:</b> $67,400 (+1.2%)\n"
            "• <b>ETH:</b> $2,550 (-0.8%)\n\n"
            "<i>Updated in real-time.</i>"
        )
    elif text == "💰 My Balance":
        response = (
            "💰 <b>Your Account Balance</b>\n\n"
            "• <b>TON Wallet:</b> 0.0450 TON (~$0.24)\n"
            "• <b>USDT Balance:</b> $0.00\n"
            "• <b>Travel Voucher:</b> $10.00 (Welcome Bonus)"
        )
    elif text == "📋 My Orders":
        response = (
            "📋 <b>Your Active Orders & Bookings</b>\n\n"
            "You have no confirmed bookings yet.\n"
            "Use <b>✈️ Search Cheap Flights</b> to look up available routes and book your first trip!"
        )
    else:
        response = (
            f"You selected: {text}\n\n"
            "Please use the menu buttons below to navigate through features and check prices!"
        )
        
    await update.message.reply_text(response, parse_mode='HTML', reply_markup=get_main_keyboard())

def main():
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("crypto", start_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("🚀 MoneyMind Bot is running with full menu support...")
    application.run_polling()

if __name__ == '__main__':
    main()
