import asyncio
import logging
import sqlite3
import time
from aiogram import Bot, Dispatcher, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, LabeledPrice

TOKEN = "8934594855:AAGOKofRKqQb1oGvq0qEDqV9AjoWtkfbo3M"
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
            [KeyboardButton(text="🎯 Поиск по полу (Премиум)")],
            [KeyboardButton(text="📄 Посмотреть мою анкету"), KeyboardButton(text="✏️ Заполнить анкету заново")],
            [KeyboardButton(text="💎 Премиум-статус"), KeyboardButton(text="📢 Наш Telegram-канал")],
            [KeyboardButton(text="💬 Поддержка")]
        ],
        resize_keyboard=True
    )

def get_chat_control_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎁 Отправить подарок (Telegram)")],
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
    if is_premium and premium_expires > time.time():
        prem_status = "💎 Активен"

    await message.answer(
        f"📄 **Твоя анкета:**\n\n👤 Пол: {gender}\n🎂 Возраст: {age}\n✨ Интересы: {interests}\n⭐ Репутация: {reputation}\n💎 Премиум: {prem_status}",
        reply_markup=get_main_menu()
    )

@dp.message(F.text == "💎 Премиум-статус")
@dp.message(F.text == "/premium")
async def premium_info(message: types.Message):
    text = (
        "💎 **Премиум-статус в Анонимном чате**\n\n"
        "Что дает Премиум:\n"
        "✨ **Поиск собеседника по полу**\n"
        "✨ Приоритет при поиске\n"
        "✨ Отправка ссылок без ожидания таймера\n"
        "✨ Эксклюзивный значок в профиле\n\n"
        "🏷 **Прайс-лист (Telegram Stars):**\n"
        "⭐ **1 час** — 10 Stars\n"
        "⭐ **1 день** — 30 Stars\n"
        "⭐ **1 неделя** — 150 Stars\n"
        "⭐ **1 месяц** — 450 Stars\n"
        "⭐ **1 год** — 1500 Stars\n"
        "⭐ **Навсегда** — 4000 Stars\n\n"
        "Выбери подходящий тариф:"
    )
    
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐ 1 час (10 🌟)", callback_data="buy_star_hour"), InlineKeyboardButton(text="⭐ 1 день (30 🌟)", callback_data="buy_star_day")],
        [InlineKeyboardButton(text="⭐ 1 неделя (150 🌟)", callback_data="buy_star_week"), InlineKeyboardButton(text="⭐ 1 месяц (450 🌟)", callback_data="buy_star_month")],
        [InlineKeyboardButton(text="⭐ 1 год (1500 🌟)", callback_data="buy_star_year"), InlineKeyboardButton(text="⭐ Навсегда (4000 🌟)", callback_data="buy_star_forever")]
    ])
    
    await message.answer(text, reply_markup=markup, parse_mode="Markdown")

@dp.callback_query(F.data.startswith("buy_star_"))
async def process_buy_stars(callback: types.CallbackQuery):
    tariff = callback.data.replace("buy_star_", "")
    
    prices_map = {
        "hour": (10, "Премиум на 1 час"),
        "day": (30, "Премиум на 1 день"),
        "week": (150, "Премиум на 1 неделю"),
        "month": (450, "Премиум на 1 месяц"),
        "year": (1500, "Премиум на 1 год"),
        "forever": (4000, "Премиум навсегда")
    }
    
    price, title = prices_map.get(tariff, (150, "Премиум"))
    
    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title=title,
        description=f"Покупка тарифа: {title}",
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
    payload = message.successful_payment.invoice_payload
    
    durations = {
        "prem_hour": 3600,
        "prem_day": 86400,
        "prem_week": 7 * 86400,
        "prem_month": 30 * 86400,
        "prem_year": 365 * 86400,
        "prem_forever": 3650 * 86400
    }
    
    duration = durations.get(payload, 7 * 86400)
    
    conn = sqlite3.connect("users_db.db")
    cursor = conn.cursor()
    cursor.execute("SELECT premium_expires FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    current_expires = row[0] if row and row[0] > time.time() else time.time()
    
    new_expires = current_expires + duration
    cursor.execute("UPDATE users SET is_premium = 1, premium_expires = ? WHERE user_id = ?", (new_expires, user_id))
    conn.commit()
    conn.close()
    
    await message.answer("🎉 Ура! Премиум-статус успешно активирован!", reply_markup=get_main_menu())

@dp.message(F.text == "/give")
async def admin_give(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    conn = sqlite3.connect("users_db.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET is_premium = 1, premium_expires = ? WHERE user_id = ?", (time.time() + 3650*86400, message.from_user.id))
    conn.commit()
    conn.close()
    await message.answer("💎 Премиум выдан навсегда админу!")

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

@dp.message(F.text == "🎯 Поиск по полу (Премиум)")
async def gender_search_menu(message: types.Message):
    user_id = message.from_user.id
    conn = sqlite3.connect("users_db.db")
    cursor = conn.cursor()
    cursor.execute("SELECT is_premium, premium_expires FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()

    is_prem = row and row[0] == 1 and row[1] > time.time()

    if not is_prem:
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💎 Купить Премиум", callback_data="buy_prem_redirect")]
        ])
        await message.answer("🔒 **Функция доступна только с Премиум-статусом!**\n\nПоиск собеседника определенного пола открывается сразу после покупки Премиума.", reply_markup=markup)
        return

    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🙋‍♂️ Найти парня", callback_data="search_gender_Парень"), InlineKeyboardButton(text="🙋‍♀️ Найти девушку", callback_data="search_gender_Девушка")]
    ])
    await message.answer("🎯 Выбери, кого хочешь найти:", reply_markup=markup)

@dp.callback_query(F.data == "buy_prem_redirect")
async def redirect_to_prem(callback: types.CallbackQuery):
    await callback.message.delete()
    await premium_info(callback.message)
    await callback.answer()

@dp.message(F.text == "🔍 Начать поиск собеседника")
async def start_search(message: types.Message):
    await process_general_search(message, target_gender=None)

async def process_general_search(message: types.Message, target_gender=None):
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
    
    if target_gender:
        cursor.execute("SELECT user_id, gender, age, interests, reputation FROM users WHERE status = 'searching' AND gender = ? AND user_id != ? LIMIT 1", (target_gender, user_id))
    else:
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
        await message.answer("⏳ Ищем подходящего собеседника...", reply_markup=stop_menu)

@dp.callback_query(F.data.startswith("search_gender_"))
async def callback_gender_search(callback: types.CallbackQuery):
    target_gender = callback.data.replace("search_gender_", "")
    await callback.message.delete()
    await process_general_search(callback.message, target_gender=target_gender)
    await callback.answer()

@dp.message(F.text == "🛑 Остановить поиск")
async def stop_search(message: types.Message):
    conn = sqlite3.connect("users_db.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET status = 'idle' WHERE user_id = ?", (message.from_user.id,))
    conn.commit()
    conn.close()
    await message.answer("❌ Поиск отменен.", reply_markup=get_main_menu())

@dp.message(F.text == "🎁 Отправить подарок (Telegram)")
async def choose_telegram_gift(message: types.Message):
    conn = sqlite3.connect("users_db.db")
    cursor = conn.cursor()
    cursor.execute("SELECT partner_id FROM users WHERE user_id = ?", (message.from_user.id,))
    row = cursor.fetchone()
    conn.close()

    if not row or not row[0]:
        await message.answer("⚠️ Ты не находишься в чате с собеседником.")
        return

    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎁 Звездный подарок 1 (⭐ 15)", callback_data="send_tg_gift_1")],
        [InlineKeyboardButton(text="🎁 Звездный подарок 2 (⭐ 25)", callback_data="send_tg_gift_2")]
    ])
    await message.answer("🎁 Выбери подарок для отправки собеседнику через Telegram:", reply_markup=markup)

@dp.callback_query(F.data.startswith("send_tg_gift_"))
async def process_send_tg_gift(callback: types.CallbackQuery):
    gift_id = callback.data.replace("send_tg_gift_", "")
    
    conn = sqlite3.connect("users_db.db")
    cursor = conn.cursor()
    cursor.execute("SELECT partner_id FROM users WHERE user_id = ?", (callback.from_user.id,))
    row = cursor.fetchone()
    conn.close()

    if not row or not row[0]:
        await callback.answer("⚠️ Собеседник уже вышел из чата.", show_alert=True)
        return

    partner_id = row[0]
    try:
        await bot.send_gift(user_id=partner_id, gift_id=gift_id)
        await callback.message.edit_text("🎁 Настоящий Telegram-подарок успешно отправлен собеседнику!")
        await bot.send_message(partner_id, "🎁 Тебе пришел подарок от собеседника в Telegram!")
    except Exception:
        await callback.message.edit_text("⚠️ Не удалось отправить подарок.\nВозможно, у бота недостаточно Stars или подарок недоступен.")
    
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
    user_id = message.from_user.id
    conn = sqlite3.connect("users_db.db")
    cursor = conn.cursor()
    cursor.execute("SELECT partner_id FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    
    partner_id = row[0] if row else 0

    if partner_id:
        cursor.execute("UPDATE users SET status = 'idle', partner_id = 0, chat_start_time = 0 WHERE user_id = ?", (partner_id,))
        
        rate_markup_partner = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="👍 Хорошо", callback_data=f"rate_up_{user_id}"),
                InlineKeyboardButton(text="👎 Плохо", callback_data=f"rate_down_{user_id}")
            ],
            [InlineKeyboardButton(text="🚨 Пожаловаться", callback_data=f"complaint_{user_id}")]
        ])
        await bot.send_message(partner_id, "😢 Собеседник завершил диалог. Оцени его:", reply_markup=rate_markup_partner)

    cursor.execute("UPDATE users SET status = 'idle', partner_id = 0, chat_start_time = 0 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

    rate_markup_self = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👍 Хорошо", callback_data=f"rate_up_{partner_id}"),
            InlineKeyboardButton(text="👎 Плохо", callback_data=f"rate_down_{partner_id}")
        ],
        [InlineKeyboardButton(text="🚨 Пожаловаться", callback_data=f"complaint_{partner_id}")] if partner_id else []
    ])
    await message.answer("❌ Диалог завершен. Оцени собеседника:", reply_markup=rate_markup_self)
    await message.answer("Главное меню:", reply_markup=get_main_menu())

@dp.callback_query(F.data.startswith("rate_"))
async def process_rating(callback: types.CallbackQuery):
    data_parts = callback.data.split("_")
    action = data_parts[1]
    target_id = int(data_parts[2])

    if target_id:
        conn = sqlite3.connect("users_db.db")
        cursor = conn.cursor()
        points = 1 if action == "up" else -1
        cursor.execute("UPDATE users SET reputation = reputation + ? WHERE user_id = ?", (points, target_id))
        conn.commit()
        conn.close()

    await callback.message.edit_text("Спасибо за твою оценку!")
    await callback.answer()

@dp.callback_query(F.data.startswith("complaint_"))
async def process_complaint_start(callback: types.CallbackQuery, state: FSMContext):
    target_id = callback.data.replace("complaint_", "")
    await state.update_data(complaint_target=target_id)
    await callback.message.answer("⚠️ Напиши причину жалобы следующим сообщением:")
    await state.set_state(ProfileState.waiting_for_complaint)
    await callback.answer()

@dp.message(ProfileState.waiting_for_complaint)
async def process_complaint_finish(message: types.Message, state: FSMContext):
    data = await state.get_data()
    target_id = data.get("complaint_target")
    
    try:
        await bot.send_message(ADMIN_ID, f"🚨 **Жалоба на пользователя** `{target_id}` от `{message.from_user.id}`:\n{message.text}")
    except Exception:
        pass

    await message.answer("✅ Жалоба отправлена администратору. Спасибо!", reply_markup=get_main_menu())
    await state.clear()

@dp.message()
async def pass_messages(message: types.Message):
    if message.text in ["🔍 Начать поиск собеседника", "🎯 Поиск по полу (Премиум)", "🛑 Остановить поиск", "❌ Завершить диалог", "🔗 Оставить ссылку на профиль", "🎁 Отправить подарок (Telegram)", "✏️ Заполнить анкету заново", "📄 Посмотреть мою анкету", "💎 Премиум-статус", "📢 Наш Telegram-канал", "💬 Поддержка"]:
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
 
