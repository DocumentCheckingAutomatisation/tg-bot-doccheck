import json
from datetime import datetime

from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from db import get_user_role, REVIEWER_ROLE
from logger import logger
from services.api import get_doc_options, get_rules, change_rule, change_rule_for_all

router = Router()

MAX_STATE_LIFETIME = 300


class RuleStates(StatesGroup):
    waiting_for_doc_type = State()


def get_valid_doc_types():
    options = get_doc_options()
    return [opt["name"].lower() for opt in options] if options else []


async def is_state_expired(state: FSMContext) -> bool:
    data = await state.get_data()
    start_time = data.get("start_time")
    if not start_time:
        return False
    now = datetime.now().timestamp()
    return (now - start_time) > MAX_STATE_LIFETIME


@router.message(Command("types"))
async def available_types(message: types.Message):
    logger.debug(f"Пользователь {message.from_user.id} запросил типы документов")
    options = get_doc_options()
    if options:
        text = "\n".join(opt["name"].lower().replace("_", "\\_") for opt in options)
        await message.answer(f"*Доступные типы документов:*\n{text}", parse_mode="Markdown")
    else:
        await message.answer("❌ Ошибка при получении типов документов.")


@router.message(Command("rules"))
async def show_rules(message: types.Message, state: FSMContext):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await state.update_data(start_time=datetime.now().timestamp())
        await message.answer("✏️ Укажите тип документа (например: diploma, course_work, practice_report).")
        await state.set_state(RuleStates.waiting_for_doc_type)
        return

    doc_type = parts[1].strip().lower().replace(" ", "_")
    await process_doc_type_internal(message, doc_type, state)


@router.message(RuleStates.waiting_for_doc_type)
async def process_doc_type(message: types.Message, state: FSMContext):
    if await is_state_expired(state):
        await message.answer("⌛ Слишком долго не было ответа. Начните заново командой /rules.")
        await state.clear()
        return

    doc_type = message.text.strip().lower().replace(" ", "_")
    await process_doc_type_internal(message, doc_type, state)


async def process_doc_type_internal(message: types.Message, doc_type: str, state: FSMContext):
    valid_types = get_valid_doc_types()

    if doc_type not in valid_types:
        ds = '\\'
        text = "❌ Неверный тип документа.\n\n*Доступные типы:*\n" + "\n".join(
            f"- {t.replace('_', f'{ds}_')}" for t in valid_types)
        await state.update_data(start_time=datetime.now().timestamp())
        await message.answer(text, parse_mode="Markdown")
        await state.set_state(RuleStates.waiting_for_doc_type)
        return

    await send_rules(message, doc_type)
    await state.clear()


async def send_rules(message: types.Message, doc_type: str):
    logger.debug(f"Пользователь {message.from_user.id} запросил правила для {doc_type}")
    rules = get_rules(doc_type)

    if not rules:
        await message.answer("❌ Ошибка при получении правил.")
        return

    user_id = message.from_user.id
    role = get_user_role(user_id)

    if role == REVIEWER_ROLE:
        pretty_rules = json.dumps(rules, indent=2, ensure_ascii=False)
    else:
        pretty_rules = format_rules_for_students(rules)

    max_length = 4000

    if len(pretty_rules) > max_length:
        chunks = [pretty_rules[i:i + max_length] for i in range(0, len(pretty_rules), max_length)]
        await message.answer(f"*Правила для типа:* `{doc_type}`", parse_mode="Markdown")
        for chunk in chunks:
            await message.answer(f"```\n{chunk}\n```", parse_mode="Markdown")
    else:
        await message.answer(
            f"*Правила для типа:* `{doc_type}`\n```\n{pretty_rules}\n```",
            parse_mode="Markdown"
        )


def format_rules_for_students(rules: dict) -> str:
    parts = []
    common = rules.get("common_rules", {})
    if common:
        parts.append("\n📄 *Общие требования к оформлению:*")
        parts.append(f"• Шрифт: {common.get('font', '?')}, {common.get('font_size', '?')} пт")
        parts.append(f"• Межстрочный интервал: {common.get('line_spacing', '?')}")
        parts.append(f"• Абзацный отступ: {common.get('paragraph_indent', '?')} см")
        margins = common.get("margins", {})
        parts.append(f"• Поля: верхнее — {margins.get('top', '?')} мм, нижнее — {margins.get('bottom', '?')} мм, "
                     f"левое — {margins.get('left', '?')} мм, правое — {margins.get('right', '?')} мм")
        align = common.get("alignment", {})
        parts.append(
            f"• Выравнивание текста: {align.get('text', '?')}, номера страниц — {align.get('page_numbers', '?')}")

    structure = rules.get("structure_rules", {})
    if structure:
        parts.append("\n📚 *Структура документа:*")
        chapters = structure.get("required_chapters", [])
        if chapters:
            parts.append("• Обязательные главы:")
            for ch in chapters:
                parts.append(f"  — {ch}")
        sections = structure.get("required_sections", {})
        if sections:
            parts.append("• Требуемые разделы по главам:")
            for ch, secs in sections.items():
                parts.append(f"  Глава {ch}:")
                for s in secs:
                    parts.append(f"    — {s}")
        intro = structure.get("introduction_keywords", [])
        if intro:
            parts.append("• Во введении должны быть и выделены жирным:")
            for i in intro:
                parts.append(f"  — {i}")

    design = rules.get("design_rules", {})
    if design:
        parts.append("\n🎨 *Оформление элементов:*")
        if "chapter" in design:
            parts.append("• Главы: заголовки по центру, полужирные, 14 пт, заглавные буквы")
        if "section" in design:
            parts.append("• Разделы: заголовки слева, полужирные, 14 пт")
        if "subsection" in design:
            parts.append("• Подразделы: заголовки слева, обычные, 14 пт")
        if "list" in design:
            parts.append("• Списки: могут быть нумерованными цифрой (1) или буквой (а) или маркированными (-)")
        if "table" in design:
            parts.append("• Таблицы: подписи по центру, ссылки вида '(табл. 1.1)'")
        if "picture" in design:
            parts.append("• Рисунки: подписи по центру, ссылки вида '(рис. 1.1)'")

    return "\n".join(parts)


@router.message(Command("change_rule"))
async def update_rule(message: types.Message):
    user_id = message.from_user.id
    role = get_user_role(user_id)
    if role != REVIEWER_ROLE:
        logger.warning(f"Пользователь {user_id} попытался изменить правило без прав.")
        await message.answer("🚫 У вас нет прав для изменения правил.")
        return

    parts = message.text.split()
    if len(parts) < 4:
        await message.answer("Использование: /change_rule <тип_документа> <ключ> <новое_значение>")
        return

    # doc_type = parts[1].strip().lower().replace(" ", "_")
    # rule_key = parts[2]
    # new_value = parts[3]
    doc_type, rule_key, new_value = parts[1], parts[2], " ".join(parts[3:])

    logger.debug(f"Нормоконтролер {user_id} меняет правило {rule_key} для {doc_type} на {new_value}")
    result = change_rule(doc_type, rule_key, new_value)
    if result:
        await message.answer(result.get("message", "✅ Правило изменено."))
    else:
        await message.answer("❌ Ошибка при изменении правила.")


@router.message(Command("change_rule_for_all"))
async def handle_change_rule_for_all(message: types.Message):
    user_id = message.from_user.id
    role = get_user_role(user_id)
    if role != REVIEWER_ROLE:
        logger.warning(f"Пользователь {user_id} попытался изменить правило без прав.")
        await message.answer("🚫 У вас нет прав для изменения правил.")
        return

    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        await message.answer("Использование: /change_rule_for_all <ключ> <новое_значение>")
        return

    rule_key = parts[1]
    new_value = " ".join(parts[2:])

    # rule_key = parts[1]
    # new_value = parts[2]

    result = change_rule_for_all(rule_key, new_value)
    if result:
        text = result.get("message", "✅ Правило изменено.")
        if "errors" in result:
            text += "\n\n⚠️ Ошибки:\n" + "\n".join(result["errors"])
        await message.answer(text)
    else:
        await message.answer("❌ Ошибка при массовом изменении правила.")


def register(dp):
    dp.include_router(router)
