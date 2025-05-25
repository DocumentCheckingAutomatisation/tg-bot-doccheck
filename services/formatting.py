from aiogram.types import Message


async def send_long_message(message: Message, text: str):
    max_length = 4096
    for i in range(0, len(text), max_length):
        await message.answer(text[i:i + max_length], parse_mode="HTML")


def format_latex_validation_result(result: dict) -> str:
    def yesno(errors: list, key: str) -> str:
        patterns = {
            "structure.chapters": ["Отсутствует обязательная глава", "Ошибка: после \\\\chapter",
                                   "Ошибка: титульный лист", "Ошибка: отсутствует \\tableofcontents"],
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
