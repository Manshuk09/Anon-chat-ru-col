import asyncio
import logging
import sqlite3
import time
from aiogram import Bot, Dispatcher, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    InlineKeyboardMarkup, 
    InlineKeyboardButton, 
    ReplyKeyboardMarkup, 
    KeyboardButton,
    LabeledPrice,
    PreCheckoutQuery
)

TOKEN = "8861156320:AAEd_G2uA0GfNEifOzawEnLAFFFTov-1FHA"
ADMIN_ID = 123456789  # ⚠️ Замени на свой числовой Telegram ID

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

def get_main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔍 Начать поиск собеседника")],
            [KeyboardButton(text="📄 Посмотреть мою анкету"), KeyboardButton(text="✏️ Заполнить анкету заново")],
            [KeyboardButton(text="💎 PREMIUM"), KeyboardButton(text="📢 Наш Telegram-канал")]
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
    cursor.execute("SELECT gender, age, interests, reputation, is_premium FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        await message.answer("⚠️ У тебя еще нет анкеты. Нажми /start, чтобы создать ее.")
        return

    gender, age, interests, reputation, is_premium = row
    status_text = "💎 Активен" if is_premium else "❌ Обычный"
    
    await message.answer(
        f"📄 **Твоя анкета:**\n\n"
        f"👤 Пол: {gender}\n"
        f"🎂 Возраст: {age}\n"
        f"✨ Интересы: {interests}\n"
        f"⭐ Репутация: {reputation}\n"
        f"💎 Статус: {status_text}",
        reply_markup=get_main_menu()
    )

@dp.message(F.text == "💎 PREMIUM")
@dp.message(F.text == "/premium")
async def show_premium_menu(message: types.Message):
    text = (
        "Общайся с 💎 PREMIUM без ограничений!\n\n"
        "👫 Поиск по полу\n"
        "👥 Видишь пол и возраст собеседника\n"
        "💎 Твой PREMIUM-статус виден всем\n"
        "⚡ Быстрый поиск и никакой рекламы"
    )
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Купить PREMIUM (1 месяц) — 150 ⭐", callback_data="buy_stars_1month")],
        [InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="main_menu_callback")]
    ])
    await message.answer(text, reply_markup=markup)

@dp.callback_query(F.data == "main_menu_callback")
async def back_to_menu_cb(callback: types.CallbackQuery):
    await callback.message.delete()
    await callback.message.answer("Главное меню:", reply_markup=get_main_menu())
    await callback.answer()

@dp.callback_query(F.data == "buy_stars_1month")
async def process_buy_stars(callback: types.CallbackQuery, bot: Bot):
    prices = [LabeledPrice(label="PREMIUM на 1 месяц", amount=150)]
    
    await bot.send_invoice(
        chat_id=callback.message.chat.id,
        title="PREMIUM подписка",
        description="Доступ ко всем премиум-функциям бота на 1 месяц без ограничений.",
        payload="premium_1_month",
        provider_token="",  # Для Telegram Stars всегда пусто
        currency="XTR",     # Валюта Telegram Stars
        prices=prices,
    )
    await callback.answer()

@dp.pre_checkout_query()
async def process_pre_checkout_query(pre_checkout_query: PreCheckoutQuery, bot: Bot):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@dp.message(F.successful_payment)
async def process_successful_payment(message: types.Message):
    payment_info = message.successful_payment
    user_id = message.from_user.id
    
    expires_at = time.time() + (30 * 24 * 60 * 60) # 30 дней
    
    conn = sqlite3.connect("users_db.db")
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE users SET is_premium = 1, premium_expires = ? WHERE user_id = ?
    """, (expires_at, user_id))
    conn.commit()
    conn.close()

    await message.answer(
        "🎉 **Оплата прошла успешно!**\n\n"
        f"Списано: {payment_info.total_amount} ⭐\n"
        "Твой статус **💎 PREMIUM** активирован на 1 месяц. Приятного общения!",
        reply_markup=get_main_menu()
    )

@dp.message(F.text == "📢 Наш Telegram-канал")
async def channel_info(message: types.Message):
    await message.answer(
        "📢 **Наш официальный Telegram-канал:**\n\n"
        "Здесь будут публиковаться новости, обновления и анонсы бота!\n\n"
        "👉 Подписывайся: https://t.me/anonimnyichat_ru_channel",
        reply_markup=get_main_menu()
    )

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

@dp.message(F.text == "🔍 Начать поиск собеседника")
async def start_search(message: types.Message):
    user_id = message.from_user.id
    current_time = time.time()
    
    conn = sqlite3.connect("users_db.db")
    cursor = conn.cursor()
    
    cursor.execute("SELECT status, gender, age, interests, is_premium FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        await message.answer("Сначала заполни анкету с помощью /start")
        return
        
    if row[0] == 'chatting':
        conn.close()
        await message.answer("⚠️ Ты уже общаешься с кем-то! Сначала заверши текущий диалог.")
        return

    my_gender, my_age, my_interests, my_is_premium = row[1], row[2], row[3], row[4]

    cursor.execute("SELECT user_id, gender, age, interests, reputation, is_premium FROM users WHERE status = 'searching' AND user_id != ? LIMIT 1", (user_id,))
    partner = cursor.fetchone()

    stop_menu = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🛑 Остановить поиск")]],
        resize_keyboard=True
    )

    if partner:
        partner_id, p_gender, p_age, p_interests, p_rep, p_is_premium = partner[0], partner[1], partner[2], partner[3], partner[4], partner[5]
        
        cursor.execute("UPDATE users SET status = 'chatting', partner_id = ?, chat_start_time = ? WHERE user_id = ?", (partner_id, current_time, user_id))
        cursor.execute("UPDATE users SET status = 'chatting', partner_id = ?, chat_start_time = ? WHERE user_id = ?", (user_id, current_time, partner_id))
        conn.commit()
        conn.close()

        chat_control_menu = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="🔗 Оставить ссылку на профиль")],
                [KeyboardButton(text="❌ Завершить диалог")]
            ],
            resize_keyboard=True
        )

        my_badge = " 💎 PREMIUM" if my_is_premium else ""
        p_badge = " 💎 PREMIUM" if p_is_premium else ""

        await message.answer(
            f"🎉 Собеседник найден!{p_badge}\n\n"
            f"👤 Пол: {p_gender}\n"
            f"🎂 Возраст: {p_age}\n"
            f"✨ Интересы: {p_interests}\n"
            f"⭐ Репутация: {p_rep}\n\n"
            f"⏱ Через 1 минуту общения здесь появится возможность поделиться ссылкой на свой аккаунт.",
            reply_markup=chat_control_menu
        )
        
        await bot.send_message(
            partner_id,
            f"🎉 Собеседник найден!{my_badge}\n\n"
            f"👤 Пол: {my_gender}\n"
            f"🎂 Возраст: {my_age}\n"
            f"✨ Интересы: {my_interests}\n"
            f"⭐ Репутация: {row[4] if len(row) > 4 else 0}\n\n"
            f"⏱ Через 1 минуту общения здесь появится возможность поделиться ссылкой на свой аккаунт.",
            reply_markup=chat_control_menu
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
    if user.username:
        profile_link = f"@{user.username}"
    else:
        profile_link = f"tg://user?id={user_id}"

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
        "🛑 Остановить поиск", 
        "❌ Завершить диалог", 
        "🔗 Оставить ссылку на профиль", 
        "✏️ Заполнить анкету заново",
        "📄 Посмотреть мою анкету",
        "💎 PREMIUM",
        "📢 Наш Telegram-канал"
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
    print("Бот запущен и готов к работе!")
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
