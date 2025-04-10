import os
import sqlite3
import asyncio
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils import executor
from aiogram.types import ChatActions
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    BOT_TOKEN = "8175665332:AAH8Zbtj7Mbxau_BKspKdeDvGHParj_ewXA"

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    GEMINI_API_KEY = "AIzaSyBMT4QAjOcYRAkc9BcJXclyN7fsq_tE8Ak"

ADMIN_ID = os.getenv("ADMIN_ID", "123456789")  # Admin ID raqami

# Foydalanuvchi tillari va status ma'lumotlari
user_languages = {}
processing_messages = {}

# Database setup
def init_db():
    conn = sqlite3.connect('tezkor_quiz.db')
    c = conn.cursor()
    
    # Foydalanuvchilar jadvali (familiya va telefon raqam olib tashlandi)
    c.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        first_name TEXT,
        username TEXT,
        language TEXT DEFAULT 'uz',
        registered_at TIMESTAMP,
        questions_count INTEGER DEFAULT 0
    )
    ''')
    
    # Kunlik statistika jadvali
    c.execute('''
    CREATE TABLE IF NOT EXISTS daily_stats (
        date TEXT PRIMARY KEY,
        new_users INTEGER DEFAULT 0,
        total_questions INTEGER DEFAULT 0
    )
    ''')
    
    conn.commit()
    conn.close()

# FSM holatlari (familiya va telefon holatlari olib tashlandi)
class Registration(StatesGroup):
    first_name = State()
    language = State()

# Bot va dispatcher
storage = MemoryStorage()
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot, storage=storage)
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash')

# Foydalanuvchining tilini saqlash
def set_user_language(user_id, language):
    user_languages[user_id] = language
    
    conn = sqlite3.connect('tezkor_quiz.db')
    c = conn.cursor()
    c.execute('UPDATE users SET language = ? WHERE user_id = ?', (language, user_id))
    conn.commit()
    conn.close()

# Foydalanuvchining tilini olish
def get_user_language(user_id):
    # Avval local cache'dan tekshirish
    if user_id in user_languages:
        return user_languages[user_id]
    
    # Agar topilmasa, bazadan tekshirish
    conn = sqlite3.connect('tezkor_quiz.db')
    c = conn.cursor()
    c.execute('SELECT language FROM users WHERE user_id = ?', (user_id,))
    result = c.fetchone()
    conn.close()
    
    if result:
        language = result[0]
        user_languages[user_id] = language
        return language
    
    return 'uz'  # Default til

# Foydalanuvchi qo'shish (familiya va telefon raqam olib tashlandi)
def register_user(user_id, first_name, username, language='uz'):
    conn = sqlite3.connect('tezkor_quiz.db')
    c = conn.cursor()
    
    c.execute('''
    INSERT OR IGNORE INTO users (user_id, first_name, username, language, registered_at, questions_count) 
    VALUES (?, ?, ?, ?, ?, 0)
    ''', (user_id, first_name, username, language, datetime.now()))
    
    # Agar yangi foydalanuvchi qo'shilsa, kunlik statistikani yangilash
    if c.rowcount > 0:
        today = datetime.now().strftime('%Y-%m-%d')
        c.execute('INSERT OR IGNORE INTO daily_stats (date, new_users, total_questions) VALUES (?, 0, 0)', (today,))
        c.execute('UPDATE daily_stats SET new_users = new_users + 1 WHERE date = ?', (today,))
    
    conn.commit()
    conn.close()
    
    # Cache'ga saqlash
    user_languages[user_id] = language

# Savol sonini oshirish
def increment_question_count(user_id):
    conn = sqlite3.connect('tezkor_quiz.db')
    c = conn.cursor()
    
    c.execute('UPDATE users SET questions_count = questions_count + 1 WHERE user_id = ?', (user_id,))
    
    # Kunlik statistikani yangilash
    today = datetime.now().strftime('%Y-%m-%d')
    c.execute('INSERT OR IGNORE INTO daily_stats (date, new_users, total_questions) VALUES (?, 0, 0)', (today,))
    c.execute('UPDATE daily_stats SET total_questions = total_questions + 1 WHERE date = ?', (today,))
    
    conn.commit()
    conn.close()

# Start komandasi
@dp.message_handler(commands=["start"], state="*")
async def start(message: types.Message, state: FSMContext):
    await state.finish()  # Barcha holatlarni tozalash
    
    user_id = message.from_user.id
    
    # Bazadan foydalanuvchini tekshirish
    conn = sqlite3.connect('tezkor_quiz.db')
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    user = c.fetchone()
    conn.close()
    
    if user:
        # Agar foydalanuvchi ro'yxatdan o'tgan bo'lsa
        language = user[3]  # index o'zgartirildi
        user_languages[user_id] = language
        
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("🌐 Sayt", url="https://tezkorquiz.uz"))
        keyboard.add(types.InlineKeyboardButton("📢 Kanal", url="https://t.me/quiztezkor"))
        keyboard.add(types.InlineKeyboardButton("💬 Guruh", url="https://t.me/tezkorquiz_group"))
        
        greeting = {
            'uz': f"🤖 Assalomu alaykum, {user[1]}! Tezkor Quiz chatbotiga qaytganingizdan xursandmiz! Menga bemalol savol berishingiz mumkin, to'g'ri javob berishga harakat qilaman!",
            'ru': f"🤖 Здравствуйте, {user[1]}! Рады видеть вас снова в чат-боте Tezkor Quiz! Не стесняйтесь задавать мне вопросы, я постараюсь дать правильный ответ!",
            'en': f"🤖 Hello, {user[1]}! Welcome back to Tezkor Quiz chatbot! Feel free to ask me questions, I'll try to give the correct answer!"
        }
        
        await message.reply(greeting.get(language, greeting['uz']), reply_markup=keyboard)
    else:
        # Ro'yxatdan o'tish uchun
        await message.reply("🤖 Assalomu alaykum! Tezkor Quiz chatbotiga xush kelibsiz! Iltimos, ro'yxatdan o'tish uchun ismingizni kiriting:")
        await Registration.first_name.set()

# Ism kiritish uchun
@dp.message_handler(state=Registration.first_name)
async def process_first_name(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['first_name'] = message.text
    
    # Familiya va telefon raqam o'rniga to'g'ridan-to'g'ri til tanlashga o'tadi
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    keyboard.add(
        types.KeyboardButton("🇺🇿 O'zbekcha"),
        types.KeyboardButton("🇷🇺 Русский"),
        types.KeyboardButton("🇬🇧 English")
    )
    
    await message.reply("Iltimos, botdan foydalanish uchun tilni tanlang:", reply_markup=keyboard)
    await Registration.language.set()

# Til tanlash uchun
@dp.message_handler(state=Registration.language)
async def process_language(message: types.Message, state: FSMContext):
    language = 'uz'  # Default til
    
    if message.text == "🇷🇺 Русский":
        language = 'ru'
    elif message.text == "🇬🇧 English":
        language = 'en'
    
    async with state.proxy() as data:
        # Foydalanuvchini ro'yxatdan o'tkazish (familiya va telefon raqam olib tashlandi)
        register_user(
            message.from_user.id,
            data['first_name'],
            message.from_user.username,
            language
        )
    
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("🌐 Sayt", url="https://tezkorquiz.uz"))
    keyboard.add(types.InlineKeyboardButton("📢 Kanal", url="https://t.me/quiztezkor"))
    keyboard.add(types.InlineKeyboardButton("💬 Guruh", url="https://t.me/tezkorquiz_group"))
    
    greeting = {
        'uz': "🤖 Tabriklaymiz! Ro'yxatdan muvaffaqiyatli o'tdingiz. Menga bemalol savol berishingiz mumkin, to'g'ri javob berishga harakat qilaman!",
        'ru': "🤖 Поздравляем! Вы успешно зарегистрировались. Не стесняйтесь задавать мне вопросы, я постараюсь дать правильный ответ!",
        'en': "🤖 Congratulations! You have successfully registered. Feel free to ask me questions, I'll try to give the correct answer!"
    }
    
    await message.reply(greeting.get(language, greeting['uz']), reply_markup=types.ReplyKeyboardRemove())
    await message.reply("👇", reply_markup=keyboard)
    await state.finish()

# Til almashtirish
@dp.message_handler(commands=["language", "til", "язык"])
async def change_language(message: types.Message):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    keyboard.add(
        types.KeyboardButton("🇺🇿 O'zbekcha"),
        types.KeyboardButton("🇷🇺 Русский"),
        types.KeyboardButton("🇬🇧 English")
    )
    
    await message.reply("Tilni tanlang / Выберите язык / Choose language:", reply_markup=keyboard)

@dp.message_handler(lambda message: message.text in ["🇺🇿 O'zbekcha", "🇷🇺 Русский", "🇬🇧 English"])
async def set_language(message: types.Message):
    language = 'uz'  # Default til
    
    if message.text == "🇷🇺 Русский":
        language = 'ru'
    elif message.text == "🇬🇧 English":
        language = 'en'
    
    set_user_language(message.from_user.id, language)
    
    response_text = {
        'uz': "✅ Til o'zbekchaga o'zgartirildi!",
        'ru': "✅ Язык изменен на русский!",
        'en': "✅ Language changed to English!"
    }
    
    await message.reply(response_text.get(language, response_text['uz']), reply_markup=types.ReplyKeyboardRemove())

# Admin uchun statistika
@dp.message_handler(commands=["admin"])
async def admin_panel(message: types.Message):
    if str(message.from_user.id) != ADMIN_ID:
        await message.reply("Sizda adminlik huquqi yo'q!")
        return
    
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        types.InlineKeyboardButton("📊 Umumiy statistika", callback_data="stats_general"),
        types.InlineKeyboardButton("👥 Foydalanuvchilar", callback_data="users_list"),
        types.InlineKeyboardButton("📅 Kunlik statistika", callback_data="stats_daily"),
        types.InlineKeyboardButton("🔝 Top foydalanuvchilar", callback_data="users_top"),
        types.InlineKeyboardButton("🌐 Til bo'yicha statistika", callback_data="stats_language")
    )
    
    await message.reply("Admin panelga xush kelibsiz! Kerakli bo'limni tanlang:", reply_markup=keyboard)

# Admin panel callback'lari
@dp.callback_query_handler(lambda c: c.data.startswith('stats_') or c.data.startswith('users_'))
async def process_admin_callback(callback_query: types.CallbackQuery):
    if str(callback_query.from_user.id) != ADMIN_ID:
        await callback_query.answer("Sizda adminlik huquqi yo'q!", show_alert=True)
        return
    
    conn = sqlite3.connect('tezkor_quiz.db')
    c = conn.cursor()
    
    if callback_query.data == "stats_general":
        # Umumiy statistika
        c.execute('SELECT COUNT(*) FROM users')
        total_users = c.fetchone()[0]
        
        c.execute('SELECT SUM(questions_count) FROM users')
        total_questions = c.fetchone()[0] or 0
        
        c.execute('SELECT COUNT(*) FROM users WHERE registered_at >= datetime("now", "-1 day")')
        new_users_24h = c.fetchone()[0]
        
        await callback_query.message.edit_text(
            f"📊 Umumiy statistika:\n\n"
            f"👥 Jami foydalanuvchilar: {total_users}\n"
            f"❓ Jami savollar soni: {total_questions}\n"
            f"🆕 So'ngi 24 soatda yangi foydalanuvchilar: {new_users_24h}",
            reply_markup=get_back_keyboard()
        )
        
    elif callback_query.data == "users_list":
        # Foydalanuvchilar ro'yxati (oxirgi 10 ta) (familiya va telefon raqamsiz)
        c.execute('SELECT user_id, first_name, questions_count, language FROM users ORDER BY registered_at DESC LIMIT 10')
        users = c.fetchall()
        
        text = "👥 Oxirgi 10 ta foydalanuvchi:\n\n"
        for i, user in enumerate(users, 1):
            text += f"{i}. {user[1]}\n"
            text += f"   🌐 Til: {user[3]}\n"
            text += f"   ❓ Savollar: {user[2]}\n\n"
        
        await callback_query.message.edit_text(text, reply_markup=get_back_keyboard())
        
    elif callback_query.data == "stats_daily":
        # Kunlik statistika (oxirgi 7 kun)
        c.execute('SELECT date, new_users, total_questions FROM daily_stats ORDER BY date DESC LIMIT 7')
        daily_stats = c.fetchall()
        
        text = "📅 Oxirgi 7 kunlik statistika:\n\n"
        for day in daily_stats:
            text += f"📆 {day[0]}:\n"
            text += f"   🆕 Yangi foydalanuvchilar: {day[1]}\n"
            text += f"   ❓ Jami savollar: {day[2]}\n\n"
        
        await callback_query.message.edit_text(text, reply_markup=get_back_keyboard())
        
    elif callback_query.data == "users_top":
        # Eng ko'p savol bergan foydalanuvchilar
        c.execute('SELECT first_name, questions_count FROM users ORDER BY questions_count DESC LIMIT 10')
        top_users = c.fetchall()
        
        text = "🔝 Eng faol 10 ta foydalanuvchi:\n\n"
        for i, user in enumerate(top_users, 1):
            text += f"{i}. {user[0]} - {user[1]} ta savol\n"
        
        await callback_query.message.edit_text(text, reply_markup=get_back_keyboard())
    
    elif callback_query.data == "stats_language":
        # Til bo'yicha statistika
        c.execute('SELECT language, COUNT(*) FROM users GROUP BY language')
        language_stats = c.fetchall()
        
        text = "🌐 Til bo'yicha foydalanuvchilar:\n\n"
        language_names = {
            'uz': "O'zbekcha",
            'ru': "Ruscha",
            'en': "Inglizcha",
            None: "Belgilanmagan"
        }
        
        for lang in language_stats:
            lang_name = language_names.get(lang[0], lang[0])
            text += f"{lang_name}: {lang[1]} ta foydalanuvchi\n"
        
        await callback_query.message.edit_text(text, reply_markup=get_back_keyboard())
    
    elif callback_query.data == "admin_back":
        # Admin paneliga qaytish
        keyboard = types.InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            types.InlineKeyboardButton("📊 Umumiy statistika", callback_data="stats_general"),
            types.InlineKeyboardButton("👥 Foydalanuvchilar", callback_data="users_list"),
            types.InlineKeyboardButton("📅 Kunlik statistika", callback_data="stats_daily"),
            types.InlineKeyboardButton("🔝 Top foydalanuvchilar", callback_data="users_top"),
            types.InlineKeyboardButton("🌐 Til bo'yicha statistika", callback_data="stats_language")
        )
        
        await callback_query.message.edit_text("Admin panelga xush kelibsiz! Kerakli bo'limni tanlang:", reply_markup=keyboard)
    
    conn.close()
    await callback_query.answer()

def get_back_keyboard():
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("⬅️ Orqaga", callback_data="admin_back"))
    return keyboard

# Savol so'rashni to'xtatish knopkasi
def get_cancel_keyboard(user_id):
    language = get_user_language(user_id)
    
    cancel_text = {
        'uz': "❌ To'xtatish",
        'ru': "❌ Остановить",
        'en': "❌ Stop"
    }
    
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(cancel_text.get(language, cancel_text['uz']), callback_data="cancel_request"))
    return keyboard

# So'rovni bekor qilish
@dp.callback_query_handler(lambda c: c.data == "cancel_request")
async def cancel_request(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    language = get_user_language(user_id)
    
    if user_id in processing_messages:
        message_id = processing_messages[user_id]
        del processing_messages[user_id]
        
        cancel_text = {
            'uz': "❌ So'rov to'xtatildi",
            'ru': "❌ Запрос остановлен",
            'en': "❌ Request stopped"
        }
        
        await bot.edit_message_text(
            chat_id=callback_query.message.chat.id,
            message_id=message_id,
            text=cancel_text.get(language, cancel_text['uz'])
        )
    
    await callback_query.answer()

# Typing animatsiyasi bilan javob yuborish
async def send_typing_action(chat_id, user_id, language):
    typing_text = {
        'uz': "Yozmoqda...",
        'ru': "Пишет...",
        'en': "Typing..."
    }
    
    sent_message = await bot.send_message(
        chat_id=chat_id,
        text=typing_text.get(language, typing_text['uz']),
        reply_markup=get_cancel_keyboard(user_id)
    )
    
    processing_messages[user_id] = sent_message.message_id
    return sent_message.message_id

# Savollarni qayta ishlash
@dp.message_handler()
async def chat_with_ai(message: types.Message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    
    try:
        # Foydalanuvchi mavjudligini tekshirish
        conn = sqlite3.connect('tezkor_quiz.db')
        c = conn.cursor()
        c.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        user = c.fetchone()
        conn.close()
        
        if not user:
            # Agar foydalanuvchi topilmasa, ro'yxatdan o'tishni taklif qilish
            await message.reply("Iltimos, botdan foydalanish uchun /start buyrug'ini bosing va ro'yxatdan o'ting!")
            return
        
        # Foydalanuvchi tilini olish
        language = get_user_language(user_id)
        
        # Yozayotganini ko'rsatish
        await bot.send_chat_action(chat_id, ChatActions.TYPING)
        message_id = await send_typing_action(chat_id, user_id, language)
        
        # Savol sonini oshirish
        increment_question_count(user_id)
        
        # Gemini API dan javob olish
        try:
            response = model.generate_content(message.text)
            response_text = response.text
            
            # Jarayonni to'xtatish tekshiruvi
            if user_id in processing_messages:
                # Javob tayyor bo'lsa, statusni o'zgartirish
                await bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=response_text,
                    reply_markup=None
                )
                del processing_messages[user_id]
            else:
                # Agar jarayon bekor qilingan bo'lsa, yangi xabar yuborish
                await message.reply(response_text)
        
        except Exception as e:
            # Agar Gemini API bilan xatolik yuz bersa
            if user_id in processing_messages:
                error_text = {
                    'uz': f"Xatolik yuz berdi: {str(e)}",
                    'ru': f"Произошла ошибка: {str(e)}",
                    'en': f"Error occurred: {str(e)}"
                }
                
                await bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=error_text.get(language, error_text['uz']),
                    reply_markup=None
                )
                del processing_messages[user_id]
            else:
                await message.reply(f"Xatolik yuz berdi: {str(e)}")
    
    except Exception as e:
        await message.reply(f"Tizim xatoligi: {str(e)}")

if __name__ == "__main__":
    print("Bot ishga tushmoqda...")
    init_db()  # Ma'lumotlar bazasini yaratish
    print(f"Bot token: {BOT_TOKEN[:5]}... (qolgan qismi yashirilgan)")
    print(f"Gemini API key: {GEMINI_API_KEY[:5]}... (qolgan qismi yashirilgan)")
    executor.start_polling(dp, skip_updates=True)
