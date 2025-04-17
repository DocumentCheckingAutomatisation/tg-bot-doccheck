
from aiogram import Router, types
from aiogram.filters import Command
from db import get_user_role, set_user_role, REVIEWER_ROLE, STUDENT_ROLE
from config import SECRET_CODE
from logger import logger

router = Router()

@router.message(Command("start"))
async def start(message: types.Message):
    user_id = message.from_user.id
    role = get_user_role(user_id)
    logger.info(f"👤 Пользователь {user_id} начал сессию как {role}.")
    await message.answer(
        f"Привет! Ваша текущая роль: {role}.\n"
        "Доступные команды:\n"
        "/types — показать типы документов\n"
        "/rules <тип_документа> — показать правила\n"
        "/change_rule <тип> <ключ> <значение> — изменить правило (только нормоконтролерам)\n"
        "/set_reviewer <секретный_код> — получить роль нормоконтролера"
    )


@router.message(Command("set_reviewer"))
async def set_reviewer(message: types.Message):
    parts = message.text.split()
    if len(parts) != 2:
        await message.answer("Использование: /set_reviewer <секретный_код>")
        return

    secret = parts[1]
    if secret == SECRET_CODE:
        user_id = message.from_user.id
        set_user_role(user_id, REVIEWER_ROLE)
        logger.info(f"✅ Пользователю {user_id} присвоена роль: reviewer")
        await message.answer("Вы успешно стали нормоконтролёром!")
    else:
        logger.warning(f"❌ Пользователь {message.from_user.id} ввел неверный секретный код")
        await message.answer("Неверный секретный код.")


def register(dp):
    dp.include_router(router)