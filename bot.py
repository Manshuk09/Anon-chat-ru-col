import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# ================= НАСТРОЙКИ =================
TOKEN = "8861156320:AAEd_G2uA0GfNEifOzawEnLAFFFTov-1FHA"
ADMIN_ID = 6681923689
# ============================================

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()

search_queue = []          
active_chats = {}          
user_profiles = {}         

class States(StatesGroup):
    waiting_for_support = State()
    profile_gender = State()
    profile_age = State()
    profile_interests = State()
    profile_bio = State()

def get_main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔍 Начать поиск собеседника")],
            [KeyboardButton(text="📄 Посмотреть мою анкету"), KeyboardButton(text="✏️ Заполнить анкету заново")],
            [KeyboardButton(text="💬 Поддержка")],
            [KeyboardButton(text="📢 Наш канал")]
        ],
        resize_keyboard=True
    )

def get_chat_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🛑 Остановить диалог")]
        ],
        resize_keyboard=True
    )

# 1. /start
@dp.message(F.text == "/start")
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    if user_id in active_chats:
        partner_id = active_chats.pop(user_id)
        if partner_id in active_chats:
            active_chats.pop(partner_id)
        try:
            await bot.send_message(partner_id, "⚠️ Собеседник завершил сеанс.", reply_markup=get_main_menu())
        except:
            pass

    await message.answer(
        "👋 Привет! Добро пожаловать в анонимный чат (**строго 18+**).\n\n"
        "Здесь ты можешь общаться с анонимными собеседниками и заводить новые знакомства.",
        reply_markup=get_main_menu()
    )

# 2. Наш канал
@dp.message(F.text == "📢 Наш канал")
async def channel_link(message: types.Message):
    await message.answer("📢 Наш официальный канал: https://t.me/anonimnyichat_ru_bot", reply_markup=get_main_menu())

# ================= АНКЕТА (СТРОГО 18+) =================

@dp.message(F.text == "✏️ Заполнить анкету заново")
async def start_filling_profile(message: types.Message, state: FSMContext):
    await state.set_state(States.profile_gender)
    markup = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👤 Парень"), KeyboardButton(text="👧 Девушка")],
            [KeyboardButton(text="❌ Отмена")]
        ],
        resize_keyboard=True
    )
    await message.answer("📝 Шаг 1/3: Укажи свой пол:", reply_markup=markup)

@dp.message(F.text == "❌ Отмена")
async def cancel_profile(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Действие отменено.", reply_markup=get_main_menu())

@dp.message(States.profile_gender, F.text.in_(["👤 Парень", "👧 Девушка"]))
async def profile_gender_chosen(message: types.Message, state: FSMContext):
    await state.update_data(gender=message.text)
    await state.set_state(States.profile_age)
    await message.answer(
        "📝 Шаг 2/3: Сколько тебе лет?\n⚠️ **Внимание: бот строго 18+!** Введи свой возраст цифрой:", 
        reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True)
    )

# Гибкая проверка возраста: если < 18, просто просим ввести заново БЕЗ сброса анкеты
@dp.message(States.profile_age)
async def profile_age_chosen(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("⚠️ Пожалуйста, введи возраст цифрами (например: 18, 20, 25).")
        return

    age = int(message.text)
    if age < 18:
        await message.answer(
            "🛑 **Сюда нельзя!** Использование бота разрешено только с 18 лет.\n"
            "Пожалуйста, введи реальный возраст (от 18 и выше), чтобы продолжить:",
            reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True)
        )
        return  # Не сбрасываем state, даем возможность ввести число заново!

    await state.update_data(age=str(age))
    await state.set_state(States.profile_interests)
    
    markup = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎨 Рисование"), KeyboardButton(text="🎬 Сериалы")],
            [KeyboardButton(text="📖 Книги"), KeyboardButton(text="🌸 Аниме")],
            [KeyboardButton(text="⚽ Спорт"), KeyboardButton(text="🎵 Музыка")],
            [KeyboardButton(text="❌ Отмена")]
        ],
        resize_keyboard=True
    )
    await message.answer("📝 Шаг 3/3: Выбери свой главный интерес:", reply_markup=markup)

@dp.message(States.profile_interests, F.text.in_(["🎨 Рисование", "🎬 Сериалы", "📖 Книги", "🌸 Аниме", "⚽ Спорт", "🎵 Музыка"]))
async def profile_interests_chosen(message: types.Message, state: FSMContext):
    await state.update_data(interests=message.text)
    await state.set_state(States.profile_bio)
    await message.answer("📝 И последнее: напиши пару слов о себе (описание):", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))

@dp.message(States.profile_bio)
async def profile_bio_chosen(message: types.Message, state: FSMContext):
    data = await state.get_data()
    user_id = message.from_user.id
    
    user_profiles[user_id] = {
        "gender": data["gender"],
        "age": data["age"],
        "interests": data["interests"],
        "bio": message.text
    }
    
    await state.clear()
    await message.answer(
        "✅ Анкета успешно заполнена и сохранена!\n\n"
        f"👤 Пол: {data['gender']}\n"
        f"🎂 Возраст: {data['age']}\n"
        f"💡 Интерес: {data['interests']}\n"
        f"📄 Описание: {message.text}",
        reply_markup=get_main_menu()
    )

@dp.message(F.text == "📄 Посмотреть мою анкету")
async def view_profile(message: types.Message):
    user_id = message.from_user.id
    if user_id in user_profiles:
        p = user_profiles[user_id]
        await message.answer(
            f"📄 **Твоя анкета:**\n\n"
            f"👤 Пол: {p['gender']}\n"
            f"🎂 Возраст: {p['age']}\n"
            f"💡 Интерес: {p.get('interests', 'Не указан')}\n"
            f"📄 Описание: {p['bio']}",
            reply_markup=get_main_menu()
        )
    else:
        await message.answer(
            "У тебя еще нет заполненной анкеты. Нажми «✏️ Заполнить анкету заново», чтобы создать её!",
            reply_markup=get_main_menu()
        )

# ================= ПОДДЕРЖКА =================

@dp.message(F.text == "💬 Поддержка")
async def support_start(message: types.Message, state: FSMContext):
    await state.set_state(States.waiting_for_support)
    await message.answer(
        "💬 **Служба поддержки**\n\n"
        "Напиши свой вопрос одним сообщением, и администратор ответит тебе.",
        reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True)
    )

@dp.message(F.text == "❌ Отмена", States.waiting_for_support)
async def support_cancel(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Обращение отменено.", reply_markup=get_main_menu())

@dp.message(States.waiting_for_support)
async def support_send_to_admin(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    username = f"@{message.from_user.username}" if message.from_user.username else f"ID: {user_id}"

    admin_text = (
        f"📩 **Новое обращение!**\n\n"
        f"👤 От: {username}\n"
        f"🆔 ID пользователя: `{user_id}`\n\n"
        f"💬 Текст: {message.text}"
    )

    try:
        await bot.send_message(ADMIN_ID, admin_text, parse_mode="Markdown")
        await message.answer("✅ Твое сообщение успешно отправлено поддержке!", reply_markup=get_main_menu())
    except Exception:
        await message.answer("⚠️ Не удалось отправить сообщение.", reply_markup=get_main_menu())
    
    await state.clear()

@dp.message(F.chat.id == ADMIN_ID)
async def admin_reply_to_user(message: types.Message):
    if message.reply_to_message:
        reply_text = message.reply_to_message.text
        if "🆔 ID пользователя:" in reply_text:
            try:
                for line in reply_text.split("\n"):
                    if "🆔 ID пользователя:" in line:
                        target_user_id = int(line.replace("🆔 ID пользователя:", "").replace("`", "").strip())
                        await bot.send_message(target_user_id, f"💬 **Ответ от поддержки:**\n\n{message.text}")
                        await message.reply("✅ Ответ отправлен!")
                        return
            except Exception as e:
                await message.reply(f"⚠️ Ошибка: {e}")

# ================= ПОИСК СОБЕСЕДНИКА =================

@dp.message(F.text == "🔍 Начать поиск собеседника")
async def start_search(message: types.Message):
    user_id = message.from_user.id
    if user_id in active_chats:
        await message.answer("Ты уже в диалоге! Сначала заверши его.", reply_markup=get_chat_menu())
        return

    if user_id in search_queue:
        await message.answer("⏳ Ты уже ищешь собеседника...", reply_markup=get_chat_menu())
        return

    if user_id not in user_profiles:
        await message.answer("⚠️ Сначала заполни анкету!", reply_markup=get_main_menu())
        return

    search_queue.append(user_id)
    
    if len(search_queue) >= 2:
        search_queue.remove(user_id)
        partner_id = search_queue.pop(0)
        
        active_chats[user_id] = partner_id
        active_chats[partner_id] = user_id

        p1 = user_profiles.get(user_id, {})
        p2 = user_profiles.get(partner_id, {})

        try:
            await bot.send_message(user_id, f"🎉 Собеседник найден!\nПол: {p2.get('gender')}, {p2.get('age')} лет\nИнтерес: {p2.get('interests')}\nОписание: {p2.get('bio')}", reply_markup=get_chat_menu())
            await bot.send_message(partner_id, f"🎉 Собеседник найден!\nПол: {p1.get('gender')}, {p1.get('age')} лет\nИнтерес: {p1.get('interests')}\nОписание: {p1.get('bio')}", reply_markup=get_chat_menu())
        except:
            pass
        return

    await message.answer("🔍 Ищем тебе случайного собеседника (18+)...", reply_markup=get_chat_menu())

@dp.message(F.text == "🛑 Остановить диалог")
async def stop_chat(message: types.Message):
    user_id = message.from_user.id
    
    if user_id in search_queue:
        search_queue.remove(user_id)
        await message.answer("❌ Поиск остановлен.", reply_markup=get_main_menu())
        return

    if user_id in active_chats:
        partner_id = active_chats.pop(user_id)
        if partner_id in active_chats:
            active_chats.pop(partner_id)
        
        await message.answer("🛑 Диалог завершен.", reply_markup=get_main_menu())
        try:
            await bot.send_message(partner_id, "🛑 Собеседник покинул чат.", reply_markup=get_main_menu())
        except:
            pass
    else:
        await message.answer("Ты не находишься в диалоге.", reply_markup=get_main_menu())

# Пересылка сообщений в активном чате
@dp.message()
async def forward_messages(message: types.Message):
    user_id = message.from_user.id
    if user_id in active_chats:
        partner_id = active_chats[user_id]
        try:
            await message.copy_to(partner_id)
        except Exception:
            await message.answer("⚠️ Не удалось отправить сообщение собеседнику.")

async def main():
    print("Бот успешно запущен!")
    await dp.start_polling(bot, drop_pending_updates=True)

if __name__ == '__main__':
    asyncio.run(main())
