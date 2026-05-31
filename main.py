import os
import time
import logging
import threading
import sqlite3
import requests
from datetime import datetime
from pathlib import Path
from flask import Flask
import telebot
from instagrapi import Client

# 1. RENDER'DAN MAXFIY KALITLARNI O'QISH
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
INSTAGRAM_USERNAME = os.getenv("INSTAGRAM_USERNAME")
INSTAGRAM_PASSWORD = os.getenv("INSTAGRAM_PASSWORD")

BASE_DIR = Path(__file__).resolve().parent
DOWNLOAD_DIR = os.path.join(BASE_DIR, "downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)
DB_FILE = os.path.join(BASE_DIR, "bot_database.db")
INSTAGRAM_SESSION_FILE = os.path.join(BASE_DIR, "instagram_session.json")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("__main__")

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)
cl = Client()
cl.delay_range = [5, 10]
cl.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"

processed_text_ids = set()
processed_video_ids = set()

# 2. MA'LUMOTLAR BAZASI SETUP
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS users (telegram_id INTEGER PRIMARY KEY, instagram_user_id TEXT UNIQUE, instagram_username TEXT, created_at TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS video_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, telegram_id INTEGER, instagram_msg_id TEXT UNIQUE, media_url TEXT, status TEXT, error_message TEXT, timestamp TEXT)")
    conn.commit()
    conn.close()

# 3. INSTAGRAM LOGGIN TIZIMI
def login_instagram():
    session_path = Path(INSTAGRAM_SESSION_FILE)
    try:
        if session_path.exists():
            cl.load_settings(str(session_path))
            cl.login(INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD)
            logger.info("✅ Instagram sessiyadan yuklandi")
        else:
            cl.login(INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD)
            cl.dump_settings(INSTAGRAM_SESSION_FILE)
            logger.info("✅ Instagram yangitdan login bo'ldi")
    except Exception as e:
        logger.error(f"❌ Instagram login xatosi: {e}")
        raise e

# 4. INSTAGRAM DIRECT MONITORING (POLLING)
def instagram_polling():
    while True:
        try:
            if not cl.user_id:
                login_instagram()
                
            threads = cl.direct_threads(amount=5)
            for thread in threads:
                for msg in thread.messages:
                    msg_id = str(msg.id)
                    
                    # Telegram ID bog'lash qismi
                    if msg.item_type == "text" and msg_id not in processed_text_ids:
                        processed_text_ids.add(msg_id)
                        text = (msg.text or "").strip()
                        if text.isdigit():
                            tg_id = int(text)
                            sender_id = str(thread.users[0].pk) if thread.users else None
                            sender_name = thread.users[0].username if thread.users else "unknown"
                            
                            if sender_id:
                                conn = sqlite3.connect(DB_FILE)
                                conn.execute("INSERT OR IGNORE INTO users (telegram_id, created_at) VALUES (?, ?)", (tg_id, datetime.now().isoformat()))
                                conn.execute("UPDATE users SET instagram_user_id = ?, instagram_username = ? WHERE telegram_id = ?", (sender_id, sender_name, tg_id))
                                conn.commit()
                                conn.close()
                                cl.direct_send(f"✅ Profilingiz (@{sender_name}) ulandi!", thread_ids=[thread.id])
                                bot.send_message(tg_id, f"🎉 Akkauntingiz (@{sender_name}) muvaffaqiyatli ulandi!")

                # Videolarni ilib olish qismi
                conn = sqlite3.connect(DB_FILE)
                linked_users = conn.execute("SELECT * FROM users WHERE instagram_user_id IS NOT NULL").fetchall()
                conn.close()
                
                thread_user_ids = [str(u.pk) for u in thread.users]
                current_user = None
                for u in linked_users:
                    if u[1] in thread_user_ids:
                        current_user = u
                        break
                
                if current_user:
                    tg_id = current_user[0]
                    for msg in thread.messages:
                        msg_id = str(msg.id)
                        if msg.item_type in ("clip", "media", "felix_share") and msg_id not in processed_video_ids:
                            processed_video_ids.add(msg_id)
                            
                            url = None
                            if hasattr(msg, "clip") and msg.clip: url = msg.clip.video_url
                            elif hasattr(msg, "media") and msg.media and hasattr(msg.media, "video_url"): url = str(msg.media.video_url)
                            
                            if url:
                                safe_name = "".join(c for c in msg_id if c.isalnum())
                                path = os.path.join(DOWNLOAD_DIR, f"{safe_name}.mp4")
                                resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=60, stream=True)
                                with open(path, "wb") as f:
                                    for chunk in resp.iter_content(chunk_size=8192): f.write(chunk)
                                
                                if os.path.exists(path):
                                    with open(path, 'rb') as video:
                                        bot.send_video(tg_id, video, caption="Instadan kelgan video 🚀")
                                    os.remove(path)
                                    
        except Exception as e:
            logger.error(f"⚠ Instagram Direct xatosi: {e}")
            if "Login required" in str(e):
                cl.user_id = None
                if os.path.exists(INSTAGRAM_SESSION_FILE):
                    os.remove(INSTAGRAM_SESSION_FILE)
            time.sleep(60)
        time.sleep(40)

# 5. RENDER PORT UCHUN WEBSERVER
app = Flask('')
@app.route('/')
def home(): return "Bot Active 🚀"

def run_web_server():
    app.run(host="0.0.0.0", port=10000)

# 6. TELEGRAM BANS VA KOMANDALARI
@bot.message_handler(commands=['start'])
def send_welcome(message):
    conn = sqlite3.connect(DB_FILE)
    conn.execute("INSERT OR IGNORE INTO users (telegram_id, created_at) VALUES (?, ?)", (message.chat.id, datetime.now().isoformat()))
    conn.commit()
    conn.close()
    bot.send_message(message.chat.id, f"🤖 **Bot faol!**\n\nSizning Telegram ID raqamingiz: `{message.chat.id}`\n\nUshbu ID raqamni Instagram Direct'ga yozib yuboring.")

# 7. ASOSIY ISHGA TUSHIRISH NUQTASI
if __name__ == "__main__":
    init_db()
    
    # 1. Veb-serverni port 10000 da yoqish (Render talabi)
    threading.Thread(target=run_web_server, daemon=True).start()
    
    # 2. Telegram botni alohida xavfsiz oqimda yuritish
    logger.info("🤖 Bot to'liq faollashdi...")
    threading.Thread(target=bot.infinity_polling, daemon=True).start()
    
    # 3. Instagram pollingni sekinroq ishga tushirish
    try:
        login_instagram()
        threading.Thread(target=instagram_polling, daemon=True).start()
    except Exception as ig_error:
        logger.error(f"🛑 Instagram boshlang'ich ulanishda xato, lekin Telegram ishlayapti: {ig_error}")

    # Konteyner o'chib ketmasligi uchun cheksiz sikl
    while True:
        time.sleep(1)
