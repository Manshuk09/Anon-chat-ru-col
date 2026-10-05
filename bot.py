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
            last_partner_id INTEGER DEFAULT 0,
            reputation INTEGER DEFAULT 0,
            chat_start_time REAL DEFAULT 0,
            is_premium INTEGER DEFAULT 0,
            premium_expires REAL DEFAULT 0,
            registration_time REAL DEFAULT 0
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

def check_is_premium(user_id: int) -> bool:
    conn = sqlite3.connect("users_db.db")
    cursor = conn.cursor()
    cursor.execute("SELECT is_premium, premium_expires FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row and row[0] == 1 and row[1] > time.time():
        return True
    return False

def get_main_menu(user_id: int):
    is_prem = check_is_premium(user_id)
    prem_btn_text = "💎 Премиум (Активен)" if is_prem else "💎 Премиум-статус"
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔍 Начать поиск собеседника")],
            [KeyboardButton(text="🎯 Поиск по полу (Премиум)"), KeyboardButton(text="🔄 Вернуть собеседника")],
            [KeyboardButton(text="📄 Посмотреть мою анкету"), KeyboardButton(text="✏️ Заполнить анкету заново")],
            [KeyboardButton(text=prem_btn_text), KeyboardButton(text="💬 Поддержка")]
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
    user_id = message.from_user.id
    current_time = time.time()
    
    conn = sqlite3.connect("users_db.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    
    if not user:
        cursor.execute("INSERT OR IGNORE INTO users (user_id, status, registration_time) VALUES (?, 'idle', ?)", (user_id, current_time))
        conn.commit()
    conn.close()

    if user and user[1]:
        await message.answer("Ты уже зарегистрирована! Нажми кнопку ниже, чтобы начать общение:", reply_markup=get_main_menu(user_id))
        return

    markup = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🙋‍♂️ Парень", callback_data="gender_male"),
            InlineKeyboardButton(text="🙋‍♀️ Девушка", callback_data="gender_female")
        ]
    ])
    await message.answer("👋 Привет! Этот бот предназначен только для пользователей 18+.\n\nСоздадим твою анкету. Укажи свой пол:", reply_markup=markup)
    await state.set_state(ProfileState.waiting_for_gender)

@dp.message(F.text == "📄 Посмотреть мою анкету")
async def show_my_profile(message: types.Message):
    user_id = message.from_user.id
    conn = sqlite3.connect("users_db.db")
    cursor = conn.cursor()
    cursor.execute("SELECT gender, age, interests, reputation, is_premium, premium_expires FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()

    if not row or not row[0]:
        await message.answer("⚠️ У тебя еще нет заполненной анкеты. Нажми /start, чтобы создать ее.")
        return

    gender, age, interests, reputation, is_premium, premium_expires = row
    
    prem_status = "❌ Отсутствует"
    if is_premium and premium_expires > time.time():
        prem_status = "💎 Активен (👑 Премиум)"

    await message.answer(
        f"📄 **Твоя анкета (18+):**\n\n👤 Пол: {gender}\n🎂 Возраст: {age}\n✨ Интересы: {interests}\n⭐ Репутация: {reputation}\n💎 Премиум: {prem_status}",
        reply_markup=get_main_menu(user_id)
    )

@dp.message(F.text.in_({"💎 Премиум-статус", "💎 Премиум (Активен)"}))
@dp.message(F.text == "/premium")
async def premium_info(message: types.Message):
    user_id = message.from_user.id
    is_prem = check_is_premium(user_id)
    status_text = "💎 Статус: **АКТИВЕН** ✅" if is_prem else "💎 Статус: **ОТСУТСТВУЕТ** ❌"
    
    text = (
        f"{status_text}\n\n"
        "**Преимущества Премиум-подписки:**\n"
        "✨ **Поиск собеседника по полу**\n"
        "🚀 **VIP-очередь** (соединение в приоритете)\n"
        "👑 **Корона и значок** в профиле и начале чата\n"
        "⏳ **Отправка ссылок без ожидания таймера** (можно сразу)\n"
        "🔄 **Возврат собеседника** при сбросе\n"
        "🎯 **Расширенные интересы** (до 10 вместо 5)\n\n"
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
    
    await message.answer("🎉 Ура! Премиум-статус успешно активирован!", reply_markup=get_main_menu(user_id))

@dp.message(F.text == "/give")
async def admin_give(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    conn = sqlite3.connect("users_db.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET is_premium = 1, premium_expires = ? WHERE user_id = ?", (time.time() + 3650*86400, message.from_user.id))
    conn.commit()
    conn.close()
    await message.answer("💎 Премиум выдан навсегда админу!", reply_markup=get_main_menu(message.from_user.id))

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
    await message.answer("✅ Отправлено!", reply_markup=get_main_menu(message.from_user.id))
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
        await message.answer("⚠️ Бот строго 18+. Введи корректный возраст от 18 лет:")
        return
    await state.update_data(age=int(message.text))
    await state.set_state(ProfileState.waiting_for_interests)
    
    user_id = message.from_user.id
    max_limit = 10 if check_is_premium(user_id) else 5
    await send_interests_message(message, state, f"Выбери интересы (до {max_limit}):")

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
    
    user_id = callback.from_user.id
    max_limit = 10 if check_is_premium(user_id) else 5

    if interest in selected:
        selected.remove(interest)
    else:
        if len(selected) >= max_limit:
            await callback.answer(f"⚠️ Для твоего статуса максимум {max_limit} интересов!", show_alert=True)
            return
        selected.append(interest)
        
    await state.update_data(selected_interests=selected)
    await send_interests_message(callback, state, f"Выбрано: {len(selected)} (лимит: {max_limit}). Жми Готово:")
    await callback.answer()

@dp.callback_query(F.data == "interests_done", ProfileState.waiting_for_interests)
async def process_interests_done(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    user_id = callback.from_user.id
    gender = data.get("gender")
    age = data.get("age")
    selected_interests = data.get("selected_interests", [])
    current_time = time.time()
    
    if not selected_interests:
        await callback.answer("⚠️ Выбери хотя бы один интерес!", show_alert=True)
        return

    interests = ", ".join(selected_interests)

    conn = sqlite3.connect("users_db.db")
    cursor = conn.cursor()
    cursor.execute("SELECT registration_time FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    reg_time = row[0] if row and row[0] > 0 else current_time

    cursor.execute("""
        UPDATE users SET gender = ?, age = ?, interests = ?, status = 'idle', registration_time = ?
        WHERE user_id = ?
    """, (gender, age, interests, reg_time, user_id))
    conn.commit()
    conn.close()

    await state.clear()

    try:
        await callback.message.edit_text("🎉 Анкета успешно сохранена! Всё готово к общению:")
    except Exception:
        pass
        
    await callback.message.answer("Главное меню:", reply_markup=get_main_menu(user_id))
    await callback.answer()

@dp.message(F.text == "🎯 Поиск по полу (Премиум)")
async def gender_search_menu(message: types.Message):
    user_id = message.from_user.id
    if not check_is_premium(user_id):
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
    is_prem = check_is_premium(user_id)
    
    conn = sqlite3.connect("users_db.db")
    cursor = conn.cursor()
    cursor.execute("SELECT status, gender, age, interests, reputation FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    
    if not row or not row[1]:
        conn.close()
        await message.answer("Сначала заполни анкету через /start")
        return
    if row[0] == 'chatting':
        conn.close()
        await message.answer("⚠️ Ты уже в чате!")
        return

    my_gender, my_age, my_interests, my_rep = row[1], row[2], row[3], row[4]
    
    if target_gender:
        cursor.execute("SELECT user_id, gender, age, interests, reputation, is_premium FROM users WHERE status = 'searching' AND gender = ? AND user_id != ? ORDER BY is_premium DESC LIMIT 1", (target_gender, user_id))
    else:
        cursor.execute("SELECT user_id, gender, age, interests, reputation, is_premium FROM users WHERE status = 'searching' AND user_id != ? ORDER BY is_premium DESC LIMIT 1", (user_id,))
        
    partner = cursor.fetchone()
    stop_menu = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="🛑 Остановить поиск")]], resize_keyboard=True)

    if partner:
        partner_id, p_gender, p_age, p_interests, p_rep, p_is_prem = partner
        
        cursor.execute("UPDATE users SET status = 'chatting', partner_id = ?, last_partner_id = ?, chat_start_time = ? WHERE user_id = ?", (partner_id, partner_id, current_time, user_id))
        cursor.execute("UPDATE users SET status = 'chatting', partner_id = ?, last_partner_id = ?, chat_start_time = ? WHERE user_id = ?", (user_id, user_id, current_time, partner_id))
        conn.commit()
        conn.close()

        my_crown = "👑 " if is_prem else ""
        partner_crown = "👑 " if p_is_prem else ""

        await message.answer(f"🎉 {my_crown}Собеседник найден!\nПол: {p_gender}, Возраст: {p_age}\nИнтересы: {p_interests}", reply_markup=get_chat_control_menu())
        await bot.send_message(partner_id, f"🎉 {partner_crown}Собеседник найден!\nПол: {my_gender}, Возраст: {my_age}\nИнтересы: {my_interests}", reply_markup=get_chat_control_menu())
    else:
        cursor.execute("UPDATE users SET status = 'searching' WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()
        queue_text = "🚀 VIP-поиск собеседника..." if is_prem else "⏳ Ищем подходящего собеседника..."
        await message.answer(queue_text, reply_markup=stop_menu)

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
    await message.answer("❌ Поиск отменен.", reply_markup=get_main_menu(message.from_user.id))

@dp.message(F.text == "🔄 Вернуть собеседника")
async def return_last_partner(message: types.Message):
    user_id = message.from_user.id
    if not check_is_premium(user_id):
        await message.answer("🔒 Функция возврата собеседника доступна только с **Премиум-статусом**!", reply_markup=get_main_menu(user_id))
        return

    conn = sqlite3.connect("users_db.db")
    cursor = conn.cursor()
    cursor.execute("SELECT status, last_partner_id FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()

    if not row or row[0] == 'chatting':
        conn.close()
        await message.answer("⚠️ Ты уже в активном чате или не с кем возобновлять связь.")
        return

    last_partner_id = row[1]
    if not last_partner_id:
        conn.close()
        await message.answer("⚠️ У тебя нет предыдущего собеседника для возврата.")
        return

    cursor.execute("SELECT status FROM users WHERE user_id = ?", (last_partner_id,))
    p_row = cursor.fetchone()
    
    if not p_row or p_row[0] != 'idle':
        conn.close()
        await message.answer("⚠️ К сожалению, прошлый собеседник уже занят или вышел из бота.")
        return

    current_time = time.time()
    cursor.execute("UPDATE users SET status = 'chatting', partner_id = ?, chat_start_time = ? WHERE user_id = ?", (last_partner_id, current_time, user_id))
    cursor.execute("UPDATE users SET status = 'chatting', partner_id = ?, chat_start_time = ? WHERE user_id = ?", (user_id, current_time, last_partner_id))
    conn.commit()
    conn.close()

    await message.answer("🔄 Собеседник успешно возвращен в чат!", reply_markup=get_chat_control_menu())
    await bot.send_message(last_partner_id, "🔄 Премиум-собеседник восстановил чат с тобой!", reply_markup=get_chat_control_menu())

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
    user_id = message.from_user.id
    is_prem = check_is_premium(user_id)

    conn = sqlite3.connect("users_db.db")
    cursor = conn.cursor()
    cursor.execute("SELECT partner_id, chat_start_time FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()

    if not row or not row[0]:
        await message.answer("⚠️ Ты не в чате.")
        return
    
    if not is_prem and (time.time() - row[1] < 60):
        await message.answer("⏳ Подожди хотя бы 1 минуту общения перед отправкой ссылки (или купи Премиум для отправки без ожидания).")
        return

    user = await bot.get_chat(user_id)
    link = f"@{user.username}" if user.username else f"tg://user?id={user_id}"
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
    await message.answer("Главное меню:", reply_markup=get_main_menu(user_id))

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

    await callback.message.edit_text("Спасибо за твою оценку! Репутация обновлена ⭐")
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

    await message.answer("✅ Жалоба отправлена администратору. Спасибо!", reply_markup=get_main_menu(message.from_user.id))
    await state.clear()

@dp.message(F.text == "/stats")
async def admin_stats(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
        
    conn = sqlite3.connect("users_db.db")
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM users WHERE status = 'searching'")
    searching_users = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM users WHERE status = 'chatting'")
    chatting_users = cursor.fetchone()[0]
    
    current_time = time.time()
    cursor.execute("SELECT COUNT(*) FROM users WHERE is_premium = 1 AND premium_expires > ?", (current_time,))
    premium_users = cursor.fetchone()[0]
    
    day_ago = current_time - 86400
    cursor.execute("SELECT COUNT(*) FROM users WHERE registration_time > ?", (day_ago,))
    new_users_24h = cursor.fetchone()[0]
    
    conn.close()
    
    await message.answer(
        f"📊 **Подробная статистика бота:**\n\n"
        f"👥 **Всего зарегистрировано:** `{total_users}`\n"
        f"🆕 **Новых за 24 часа:** `{new_users_24h}`\n"
        f"⏳ **Ищут собеседника:** `{searching_users}`\n"
        f"💬 **Общаются в чатах:** `{chatting_users}` (👥 `{chatting_users // 2}` пар)\n"
        f"💎 **Активных Премиумов:** `{premium_users}`",
        parse_mode="Markdown"
    )

@dp.message()
async def pass_messages(message: types.Message):
    if message.text in ["/stats", "🔍 Начать поиск собеседника", "🎯 Поиск по полу (Премиум)", "🔄 Вернуть собеседника", "🛑 Остановить поиск", "❌ Завершить диалог", "🔗 Оставить ссылку на профиль", "🎁 Отправить подарок (Telegram)", "✏️ Заполнить анкету заново", "📄 Посмотреть мою анкету", "💎 Премиум-статус", "💎 Премиум (Активен)", "💬 Поддержка"]:
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
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
