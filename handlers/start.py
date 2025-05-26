from datetime import datetime

from aiogram import Router, types
from aiogram.filters import Command

from config import SECRET_CODE, ADMIN_USER_ID
from db import get_user_role, set_user_role, REVIEWER_ROLE, STUDENT_ROLE, get_recent_checks

from logger import logger
from services.formatting import send_long_message

router = Router()


def get_available_commands(role: str) -> list[str]:
    commands = [
        "/types — показать типы документов",
        "/rules <тип_документа> — показать правила",
        "/check_docx <тип_документа> — проверить .docx документ",
        "/check_latex <тип_документа> — проверить .tex и .sty файлы",
        "/my_role — показать текущую роль",
        "/help — список доступных команд",
        "/info — информация о боте",
        "/feedback <сообщение> — отправить отзыв",
    ]

    if role == STUDENT_ROLE:
        commands.append("/set_reviewer <секретный_код> — получить роль нормоконтролера")

    if role == REVIEWER_ROLE:
        commands.append("/change_rule <тип> <ключ> <значение> — изменить правило")
        commands.append("/change_rule_for_all <ключ> <значение> — изменить правило для всех типов")
        commands.append("/recent_checks — список проверок за последние 14 дней")
        commands.append("/reset_role — сбросить роль до student")

    return commands


@router.message(Command("start"))
async def start(message: types.Message):
    user_id = message.from_user.id
    role = get_user_role(user_id, message.from_user.username)
    logger.info(f"👤 Пользователь {user_id} начал сессию как {role}.")

    commands = get_available_commands(role)

    await message.answer(
        f"Привет! Ваша текущая роль: {role}.\n"
        "Доступные команды:\n" +
        "\n".join(commands) +
        "\n\nLaTeX-шаблон студенческих работ ИГУ: https://github.com/Alyona1619/LaTeXTemplate \n"
        "Видео-гайд по работе с шаблоном: https://www.youtube.com/playlist?list=PLEi6YXJjTzwHIK_g0Zc2m4cs4OVbxLyXN, https://rutube.ru/channel/64712980/ \n"
        "\nПример верно оформленной ВКР (.docx): https://drive.google.com/file/d/1UVObCmf_YjNV5h06Pp7QGsTttSxrG3e5/view?usp=drive_link \n"
        "Документ с правилами оформления ИГУ: https://docs.google.com/document/d/1u4fIvEEHkwORaAj1kNBk3aBlEca7_pJ7/edit?usp=drive_link&ouid=115137208764228085296&rtpof=true&sd=true"
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


@router.message(Command("my_role"))
async def my_role(message: types.Message):
    user_id = message.from_user.id
    role = get_user_role(user_id, message.from_user.username)
    await message.answer(f"Ваша текущая роль: {role}")


@router.message(Command("help"))
async def help_command(message: types.Message):
    user_id = message.from_user.id
    role = get_user_role(user_id, message.from_user.username)
    commands = get_available_commands(role)
    await message.answer("Справка по доступным командам:\n" + "\n".join(commands))


@router.message(Command("info"))
async def info(message: types.Message):
    await message.answer(
        "📝 Этот бот помогает проверять оформление студенческих работ (ВКР, курсовых, отчетов по практике) "
        "в соответствии с требованиями ГОСТ 7.32-2017 и требованиями Иркутского государственного университета.\n\n"
        "📌 Возможности:\n"
        "- Просмотр доступных для проверки типов работ и правил\n"
        "- Проверка документов формата .docx\n"
        "- Проверка документов формата LaTeX (.tex и .sty)\n"
        "- Изменение правил (только для нормоконтролеров)\n"
        "- Просмотр списка студентов, проверивших свои работы (только для нормоконтролеров)\n"
        "\n"
        "📌 LaTeX работы должны быть оформлены по шаблону для студенческих работ ИГУ: https://github.com/Alyona1619/LaTeXTemplate \n"
        "Видео-гайд по работе с шаблоном: https://www.youtube.com/playlist?list=PLEi6YXJjTzwHIK_g0Zc2m4cs4OVbxLyXN, https://rutube.ru/channel/64712980/ \n"
        "Пример верно оформленной ВКР (.docx): https://drive.google.com/file/d/1UVObCmf_YjNV5h06Pp7QGsTttSxrG3e5/view?usp=drive_link \n"
        "Документ с правилами оформления ИГУ: https://docs.google.com/document/d/1u4fIvEEHkwORaAj1kNBk3aBlEca7_pJ7/edit?usp=drive_link&ouid=115137208764228085296&rtpof=true&sd=true"
        "\n"
        "📌 В LaTeX работах проверяется:\n"
        "- структура работы (главы и разделы)\n"
        "- наличие ключевых слов во введении, выделенных жирным\n"
        "- отсутствие жирности, курсива, подчеркиваний в тексте работы\n"
        "- оформление списков (знаки препинания в вводном предложении и элементах, строчные/заглавные первые буквы элементов)\n"
        "- наличие пары объект-ссылка у рисунков, таблиц, приложения, списка использованных источников\n"
        "- расстояние от ссылки до рисунка/таблицы\n"
        "- использование правильных кавычек\n"
        "- правильность .sty файла (размер шрифта, межстрочный интервал, отступы, формат подписей и другое)\n"
        "\n"
        "📌 В docx работах проверяется:\n"
        "- структура работы (главы и разделы 'Выводы по главе')\n"
        "- размер шрифта всего текста\n"
        "- ключевые слова во введении выделенные жирным\n"
        "- рисунки, таблицы, приложения, список использ. источн. (наличие пары объект-ссылка)\n"
        "\n"
        "Используйте /help, чтобы увидеть список всех доступных команд."
    )


@router.message(Command("reset_role"))
async def reset_role(message: types.Message):
    user_id = message.from_user.id
    set_user_role(user_id, STUDENT_ROLE)
    logger.info(f"🔄 Пользователю {user_id} сброшена роль до student.")
    await message.answer("Ваша роль сброшена до 'student'. Вы больше не нормоконтролер.")


@router.message(Command("feedback"))
async def feedback(message: types.Message):
    user_id = message.from_user.id
    text_parts = message.text.split(maxsplit=1)

    if len(text_parts) < 2:
        await message.answer("Пожалуйста, введите сообщение: /feedback <текст>")
        return

    feedback_text = text_parts[1]

    # Логирование
    logger.feedback(f"✉️ Отзыв от {user_id}: {feedback_text}")

    # Отправка админу
    try:
        await message.bot.send_message(
            ADMIN_USER_ID,
            f"📩 Отзыв от пользователя {user_id} (@{message.from_user.username}):\n{feedback_text}"
        )
    except Exception as e:
        logger.warning(f"⚠️ Не удалось отправить сообщение админу: {e}")

    await message.answer("Спасибо за ваш отзыв! Он был отправлен администратору.")


@router.message(Command("recent_checks"))
async def recent_checks(message: types.Message):
    user_id = message.from_user.id
    role = get_user_role(user_id)

    if role != REVIEWER_ROLE:
        logger.warning(f"Пользователь {user_id} попытался использовать команду recent_checks.")
        await message.answer("⛔️ Эта команда доступна только нормоконтролёрам.")
        return

    checks = get_recent_checks(14)
    if not checks:
        await message.answer("За последние 14 дней не было проверок.")
        return

    text = "📄 <b>Последние проверки за 14 дней:</b>\n\n"
    current_type = None

    for username, doc_type, check_type, result, check_time in checks:
        if doc_type != current_type:
            current_type = doc_type
            text += f"\n🔷 <u><b>Тип документа: {doc_type}</b></u>\n"

        readable_time = datetime.fromisoformat(str(check_time)).strftime("%d.%m.%Y %H:%M")
        if result == '0':
            result_str = "Найдены ошибки ❌"
        elif result == '1':
            result_str = "Ошибки не найдены ✅"
        else:
            result_str = "Неизвестный результат"

        text += (
            f"👤 @{username or 'неизвестно'}\n"
            f"🕒 Время: {readable_time}\n"
            f"🔍 Проверка: {check_type}\n"
            f"☑️ Результат: {result_str}\n\n"
        )

    await send_long_message(message, text)


def register(dp):
    dp.include_router(router)
