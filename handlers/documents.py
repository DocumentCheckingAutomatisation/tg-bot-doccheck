import os

from aiogram import Router, types, F
from aiogram.filters import Command

from logger import logger
from services.api import validate_docx_document, validate_latex_document

router = Router()

user_documents = {}  # Временное хранилище для пользователей, загружающих LaTeX-файлы


@router.message(Command("check_docx"))
async def handle_docx_check(message: types.Message):
    user_id = message.from_user.id
    logger.debug(f"📄 Пользователь {user_id} начал проверку .docx документа")

    if not message.reply_to_message or not message.reply_to_message.document:
        await message.answer("Пожалуйста, прикрепите .docx файл в ответ на эту команду.")
        return

    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Использование: /check_docx <тип_документа> (в ответ на файл)")
        return

    doc_type = parts[1]
    file = message.reply_to_message.document

    doc_path = f"/tmp/{file.file_id}.docx"
    await file.download(destination=doc_path)
    logger.debug(f"📥 Файл {file.file_name} сохранён как {doc_path}")

    result = validate_docx_document(doc_path, doc_type)
    os.remove(doc_path)

    if result:
        await message.answer(result.get("message", "Проверка завершена."))
        if "errors" in result:
            await message.answer("Ошибки:\n" + "\n".join(result["errors"]))
    else:
        await message.answer("Ошибка при проверке документа.")


@router.message(Command("check_latex"))
async def handle_latex_check(message: types.Message):
    user_id = message.from_user.id
    logger.debug(f"📄 Пользователь {user_id} начал проверку LaTeX документа")

    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Использование: /check_latex <тип_документа>")
        return

    doc_type = parts[1]
    user_documents[user_id] = {"doc_type": doc_type}
    await message.answer("Пришлите .tex файл.")


@router.message(F.document)
async def handle_latex_files(message: types.Message):
    user_id = message.from_user.id

    if user_id not in user_documents:
        return  # Игнорируем документы, если пользователь не начал /check_latex

    file = message.document
    filename = file.file_name

    if filename.endswith(".tex"):
        path = f"/tmp/{file.file_id}.tex"
        await file.download(destination=path)
        user_documents[user_id]["tex"] = path
        logger.debug(f"📥 Получен .tex файл от {user_id}")
        await message.answer("Теперь отправьте .sty файл.")
    elif filename.endswith(".sty"):
        path = f"/tmp/{file.file_id}.sty"
        await file.download(destination=path)
        user_documents[user_id]["sty"] = path
        logger.debug(f"📥 Получен .sty файл от {user_id}")

        doc_type = user_documents[user_id].get("doc_type")
        tex_path = user_documents[user_id].get("tex")
        sty_path = user_documents[user_id].get("sty")

        if not tex_path or not sty_path or not doc_type:
            await message.answer("Ошибка: не хватает одного из файлов.")
            return

        result = validate_latex_document(tex_path, sty_path, doc_type)

        os.remove(tex_path)
        os.remove(sty_path)
        user_documents.pop(user_id, None)

        if result:
            await message.answer(result.get("message", "Проверка завершена."))
            if "errors" in result:
                await message.answer("Ошибки:\n" + "\n".join(result["errors"]))
        else:
            await message.answer("Ошибка при проверке документа.")


def register(dp):
    dp.include_router(router)
