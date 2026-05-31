# 📱 Instagram ↔ Telegram Bot Tizimi

> Python 3.11+ | instagrapi | pyTelegramBotAPI | SQLite | Flask Dashboard

---

## 📁 Fayl tuzilmasi

```
bot_system/
├── main.py              ← Asosiy kirish nuqtasi
├── config.py            ← Sozlamalar (.env dan o'qiydi)
├── database.py          ← SQLite CRUD operatsiyalari
├── telegram_bot.py      ← Telegram bot (telebot)
├── instagram_bot.py     ← Instagram polling (instagrapi)
├── dashboard_api.py     ← Flask REST API
├── dashboard_dist/
│   └── index.html       ← Dashboard frontend
├── .env.example         ← Muhit o'zgaruvchilari namunasi
├── requirements.txt     ← Python kutubxonalari
├── downloads/           ← Yuklangan videolar (avtomatik yaratiladi)
├── bot_database.db      ← SQLite fayl (avtomatik yaratiladi)
├── ig_session.json      ← Instagram sessiya (avtomatik yaratiladi)
└── bot.log              ← Log fayl (avtomatik yaratiladi)
```

---

## ⚡ Ishga tushirish qo'llanmasi

### 1. Python versiyasini tekshirish

```bash
python --version
# Python 3.11.x yoki undan yuqori bo'lishi kerak
```

### 2. Virtual muhit yaratish (tavsiya etiladi)

```bash
# Loyiha papkasiga o'ting
cd bot_system

# Virtual muhit yaratish
python -m venv venv

# Faollashtirish (Linux/Mac)
source venv/bin/activate

# Faollashtirish (Windows)
venv\Scripts\activate
```

### 3. Kutubxonalarni o'rnatish

```bash
pip install -r requirements.txt
```

### 4. `.env` faylini sozlash

```bash
# Namunadan ko'chirish
cp .env.example .env

# Matn muharririda ochish
nano .env
# yoki
code .env
```

**`.env` ichiga quyidagilarni kiriting:**

```env
TELEGRAM_BOT_TOKEN=1234567890:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi
INSTAGRAM_USERNAME=sizning_instagram_username
INSTAGRAM_PASSWORD=sizning_instagram_parol
DASHBOARD_SECRET_KEY=o'zgartiring_bu_maxfiy_kalitni
```

### 5. Telegram botni yaratish

1. Telegramda [@BotFather](https://t.me/BotFather) ga yozing
2. `/newbot` buyrug'ini yuboring
3. Bot nomini kiriting (masalan: `MyLinkerBot`)
4. Username ni kiriting (masalan: `my_linker_bot`)
5. Olingan **Token** ni `.env` faylga kiriting

### 6. Instagram akkauntni tayyorlash

> ⚠️ **MUHIM:** Shaxsiy akkauntingizni emas, maxsus bot akkaunt oching!

- Yangi Instagram akkaunt oching
- Telefon raqami bilan tasdiqlang
- Bir necha kun davomida oddiy foydalanuvchi kabi ish qiling (rasmlar joylang, subs qiling)
- Keyin botda ishlatishni boshlang

### 7. Botni ishga tushirish

```bash
python main.py
```

Muvaffaqiyatli ishga tushsa quyidagi log ko'rinadi:

```
2025-01-01 12:00:00 [INFO] ✅ Ma'lumotlar bazasi tayyor: bot_database.db
2025-01-01 12:00:01 [INFO] ✅ Instagram sessiyadan tiklandi
2025-01-01 12:00:01 [INFO] ✅ Thread ishga tushdi: TelegramBot
2025-01-01 12:00:01 [INFO] ✅ Thread ishga tushdi: InstagramPolling
2025-01-01 12:00:01 [INFO] ✅ Thread ishga tushdi: DashboardAPI
2025-01-01 12:00:01 [INFO] ✅ Tizim to'liq ishga tushdi!
```

### 8. Dashboard ga kirish

Brauzerda oching: **http://localhost:5000**

API kalitni kiriting (`.env` dagi `DASHBOARD_SECRET_KEY`) va **Yuklash** tugmasini bosing.

---

## 🔄 Tizim ishlash tartibi

```
Foydalanuvchi Telegram botga /start bosadi
     ↓
Bot unga Telegram ID raqamini ko'rsatadi
     ↓
Foydalanuvchi Instagram DM ga o'sha ID ni yuborgm
     ↓
Instagram polling (har 60s) DM ni tekshiradi
     ↓
ID topilsa → SQLite bazada bog'lanadi
     ↓
Tasdiqlash xabari Telegram va Instagram DM ga yuboriladi
     ↓
Endi foydalanuvchi DM ga video yuborganida:
     ↓
Bot yuklab oladi → Telegram ga yuboradi → Bazaga yozadi
```

---

## 🛡️ Xavfsizlik tavsiyalari

| Masala | Tavsiya |
|--------|---------|
| Instagram ban | Polling intervalini 60s dan kam qo'ymang |
| Sessiya | `ig_session.json` ni xavfsiz saqlang |
| Parol | `.env` faylni hech qachon GitHub ga yubormang |
| Dashboard | `DASHBOARD_SECRET_KEY` ni kuchli parol bilan almashtiring |
| Serverda | Nginx + SSL orqali dashboard ni himoya qiling |

---

## 🌐 Vercel / Production da deploy qilish

### Dashboard (Next.js yoki static hosting)

```bash
# dashboard_dist/index.html ni Vercel ga yuklash
# vercel.json fayl yarating:
```

```json
{
  "rewrites": [{ "source": "/(.*)", "destination": "/index.html" }]
}
```

`.env` dagi `API_BASE` ni production server URL ga o'zgartiring.

### Python backend (VPS yoki Railway)

```bash
# systemd service yarating (Linux server):
sudo nano /etc/systemd/system/botlink.service
```

```ini
[Unit]
Description=BotLink Instagram-Telegram Bot
After=network.target

[Service]
WorkingDirectory=/home/user/bot_system
ExecStart=/home/user/bot_system/venv/bin/python main.py
Restart=always
RestartSec=10
EnvironmentFile=/home/user/bot_system/.env

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable botlink
sudo systemctl start botlink
sudo systemctl status botlink
```

---

## 🐛 Muammolar va yechimlar

### Instagram login xatosi
```
Xato: LoginRequired
Yechim: ig_session.json faylni o'chiring va qayta ishga tushiring
```

### Telegram webhook xatosi
```
Xato: Conflict: terminated by other getUpdates request
Yechim: Faqat bitta process ishlayotganini tekshiring
```

### Video yuklanmaydi
```
Yechim: downloads/ papkasi mavjudligini tekshiring
chmod 755 downloads/  (Linux)
```

---

## 📊 API Endpointlar

| Endpoint | Metod | Tavsif |
|----------|-------|--------|
| `/api/stats` | GET | Umumiy statistika |
| `/api/users` | GET | Barcha foydalanuvchilar |
| `/api/videos` | GET | Video loglari |
| `/api/health` | GET | Server holati |

**Header:** `X-API-Key: your_secret_key`

---

## 📝 Litsenziya

MIT — Erkin foydalaning, o'zgartiring, tarqating.
