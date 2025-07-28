import asyncio
import time
import aiohttp
import os
import config
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.enums import ParseMode
from dotenv import load_dotenv

load_dotenv()

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

API_KEY = os.getenv("API_KEY")
TG_TOKEN = os.getenv("TG_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")
API_URL = "https://api.slidesgpt.com/v1"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

bot = Bot(token=TG_TOKEN)
dp = Dispatcher()
greeted_users = set()

async def download_presentation(session, presentation_id, file_format):
    url = f"{API_URL}/presentations/{presentation_id}/download"
    async with session.get(url, headers={"Authorization": f"Bearer {API_KEY}"}) as resp:
        if resp.status == 200:
            content = await resp.read()
            filename = os.path.join(DOWNLOAD_DIR, f"presentation-{presentation_id}.{file_format}")
            with open(filename, "wb") as f:
                f.write(content)
            return filename
        else:
            print(f"Ошибка: {resp.status}")
            return None
        
async def cleanup_old_files():
    while True:
        now = time.time()
        for filename in os.listdir(DOWNLOAD_DIR):
            filepath = os.path.join(DOWNLOAD_DIR, filename)
            if os.path.isfile(filepath):
                file_age = now - os.path.getmtime(filepath)
                if file_age > config.CLEANUP_MINUTES * 60:
                    try:
                        os.remove(filepath)
                        print(f"Удалён файл: {filename}")
                    except Exception as e:
                        print(f"Ошибка при удалении {filename}: {e}")
        await asyncio.sleep(config.CLEANUP_MINUTES * 60)

@dp.message(Command("generate"))
async def handle_generate(message: Message):
    prompt = message.text.replace("/generate", "").strip()
    if not prompt:
        await message.answer("Укажи тему после команды: `/generate твоя тема`", parse_mode=ParseMode.MARKDOWN_V2)
        return

    await message.answer(
        f"Генерирую презентацию на тему: *{prompt}*\\.\\.\\.\n"
        "Время ожидания 2\\-3 минуты ⏳",
        parse_mode=ParseMode.MARKDOWN_V2
        )

    payload = {
        "prompt": prompt,
        "format": config.FORMAT
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(f"{API_URL}/presentations/generate", headers=headers, json=payload) as resp:
            try:
                data = await resp.json()
            except:
                await message.answer("Не удалось создать презентацию.")
                return

            presentation_id = data.get("id")
            if not presentation_id:
                await message.answer("Презентация не создана.")
                return

            await bot.send_message(ADMIN_ID, f"📢 Пользователь @{message.from_user.username} создал презентацию")
            # await message.answer("Загружаю файл")

            file_path = await download_presentation(session, presentation_id, "pptx")
            if file_path:
                await message.answer_document(
                    types.FSInputFile(file_path), caption=f"Готово: {prompt} 📈🎉\n"
                    "Ждём тебя ещё! 👨‍💻",
                    parse_mode=ParseMode.MARKDOWN)
            else:
                await message.answer("Ошибка при скачивании.")


@dp.message(Command("start"))
async def start_handler(message: types.Message):
    greeted_users.add(message.from_user.id)
    await message.answer(
            "👋 Привет\\! Я бот, который создаёт презентации по твоему запросу\\.\n"
            "Напиши, например:\n\n"
            "`/generate Презентация про ИИ`",
            parse_mode=ParseMode.MARKDOWN_V2
        )
       
@dp.message()
async def handle_any_message(message: types.Message):
    if message.from_user.id not in greeted_users:
        greeted_users.add(message.from_user.id)
        await message.answer(
            "👋 Привет\\! Я бот, который создаёт презентации по твоему запросу\\.\n"
            "Напиши, например:\n\n"
            "`/generate Презентация про ИИ`",
            parse_mode=ParseMode.MARKDOWN_V2
        )
    else:
        await message.answer(
            "Немного не понял тебя 🙂\n"
            "Напиши, например:\n\n"
            "`/generate Презентация про ИИ`",
            parse_mode=ParseMode.MARKDOWN_V2
        )

if __name__ == "__main__":
    asyncio.run(dp.start_polling(bot))