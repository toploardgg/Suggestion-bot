# Код написан Toploardgg 30 декабря 2025 года
# Telegram бот с выбором языка и пересылкой сообщений админу + ответы от админа

import asyncio
import logging
import json
import os
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config import BOT_TOKEN, ADMIN_ID

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Файл для хранения языков пользователей
LANGUAGES_FILE = "user_languages.json"

# Словарь для хранения выбранного языка пользователей
user_languages = {}

# Словарь для хранения соответствия message_id админа -> user_id отправителя
# Формат: {message_id_в_чате_админа: user_id_отправителя}
admin_message_map = {}

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
        'admin_notification': '📨 New message from user',
        'admin_reply': '💬 Reply from author:'
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
        'admin_notification': '📨 Новое сообщение от пользователя',
        'admin_reply': '💬 Ответ от автора:'
    }
}

# Функция для загрузки языков пользователей из файла
def load_languages():
    """Загружает сохраненные языки пользователей из JSON файла"""
    global user_languages
    if os.path.exists(LANGUAGES_FILE):
        try:
            with open(LANGUAGES_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Конвертируем ключи обратно в int
                user_languages = {int(k): v for k, v in data.items()}
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
    
    # Проверяем, выбран ли уже язык (теперь он загружается из файла!)
    if user_id in user_languages:
        lang = user_languages[user_id]
        # Пользователь уже выбрал язык, показываем описание бота
        await message.answer(TEXTS[lang]['bot_description'])
        logging.info(f"👤 Пользователь {user_id} вернулся, язык: {lang}")
    else:
        # Первый запуск, предлагаем выбрать язык
        await message.answer(
            "👋 Welcome! Please select your language:\n"
            "👋 Добро пожаловать! Выберите язык:",
            reply_markup=get_language_keyboard()
        )
        logging.info(f"🆕 Новый пользователь {user_id}, предлагаем выбрать язык")

# Обработчик выбора языка
@dp.callback_query(F.data.startswith("lang_"))
async def process_language_selection(callback: CallbackQuery):
    lang = callback.data.split("_")[1]  # Получаем 'en' или 'ru'
    user_id = callback.from_user.id
    
    # Сохраняем язык пользователя в память
    user_languages[user_id] = lang
    
    # ВАЖНО: Сохраняем в файл сразу после выбора
    save_languages()
    
    logging.info(f"🌐 Пользователь {user_id} выбрал язык: {lang}")
    
    # Отправляем подтверждение
    await callback.message.edit_text(
        f"{TEXTS[lang]['language_selected']}\n\n{TEXTS[lang]['send_message']}"
    )
    await callback.answer()

# Обработчик текстовых сообщений от пользователей (НЕ админа)
@dp.message(F.text & ~F.from_user.id.in_([ADMIN_ID]))
async def forward_text_to_admin(message: Message):
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
        f"📨 Новое сообщение:\n\n"
        f"👤 ID: <code>{user_id}</code>\n"
        f"📝 @{message.from_user.username or 'нет'}\n"
        f"👨‍💼 {message.from_user.full_name}\n"
        f"🌐 {lang.upper()}\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"💬 {message.text}"
    )
    
    # Отправляем сообщение админу
    sent_msg = await bot.send_message(ADMIN_ID, user_info, parse_mode="HTML")
    
    # Сохраняем связь: message_id админа -> user_id отправителя
    admin_message_map[sent_msg.message_id] = user_id
    
    # Подтверждение пользователю
    await message.answer(TEXTS[lang]['forwarded_to_admin'])
    
    logging.info(f"📨 Сообщение от {user_id} отправлено админу")

# Обработчик медиа-сообщений от пользователей (НЕ админа)
@dp.message(~F.text & ~F.from_user.id.in_([ADMIN_ID]))
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
        message_type = "📸 Фото"
    elif message.video:
        message_type = "🎥 Видео"
    elif message.video_note:
        message_type = "📹 Кружок"
    elif message.voice:
        message_type = "🎤 Голосовое"
    elif message.audio:
        message_type = "🎵 Аудио"
    elif message.document:
        message_type = "📁 Файл"
    elif message.sticker:
        message_type = "🎭 Стикер"
    elif message.animation:
        message_type = "🎬 GIF"
    elif message.location:
        message_type = "🗺️ Локация"
    elif message.contact:
        message_type = "📞 Контакт"
    elif message.poll:
        message_type = "📊 Опрос"
    elif message.dice:
        message_type = "🎲 Кубик"
    
    # Формируем информацию о пользователе
    caption_text = message.caption if message.caption else ""
    user_info = (
        f"📨 Новое сообщение:\n\n"
        f"👤 ID: <code>{user_id}</code>\n"
        f"📝 @{message.from_user.username or 'нет'}\n"
        f"👨‍💼 {message.from_user.full_name}\n"
        f"🌐 {lang.upper()}\n"
        f"📦 Тип: {message_type}\n"
        f"━━━━━━━━━━━━━━━━"
    )
    
    if caption_text:
        user_info += f"\n💬 Подпись: {caption_text}"
    
    # Отправляем информацию админу
    info_msg = await bot.send_message(ADMIN_ID, user_info, parse_mode="HTML")
    
    # Копируем само сообщение админу (не пересылаем, чтобы не было "Forwarded from")
    copied_msg = await message.copy_to(ADMIN_ID)
    
    # Сохраняем связь для скопированного сообщения
    admin_message_map[copied_msg.message_id] = user_id
    # Также сохраняем для информационного сообщения
    admin_message_map[info_msg.message_id] = user_id
    
    # Подтверждение пользователю
    await message.answer(TEXTS[lang]['forwarded_to_admin'])
    
    logging.info(f"📨 {message_type} от {user_id} отправлено админу")

# Обработчик ОТВЕТОВ от АДМИНА (когда админ нажимает "Ответить")
@dp.message(F.reply_to_message & F.from_user.id.in_([ADMIN_ID]))
async def admin_reply_handler(message: Message):
    # Получаем ID сообщения, на которое отвечает админ
    replied_message_id = message.reply_to_message.message_id
    
    # Проверяем, есть ли это сообщение в нашей карте
    if replied_message_id not in admin_message_map:
        await message.answer("❌ Не могу найти получателя для этого сообщения.")
        logging.warning(f"⚠️ Админ ответил на сообщение {replied_message_id}, но ID не найден в карте")
        return
    
    # Получаем user_id получателя
    recipient_id = admin_message_map[replied_message_id]
    
    # Получаем язык пользователя (по умолчанию 'en' если не найден)
    lang = user_languages.get(recipient_id, 'en')
    
    try:
        # Заголовок ответа
        reply_header = TEXTS[lang]['admin_reply']
        
        # Если это текстовое сообщение
        if message.text:
            await bot.send_message(
                recipient_id,
                f"{reply_header}\n\n{message.text}"
            )
        # Если это медиа с подписью
        elif message.caption:
            # Отправляем заголовок отдельно
            await bot.send_message(recipient_id, reply_header)
            # Копируем медиа с подписью
            await message.copy_to(recipient_id)
        # Если это медиа без подписи
        else:
            # Отправляем заголовок отдельно
            await bot.send_message(recipient_id, reply_header)
            # Копируем медиа
            await message.copy_to(recipient_id)
        
        # Подтверждение админу (КОРОТКОЕ)
        await message.answer(f"✅ Отправлено пользователю {recipient_id}")
        logging.info(f"📤 Админ ответил пользователю {recipient_id}")
        
    except Exception as e:
        await message.answer(f"❌ Ошибка отправки: {e}")
        logging.error(f"❌ Ошибка отправки ответа пользователю {recipient_id}: {e}")

# Главная функция запуска бота
async def main():
    # ВАЖНО: Загружаем сохраненные языки ПРИ ЗАПУСКЕ бота
    load_languages()
    logging.info(f"📂 Загружено языков из базы: {len(user_languages)}")
    
    # Удаляем вебхуки (если были) БЕЗ удаления накопленных сообщений
    await bot.delete_webhook(drop_pending_updates=False)
    
    # Запускаем polling
    logging.info("🚀 Бот запущен и обрабатывает все накопленные сообщения!")
    await dp.start_polling(bot)

# Точка входа
if __name__ == "__main__":
    asyncio.run(main())
