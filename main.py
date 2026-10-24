import os
import sqlite3
import random
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters

# Simple HTTP server for Render deployment check
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'Crypto Airline Bot is running!')

def run_server():
    port = int(os.environ.get('PORT', 10000))
    server = HTTPServer(('0.0.0.0', port), SimpleHandler)
    server.serve_forever()

# Database setup
def init_db():
    conn = sqlite3.connect('bot_database.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_balances (
            user_id INTEGER PRIMARY KEY,
            balance_usdt REAL DEFAULT 500.0,
            mined_crypto REAL DEFAULT 0.0
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            order_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            flight_details TEXT,
            price_usdt REAL,
            pnr_code TEXT
        )
    ''')
    conn.commit()
    conn.close()

def get_user_balance(user_id):
    conn = sqlite3.connect('bot_database.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO user_balances (user_id, balance_usdt, mined_crypto) VALUES (?, 500.0, 0.0)', (user_id,))
    conn.commit()
    cursor.execute('SELECT balance_usdt, mined_crypto FROM user_balances WHERE user_id = ?', (user_id,))
    res = cursor.fetchone()
    conn.close()
    return res if res else (500.0, 0.0)

def update_balance(user_id, new_balance):
    conn = sqlite3.connect('bot_database.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('UPDATE user_balances SET balance_usdt = ? WHERE user_id = ?', (new_balance, user_id))
    conn.commit()
    conn.close()

def add_order(user_id, flight_details, price_usdt, pnr_code):
    conn = sqlite3.connect('bot_database.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO orders (user_id, flight_details, price_usdt, pnr_code) VALUES (?, ?, ?, ?)',
                   (user_id, flight_details, price_usdt, pnr_code))
    conn.commit()
    conn.close()

def get_user_orders(user_id):
    conn = sqlite3.connect('bot_database.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('SELECT flight_details, price_usdt, pnr_code FROM orders WHERE user_id = ?', (user_id,))
    orders = cursor.fetchall()
    conn.close()
    return orders

# Flight mock database
FLIGHTS = [
    {"id": "1", "route": "Tbilisi (TBS) ➔ Istanbul (IST)", "price": 120.0, "time": "Tomorrow, 10:30 AM"},
    {"id": "2", "route": "Kutaisi (KUT) ➔ Vienna (VIE)", "price": 85.0, "time": "Oct 28, 14:15 PM"},
    {"id": "3", "route": "Tbilisi (TBS) ➔ Berlin (BER)", "price": 150.0, "time": "Nov 02, 08:00 AM"},
    {"id": "4", "route": "Batumi (BUS) ➔ Dubai (DXB)", "price": 210.0, "time": "Nov 05, 19:45 PM"},
]

# /start command
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    init_db()
    keyboard = [
        ["✈️ Search Cheap Flights", "💳 Buy Ticket with Crypto"],
        ["⛏️ Crypto Mining", "📊 Crypto Prices"],
        ["💰 My Balance", "📋 My Orders"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    welcome_text = (
        "<b>Welcome to Crypto Flight Booking Bot! ✈️🌍</b>\n\n"
        "Book international airline tickets instantly using Cryptocurrency.\n"
        "Earn crypto via free cloud mining and track real-time rates.\n\n"
        "Please select an option from the menu below:"
    )
    await update.message.reply_text(welcome_text, parse_mode='HTML', reply_markup=reply_markup)

# Handling text messages from keyboard
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    balance, mined = get_user_balance(user_id)

    if text == "✈️ Search Cheap Flights" or text == "💳 Buy Ticket with Crypto":
        msg = "<b>✈️ Available Cheap Flights:</b>\n\n"
        keyboard = []
        for flight in FLIGHTS:
            msg += f"• <b>{flight['route']}</b>\n  Departure: {flight['time']}\n  Price: <b>${flight['price']} USDT</b>\n\n"
            keyboard.append([InlineKeyboardButton(f"Book {flight['route'].split('➔')[1]} - ${flight['price']}", callback_data=f"buy_{flight['id']}")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(msg, parse_mode='HTML', reply_markup=reply_markup)

    elif text == "⛏️ Crypto Mining":
        mined_add = round(random.uniform(0.5, 2.5), 2)
        new_balance = balance + mined_add
        update_balance(user_id, new_balance)
        
        await update.message.reply_text(
            f"<b>⛏️ Cloud Mining Active!</b>\n\n"
            f"You successfully mined <b>+{mined_add} USDT</b> worth of crypto!\n"
            f"Updated Wallet Balance: <b>${new_balance:.2f} USDT</b>",
            parse_mode='HTML'
        )

    elif text == "📊 Crypto Prices":
        prices_text = (
            "<b>📊 Live Crypto Market Rates:</b>\n\n"
            "• <b>Bitcoin (BTC):</b> $67,450.00 USDT (+2.4%)\n"
            "• <b>Ethereum (ETH):</b> $3,520.50 USDT (+1.8%)\n"
            "• <b>TON (Toncoin):</b> $6.80 USDT (+5.1%)\n"
            "• <b>Tether (USDT):</b> $1.00 USD"
        )
        await update.message.reply_text(prices_text, parse_mode='HTML')

    elif text == "💰 My Balance":
        await update.message.reply_text(
            f"<b>💳 Your Crypto Wallet:</b>\n\n"
            f"Balance: <b>${balance:.2f} USDT</b>\n\n"
            f"<i>Tip: Use command <code>/deposit 100</code> to top up your balance for testing.</i>",
            parse_mode='HTML'
        )

    elif text == "📋 My Orders":
        orders = get_user_orders(user_id)
        if not orders:
            await update.message.reply_text("📋 You have no active ticket bookings yet.")
        else:
            msg = "<b>📋 Your Booked Tickets:</b>\n\n"
            for flight_details, price, pnr in orders:
                msg += f"✈️ <b>Flight:</b> {flight_details}\n💰 <b>Paid:</b> ${price} USDT\n🎟️ <b>PNR Code:</b> <code>{pnr}</code>\n-------------------------\n"
            await update.message.reply_text(msg, parse_mode='HTML')

# Inline buying callback
async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    balance, _ = get_user_balance(user_id)

    if query.data.startswith("buy_"):
        flight_id = query.data.split("_")[1]
        flight = next((f for f in FLIGHTS if f["id"] == flight_id), None)

        if flight:
            if balance < flight["price"]:
                await query.edit_message_text(
                    f"❌ <b>Insufficient Balance!</b>\n\n"
                    f"Ticket Price: ${flight['price']} USDT\n"
                    f"Your Balance: ${balance:.2f} USDT\n\n"
                    f"Use <code>/deposit 200</code> to top up your wallet.",
                    parse_mode='HTML'
                )
            else:
                new_bal = balance - flight["price"]
                update_balance(user_id, new_bal)
                pnr = "PNR-" + "".join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", k=6))
                add_order(user_id, flight["route"], flight["price"], pnr)

                await query.edit_message_text(
                    f"✅ <b>Flight Ticket Successfully Purchased!</b>\n\n"
                    f"✈️ <b>Route:</b> {flight['route']}\n"
                    f"📅 <b>Time:</b> {flight['time']}\n"
                    f"💰 <b>Paid:</b> ${flight['price']} USDT\n"
                    f"🎟️ <b>Electronic PNR Code:</b> <code>{pnr}</code>\n\n"
                    f"Remaining Balance: <b>${new_bal:.2f} USDT</b>\n"
                    f"Show this PNR code at the airport check-in counter.",
                    parse_mode='HTML'
                )

# Deposit simulation command
async def deposit_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    balance, _ = get_user_balance(user_id)
    try:
        amount = float(context.args[0])
        new_bal = balance + amount
        update_balance(user_id, new_bal)
        await update.message.reply_text(f"✅ Successfully deposited <b>+${amount:.2f} USDT</b>!\nNew balance: <b>${new_bal:.2f} USDT</b>", parse_mode='HTML')
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: <code>/deposit 100</code> (Specify amount to deposit)", parse_mode='HTML')

def main():
    TOKEN = "8733823493:AAGCALU3J6Ha-a-Jq9cdyYx0phQGGxHkLiQ"
    
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("deposit", deposit_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(button_click))
    
    application.run_polling()

if __name__ == '__main__':
    main()
