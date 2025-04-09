import os
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from dotenv import load_dotenv
import google.generativeai as genai


load_dotenv() 


BOT_TOKEN = os.getenv("8175665332:AAH8Zbtj7Mbxau_BKspKdeDvGHParj_ewXA")
if not BOT_TOKEN:
    BOT_TOKEN = "8175665332:AAH8Zbtj7Mbxau_BKspKdeDvGHParj_ewXA"

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
 
    GEMINI_API_KEY = "AIzaSyBMT4QAjOcYRAkc9BcJXclyN7fsq_tE8Ak" 


bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)
genai.configure(api_key=GEMINI_API_KEY)


model = genai.GenerativeModel('gemini-2.0-flash')


@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("🌐 Sayt", url="https://tezkorquiz.uz"))
    keyboard.add(types.InlineKeyboardButton("📢 Kanal", url="https://t.me/quiztezkor"))
    keyboard.add(types.InlineKeyboardButton("💬 Guruh", url="https://t.me/sizningguruh"))
    
    await message.reply("🤖 Assalomu alaykum! Tezkor Quiz chatbotiga xush kelibsiz!", reply_markup=keyboard)

@dp.message_handler()
async def chat_with_ai(message: types.Message):
    try:
        # Gemini API dan javob olish
        response = model.generate_content(message.text)
        await message.reply(response.text)
    except Exception as e:
        await message.reply(f"Xatolik yuz berdi: {str(e)}")


if __name__ == "__main__":
    print("Bot ishga tushmoqda...")
    print(f"Bot token: {BOT_TOKEN[:5]}... (qolgan qismi yashirilgan)")
    print(f"Gemini API key: {GEMINI_API_KEY[:5]}... (qolgan qismi yashirilgan)")
    executor.start_polling(dp, skip_updates=True)
