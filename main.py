import logging
import aiosqlite
import requests
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.utils import executor

# ========================
# Config
# ========================
API_TOKEN = "8499950969:AAH7FlZ9D0Mr1NU2h3_Qitd0xGwRdAzBSvA"
BASE_URL = "https://instagram-api.coder-abdulaziz.workers.dev/"
ADMIN_ID = 1306019543  # <-- Bu yerga Telegram ID ni yozing

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

DB_PATH = "users.db"

# ========================
# Debug log
# ========================
def debug_log(data):
    with open("debug.txt", "a", encoding="utf-8") as f:
        f.write(str(data) + "\n\n")

# ========================
# DB init
# ========================
async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER UNIQUE,
                username TEXT
            )
        """)
        await db.commit()

# ========================
# Add user
# ========================
async def add_user(chat_id, username=None):
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute("INSERT OR IGNORE INTO users(chat_id, username) VALUES (?, ?)", (chat_id, username))
            await db.commit()
        except Exception as e:
            logging.error(f"DB error: {e}")

# ========================
# /start
# ========================
@dp.message(Command(commands=["start"]))
async def start_cmd(message: types.Message):
    await add_user(message.chat.id, message.from_user.username)
    await message.answer(
        "Salom! 😊\nQuyidagi komandalarni ishlatishingiz mumkin:\n"
        "/info <username>\n/posts <username>\n/stories <username>"
    )

# ========================
# /info <username>
# ========================
@dp.message(Command(commands=["info"]))
async def info_cmd(message: types.Message):
    parts = message.text.split()
    if len(parts) < 2:
        await message.reply("Iltimos, username kiriting: /info <username>")
        return
    username = parts[1]

    url = f"{BASE_URL}?get=info&username={username}"
    resp = requests.get(url).json()
    debug_log(resp)

    if not resp.get("success"):
        await message.reply("Profil topilmadi yoki xatolik yuz berdi.")
        return

    data = resp
    msg = (
        f"👤 <b>{data['full_name']}</b>\n"
        f"📝 Bio: {data['bio']}\n"
        f"📌 Followers: {data['followers']}\n"
        f"📌 Following: {data['following']}\n"
        f"📌 Posts: {data['posts']}\n"
        f"🔗 Username: @{data['username']}"
    )
    await bot.send_photo(chat_id=message.chat.id, photo=data['profile_pic'], caption=msg)

# ========================
# /posts <username>
# ========================
@dp.message(Command(commands=["posts"]))
async def posts_cmd(message: types.Message):
    parts = message.text.split()
    if len(parts) < 2:
        await message.reply("Iltimos, username kiriting: /posts <username>")
        return
    username = parts[1]

    url = f"{BASE_URL}?get=posts&username={username}"
    resp = requests.get(url).json()
    debug_log(resp)

    if not resp.get("success") or not resp.get("posts"):
        await message.reply("Postlar topilmadi yoki xatolik yuz berdi.")
        return

    for post in resp["posts"]:
        caption = post.get("caption", "Yo'q caption")
        media_type = post.get("media_type")
        if media_type == 2 and post.get("video_url"):
            await bot.send_video(chat_id=message.chat.id, video=post["video_url"], caption=f"{caption}\n❤️ {post['like_count']} | 💬 {post['comment_count']}")
        else:
            await bot.send_photo(chat_id=message.chat.id, photo=post["image_url"], caption=f"{caption}\n❤️ {post['like_count']} | 💬 {post['comment_count']}")

# ========================
# /stories <username>
# ========================
@dp.message(Command(commands=["stories"]))
async def stories_cmd(message: types.Message):
    parts = message.text.split()
    if len(parts) < 2:
        await message.reply("Iltimos, username kiriting: /stories <username>")
        return
    username = parts[1]

    url = f"{BASE_URL}?get=stories&username={username}"
    resp = requests.get(url).json()
    debug_log(resp)

    if not resp.get("success") or not resp.get("stories"):
        await message.reply("Stories topilmadi yoki foydalanuvchi faollashtirmagan.")
        return

    for story in resp["stories"]:
        for item in story["items"]:
            if item.get("video_url"):
                await bot.send_video(chat_id=message.chat.id, video=item["video_url"])
            else:
                await bot.send_photo(chat_id=message.chat.id, photo=item["image_url"])

# ========================
# Admin panel: /users va /broadcast
# ========================
@dp.message(Command(commands=["users"]))
async def admin_users(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT chat_id, username FROM users")
        rows = await cursor.fetchall()
    text = "\n".join([f"{r[0]} | @{r[1]}" for r in rows])
    await message.reply(f"Foydalanuvchilar:\n{text or 'Bo\'sh'}")

@dp.message(Command(commands=["broadcast"]))
async def admin_broadcast(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.reply("Xabar matnini yozing: /broadcast <matn>")
        return
    text = parts[1]
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT chat_id FROM users")
        rows = await cursor.fetchall()
    for row in rows:
        try:
            await bot.send_message(chat_id=row[0], text=text)
        except Exception as e:
            logging.error(f"Xabar yuborilmadi {row[0]}: {e}")
    await message.reply("Xabar barcha foydalanuvchilarga yuborildi!")

# ========================
# Start bot
# ========================
if __name__ == "__main__":
    import asyncio
    asyncio.run(init_db())
    executor.start_polling(dp, skip_updates=True)
