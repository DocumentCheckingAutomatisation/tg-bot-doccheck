# 📁 Структура проекта:
# telegram_bot/
# ├── bot.py               # Точка входа
# ├── config.py            # Настройки и переменные окружения
# ├── logger.py            # Логирование
# ├── db.py                # Хранение ролей в памяти
# ├── services/api.py      # Взаимодействие с FastAPI-сервисом
# └── handlers/
#     ├── start.py         # Команды start и set_reviewer
#     ├── documents.py     # Команды для работы с документами
#     └── rules.py         # Получение и изменение правил

from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from logger import logger
from db import init_db
from handlers import start, documents, rules

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

init_db()

# Регистрация хендлеров
start.register(dp)
documents.register(dp)
rules.register(dp)

if __name__ == "__main__":
    logger.info("🔁 Бот запущен.")
    try:
        dp.run_polling(bot)
    except Exception as e:
        logger.critical(f"🔥 Критическая ошибка: {e}")



# import logging
# import os
# from dotenv import load_dotenv
# from aiogram import Bot, Dispatcher, types
# from aiogram.types import Message
# from aiogram.filters import Command
# from db import get_user_role, set_user_role
#
# # === Логирование ===
# log_format = "%(asctime)s [%(levelname)s] %(message)s"
#
# file_handler = logging.FileHandler("bot.log", encoding="utf-8")
# file_handler.setLevel(logging.DEBUG)
# file_handler.setFormatter(logging.Formatter(log_format))
#
# # Настройка логгера
# logger = logging.getLogger(__name__)
# logger.setLevel(logging.DEBUG)
# logger.addHandler(file_handler)
#
# # === Загрузка переменных окружения ===
# load_dotenv()
# BOT_TOKEN = os.getenv("BOT_TOKEN")
# SECRET_CODE = os.getenv("SECRET_CODE")
#
# bot = Bot(token=BOT_TOKEN)
# dp = Dispatcher()
#
# # === Команды ===
#
# @dp.message(Command("start"))
# async def cmd_start(message: Message):
#     user_id = message.from_user.id
#     set_user_role(user_id, "student")
#     logger.info(f"[START] Пользователь {user_id} начал работу.")
#     await message.answer("Привет! Ты зарегистрирован как студент.\nЕсли ты нормоконтролер — введи /set_reviewer")
#
# @dp.message(Command("set_reviewer"))
# async def cmd_set_reviewer(message: Message):
#     user_id = message.from_user.id
#     await message.answer("Введите секретный код:")
#
#     @dp.message()
#     async def handle_code(msg: Message):
#         if msg.from_user.id != user_id:
#             return
#         if msg.text.strip() == SECRET_CODE:
#             set_user_role(msg.from_user.id, "reviewer")
#             logger.info(f"[ROLE] Пользователь {msg.from_user.id} стал нормоконтролером.")
#             await msg.answer("✅ Роль изменена: теперь вы нормоконтролер.")
#         else:
#             logger.warning(f"[AUTH_FAIL] Неверный код от пользователя {msg.from_user.id}.")
#             await msg.answer("❌ Неверный код. Вы остались студентом.")
#         dp.message.unregister(handle_code)
#
# @dp.message(Command("change_rules"))
# async def cmd_change_rules(message: Message):
#     user_id = message.from_user.id
#     role = get_user_role(user_id)
#     logger.debug(f"[ACCESS] Пользователь {user_id} попытался зайти в /change_rules. Роль: {role}")
#     if role != "reviewer":
#         logger.warning(f"[DENIED] Доступ запрещен пользователю {user_id}.")
#         await message.answer("⛔ Доступ запрещен. Только для нормоконтролеров.")
#         return
#     await message.answer("🛠 Здесь вы можете изменить правила проверки.")
#     logger.info(f"[ACCESS_GRANTED] Пользователь {user_id} получил доступ к /change_rules")
#
# @dp.message(Command("check_document"))
# async def cmd_check_document(message: Message):
#     user_id = message.from_user.id
#     logger.info(f"[DOC] Пользователь {user_id} начал проверку документа.")
#
#     try:
#         await message.answer("📄 Загрузка документа и запуск проверки...")
#         logger.debug(f"[DOC] Документ пользователя {user_id} принят на проверку.")
#
#         # Здесь могла бы быть логика проверки
#         await message.answer("✅ Проверка завершена. Нарушений не найдено.")
#         logger.info(f"[DOC_SUCCESS] Проверка завершена для пользователя {user_id}.")
#
#     except Exception as e:
#         logger.error(f"[DOC_ERROR] Ошибка при проверке документа у пользователя {user_id}: {e}")
#         await message.answer("❌ Ошибка при проверке документа.")
#
# # === Запуск ===
# if __name__ == "__main__":
#     logger.info("🔁 Бот запущен и готов к работе.")
#     try:
#         dp.run_polling(bot)
#     except Exception as e:
#         logger.critical(f"🔥 Критическая ошибка при запуске бота: {e}")
