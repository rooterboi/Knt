import os

# === ASOSIY SOZLAMALAR ===
# Bot tokenini @BotFather dan oling va shu yerga yoki environment variable orqali kiriting
BOT_TOKEN = os.getenv("BOT_TOKEN", "BOT_TOKEN_SHU_YERGA")

# Bosh admin (Owner) Telegram user_id. Faqat shu odam adminlarni boshqara oladi.
OWNER_ID = int(os.getenv("OWNER_ID", "123456789"))

# SQLite baza fayli nomi
DB_PATH = os.getenv("DB_PATH", "cinema_bot.db")

# Bot username (referal havola yasash uchun, @ belgisiz)
BOT_USERNAME = os.getenv("BOT_USERNAME", "sizning_bot_username")

# Standart (default) sozlamalar - agar settings jadvalida bo'lmasa shular ishlatiladi
DEFAULT_SETTINGS = {
    "premium_enabled": "1",       # "1" - premium tizimi yoqilgan, "0" - o'chirilgan (hammaga tekin)
    "promo_enabled": "1",         # "1" - promokod tizimi yoqilgan, "0" - o'chirilgan
    "referral_bonus": "500",      # bitta taklif qilingan do'st uchun so'mda bonus
    "post_channel_id": "",        # avto-post qilinadigan kanal (masalan: -1001234567890)
    "price_1m": "15000",          # 1 oylik premium narxi (so'm)
    "price_3m": "35000",          # 3 oylik premium narxi (so'm)
    "price_lifetime": "99000",    # umrbod premium narxi (so'm)
}

# To'lov uchun ko'rsatiladigan karta/ma'lumot (xohishga ko'ra o'zgartiring)
PAYMENT_INFO = (
    "💳 To'lov uchun karta: 8600 1234 5678 9012\n"
    "Egasi: XXXX XXXX\n\n"
    "To'lovdan so'ng chekni @admin_username ga yuboring."
)
