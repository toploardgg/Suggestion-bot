# Код написан Toploardgg 30 декабря 2025 года
# Telegram бот с выбором языка и пересылкой сообщений админу

import asyncio
import logging
import json
import os
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.storage.memory import MemoryStorage
from config import BOT_TOKEN, ADMIN_ID
from aiogram.filters import Command
from aiogram import F

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Файл для хранения языков пользователей
LANGUAGES_FILE = "user_languages.json"

# Словарь для хранения выбранного языка пользователей
user_languages = {}

# Тексты на разных языках
TEXTS = {
    'en': {
        'welcome': '👋 Welcome! Please select your language:',
        'language_selected': '✅ English language selected!',
        'send_message': '📝 Send me any message and I will forward it to the author.',
        'bot_description': (
            '👋 Hello! I am a Suggestion bot.\n\n'
            '• I forward all your messages to author\n'
            '✉️ Just send me a message and I will forward it to the author!'
        ),
        'forwarded_to_admin': '✅ Your message has been forwarded to the author!',
        'admin_notification': '📨 New message from user'
    },
    'ru': {
        'welcome': '👋 Добро пожаловать! Пожалуйста, выберите язык:',
        'language_selected': '✅ Русский язык выбран!',
        'send_message': '📝 Отправьте мне любое сообщение, и я перешлю его автору.',
        'bot_description': (
            '👋 Привет! Я бот предложки.\n\n'
            '📌 Что я делаю:\n'
            '• Пересылаю все ваши сообщения автору\n'
            '✉️ Просто отправьте мне сообщение, и я перешлю его автору!'
        ),
        'forwarded_to_admin': '✅ Ваше сообщение отправлено автору!',
        'admin_notification': '📨 Новое сообщение от пользователя'
    }
}

# Функция для загрузки языков пользователей из файла
def load_languages():
    """Загружает сохраненные языки пользователей из JSON файла"""
    global user_languages
    if os.path.exists(LANGUAGES_FILE):
        try:
            with open(LANGUAGES_FILE, 'r', encoding='utf-8') as f:
                # Конвертируем ключи обратно в int
                user_languages = {int(k): v for k, v in json.load(f).items()}
            logging.info(f"✅ Загружено {len(user_languages)} языковых настроек пользователей")
        except Exception as e:
            logging.error(f"❌ Ошибка загрузки языков: {e}")
            user_languages = {}
    else:
        logging.info("ℹ️ Файл языков не найден, создан новый словарь")
        user_languages = {}

# Функция для сохранения языков пользователей в файл
def save_languages():
    """Сохраняет языки пользователей в JSON файл"""
    try:
        with open(LANGUAGES_FILE, 'w', encoding='utf-8') as f:
            # Конвертируем ключи в string для JSON
            json.dump({str(k): v for k, v in user_languages.items()}, f, ensure_ascii=False, indent=2)
        logging.info(f"💾 Сохранено {len(user_languages)} языковых настроек")
    except Exception as e:
        logging.error(f"❌ Ошибка сохранения языков: {e}")

# Функция для создания клавиатуры выбора языка
def get_language_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🇬🇧 English", callback_data="lang_en"),
            InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru")
        ]
    ])
    return keyboard

# Обработчик команды /start
@dp.message(Command("start"))
async def cmd_start(message: Message):
    user_id = message.from_user.id
    
    # Проверяем, выбран ли уже язык
    if user_id in user_languages:
        lang = user_languages[user_id]
        # Пользователь уже выбрал язык, показываем описание бота
        await message.answer(TEXTS[lang]['bot_description'])
    else:
        # Первый запуск, предлагаем выбрать язык
        await message.answer(
            "👋 Welcome! Please select your language:\n"
            "👋 Добро пожаловать! Выберите язык:",
            reply_markup=get_language_keyboard()
        )

# Обработчик выбора языка
@dp.callback_query(F.data.startswith("lang_"))
async def process_language_selection(callback: CallbackQuery):
    lang = callback.data.split("_")[1]  # Получаем 'en' или 'ru'
    user_id = callback.from_user.id
    
    # Сохраняем язык пользователя
    user_languages[user_id] = lang
    save_languages()  # Сохраняем в файл
    
    # Отправляем подтверждение
    await callback.message.edit_text(
        f"{TEXTS[lang]['language_selected']}\n\n{TEXTS[lang]['send_message']}"
    )
    await callback.answer()

# Обработчик всех текстовых сообщений
@dp.message(F.text)
async def forward_to_admin(message: Message):
    user_id = message.from_user.id
    
    # Проверяем, выбран ли язык
    if user_id not in user_languages:
        await message.answer(
            "👋 Please select your language first:\n"
            "👋 Сначала выберите язык:",
            reply_markup=get_language_keyboard()
        )
        return
    
    lang = user_languages[user_id]
    
    # Формируем информацию о пользователе
    user_info = (
        f"{TEXTS[lang]['admin_notification']}:\n\n"
        f"👤 ID: {user_id}\n"
        f"📝 Username: @{message.from_user.username or 'нет username'}\n"
        f"👨‍💼 Имя: {message.from_user.full_name}\n"
        f"🌐 Язык: {lang.upper()}\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"💬 Сообщение:\n{message.text}"
    )
    
    # Отправляем сообщение админу
    await bot.send_message(ADMIN_ID, user_info)
    
    # Подтверждение пользователю
    await message.answer(TEXTS[lang]['forwarded_to_admin'])

@dp.message(F.reply_to_message & F.from_user.id == ADMIN_ID)
async def admin_reply_handler(message: Message):
    """
    Обрабатывает ответы админа на пересланные сообщения пользователей.
    Пересылает сообщение админа обратно исходному пользователю.
    Поддерживает все типы: текст, фото, видео, кружки (video_note), голосовые, стикеры, документы, анимации и т.д.
    """
    replied_msg = message.reply_to_message
    
    # Проверяем, что это наше пересланное сообщение и есть forward_from
    if replied_msg.forward_from:
        original_user_id = replied_msg.forward_from.id
    elif replied_msg.forward_sender_name:  # если пользователь скрыл профиль
        # К сожалению, в этом случае ID недоступен — пропускаем или уведомляем админа
        await message.reply("❌ Не могу отправить: пользователь скрыл профиль (forward_sender_name)")
        return
    else:
        await message.reply("❌ Это не пересланное сообщение от пользователя")
        return
    
    try:
        # Копируем сообщение админа пользователю (сохраняет весь формат и тип)
        await message.copy_to(chat_id=original_user_id)
        # Опционально: подтверждение админу
        await message.reply("✅ Ответ отправлен пользователю!")
    except Exception as e:
        logging.error(f"Ошибка отправки ответа пользователю {original_user_id}: {e}")
        await message.reply(f"❌ Ошибка отправки: {e}")

# Обработчик всех остальных типов сообщений (фото, видео, документы, кружки, голосовые и т.д.)
@dp.message()
async def forward_media_to_admin(message: Message):
    user_id = message.from_user.id
    
    # Проверяем, выбран ли язык
    if user_id not in user_languages:
        await message.answer(
            "👋 Please select your language first:\n"
            "👋 Сначала выберите язык:",
            reply_markup=get_language_keyboard()
        )
        return
    
    lang = user_languages[user_id]
    
    # Определяем тип сообщения для логирования
    message_type = "Unknown"
    if message.photo:
        message_type = "📸 Photo"
    elif message.video:
        message_type = "🎥 Video"
    elif message.video_note:
        message_type = "📹 Video Note (Circle)"
    elif message.voice:
        message_type = "🎤 Voice Message"
    elif message.audio:
        message_type = "🎵 Audio"
    elif message.document:
        message_type = "📁 Document"
    elif message.sticker:
        message_type = "🎭 Sticker"
    elif message.animation:
        message_type = "🎬 GIF/Animation"
    elif message.location:
        message_type = "🗺️ Location"
    elif message.contact:
        message_type = "📞 Contact"
    elif message.poll:
        message_type = "📊 Poll"
    elif message.dice:
        message_type = "🎲 Dice"
    
    # Формируем информацию о пользователе
    user_info = (
        f"{TEXTS[lang]['admin_notification']}:\n\n"
        f"👤 ID: {user_id}\n"
        f"📝 Username: @{message.from_user.username or 'нет username'}\n"
        f"👨‍💼 Имя: {message.from_user.full_name}\n"
        f"🌐 Язык: {lang.upper()}\n"
        f"📦 Тип: {message_type}\n"
        f"━━━━━━━━━━━━━━━━"
    )
    
    # Отправляем информацию админу
    await bot.send_message(ADMIN_ID, user_info)
    
    # Пересылаем само сообщение (со всеми медиа, кружками, голосовыми и т.д.)
    await message.forward(ADMIN_ID)
    
    # Подтверждение пользователю
    await message.answer(TEXTS[lang]['forwarded_to_admin'])

# Главная функция запуска бота
async def main():
    # Загружаем сохраненные языки при запуске
    load_languages()
    
    # Удаляем вебхуки (если были) БЕЗ удаления накопленных сообщений
    # drop_pending_updates=False означает, что бот обработает все сообщения,
    # которые были отправлены, когда он был выключен (до 24 часов)
    await bot.delete_webhook(drop_pending_updates=False)
    
    # Запускаем polling
    logging.info("🚀 Бот запущен и обрабатывает все накопленные сообщения!")
    await dp.start_polling(bot)

# Точка входа
if __name__ == "__main__":
    asyncio.run(main())