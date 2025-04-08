
BOT_TOKEN = os.getenv("8175665332:AAH8Zbtj7Mbxau_BKspKdeDvGHParj_ewXA")
OPENAI_API_KEY = os.getenv("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")

import os
import openai
from aiogram import Bot, Dispatcher, types
from aiogram.utils import start_polling  # Yangi usul
from dotenv import load_dotenv

# API kalitlarni yuklash
load_dotenv()
8175665332:AAH8Zbtj7Mbxau_BKspKdeDvGHParj_ewXA = os.getenv("BOT_TOKEN")  # .env faylidan o'qish, to'g'ri kalitni ishlating 
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 = os.getenv("OPENAI_API_KEY")  # .env faylidan o'qish, to'g'ri kalitni ishlating

# Telegram va OpenAI API sozlash
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)
openai.api_key = OPENAI_API_KEY

# Start komandasi
@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("🌐 Sayt", url="https://tezkorquiz.uz"))
    keyboard.add(types.InlineKeyboardButton("📢 Kanal", url="https://t.me/quiztezkor"))
    keyboard.add(types.InlineKeyboardButton("💬 Guruh", url="https://t.me/sizningguruh"))
    
    await message.reply("🤖 Assalomu alaykum! Tezkor Quiz chatbotiga xush kelibsiz!", reply_markup=keyboard)

# AI bilan muloqot
@dp.message_handler()
async def chat_with_ai(message: types.Message):
    response = openai.ChatCompletion.create(
        model="mistralai/Mistral-7B-Instruct",
        messages=[{"role": "user", "content": message.text}]
    )
    await message.reply(response["choices"][0]["message"]["content"])

# Botni ishga tushirish
if __name__ == "__main__":
    start_polling(dp, skip_updates=True)  # Yangi usulda botni ishga tushirish
