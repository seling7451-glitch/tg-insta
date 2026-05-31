import sqlite3

conn = sqlite3.connect('bot_database.db')
conn.row_factory = sqlite3.Row

print("=== Users ===")
users = conn.execute('SELECT * FROM users').fetchall()
for u in users:
    print(f"TG: {u['telegram_id']}, IG: {u['instagram_user_id']}, Name: {u['instagram_username']}")

print("\n=== Video Logs ===")
videos = conn.execute('SELECT * FROM video_logs ORDER BY created_at DESC LIMIT 5').fetchall()
for v in videos:
    print(f"ID: {v['id']}, TG: {v['telegram_id']}, Status: {v['status']}, URL: {v['media_url'][:50] if v['media_url'] else 'None'}")

conn.close()
