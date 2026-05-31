# config.py - Barcha sozlamalar va muhit o'zgaruvchilari

import os
from dotenv import load_dotenv

load_dotenv()

# ── Telegram ──────────────────────────────────────────
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN")

# ── Instagram ─────────────────────────────────────────
INSTAGRAM_USERNAME = os.getenv("INSTAGRAM_USERNAME", "qora.fonvedio")
INSTAGRAM_PASSWORD = os.getenv("INSTAGRAM_PASSWORD", "salom123")

# ── SQLite ────────────────────────────────────────────
DB_PATH = os.getenv("DB_PATH", "bot_database.db")

# ── Polling sozlamalari ───────────────────────────────
# Instagram ban xavfini kamaytirish uchun oqilona interval (soniyada)
INSTAGRAM_POLL_INTERVAL = int(os.getenv("INSTAGRAM_POLL_INTERVAL", "60"))   # 1 daqiqa
INSTAGRAM_SESSION_FILE  = os.getenv("INSTAGRAM_SESSION_FILE", "ig_session.json")

# ── Yuklab olish papkasi ──────────────────────────────
DOWNLOAD_DIR = os.getenv("DOWNLOAD_DIR", "downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# ── Dashboard API (ixtiyoriy) ─────────────────────────
DASHBOARD_SECRET_KEY = os.getenv("DASHBOARD_SECRET_KEY", "change_this_secret")
