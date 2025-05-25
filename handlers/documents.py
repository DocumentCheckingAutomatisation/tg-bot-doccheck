from datetime import datetime

from aiogram import F
from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message

from db import save_check_result
from logger import logger
from services.api import validate_docx_document, validate_latex_document

router = Router()

MAX_STATE_LIFETIME = 300


class DocxCheck(StatesGroup):
    waiting_for_file = State()
    waiting_for_type = State()


class LatexCheck(StatesGroup):
    waiting_for_tex = State()
    waiting_for_sty = State()
    waiting_for_type = State()


VALID_TYPES = ["diploma", "course_work", "practice_report"]


def get_valid_types_str():
    return ", ".join(doc_type.replace("_", "_") for doc_type in VALID_TYPES)


async def check_file_size(message: Message, max_size_mb: int = 25) -> bool:
    if message.document.file_size > max_size_mb * 1024 * 1024:
        await message.answer(f"❌ Файл слишком большой. Максимальный размер — {max_size_mb} МБ.")
        logger.warning(f"Файл от пользователя {message.from_user.id} превышает размер {max_size_mb} МБ")
        return False
    return True


async def is_state_expired(state: FSMContext) -> bool:
    data = await state.get_data()
    start_time = data.get("start_time")
    if not start_time:
        return False
    now = datetime.now().timestamp()
    return (now - start_time) > MAX_STATE_LIFETIME


async def send_long_message(message: Message, text: str):
    max_length = 4096
    for i in range(0, len(text), max_length):
        await message.answer(text[i:i + max_length], parse_mode="HTML")

def format_latex_validation_result(result: dict) -> str:
    def yesno(errors: list, key: str) -> str:
        patterns = {
            "structure.chapters": ["Отсутствует обязательная глава", "Ошибка: после \\\\chapter", "Ошибка: титульный лист", "Ошибка: отсутствует \\tableofcontents"],
            "structure.sections": ["В главе"],
            "bold.relevance": ["актуальн"],
            "bold.goal": ["цель"],
            "bold.tasks": ["Не удалось найти текст введения", "ключевое слово.*задачи"],
            "bold.object": ["Не удалось найти текст введения", "ключевое слово.*предмет"],
            "bold.subject": ["Не удалось найти текст введения", "ключевое слово.*объект"],
            "bold.novelty": ["Не удалось найти текст введения", "ключевое слово.*новизн"],
            "bold.significance": ["Не удалось найти текст введения", "ключевое слово.*практическая значимость"],
            "bold.excess": ["жирный"],
            "italic": ["курсив"],
            "underline": ["подчёркивание"],
            "lists": ["Пункт списка", "Вводная часть перед списком", "во вложенном списке", "вложенного списка"],
            "pictures.links": ["Нет ссылки на рисунок", "Нет рисунка"],
            "tables.links": ["Нет ссылки на table", "Нет table", "Нет ссылки на longtable", "Нет longtable"],
            "appendices.links": ["приложение"],
            "bibliography.links": ["библиографии"],
            "order.references_before_objects": ["находится после"],
            "order.same_page": ["Слишком большое расстояние", "на той же или следующей странице"],
            "sty": ["Файл settings.sty", "Несовпадение в settings.sty"],
        }

        import re
        key_patterns = patterns.get(key, [])
        for err in errors:
            for p in key_patterns:
                if re.search(p, err, re.IGNORECASE):
                    return "Нет ❌"
        return "Да ✅"

    def get_list_summary(found: dict) -> str:
        lists = found.get("lists", {})
        return (
            f"<blockquote>Найденные списки:\n"
            f"- Нумерованные (буквы): {len(lists.get('enumasbuk', []))}\n"
            f"- Нумерованные (цифры): {len(lists.get('enumarabic', []))}\n"
            f"- Маркированные (дефис): {len(lists.get('enummarker', []))}</blockquote>"
        )

    def get_pic_summary(found: dict) -> str:
        pics = found.get("pictures", {})
        labels = ", ".join(p.get("label") for p in pics.get("labels", [])) or "нет"
        refs = ", ".join(p.get("label") for p in pics.get("refs", [])) or "нет"
        return f"<blockquote>Найденные рисунки:\n- Метка объектов: {labels}\n- Ссылки в тексте: {refs}</blockquote>"

    def get_table_summary(found: dict) -> str:
        tables = found.get("tables", {}).get("tables", {})
        labels = ", ".join(t.get("label") for t in tables.get("labels", [])) or "нет"
        refs = ", ".join(t.get("label") for t in tables.get("refs", [])) or "нет"
        return f"<blockquote>Найденные таблицы:\n- Метки объектов: {labels}\n- Ссылки в тексте: {refs}</blockquote>"

    def get_chapters(found: dict) -> str:
        structure = found.get("structure", {})
        unnum = ", ".join(structure.get("unnumbered_chapters", [])) or "нет"
        num = ", ".join(structure.get("numbered_chapters", [])) or "нет"
        return f"<blockquote> Главы:\n- Ненумерованные: {unnum}\n- Нумерованные: {num} </blockquote>"

    def get_sections(found: dict) -> str:
        structure = found.get("structure", {})
        sec = structure.get("numbered_sections", {})
        unsec = structure.get("unnumbered_sections", {})

        def format_sec(sec_dict, title):
            entries = sec_dict.get(title, [])
            return ", ".join(entries) if entries else "нет"

        return (
            f"<blockquote>Разделы:\n"
            f"- 1 глава: нумерованные: {format_sec(sec, '1 глава')}, ненумерованные: {format_sec(unsec, '1 глава')}\n"
            f"- 2 глава: нумерованные: {format_sec(sec, '2 глава')}, ненумерованные: {format_sec(unsec, '2 глава')}</blockquote>"
        )

    def format_readable() -> str:
        errors = result.get("errors", [])
        found = result.get("found", {})

        aspects = [
            ("Необходимые главы", yesno(errors, "structure.chapters"), get_chapters(found)),
            ("Необходимые разделы", yesno(errors, "structure.sections"), get_sections(found)),
            ("Цель выделена жирным", yesno(errors, "bold.goal")),
            ("Задачи выделены жирным", yesno(errors, "bold.tasks")),
            ("Актуальность жирным", yesno(errors, "bold.relevance")),
            ("Объект выделен жирным", yesno(errors, "bold.subject")),
            ("Предмет выделен жирным", yesno(errors, "bold.object")),
            ("Новизна выделена жирным", yesno(errors, "bold.novelty")),
            ("Практич. значимость жирным", yesno(errors, "bold.significance")),
            ("Нет лишнего жирного", yesno(errors, "bold.excess")),
            ("Нет курсива", yesno(errors, "italic")),
            ("Нет подчеркиваний", yesno(errors, "underline")),
            ("Списки оформлены корректно", yesno(errors, "lists"), get_list_summary(found)),
            ("Рисунки и ссылки на них", yesno(errors, "pictures.links"), get_pic_summary(found)),
            ("Таблицы и ссылки на них", yesno(errors, "tables.links"), get_table_summary(found)),
            ("Приложения и ссылки на них", yesno(errors, "appendices.links")),
            ("Источники и ссылки на них", yesno(errors, "bibliography.links")),
            ("Ссылки находятся до рисунка/таблицы", yesno(errors, "order.references_before_objects")),
            ("Ссылки на той же/соседней странице от рис./табл.", yesno(errors, "order.same_page")),
            ("Файл settings.sty соответствует требованиям", yesno(errors, "sty")),
        ]

        lines = []
        for aspect in aspects:
            if len(aspect) == 2:
                name, validity = aspect
                lines.append(f"🔹{name}: {validity}\n")
            else:
                name, validity, detail = aspect
                lines.append(f"🔹{name} — {validity} {detail}\n")

        return "\n".join(lines)

    def format_errors(errors: list) -> str:
        return "\n".join(f"📌 {e}\n" for e in errors) if errors else "Ошибок не найдено😊"

    valid = "Да ✅" if result.get("valid", True) else "Нет ❌"
    check_results = format_readable()
    errors_text = format_errors(result.get("errors", []))

    return (
        f"📋 <b>Результат проверки LaTeX-документа</b>\n\n"
        f"💬 <u><b>Правильное оформление:</b></u> {valid}\n\n"
        f"🔎 <u><b>Детали проверки:</b></u>\n{check_results}\n"
        f"⚠️ <u><b>Обнаруженные ошибки:</b></u>\n\n{errors_text}"
    )


def format_docx_validation_result(result: dict) -> str:
    valid = "✅ Да" if result.get("valid", True) else "❌ Нет"

    found = result.get("found")
    if found:
        found_list = "\n".join(f"- {item}" for item in found)
    else:
        found_list = "_Элементы не найдены.(в разработке)_"

    errors = result.get("errors")
    if errors:
        errors_list = "\n".join(f"- {error}" for error in errors)
    else:
        errors_list = "_Ошибок нет._"

    formatted_text = (
        f"📋 Результат проверки документа:\n\n"
        f"💬 *Правильность оформления:* {valid}\n\n"
        f"🔎 *Найденные элементы:*\n{found_list}\n\n"
        f"⚠️ *Ошибки:*\n{errors_list}"
    )
    return formatted_text


@router.message(Command("check_docx"))
async def handle_docx_check(message: Message, state: FSMContext):
    logger.info(f"Пользователь {message.from_user.id} начал проверку docx")
    parts = message.text.split(maxsplit=1)
    if len(parts) >= 2:
        doc_type = parts[1].strip().lower().replace(" ", "_")
        logger.debug(f"Пользователь {message.from_user.id} ввел тип документа docx: {doc_type}")
        if doc_type not in VALID_TYPES:
            logger.warning(f"Пользователь {message.from_user.id} указал неверный тип docx: {doc_type}")
            await message.answer(
                f"❌ Неизвестный тип документа: {doc_type}.\n"
                f"✅ Возможные типы: {get_valid_types_str()}.\n"
                f"Попробуйте снова: `/check_docx diploma` или просто `/check_docx` и следуйте инструкциям.",
                parse_mode="Markdown"
            )
            return
        await state.update_data(start_time=datetime.now().timestamp())
        await state.set_state(DocxCheck.waiting_for_file)
        await message.answer(f"Тип документа: {doc_type}\nТеперь отправьте .docx файл для проверки.")
    else:
        await state.update_data(start_time=datetime.now().timestamp())
        await state.set_state(DocxCheck.waiting_for_file)
        await message.answer("Пожалуйста, отправьте .docx файл для проверки.")


@router.message(DocxCheck.waiting_for_file, F.document)
async def handle_docx_file(message: Message, state: FSMContext):
    if await is_state_expired(state):
        logger.info(f"Сессия истекла для пользователя {message.from_user.id}")
        await message.answer(
            "⌛ Слишком долго не было ответа. Начните проверку заново командой /check_docx или /check_latex.")
        await state.clear()
        return

    if not message.document.file_name.endswith(".docx"):
        logger.warning(
            f"Пользователь {message.from_user.id} отправил файл с неправильным расширением: {message.document.file_name}")
        await message.answer("Пожалуйста, отправьте файл с расширением .docx")
        return
    if not await check_file_size(message):
        return

    await state.update_data(file=message.document)

    data = await state.get_data()
    logger.info(f"Пользователь {message.from_user.id} отправил файл {message.document.file_name}")

    if "doc_type" in data:
        file_obj = await message.bot.get_file(data["file"].file_id)
        file = await message.bot.download_file(file_obj.file_path)

        logger.info(f"Началась проверка docx файла {data['file'].file_name} для пользователя {message.from_user.id}")
        await message.answer("⏳ Проверка документа началась, подождите немного...")

        result = validate_docx_document(file, data["file"].file_name, data["doc_type"])

        if result.get("error"):
            r = result.get("error")
            logger.error(f"Ошибка при проверке docx: {r}")
            await message.answer(f"❌ Произошла ошибка при проверке документа: {r}")
        else:
            logger.info(f"Проверка docx завершена для пользователя {message.from_user.id}")
            save_check_result(
                user_id=message.from_user.id,
                doc_type=data["doc_type"],
                check_type="docx",
                result=bool(result['valid'])
            )
            logger.debug(f"Проверка latex по пользователю {message.from_user.id} записана в таблицу users_checks")
            res = format_docx_validation_result(result)
            # await message.answer(res, parse_mode="Markdown")
            await send_long_message(message, res)
            logger.debug(f"Проверка docx завершена для пользователя {message.from_user.username} c результатом {res}")

        # result = validate_docx_document(file, data["file"].file_name, data["doc_type"])
        #
        # logger.info(f"Проверка docx завершена для пользователя {message.from_user.id}")
        # await message.answer(format_validation_result(result), parse_mode="Markdown")

        await state.clear()
    else:
        await state.update_data(start_time=datetime.now().timestamp())
        await state.set_state(DocxCheck.waiting_for_type)
        await message.answer(f"Теперь укажите тип документа: {get_valid_types_str()}")


@router.message(DocxCheck.waiting_for_type)
async def handle_docx_type(message: Message, state: FSMContext):
    if await is_state_expired(state):
        logger.info(f"Сессия истекла для пользователя {message.from_user.id}")
        await message.answer(
            "⌛ Слишком долго не было ответа. Начните проверку заново командой /check_docx или /check_latex.")
        await state.clear()
        return

    doc_type = message.text.strip().lower().replace(" ", "_")
    logger.debug(f"Пользователь {message.from_user.id} ввёл тип документа docx: {doc_type}")
    if doc_type not in VALID_TYPES:
        logger.warning(f"Пользователь {message.from_user.id} указал неверный тип docx: {doc_type}")
        await message.answer(f"Неверный тип документа. Возможные типы: {get_valid_types_str()}.")
        return

    data = await state.get_data()
    file_obj = await message.bot.get_file(data["file"].file_id)
    file = await message.bot.download_file(file_obj.file_path)

    logger.info(f"Началась проверка docx файла {data['file'].file_name} для пользователя {message.from_user.id}")
    await message.answer("⏳ Проверка документа началась, подождите немного...")

    result = validate_docx_document(file, data["file"].file_name, doc_type)

    if result.get("error"):
        r = result.get("error")
        logger.error(f"Ошибка при проверке docx: {r}")
        await message.answer(f"❌ Произошла ошибка при проверке документа: {r}")
    else:
        logger.info(f"Проверка docx завершена для пользователя {message.from_user.id}")
        save_check_result(
            user_id=message.from_user.id,
            doc_type=doc_type,
            check_type="docx",
            result=bool(result['valid'])
        )
        logger.debug(f"Проверка latex по пользователю {message.from_user.id} записана в таблицу users_checks")
        res = format_docx_validation_result(result)
        # await message.answer(res, parse_mode="Markdown")
        await send_long_message(message, res)
        logger.debug(f"Проверка docx завершена для пользователя {message.from_user.username} c результатом {res}")

    # result = validate_docx_document(file, data["file"].file_name, doc_type)
    # logger.info(f"Проверка docx завершена для пользователя {message.from_user.id}")
    # await message.answer(format_validation_result(result), parse_mode="Markdown")

    await state.clear()


@router.message(Command("check_latex"))
async def handle_latex_check(message: Message, state: FSMContext):
    parts = message.text.split(maxsplit=1)
    if len(parts) >= 2:
        doc_type = parts[1].strip().lower().replace(" ", "_")
        logger.debug(f"Пользователь {message.from_user.id} ввел тип документа LaTeX: {doc_type}")
        if doc_type not in VALID_TYPES:
            logger.warning(f"Пользователь {message.from_user.id} ввел недопустимый тип LaTeX: {doc_type}")
            await message.answer(
                f"❌ Неизвестный тип документа: {doc_type}.\n"
                f"✅ Возможные типы: {get_valid_types_str()}.\n"
                f"Попробуйте снова: `/check_latex diploma` или просто `/check_latex` и следуйте инструкциям.",
                parse_mode="Markdown"
            )
            return
        await state.update_data(start_time=datetime.now().timestamp())
        await state.set_state(LatexCheck.waiting_for_tex)
        await message.answer(f"Тип документа: {doc_type}\nПожалуйста, отправьте .tex файл.")
    else:
        await state.update_data(start_time=datetime.now().timestamp())
        await state.set_state(LatexCheck.waiting_for_tex)
        await message.answer("Пожалуйста, отправьте .tex файл.")


@router.message(LatexCheck.waiting_for_tex, F.document)
async def handle_latex_tex(message: Message, state: FSMContext):
    if await is_state_expired(state):
        logger.info(f"Сессия истекла для пользователя {message.from_user.id} (этап .tex)")
        await message.answer(
            "⌛ Слишком долго не было ответа. Начните проверку заново командой /check_docx или /check_latex.")
        await state.clear()
        return

    if not message.document.file_name.endswith(".tex"):
        logger.warning(f"Пользователь {message.from_user.id} отправил не .tex файл: {message.document.file_name}")
        await message.answer("Пожалуйста, отправьте файл с расширением .tex")
        return
    if not await check_file_size(message):
        return

    await state.update_data(start_time=datetime.now().timestamp())
    await state.update_data(tex=message.document)
    await state.set_state(LatexCheck.waiting_for_sty)
    await message.answer("Теперь отправьте .sty файл.")


@router.message(LatexCheck.waiting_for_sty, F.document)
async def handle_latex_sty(message: Message, state: FSMContext):
    if await is_state_expired(state):
        logger.info(f"Сессия истекла для пользователя {message.from_user.id} (этап .sty)")
        await message.answer(
            "⌛ Слишком долго не было ответа. Начните проверку заново командой /check_docx или /check_latex.")
        await state.clear()
        return

    if not message.document.file_name.endswith(".sty"):
        logger.warning(f"Пользователь {message.from_user.id} отправил не .sty файл: {message.document.file_name}")
        await message.answer("Пожалуйста, отправьте файл с расширением .sty")
        return
    if not await check_file_size(message):
        return

    await state.update_data(sty=message.document)

    data = await state.get_data()
    if "doc_type" in data:
        await process_latex_validation(message, state)
    else:
        await state.update_data(start_time=datetime.now().timestamp())
        await state.set_state(LatexCheck.waiting_for_type)
        await message.answer(f"Теперь укажите тип документа: {get_valid_types_str()}")


@router.message(LatexCheck.waiting_for_type)
async def handle_latex_type(message: Message, state: FSMContext):
    if await is_state_expired(state):
        logger.info(f"Сессия истекла для пользователя {message.from_user.id} (этап выбора типа для latex)")
        await message.answer(
            "⌛ Слишком долго не было ответа. Начните проверку заново командой /check_docx или /check_latex.")
        await state.clear()
        return

    doc_type = message.text.strip().lower().replace(" ", "_")
    logger.debug(f"Пользователь {message.from_user.id} ввел тип LaTeX-документа: {doc_type}")
    if doc_type not in VALID_TYPES:
        logger.warning(f"Пользователь {message.from_user.id} указал недопустимый тип документа LaTeX: {doc_type}")
        await message.answer(f"Неверный тип документа. Возможные типы: {get_valid_types_str()}.")
        return
    await state.update_data(doc_type=doc_type)
    await process_latex_validation(message, state)


async def process_latex_validation(message: Message, state: FSMContext):
    data = await state.get_data()
    tex_file_info = await message.bot.get_file(data["tex"].file_id)
    tex_file = await message.bot.download_file(tex_file_info.file_path)

    sty_file_info = await message.bot.get_file(data["sty"].file_id)
    sty_file = await message.bot.download_file(sty_file_info.file_path)

    logger.info(f"Началась проверка LaTeX-документов для пользователя {message.from_user.id}")
    await message.answer("⏳ Проверка документа началась, подождите немного...")

    result = validate_latex_document(
        tex_file, data["tex"].file_name,
        sty_file, data["sty"].file_name,
        data["doc_type"]
    )


    if result.get("error"):
        r = result.get("error")
        logger.error(f"Ошибка при проверке latex: {r}")
        await message.answer(f"❌ Произошла ошибка при проверке документа: {r}")
    else:
        logger.info(f"Проверка latex завершена для пользователя {message.from_user.id}")
        save_check_result(
            user_id=message.from_user.id,
            doc_type=data["doc_type"],
            check_type="latex",
            result=bool(result['valid'])
        )
        logger.debug(f"Проверка latex по пользователю {message.from_user.id} записана в таблицу users_checks")
        res = format_latex_validation_result(result)
        await send_long_message(message, res)
        logger.debug(f"Проверка docx завершена для пользователя {message.from_user.username} c результатом {res}")

    # logger.info(f"Проверка LaTeX завершена для пользователя {message.from_user.id}")
    # await message.answer(format_validation_result(result), parse_mode="Markdown")

    await state.clear()


def register(dp):
    dp.include_router(router)
