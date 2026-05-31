# telegram_bot.py - Telegram bot (pyTelegramBotAPI / telebot)

import logging
import threading
import telebot
from telebot.types import Message

from config import TELEGRAM_BOT_TOKEN, INSTAGRAM_USERNAME
import database as db

logger = logging.getLogger(__name__)

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN, parse_mode="HTML")


# ── /start buyrug'i ────────────────────────────────────────────────────────────

@bot.message_handler(commands=["start"])
def cmd_start(message: Message):
    tg_id       = message.from_user.id
    tg_username = message.from_user.username or message.from_user.first_name

    # Foydalanuvchini bazaga qo'shish
    db.upsert_telegram_user(tg_id, tg_username)
    user = db.get_user_by_telegram_id(tg_id)

    if user and user["instagram_user_id"]:
        bot.send_message(message.chat.id,
            f"👋 Xush kelibsiz, <b>{tg_username}</b>!\n\n"
            f"✅ Siz allaqachon Instagram akkauntingiz bilan bog'langansiz:\n"
            f"📸 <b>@{user['instagram_username']}</b>\n\n"
            f"Instagram DM ga video yuboring — avtomatik bu yerga keladi! 🚀"
        )
        return

    bot.send_message(message.chat.id,
        f"👋 Xush kelibsiz, <b>{tg_username}</b>!\n\n"
        f"🔗 <b>Instagram akkauntingizni bog'lash uchun:</b>\n\n"
        f"1️⃣ Instagram ilovasini oching\n"
        f"2️⃣ <b>@{INSTAGRAM_USERNAME}</b> profiliga kiring\n"
        f"3️⃣ Direct (DM) xabar yuboring va quyidagi <b>ID raqamingizni</b> yozing:\n\n"
        f"<code>{tg_id}</code>\n\n"
        f"⏳ Xabarni yuborganingizdan so'ng bir necha soniyada bog'lanish tasdiqlanganligi haqida xabar olasiz.",
        reply_markup=_main_keyboard(user)
    )


# ── /status buyrug'i ───────────────────────────────────────────────────────────

@bot.message_handler(commands=["status"])
def cmd_status(message: Message):
    tg_id = message.from_user.id
    user  = db.get_user_by_telegram_id(tg_id)

    if not user:
        bot.send_message(message.chat.id, "❌ Siz hali ro'yxatdan o'tmagansiz. /start bosing.")
        return

    if user["instagram_user_id"]:
        bot.send_message(message.chat.id,
            f"✅ <b>Bog'langan</b>\n"
            f"📱 Telegram ID: <code>{tg_id}</code>\n"
            f"📸 Instagram: <b>@{user['instagram_username']}</b>\n"
            f"🕐 Bog'langan vaqt: {user['linked_at'] or 'Nomaʼlum'}"
        )
    else:
        bot.send_message(message.chat.id,
            f"⏳ <b>Bog'lanmagan</b>\n"
            f"📱 Sizning ID: <code>{tg_id}</code>\n\n"
            f"Instagram DM ga <b>@{INSTAGRAM_USERNAME}</b> ga ushbu ID ni yuboring."
        )


# ── /help buyrug'i ─────────────────────────────────────────────────────────────

@bot.message_handler(commands=["help"])
def cmd_help(message: Message):
    bot.send_message(message.chat.id,
        "📖 <b>Yordam</b>\n\n"
        "/start — Botni ishga tushirish va ID olish\n"
        "/status — Bog'lanish holatini tekshirish\n"
        "/unlink — Instagram akkauntini ajratish\n"
        "/help — Ushbu yordam xabari\n\n"
        "💡 <b>Qanday ishlaydi?</b>\n"
        "1. /start bosib ID oling\n"
        "2. ID ni Instagram DM ga yuboring\n"
        "3. Bog'langandan so'ng videolaringiz avtomatik keladi!"
    )


# ── /unlink buyrug'i ──────────────────────────────────────────────────────────

@bot.message_handler(commands=["unlink"])
def cmd_unlink(message: Message):
    tg_id = message.from_user.id
    user  = db.get_user_by_telegram_id(tg_id)

    if not user or not user["instagram_user_id"]:
        bot.send_message(message.chat.id, "⚠️ Bog'langan Instagram akkaunt topilmadi.")
        return

    with db.get_connection() as conn:
        conn.execute("""
            UPDATE users
            SET instagram_user_id = NULL, instagram_username = NULL, linked_at = NULL
            WHERE telegram_id = ?
        """, (tg_id,))

    bot.send_message(message.chat.id,
        f"✅ Instagram akkauntingiz (@{user['instagram_username']}) ajratildi.\n"
        f"Qayta bog'lash uchun /start bosing."
    )


# ── Callback funksiyalar (Instagram bot tomonidan chaqiriladi) ─────────────────

def send_message_to_user(telegram_id: int, text: str = None, video_path: str = None):
    """
    Instagram bot callback: matn yoki video yuborish.
    Bu funksiya threading muhitida chaqiriladi — thread-safe.
    """
    try:
        if text:
            bot.send_message(telegram_id, text)

        if video_path:
            with open(video_path, "rb") as vf:
                bot.send_video(
                    telegram_id, vf,
                    caption="📹 Instagram dan yangi video!",
                    supports_streaming=True
                )
            logger.info("📤 Video yuborildi: TG=%s, fayl=%s", telegram_id, video_path)

    except telebot.apihelper.ApiException as exc:
        logger.error("Telegram API xatosi (ID=%s): %s", telegram_id, exc)
    except FileNotFoundError:
        logger.error("Video fayl topilmadi: %s", video_path)
    except Exception as exc:
        logger.exception("send_message_to_user kutilmagan xato: %s", exc)


# ── Klaviatura ─────────────────────────────────────────────────────────────────

def _main_keyboard(user=None):
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(telebot.types.KeyboardButton("📊 Holat"), 
               telebot.types.KeyboardButton("❓ Yordam"))
    return markup


@bot.message_handler(func=lambda m: m.text in ("📊 Holat", "❓ Yordam"))
def handle_buttons(message: Message):
    if message.text == "📊 Holat":
        cmd_status(message)
    elif message.text == "❓ Yordam":
        cmd_help(message)


# ── Botni ishga tushirish ──────────────────────────────────────────────────────

def run_bot():
    """Telegramni polling bilan ishga tushirish (alohida thread uchun)."""
    logger.info("🤖 Telegram bot polling boshlandi...")
    bot.infinity_polling(timeout=30, long_polling_timeout=30)
