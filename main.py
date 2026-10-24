import os
import sqlite3
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# მარტივი სერვერი Render-ისთვის, რომ ბოტი მუშაობდეს 24/7
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'Bot is alive and running!')

def run_server():
    port = int(os.environ.get('PORT', 10000))
    server = HTTPServer(('0.0.0.0', port), SimpleHandler)
    server.serve_forever()

# ბაზის და კრიპტო ბალანსების ცხრილის ინიციალიზაცია
conn = sqlite3.connect('bot_database.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_balances (
        user_id INTEGER PRIMARY KEY,
        balance_crypto REAL DEFAULT 0.0
    )
''')
conn.commit()

# ახალი /start ბრძანება და კრიპტო-ავიაკასის მენიუ
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # შევამოწმოთ და დავარეგისტრიროთ მომხმარებელი ბაზაში თუ არ არსებობს
    cursor.execute('INSERT OR IGNORE INTO user_balances (user_id, balance_crypto) VALUES (?, ?)', (user_id, 0.0))
    conn.commit()
    
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
    # შენი ბოტის ტოკენი (Render-ის Environment Variables-დან ან პირდაპირ)
    TOKEN = os.environ.get("BOT_TOKEN", "შენი_ტოკენი_აქ")
    
    application = ApplicationBuilder().token(TOKEN).build()
    
    # ჰენდლერის რეგისტრაცია
    application.add_handler(CommandHandler("start", start_command))
    
    application.run_polling()

if __name__ == '__main__':
    # ვუშვებთ ვებ სერვერს ფონურ რეჟიმში
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    
    # ვუშვებთ ტელეგრამ ბოტს
    main()
    "link": link,
                "source": source,
                "published_at": published_at,
            }
        )

    if not headlines:
        raise ValueError(f"{source} feed had no usable headlines")
    return headlines


async def news_command( update: Update, context: ContextTypes.DEFAULT_TYPE ) -> None:
    """Send the three newest headlines from public crypto RSS feeds."""
    del context
    if not update.message:
        return

    results = await asyncio.gather(
        *(
            asyncio.to_thread(fetch_news_feed, source, url)
            for source, url in NEWS_FEEDS
        ),
        return_exceptions=True,
    )

    headlines: list[dict[str, object]] = []
    unavailable_sources: list[str] = []
    for (source, _), result in zip(NEWS_FEEDS, results):
        if isinstance(result, BaseException):
            unavailable_sources.append(source)
        else:
            headlines.extend(result)

    if unavailable_sources:
        logger.warning(
            "Crypto news feeds unavailable: %s.",
            ", ".join(unavailable_sources),
        )
    if not headlines:
        await update.message.reply_text(
            "I couldn't fetch crypto news right now. Please try again shortly."
        )
        return

    headlines.sort(
        key=lambda item: item["published_at"],
        reverse=True,
    )
    latest: list[dict[str, object]] = []
    seen_titles: set[str] = set()
    for headline in headlines:
        normalized_title = " ".join(str(headline["title"]).casefold().split())
        if normalized_title in seen_titles:
            continue
        seen_titles.add(normalized_title)
        latest.append(headline)
        if len(latest) == 3:
            break

    lines = ["Latest Bitcoin & crypto headlines:"]
    for number, headline in enumerate(latest, start=1):
        published_at = headline["published_at"]
        assert isinstance(published_at, datetime)
        lines.append(
            f"{number}. {headline['title']}\n"
            f"{headline['source']} · "
            f"{published_at.strftime('%Y-%m-%d %H:%M UTC')}\n"
            f"{headline['link']}"
        )
    if unavailable_sources:
        lines.append(
            "Some news sources were unavailable: "
            + ", ".join(unavailable_sources)
            + "."
        )
    await update.message.reply_text("\n\n".join(lines))


def initialize_database() -> None:
    """Create persistent storage for miners and registered command users."""
    with sqlite3.connect(DATABASE_PATH, timeout=10) as connection:
        connection.execute(
            """ CREATE TABLE IF NOT EXISTS miners ( telegram_user_id INTEGER PRIMARY KEY, display_name TEXT NOT NULL, username TEXT, balance_satoshis INTEGER NOT NULL DEFAULT 0, last_mined_at REAL ) """
        )
        connection.execute(
            """ CREATE TABLE IF NOT EXISTS registered_users ( telegram_user_id INTEGER PRIMARY KEY, first_seen_at REAL NOT NULL, last_command_at REAL NOT NULL ) """
        )
        now = time.time()
        connection.execute(
            """ INSERT OR IGNORE INTO registered_users ( telegram_user_id, first_seen_at, last_command_at ) SELECT telegram_user_id, COALESCE(last_mined_at, ?), COALESCE(last_mined_at, ?) FROM miners """,
            (now, now),
        )


def register_telegram_user(user_id: int) -> None:
    """Insert a user once and refresh their last-command timestamp."""
    now = time.time()
    with sqlite3.connect(DATABASE_PATH, timeout=10) as connection:
        connection.execute(
            """ INSERT INTO registered_users ( telegram_user_id, first_seen_at, last_command_at ) VALUES (?, ?, ?) ON CONFLICT(telegram_user_id) DO UPDATE SET last_command_at = excluded.last_command_at """,
            (user_id, now, now),
        )


def get_registered_user_count() -> int:
    """Return the number of unique Telegram users who have used a command."""
    with sqlite3.connect(DATABASE_PATH, timeout=10) as connection:
        row = connection.execute(
            "SELECT COUNT(*) FROM registered_users"
        ).fetchone()
    return int(row[0]) if row else 0


def get_registered_user_ids() -> list[int]:
    """Return unique registered Telegram user IDs for broadcasting."""
    with sqlite3.connect(DATABASE_PATH, timeout=10) as connection:
        rows = connection.execute(
            """ SELECT telegram_user_id FROM registered_users ORDER BY first_seen_at ASC """
        ).fetchall()
    return [int(row[0]) for row in rows]


def get_configured_admin_user_id() -> int | None:
    """Read the single authorized admin ID from project environment."""
    raw_admin_id = os.getenv("ADMIN_TELEGRAM_USER_ID", "").strip()
    if not raw_admin_id.isdecimal():
        return None
    admin_user_id = int(raw_admin_id)
    return admin_user_id if admin_user_id > 0 else None


def is_admin_user(user_id: int | None) -> bool:
    """Check whether a Telegram user matches the configured admin ID."""
    admin_user_id = get_configured_admin_user_id()
    return (
        user_id is not None
        and admin_user_id is not None
        and user_id == admin_user_id
    )


async def track_command_user( update: Update, context: ContextTypes.DEFAULT_TYPE ) -> None:
    """Register any Telegram user who sends a bot command."""
    del context
    if not update.effective_user:
        return
    try:
        await asyncio.to_thread(
            register_telegram_user, update.effective_user.id
        )
    except sqlite3.Error as error:
        logger.error(
            "Command user registration failed (%s).",
            type(error).__name__,
        )


def mine_virtual_bitcoin( user_id: int, display_name: str, username: str | None, now: float | None = None, ) -> tuple[bool, int, int]:
    """Atomically award a virtual satoshi, enforcing the mining cooldown."""
    current_time = time.time() if now is None else now
    with sqlite3.connect(DATABASE_PATH, timeout=10) as connection:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute(
            """ SELECT balance_satoshis, last_mined_at FROM miners WHERE telegram_user_id = ? """,
            (user_id,),
        ).fetchone()

        if row is None:
            balance_satoshis = 0
            last_mined_at = None
            connection.execute(
                """ INSERT INTO miners ( telegram_user_id, display_name, username, balance_satoshis, last_mined_at ) VALUES (?, ?, ?, 0, NULL) """,
                (user_id, display_name, username),
            )
        else:
            balance_satoshis, last_mined_at = row
            connection.execute(
                """ UPDATE miners SET display_name = ?, username = ? WHERE telegram_user_id = ? """,
                (display_name, username, user_id),
            )

        if last_mined_at is not None:
            seconds_remaining = (
                MINING_COOLDOWN_SECONDS - (current_time - last_mined_at)
            )
            if seconds_remaining > 0:
                return False, balance_satoshis, ceil(seconds_remaining)

        balance_satoshis += MINING_REWARD_SATOSHIS
        connection.execute(
            """ UPDATE miners SET balance_satoshis = ?, last_mined_at = ? WHERE telegram_user_id = ? """,
            (balance_satoshis, current_time, user_id),
        )
        return True, balance_satoshis, 0


def get_balance_satoshis(user_id: int) -> int:
    """Read one player's virtual balance."""
    with sqlite3.connect(DATABASE_PATH, timeout=10) as connection:
        row = connection.execute(
            "SELECT balance_satoshis FROM miners WHERE telegram_user_id = ?",
            (user_id,),
        ).fetchone()
    return int(row[0]) if row else 0


def get_leaderboard() -> list[tuple[str, str | None, int]]:
    """Return the highest virtual balances."""
    with sqlite3.connect(DATABASE_PATH, timeout=10) as connection:
        rows = connection.execute(
            """ SELECT display_name, username, balance_satoshis FROM miners WHERE balance_satoshis > 0 ORDER BY balance_satoshis DESC, display_name COLLATE NOCASE ASC LIMIT ? """,
            (LEADERBOARD_LIMIT,),
        ).fetchall()
    return [
        (str(name), username, int(balance))
        for name, username, balance in rows
    ]


def format_virtual_balance(satoshis: int) -> str:
    """Format integer satoshis without floating-point rounding."""
    btc = Decimal(satoshis) / Decimal(SATOSHIS_PER_BTC)
    unit = "satoshi" if satoshis == 1 else "sats"
    return f"{btc:.8f} BTC ({satoshis:,} {unit})"


async def mine_command( update: Update, context: ContextTypes.DEFAULT_TYPE ) -> None:
    """Award virtual Bitcoin to the Telegram user."""
    del context
    if not update.message or not update.effective_user:
        return

    user = update.effective_user
    display_name = " ".join(user.full_name.split())[:60] or "Player"
    try:
        mined, balance, seconds_remaining = await asyncio.to_thread(
            mine_virtual_bitcoin,
            user.id,
            display_name,
            user.username,
        )
    except sqlite3.Error as error:
        logger.warning(
            "Mining database operation failed (%s).",
            type(error).__name__,
        )
        await update.message.reply_text(
            "I couldn't update your mining balance right now. Please try again."
        )
        return

    if mined:
        await update.message.reply_text(
            f"Mining complete: +{MINING_REWARD_SATOSHIS} virtual satoshi.\n"
            f"Your balance: {format_virtual_balance(balance)}\n"
            f"You can mine again in {MINING_COOLDOWN_SECONDS} seconds."
        )
    else:
        await update.message.reply_text(
            f"You can mine again in {seconds_remaining} seconds.\n"
            f"Your balance: {format_virtual_balance(balance)}"
        )


async def balance_command( update: Update, context: ContextTypes.DEFAULT_TYPE ) -> None:
    """Show the caller's persisted virtual Bitcoin balance."""
    del context
    if not update.message or not update.effective_user:
        return

    try:
        balance = await asyncio.to_thread(
            get_balance_satoshis, update.effective_user.id
        )
    except sqlite3.Error as error:
        logger.warning(
            "Balance lookup failed (%s).", type(error).__name__
        )
        await update.message.reply_text(
            "I couldn't read your balance right now. Please try again."
        )
        return
    awai
# კრიპტო ბალანსის ცხრილის შექმნა ბაზაში
cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_balances (
        user_id INTEGER PRIMARY KEY,
        balance_crypto REAL DEFAULT 0.0
    )
''')
conn.commit()
from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import ContextTypes

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # მთავარი მენიუს ღილაკები
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
from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import ContextTypes, CommandHandler

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # მთავარი მენიუს ღილაკები
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
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("start", start_command))
    
    
