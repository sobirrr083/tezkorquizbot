import os
import openai
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv
import asyncio

load_dotenv()


BOT_TOKEN = os.environ["BOT_TOKEN"] 
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]  


bot = Bot(token=8175665332:AAH8Zbtj7Mbxau_BKspKdeDvGHParj_ewXA)
dp = Dispatcher()

client = openai.OpenAI(api_key=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)

@dp.message(Command("start"))
async def start(message: types.Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌐 Sayt", url="https://tezkorquiz.uz")],
        [InlineKeyboardButton(text="📢 Kanal", url="https://t.me/quiztezkor")],
        [InlineKeyboardButton(text="💬 Guruh", url="https://t.me/sizningguruh")]
    ])
    
    await message.reply("🤖 Assalomu alaykum! Tezkor Quiz chatbotiga xush kelibsiz!", reply_markup=keyboard)

@dp.message()
async def chat_with_ai(message: types.Message):
    try:
        response = client.chat.completions.create(
            model="mistralai/Mistral-7B-Instruct",
            messages=[{"role": "user", "content": message.text}]
        )
        await message.reply(response.choices[0].message.content)
    except Exception as e:
        await message.reply(f"Xatolik yuz berdi: {str(e)}")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
