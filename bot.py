import asyncio
import logging
import sqlite3
import time
from aiogram import Bot, Dispatcher, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, LabeledPrice

TOKEN = "ТВОЙ_АКТУАЛЬНЫЙ_ТОКЕН"
ADMIN_ID = 6681923689

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()

def init_db():
    conn = sqlite3.connect("users_db.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            gender TEXT,
            age INTEGER,
            interests TEXT,
            status TEXT DEFAULT 'idle',
            partner_id INTEGER DEFAULT 0,
            reputation INTEGER DEFAULT 0,
            chat_start_time REAL DEFAULT 0,
            is_premium INTEGER DEFAULT 0,
            premium_expires REAL DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

init_db()

INTERESTS = [
    "🎨 Рисование", "💻 Программирование", "🎮 Игры", 
    "🎬 Аниме & Манга", "🎧 Музыка", "📚 Книги & Манхва", 
    "🥋 Боевые искусства", "🍕 Кулинария", 
    "🐾 Животные", "🔮 Таро & Эзотерика", "📸 Видеомонтаж"
]

class ProfileState(StatesGroup):
    waiting_for_gender = State()
    waiting_for_age = State()
    waiting_for_interests = State()
    waiting_for_complaint = State()

class SupportState(StatesGroup):
    waiting_for_message = State()

def get_main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔍 Начать поиск собеседника")],
            [KeyboardButton(text="📄 Посмотреть мою анкету"), KeyboardButton(text="✏️ Заполнить анкету заново")],
            [KeyboardButton(text="💎 Премиум-статус"), KeyboardButton(text="📢 Наш Telegram-канал")],
            [KeyboardButton(text="💬 Поддержка")]
        ],
        resize_keyboard=True
    )

def get_chat_control_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎁 Подарить подарок")],
            [KeyboardButton(text="🔗 Оставить ссылку на профиль")],
            [KeyboardButton(text="❌ Завершить диалог")]
        ],
        resize_keyboard=True
    )

# Исправленный /start (теперь проверяет наличие пользователя в БД)
@dp.message(F.text == "/start")
async def cmd_start(message: types.Message, state: FSMContext):
    conn = sqlite3.connect("users_db.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (message.from_user.id,))
    user = cursor.fetchone()
    conn.close()

    if user:
        await message.answer("Ты уже зарегистрирована! Нажми кнопку ниже, чтобы начать общение:", reply_markup=get_main_menu())
        return

    markup = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🙋‍♂️ Парень", callback_data="gender_male"),
            InlineKeyboardButton(text="🙋‍♀️ Девушка", callback_data="gender_female")
        ]
    ])
    await message.answer("👋 Привет! Создадим твоју анкету.\n\nУкажи свой пол:", reply_markup=markup)
    await state.set_state(ProfileState.waiting_for_gender)

@dp.message(F.text == "📄 Посмотреть мою анкету")
async def show_my_profile(message: types.Message):
    user_id = message.from_user.id
    conn = sqlite3.connect("users_db.db")
    cursor = conn.cursor()
    cursor.execute("SELECT gender, age, interests, reputation, is_premium, premium_expires FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        await message.answer("⚠️ У тебя еще нет анкеты. Нажми /start, чтобы создать ее.")
        return

    gender, age, interests, reputation, is_premium, premium_expires = row
    
    prem_status = "❌ Отсутствует"
    if is_premium and premium_expires > time.time():
        prem_status = "💎 Активен"

    await message.answer(
        f"📄 **Твоя анкета:**\n\n👤 Пол: {gender}\n🎂 Возраст: {age}\n✨ Интересы: {interests}\n⭐ Репутация: {reputation}\n💎 Премиум: {prem_status}",
        reply_markup=get_main_menu()
    )

@dp.message(F.text == "💎 Премиум-статус")
@dp.message(F.text == "/premium")
async def premium_info(message: types.Message):
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐ 1 неделя — 150 Stars", callback_data="buy_star_week")],
        [InlineKeyboardButton(text="⭐ Навсегда — 4000 Stars", callback_data="buy_star_forever")]
    ])
    await message.answer("💎 Выбери тариф Премиум за Telegram Stars:", reply_markup=markup)

@dp.callback_query(F.data.startswith("buy_star_"))
async def process_buy_stars(callback: types.CallbackQuery):
    tariff = callback.data.replace("buy_star_", "")
    price = 150 if tariff == "week" else 4000
    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title="Премиум-статус",
        description="Покупка премиума",
        payload=f"prem_{tariff}",
        currency="XTR",
        prices=[LabeledPrice(label="Stars", amount=price)]
    )
    await callback.answer()

@dp.pre_checkout_query()
async def pre_checkout_handler(query: types.PreCheckoutQuery):
    await bot.answer_pre_checkout_query(query.id, ok=True)

@dp.message(F.successful_payment)
async def successful_payment_handler(message: types.Message):
    user_id = message.from_user.id
    conn = sqlite3.connect("users_db.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET is_premium = 1, premium_expires = ? WHERE user_id = ?", (time.time() + 30*86400, user_id))
    conn.commit()
    conn.close()
    await message.answer("🎉 Премиум активирован!", reply_markup=get_main_menu())

@dp.message(F.text == "/give")
async def admin_give(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    conn = sqlite3.connect("users_db.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET is_premium = 1, premium_expires = ? WHERE user_id = ?", (time.time() + 3650*86400, message.from_user.id))
    conn.commit()
    conn.close()
    await message.answer("💎 Премиум выдан навсегда!")

@dp.message(F.text == "📢 Наш Telegram-канал")
async def channel_info(message: types.Message):
    await message.answer("📢 Наш канал: https://t.me/anonimnyichat_ru_channel", reply_markup=get_main_menu())

@dp.message(F.text == "💬 Поддержка")
async def support_handler(message: types.Message, state: FSMContext):
    await message.answer("💬 Напиши вопрос админу следующим сообщением:")
    await state.set_state(SupportState.waiting_for_message)

@dp.message(SupportState.waiting_for_message)
async def send_support_message(message: types.Message, state: FSMContext):
    try:
        await bot.send_message(ADMIN_ID, f"💬 Вопрос от `{message.from_user.id}`:\n{message.text}")
    except Exception:
        pass
    await message.answer("✅ Отправлено!", reply_markup=get_main_menu())
    await state.clear()

# Отдельный обработчик для пересоздания анкеты
@dp.message(F.text == "✏️ Заполнить анкету заново")
@dp.message(F.text == "/edit")
async def cmd_edit_profile(message: types.Message, state: FSMContext):
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🙋‍♂️ Парень", callback_data="gender_male"), InlineKeyboardButton(text="🙋‍♀️ Девушка", callback_data="gender_female")]
    ])
    await message.answer("Укажи свой пол:", reply_markup=markup)
    await state.set_state(ProfileState.waiting_for_gender)

@dp.callback_query(F.data.startswith("gender_"), ProfileState.waiting_for_gender)
async def process_gender(callback: types.CallbackQuery, state: FSMContext):
    gender = "Парень" if callback.data == "gender_male" else "Девушка"
    await state.update_data(gender=gender, selected_interests=[])
    await callback.message.edit_text("Введи свой возраст (цифрой от 18):")
    await state.set_state(ProfileState.waiting_for_age)
    await callback.answer()

@dp.message(ProfileState.waiting_for_age)
async def process_age(message: types.Message, state: FSMContext):
    if not message.text.isdigit() or not (18 <= int(message.text) <= 99):
        await message.answer("⚠️ Введи корректный возраст от 18 лет:")
        return
    await state.update_data(age=int(message.text))
    await state.set_state(ProfileState.waiting_for_interests)
    await send_interests_message(message, state, "Выбери интересы (от 1 до 5):")

async def send_interests_message(message_or_callback, state: FSMContext, text: str):
    data = await state.get_data()
    selected = data.get("selected_interests", [])
    buttons = []
    for interest in INTERESTS:
        btn_text = f"✅ {interest}" if interest in selected else interest
        buttons.append([InlineKeyboardButton(text=btn_text, callback_data=f"interest_{interest}")])
    buttons.append([InlineKeyboardButton(text="🚀 Готово", callback_data="interests_done")])
    markup = InlineKeyboardMarkup(inline_keyboard=buttons)
    if isinstance(message_or_callback, types.CallbackQuery):
        await message_or_callback.message.edit_text(text, reply_markup=markup)
    else:
        await message_or_callback.answer(text, reply_markup=markup)

@dp.callback_query(F.data.startswith("interest_"), ProfileState.waiting_for_interests)
async def process_interest_toggle(callback: types.CallbackQuery, state: FSMContext):
    interest = callback.data.replace("interest_", "")
    data = await state.get_data()
    selected = data.get("selected_interests", [])
    if interest in selected:
        selected.remove(interest)
    else:
        if len(selected) >= 5:
            await callback.answer("⚠️ Максимум 5 интересов!", show_alert=True)
            return
        selected.append(interest)
    await state.update_data(selected_interests=selected)
    await send_interests_message(callback, state, f"Выбрано: {len(selected)}. Жми Готово:")
    await callback.answer()

@dp.callback_query(F.data == "interests_done", ProfileState.waiting_for_interests)
async def process_interests_done(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    user_id = callback.from_user.id
    gender, age, interests = data.get("gender"), data.get("age"), ", ".join(data.get("selected_interests", []))
    
    if not interests:
        await callback.answer("⚠️ Выбери хотя бы один интерес!", show_alert=True)
        return

    conn = sqlite3.connect("users_db.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO users (user_id, gender, age, interests, status, partner_id, reputation, chat_start_time)
        VALUES (?, ?, ?, ?, 'idle', 0, 0, 0)
        ON CONFLICT(user_id) DO UPDATE SET gender=excluded.gender, age=excluded.age, interests=excluded.interests, status='idle'
    """, (user_id, gender, age, interests))
    conn.commit()
    conn.close()

    await callback.message.delete()
    await callback.message.answer("🎉 Анкета сохранена! Всё готово к общению:", reply_markup=get_main_menu())
    await state.clear()

@dp.message(F.text == "🔍 Начать поиск собеседника")
async def start_search(message: types.Message):
    user_id = message.from_user.id
    current_time = time.time()
    conn = sqlite3.connect("users_db.db")
    cursor = conn.cursor()
    cursor.execute("SELECT status, gender, age, interests, reputation FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    
    if not row:
        conn.close()
        await message.answer("Сначала заполни анкету через /start")
        return
    if row[0] == 'chatting':
        conn.close()
        await message.answer("⚠️ Ты уже в чате!")
        return

    my_gender, my_age, my_interests, my_rep = row[1], row[2], row[3], row[4]
    cursor.execute("SELECT user_id, gender, age, interests, reputation FROM users WHERE status = 'searching' AND user_id != ? LIMIT 1", (user_id,))
    partner = cursor.fetchone()

    stop_menu = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="🛑 Остановить поиск")]], resize_keyboard=True)

    if partner:
        partner_id, p_gender, p_age, p_interests, p_rep = partner
        cursor.execute("UPDATE users SET status = 'chatting', partner_id = ?, chat_start_time = ? WHERE user_id = ?", (partner_id, current_time, user_id))
        cursor.execute("UPDATE users SET status = 'chatting', partner_id = ?, chat_start_time = ? WHERE user_id = ?", (user_id, current_time, partner_id))
        conn.commit()
        conn.close()

        await message.answer(f"🎉 Собеседник найден!\nПол: {p_gender}, Возраст: {p_age}\nИнтересы: {p_interests}", reply_markup=get_chat_control_menu())
        await bot.send_message(partner_id, f"🎉 Собеседник найден!\nПол: {my_gender}, Возраст: {my_age}\nИнтересы: {my_interests}", reply_markup=get_chat_control_menu())
    else:
        cursor.execute("UPDATE users SET status = 'searching' WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()
        await message.answer("⏳ Ищем собеседника...", reply_markup=stop_menu)

@dp.message(F.text == "🛑 Остановить поиск")
async def stop_search(message: types.Message):
    conn = sqlite3.connect("users_db.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET status = 'idle' WHERE user_id = ?", (message.from_user.id,))
    conn.commit()
    conn.close()
    await message.answer("❌ Поиск отменен.", reply_markup=get_main_menu())

@dp.message(F.text == "🎁 Подарить подарок")
async def choose_gift(message: types.Message):
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌹 Роза (⭐ 5)", callback_data="gift_rose"), InlineKeyboardButton(text="🍫 Шоколад (⭐ 10)", callback_data="gift_choco")]
    ])
    await message.answer("🎁 Выбери подарок:", reply_markup=markup)

@dp.callback_query(F.data.startswith("gift_"))
async def process_gift(callback: types.CallbackQuery):
    conn = sqlite3.connect("users_db.db")
    cursor = conn.cursor()
    cursor.execute("SELECT partner_id FROM users WHERE user_id = ?", (callback.from_user.id,))
    row = cursor.fetchone()
    if row and row[0]:
        cursor.execute("UPDATE users SET reputation = reputation + 1 WHERE user_id = ?", (row[0],))
        conn.commit()
        await bot.send_message(row[0], "🎁 Тебе прилетел подарок!")
    conn.close()
    await callback.message.edit_text("Подарок отправлен!")
    await callback.answer()

@dp.message(F.text == "🔗 Оставить ссылку на профиль")
async def share_profile(message: types.Message):
    conn = sqlite3.connect("users_db.db")
    cursor = conn.cursor()
    cursor.execute("SELECT partner_id, chat_start_time FROM users WHERE user_id = ?", (message.from_user.id,))
    row = cursor.fetchone()
    conn.close()

    if not row or not row[0]:
        await message.answer("⚠️ Ты не в чате.")
        return
    if time.time() - row[1] < 60:
        await message.answer("⏳ Подожди хотя бы 1 минуту общения перед отправкой ссылки.")
        return

    user = await bot.get_chat(message.from_user.id)
    link = f"@{user.username}" if user.username else f"tg://user?id={message.from_user.id}"
    await message.answer("✅ Ссылка отправлена.")
    await bot.send_message(row[0], f"✨ Собеседник поделился контактом: {link}")

@dp.message(F.text == "❌ Завершить диалог")
async def stop_chat(message: types.Message):
    conn = sqlite3.connect("users_db.db")
    cursor = conn.cursor()
    cursor.execute("SELECT partner_id FROM users WHERE user_id = ?", (message.from_user.id,))
    row = cursor.fetchone()
    if row and row[0]:
        cursor.execute("UPDATE users SET status = 'idle', partner_id = 0, chat_start_time = 0 WHERE user_id = ?", (row[0],))
        await bot.send_message(row[0], "😢 Собеседник завершил диалог.", reply_markup=get_main_menu())
    cursor.execute("UPDATE users SET status = 'idle', partner_id = 0, chat_start_time = 0 WHERE user_id = ?", (message.from_user.id,))
    conn.commit()
    conn.close()
    await message.answer("❌ Диалог завершен.", reply_markup=get_main_menu())

@dp.message()
async def pass_messages(message: types.Message):
    if message.text in ["🔍 Начать поиск собеседника", "🛑 Остановить поиск", "❌ Завершить диалог", "🔗 Оставить ссылку на профиль", "🎁 Подарить подарок", "✏️ Заполнить анкету заново", "📄 Посмотреть мою анкету", "💎 Премиум-статус", "📢 Наш Telegram-канал", "💬 Поддержка"]:
        return
    
    conn = sqlite3.connect("users_db.db")
    cursor = conn.cursor()
    cursor.execute("SELECT status, partner_id FROM users WHERE user_id = ?", (message.from_user.id,))
    row = cursor.fetchone()
    conn.close()

    if row and row[0] == 'chatting' and row[1]:
        try:
            await message.copy_to(row[1])
        except Exception:
            await message.answer("⚠️ Не удалось доставить сообщение.")

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
