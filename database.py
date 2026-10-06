"""
database.py
SQLite bilan ishlovchi barcha funksiyalar shu yerda.
Har bir funksiya o'z connection'ini ochib-yopadi (thread-safe, yuqori yuklamaga chidamli).
"""

import sqlite3
import time
import logging
from contextlib import contextmanager

from config import DB_PATH, DEFAULT_SETTINGS, OWNER_ID

logger = logging.getLogger(__name__)


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")   # bir vaqtda ko'p o'qish/yozish uchun
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Botni ishga tushirishda barcha jadvallarni yaratadi."""
    with get_conn() as conn:
        cur = conn.cursor()

        cur.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            user_id INTEGER PRIMARY KEY,
            role TEXT NOT NULL CHECK(role IN ('owner', 'admin')),
            added_at INTEGER NOT NULL
        )""")

        cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            balance INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'free' CHECK(status IN ('free', 'premium')),
            premium_expires_at INTEGER,
            referrer_id INTEGER,
            referral_count INTEGER NOT NULL DEFAULT 0,
            is_banned INTEGER NOT NULL DEFAULT 0,
            created_at INTEGER NOT NULL
        )""")

        cur.execute("""
        CREATE TABLE IF NOT EXISTS movies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            title TEXT NOT NULL,
            file_id TEXT NOT NULL,
            poster_id TEXT,
            access_level TEXT NOT NULL DEFAULT 'all' CHECK(access_level IN ('all','free','premium')),
            description TEXT,
            views INTEGER NOT NULL DEFAULT 0,
            is_series INTEGER NOT NULL DEFAULT 0,
            created_at INTEGER NOT NULL
        )""")

        cur.execute("""
        CREATE TABLE IF NOT EXISTS series (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL,
            title TEXT NOT NULL,
            season INTEGER NOT NULL,
            episode INTEGER NOT NULL,
            file_id TEXT NOT NULL,
            access_level TEXT NOT NULL DEFAULT 'all' CHECK(access_level IN ('all','free','premium')),
            created_at INTEGER NOT NULL,
            UNIQUE(code, season, episode)
        )""")

        cur.execute("""
        CREATE TABLE IF NOT EXISTS promocodes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            reward_amount INTEGER NOT NULL,
            max_uses INTEGER NOT NULL,
            current_uses INTEGER NOT NULL DEFAULT 0,
            created_at INTEGER NOT NULL
        )""")

        cur.execute("""
        CREATE TABLE IF NOT EXISTS promo_usage (
            user_id INTEGER NOT NULL,
            promo_id INTEGER NOT NULL,
            used_at INTEGER NOT NULL,
            PRIMARY KEY (user_id, promo_id)
        )""")

        cur.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )""")

        cur.execute("""
        CREATE TABLE IF NOT EXISTS channels (
            channel_id TEXT PRIMARY KEY,
            title TEXT,
            added_at INTEGER NOT NULL
        )""")

        # Standart sozlamalarni kiritish (agar mavjud bo'lmasa)
        for key, value in DEFAULT_SETTINGS.items():
            cur.execute(
                "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
                (key, value),
            )

        # Owner'ni adminlar jadvaliga qo'shish
        cur.execute(
            "INSERT OR IGNORE INTO admins (user_id, role, added_at) VALUES (?, 'owner', ?)",
            (OWNER_ID, int(time.time())),
        )

    logger.info("Baza tayyor: %s", DB_PATH)


# ---------------------------------------------------------------- SETTINGS
def get_setting(key: str, default: str = "") -> str:
    with get_conn() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return row["value"] if row else default


def set_setting(key: str, value: str):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, str(value)),
        )


def is_premium_system_enabled() -> bool:
    return get_setting("premium_enabled", "1") == "1"


def is_promo_system_enabled() -> bool:
    return get_setting("promo_enabled", "1") == "1"


# ---------------------------------------------------------------- ADMINS
def is_owner(user_id: int) -> bool:
    return user_id == OWNER_ID


def is_admin(user_id: int) -> bool:
    with get_conn() as conn:
        row = conn.execute("SELECT 1 FROM admins WHERE user_id=?", (user_id,)).fetchone()
        return row is not None


def add_admin(user_id: int) -> bool:
    with get_conn() as conn:
        exists = conn.execute("SELECT 1 FROM admins WHERE user_id=?", (user_id,)).fetchone()
        if exists:
            return False
        conn.execute(
            "INSERT INTO admins (user_id, role, added_at) VALUES (?, 'admin', ?)",
            (user_id, int(time.time())),
        )
        return True


def remove_admin(user_id: int) -> bool:
    with get_conn() as conn:
        row = conn.execute("SELECT role FROM admins WHERE user_id=?", (user_id,)).fetchone()
        if not row or row["role"] == "owner":
            return False  # owner'ni o'chirib bo'lmaydi
        conn.execute("DELETE FROM admins WHERE user_id=?", (user_id,))
        return True


def list_admins():
    with get_conn() as conn:
        return conn.execute("SELECT user_id, role, added_at FROM admins ORDER BY added_at").fetchall()


# ---------------------------------------------------------------- USERS
def get_user(user_id: int):
    with get_conn() as conn:
        return conn.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()


def create_user_if_not_exists(user_id: int, username: str, full_name: str, referrer_id: int = None):
    with get_conn() as conn:
        exists = conn.execute("SELECT 1 FROM users WHERE user_id=?", (user_id,)).fetchone()
        if exists:
            return False
        # referrer o'zini o'ziga taklif qila olmaydi, va referrer botda ro'yxatdan o'tgan bo'lishi kerak
        valid_referrer = None
        if referrer_id and referrer_id != user_id:
            ref_exists = conn.execute("SELECT 1 FROM users WHERE user_id=?", (referrer_id,)).fetchone()
            if ref_exists:
                valid_referrer = referrer_id

        conn.execute(
            "INSERT INTO users (user_id, username, full_name, balance, status, referrer_id, created_at) "
            "VALUES (?, ?, ?, 0, 'free', ?, ?)",
            (user_id, username, full_name, valid_referrer, int(time.time())),
        )

        if valid_referrer:
            bonus = int(get_setting("referral_bonus", "500"))
            conn.execute(
                "UPDATE users SET balance = balance + ?, referral_count = referral_count + 1 WHERE user_id=?",
                (bonus, valid_referrer),
            )
        return True


def update_balance(user_id: int, amount: int):
    """amount musbat yoki manfiy bo'lishi mumkin"""
    with get_conn() as conn:
        conn.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (amount, user_id))


def set_balance(user_id: int, amount: int):
    with get_conn() as conn:
        conn.execute("UPDATE users SET balance = ? WHERE user_id=?", (amount, user_id))


def grant_premium(user_id: int, seconds: int = None):
    """seconds=None -> umrbod premium"""
    expires = None if seconds is None else int(time.time()) + seconds
    with get_conn() as conn:
        conn.execute(
            "UPDATE users SET status='premium', premium_expires_at=? WHERE user_id=?",
            (expires, user_id),
        )


def revoke_premium(user_id: int):
    with get_conn() as conn:
        conn.execute(
            "UPDATE users SET status='free', premium_expires_at=NULL WHERE user_id=?",
            (user_id,),
        )


def check_and_expire_premium(user_id: int):
    """Muddati tugagan premiumni avtomatik 'free'ga qaytaradi."""
    user = get_user(user_id)
    if user and user["status"] == "premium" and user["premium_expires_at"]:
        if user["premium_expires_at"] < int(time.time()):
            revoke_premium(user_id)
            return True
    return False


def has_access(user, access_level: str) -> bool:
    """Foydalanuvchi berilgan access_level'dagi kontentni ko'ra oladimi."""
    if not is_premium_system_enabled():
        return True
    if access_level in ("all", "free"):
        return True
    if access_level == "premium":
        return user is not None and user["status"] == "premium"
    return False


def all_user_ids():
    with get_conn() as conn:
        rows = conn.execute("SELECT user_id FROM users WHERE is_banned=0").fetchall()
        return [r["user_id"] for r in rows]


def user_stats():
    with get_conn() as conn:
        total = conn.execute("SELECT COUNT(*) c FROM users").fetchone()["c"]
        premium = conn.execute("SELECT COUNT(*) c FROM users WHERE status='premium'").fetchone()["c"]
        today_start = int(time.time()) - 86400
        new_today = conn.execute(
            "SELECT COUNT(*) c FROM users WHERE created_at >= ?", (today_start,)
        ).fetchone()["c"]
        movies_count = conn.execute("SELECT COUNT(*) c FROM movies").fetchone()["c"]
        return {
            "total": total,
            "premium": premium,
            "new_today": new_today,
            "movies": movies_count,
        }


# ---------------------------------------------------------------- MOVIES
def add_movie(code, title, file_id, poster_id, access_level, description, is_series=0):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO movies (code, title, file_id, poster_id, access_level, description, is_series, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (code, title, file_id, poster_id, access_level, description, is_series, int(time.time())),
        )


def get_movie_by_code(code: str):
    with get_conn() as conn:
        return conn.execute("SELECT * FROM movies WHERE code=?", (code,)).fetchone()


def increment_movie_views(code: str):
    with get_conn() as conn:
        conn.execute("UPDATE movies SET views = views + 1 WHERE code=?", (code,))


def delete_movie(code: str) -> bool:
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM movies WHERE code=?", (code,))
        return cur.rowcount > 0


# ---------------------------------------------------------------- SERIES
def add_episode(code, title, season, episode, file_id, access_level):
    with get_conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO series (code, title, season, episode, file_id, access_level, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (code, title, season, episode, file_id, access_level, int(time.time())),
        )


def get_series_by_code(code: str):
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM series WHERE code=? ORDER BY season, episode", (code,)
        ).fetchall()


def get_episode(code: str, season: int, episode: int):
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM series WHERE code=? AND season=? AND episode=?",
            (code, season, episode),
        ).fetchone()


def get_seasons(code: str):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT DISTINCT season FROM series WHERE code=? ORDER BY season", (code,)
        ).fetchall()
        return [r["season"] for r in rows]


def get_episodes_of_season(code: str, season: int):
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM series WHERE code=? AND season=? ORDER BY episode",
            (code, season),
        ).fetchall()


# ---------------------------------------------------------------- PROMOCODES
def create_promocode(code: str, reward_amount: int, max_uses: int) -> bool:
    with get_conn() as conn:
        exists = conn.execute("SELECT 1 FROM promocodes WHERE code=?", (code,)).fetchone()
        if exists:
            return False
        conn.execute(
            "INSERT INTO promocodes (code, reward_amount, max_uses, created_at) VALUES (?, ?, ?, ?)",
            (code, reward_amount, max_uses, int(time.time())),
        )
        return True


def redeem_promocode(user_id: int, code: str):
    """Qaytaradi: (muvaffaqiyat: bool, xabar: str, bonus: int)"""
    with get_conn() as conn:
        promo = conn.execute("SELECT * FROM promocodes WHERE code=?", (code,)).fetchone()
        if not promo:
            return False, "❌ Bunday promokod topilmadi.", 0
        if promo["current_uses"] >= promo["max_uses"]:
            return False, "❌ Bu promokodning foydalanish limiti tugagan.", 0
        used = conn.execute(
            "SELECT 1 FROM promo_usage WHERE user_id=? AND promo_id=?",
            (user_id, promo["id"]),
        ).fetchone()
        if used:
            return False, "❌ Siz bu promokoddan allaqachon foydalangansiz.", 0

        conn.execute(
            "INSERT INTO promo_usage (user_id, promo_id, used_at) VALUES (?, ?, ?)",
            (user_id, promo["id"], int(time.time())),
        )
        conn.execute("UPDATE promocodes SET current_uses = current_uses + 1 WHERE id=?", (promo["id"],))
        conn.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (promo["reward_amount"], user_id))
        return True, f"✅ Promokod qabul qilindi! Balansingizga {promo['reward_amount']} so'm qo'shildi.", promo["reward_amount"]


# ---------------------------------------------------------------- CHANNELS (majburiy obuna)
def add_channel(channel_id: str, title: str = ""):
    with get_conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO channels (channel_id, title, added_at) VALUES (?, ?, ?)",
            (channel_id, title, int(time.time())),
        )


def remove_channel(channel_id: str) -> bool:
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM channels WHERE channel_id=?", (channel_id,))
        return cur.rowcount > 0


def list_channels():
    with get_conn() as conn:
        return conn.execute("SELECT * FROM channels").fetchall()
