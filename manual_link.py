#!/usr/bin/env python3
# Direct linking test - Telegram ID raqamini kiritib Instagram akkauntingizni bog'lang

import sqlite3

print("=" * 60)
print("🔗 Instagram - Telegram Bot Bog'lash Testi")
print("=" * 60)

telegram_id = int(input("\n📱 Sizning Telegram ID raqamini kiriting: "))
instagram_username = input("📸 Instagram username kiriting (masalan: xumoyun.cyber): ")
instagram_user_id = input("📸 Instagram User ID kiriting: ")

conn = sqlite3.connect('bot_database.db')
cursor = conn.cursor()

# Check if user exists
existing = cursor.execute('SELECT * FROM users WHERE telegram_id = ?', (telegram_id,)).fetchone()

if existing and existing[3]:  # instagram_user_id already set
    print(f"\n✅ Siz allaqachon bog'langansiz: @{existing[4]}")
else:
    # Link user
    cursor.execute('''
        INSERT OR REPLACE INTO users (telegram_id, instagram_user_id, instagram_username)
        VALUES (?, ?, ?)
    ''', (telegram_id, instagram_user_id, instagram_username))
    conn.commit()
    print(f"\n✅ Bog'landi: Telegram {telegram_id} ↔ Instagram @{instagram_username}")

# Show all linked users
print("\n=== Bog'langan Foydalanuvchilar ===")
users = cursor.execute('SELECT telegram_id, instagram_username FROM users WHERE instagram_user_id IS NOT NULL').fetchall()
for u in users:
    print(f"  TG: {u[0]} ↔ IG: @{u[1]}")

conn.close()
print("\n✅ Tayyoq! Bot endi videoları kutmoqda.")
