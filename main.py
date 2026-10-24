import os
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'Bot is alive and running!')

def run_server():
    port = int(os.environ.get('PORT', 10000))
    server = HTTPServer(('0.0.0.0', port), SimpleHandler)
    server.serve_forever()

threading.Thread(target=run_server, daemon=True).start()

import asyncio
import json
import logging
import os
import sqlite3
import time
from datetime import datetime, timezone
from decimal import Decimal
from email.utils import parsedate_to_datetime
from math import ceil
from pathlib import Path
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen
from xml.etree import ElementTree

from telegram import ReplyKeyboardMarkup, Update
from telegram.error import InvalidToken, RetryAfter, TelegramError
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

COINGECKO_PRICE_API = "https://api.coingecko.com/api/v3/simple/price"
CRYPTO_ASSETS = {
    "btc": ("bitcoin", "Bitcoin"),
    "eth": ("ethereum", "Ethereum"),
    "sol": ("solana", "Solana"),
    "doge": ("dogecoin", "Dogecoin"),
}
ALTCOIN_SYMBOLS = ["eth", "sol", "doge"]
PRICE_REQUEST_TIMEOUT_SECONDS = 10
MAX_PRICE_RESPONSE_BYTES = 64 * 1024

NEWS_FEEDS = (
    ("CoinDesk", "https://www.coindesk.com/arc/outboundfeeds/rss/"),
    ("Cointelegraph", "https://cointelegraph.com/rss"),
)
NEWS_REQUEST_TIMEOUT_SECONDS = 10
MAX_NEWS_FEED_BYTES = 256 * 1024

DATABASE_PATH = Path(__file__).with_name("bot_data.sqlite3")
SATOSHIS_PER_BTC = 100_000_000
MINING_REWARD_SATOSHIS = 1
MINING_COOLDOWN_SECONDS = 30
LEADERBOARD_LIMIT = 10


async def start( update: Update, context: ContextTypes.DEFAULT_TYPE ) -> None:
    """Welcome a user when they start the bot."""
    del context
    if update.message:
        await update.message.reply_text(
            "Welcome! Choose a command from the menu below to check crypto "
            "prices, mine virtual Bitcoin, view balances, or read the latest "
            "news.",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[
                    ["/crypto", "/mine"],
                    ["/balance", "/leaderboard"],
                    ["/news", "/help"],
                ],
                resize_keyboard=True,
                is_persistent=True,
                input_field_placeholder="Choose a command",
            ),
        )


async def help_command( update: Update, context: ContextTypes.DEFAULT_TYPE ) -> None:
    """Show available commands."""
    del context
    if update.message:
        await update.message.reply_text(
            "Available commands:\n"
            "/start — start the bot\n"
            "/help — show this help message\n"
            "/price — live Bitcoin price in USD\n"
            "/crypto — live Ethereum, Solana, and Dogecoin prices\n"
            "/crypto [btc|eth|sol|doge] — price for one coin\n"
            "/eth, /sol, /doge — coin price shortcuts\n"
            "/mine — mine 1 virtual satoshi (30-second cooldown)\n"
            "/balance — check your virtual BTC balance\n"
            "/leaderboard — see the top 10 virtual miners\n"
            "/news — get the 3 latest Bitcoin/crypto headlines\n\n"
            "/stats — admin: count registered users\n"
            "/broadcast <text> — admin: message all registered users\n\n"
            "Mining balances are virtual game points, not real Bitcoin."
        )

def fetch_crypto_prices_usd(symbols: list[str]) -> dict[str, Decimal]:
    """Fetch and validate CoinGecko prices for the requested symbols."""
    requested_symbols = list(dict.fromkeys(symbols))
    if not requested_symbols or any(
        symbol not in CRYPTO_ASSETS for symbol in requested_symbols
    ):
        raise ValueError("Unsupported cryptocurrency symbol")

    coin_ids = [CRYPTO_ASSETS[symbol][0] for symbol in requested_symbols]
    query = urlencode({"ids": ",".join(coin_ids), "vs_currencies": "usd"})
    request = Request(
        f"{COINGECKO_PRICE_API}?{query}",
        headers={
            "Accept": "application/json",
            "User-Agent": "TelegramCryptoBot/1.0",
        },
    )
    with urlopen(request, timeout=PRICE_REQUEST_TIMEOUT_SECONDS) as response:
        if response.status != 200:
            raise ValueError(f"CoinGecko returned HTTP {response.status}")
        response_body = response.read(MAX_PRICE_RESPONSE_BYTES + 1)

    if len(response_body) > MAX_PRICE_RESPONSE_BYTES:
        raise ValueError("CoinGecko response exceeded the size limit")

    payload = json.loads(response_body)
    if not isinstance(payload, dict):
        raise ValueError("CoinGecko returned an invalid response")

    prices: dict[str, Decimal] = {}
    for symbol in requested_symbols:
        coin_id = CRYPTO_ASSETS[symbol][0]
        coin_data = payload.get(coin_id)
        if not isinstance(coin_data, dict):
            raise ValueError("CoinGecko did not return a requested coin")
        raw_price = coin_data.get("usd")
        if isinstance(raw_price, bool) or not isinstance(
            raw_price, (int, float, str)
        ):
            raise ValueError("CoinGecko returned an invalid price")

        price = Decimal(str(raw_price))
        if not price.is_finite() or price <= 0:
            raise ValueError("CoinGecko returned an invalid price")
        prices[symbol] = price

    return prices


async def send_crypto_prices(update: Update, symbols: list[str]) -> None:
    """Fetch and send live USD prices for one or more supported coins."""
    if not update.message:
        return

    try:
        prices = await asyncio.to_thread(fetch_crypto_prices_usd, symbols)
    except Exception as error:
        logger.warning(
            "Crypto price lookup failed (%s).", type(error).__name__
        )
        await update.message.reply_text(
            "I couldn't fetch crypto prices right now. Please try again shortly."
        )
        return

    lines = ["Live crypto prices (USD):"]
    for symbol in symbols:
        name = CRYPTO_ASSETS[symbol][1]
        lines.append(f"{name} ({symbol.upper()}): ${prices[symbol]:,.2f}")
    checked_at = datetime.now(timezone.utc).strftime("%H:%M:%S UTC")
    lines.append(f"Source: CoinGecko · checked at {checked_at}")
    await update.message.reply_text("\n".join(lines))


async def price_command( update: Update, context: ContextTypes.DEFAULT_TYPE ) -> None:
    """Reply with the current Bitcoin price in US dollars."""
    del context
    await send_crypto_prices(update, ["btc"])


async def crypto_command( update: Update, context: ContextTypes.DEFAULT_TYPE ) -> None:
    """Show all supported altcoin prices or one selected coin."""
    if not update.message:
        return

    if not context.args:
        symbols = ALTCOIN_SYMBOLS
    elif len(context.args) == 1 and context.args[0].lower() in CRYPTO_ASSETS:
        symbols = [context.args[0].lower()]
    else:
        await update.message.reply_text(
            "Usage: /crypto [btc|eth|sol|doge]. "
            "With no symbol, /crypto shows ETH, SOL, and DOGE."
        )
        return

    await send_crypto_prices(update, symbols)


async def crypto_shortcut_command( update: Update, context: ContextTypes.DEFAULT_TYPE ) -> None:
    """Handle /eth, /sol, and /doge single-price shortcuts."""
    del context
    if not update.message or not update.message.text:
        return

    command = (
        update.message.text.split(maxsplit=1)[0]
        .split("@", maxsplit=1)[0]
        .lstrip("/")
        .lower()
    )
    if command in CRYPTO_ASSETS and command != "btc":
        await send_crypto_prices(update, [command])


def parse_news_date(date_text: str) -> datetime:
    """Parse an RSS publication date and normalize it to UTC."""
    try:
        published_at = parsedate_to_datetime(date_text)
    except (TypeError, ValueError):
        published_at = datetime.fromisoformat(date_text.replace("Z", "+00:00"))

    if published_at.tzinfo is None:
        published_at = published_at.replace(tzinfo=timezone.utc)
    return published_at.astimezone(timezone.utc)


def fetch_news_feed(source: str, feed_url: str) -> list[dict[str, object]]:
    """Fetch a public RSS feed and return safe, dated headlines."""
    request = Request(
        feed_url,
        headers={
            "Accept": "application/rss+xml, application/xml, text/xml",
            "User-Agent": "TelegramCryptoBot/1.0",
        },
    )
    with urlopen(request, timeout=NEWS_REQUEST_TIMEOUT_SECONDS) as response:
        if response.status != 200:
            raise ValueError(f"{source} returned HTTP {response.status}")
        response_body = response.read(MAX_NEWS_FEED_BYTES + 1)

    if len(response_body) > MAX_NEWS_FEED_BYTES:
        raise ValueError(f"{source} feed exceeded the size limit")

    root = ElementTree.fromstring(response_body)
    channel = root.find("channel")
    if channel is None:
        raise ValueError(f"{source} returned an unsupported RSS feed")

    headlines: list[dict[str, object]] = []
    for item in channel.findall("item"):
        title = " ".join((item.findtext("title") or "").split())
        link = (item.findtext("link") or "").strip()
        date_text = (item.findtext("pubDate") or "").strip()
        if not title or not link or not date_text:
            continue

        try:
            published_at = parse_news_date(date_text)
            parsed_link = urlsplit(link)
        except (TypeError, ValueError, OverflowError):
            continue

        if parsed_link.scheme != "https" or not parsed_link.hostname:
            continue

        headlines.append(
            {
                "title": title[:200],
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
