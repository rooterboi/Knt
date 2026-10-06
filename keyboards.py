from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import BOT_USERNAME


# ===================== FOYDALANUVCHI MENYUSI =====================
def main_menu_kb(is_admin: bool = False) -> ReplyKeyboardMarkup:
    rows = [
        [KeyboardButton(text="🔎 Kod orqali qidirish")],
        [KeyboardButton(text="💎 Premium sotib olish"), KeyboardButton(text="👤 Mening balansim")],
        [KeyboardButton(text="🎁 Promokod"), KeyboardButton(text="🤝 Do'st taklif qilish")],
    ]
    if is_admin:
        rows.append([KeyboardButton(text="⚙️ Admin panel")])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def subscribe_check_kb(channels) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for ch in channels:
        username = ch["channel_id"]
        link = f"https://t.me/{username.lstrip('@')}" if not username.startswith("-") else None
        if link:
            kb.row(InlineKeyboardButton(text=f"📢 {ch['title'] or username}", url=link))
    kb.row(InlineKeyboardButton(text="✅ Obunani tekshirish", callback_data="check_sub"))
    return kb.as_markup()


def premium_required_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="💎 Premium sotib olish", callback_data="buy_premium"))
    kb.row(InlineKeyboardButton(text="🤝 Referal orqali pul yig'ish", callback_data="show_referral"))
    kb.row(InlineKeyboardButton(text="🎁 Promokod kiritish", callback_data="enter_promo"))
    return kb.as_markup()


def premium_plans_kb(price_1m, price_3m, price_life) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text=f"1 oy — {price_1m} so'm", callback_data="plan_1m"))
    kb.row(InlineKeyboardButton(text=f"3 oy — {price_3m} so'm", callback_data="plan_3m"))
    kb.row(InlineKeyboardButton(text=f"Umrbod — {price_life} so'm", callback_data="plan_lifetime"))
    return kb.as_markup()


def seasons_kb(code: str, seasons: list) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for s in seasons:
        kb.button(text=f"{s}-fasl", callback_data=f"season_{code}_{s}")
    kb.adjust(3)
    return kb.as_markup()


def episodes_kb(code: str, season: int, episodes: list) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for ep in episodes:
        kb.button(text=f"{ep['episode']}-qism", callback_data=f"ep_{code}_{season}_{ep['episode']}")
    kb.adjust(4)
    kb.row(InlineKeyboardButton(text="⬅️ Fasllarga qaytish", callback_data=f"backseasons_{code}"))
    return kb.as_markup()


def referral_link(user_id: int) -> str:
    return f"https://t.me/{BOT_USERNAME}?start=ref{user_id}"


# ===================== ADMIN MENYUSI =====================
def admin_main_kb(is_owner: bool) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="🎬 Kino qo'shish", callback_data="adm_add_movie"),
           InlineKeyboardButton(text="📺 Serial qismi qo'shish", callback_data="adm_add_episode"))
    kb.row(InlineKeyboardButton(text="🗑 Kino o'chirish", callback_data="adm_del_movie"))
    kb.row(InlineKeyboardButton(text="🎟 Promokodlar", callback_data="adm_promo_menu"))
    kb.row(InlineKeyboardButton(text="👥 Foydalanuvchini boshqarish", callback_data="adm_user_menu"))
    kb.row(InlineKeyboardButton(text="📢 Xabar yuborish (Broadcast)", callback_data="adm_broadcast"))
    kb.row(InlineKeyboardButton(text="📡 Majburiy obuna kanallari", callback_data="adm_channels"))
    kb.row(InlineKeyboardButton(text="📮 Avto-post kanali", callback_data="adm_post_channel"))
    kb.row(InlineKeyboardButton(text="💰 Narx va referal sozlamalari", callback_data="adm_pricing"))
    kb.row(InlineKeyboardButton(text="📊 Statistika", callback_data="adm_stats"))
    toggles = InlineKeyboardButton(text="🔀 Tizimlarni yoqish/o'chirish", callback_data="adm_toggles")
    kb.row(toggles)
    if is_owner:
        kb.row(InlineKeyboardButton(text="👑 Adminlarni boshqarish", callback_data="adm_admins_menu"))
    return kb.as_markup()


def back_to_admin_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="⬅️ Admin panelga qaytish", callback_data="adm_back"))
    return kb.as_markup()


def access_level_kb(prefix: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="🌍 Barchaga", callback_data=f"{prefix}_all"),
        InlineKeyboardButton(text="🆓 Faqat Oddiy", callback_data=f"{prefix}_free"),
        InlineKeyboardButton(text="💎 Faqat Premium", callback_data=f"{prefix}_premium"),
    )
    return kb.as_markup()


def admins_menu_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="➕ Yangi admin qo'shish", callback_data="adm_add_admin"))
    kb.row(InlineKeyboardButton(text="➖ Adminni olib tashlash", callback_data="adm_remove_admin"))
    kb.row(InlineKeyboardButton(text="📋 Adminlar ro'yxati", callback_data="adm_list_admins"))
    kb.row(InlineKeyboardButton(text="⬅️ Orqaga", callback_data="adm_back"))
    return kb.as_markup()


def toggles_kb(premium_on: bool, promo_on: bool) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    p_text = "💎 Premium tizimi: ✅ YOQILGAN" if premium_on else "💎 Premium tizimi: ❌ O'CHIRILGAN"
    pr_text = "🎟 Promokod tizimi: ✅ YOQILGAN" if promo_on else "🎟 Promokod tizimi: ❌ O'CHIRILGAN"
    kb.row(InlineKeyboardButton(text=p_text, callback_data="toggle_premium"))
    kb.row(InlineKeyboardButton(text=pr_text, callback_data="toggle_promo"))
    kb.row(InlineKeyboardButton(text="⬅️ Orqaga", callback_data="adm_back"))
    return kb.as_markup()


def promo_menu_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="➕ Yangi promokod yaratish", callback_data="adm_create_promo"))
    kb.row(InlineKeyboardButton(text="⬅️ Orqaga", callback_data="adm_back"))
    return kb.as_markup()


def user_menu_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="💎 Premium berish", callback_data="adm_give_premium"))
    kb.row(InlineKeyboardButton(text="🚫 Premiumni bekor qilish", callback_data="adm_revoke_premium"))
    kb.row(InlineKeyboardButton(text="💰 Balansni to'ldirish/nolga tushirish", callback_data="adm_set_balance"))
    kb.row(InlineKeyboardButton(text="⬅️ Orqaga", callback_data="adm_back"))
    return kb.as_markup()


def confirm_kb(yes_cb: str, no_cb: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="✅ Ha", callback_data=yes_cb),
           InlineKeyboardButton(text="❌ Yo'q", callback_data=no_cb))
    return kb.as_markup()
