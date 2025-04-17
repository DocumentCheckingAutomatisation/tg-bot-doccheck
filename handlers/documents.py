# === handlers/documents.py ===
from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, BufferedInputFile
from aiogram.filters import Command
from services.api import get_doc_options
from utils.helpers import is_reviewer, upload_file_and_check_single, upload_latex_and_check

router = Router()


@router.message(Command("documents"))
async def cmd_documents(message: Message):
    options = get_doc_options()
    if not options:
        await message.answer("Не удалось получить список доступных типов документов.")
        return

    doc_types = "\n".join(f"- {opt}" for opt in options)
    await message.answer(f"Доступные типы документов:\n{doc_types}")


@router.message(F.document)
async def handle_document_upload(message: Message, state: FSMContext):
    user_id = message.from_user.id
    document = message.document

    if document.file_name.endswith(".docx"):
        await message.answer("Загружаем и проверяем .docx документ...")
        result = await upload_file_and_check_single(document, user_id)
        await message.answer(result)

    elif document.file_name.endswith(".tex"):
        await state.update_data(tex_file=document)
        await message.answer("Файл .tex загружен. Теперь загрузите файл .sty")

    elif document.file_name.endswith(".sty"):
        data = await state.get_data()
        tex_file = data.get("tex_file")
        if not tex_file:
            await message.answer("Сначала загрузите .tex файл")
            return

        await message.answer("Загружаем и проверяем LaTeX-документ...")
        result = await upload_latex_and_check(tex_file, document, user_id)
        await message.answer(result)
        await state.clear()

    else:
        await message.answer("Неподдерживаемый формат файла. Поддерживаются: .docx, .tex, .sty")