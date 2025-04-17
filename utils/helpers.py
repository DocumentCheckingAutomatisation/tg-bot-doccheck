import aiohttp
import tempfile

from aiogram.types import Document
from config import API_URL


def is_reviewer(user_id: int) -> bool:
    # заглушка, позже бд или список
    return user_id in {123456789}  # список ID нормоконтролёров


async def upload_file_and_check_single(document: Document, user_id: int) -> str:
    try:
        file_url = document.url if hasattr(document, "url") else None
        file_name = document.file_name

        if not file_url:
            return "Не удалось получить файл."

        async with aiohttp.ClientSession() as session:
            async with session.get(file_url) as response:
                if response.status != 200:
                    return "Ошибка загрузки файла."
                content = await response.read()

        with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as temp:
            temp.write(content)
            temp.seek(0)
            files = {"file": (file_name, open(temp.name, "rb"))}
            data = {"doc_type": "diploma"}  # позже спросить у пользователя

            async with aiohttp.ClientSession() as session:
                async with session.post(f"{API_URL}/api/documents/validate/single_file", data=data, files=files) as resp:
                    if resp.status != 200:
                        return f"Ошибка проверки: {resp.status}"
                    return await resp.text()

    except Exception as e:
        return f"Произошла ошибка: {e}"


async def upload_latex_and_check(tex_file: Document, sty_file: Document, user_id: int) -> str:
    try:
        async def download(document: Document):
            file_url = document.url if hasattr(document, "url") else None
            if not file_url:
                return None
            async with aiohttp.ClientSession() as session:
                async with session.get(file_url) as resp:
                    if resp.status != 200:
                        return None
                    return await resp.read()

        tex_bytes = await download(tex_file)
        sty_bytes = await download(sty_file)

        if not tex_bytes or not sty_bytes:
            return "Ошибка при загрузке одного из файлов."

        files = {
            "tex_file": (tex_file.file_name, tex_bytes),
            "sty_file": (sty_file.file_name, sty_bytes)
        }
        data = {"doc_type": "diploma"}  # выбор пользователем позже

        async with aiohttp.ClientSession() as session:
            async with session.post(f"{API_URL}/api/documents/validate/latex", data=data, files=files) as resp:
                if resp.status != 200:
                    return f"Ошибка проверки: {resp.status}"
                return await resp.text()

    except Exception as e:
        return f"Произошла ошибка: {e}"
