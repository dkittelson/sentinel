"""Telegram public channel monitoring for Levant OSINT.

Monitors ~25 public channels for conflict-related activity. Telegram is
the primary real-time information source in Levant conflict zones —
messages appear minutes before GDELT picks up the same events.

Requires: TELEGRAM_API_ID and TELEGRAM_API_HASH environment variables
(free from my.telegram.org).

Usage:
  # First run: will prompt for phone number authentication
  python ingest/telegram_monitor.py

  # After auth: runs automatically, saves to parquet
"""
import pandas as pd
import os
import asyncio
from datetime import datetime, timedelta

OUTPUT = os.path.join(os.path.dirname(__file__), "..", "data", "processed", "telegram_daily.parquet")

# ── Public channels to monitor ────────────────────────────────
# These are PUBLIC channels — no privacy concerns, same as reading a news site
CHANNELS = {
    # Lebanese news
    "naborsnews": "NNA (National News Agency Lebanon)",
    "mtaborsnews": "MTV Lebanon Breaking",
    "almanaborsnews": "Al Manar (Hezbollah-affiliated)",
    "lebaborsnews": "Lebanon Breaking",

    # IDF / Israeli security
    "tzaborsnews": "Red Alert Israel",
    "oaborsnews": "Pikud HaOref Bot",

    # Regional conflict OSINT
    "intelaborsnews": "Intel Slava Z (OSINT)",
    "aaborsnews": "Ain al-Asifa (Levant OSINT)",

    # Syrian opposition / war
    "syraborsnews": "Syrian Observatory HR",
}

# Conflict keywords (Arabic + Hebrew + English)
URGENT_KEYWORDS_AR = ["قصف", "صاروخ", "غارة", "شهداء", "اشتباك", "عدوان", "قتلى"]
URGENT_KEYWORDS_HE = ["צבע אדום", "ירי", "רקטה", "פיגוע", "חיסול", "תקיפה"]
URGENT_KEYWORDS_EN = ["strike", "rocket", "casualt", "killed", "explosion", "missile", "attack"]
ALL_KEYWORDS = URGENT_KEYWORDS_AR + URGENT_KEYWORDS_HE + URGENT_KEYWORDS_EN


async def fetch_channel_history(client, channel_name, start_date, end_date):
    """Fetch messages from a public channel within a date range."""
    rows = []
    try:
        entity = await client.get_entity(channel_name)
        async for msg in client.iter_messages(entity, offset_date=end_date,
                                               reverse=True):
            if msg.date.replace(tzinfo=None) < start_date:
                continue
            if msg.date.replace(tzinfo=None) > end_date:
                break

            text = msg.text or ""
            has_urgent = any(kw in text.lower() for kw in ALL_KEYWORDS)
            rows.append({
                "date": msg.date.date(),
                "channel": channel_name,
                "has_urgent_keyword": int(has_urgent),
                "text_length": len(text),
            })
    except Exception as e:
        print(f"  Warning: Failed to fetch {channel_name}: {e}")

    return rows


async def ingest_telegram_async():
    """Main async function for Telegram ingestion."""
    try:
        from telethon import TelegramClient
    except ImportError:
        print("telethon not installed. Run: pip install telethon")
        return

    api_id = os.environ.get("TELEGRAM_API_ID")
    api_hash = os.environ.get("TELEGRAM_API_HASH")

    if not api_id or not api_hash:
        print("TELEGRAM_API_ID and TELEGRAM_API_HASH not set.")
        print("Get them free from https://my.telegram.org")
        print("Then: export TELEGRAM_API_ID=xxx TELEGRAM_API_HASH=yyy")
        return

    session_path = os.path.join(os.path.dirname(__file__), "..", "data", "raw", "telegram_session")
    client = TelegramClient(session_path, int(api_id), api_hash)

    await client.start()
    print("Telegram client connected")

    # Fetch last 30 days (Telegram limits historical access)
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=30)

    all_rows = []
    for channel_id, channel_desc in CHANNELS.items():
        print(f"  Fetching {channel_desc}...")
        rows = await fetch_channel_history(client, channel_id, start_date, end_date)
        all_rows.extend(rows)
        print(f"    {len(rows)} messages")

    await client.disconnect()

    if not all_rows:
        print("  No messages fetched")
        return

    df = pd.DataFrame(all_rows)

    # Aggregate per day
    daily = df.groupby("date").agg(
        telegram_message_count=("channel", "size"),
        telegram_urgent_count=("has_urgent_keyword", "sum"),
        telegram_channels_active=("channel", "nunique"),
    ).reset_index()

    # Volume spike (vs 7-day rolling mean)
    daily = daily.sort_values("date")
    roll7 = daily["telegram_message_count"].rolling(7, min_periods=1).mean()
    daily["telegram_volume_spike"] = (daily["telegram_message_count"] / roll7.clip(lower=1)).round(2)

    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    daily.to_parquet(OUTPUT, index=False)
    print(f"  Saved {len(daily)} rows to {OUTPUT}")


def ingest_telegram():
    if os.path.exists(OUTPUT):
        print(f"Cache hit: {OUTPUT}")
        return
    asyncio.run(ingest_telegram_async())


if __name__ == "__main__":
    ingest_telegram()
