# database.py - SQLite ma'lumotlar bazasi boshqaruvi

import sqlite3
import logging
from datetime import datetime
from config import DB_PATH

logger = logging.getLogger(__name__)


def get_connection() -> sqlite3.Connection:
    """Thread-safe SQLite ulanish."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Jadvallarni yaratish (agar mavjud bo'lmasa)."""
    with get_connection() as conn:
        conn.executescript("""
            -- Foydalanuvchilar jadvali
            CREATE TABLE IF NOT EXISTS users (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id      INTEGER UNIQUE NOT NULL,
                telegram_username TEXT,
                instagram_user_id TEXT UNIQUE,
                instagram_username TEXT,
                linked_at        DATETIME,
                created_at       DATETIME DEFAULT CURRENT_TIMESTAMP,
                is_active        INTEGER  DEFAULT 1
            );

            -- Yuborilgan videolar tarixi
            CREATE TABLE IF NOT EXISTS video_logs (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id      INTEGER NOT NULL,
                instagram_media_id TEXT,
                media_url        TEXT,
                local_path       TEXT,
                status           TEXT DEFAULT 'pending',   -- pending | sent | failed
                error_message    TEXT,
                created_at       DATETIME DEFAULT CURRENT_TIMESTAMP,
                sent_at          DATETIME
            );

            -- Bot statistikasi (har kuni bir qator)
            CREATE TABLE IF NOT EXISTS bot_stats (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                date             DATE UNIQUE DEFAULT (DATE('now')),
                total_users      INTEGER DEFAULT 0,
                linked_users     INTEGER DEFAULT 0,
                videos_sent      INTEGER DEFAULT 0,
                videos_failed    INTEGER DEFAULT 0,
                updated_at       DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            -- Indekslar
            CREATE INDEX IF NOT EXISTS idx_users_telegram_id   ON users(telegram_id);
            CREATE INDEX IF NOT EXISTS idx_users_ig_user_id    ON users(instagram_user_id);
            CREATE INDEX IF NOT EXISTS idx_video_logs_tg_id    ON video_logs(telegram_id);
        """)
    logger.info("✅ Ma'lumotlar bazasi tayyor: %s", DB_PATH)


# ── CRUD operatsiyalari ────────────────────────────────────────────────────────

def upsert_telegram_user(telegram_id: int, telegram_username: str | None):
    """Telegram foydalanuvchini qo'shish yoki yangilash."""
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO users (telegram_id, telegram_username)
            VALUES (?, ?)
            ON CONFLICT(telegram_id) DO UPDATE SET
                telegram_username = excluded.telegram_username
        """, (telegram_id, telegram_username))
    _refresh_stats()


def link_instagram(telegram_id: int, ig_user_id: str, ig_username: str) -> bool:
    """Instagram akkauntini Telegram ID ga bog'lash."""
    try:
        with get_connection() as conn:
            conn.execute("""
                UPDATE users
                SET instagram_user_id = ?,
                    instagram_username = ?,
                    linked_at = ?
                WHERE telegram_id = ?
            """, (ig_user_id, ig_username, datetime.utcnow().isoformat(), telegram_id))
        _refresh_stats()
        return True
    except Exception as exc:
        logger.error("link_instagram xatosi: %s", exc)
        return False


def get_user_by_telegram_id(telegram_id: int) -> sqlite3.Row | None:
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
        ).fetchone()


def get_user_by_ig_user_id(ig_user_id: str) -> sqlite3.Row | None:
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM users WHERE instagram_user_id = ?", (ig_user_id,)
        ).fetchone()


def get_all_linked_users() -> list[sqlite3.Row]:
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM users WHERE instagram_user_id IS NOT NULL AND is_active = 1"
        ).fetchall()


def log_video(telegram_id: int, ig_media_id: str, media_url: str,
              local_path: str = None) -> int:
    """Yangi video yozuv qo'shish, ID qaytarish."""
    with get_connection() as conn:
        cursor = conn.execute("""
            INSERT INTO video_logs (telegram_id, instagram_media_id, media_url, local_path)
            VALUES (?, ?, ?, ?)
        """, (telegram_id, ig_media_id, media_url, local_path))
        return cursor.lastrowid


def update_video_log(log_id: int, status: str, error: str = None):
    sent_at = datetime.utcnow().isoformat() if status == "sent" else None
    with get_connection() as conn:
        conn.execute("""
            UPDATE video_logs
            SET status = ?, error_message = ?, sent_at = ?
            WHERE id = ?
        """, (status, error, sent_at, log_id))
    _refresh_stats()


def get_dashboard_data() -> dict:
    """Dashboard uchun umumiy statistika."""
    with get_connection() as conn:
        users     = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        linked    = conn.execute(
            "SELECT COUNT(*) FROM users WHERE instagram_user_id IS NOT NULL"
        ).fetchone()[0]
        sent      = conn.execute(
            "SELECT COUNT(*) FROM video_logs WHERE status = 'sent'"
        ).fetchone()[0]
        failed    = conn.execute(
            "SELECT COUNT(*) FROM video_logs WHERE status = 'failed'"
        ).fetchone()[0]
        recent    = conn.execute("""
            SELECT u.telegram_username, u.instagram_username,
                   u.linked_at, u.created_at
            FROM users u ORDER BY u.created_at DESC LIMIT 10
        """).fetchall()
        recent_videos = conn.execute("""
            SELECT vl.*, u.telegram_username, u.instagram_username
            FROM video_logs vl
            LEFT JOIN users u ON u.telegram_id = vl.telegram_id
            ORDER BY vl.created_at DESC LIMIT 20
        """).fetchall()

    return {
        "total_users":   users,
        "linked_users":  linked,
        "videos_sent":   sent,
        "videos_failed": failed,
        "recent_users":  [dict(r) for r in recent],
        "recent_videos": [dict(r) for r in recent_videos],
    }


def _refresh_stats():
    """Kunlik statistikani yangilash."""
    with get_connection() as conn:
        users  = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        linked = conn.execute(
            "SELECT COUNT(*) FROM users WHERE instagram_user_id IS NOT NULL"
        ).fetchone()[0]
        sent   = conn.execute(
            "SELECT COUNT(*) FROM video_logs WHERE status='sent' AND DATE(created_at)=DATE('now')"
        ).fetchone()[0]
        failed = conn.execute(
            "SELECT COUNT(*) FROM video_logs WHERE status='failed' AND DATE(created_at)=DATE('now')"
        ).fetchone()[0]
        conn.execute("""
            INSERT INTO bot_stats (date, total_users, linked_users, videos_sent, videos_failed)
            VALUES (DATE('now'), ?, ?, ?, ?)
            ON CONFLICT(date) DO UPDATE SET
                total_users = excluded.total_users,
                linked_users = excluded.linked_users,
                videos_sent = excluded.videos_sent,
                videos_failed = excluded.videos_failed,
                updated_at = CURRENT_TIMESTAMP
        """, (users, linked, sent, failed))
