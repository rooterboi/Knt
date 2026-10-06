import logging
import time

from aiogram import Router, F, Bot
from aiogram.filters import CommandStart, Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from aiogram.exceptions import TelegramBadRequest

import database as db
import keyboards as kb
from states import PromoStates, SearchStates
from config import PAYMENT_INFO

logger = logging.getLogger(__name__)
router = Router(name="user")


# --------------------------------------------------------------- yordamchilar
async def is_subscribed_everywhere(bot: Bot, user_id: int) -> bool:
    channels = db.list_channels()
    if not channels:
        return True
    for ch in channels:
        try:
            member = await bot.get_chat_member(chat_id=ch["channel_id"], user_id=user_id)
            if member.status in ("left", "kicked"):
                return False
        except TelegramBadRequest:
            # Bot kanalda admin bo'lmasa yoki kanal topilmasa — tekshirishni o'tkazib yuboramiz
            logger.warning("Kanal tekshirib bo'lmadi: %s", ch["channel_id"])
            continue
    return True


async def send_subscribe_prompt(message: Message):
    channels = db.list_channels()
    await message.answer(
        "⚠️ Botdan foydalanish uchun quyidagi kanallarga obuna bo'ling, so'ng \"✅ Obunani tekshirish\" tugmasini bosing:",
        reply_markup=kb.subscribe_check_kb(channels),
    )


# --------------------------------------------------------------- /start
@router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject, bot: Bot):
    user_id = message.from_user.id
    referrer_id = None
    if command.args and command.args.startswith("ref"):
        try:
            referrer_id = int(command.args[3:])
        except ValueError:
            referrer_id = None

    is_new = db.create_user_if_not_exists(
        user_id=user_id,
        username=message.from_user.username or "",
        full_name=message.from_user.full_name or "",
        referrer_id=referrer_id,
    )

    if is_new and referrer_id and referrer_id != user_id:
        bonus = db.get_setting("referral_bonus", "500")
        try:
            await bot.send_message(
                referrer_id,
                f"🎉 Siz yangi do'st taklif qildingiz! Balansingizga {bonus} so'm qo'shildi.",
            )
        except Exception:
            pass

    if not await is_subscribed_everywhere(bot, user_id):
        await send_subscribe_prompt(message)
        return

    admin = db.is_admin(user_id)
    await message.answer(
        "🎬 <b>Mukammal Kino va Serial Bot</b>ga xush kelibsiz!\n\n"
        "🔎 Kino yoki serial kodini yuboring, yoki pastdagi menyudan foydalaning.",
        reply_markup=kb.main_menu_kb(is_admin=admin),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "check_sub")
async def cb_check_sub(call: CallbackQuery, bot: Bot):
    if await is_subscribed_everywhere(bot, call.from_user.id):
        await call.message.delete()
        admin = db.is_admin(call.from_user.id)
        await call.message.answer(
            "✅ Obuna tasdiqlandi! Endi botdan to'liq foydalanishingiz mumkin.",
            reply_markup=kb.main_menu_kb(is_admin=admin),
        )
    else:
        await call.answer("❌ Siz hali barcha kanallarga obuna bo'lmadingiz.", show_alert=True)


# --------------------------------------------------------------- Kod orqali qidiruv
@router.message(F.text == "🔎 Kod orqali qidirish")
async def ask_code(message: Message, state: FSMContext):
    await state.set_state(SearchStates.waiting_code)
    await message.answer("🔢 Kino yoki serial kodini kiriting:")


@router.message(SearchStates.waiting_code)
async def process_code_state(message: Message, state: FSMContext, bot: Bot):
    await state.clear()
    await handle_code_lookup(message, message.text.strip(), bot)


# Foydalanuvchi to'g'ridan-to'g'ri kod yuborsa ham ishlaydi (masalan "KOD123")
@router.message(F.text.regexp(r"^[A-Za-z0-9_\-]{2,30}$"))
async def direct_code_lookup(message: Message, bot: Bot):
    await handle_code_lookup(message, message.text.strip(), bot)


async def handle_code_lookup(message: Message, code: str, bot: Bot):
    user_id = message.from_user.id

    if not await is_subscribed_everywhere(bot, user_id):
        await send_subscribe_prompt(message)
        return

    db.check_and_expire_premium(user_id)
    user = db.get_user(user_id)

    movie = db.get_movie_by_code(code)
    if movie:
        if not db.has_access(user, movie["access_level"]):
            await message.answer(
                "🔒 Bu kino faqat <b>Premium</b> foydalanuvchilar uchun.\n"
                "Premium olish yoki balans yig'ish uchun quyidagilardan birini tanlang:",
                reply_markup=kb.premium_required_kb(),
                parse_mode="HTML",
            )
            return

        db.increment_movie_views(code)
        caption = f"🎬 <b>{movie['title']}</b>\n\n{movie['description'] or ''}"
        try:
            if movie["poster_id"]:
                await message.answer_photo(movie["poster_id"], caption=caption, parse_mode="HTML")
            await message.answer_video(movie["file_id"], caption=caption, parse_mode="HTML")
        except TelegramBadRequest:
            await message.answer_document(movie["file_id"], caption=caption, parse_mode="HTML")
        return

    seasons = db.get_seasons(code)
    if seasons:
        await message.answer(
            "📺 Mana shu serial uchun fasllar topildi. Fasl tanlang:",
            reply_markup=kb.seasons_kb(code, seasons),
        )
        return

    await message.answer("❌ Bunday kodga ega kino yoki serial topilmadi. Kodni tekshirib qayta urinib ko'ring.")


@router.callback_query(F.data.startswith("season_"))
async def cb_pick_season(call: CallbackQuery):
    _, code, season = call.data.split("_", 2)
    season = int(season)
    episodes = db.get_episodes_of_season(code, season)
    await call.message.edit_text(
        f"📺 {season}-fasl. Qism tanlang:",
        reply_markup=kb.episodes_kb(code, season, episodes),
    )
    await call.answer()


@router.callback_query(F.data.startswith("backseasons_"))
async def cb_back_seasons(call: CallbackQuery):
    code = call.data.split("_", 1)[1]
    seasons = db.get_seasons(code)
    await call.message.edit_text("📺 Fasl tanlang:", reply_markup=kb.seasons_kb(code, seasons))
    await call.answer()


@router.callback_query(F.data.startswith("ep_"))
async def cb_pick_episode(call: CallbackQuery, bot: Bot):
    _, code, season, episode = call.data.split("_", 3)
    season, episode = int(season), int(episode)

    db.check_and_expire_premium(call.from_user.id)
    user = db.get_user(call.from_user.id)
    ep = db.get_episode(code, season, episode)
    if not ep:
        await call.answer("Topilmadi.", show_alert=True)
        return

    if not db.has_access(user, ep["access_level"]):
        await call.message.answer(
            "🔒 Bu qism faqat <b>Premium</b> foydalanuvchilar uchun.",
            reply_markup=kb.premium_required_kb(),
            parse_mode="HTML",
        )
        await call.answer()
        return

    try:
        await call.message.answer_video(
            ep["file_id"], caption=f"🎬 {ep['title']} — {season}-fasl, {episode}-qism"
        )
    except TelegramBadRequest:
        await call.message.answer_document(
            ep["file_id"], caption=f"🎬 {ep['title']} — {season}-fasl, {episode}-qism"
        )
    await call.answer()


# --------------------------------------------------------------- Balans / Premium / Referal
@router.message(F.text == "👤 Mening balansim")
async def my_balance(message: Message):
    db.check_and_expire_premium(message.from_user.id)
    user = db.get_user(message.from_user.id)
    if not user:
        await message.answer("Iltimos /start buyrug'ini yuboring.")
        return
    status = "💎 Premium" if user["status"] == "premium" else "🆓 Oddiy"
    expires = ""
    if user["status"] == "premium" and user["premium_expires_at"]:
        expires = f"\n⏳ Premium tugash sanasi: {time.strftime('%Y-%m-%d %H:%M', time.localtime(user['premium_expires_at']))}"
    elif user["status"] == "premium":
        expires = "\n♾ Umrbod premium"

    await message.answer(
        f"👤 <b>Profilingiz</b>\n\n"
        f"🆔 ID: <code>{user['user_id']}</code>\n"
        f"💰 Balans: {user['balance']} so'm\n"
        f"📌 Status: {status}{expires}\n"
        f"🤝 Takliflar soni: {user['referral_count']}",
        parse_mode="HTML",
    )


@router.message(F.text == "🤝 Do'st taklif qilish")
async def referral_info(message: Message):
    user = db.get_user(message.from_user.id)
    bonus = db.get_setting("referral_bonus", "500")
    link = kb.referral_link(message.from_user.id)
    await message.answer(
        f"🤝 <b>Do'stlaringizni taklif qiling va pul yig'ing!</b>\n\n"
        f"Har bir taklif qilingan do'st uchun: <b>{bonus} so'm</b>\n"
        f"Sizning havolangiz:\n<code>{link}</code>\n\n"
        f"📊 Jami takliflar: {user['referral_count'] if user else 0}",
        parse_mode="HTML",
    )


@router.callback_query(F.data == "show_referral")
async def cb_show_referral(call: CallbackQuery):
    await referral_info(call.message)
    await call.answer()


@router.message(F.text == "💎 Premium sotib olish")
async def premium_menu(message: Message):
    await show_premium_plans(message)


@router.callback_query(F.data == "buy_premium")
async def cb_buy_premium(call: CallbackQuery):
    await show_premium_plans(call.message)
    await call.answer()


async def show_premium_plans(message: Message):
    p1 = db.get_setting("price_1m", "15000")
    p3 = db.get_setting("price_3m", "35000")
    pl = db.get_setting("price_lifetime", "99000")
    await message.answer(
        "💎 <b>Premium tariflarni tanlang:</b>\n\n"
        "Balansingiz yetarli bo'lsa, tarifni tanlashingiz bilan avtomatik ulanadi.\n"
        f"Yoki quyidagi rekvizit orqali to'g'ridan-to'g'ri to'lov qiling:\n\n{PAYMENT_INFO}",
        reply_markup=kb.premium_plans_kb(p1, p3, pl),
        parse_mode="HTML",
    )


PLAN_SECONDS = {
    "plan_1m": 30 * 86400,
    "plan_3m": 90 * 86400,
    "plan_lifetime": None,
}
PLAN_PRICE_KEY = {
    "plan_1m": "price_1m",
    "plan_3m": "price_3m",
    "plan_lifetime": "price_lifetime",
}


@router.callback_query(F.data.in_(list(PLAN_SECONDS.keys())))
async def cb_pick_plan(call: CallbackQuery):
    price = int(db.get_setting(PLAN_PRICE_KEY[call.data], "0"))
    user = db.get_user(call.from_user.id)

    if not user or user["balance"] < price:
        await call.message.answer(
            f"❌ Balansingizda yetarli mablag' yo'q (kerak: {price} so'm, mavjud: "
            f"{user['balance'] if user else 0} so'm).\n\n"
            f"Do'st taklif qiling yoki promokod kiriting."
        )
        await call.answer()
        return

    db.update_balance(call.from_user.id, -price)
    db.grant_premium(call.from_user.id, PLAN_SECONDS[call.data])
    await call.message.answer("🎉 Tabriklaymiz! Sizga Premium status faollashtirildi.")
    await call.answer()


# --------------------------------------------------------------- Promokod
@router.message(F.text == "🎁 Promokod")
async def promo_entry(message: Message, state: FSMContext):
    await start_promo_flow(message, state)


@router.callback_query(F.data == "enter_promo")
async def cb_enter_promo(call: CallbackQuery, state: FSMContext):
    await start_promo_flow(call.message, state)
    await call.answer()


async def start_promo_flow(message: Message, state: FSMContext):
    if not db.is_promo_system_enabled():
        await message.answer("ℹ️ Promokod tizimi hozircha vaqtincha nofaol.")
        return
    await state.set_state(PromoStates.waiting_code)
    await message.answer("🎁 Promokodni kiriting:")


@router.message(PromoStates.waiting_code)
async def process_promo_code(message: Message, state: FSMContext):
    await state.clear()
    if not db.is_promo_system_enabled():
        await message.answer("ℹ️ Promokod tizimi hozircha vaqtincha nofaol.")
        return
    ok, text, _ = db.redeem_promocode(message.from_user.id, message.text.strip())
    await message.answer(text)
