# 🎬 Mukammal Kino va Serial Bot

aiogram 3.x + SQLite asosida yozilgan to'liq funksional Telegram kino-bot.

## O'rnatish

```bash
pip install -r requirements.txt
```

`config.py` faylida quyidagilarni to'ldiring (yoki environment variable orqali bering):

- `BOT_TOKEN` — @BotFather dan olingan token
- `OWNER_ID` — sizning Telegram user_id'ingiz (bosh admin)
- `BOT_USERNAME` — bot username'i (referal havola uchun, @ belgisiz)

Ishga tushirish:

```bash
python bot.py
```

## Fayl tuzilishi

```
cinema_bot/
├── bot.py              # ishga tushirish nuqtasi
├── config.py           # sozlamalar
├── database.py         # SQLite bilan ishlash (barcha jadvallar va funksiyalar)
├── keyboards.py        # inline/reply klaviaturalar
├── states.py            # FSM holatlari
├── handlers/
│   ├── user.py          # foydalanuvchi: /start, qidiruv, balans, promo, premium, referal
│   └── admin.py         # admin panel: kino/serial qo'shish, adminlar, broadcast, sozlamalar
└── requirements.txt
```

## Asosiy imkoniyatlar

- **Oddiy / Premium foydalanuvchilar**, kirish darajasiga qarab cheklov
- **Referal tizimi** — do'st taklif qilib ichki balansga pul yig'ish
- **Promokodlar** — admin yaratadi, foydalanuvchi /promo yoki "🎁 Promokod" orqali kiritadi, limit va bir martalik ishlatish nazorat qilinadi
- **Majburiy obuna** (sponsor kanallar) — obuna bo'lmaguncha botdan foydalanib bo'lmaydi
- **Avto-post** — yangi kino/serial qo'shilganda sozlangan kanalga avtomatik chiroyli post (poster + nom + kod + bot havolasi) joylanadi
- **To'liq admin panel**:
  - Admin qo'shish/olib tashlash (faqat Bosh admin — Owner)
  - Premium tizimini yoqish/o'chirish (o'chirilsa — hammaga tekin)
  - Promokod tizimini yoqish/o'chirish
  - Kino/serial qo'shish (kirish darajasini tanlab), seriyalarni fasl/qism bo'yicha tartiblash
  - Promokod yaratish (nom, summa, limit)
  - Referal bonusi va premium narxlarini sozlash
  - Foydalanuvchiga premium berish/bekor qilish, balansini o'zgartirish
  - Broadcast (ommaviy xabar yuborish), flood-limitga chidamli (RetryAfter'ni ushlaydi)
  - Majburiy obuna kanallarini qo'shish/o'chirish
  - Statistika (jami/premium foydalanuvchilar, bugungi yangi a'zolar, kinolar soni)

## Texnik eslatmalar

- SQLite **WAL** rejimida ishlaydi — bir vaqtda ko'p o'qish/yozish so'rovlariga chidamli.
- Har bir DB funksiyasi o'z connection'ini ochib-yopadi — oqimlar orasida konflikt bo'lmaydi.
- Barcha tashqi so'rovlar (Telegram API chaqiruvlari) `try/except` bilan o'ralgan — bitta foydalanuvchidagi xatolik butun botni to'xtatmaydi.
- Botni kanalga avto-post qilish yoki majburiy obunani tekshirish uchun **bot o'sha kanallarda admin bo'lishi shart**.
- Katta auditoriyaga broadcast yuborishda so'rovlar orasiga kichik `sleep` qo'yilgan — Telegramning flood-limitidan saqlanish uchun.

## Kengaytirish g'oyalari

- To'lov tizimini avtomatlashtirish uchun Payme/Click/Stripe kabi to'lov provayderini ulash mumkin (`PAYMENT_INFO` o'rniga).
- `movies`/`series` jadvaliga `genre`, `year`, `rating` kabi maydonlar qo'shib, janr bo'yicha qidiruv va reytingga asoslangan tavsiyalar qo'shish mumkin.
- Katta hajmdagi fayllar uchun Telegram File API o'rniga alohida fayl-serverga (masalan MTProto client orqali) o'tish tavsiya etiladi.
