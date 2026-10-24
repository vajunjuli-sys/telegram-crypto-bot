import os
import sqlite3
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# მარტივი სერვერი Render-ისთვის
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'Bot is alive and running!')

def run_server():
    port = int(os.environ.get('PORT', 10000))
    server = HTTPServer(('0.0.0.0', port), SimpleHandler)
    server.serve_forever()

# ახალი /start ბრძანება (ბაზა იხსნება ფუნქციის შიგნით უსაფრთხოდ)
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # ვხსნით ბაზას ადგილზევე
    conn = sqlite3.connect('bot_database.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_balances (
            user_id INTEGER PRIMARY KEY,
            balance_crypto REAL DEFAULT 0.0
        )
    ''')
    cursor.execute('INSERT OR IGNORE INTO user_balances (user_id, balance_crypto) VALUES (?, ?)', (user_id, 0.0))
    conn.commit()
    conn.close()
    
    keyboard = [
        ["✈️ იაფი ბილეთების ძებნა", "💳 ბილეთის ყიდვა კრიპთოთი"],
        ["💰 ჩემი კრიპტო-ბალანსი", "📋 ჩემი შეკვეთები"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "მოგესალმებით! ეს არის კრიპტო-ავიაკასა და საერთაშორისო ფრენების პლატფორმა.\n"
        "აირჩიეთ სასურველი მოქმედება ქვემოთ მოცემული მენიუდან:",
        reply_markup=reply_markup
    )

def main():
    TOKEN = os.environ.get("BOT_TOKEN", "შენი_ტოკენი_აქ")
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start_command))
    application.run_polling()

if __name__ == '__main__':
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    main()
    
