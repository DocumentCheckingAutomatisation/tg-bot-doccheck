# тип документа можно писать вместе с командой или бот спросит потом

from aiogram import F
from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message

from services.api import validate_docx_document, validate_latex_document

router = Router()

class DocxCheck(StatesGroup):
    waiting_for_file = State()
    waiting_for_type = State()

class LatexCheck(StatesGroup):
    waiting_for_tex = State()
    waiting_for_sty = State()
    waiting_for_type = State()

VALID_TYPES = ["diploma", "course_work", "practice_report"]

def get_valid_types_str():
    return ", ".join(doc_type.replace("_", "\\_") for doc_type in VALID_TYPES)

@router.message(Command("check_docx"))
async def handle_docx_check(message: Message, state: FSMContext):
    parts = message.text.split()
    if len(parts) >= 2:
        doc_type = parts[1].lower()
        if doc_type not in VALID_TYPES:
            await message.answer(
                f"❌ Неизвестный тип документа: {doc_type}.\n"
                f"✅ Возможные типы: {get_valid_types_str()}.\n"
                f"Попробуйте снова: `/check_docx diploma` или просто `/check_docx` и следуйте инструкциям.",
                parse_mode="Markdown"
            )
            return
        await state.update_data(doc_type=doc_type)
        await message.answer(f"Тип документа: {doc_type}\nТеперь отправьте .docx файл для проверки.")
        await state.set_state(DocxCheck.waiting_for_file)
    else:
        await message.answer("Пожалуйста, отправьте .docx файл для проверки.")
        await state.set_state(DocxCheck.waiting_for_file)

@router.message(DocxCheck.waiting_for_file, F.document)
async def handle_docx_file(message: Message, state: FSMContext):
    if not message.document.file_name.endswith(".docx"):
        await message.answer("Пожалуйста, отправьте файл с расширением .docx")
        return
    await state.update_data(file=message.document)

    data = await state.get_data()
    if "doc_type" in data:
        # Тип документа уже указан заранее
        file_obj = await message.bot.get_file(data["file"].file_id)
        file = await message.bot.download_file(file_obj.file_path)

        result = validate_docx_document(file, data["file"].file_name, data["doc_type"])
        await message.answer(f"Результат проверки:\n{result}")
        await state.clear()
    else:
        # Тип документа не указан — спрашиваем его
        await message.answer(f"Теперь укажите тип документа: {get_valid_types_str()}")
        await state.set_state(DocxCheck.waiting_for_type)

@router.message(DocxCheck.waiting_for_type)
async def handle_docx_type(message: Message, state: FSMContext):
    doc_type = message.text.strip().lower()
    if doc_type not in VALID_TYPES:
        await message.answer(f"Неверный тип документа. Возможные типы: {get_valid_types_str()}.")
        return

    data = await state.get_data()
    file_obj = await message.bot.get_file(data["file"].file_id)
    file = await message.bot.download_file(file_obj.file_path)

    result = validate_docx_document(file, data["file"].file_name, doc_type)
    await message.answer(f"Результат проверки:\n{result}")
    await state.clear()

@router.message(Command("check_latex"))
async def handle_latex_check(message: Message, state: FSMContext):
    parts = message.text.split()
    if len(parts) >= 2:
        doc_type = parts[1].lower()
        if doc_type not in VALID_TYPES:
            await message.answer(
                f"❌ Неизвестный тип документа: {doc_type}.\n"
                f"✅ Возможные типы: {get_valid_types_str()}.\n"
                f"Попробуйте снова: `/check_latex diploma` или просто `/check_latex` и следуйте инструкциям.",
                parse_mode="Markdown"
            )
            return
        await state.update_data(doc_type=doc_type)
        await message.answer(f"Тип документа: {doc_type}\nПожалуйста, отправьте .tex файл.")
        await state.set_state(LatexCheck.waiting_for_tex)
    else:
        await message.answer("Пожалуйста, отправьте .tex файл.")
        await state.set_state(LatexCheck.waiting_for_tex)

@router.message(LatexCheck.waiting_for_tex, F.document)
async def handle_latex_tex(message: Message, state: FSMContext):
    if not message.document.file_name.endswith(".tex"):
        await message.answer("Пожалуйста, отправьте файл с расширением .tex")
        return
    await state.update_data(tex=message.document)
    await message.answer("Теперь отправьте .sty файл.")
    await state.set_state(LatexCheck.waiting_for_sty)

@router.message(LatexCheck.waiting_for_sty, F.document)
async def handle_latex_sty(message: Message, state: FSMContext):
    if not message.document.file_name.endswith(".sty"):
        await message.answer("Пожалуйста, отправьте файл с расширением .sty")
        return
    await state.update_data(sty=message.document)

    data = await state.get_data()
    if "doc_type" in data:
        await process_latex_validation(message, state)
    else:
        await message.answer(f"Теперь укажите тип документа: {get_valid_types_str()}")
        await state.set_state(LatexCheck.waiting_for_type)

@router.message(LatexCheck.waiting_for_type)
async def handle_latex_type(message: Message, state: FSMContext):
    doc_type = message.text.strip().lower()
    if doc_type not in VALID_TYPES:
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

    result = validate_latex_document(
        tex_file, data["tex"].file_name,
        sty_file, data["sty"].file_name,
        data["doc_type"]
    )
    await message.answer(f"Результат проверки:\n{result}")
    await state.clear()

def register(dp):
    dp.include_router(router)




# тип документа сразу с командой

# from aiogram import F, Router
# from aiogram.filters import Command
# from aiogram.fsm.context import FSMContext
# from aiogram.fsm.state import State, StatesGroup
# from aiogram.types import Message
#
# from services.api import validate_docx_document, validate_latex_document
#
# router = Router()
#
# VALID_DOC_TYPES = ["diploma", "course_work", "practice_report"]
#
#
# class DocxCheck(StatesGroup):
#     waiting_for_file = State()
#     waiting_for_type = State()
#
#
# class LatexCheck(StatesGroup):
#     waiting_for_tex = State()
#     waiting_for_sty = State()
#     waiting_for_type = State()
#
#
# @router.message(Command("check_docx"))
# async def handle_docx_check(message: Message, state: FSMContext):
#     parts = message.text.strip().split()
#     if len(parts) == 2 and parts[1].lower() in VALID_DOC_TYPES:
#         await state.update_data(doc_type=parts[1].lower())
#         await message.answer("Пожалуйста, отправьте .docx файл для проверки.")
#         await state.set_state(DocxCheck.waiting_for_file)
#     else:
#         await message.answer("Использование: /check_docx <тип_документа>\nПримеры: diploma, course_work, practice_report")
#
#
# @router.message(DocxCheck.waiting_for_file, F.document)
# async def handle_docx_file(message: Message, state: FSMContext):
#     if not message.document.file_name.endswith(".docx"):
#         await message.answer("Пожалуйста, отправьте файл с расширением .docx")
#         return
#
#     data = await state.get_data()
#     doc_type = data.get("doc_type")
#     if not doc_type:
#         await message.answer("Ошибка: не задан тип документа.")
#         return
#
#     file_obj = await message.bot.get_file(message.document.file_id)
#     file = await message.bot.download_file(file_obj.file_path)
#
#     result = validate_docx_document(file, message.document.file_name, doc_type)
#     await message.answer(f"Результат проверки:\n{result}")
#     await state.clear()
#
#
# @router.message(Command("check_latex"))
# async def handle_latex_check(message: Message, state: FSMContext):
#     parts = message.text.strip().split()
#     if len(parts) == 2 and parts[1].lower() in VALID_DOC_TYPES:
#         await state.update_data(doc_type=parts[1].lower())
#         await message.answer("Пожалуйста, отправьте .tex файл.")
#         await state.set_state(LatexCheck.waiting_for_tex)
#     else:
#         await message.answer("Использование: /check_latex <тип_документа>\nПримеры: diploma, course_work, practice_report")
#
#
# @router.message(LatexCheck.waiting_for_tex, F.document)
# async def handle_latex_tex(message: Message, state: FSMContext):
#     if not message.document.file_name.endswith(".tex"):
#         await message.answer("Пожалуйста, отправьте файл с расширением .tex")
#         return
#
#     await state.update_data(tex=message.document)
#     await message.answer("Теперь отправьте .sty файл.")
#     await state.set_state(LatexCheck.waiting_for_sty)
#
#
# @router.message(LatexCheck.waiting_for_sty, F.document)
# async def handle_latex_sty(message: Message, state: FSMContext):
#     if not message.document.file_name.endswith(".sty"):
#         await message.answer("Пожалуйста, отправьте файл с расширением .sty")
#         return
#
#     await state.update_data(sty=message.document)
#     data = await state.get_data()
#     if not data.get("doc_type"):
#         await message.answer("Ошибка: не задан тип документа.")
#         return
#
#     tex_file_info = await message.bot.get_file(data["tex"].file_id)
#     tex_file = await message.bot.download_file(tex_file_info.file_path)
#
#     sty_file_info = await message.bot.get_file(data["sty"].file_id)
#     sty_file = await message.bot.download_file(sty_file_info.file_path)
#
#     result = validate_latex_document(
#         tex_file, data["tex"].file_name,
#         sty_file, data["sty"].file_name,
#         data["doc_type"]
#     )
#     await message.answer(f"Результат проверки:\n{result}")
#     await state.clear()
#
#
# def register(dp):
#     dp.include_router(router)


# отдельный вопрос про тип документа

# from aiogram import F
# from aiogram import Router
# from aiogram.filters import Command
# from aiogram.fsm.context import FSMContext
# from aiogram.fsm.state import State, StatesGroup
# from aiogram.types import Message
#
# from services.api import validate_docx_document, validate_latex_document
#
# router = Router()
#
#
# class DocxCheck(StatesGroup):
#     waiting_for_file = State()
#     waiting_for_type = State()
#
#
# class LatexCheck(StatesGroup):
#     waiting_for_tex = State()
#     waiting_for_sty = State()
#     waiting_for_type = State()
#
#
# @router.message(Command("check_docx"))
# async def handle_docx_check(message: Message, state: FSMContext):
#     await message.answer("Пожалуйста, отправьте .docx файл для проверки.")
#     await state.set_state(DocxCheck.waiting_for_file)
#
#
# @router.message(DocxCheck.waiting_for_file, F.document)
# async def handle_docx_file(message: Message, state: FSMContext):
#     if not message.document.file_name.endswith(".docx"):
#         await message.answer("Пожалуйста, отправьте файл с расширением .docx")
#         return
#     await state.update_data(file=message.document)
#     await message.answer("Теперь укажите тип документа: diploma, course_work или practice_report")
#     await state.set_state(DocxCheck.waiting_for_type)
#
#
# @router.message(DocxCheck.waiting_for_type)
# async def handle_docx_type(message: Message, state: FSMContext):
#     doc_type = message.text.strip().lower()
#     if doc_type not in ["diploma", "course_work", "practice_report"]:
#         await message.answer("Неверный тип документа. Попробуйте снова.")
#         return
#
#     data = await state.get_data()
#     file_obj = await message.bot.get_file(data["file"].file_id)
#     file = await message.bot.download_file(file_obj.file_path)
#
#     result = validate_docx_document(file, data["file"].file_name, doc_type)
#     await message.answer(f"Результат проверки:\n{result}")
#     await state.clear()
#
#
# @router.message(Command("check_latex"))
# async def handle_latex_check(message: Message, state: FSMContext):
#     await message.answer("Пожалуйста, отправьте .tex файл.")
#     await state.set_state(LatexCheck.waiting_for_tex)
#
#
# @router.message(LatexCheck.waiting_for_tex, F.document)
# async def handle_latex_tex(message: Message, state: FSMContext):
#     if not message.document.file_name.endswith(".tex"):
#         await message.answer("Пожалуйста, отправьте файл с расширением .tex")
#         return
#     await state.update_data(tex=message.document)
#     await message.answer("Теперь отправьте .sty файл.")
#     await state.set_state(LatexCheck.waiting_for_sty)
#
#
# @router.message(LatexCheck.waiting_for_sty, F.document)
# async def handle_latex_sty(message: Message, state: FSMContext):
#     if not message.document.file_name.endswith(".sty"):
#         await message.answer("Пожалуйста, отправьте файл с расширением .sty")
#         return
#     await state.update_data(sty=message.document)
#     await message.answer("Теперь укажите тип документа: diploma, course_work или practice_report")
#     await state.set_state(LatexCheck.waiting_for_type)
#
#
# @router.message(LatexCheck.waiting_for_type)
# async def handle_latex_type(message: Message, state: FSMContext):
#     doc_type = message.text.strip().lower()
#     if doc_type not in ["diploma", "course_work", "practice_report"]:
#         await message.answer("Неверный тип документа. Попробуйте снова.")
#         return
#
#     data = await state.get_data()
#     tex_file_info = await message.bot.get_file(data["tex"].file_id)
#     tex_file = await message.bot.download_file(tex_file_info.file_path)
#
#     sty_file_info = await message.bot.get_file(data["sty"].file_id)
#     sty_file = await message.bot.download_file(sty_file_info.file_path)
#
#     result = validate_latex_document(
#         tex_file, data["tex"].file_name,
#         sty_file, data["sty"].file_name,
#         doc_type
#     )
#     await message.answer(f"Результат проверки:\n{result}")
#     await state.clear()
#
#
# def register(dp):
#     dp.include_router(router)
