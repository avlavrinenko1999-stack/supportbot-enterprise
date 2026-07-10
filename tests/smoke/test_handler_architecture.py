from pathlib import Path


HANDLERS_ROOT = Path("app/handlers")

ALLOWED_TEXT_FILTERS = {
    "app/handlers/fallback.py": {
        "@router.message(F.text)",
    },
    "app/handlers/admin/company/card.py": {
        '@router.message(F.text.regexp(r"^[✅⛔] \\d+\\. "))',
    },
    "app/handlers/admin/coordinators.py": {
        '@router.message(F.text.regexp(r"^[✅⛔] \\d+\\. "))',
    },
    "app/handlers/admin/company_categories.py": {
        '@router.message(F.text.regexp(r"^[📂📦] .+"))',
    },
}

FORBIDDEN_HANDLER_TOKENS = (
    "message.answer(",
    "callback.message.answer(",
    "bot.send_message(",
    "F.text ==",
    "F.text.in_(",
    "F.text.contains(",
)


def iter_handler_files():
    yield from HANDLERS_ROOT.rglob("*.py")


def test_handlers_do_not_send_messages_directly() -> None:
    errors = []

    for path in iter_handler_files():
        relative = path.as_posix()
        text = path.read_text(encoding="utf-8")

        for line_number, line in enumerate(text.splitlines(), start=1):
            if any(token in line for token in FORBIDDEN_HANDLER_TOKENS):
                errors.append(
                    f"{relative}:{line_number}: {line.strip()}"
                )

    assert not errors, (
        "Найдены запрещённые прямые вызовы или текстовые фильтры:\n"
        + "\n".join(errors)
    )


def test_only_expected_dynamic_text_filters_remain() -> None:
    errors = []

    for path in iter_handler_files():
        relative = path.as_posix()
        allowed_lines = ALLOWED_TEXT_FILTERS.get(relative, set())

        for line_number, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(),
            start=1,
        ):
            stripped = line.strip()

            if "@router.message(F.text" not in stripped:
                continue

            if stripped not in allowed_lines:
                errors.append(
                    f"{relative}:{line_number}: {stripped}"
                )

    assert not errors, (
        "Обнаружены незарегистрированные F.text-фильтры:\n"
        + "\n".join(errors)
    )


def test_callback_editing_is_centralized() -> None:
    allowed_file = "app/handlers/admin/common.py"
    errors = []

    for path in iter_handler_files():
        relative = path.as_posix()

        if relative == allowed_file:
            continue

        for line_number, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(),
            start=1,
        ):
            if ".edit_text(" in line:
                errors.append(
                    f"{relative}:{line_number}: {line.strip()}"
                )

    assert not errors, (
        "Прямое редактирование callback-сообщений разрешено только "
        f"в {allowed_file}:\n" + "\n".join(errors)
    )
