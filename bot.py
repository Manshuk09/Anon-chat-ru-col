import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# ================= НАСТРОЙКИ =================
TOKEN = "8861156320:AAEd_G2uA0GfNEifOzawEnLAFFFTov-1FHA"  # Твой токен
ADMIN_ID = 6681923689                                   # Твой Telegram ID
# ============================================

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Хранилище для активного поиска собеседников (очередь ожидания)
search_queue = []
# Активные диалоги: {user_id: partner_id}
active_chats = {}

# Состояния (FSM)
class States(StatesGroup):
    waiting_for_support = State()

# Главное меню (кнопки внизу экрана)
def get_main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔍 Начать поиск собеседника")],
            [KeyboardButton(text="📄 Посмотреть мою анкету"), KeyboardButton(text="✏️ Заполнить анкету заново")],
            [KeyboardButton(text="💬 Поддержка"), KeyboardButton(text="📢 Наш канал")]
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

# ================= РАЗДЕЛ ПОДДЕРЖКИ =================

@dp.message(F.text == "💬 Поддержка")
async def support_start(message: types.Message, state: FSMContext):
    await state.set_state(States.waiting_for_support)
    await message.answer(
        "💬 **Служба поддержки**\n\n"
        "Напиши свой вопрос, жалобу или предложение одним сообщением, и администратор ответит тебе в ближайшее время.",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="❌ Отмена")]],
            resize_keyboard=True
        )
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
        await message.answer("✅ Твое сообщение успешно отправлено поддержке! Жди ответа.", reply_markup=get_main_menu())
    except Exception:
        await message.answer("⚠️ Не удалось отправить сообщение. Попробуй позже.", reply_markup=get_main_menu())
    
    await state.clear()

# Ответ администратора пользователю (через Reply у себя в чате)
@dp.message(F.chat.id == ADMIN_ID)
async def admin_reply_to_user(message: types.Message):
    if message.reply_to_message:
        reply_text = message.reply_to_message.text
        if "🆔 ID пользователя:" in reply_text:
            try:
                for line in reply_text.split("\n"):
                    if "🆔 ID пользователя:" in line:
                        target_user_id = int(line.replace("🆔 ID пользователя:", "").replace("`", "").strip())
                        await bot.send_message(
                            target_user_id,
                            f"💬 **Ответ от поддержки:**\n\n{message.text}"
                        )
                        await message.reply("✅ Ответ успешно отправлен пользователю!")
                        return
            except Exception as e:
                await message.reply(f"⚠️ Ошибка при отправке ответа: {e}")

# ================= РАЗДЕЛ ПОИСКА СОБЕСЕДНИКОВ =================

@dp.message(F.text == "🔍 Начать поиск собеседника")
async def start_search(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id in active_chats:
        await message.answer("Ты уже находишься в диалоге! Сначала заверши его.", reply_markup=get_chat_menu())
        return

    if user_id in search_queue:
        await message.answer("⏳ Ты уже ищешь собеседника, подожди немного...", reply_markup=get_chat_menu())
        return

    if search_queue:
        partner_id = search_queue.pop(0)
        
        active_chats[user_id] = partner_id
        active_chats[partner_id] = user_id

        await bot.send_message(user_id, "🎉 Собеседник найден! Можете общаться. Чтобы выйти, нажмите кнопку ниже.", reply_markup=get_chat_menu())
        await bot.send_message(partner_id, "🎉 Собеседник найден! Можете общаться. Чтобы выйти, нажмите кнопку ниже.", reply_markup=get_chat_menu())
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
