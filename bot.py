import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice

# ================= НАСТРОЙКИ =================
TOKEN = "8861156320:AAEd_G2uA0GfNEifOzawEnLAFFFTov-1FHA"  # Твой токен бота
ADMIN_ID = 6681923689                                   # Твой Telegram ID
PREMIUM_PRICE_STARS = 100                               # Стоимость премиума в Telegram Stars
# ============================================

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Хранилища
search_queue = []          # Обычная очередь
premium_queue = []         # Премиум-очередь (идет первой)
active_chats = {}          # Активные диалоги: {user_id: partner_id}
user_profiles = {}         # База анкет: {user_id: {"gender": ..., "target": ..., "age": ..., "interests": ..., "bio": ..., "is_premium": bool}}

# Состояния (FSM)
class States(StatesGroup):
    waiting_for_support = State()
    profile_gender = State()
    profile_target = State()
    profile_age = State()
    profile_interests = State()
    profile_bio = State()

# Главное меню
def get_main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔍 Начать поиск собеседника")],
            [KeyboardButton(text="📄 Посмотреть мою анкету"), KeyboardButton(text="✏️ Заполнить анкету заново")],
            [KeyboardButton(text="💎 PREMIUM"), KeyboardButton(text="💬 Поддержка")],
            [KeyboardButton(text="📢 Наш канал")]
        ],
        resize_keyboard=True
    )

# Меню во время активного диалога
def get_chat_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🛑 Остановить диалог")]
        ],
        resize_keyboard=True
    )

# 1. Команда /start
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
        "👋 Привет! Добро пожаловать в анонимный чат.\n\n"
        "Здесь ты можешь общаться с анонимными собеседниками, заводить новые знакомства и делиться мыслями.",
        reply_markup=get_main_menu()
    )

# 2. Кнопка "📢 Наш канал"
@dp.message(F.text == "📢 Наш канал")
async def channel_link(message: types.Message):
    await message.answer("📢 Наш официальный канал: https://t.me/anonimnyichat_ru_bot", reply_markup=get_main_menu())

# 3. Кнопка "💎 PREMIUM" (покупка за Звезды)
@dp.message(F.text == "💎 PREMIUM")
async def premium_info(message: types.Message):
    user_id = message.from_user.id
    is_prem = user_profiles.get(user_id, {}).get("is_premium", False)
    
    status_text = "✅ У тебя активирован **PREMIUM**!" if is_prem else "❌ У тебя стандартный статус."

    markup = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"⭐ Купить за {PREMIUM_PRICE_STARS} Звезд", callback_data="buy_prem_stars")]
        ]
    )

    await message.answer(
        f"💎 **PREMIUM-статус в боте**\n\n"
        f"{status_text}\n\n"
        "Что дает Премиум:\n"
        "• 🚀 **Приоритетный поиск** (тебя соединяют первыми)\n"
        "• 🎯 **Фильтр по полу** (выбор, кого именно искать при поиске)\n"
        "• ✨ **Уникальный значок** в профиле\n\n"
        "⭐️ *Нажми кнопку ниже, чтобы приобрести Премиум за Telegram Stars:*",
        reply_markup=markup
    )

@dp.callback_query(F.data == "buy_prem_stars")
async def process_buy_stars(callback: types.CallbackQuery):
    prices = [LabeledPrice(label="💎 Telegram Premium", amount=PREMIUM_PRICE_STARS)]
    
    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title="💎 Премиум-статус в боте",
        description="Покупка Premium-статуса: приоритетный поиск, фильтр по полу и значок в профиле.",
        payload="premium_stars_purchase",
        currency="XTR",
        prices=prices
    )
    await callback.answer()

@dp.pre_checkout_query()
async def process_pre_checkout_query(pre_checkout_query: types.PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@dp.message(F.successful_payment)
async def successful_payment(message: types.Message):
    user_id = message.from_user.id
    if user_id not in user_profiles:
        user_profiles[user_id] = {"gender": "👤 Парень", "target": "🌍 Всех", "age": "18", "interests": "🎨 Рисование", "bio": "Пусто", "is_premium": True}
    else:
        user_profiles[user_id]["is_premium"] = True
        
    await message.answer(
        "🎉 **Успешная оплата!**\nТебе автоматически активирован **PREMIUM-статус** ✨",
        reply_markup=get_main_menu()
    )

# Команда бесплатной выдачи премиума: /prem ID
@dp.message(F.text.startswith("/prem"))
async def admin_give_premium(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    
    parts = message.text.split()
    if len(parts) < 2:
        await message.reply("⚠️ Укажи ID пользователя. Пример: `/prem 123456789`", parse_mode="Markdown")
        return
    
    try:
        target_id = int(parts[1])
        if target_id not in user_profiles:
            user_profiles[target_id] = {"gender": "👤 Парень", "target": "🌍 Всех", "age": "18", "interests": "🎨 Рисование", "bio": "Пусто", "is_premium": True}
        else:
            user_profiles[target_id]["is_premium"] = True
            
        await message.reply(f"✅ Премиум успешно выдан пользователю `{target_id}` бесплатно!", parse_mode="Markdown")
        try:
            await bot.send_message(target_id, "🎉 Администратор активировал тебе **PREMIUM-статус** бесплатно! ✨", parse_mode="Markdown", reply_markup=get_main_menu())
        except:
            pass
    except Exception as e:
        await message.reply(f"⚠️ Ошибка: {e}")

# ================= РАЗДЕЛ АНКЕТ И ИНТЕРЕСОВ =================

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
    user_id = message.from_user.id
    is_prem = user_profiles.get(user_id, {}).get("is_premium", False)
    
    steps_total = "5" if is_prem else "4"
    await message.answer(f"📝 Шаг 1/{steps_total}: Укажи свой пол:", reply_markup=markup)

@dp.message(F.text == "❌ Отмена")
async def cancel_profile(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Действие отменено.", reply_markup=get_main_menu())

# Шаг 1: Пол выбирают ВСЕ
@dp.message(States.profile_gender, F.text.in_(["👤 Парень", "👧 Девушка"]))
async def profile_gender_chosen(message: types.Message, state: FSMContext):
    await state.update_data(gender=message.text)
    user_id = message.from_user.id
    is_prem = user_profiles.get(user_id, {}).get("is_premium", False)

    if is_prem:
        await state.set_state(States.profile_target)
        markup = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="🔎 Парня"), KeyboardButton(text="🔎 Девушку")],
                [KeyboardButton(text="🌍 Всех")],
                [KeyboardButton(text="❌ Отмена")]
            ],
            resize_keyboard=True
        )
        await message.answer("📝 Шаг 2/5: Кого ты хочешь искать?", reply_markup=markup)
    else:
        await state.update_data(target="🌍 Всех")
        await state.set_state(States.profile_age)
        await message.answer("📝 Шаг 2/4: Сколько тебе лет? (напиши цифрой)", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))

# Шаг 2 (только для премиума): Выбор кого искать
@dp.message(States.profile_target, F.text.in_(["🔎 Парня", "🔎 Девушку", "🌍 Всех"]))
async def profile_target_chosen(message: types.Message, state: FSMContext):
    await state.update_data(target=message.text)
    await state.set_state(States.profile_age)
    await message.answer("📝 Шаг 3/5: Сколько тебе лет? (напиши цифрой)", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))

# Шаг возраста
@dp.message(States.profile_age)
async def profile_age_chosen(message: types.Message, state: FSMContext):
    await state.update_data(age=message.text)
    await state.set_state(States.profile_interests)
    
    # Кнопки с твоими интересами
    markup = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎨 Рисование"), KeyboardButton(text="📖 Книги")],
            [KeyboardButton(text="🎬 Сериалы"), KeyboardButton(text="🌸 Аниме")],
            [KeyboardButton(text="⚽ Спорт"), KeyboardButton(text="💃 Танцы")],
            [KeyboardButton(text="🎵 Музыка"), KeyboardButton(text="💻 Программирование")],
            [KeyboardButton(text="❌ Отмена")]
        ],
        resize_keyboard=True
    )
    user_id = message.from_user.id
    is_prem = user_profiles.get(user_id, {}).get("is_premium", False)
    step_num = "4/5" if is_prem else "3/4"
    await message.answer(f"📝 Шаг {step_num}: Выбери свой главный интерес:", reply_markup=markup)

# Шаг интересов
@dp.message(States.profile_interests, F.text.in_(["🎨 Рисование", "📖 Книги", "🎬 Сериалы", "🌸 Аниме", "⚽ Спорт", "💃 Танцы", "🎵 Музыка", "💻 Программирование"]))
async def profile_interests_chosen(message: types.Message, state: FSMContext):
    await state.update_data(interests=message.text)
    await state.set_state(States.profile_bio)
    
    user_id = message.from_user.id
    is_prem = user_profiles.get(user_id, {}).get("is_premium", False)
    step_num = "5/5" if is_prem else "4/4"
    await message.answer(f"📝 Шаг {step_num}: Напиши пару слов о себе (описание):", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))

# Сохранение анкеты
@dp.message(States.profile_bio)
async def profile_bio_chosen(message: types.Message, state: FSMContext):
    data = await state.get_data()
    user_id = message.from_user.id
    
    is_prem = user_profiles.get(user_id, {}).get("is_premium", False)
    
    user_profiles[user_id] = {
        "gender": data["gender"],
        "target": data.get("target", "🌍 Всех"),
        "age": data["age"],
        "interests": data["interests"],
        "bio": message.text,
        "is_premium": is_prem
    }
    
    await state.clear()
    
    target_info = f"\n🎯 Кого ищет: {data.get('target')}" if is_prem else ""
    
    await message.answer(
        "✅ Анкета успешно заполнена и сохранена!\n\n"
        f"👤 Пол: {data['gender']}"
        f"{target_info}\n"
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
        prem_badge = " ✨ [PREMIUM]" if p.get("is_premium") else ""
        target_info = f"\n🎯 Кого ищет: {p['target']}" if p.get("is_premium") else ""
        await message.answer(
            f"📄 **Твоя анкета{prem_badge}:**\n\n"
            f"👤 Пол: {p['gender']}"
            f"{target_info}\n"
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

# ================= РАЗДЕЛ ПОДДЕРЖКИ =================

@dp.message(F.text == "💬 Поддержка")
async def support_start(message: types.Message, state: FSMContext):
    await state.set_state(States.waiting_for_support)
    await message.answer(
        "💬 **Служба поддержки**\n\n"
        "Напиши свой вопрос или предложение одним сообщением, и администратор ответит тебе.",
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
        f"📩 **Новое обращение в поддержку!**\n\n"
        f"👤 От: {username}\n"
        f"🆔 ID пользователя: `{user_id}`\n\n"
        f"💬 Текст: {message.text}"
    )

    try:
        await bot.send_message(ADMIN_ID, admin_text)
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
                await message.reply(f"⚠️ Ошибка при отправке: {e}")

# ================= ПОИСК СОБЕСЕДНИКА =================

@dp.message(F.text == "🔍 Начать поиск собеседника")
async def start_search(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id in active_chats:
        await message.answer("Ты уже в диалоге! Сначала заверши его.", reply_markup=get_chat_menu())
        return

    if user_id in search_queue or user_id in premium_queue:
        await message.answer("⏳ Ты уже ищешь собеседника...", reply_markup=get_chat_menu())
        return

    if user_id not in user_profiles:
        await message.answer("⚠️ Сначала заполни анкету!", reply_markup=get_main_menu())
        return

    user_data = user_profiles[user_id]
    is_prem = user_data.get("is_premium", False)

    # 1. ОБЫЧНЫЙ ПОЛЬЗОВАТЕЛЬ — случайный поиск
    if not is_prem:
        search_queue.append(user_id)
        
        if len(search_queue) >= 2:
            search_queue.remove(user_id)
            partner_id = search_queue.pop(0)
            
            active_chats[user_id] = partner_id
            active_chats[partner_id] = user_id

            p1 = user_profiles.get(user_id, {})
            p2 = user_profiles.get(partner_id, {})

            await bot.send_message(user_id, f"🎉 Собеседник найден!\nПол: {p2.get('gender')}, {p2.get('age')} лет\nИнтерес: {p2.get('interests')}\nОписание: {p2.get('bio')}", reply_markup=get_chat_menu())
            await bot.send_message(partner_id, f"🎉 Собеседник найден!\nПол: {p1.get('gender')}, {p1.get('age')} лет\nИнтерес: {p1.get('interests')}\nОписание: {p1.get('bio')}", reply_markup=get_chat_menu())
            return

        await message.answer("🔍 Ищем тебе случайного собеседника...", reply_markup=get_chat_menu())
        return

    # 2. ПРЕМИУМ-ПОЛЬЗОВАТЕЛЬ — поиск с фильтром по полу + приоритет
    target = user_data.get("target", "🌍 Всех")
    my_gender = user_data.get("gender", "👤 Парень")

    def match_found(queue):
        for index, candidate_id in enumerate(queue):
            cand_data = user_profiles.get(candidate_id, {})
            cand_target = cand_data.get("target", "🌍 Всех")
            cand_gender = cand_data.get("gender", "👤 Парень")

            my_target_match = (target == "🌍 Всех") or (target == "🔎 Парня" and cand_gender == "👤 Парень") or (target == "🔎 Девушку" and cand_gender == "👧 Девушка")
            cand_target_match = (cand_target == "🌍 Всех") or (cand_target == "🔎 Парня" and my_gender == "👤 Парень") or (cand_target == "🔎 Девушку" and my_gender == "👧 Девушка")

            if my_target_match and cand_target_match:
                return index, candidate_id
        return None, None

    found_idx, partner_id = match_found(premium_queue)
    if partner_id is None:
        found_idx, partner_id = match_found(search_queue)

    if partner_id is not None:
        if partner_id in premium_queue:
            premium_queue.remove(partner_id)
        elif partner_id in search_queue:
            search_queue.remove(partner_id)

        active_chats[user_id] = partner_id
        active_chats[partner_id] = user_id

        p1 = user_profiles.get(user_id, {})
        p2 = user_profiles.get(partner_id, {})

        await bot.send_message(user_id, f"🎉 Собеседник найден!\nПол: {p2.get('gender')}, {p2.get('age')} лет\nИнтерес: {p2.get('interests')}\nОписание: {p2.get('bio')}", reply_markup=get_chat_menu())
        await bot.send_message(partner_id, f"🎉 Собеседник найден!\nПол: {p1.get('gender')}, {p1.get('age')} лет\nИнтерес: {p1.get('interests')}\nОписание: {p1.get('bio')}", reply_markup=get_chat_menu())
    else:
        premium_queue.append(user_id)
        await message.answer("💎 **[PREMIUM]** Поиск с фильтром по полу запущен...", reply_markup=get_chat_menu())

@dp.message(F.text == "🛑 Остановить диалог")
async def stop_chat(message: types.Message):
    user_id = message.from_user.id
    
    if user_id in search_queue:
        search_queue.remove(user_id)
        await message.answer("❌ Поиск остановлен.", reply_markup=get_main_menu())
        return
    if user_id in premium_queue:
        premium_queue.remove(user_id)
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

# Пересылка сообщений между собеседниками
@dp.message()
async def forward_messages(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id in active_chats:
        partner_id = active_chats[user_id]
        try:
            await message.copy_to(partner_id)
        except Exception:
            await message.answer("⚠️ Не удалось отправить сообщение собеседнику.")

# Запуск бота
async def main():
    print("Бот запущен и готов к работе!")
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
