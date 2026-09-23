import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# ================= НАСТРОЙКИ =================
TOKEN = "8861156320:AAEd_G2uA0GfNEifOzawEnLAFFFTov-1FHA"  # Твой токен
ADMIN_ID = 6681923689                                   # Твой Telegram ID
# ============================================

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Хранилища
search_queue = []          # Обычная очередь
premium_queue = []         # Премиум-очередь (идет первой)
active_chats = {}          # Активные диалоги: {user_id: partner_id}
user_profiles = {}         # База анкет: {user_id: {"gender": ..., "target": ..., "age": ..., "bio": ..., "is_premium": bool}}

# Состояния (FSM)
class States(StatesGroup):
    waiting_for_support = State()
    profile_gender = State()
    profile_target = State()
    profile_age = State()
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
    await message.answer("📢 Наш официальный канал: https://t.me/твой_канал", reply_markup=get_main_menu())

# 3. Кнопка "💎 PREMIUM"
@dp.message(F.text == "💎 PREMIUM")
async def premium_info(message: types.Message):
    user_id = message.from_user.id
    is_prem = user_profiles.get(user_id, {}).get("is_premium", False)
    
    status_text = "✅ У тебя активирован **PREMIUM**!" if is_prem else "❌ У тебя стандартный статус."

    markup = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⭐ Активировать тестовый Премиум", callback_data="activate_prem")]
        ]
    )

    await message.answer(
        f"💎 **PREMIUM-статус в боте**\n\n"
        f"{status_text}\n\n"
        "Что дает Премиум:\n"
        "• 🚀 **Приоритетный поиск** (тебя соединяют первыми)\n"
        "• 🎯 **Фильтр по полу** (автоматический подбор по твоей анкете)\n"
        "• ✨ **Уникальный значок** в профиле\n\n"
        "🎁 *Нажми кнопку ниже, чтобы получить премиум бесплатно!*",
        reply_markup=markup
    )

@dp.callback_query(F.data == "activate_prem")
async def process_activate_prem(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if user_id not in user_profiles:
        user_profiles[user_id] = {"gender": "Не указан", "target": "Всех", "age": "Не указан", "bio": "Пусто", "is_premium": True}
    else:
        user_profiles[user_id]["is_premium"] = True
    
    await callback.message.answer("🎉 Поздравляем! Премиум-статус успешно активирован для твоего аккаунта!")
    await callback.answer()

# ================= РАЗДЕЛ АНКЕТ И ВОЗРАСТА =================

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
    await message.answer("📝 Шаг 1/4: Укажи свой пол:", reply_markup=markup)

@dp.message(F.text == "❌ Отмена")
async def cancel_profile(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Заполнение анкеты отменено.", reply_markup=get_main_menu())

@dp.message(States.profile_gender, F.text.in_(["👤 Парень", "👧 Девушка"]))
async def profile_gender_chosen(message: types.Message, state: FSMContext):
    await state.update_data(gender=message.text)
    await state.set_state(States.profile_target)
    markup = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔎 Парня"), KeyboardButton(text="🔎 Девушку")],
            [KeyboardButton(text="🌍 Всех")],
            [KeyboardButton(text="❌ Отмена")]
        ],
        resize_keyboard=True
    )
    await message.answer("📝 Шаг 2/4: Кого ты хочешь искать?", reply_markup=markup)

@dp.message(States.profile_target, F.text.in_(["🔎 Парня", "🔎 Девушку", "🌍 Всех"]))
async def profile_target_chosen(message: types.Message, state: FSMContext):
    await state.update_data(target=message.text)
    await state.set_state(States.profile_age)
    await message.answer("📝 Шаг 3/4: Сколько тебе лет? (напиши цифрой)", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))

@dp.message(States.profile_age)
async def profile_age_chosen(message: types.Message, state: FSMContext):
    await state.update_data(age=message.text)
    await state.set_state(States.profile_bio)
    await message.answer("📝 Шаг 4/4: Напиши пару слов о себе (описание, хобби):", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True))

@dp.message(States.profile_bio)
async def profile_bio_chosen(message: types.Message, state: FSMContext):
    data = await state.get_data()
    user_id = message.from_user.id
    
    is_prem = user_profiles.get(user_id, {}).get("is_premium", False)
    
    user_profiles[user_id] = {
        "gender": data["gender"],
        "target": data["target"],
        "age": data["age"],
        "bio": message.text,
        "is_premium": is_prem
    }
    
    await state.clear()
    await message.answer(
        "✅ Анкета успешно заполнена и сохранена!\n\n"
        f"👤 Пол: {data['gender']}\n"
        f"🎯 Кого ищет: {data['target']}\n"
        f"🎂 Возраст: {data['age']}\n"
        f"📄 Описание: {message.text}",
        reply_markup=get_main_menu()
    )

@dp.message(F.text == "📄 Посмотреть мою анкету")
async def view_profile(message: types.Message):
    user_id = message.from_user.id
    if user_id in user_profiles:
        p = user_profiles[user_id]
        prem_badge = " ✨ [PREMIUM]" if p.get("is_premium") else ""
        await message.answer(
            f"📄 **Твоя анкета{prem_badge}:**\n\n"
            f"👤 Пол: {p['gender']}\n"
            f"🎯 Кого ищет: {p['target']}\n"
            f"🎂 Возраст: {p['age']}\n"
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
                await message.reply(f"⚠️ Ошибка: {e}")

# ================= УМНЫЙ ПОИСК С УЧЕТОМ ПОЛА И ПРЕМИУМА =================

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
        await message.answer("⚠️ Сначала заполни анкету, чтобы бот знал твои предпочтения!", reply_markup=get_main_menu())
        return

    user_data = user_profiles[user_id]
    is_prem = user_data.get("is_premium", False)
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

        info_for_user = (
            "🎉 Собеседник найден!\n\n"
            f"👤 Пол: {p2.get('gender')}, {p2.get('age')} лет\n"
            f"📄 Описание: {p2.get('bio')}\n\n"
            "Можете общаться. Чтобы выйти, нажмите кнопку ниже."
        )
        info_for_partner = (
            "🎉 Собеседник найден!\n\n"
            f"👤 Пол: {p1.get('gender')}, {p1.get('age')} лет\n"
            f"📄 Описание: {p1.get('bio')}\n\n"
            "Можете общаться. Чтобы выйти, нажмите кнопку ниже."
        )

        await bot.send_message(user_id, info_for_user, reply_markup=get_chat_menu())
        await bot.send_message(partner_id, info_for_partner, reply_markup=get_chat_menu())
    else:
        if is_prem:
            premium_queue.append(user_id)
            await message.answer("💎 **[PREMIUM]** Приоритетный поиск запущен... Ищем подходящего собеседника.", reply_markup=get_chat_menu())
        else:
            search_queue.append(user_id)
            await message.answer("🔍 Ищем тебе собеседника...", reply_markup=get_chat_menu())

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

