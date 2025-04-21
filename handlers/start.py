from aiogram import Router, types
from aiogram.filters import Command
from db import get_user_role, set_user_role, REVIEWER_ROLE
from config import SECRET_CODE
from logger import logger

router = Router()

def get_available_commands(role: str) -> list[str]:
    commands = [
        "/types — показать типы документов",
        "/rules <тип_документа> — показать правила",
        "/check_docx — проверить .docx документ",
        "/check_latex — проверить .tex и .sty файлы",
    ]

    if role == REVIEWER_ROLE:
        commands.append("/change_rule <тип> <ключ> <значение> — изменить правило")
        commands.append("/change_rule_for_all <ключ> <значение> — изменить правило для всех типов")

    commands.append("/set_reviewer <секретный_код> — получить роль нормоконтролера")
    return commands

@router.message(Command("start"))
async def start(message: types.Message):
    user_id = message.from_user.id
    role = get_user_role(user_id)
    logger.info(f"👤 Пользователь {user_id} начал сессию как {role}.")

    commands = get_available_commands(role)

    await message.answer(
        f"Привет! Ваша текущая роль: {role}.\n"
        "Доступные команды:\n" +
        "\n".join(commands)
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

        commands = get_available_commands(REVIEWER_ROLE)
        await message.answer(
            "Вы успешно стали нормоконтролёром!\n"
            "Теперь вам доступны следующие команды:\n" +
            "\n".join(commands)
        )
    else:
        logger.warning(f"❌ Пользователь {message.from_user.id} ввел неверный секретный код")
        await message.answer("Неверный секретный код.")

def register(dp):
    dp.include_router(router)

