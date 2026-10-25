import os
import requests
import time
import datetime
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

# --- კონფიგურაცია ---
TELEGRAM_BOT_TOKEN = "8814326130:AAH4etd9dQYrpWbUMaTMZ2wBRNK8-tRuFeY"
TELEGRAM_CHAT_ID = "1090757467"

# შენი პირადი API გასაღები
ODDS_API_KEY = "baf4f55404f1122cdef45b7d148cdf7c"

# სპორტის სახეობები მონიტორინგისთვის
SPORTS_TO_SCAN = [
    'rugby_league',
    'rugby_union',
    'soccer_epl',
    'soccer_spain_la_liga',
    'soccer_italy_serie_a',
    'soccer_germany_bundesliga',
    'soccer_france_ligue_one',
    'soccer_uefa_champs_league',
    'basketball_nba'
]

# მარტივი სერვერი Render-ზე გაშვების უზრუნველსაყოფად
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain; charset=utf-8')
        self.end_headers()
        self.wfile.write('სპორტული სიგნალების ბოტი აქტიურია!'.encode('utf-8'))

def start_health_server():
    port = int(os.environ.get('PORT', 10000))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    server.serve_forever()

def get_upcoming_matches(sport):
    """იღებს უახლოეს მატჩებს API-დან"""
    url = f"https://api.the-odds-api.com/v4/sports/{sport}/odds/"
    params = {
        'apiKey': ODDS_API_KEY,
        'regions': 'eu',
        'markets': 'h2h,totals',
        'dateFormat': 'iso'
    }
    
    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"⚠️ API შეცდომა {sport}-ისთვის: {response.status_code}")
            return []
    except Exception as e:
        print(f"❌ შეცდომა მოთხოვნისას: {e}")
        return []

def background_scanner(app):
    """მთავარი ფონური ციკლი - ეძებს მატჩებს და აგზავნის სიგნალებს"""
    time.sleep(5)
    processed_matches = set()
    daily_signals = []  
    
    while True:
        print("🔍 იწყება მატჩების სკანირება...")
        now = datetime.datetime.utcnow()
        
        for sport in SPORTS_TO_SCAN:
            matches = get_upcoming_matches(sport)
            
            for match in matches:
                match_id = match.get('id')
                commence_raw = match.get('commence_time')
                
                if not commence_raw or match_id in processed_matches:
                    continue
                
                commence_time = datetime.datetime.fromisoformat(commence_raw.replace('Z', '+00:00')).replace(tzinfo=None)
                minutes_left = (commence_time - now).total_seconds() / 60
                
                if 20 <= minutes_left <= 30:
                    sport_title = match.get('sport_title', 'სპორტი')
                    home = match.get('home_team')
                    away = match.get('away_team')
                    
                    for bm in match.get('bookmakers', []):
                        for market in bm.get('markets', []):
                            
                            if market.get('key') == 'h2h':
                                for outcome in market.get('outcomes', []):
                                    current_price = outcome.get('price', 0)
                                    initial_price = outcome.get('initial_price', current_price)
                                    
                                    if initial_price > 0:
                                        drop_percent = ((initial_price - current_price) / initial_price) * 100
                                        
                                        if drop_percent >= 35 and initial_price >= 3.0:
                                            alert = (
                                                f"🚨 <b>მაღალი კუში + ვარდნა!</b>\n\n"
                                                f"🏉 <b>სპორტი:</b> {sport_title}\n"
                                                f"⚔️ <b>მატჩი:</b> {home} vs {away}\n"
                                                f"🎯 <b>პოზიცია:</b> {outcome.get('name')}\n"
                                                f"📉 <b>ვარდნა:</b> {drop_percent:.1f}%\n"
                                                f"💰 <b>საწყისი კუში:</b> {initial_price:.2f} ➔ <b>ახალი:</b> {current_price:.2f}\n"
                                                f"⏱️ <b>დაწყებამდე დარჩენილია:</b> {int(minutes_left)} წუთი!"
                                            )
                                            try:
                                                app.bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=alert, parse_mode='HTML')
                                            except Exception as e:
                                                print(f"Error sending alert: {e}")
                                            processed_matches.add(match_id)
                                            daily_signals.append(f"{home} vs {away} ({outcome.get('name')}) - კუში: {current_price}")
                            
                            elif market.get('key') == 'totals':
                                for outcome in market.get('outcomes', []):
                                    name = outcome.get('name', '')
                                    price = outcome.get('price', 0)
                                    
                                    if any(target in name for target in ['Over 3.5', 'Over 4.5', 'Over 5.5']):
                                        alert = (
                                            f"⚽ <b>მაღალი ტოტალი!</b>\n\n"
                                            f"🏆 <b>სპორტი:</b> {sport_title}\n"
                                            f"⚔️ <b>მატჩი:</b> {home} vs {away}\n"
                                            f"🎯 <b>პოზიცია:</b> {name}\n"
                                            f"💰 <b>კუში:</b> {price:.2f}\n"
                                            f"⏱️ <b>დაწყებამდე დარჩენილია:</b> {int(minutes_left)} წუთი!"
                                        )
                                        try:
                                            app.bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=alert, parse_mode='HTML')
                                        except Exception as e:
                                            print(e)
                                        processed_matches.add(match_id)
                                        daily_signals.append(f"{home} vs {away} ({name}) - კუში: {price}")

        if len(daily_signals) > 0:
            express_msg = "📊 <b>დღის ნაღდი ექსპრესების კრებული (ყველა ნაპოვნი):</b>\n\n"
            for s in daily_signals:
                express_msg += f"• {s}\n"
            express_msg += "\n🔥 <i>წარმატებები! ყველა სიგნალი გაერთიანდა ბილეთში.</i>"
            try:
                app.bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=express_msg, parse_mode='HTML')
            except Exception as e:
                print(e)
            daily_signals.clear()

        time.sleep(180)

# --- ტელეგრამის ბრძანებები ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "<b>სპორტული სიგნალების ბოტი აქტიურია! 🎯🏉⚽</b>\n\n"
        "მიმდინარეობს მატჩების ავტომატური სკანირება.\n"
        "როგორც კი მაღალი კუში ან კოეფიციენტის მკვეთრი ვარდნა დაფიქსირდება, შეტყობინებას ავტომატურად მიიღებთ!"
    )
    await update.message.reply_text(welcome_text, parse_mode='HTML')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("გამარჯობა! მე ვარ სპორტული სიგნალების ბოტი. სიგნალებს გამოვგზავნი ავტომატურად, როცა მატჩები გამოჩნდება.", parse_mode='HTML')

def main():
    # ვებ სერვერის გაშვება ფონურ რეჟიმში (Render-ისთვის)
    server_thread = threading.Thread(target=start_health_server, daemon=True)
    server_thread.start()
    
    # აპლიკაციის აწყობა ახალი სტილით (რათა /start-ს უპასუხოს)
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    
    # ჰენდლერების დამატება
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # ფონური სკანერის გაშვება ცალკე ნაკადში
    scanner_thread = threading.Thread(target=background_scanner, args=(application,), daemon=True)
    scanner_thread.start()
    
    print("🚀 ბოტი წარმატებით გაშვებულია და უსმენს ბრძანებებს!")
    application.run_polling()

if __name__ == '__main__':
    main()
