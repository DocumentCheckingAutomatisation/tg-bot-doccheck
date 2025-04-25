import json

from aiogram import Router, types
from aiogram.filters import Command

from db import get_user_role, REVIEWER_ROLE
from logger import logger
from services.api import get_doc_options, get_rules, change_rule, change_rule_for_all

router = Router()


@router.message(Command("types"))
async def available_types(message: types.Message):
    logger.debug(f"📩 Пользователь {message.from_user.id} запросил типы документов")
    options = get_doc_options()
    if options:
        text = "\n".join(opt["name"] for opt in options)
        await message.answer(f"Доступные типы документов:\n{text}")
    else:
        await message.answer("Ошибка при получении типов документов.")


@router.message(Command("rules"))
async def show_rules(message: types.Message):
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Использование: /rules <тип_документа>")
        return
    doc_type = parts[1]
    logger.debug(f"📩 Пользователь {message.from_user.id} запросил правила для {doc_type}")

    rules = get_rules(doc_type)

    if not rules:
        await message.answer("Ошибка при получении правил.")
        return

    pretty_rules = json.dumps(rules, indent=2, ensure_ascii=False)
    # Ограничение Telegram: 4096 символов в одном сообщении
    max_length = 4000

    if len(pretty_rules) > max_length:
        chunks = [pretty_rules[i:i + max_length] for i in range(0, len(pretty_rules), max_length)]
        await message.answer(f"*Правила для типа:* `{doc_type}`", parse_mode="Markdown")
        for chunk in chunks:
            await message.answer(f"```json\n{chunk}\n```", parse_mode="Markdown")
    else:
        await message.answer(
            f"*Правила для типа:* `{doc_type}`\n```json\n{pretty_rules}\n```",
            parse_mode="Markdown"
        )


@router.message(Command("change_rule"))
async def update_rule(message: types.Message):
    user_id = message.from_user.id
    role = get_user_role(user_id)
    if role != REVIEWER_ROLE:
        logger.warning(f"🚫 Пользователь {user_id} попытался изменить правило без прав.")
        await message.answer("У вас нет прав для изменения правил.")
        return

    parts = message.text.split()
    if len(parts) < 4:
        await message.answer("Использование: /change_rule <тип_документа> <ключ> <новое_значение>")
        return

    doc_type, rule_key, new_value = parts[1], parts[2], " ".join(parts[3:])
    logger.debug(f"📝 Нормоконтролер {user_id} меняет правило {rule_key} для {doc_type} на {new_value}")
    result = change_rule(doc_type, rule_key, new_value)
    if result:
        await message.answer(result.get("message", "Правило изменено."))
    else:
        await message.answer("Ошибка при изменении правила.")


@router.message(Command("change_rule_for_all"))
async def handle_change_rule_for_all(message: types.Message):
    user_id = message.from_user.id
    role = get_user_role(user_id)
    if role != REVIEWER_ROLE:
        logger.warning(f"🚫 Пользователь {user_id} попытался изменить правило без прав.")
        await message.answer("У вас нет прав для изменения правил.")
        return

    parts = message.text.split()
    if len(parts) < 3:
        await message.answer("Использование: /change_rule_for_all <ключ> <новое_значение>")
        return

    rule_key = parts[1]
    new_value = " ".join(parts[2:])

    result = change_rule_for_all(rule_key, new_value)
    if result:
        text = result.get("message", "Правило изменено.")
        if "errors" in result:
            text += "\n\nОшибки:\n" + "\n".join(result["errors"])
        await message.answer(text)
    else:
        await message.answer("Ошибка при массовом изменении правила.")


def register(dp):
    dp.include_router(router)
