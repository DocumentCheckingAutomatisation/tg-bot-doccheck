# Структура проекта:
# telegram_bot/
# ├── bot.py               # Точка входа
# ├── config.py            # Настройки и переменные окружения
# ├── logger.py            # Логирование
# ├── db.py                # Хранение ролей в памяти
# ├── bot.log              # Логи
# ├── roles.db             # БД
# ├── requirements.txt     # Зависимости
# ├── README.md            # Документация
# ├── .env                 # Переменные окружения
# ├── .gitignore           # Игнорируемые файлы
# ├── services/api.py      # Взаимодействие с FastAPI-сервисом
# └── handlers/
#     ├── start.py         # Команды start и set_reviewer
#     ├── documents.py     # Команды для работы с документами
#     └── rules.py         # Получение и изменение правил

from aiogram import Bot, Dispatcher

from config import BOT_TOKEN
from db import init_db
from handlers import start, documents, rules
from logger import logger

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

init_db()

start.register(dp)
documents.register(dp)
rules.register(dp)

if __name__ == "__main__":
    logger.info("🔁 Бот запущен.")
    try:
        dp.run_polling(bot)
    except Exception as e:
        logger.critical(f"🔥 Критическая ошибка: {e}")
