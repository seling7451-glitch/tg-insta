# main.py - Asosiy kirish nuqtasi: barcha tizimlarni threading bilan boshqarish

import logging
import signal
import sys
import threading

# ── Logging sozlamasi ──────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("bot.log", encoding="utf-8"),
    ]
)
logger = logging.getLogger(__name__)

# ── Modullarni import qilish ───────────────────────────────────────────────────
import database as db
from telegram_bot import run_bot, send_message_to_user
from instagram_bot import InstagramBot, stop_polling
from dashboard_api import run_dashboard


def main():
    logger.info("=" * 60)
    logger.info("🚀  Instagram ↔ Telegram Bot Tizimi ishga tushmoqda...")
    logger.info("=" * 60)

    # 1. Ma'lumotlar bazasini tayyorlash
    db.init_db()

    # 2. Instagram bot ni sozlash
    ig_bot = InstagramBot()
    try:
        ig_bot.login()
    except Exception as exc:
        logger.critical("❌ Instagram login muvaffaqiyatsiz: %s", exc)
        logger.critical("   INSTAGRAM_USERNAME va INSTAGRAM_PASSWORD ni tekshiring.")
        sys.exit(1)

    # Telegram callback ni o'rnatish
    ig_bot.set_telegram_callback(send_message_to_user)

    # 3. Threadlarni yaratish
    threads: list[threading.Thread] = []

    # Thread 1: Telegram bot
    tg_thread = threading.Thread(
        target=run_bot,
        name="TelegramBot",
        daemon=True
    )
    threads.append(tg_thread)

    # Thread 2: Instagram polling
    ig_thread = threading.Thread(
        target=ig_bot.poll_loop,
        name="InstagramPolling",
        daemon=True
    )
    threads.append(ig_thread)

    # Thread 3: Dashboard API
    dash_thread = threading.Thread(
        target=run_dashboard,
        kwargs={"host": "0.0.0.0", "port": 5000},
        name="DashboardAPI",
        daemon=True
    )
    threads.append(dash_thread)

    # 4. Barcha threadlarni ishga tushirish
    for t in threads:
        t.start()
        logger.info("✅ Thread ishga tushdi: %s", t.name)

    # 5. Graceful shutdown
    def shutdown(signum, frame):
        logger.info("\n🛑 To'xtatish signali olindi, tozalash...")
        stop_polling()
        sys.exit(0)

    signal.signal(signal.SIGINT,  shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    logger.info("✅ Tizim to'liq ishga tushdi! Ctrl+C bilan to'xtating.\n")

    # Asosiy thread tirik turishi uchun
    for t in threads:
        t.join()


if __name__ == "__main__":
    main()
