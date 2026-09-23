import asyncio
import logging
import sqlite3
import time
from aiogram import Bot, Dispatcher, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, LabeledPrice

TOKEN = "8861156320:AAGOPPoi7mE9zZLH2DL8xp26N1SLKUQONuM"
ADMIN_ID = 6681923689  # Твой числовой Telegram ID

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
            [KeyboardButton(text="🔍 Поиск по полу (Премиум)")],
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
    await message.answer("👋 Привет! Создадим твою анкету.\n\nУкажи свой пол:", reply_markup=markup)
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
    if is_premium:
        if premium_expires > time.time():
            if premium_expires - time.time() > 10 * 365 * 86400:
                prem_status = "💎 Активен (Навсегда)"
            else:
                left_seconds = int(premium_expires - time.time())
                if left_seconds < 86400:
                    hours = left_seconds // 3600
                    prem_status = f"💎 Активен (еще {hours} ч.)"
                else:
                    days_left = left_seconds // 86400
                    prem_status = f"💎 Активен (еще {days_left} дн.)"
        else:
            conn = sqlite3.connect("users_db.db")
            conn.cursor().execute("UPDATE users SET is_premium = 0 WHERE user_id = ?", (user_id,))
            conn.commit()
            conn.close()

    await message.answer(
        f"📄 **Твоя анкета:**\n\n"
        f"👤 Пол: {gender}\n"
        f"🎂 Возраст: {age}\n"
        f"✨ Интересы: {interests}\n"
        f"⭐ Репутация: {reputation}\n"
        f"💎 Премиум: {prem_status}",
        reply_markup=get_main_menu()
    )

@dp.message(F.text == "💎 Премиум-статус")
@dp.message(F.text == "/premium")
async def premium_info(message: types.Message):
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐ 1 час — 10 Stars", callback_data="buy_star_hour")],
        [InlineKeyboardButton(text="⭐ 1 день — 35 Stars", callback_data="buy_star_day")],
        [InlineKeyboardButton(text="⭐ 1 неделя — 150 Stars", callback_data="buy_star_week")],
        [InlineKeyboardButton(text="⭐ 1 месяц — 400 Stars", callback_data="buy_star_month")],
        [InlineKeyboardButton(text="⭐ 1 год — 2000 Stars", callback_data="buy_star_year")],
        [InlineKeyboardButton(text="⭐ Навсегда — 4000 Stars", callback_data="buy_star_forever")]
    ])
    await message.answer(
        "💎 **Премиум-возможности в боте:**\n\n"
        "• Выбор пола собеседника при поиске 🎯\n"
        "• Приоритетный поиск собеседников 🚀\n"
        "• Особый значок в анкете ✨\n\n"
        "Выбери подходящий тариф за Telegram Stars:",
        reply_markup=markup
    )

@dp.callback_query(F.data.startswith("buy_star_"))
async def process_buy_stars(callback: types.CallbackQuery):
    tariff = callback.data.replace("buy_star_", "")
    tariffs_data = {
        "hour": ("Премиум на 1 час", 10),
        "day": ("Премиум на 1 день", 35),
        "week": ("Премиум на 1 неделю", 150),
        "month": ("Премиум на 1 месяц", 400),
        "year": ("Премиум на 1 год", 2000),
        "forever": ("Премиум навсегда", 4000)
    }
    title, price = tariffs_data.get(tariff, ("Премиум на 1 неделю", 150))
    
    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title=title,
        description="Покупка премиум-статуса в анонимном чате.",
        payload=f"prem_{tariff}",
        currency="XTR",
        prices=[LabeledPrice(label="Telegram Stars", amount=price)]
    )
    await callback.answer()

@dp.pre_checkout_query()
async def pre_checkout_handler(pre_checkout_query: types.PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@dp.message(F.successful_payment)
async def successful_payment_handler(message: types.Message):
    payload = message.successful_payment.invoice_payload
    user_id = message.from_user.id
    current_time = time.time()
    
    durations = {
        "prem_hour": 3600,
        "prem_day": 86400,
        "prem_week": 7 * 86400,
        "prem_month": 30 * 86400,
        "prem_year": 365 * 86400,
        "prem_forever": 36500 * 86400
    }
    add_time = durations.get(payload, 7 * 86400)
    
    conn = sqlite3.connect("users_db.db")
    cursor = conn.cursor()
    cursor.execute("SELECT premium_expires FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    
    current_expires = row[0] if row and row[0] > current_time else current_time
    new_expires = current_expires + add_time
    
    cursor.execute("UPDATE users SET is_premium = 1, premium_expires = ? WHERE user_id = ?", (new_expires, user_id))
    conn.commit()
    conn.close()
    
    await message.answer("🎉 Успешно! Твой премиум-статус активирован.", reply_markup=get_main_menu())

@dp.message(F.text == "/give")
async def admin_give_premium_to_self(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    
    user_id = message.from_user.id
    expires_time = time.time() + (3650 * 86400)  # Навсегда
    
    conn = sqlite3.connect("users_db.db")
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE users 
        SET is_premium = 1, premium_expires = ? 
        WHERE user_id = ?
    """, (expires_time, user_id))
    conn.commit()
    conn.close()

    await message.answer("💎 Премиум-статус успешно выдан тебе навсегда!", parse_mode="Markdown", reply_markup=get_main_menu())

@dp.message(F.text == "📢 Наш Telegram-канал")
async def channel_info(message: types.Message):
    await message.answer(
        "📢 **Наш официальный Telegram-канал:**\n\n"
        "👉 Подписывайся: https://t.me/anonimnyichat_ru_channel",
        reply_markup=get_main_menu()
    )

# Поддержка через бота (без показа личного аккаунта)
@dp.message(F.text == "💬 Поддержка")
async def support_handler(message: types.Message, state: FSMContext):
    await message.answer(
        "💬 Возникли вопросы или проблемы?\n\n"
        "Напиши свой вопрос или проблему следующим сообщением, и оно будет отправлено администратору:"
    )
    await state.set_state(SupportState.waiting_for_message)

@dp.message(SupportState.waiting_for_message)
async def send_support_message(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    username = f"@{message.from_user.username}" if message.from_user.username else f"id: {user_id}"

    support_text = (
        f"💬 **Новое обращение в поддержку!**\n\n"
        f"👤 От кого: {username} (`{user_id}`)\n"
        f"📄 Текст: {message.text}"
    )
    
    try:
        await bot.send_message(ADMIN_ID, support_text)
    except Exception:
        pass

    await message.answer("✅ Твое сообщение успешно отправлено администратору!", reply_markup=get_main_menu())
    await state.clear()

@dp.message(F.text == "✏️ Заполнить анкету заново")
@dp.message(F.text == "/edit")
async def cmd_edit_profile(message: types.Message, state: FSMContext):
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🙋‍♂️ Парень", callback_data="gender_male"),
            InlineKeyboardButton(text="🙋‍♀️ Девушка", callback_data="gender_female")
        ]
    ])
    await message.answer("🔄 Давай обновим твою анкету.\n\nУкажи свой пол:", reply_markup=markup)
    await state.set_state(ProfileState.waiting_for_gender)

@dp.callback_query(F.data.startswith("gender_"), ProfileState.waiting_for_gender)
async def process_gender(callback: types.CallbackQuery, state: FSMContext):
    gender = "Парень" if callback.data == "gender_male" else "Девушка"
    await state.update_data(gender=gender, selected_interests=[])
    
    await callback.message.edit_text(f"Пол выбран: {gender}\n\nТеперь введи свой возраст цифрой (строго от 18 лет):")
    await state.set_state(ProfileState.waiting_for_age)
    await callback.answer()

@dp.message(ProfileState.waiting_for_age)
async def process_age(message: types.Message, state: FSMContext):
    if not message.text or not message.text.isdigit() or not (18 <= int(message.text) <= 99):
        await message.answer("⚠️ Ошибка! Доступ разрешен только с 18 лет. Введи корректный возраст:")
        return

    await state.update_data(age=int(message.text))
    await state.set_state(ProfileState.waiting_for_interests)
    await send_interests_message(message, state, "Отлично! Теперь выбери интересы (можно выбрать от 1 до 5):")

async def send_interests_message(message_or_callback, state: FSMContext, text: str):
    data = await state.get_data()
    selected = data.get("selected_interests", [])

    buttons = []
    for interest in INTERESTS:
        btn_text = f"✅ {interest}" if interest in selected else interest
        buttons.append([InlineKeyboardButton(text=btn_text, callback_data=f"interest_{interest}")])
    
    buttons.append([InlineKeyboardButton(text="🚀 Готово (сохранить анкету)", callback_data="interests_done")])
    markup = InlineKeyboardMarkup(inline_keyboard=buttons)

    if isinstance(message_or_callback, types.CallbackQuery):
        try:
            await message_or_callback.message.edit_text(text, reply_markup=markup)
        except Exception:
            await message_or_callback.message.answer(text, reply_markup=markup)
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
            await callback.answer("⚠️ Можно выбрать максимум 5 интересов!", show_alert=True)
            return
        selected.append(interest)

    await state.update_data(selected_interests=selected)
    await send_interests_message(callback, state, f"Выбрано интересов: {len(selected)}. Жми еще или «Готово»:")
    await callback.answer()

@dp.callback_query(F.data == "interests_done", ProfileState.waiting_for_interests)
async def process_interests_done(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    user_id = callback.from_user.id
    gender = data.get("gender")
    age = data.get("age")
    interests = data.get("selected_interests", [])

    if not interests:
        await callback.answer("⚠️ Выбери хотя бы один интерес перед сохранением!", show_alert=True)
        return

    interests_str = ", ".join(interests)
    
    conn = sqlite3.connect("users_db.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO users (user_id, gender, age, interests, status, partner_id, reputation, chat_start_time)
        VALUES (?, ?, ?, ?, 'idle', 0, 0, 0)
        ON CONFLICT(user_id) DO UPDATE SET
        gender=excluded.gender,
        age=excluded.age,
        interests=excluded.interests,
        status='idle'
    """, (user_id, gender, age, interests_str))
    conn.commit()
    conn.close()

    await callback.answer("Анкета успешно сохранена!")
    try:
        await callback.message.delete()
    except Exception:
        pass

    await callback.message.answer(
        f"🎉 Твоя анкета готова!\n\n"
        f"👤 Пол: {gender}\n"
        f"🎂 Возраст: {age}\n"
        f"✨ Интересы: {interests_str}\n\n"
        f"Всё готово к общению! Нажми кнопку ниже 👇",
        reply_markup=get_main_menu()
    )
    await state.clear()

@dp.message(F.text == "🔍 Поиск по полу (Премиум)")
async def search_by_gender_menu(message: types.Message):
    user_id = message.from_user.id
    current_time = time.time()
    
    conn = sqlite3.connect("users_db.db")
    cursor = conn.cursor()
    cursor.execute("SELECT is_premium, premium_expires, status FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        await message.answer("Сначала заполни анкету с помощью /start")
        return

    is_premium, premium_expires, status = row[0], row[1], row[2]

    if is_premium and premium_expires < current_time:
        conn = sqlite3.connect("users_db.db")
        conn.cursor().execute("UPDATE users SET is_premium = 0 WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()
        is_premium = 0

    if not is_premium:
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💎 Купить Премиум", callback_data="open_prem_menu")]
        ])
        await message.answer(
            "🔒 **Функция доступна только с Премиум-статусом!**\n\n"
            "Приобрети премиум, чтобы выбирать, с кем именно начать общение.",
            reply_markup=markup
        )
        return

    if status == 'chatting':
        await message.answer("⚠️ Ты уже общаешься с кем-то! Сначала заверши текущий диалог.")
        return

    markup = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🙋‍♂️ Парень", callback_data="target_gender_Парень"),
            InlineKeyboardButton(text="🙋‍♀️ Девушка", callback_data="target_gender_Девушка")
        ]
    ])
    await message.answer("🎯 Выбери, какого пола собеседника ты хочешь найти:", reply_markup=markup)

@dp.callback_query(F.data == "open_prem_menu")
async def open_prem_from_inline(callback: types.CallbackQuery):
    await premium_info(callback.message)
    await callback.answer()

@dp.callback_query(F.data.startswith("target_gender_"))
async def process_target_gender(callback: types.CallbackQuery):
    target_gender = callback.data.replace("target_gender_", "")
    user_id = callback.from_user.id
    current_time = time.time()

    conn = sqlite3.connect("users_db.db")
    cursor = conn.cursor()
    cursor.execute("SELECT gender, age, interests, reputation, is_premium FROM users WHERE user_id = ?", (user_id,))
    user_row = cursor.fetchone()
    if not user_row:
        conn.close()
        await callback.message.answer("⚠️ Сначала заполни анкету.")
        return

    my_gender, my_age, my_interests, my_rep, my_prem = user_row

    cursor.execute("""
        SELECT user_id, gender, age, interests, reputation 
        FROM users 
        WHERE status = 'searching' AND user_id != ? AND gender = ? 
        ORDER BY is_premium DESC 
        LIMIT 1
    """, (user_id, target_gender))
    partner = cursor.fetchone()

    stop_menu = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🛑 Остановить поиск")]],
        resize_keyboard=True
    )

    if partner:
        partner_id, p_gender, p_age, p_interests, p_rep = partner
        
        cursor.execute("UPDATE users SET status = 'chatting', partner_id = ?, chat_start_time = ? WHERE user_id = ?", (partner_id, current_time, user_id))
        cursor.execute("UPDATE users SET status = 'chatting', partner_id = ?, chat_start_time = ? WHERE user_id = ?", (user_id, current_time, partner_id))
        conn.commit()
        conn.close()

        await callback.message.edit_text(f"🎉 Собеседник ({target_gender}) успешно найден!")
        
        await bot.send_message(
            user_id,
            f"🎉 Собеседник найден!\n\n"
            f"👤 Пол: {p_gender}\n"
            f"🎂 Возраст: {p_age}\n"
            f"✨ Интересы: {p_interests}\n"
            f"⭐ Репутация: {p_rep}\n\n"
            f"⏱ Через 1 минуту общения здесь появится возможность поделиться ссылкой на свой аккаунт.",
            reply_markup=get_chat_control_menu()
        )
        
        await bot.send_message(
            partner_id,
            f"🎉 Собеседник найден!\n\n"
            f"👤 Пол: {my_gender}\n"
            f"🎂 Возраст: {my_age}\n"
            f"✨ Интересы: {my_interests}\n"
            f"⭐ Репутация: {my_rep}\n\n"
            f"⏱ Через 1 минуту общения здесь появится возможность поделиться ссылкой на свой аккаунт.",
            reply_markup=get_chat_control_menu()
        )
    else:
        cursor.execute("UPDATE users SET status = 'searching' WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()

        await callback.message.edit_text(f"⏳ Ищем собеседника ({target_gender})...")
        await bot.send_message(user_id, "Ожидаем подходящего кандидата...", reply_markup=stop_menu)

    await callback.answer()

@dp.message(F.text == "🔍 Начать поиск собеседника")
async def start_search(message: types.Message):
    user_id = message.from_user.id
    current_time = time.time()
    
    conn = sqlite3.connect("users_db.db")
    cursor = conn.cursor()
    
    cursor.execute("SELECT status, gender, age, interests, is_premium, premium_expires, reputation FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        await message.answer("Сначала заполни анкету с помощью /start")
        return
        
    if row[0] == 'chatting':
        conn.close()
        await message.answer("⚠️ Ты уже общаешься с кем-то! Сначала заверши текущий диалог.")
        return

    my_gender, my_age, my_interests, my_prem, my_prem_exp, my_rep = row[1], row[2], row[3], row[4], row[5], row[6]

    if my_prem and my_prem_exp < current_time:
        cursor.execute("UPDATE users SET is_premium = 0 WHERE user_id = ?", (user_id,))
        conn.commit()
        my_prem = 0

    cursor.execute("SELECT user_id, gender, age, interests, reputation FROM users WHERE status = 'searching' AND user_id != ? ORDER BY is_premium DESC LIMIT 1", (user_id,))
    partner = cursor.fetchone()

    stop_menu = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🛑 Остановить поиск")]],
        resize_keyboard=True
    )

    if partner:
        partner_id, p_gender, p_age, p_interests, p_rep = partner[0], partner[1], partner[2], partner[3], partner[4]
        
        cursor.execute("UPDATE users SET status = 'chatting', partner_id = ?, chat_start_time = ? WHERE user_id = ?", (partner_id, current_time, user_id))
        cursor.execute("UPDATE users SET status = 'chatting', partner_id = ?, chat_start_time = ? WHERE user_id = ?", (user_id, current_time, partner_id))
        conn.commit()
        conn.close()

        await message.answer(
            f"🎉 Собеседник найден!\n\n"
            f"👤 Пол: {p_gender}\n"
            f"🎂 Возраст: {p_age}\n"
            f"✨ Интересы: {p_interests}\n"
            f"⭐ Репутация: {p_rep}\n\n"
            f"⏱ Через 1 минуту общения здесь появится возможность поделиться ссылкой на свой аккаунт.",
            reply_markup=get_chat_control_menu()
        )
        
        await bot.send_message(
            partner_id,
            f"🎉 Собеседник найден!\n\n"
            f"👤 Пол: {my_gender}\n"
            f"🎂 Возраст: {my_age}\n"
            f"✨ Интересы: {my_interests}\n"
            f"⭐ Репутация: {my_rep}\n\n"
            f"⏱ Через 1 минуту общения здесь появится возможность поделиться ссылкой на свой аккаунт.",
            reply_markup=get_chat_control_menu()
        )
    else:
        cursor.execute("UPDATE users SET status = 'searching' WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()
        await message.answer("⏳ Ищем подходящего собеседника...", reply_markup=stop_menu)

@dp.message(F.text == "🛑 Остановить поиск")
async def stop_search(message: types.Message):
    user_id = message.from_user.id
    conn = sqlite3.connect("users_db.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET status = 'idle' WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
    await message.answer("❌ Поиск отменен.", reply_markup=get_main_menu())

# Функционал подарков
@dp.message(F.text == "🎁 Подарить подарок")
async def choose_gift(message: types.Message):
    user_id = message.from_user.id
    conn = sqlite3.connect("users_db.db")
    cursor = conn.cursor()
    cursor.execute("SELECT status, partner_id FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()

    if not row or row[0] != 'chatting':
        await message.answer("⚠️ Ты можешь дарить подарки только во время активного диалога.")
        return

    markup = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🌹 Роза (⭐ 5)", callback_data="send_gift_rose"),
            InlineKeyboardButton(text="🍫 Шоколад (⭐ 10)", callback_data="send_gift_choco")
        ],
        [
            InlineKeyboardButton(text="🧸 Мишка (⭐ 25)", callback_data="send_gift_bear"),
            InlineKeyboardButton(text="💎 Алмаз (⭐ 50)", callback_data="send_gift_diamond")
        ]
    ])
    await message.answer("🎁 Выбери подарок для своего собеседника:", reply_markup=markup)

@dp.callback_query(F.data.startswith("send_gift_"))
async def process_send_gift(callback: types.CallbackQuery):
    gift_type = callback.data.replace("send_gift_", "")
    user_id = callback.from_user.id
    
    gifts_info = {
        "rose": ("🌹 Роза", 5),
        "choco": ("🍫 Шоколад", 10),
        "bear": ("🧸 Мишка", 25),
        "diamond": ("💎 Алмаз", 50)
    }
    gift_name, price = gifts_info.get(gift_type, ("🎁 Подарок", 5))

    conn = sqlite3.connect("users_db.db")
    cursor = conn.cursor()
    cursor.execute("SELECT partner_id FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    
    if not row or not row[0]:
        conn.close()
        await callback.answer("⚠️ Собеседник не найден.", show_alert=True)
        return
        
    partner_id = row[0]
    cursor.execute("UPDATE users SET reputation = reputation + ? WHERE user_id = ?", (price // 5, partner_id))
    conn.commit()
    conn.close()

    await callback.message.edit_text(f"Ты успешно отправил(а) подарок: {gift_name}!")
    await bot.send_message(partner_id, f"🎁 Тебе прилетел подарок от собеседника: **{gift_name}**! 💖")
    await callback.answer()

@dp.message(F.text == "🔗 Оставить ссылку на профиль")
async def share_profile(message: types.Message):
    user_id = message.from_user.id
    current_time = time.time()

    conn = sqlite3.connect("users_db.db")
    cursor = conn.cursor()
    cursor.execute("SELECT status, partner_id, chat_start_time FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()

    if not row or row[0] != 'chatting':
        await message.answer("⚠️ Ты не находишься в активном чате.")
        return

    partner_id = row[1]
    start_time = row[2]

    if current_time - start_time < 60:
        remaining = int(60 - (current_time - start_time))
        await message.answer(f"⏳ Рано! Общаться нужно хотя бы 1 минуту. Подожди еще {remaining} секунд.")
        return

    user = await bot.get_chat(user_id)
    profile_link = f"@{user.username}" if user.username else f"tg://user?id={user_id}"

    await message.answer("✅ Ты отправил свою ссылку на профиль собеседнику.")
    await bot.send_message(partner_id, f"✨ Собеседник поделился своим контактом: {profile_link}")

@dp.message(F.text == "❌ Завершить диалог")
async def stop_chat(message: types.Message):
    user_id = message.from_user.id
    conn = sqlite3.connect("users_db.db")
    cursor = conn.cursor()
    
    cursor.execute("SELECT partner_id FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    
    partner_id = 0
    if row and row[0]:
        partner_id = row[0]
        cursor.execute("UPDATE users SET status = 'idle', partner_id = 0, chat_start_time = 0 WHERE user_id = ?", (partner_id,))
        
        rate_markup_partner = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="👍 Хорошо", callback_data=f"rate_good_{user_id}"),
                InlineKeyboardButton(text="👎 Плохо", callback_data=f"rate_bad_{user_id}")
            ],
            [
                InlineKeyboardButton(text="🚨 Пожаловаться админам", callback_data=f"complaint_{user_id}")
            ]
        ])
        
        await bot.send_message(partner_id, "😢 Собеседник завершил диалог.", reply_markup=get_main_menu())
        await bot.send_message(partner_id, "Оцени общение или отправь жалобу:", reply_markup=rate_markup_partner)

    cursor.execute("UPDATE users SET status = 'idle', partner_id = 0, chat_start_time = 0 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
    
    rate_markup_user = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👍 Хорошо", callback_data=f"rate_good_{partner_id}"),
            InlineKeyboardButton(text="👎 Плохо", callback_data=f"rate_bad_{partner_id}")
        ],
        [
            InlineKeyboardButton(text="🚨 Пожаловаться админам", callback_data=f"complaint_{partner_id}")
        ]
    ])

    await message.answer("❌ Диалог завершен.", reply_markup=get_main_menu())
    await message.answer("Оцени общение или отправь жалобу:", reply_markup=rate_markup_user)

@dp.callback_query(F.data.startswith("rate_"))
async def process_rating(callback: types.CallbackQuery):
    data_parts = callback.data.split("_")
    action = data_parts[1]
    target_user_id = int(data_parts[2]) if len(data_parts) > 2 and data_parts[2].isdigit() else 0
    
    conn = sqlite3.connect("users_db.db")
    cursor = conn.cursor()

    if action == "good":
        if target_user_id:
            cursor.execute("UPDATE users SET reputation = reputation + 1 WHERE user_id = ?", (target_user_id,))
            conn.commit()
        await callback.message.edit_text("👍 Спасибо за оценку! Репутация собеседника повышена.")
    else:
        if target_user_id:
            cursor.execute("UPDATE users SET reputation = reputation - 1 WHERE user_id = ?", (target_user_id,))
            conn.commit()
        await callback.message.edit_text("👎 Спасибо за оценку.")
        
    conn.close()
    await callback.answer()

@dp.callback_query(F.data.startswith("complaint_"))
async def process_complaint_start(callback: types.CallbackQuery, state: FSMContext):
    target_user_id = callback.data.split("_")[1]
    await state.update_data(target_user_id=target_user_id)
    await state.set_state(ProfileState.waiting_for_complaint)
    
    await callback.message.edit_text("🚨 Напиши текстом причину жалобы на собеседника:")
    await callback.answer()

@dp.message(ProfileState.waiting_for_complaint)
async def process_complaint_send(message: types.Message, state: FSMContext):
    data = await state.get_data()
    target_user_id = data.get("target_user_id")
    reporter_id = message.from_user.id
    reporter_username = f"@{message.from_user.username}" if message.from_user.username else f"id: {reporter_id}"

    if target_user_id and target_user_id.isdigit():
        conn = sqlite3.connect("users_db.db")
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET reputation = reputation - 5 WHERE user_id = ?", (int(target_user_id),))
        conn.commit()
        conn.close()

    complaint_text = (
        f"🚨 **Новая жалоба на пользователя!**\n\n"
        f"👤 От кого: {reporter_username} (`{reporter_id}`)\n"
        f"🎯 Нарушитель (ID): `{target_user_id}`\n"
        f"📄 Причина: {message.text}"
    )
    
    try:
        await bot.send_message(ADMIN_ID, complaint_text)
    except Exception:
        pass

    await message.answer("✅ Жалоба успешно отправлена администраторам.", reply_markup=get_main_menu())
    await state.clear()

@dp.message()
async def pass_messages(message: types.Message):
    user_id = message.from_user.id
    
    ignore_texts = [
        "🔍 Начать поиск собеседника", 
        "🔍 Поиск по полу (Премиум)",
        "🛑 Остановить поиск", 
        "❌ Завершить диалог", 
        "🔗 Оставить ссылку на профиль", 
        "🎁 Подарить подарок",
        "✏️ Заполнить анкету заново",
        "📄 Посмотреть мою анкету",
        "💎 Премиум-статус",
        "📢 Наш Telegram-канал",
        "💬 Поддержка"
    ]
    
    if message.text in ignore_texts:
        return

    conn = sqlite3.connect("users_db.db")
    cursor = conn.cursor()
    cursor.execute("SELECT status, partner_id FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()

    if row and row[0] == 'chatting' and row[1]:
        partner_id = row[1]
        try:
            await message.copy_to(partner_id)
        except Exception:
            await message.answer("⚠️ Не удалось отправить сообщение собеседнику.")

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
