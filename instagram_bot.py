# instagram_bot.py - Instagram polling va video uzatish (To'g'rilangan variant)

import os
import time
import logging
import threading
import requests
from pathlib import Path
from datetime import datetime

from instagrapi import Client
from instagrapi.exceptions import LoginRequired, ClientError

from config import (
    INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD,
    INSTAGRAM_SESSION_FILE, INSTAGRAM_POLL_INTERVAL, DOWNLOAD_DIR
)
import database as db

logger = logging.getLogger(__name__)

# Global to'xtatish bayrog'i
_stop_event = threading.Event()


class InstagramBot:
    """instagrapi asosida Instagram DM polling va video yuklab olish."""

    def __init__(self):
        self.cl = Client()
        self.cl.delay_range = [2, 5]          # so'rovlar orasida tasodifiy pauza
        self._processed_text_ids: set[str] = set() # Matnlar (ID) uchun alohida kesh
        self._processed_video_ids: set[str] = set() # Videolar uchun alohida kesh
        self._tg_send_callback = None          # Telegram ga yuborish funksiyasi

    # ── Login ──────────────────────────────────────────────────────────────

    def login(self):
        """Sessiyadan yoki hisob ma'lumotlaridan foydalanib kirish."""
        session_path = Path(INSTAGRAM_SESSION_FILE)
        try:
            if session_path.exists():
                self.cl.load_settings(str(session_path))
                self.cl.login(INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD)
                logger.info("✅ Instagram sessiyadan tiklandi")
            else:
                self._fresh_login()
        except (LoginRequired, Exception) as exc:
            logger.warning("Sessiya eskirgan, qayta login: %s", exc)
            self._fresh_login()

    def _fresh_login(self):
        self.cl.login(INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD)
        self.cl.dump_settings(INSTAGRAM_SESSION_FILE)
        logger.info("✅ Instagram ga yangi login, sessiya saqlandi")

    def _relogin_if_needed(self):
        """Har 6 soatda sessiyani yangilash."""
        try:
            self.cl.get_timeline_feed()
        except LoginRequired:
            logger.warning("⚠️  Sessiya muddati tugadi, qayta login...")
            self._fresh_login()

    # ── DM polling ────────────────────────────────────────────────────────

    def set_telegram_callback(self, callback):
        """Telegram ga video yuborish uchun callback o'rnatish."""
        self._tg_send_callback = callback

    def poll_loop(self):
        """Asosiy polling sikli — alohida threadda ishga tushiriladi."""
        logger.info("📡 Instagram polling boshlandi (interval: %ss)", INSTAGRAM_POLL_INTERVAL)
        relogin_counter = 0

        while not _stop_event.is_set():
            try:
                # Har 360 sikl (~6 soat) da sessiyani tekshirish
                relogin_counter += 1
                if relogin_counter >= 360:
                    self._relogin_if_needed()
                    relogin_counter = 0

                self._check_pending_links()
                self._check_new_videos()

            except ClientError as exc:
                logger.error("Instagram ClientError: %s — 60s kutilmoqda", exc)
                time.sleep(60)
            except Exception as exc:
                logger.exception("Kutilmagan xato polling da: %s", exc)
                time.sleep(30)

            _stop_event.wait(timeout=INSTAGRAM_POLL_INTERVAL)

        logger.info("🛑 Instagram polling to'xtatildi")

    # ── Akkaunt bog'lash ───────────────────────────────────────────────────

    def _check_pending_links(self):
        """
        Kiruvchi DM lardagi raqamlarni tekshirish.
        Agar xabar faqat son bo'lsa — Telegram ID deb qabul qiladi va bog'laydi.
        """
        try:
            threads = self.cl.direct_threads(amount=20)
        except Exception as exc:
            logger.warning("direct_threads xatosi: %s", exc)
            return

        for thread in threads:
            for msg in thread.messages:
                msg_id = str(msg.id)

                # Faqat matnli xabarlarni tekshiramiz
                if msg.item_type != "text":
                    continue

                # Agar bu matnli xabar allaqachon tekshirilgan bo'lsa, o'tib ketamiz
                if msg_id in self._processed_text_ids:
                    continue
                self._processed_text_ids.add(msg_id)

                text = (msg.text or "").strip()
                if not text.isdigit():
                    continue

                telegram_id = int(text)
                sender_id   = str(thread.users[0].pk) if thread.users else None
                sender_name = thread.users[0].username if thread.users else "unknown"

                if not sender_id:
                    continue

                # Foydalanuvchi mavjudmi?
                user = db.get_user_by_telegram_id(telegram_id)
                if not user:
                    logger.info("⚠️  Telegram ID %s topilmadi, xabar e'tiborga olinmadi", telegram_id)
                    self._reply_dm(thread.id, "❌ Ushbu Telegram ID topilmadi. Avval /start bosing.")
                    continue

                # Allaqachon bog'langanmi?
                if user["instagram_user_id"]:
                    self._reply_dm(thread.id, "✅ Siz allaqachon bog'langansiz!")
                    continue

                # Bog'lash
                success = db.link_instagram(telegram_id, sender_id, sender_name)
                if success:
                    logger.info("🔗 Bog'landi: TG=%s ↔ IG=%s", telegram_id, sender_name)
                    self._reply_dm(thread.id,
                        f"✅ Muvaffaqiyatli bog'landi!\n"
                        f"Endi videolaringiz Telegram ga avtomatik yuboriladi. 🚀")
                    
                    # Telegram ga ham xabar berish
                    if self._tg_send_callback:
                        self._tg_send_callback(
                            telegram_id,
                            f"🎉 Instagram akkauntingiz (@{sender_name}) muvaffaqiyatli bog'landi!\n"
                            f"Endi Instagram DM ga video yuborsangiz, bu yerga avtomatik keladi."
                        )

    # ── Video kuzatish ─────────────────────────────────────────────────────

    def _check_new_videos(self):
        """Bog'langan foydalanuvchilarning DM videolarini tekshirish."""
        linked_users = db.get_all_linked_users()
        if not linked_users:
            logger.debug("Bog'langan foydalanuvchi topilmadi")
            return

        try:
            threads = self.cl.direct_threads(amount=20)
            for thread in threads:
                thread_user_ids = [str(u.pk) for u in thread.users]
                
                # Chatdagi odamlar orasida biz bazaga bog'lagan foydalanuvchi bormi?
                current_user = None
                for user in linked_users:
                    if user["instagram_user_id"] in thread_user_ids:
                        current_user = user
                        break
                
                if not current_user:
                    continue

                telegram_id = current_user["telegram_id"]
                ig_user_id = current_user["instagram_user_id"]

                for msg in thread.messages:
                    msg_id = str(msg.id)

                    # Agar bu video fayl oldin qayta ishlangan bo'lsa, o'tib ketamiz
                    if msg_id in self._processed_video_ids:
                        continue

                    logger.info("📨 Xabar tekshirilmoqda: item_type=%s, id=%s", msg.item_type, msg_id)
                    
                    media_types = []
                    if hasattr(msg, 'media') and msg.media:
                        media_types.append("media")
                    if hasattr(msg, 'clip') and msg.clip:
                        media_types.append("clip")
                    if hasattr(msg, 'reel_share') and msg.reel_share:
                        media_types.append("reel_share")
                    if hasattr(msg, 'visual_media') and msg.visual_media:
                        media_types.append("visual_media")
                    if hasattr(msg, 'xma_share') and msg.xma_share:
                        media_types.append("xma_share")
                    if hasattr(msg, 'video_call_event') and msg.video_call_event:
                        media_types.append("video_call_event")

                    if media_types:
                        logger.info("🎬 Media topildi: %s", ", ".join(media_types))
                        self._processed_video_ids.add(msg_id)
                        self._handle_video_message(msg, telegram_id, ig_user_id)
                    else:
                        logger.debug("⏭️  Tekshirildi (media yo'q): item_type=%s", msg.item_type)

        except Exception as exc:
            logger.error("Video tekshirishda umumiy xato: %s", exc)

    def _handle_video_message(self, msg, telegram_id: int, ig_user_id: str):
        """Videoni yuklab olib Telegram ga yuborish."""
        media_url = self._extract_video_url(msg)
        if not media_url:
            logger.warning("❌ Video URL topilmadi yoki bu video fayl emas: msg_id=%s", msg.id)
            return

        log_id = db.log_video(telegram_id, str(msg.id), media_url)
        logger.info("📝 Video loglandi: log_id=%s, telegram_id=%s", log_id, telegram_id)

        try:
            logger.info("⬇️  Video yuklash boshlandi: %s", media_url[:80])
            local_path = self._download_video(media_url, str(msg.id))
            logger.info("✅ Video yuklandi: %s", local_path)
            
            db.update_video_log(log_id, "pending", None)

            if self._tg_send_callback:
                logger.info("📤 Telegram bot orqali chatga yuborilmoqda... TG=%s", telegram_id)
                self._tg_send_callback(telegram_id, None, video_path=local_path)
                db.update_video_log(log_id, "sent")
                logger.info("✅ Video Telegramga yuborildi: TG=%s, fayl=%s", telegram_id, local_path)
            else:
                logger.error("❌ Telegram callback o'rnatilmagan!")
                db.update_video_log(log_id, "failed", "Telegram callback missing")

        except FileNotFoundError as exc:
            logger.error("❌ Video fayl topilmadi: %s", local_path)
            db.update_video_log(log_id, "failed", f"File not found: {local_path}")
        except Exception as exc:
            logger.error("❌ Video yuborishda xato: %s", exc)
            db.update_video_log(log_id, "failed", str(exc))

    def _extract_video_url(self, msg) -> str | None:
        """Turli media turlaridan video URL ni olish."""
        try:
            # Reel share (Reels forward)
            if hasattr(msg, 'reel_share') and msg.reel_share:
                rs = msg.reel_share
                if hasattr(rs, 'media') and rs.media:
                    logger.info("📹 Reel share media topildi")
                    return self._extract_video_from_media(rs.media)

            # Clip (Direct Reels)
            if hasattr(msg, 'clip') and msg.clip:
                logger.info("📹 Clip topildi")
                if hasattr(msg.clip, 'video_url') and msg.clip.video_url:
                    return self._resolve_instagram_link(str(msg.clip.video_url))
                if hasattr(msg.clip, 'video_versions') and msg.clip.video_versions:
                    return str(msg.clip.video_versions[0].url)

            # XMA share (shared clip/reel link)
            if hasattr(msg, 'xma_share') and msg.xma_share:
                xma = msg.xma_share
                if hasattr(xma, 'video_url') and xma.video_url:
                    logger.info("📹 XMA share topildi")
                    return self._resolve_instagram_link(str(xma.video_url))

            # Visual media
            if hasattr(msg, 'visual_media') and msg.visual_media:
                logger.info("📹 Visual media topildi")
                return self._extract_video_from_media(msg.visual_media)

            # Regular media
            if hasattr(msg, 'media') and msg.media:
                logger.info("📹 Media topildi")
                return self._extract_video_from_media(msg.media)

            logger.warning("❌ Video URL topilmadi: msg_id=%s, item_type=%s", 
                         msg.id, msg.item_type)
        except Exception as exc:
            logger.error("URL ajratishda xato: %s", exc)
        return None

    def _extract_video_from_media(self, media) -> str | None:
        """Media objektidan video URL ni olish."""
        try:
            # Video versions
            if hasattr(media, 'video_versions') and media.video_versions and len(media.video_versions) > 0:
                logger.debug("✅ Video versions topildi")
                return str(media.video_versions[0].url)
            
            # Video URL
            if hasattr(media, 'video_url') and media.video_url:
                logger.debug("✅ Video URL topildi")
                return str(media.video_url)
            
            # Carousel media with videos
            if hasattr(media, 'carousel_media') and media.carousel_media:
                for item in media.carousel_media:
                    if hasattr(item, 'video_versions') and item.video_versions:
                        logger.debug("✅ Carousel video versions topildi")
                        return str(item.video_versions[0].url)
                    if hasattr(item, 'video_url') and item.video_url:
                        logger.debug("✅ Carousel video URL topildi")
                        return str(item.video_url)
            
            logger.debug("❌ Media da video topilmadi")
        except Exception as exc:
            logger.error("Media dan URL ajratishda xato: %s", exc)
        return None

    def _resolve_instagram_link(self, url: str) -> str | None:
        """Agar link Instagram sahifasiga bo'lsa, uni to'g'ridan-to'g'ri media URL ga aylantirish."""
        try:
            if "instagram.com" in url:
                media_pk = self.cl.media_pk_from_url(url)
                media = self.cl.media_info(media_pk)
                return self._extract_video_from_media(media)
        except Exception as exc:
            logger.warning("Instagram linkni media URL ga aylantirishda xato: %s", exc)
        return url

    def _download_video(self, url: str, filename: str) -> str:
        """Videoni lokal faylga yuklab olish."""
        safe_name = "".join(c for c in filename if c.isalnum() or c in "-_")
        path = os.path.join(DOWNLOAD_DIR, f"{safe_name}.mp4")

        headers = {"User-Agent": "Instagram 219.0.0.12.117 Android"}
        resp = requests.get(url, headers=headers, timeout=60, stream=True)
        resp.raise_for_status()

        with open(path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)

        logger.info("⬇️  Video yuklandi: %s (%.1f KB)", path, os.path.getsize(path) / 1024)
        return path

    def _reply_dm(self, thread_id: str, text: str):
        """DM ga xabar yuborish (xatolarni tutib qolish bilan)."""
        try:
            self.cl.direct_send(text, thread_ids=[thread_id])
        except Exception as exc:
            logger.warning("DM javob yuborishda xato: %s", exc)


def stop_polling():
    """Tashqaridan polling ni to'xtatish."""
    _stop_event.set()