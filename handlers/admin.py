import asyncio
import logging

from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter, TelegramBadRequest

import database as db
import keyboards as kb
from states import (
    AddAdminStates, RemoveAdminStates, AddMovieStates, AddEpisodeStates,
    PromoCreateStates, UserManageStates, BroadcastStates, ChannelStates,
    PostChannelStates, SettingsStates, DeleteMovieStates,
)

logger = logging.getLogger(__name__)
router = Router(name="admin")


def admin_only(user_id: int) -> bool:
    return db.is_admin(user_id)


def owner_only(user_id: int) -> bool:
    return db.is_owner(user_id)


# --------------------------------------------------------------- Kirish
@router.message(F.text == "⚙️ Admin panel")
async def open_admin_panel(message: Message):
    if not admin_only(message.from_user.id):
        return
    await message.answer(
        "⚙️ <b>Admin panel</b>\nKerakli bo'limni tanlang:",
        reply_markup=kb.admin_main_kb(owner_only(message.from_user.id)),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "adm_back")
async def cb_back(call: CallbackQuery, state: FSMContext):
    await state.clear()
    if not admin_only(call.from_user.id):
        await call.answer()
        return
    await call.message.edit_text(
        "⚙️ <b>Admin panel</b>\nKerakli bo'limni tanlang:",
        reply_markup=kb.admin_main_kb(owner_only(call.from_user.id)),
        parse_mode="HTML",
    )
    await call.answer()


# --------------------------------------------------------------- Statistika
@router.callback_query(F.data == "adm_stats")
async def cb_stats(call: CallbackQuery):
    if not admin_only(call.from_user.id):
        return await call.answer()
    s = db.user_stats()
    await call.message.edit_text(
        "📊 <b>Statistika</b>\n\n"
        f"👥 Jami foydalanuvchilar: {s['total']}\n"
        f"💎 Premium foydalanuvchilar: {s['premium']}\n"
        f"🆕 Bugun qo'shilganlar: {s['new_today']}\n"
        f"🎬 Jami kinolar: {s['movies']}",
        reply_markup=kb.back_to_admin_kb(),
        parse_mode="HTML",
    )
    await call.answer()


# --------------------------------------------------------------- Tizimlarni yoqish/o'chirish
@router.callback_query(F.data == "adm_toggles")
async def cb_toggles(call: CallbackQuery):
    if not admin_only(call.from_user.id):
        return await call.answer()
    await call.message.edit_text(
        "🔀 Tizimlarni boshqarish:",
        reply_markup=kb.toggles_kb(db.is_premium_system_enabled(), db.is_promo_system_enabled()),
    )
    await call.answer()


@router.callback_query(F.data == "toggle_premium")
async def cb_toggle_premium(call: CallbackQuery):
    if not admin_only(call.from_user.id):
        return await call.answer()
    new_val = "0" if db.is_premium_system_enabled() else "1"
    db.set_setting("premium_enabled", new_val)
    await cb_toggles(call)


@router.callback_query(F.data == "toggle_promo")
async def cb_toggle_promo(call: CallbackQuery):
    if not admin_only(call.from_user.id):
        return await call.answer()
    new_val = "0" if db.is_promo_system_enabled() else "1"
    db.set_setting("promo_enabled", new_val)
    await cb_toggles(call)


# --------------------------------------------------------------- Adminlarni boshqarish (faqat owner)
@router.callback_query(F.data == "adm_admins_menu")
async def cb_admins_menu(call: CallbackQuery):
    if not owner_only(call.from_user.id):
        return await call.answer("Faqat bosh admin uchun.", show_alert=True)
    await call.message.edit_text("👑 Adminlarni boshqarish:", reply_markup=kb.admins_menu_kb())
    await call.answer()


@router.callback_query(F.data == "adm_list_admins")
async def cb_list_admins(call: CallbackQuery):
    if not owner_only(call.from_user.id):
        return await call.answer()
    admins = db.list_admins()
    text = "📋 <b>Adminlar ro'yxati:</b>\n\n" + "\n".join(
        f"• <code>{a['user_id']}</code> — {a['role']}" for a in admins
    )
    await call.message.edit_text(text, reply_markup=kb.admins_menu_kb(), parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data == "adm_add_admin")
async def cb_add_admin_start(call: CallbackQuery, state: FSMContext):
    if not owner_only(call.from_user.id):
        return await call.answer()
    await state.set_state(AddAdminStates.waiting_id)
    await call.message.edit_text("➕ Yangi adminning Telegram ID raqamini yuboring:")
    await call.answer()


@router.message(AddAdminStates.waiting_id)
async def process_add_admin(message: Message, state: FSMContext):
    await state.clear()
    if not owner_only(message.from_user.id):
        return
    try:
        new_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Noto'g'ri format. Faqat raqam yuboring.")
        return
    ok = db.add_admin(new_id)
    msg = "✅ Admin muvaffaqiyatli qo'shildi." if ok else "ℹ️ Bu foydalanuvchi allaqachon admin."
    await message.answer(msg, reply_markup=kb.admins_menu_kb())


@router.callback_query(F.data == "adm_remove_admin")
async def cb_remove_admin_start(call: CallbackQuery, state: FSMContext):
    if not owner_only(call.from_user.id):
        return await call.answer()
    await state.set_state(RemoveAdminStates.waiting_id)
    await call.message.edit_text("➖ Olib tashlanadigan adminning Telegram ID raqamini yuboring:")
    await call.answer()


@router.message(RemoveAdminStates.waiting_id)
async def process_remove_admin(message: Message, state: FSMContext):
    await state.clear()
    if not owner_only(message.from_user.id):
        return
    try:
        rem_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Noto'g'ri format. Faqat raqam yuboring.")
        return
    ok = db.remove_admin(rem_id)
    msg = "✅ Admin olib tashlandi." if ok else "❌ Bu foydalanuvchi admin emas yoki Bosh admin."
    await message.answer(msg, reply_markup=kb.admins_menu_kb())


# --------------------------------------------------------------- Kino qo'shish
@router.callback_query(F.data == "adm_add_movie")
async def cb_add_movie_start(call: CallbackQuery, state: FSMContext):
    if not admin_only(call.from_user.id):
        return await call.answer()
    await state.set_state(AddMovieStates.waiting_file)
    await call.message.edit_text("🎬 Kino videosini (yoki faylini) yuboring:")
    await call.answer()


@router.message(AddMovieStates.waiting_file, F.video | F.document)
async def process_movie_file(message: Message, state: FSMContext):
    file_id = message.video.file_id if message.video else message.document.file_id
    await state.update_data(file_id=file_id)
    await state.set_state(AddMovieStates.waiting_poster)
    await message.answer("🖼 Endi kino posterini (rasm) yuboring. Agar kerak bo'lmasa /skip yozing.")


@router.message(AddMovieStates.waiting_poster, Command("skip"))
async def skip_poster(message: Message, state: FSMContext):
    await state.update_data(poster_id=None)
    await state.set_state(AddMovieStates.waiting_title)
    await message.answer("📝 Kino nomini kiriting:")


@router.message(AddMovieStates.waiting_poster, F.photo)
async def process_movie_poster(message: Message, state: FSMContext):
    await state.update_data(poster_id=message.photo[-1].file_id)
    await state.set_state(AddMovieStates.waiting_title)
    await message.answer("📝 Kino nomini kiriting:")


@router.message(AddMovieStates.waiting_title)
async def process_movie_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text.strip())
    await state.set_state(AddMovieStates.waiting_code)
    await message.answer("🔢 Kino uchun unikal kod kiriting (masalan: KINO101):")


@router.message(AddMovieStates.waiting_code)
async def process_movie_code(message: Message, state: FSMContext):
    code = message.text.strip()
    if db.get_movie_by_code(code):
        await message.answer("❌ Bu kod band. Boshqa kod kiriting:")
        return
    await state.update_data(code=code)
    await state.set_state(AddMovieStates.waiting_description)
    await message.answer("📝 Kino haqida qisqacha tavsif yuboring. Agar kerak bo'lmasa /skip yozing.")


@router.message(AddMovieStates.waiting_description, Command("skip"))
async def skip_description(message: Message, state: FSMContext):
    await state.update_data(description="")
    await state.set_state(AddMovieStates.waiting_access)
    await message.answer("🔐 Kirish darajasini tanlang:", reply_markup=kb.access_level_kb("movacc"))


@router.message(AddMovieStates.waiting_description)
async def process_movie_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text.strip())
    await state.set_state(AddMovieStates.waiting_access)
    await message.answer("🔐 Kirish darajasini tanlang:", reply_markup=kb.access_level_kb("movacc"))


@router.callback_query(AddMovieStates.waiting_access, F.data.startswith("movacc_"))
async def process_movie_access(call: CallbackQuery, state: FSMContext):
    access = call.data.split("_", 1)[1]
    data = await state.get_data()
    db.add_movie(
        code=data["code"],
        title=data["title"],
        file_id=data["file_id"],
        poster_id=data.get("poster_id"),
        access_level=access,
        description=data.get("description", ""),
    )
    await state.clear()
    await call.message.edit_text(
        f"✅ Kino qo'shildi!\n\n🎬 {data['title']}\n🔢 Kod: <code>{data['code']}</code>\n🔐 Daraja: {access}",
        parse_mode="HTML",
    )
    await call.answer()

    # Avto-post kanalga joylash
    await auto_post_movie(call.bot, data["title"], data["code"], data.get("poster_id"),
                           data.get("description", ""), access)


async def auto_post_movie(bot: Bot, title, code, poster_id, description, access_level):
    channel_id = db.get_setting("post_channel_id", "")
    if not channel_id:
        return
    from config import BOT_USERNAME
    access_label = {"all": "🌍 Barchaga ochiq", "free": "🆓 Oddiy foydalanuvchilar uchun",
                     "premium": "💎 Faqat Premium"}.get(access_level, "")
    link = f"https://t.me/{BOT_USERNAME}?start=code{code}"
    caption = (
        f"🎬 <b>{title}</b>\n\n"
        f"{description}\n\n"
        f"🔢 Kodi: <code>{code}</code>\n"
        f"{access_label}\n\n"
        f"👉 <a href='{link}'>Botda tomosha qilish</a>"
    )
    try:
        if poster_id:
            await bot.send_photo(channel_id, poster_id, caption=caption, parse_mode="HTML")
        else:
            await bot.send_message(channel_id, caption, parse_mode="HTML")
    except (TelegramForbiddenError, TelegramBadRequest) as e:
        logger.warning("Avto-post xatosi: %s", e)


# --------------------------------------------------------------- Serial qismi qo'shish
@router.callback_query(F.data == "adm_add_episode")
async def cb_add_episode_start(call: CallbackQuery, state: FSMContext):
    if not admin_only(call.from_user.id):
        return await call.answer()
    await state.set_state(AddEpisodeStates.waiting_code)
    await call.message.edit_text(
        "📺 Serial kodini kiriting (yangi yoki mavjud serial uchun bir xil kod ishlating):"
    )
    await call.answer()


@router.message(AddEpisodeStates.waiting_code)
async def process_ep_code(message: Message, state: FSMContext):
    await state.update_data(code=message.text.strip())
    await state.set_state(AddEpisodeStates.waiting_title)
    await message.answer("📝 Serial nomini kiriting:")


@router.message(AddEpisodeStates.waiting_title)
async def process_ep_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text.strip())
    await state.set_state(AddEpisodeStates.waiting_season)
    await message.answer("🔢 Fasl raqamini kiriting (masalan: 1):")


@router.message(AddEpisodeStates.waiting_season)
async def process_ep_season(message: Message, state: FSMContext):
    if not message.text.strip().isdigit():
        await message.answer("❌ Faqat raqam kiriting.")
        return
    await state.update_data(season=int(message.text.strip()))
    await state.set_state(AddEpisodeStates.waiting_episode)
    await message.answer("🔢 Qism (seriya) raqamini kiriting:")


@router.message(AddEpisodeStates.waiting_episode)
async def process_ep_episode(message: Message, state: FSMContext):
    if not message.text.strip().isdigit():
        await message.answer("❌ Faqat raqam kiriting.")
        return
    await state.update_data(episode=int(message.text.strip()))
    await state.set_state(AddEpisodeStates.waiting_file)
    await message.answer("🎞 Qism videosini yuboring:")


@router.message(AddEpisodeStates.waiting_file, F.video | F.document)
async def process_ep_file(message: Message, state: FSMContext):
    file_id = message.video.file_id if message.video else message.document.file_id
    await state.update_data(file_id=file_id)
    await state.set_state(AddEpisodeStates.waiting_access)
    await message.answer("🔐 Kirish darajasini tanlang:", reply_markup=kb.access_level_kb("epacc"))


@router.callback_query(AddEpisodeStates.waiting_access, F.data.startswith("epacc_"))
async def process_ep_access(call: CallbackQuery, state: FSMContext):
    access = call.data.split("_", 1)[1]
    data = await state.get_data()
    db.add_episode(
        code=data["code"], title=data["title"], season=data["season"],
        episode=data["episode"], file_id=data["file_id"], access_level=access,
    )
    await state.clear()
    await call.message.edit_text(
        f"✅ Qism qo'shildi!\n\n📺 {data['title']} — {data['season']}-fasl, {data['episode']}-qism\n"
        f"🔢 Kod: <code>{data['code']}</code>",
        parse_mode="HTML",
    )
    await call.answer()


# --------------------------------------------------------------- Kino o'chirish
@router.callback_query(F.data == "adm_del_movie")
async def cb_del_movie_start(call: CallbackQuery, state: FSMContext):
    if not admin_only(call.from_user.id):
        return await call.answer()
    await call.message.edit_text("🗑 O'chiriladigan kino kodini yuboring (xabar sifatida):")
    await state.set_state(DeleteMovieStates.waiting_code)
    await call.answer()


@router.message(DeleteMovieStates.waiting_code)
async def process_del_movie(message: Message, state: FSMContext):
    await state.clear()
    ok = db.delete_movie(message.text.strip())
    await message.answer("✅ Kino o'chirildi." if ok else "❌ Bunday kodli kino topilmadi.")


# --------------------------------------------------------------- Promokodlar
@router.callback_query(F.data == "adm_promo_menu")
async def cb_promo_menu(call: CallbackQuery):
    if not admin_only(call.from_user.id):
        return await call.answer()
    await call.message.edit_text("🎟 Promokodlar bo'limi:", reply_markup=kb.promo_menu_kb())
    await call.answer()


@router.callback_query(F.data == "adm_create_promo")
async def cb_create_promo_start(call: CallbackQuery, state: FSMContext):
    if not admin_only(call.from_user.id):
        return await call.answer()
    await state.set_state(PromoCreateStates.waiting_code)
    await call.message.edit_text("🎟 Yangi promokod nomini kiriting (masalan: KANAL2026):")
    await call.answer()


@router.message(PromoCreateStates.waiting_code)
async def process_promo_create_code(message: Message, state: FSMContext):
    code = message.text.strip()
    await state.update_data(code=code)
    await state.set_state(PromoCreateStates.waiting_amount)
    await message.answer("💰 Mukofot miqdorini kiriting (so'mda, faqat raqam):")


@router.message(PromoCreateStates.waiting_amount)
async def process_promo_create_amount(message: Message, state: FSMContext):
    if not message.text.strip().isdigit():
        await message.answer("❌ Faqat raqam kiriting.")
        return
    await state.update_data(amount=int(message.text.strip()))
    await state.set_state(PromoCreateStates.waiting_limit)
    await message.answer("👥 Nechta kishi foydalana olishi mumkin? (limit, raqam kiriting):")


@router.message(PromoCreateStates.waiting_limit)
async def process_promo_create_limit(message: Message, state: FSMContext):
    if not message.text.strip().isdigit():
        await message.answer("❌ Faqat raqam kiriting.")
        return
    data = await state.get_data()
    ok = db.create_promocode(data["code"], data["amount"], int(message.text.strip()))
    await state.clear()
    msg = "✅ Promokod yaratildi!" if ok else "❌ Bu nomli promokod allaqachon mavjud."
    await message.answer(msg, reply_markup=kb.promo_menu_kb())


# --------------------------------------------------------------- Foydalanuvchini boshqarish
@router.callback_query(F.data == "adm_user_menu")
async def cb_user_menu(call: CallbackQuery):
    if not admin_only(call.from_user.id):
        return await call.answer()
    await call.message.edit_text("👥 Foydalanuvchini boshqarish:", reply_markup=kb.user_menu_kb())
    await call.answer()


@router.callback_query(F.data.in_(["adm_give_premium", "adm_revoke_premium"]))
async def cb_premium_user_start(call: CallbackQuery, state: FSMContext):
    if not admin_only(call.from_user.id):
        return await call.answer()
    await state.update_data(action=call.data)
    await state.set_state(UserManageStates.waiting_id_for_premium)
    await call.message.edit_text("🆔 Foydalanuvchi Telegram ID raqamini yuboring:")
    await call.answer()


@router.message(UserManageStates.waiting_id_for_premium)
async def process_premium_user(message: Message, state: FSMContext):
    data = await state.get_data()
    await state.clear()
    try:
        uid = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Noto'g'ri ID.")
        return
    if not db.get_user(uid):
        await message.answer("❌ Bunday foydalanuvchi topilmadi.")
        return
    if data["action"] == "adm_give_premium":
        db.grant_premium(uid, None)
        await message.answer(f"✅ {uid} ga umrbod Premium berildi.", reply_markup=kb.user_menu_kb())
    else:
        db.revoke_premium(uid)
        await message.answer(f"✅ {uid} ning Premiumi bekor qilindi.", reply_markup=kb.user_menu_kb())


@router.callback_query(F.data == "adm_set_balance")
async def cb_set_balance_start(call: CallbackQuery, state: FSMContext):
    if not admin_only(call.from_user.id):
        return await call.answer()
    await state.set_state(UserManageStates.waiting_id_for_balance)
    await call.message.edit_text("🆔 Foydalanuvchi Telegram ID raqamini yuboring:")
    await call.answer()


@router.message(UserManageStates.waiting_id_for_balance)
async def process_balance_user_id(message: Message, state: FSMContext):
    try:
        uid = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Noto'g'ri ID.")
        return
    if not db.get_user(uid):
        await message.answer("❌ Bunday foydalanuvchi topilmadi.")
        return
    await state.update_data(target_id=uid)
    await state.set_state(UserManageStates.waiting_balance_amount)
    await message.answer("💰 Yangi balansni kiriting (0 — nolga tushirish uchun):")


@router.message(UserManageStates.waiting_balance_amount)
async def process_balance_amount(message: Message, state: FSMContext):
    if not message.text.strip().lstrip("-").isdigit():
        await message.answer("❌ Faqat raqam kiriting.")
        return
    data = await state.get_data()
    await state.clear()
    db.set_balance(data["target_id"], int(message.text.strip()))
    await message.answer(f"✅ {data['target_id']} balansi yangilandi.", reply_markup=kb.user_menu_kb())


# --------------------------------------------------------------- Broadcast
@router.callback_query(F.data == "adm_broadcast")
async def cb_broadcast_start(call: CallbackQuery, state: FSMContext):
    if not admin_only(call.from_user.id):
        return await call.answer()
    await state.set_state(BroadcastStates.waiting_message)
    await call.message.edit_text("📢 Barcha foydalanuvchilarga yuboriladigan xabarni yuboring:")
    await call.answer()


@router.message(BroadcastStates.waiting_message)
async def process_broadcast(message: Message, state: FSMContext, bot: Bot):
    await state.clear()
    user_ids = db.all_user_ids()
    await message.answer(f"⏳ Yuborilmoqda... Jami: {len(user_ids)} foydalanuvchi.")

    sent, failed = 0, 0
    for uid in user_ids:
        try:
            await message.copy_to(uid)
            sent += 1
        except TelegramRetryAfter as e:
            await asyncio.sleep(e.retry_after)
        except Exception:
            failed += 1
        await asyncio.sleep(0.05)  # flood limitdan saqlanish

    await message.answer(f"✅ Xabar yuborildi!\nMuvaffaqiyatli: {sent}\nXato: {failed}",
                          reply_markup=kb.back_to_admin_kb())


# --------------------------------------------------------------- Majburiy obuna kanallari
@router.callback_query(F.data == "adm_channels")
async def cb_channels_menu(call: CallbackQuery):
    if not admin_only(call.from_user.id):
        return await call.answer()
    channels = db.list_channels()
    text = "📡 <b>Majburiy obuna kanallari</b>\n\n"
    text += "\n".join(f"• {c['channel_id']} ({c['title']})" for c in channels) or "Hozircha kanal yo'q."
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="➕ Kanal qo'shish", callback_data="adm_add_channel"))
    builder.row(InlineKeyboardButton(text="➖ Kanal o'chirish", callback_data="adm_remove_channel"))
    builder.row(InlineKeyboardButton(text="⬅️ Orqaga", callback_data="adm_back"))
    await call.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data == "adm_add_channel")
async def cb_add_channel_start(call: CallbackQuery, state: FSMContext):
    if not admin_only(call.from_user.id):
        return await call.answer()
    await state.set_state(ChannelStates.waiting_add)
    await call.message.edit_text(
        "➕ Kanal username (@kanal) yoki ID sini yuboring.\n"
        "⚠️ Bot o'sha kanalda admin bo'lishi shart!"
    )
    await call.answer()


@router.message(ChannelStates.waiting_add)
async def process_add_channel(message: Message, state: FSMContext):
    await state.clear()
    channel_id = message.text.strip()
    db.add_channel(channel_id, channel_id)
    await message.answer(f"✅ Kanal qo'shildi: {channel_id}", reply_markup=kb.back_to_admin_kb())


@router.callback_query(F.data == "adm_remove_channel")
async def cb_remove_channel_start(call: CallbackQuery, state: FSMContext):
    if not admin_only(call.from_user.id):
        return await call.answer()
    await state.set_state(ChannelStates.waiting_remove)
    await call.message.edit_text("➖ O'chiriladigan kanal username yoki ID sini yuboring:")
    await call.answer()


@router.message(ChannelStates.waiting_remove)
async def process_remove_channel(message: Message, state: FSMContext):
    await state.clear()
    ok = db.remove_channel(message.text.strip())
    msg = "✅ Kanal o'chirildi." if ok else "❌ Bunday kanal topilmadi."
    await message.answer(msg, reply_markup=kb.back_to_admin_kb())


# --------------------------------------------------------------- Avto-post kanali
@router.callback_query(F.data == "adm_post_channel")
async def cb_post_channel_start(call: CallbackQuery, state: FSMContext):
    if not admin_only(call.from_user.id):
        return await call.answer()
    current = db.get_setting("post_channel_id", "") or "o'rnatilmagan"
    await state.set_state(PostChannelStates.waiting_channel)
    await call.message.edit_text(
        f"📮 Hozirgi avto-post kanali: <code>{current}</code>\n\n"
        f"Yangi kanal username (@kanal) yoki ID sini yuboring.\n"
        f"⚠️ Bot o'sha kanalda admin bo'lishi shart, aks holda post tashlanmaydi!",
        parse_mode="HTML",
    )
    await call.answer()


@router.message(PostChannelStates.waiting_channel)
async def process_post_channel(message: Message, state: FSMContext, bot: Bot):
    await state.clear()
    channel_id = message.text.strip()
    # Botning kanalda yoza olish-olmasligini tekshirib ko'ramiz
    try:
        await bot.send_chat_action(channel_id, "typing")
    except Exception as e:
        await message.answer(
            f"⚠️ Ogohlantirish: botni shu kanalga ulashda xatolik bo'lishi mumkin ({e}).\n"
            f"Bot kanalda ADMIN ekanligini tekshiring. Baribir saqlanmoqda..."
        )
    db.set_setting("post_channel_id", channel_id)
    await message.answer(f"✅ Avto-post kanali o'rnatildi: {channel_id}", reply_markup=kb.back_to_admin_kb())


# --------------------------------------------------------------- Narx va referal sozlamalari
@router.callback_query(F.data == "adm_pricing")
async def cb_pricing_menu(call: CallbackQuery):
    if not admin_only(call.from_user.id):
        return await call.answer()
    text = (
        "💰 <b>Joriy sozlamalar</b>\n\n"
        f"🤝 Referal bonusi: {db.get_setting('referral_bonus')} so'm\n"
        f"💎 1 oylik narx: {db.get_setting('price_1m')} so'm\n"
        f"💎 3 oylik narx: {db.get_setting('price_3m')} so'm\n"
        f"💎 Umrbod narx: {db.get_setting('price_lifetime')} so'm\n\n"
        "Qaysi qiymatni o'zgartirmoqchisiz?"
    )
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🤝 Referal bonusi", callback_data="set_referral_bonus"))
    builder.row(InlineKeyboardButton(text="💎 1 oylik narx", callback_data="set_price_1m"))
    builder.row(InlineKeyboardButton(text="💎 3 oylik narx", callback_data="set_price_3m"))
    builder.row(InlineKeyboardButton(text="💎 Umrbod narx", callback_data="set_price_lifetime"))
    builder.row(InlineKeyboardButton(text="⬅️ Orqaga", callback_data="adm_back"))
    await call.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    await call.answer()


SETTING_STATE_MAP = {
    "set_referral_bonus": (SettingsStates.waiting_referral_bonus, "referral_bonus"),
    "set_price_1m": (SettingsStates.waiting_price_1m, "price_1m"),
    "set_price_3m": (SettingsStates.waiting_price_3m, "price_3m"),
    "set_price_lifetime": (SettingsStates.waiting_price_lifetime, "price_lifetime"),
}


@router.callback_query(F.data.in_(list(SETTING_STATE_MAP.keys())))
async def cb_set_setting_start(call: CallbackQuery, state: FSMContext):
    if not admin_only(call.from_user.id):
        return await call.answer()
    target_state, key = SETTING_STATE_MAP[call.data]
    await state.set_state(target_state)
    await state.update_data(setting_key=key)
    await call.message.edit_text("🔢 Yangi qiymatni kiriting (faqat raqam):")
    await call.answer()


@router.message(
    SettingsStates.waiting_referral_bonus,
    SettingsStates.waiting_price_1m,
    SettingsStates.waiting_price_3m,
    SettingsStates.waiting_price_lifetime,
)
async def process_setting_value(message: Message, state: FSMContext):
    if not message.text.strip().isdigit():
        await message.answer("❌ Faqat raqam kiriting.")
        return
    data = await state.get_data()
    await state.clear()
    db.set_setting(data["setting_key"], message.text.strip())
    await message.answer("✅ Sozlama yangilandi.", reply_markup=kb.back_to_admin_kb())
