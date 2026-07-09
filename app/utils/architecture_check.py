from pathlib import Path

FORBIDDEN = [
    "message.answer(",
    "callback.message.answer(",
    ".send_message(",
]

ALLOW_FILES = {
    "app/services/message_service.py",
    "app/utils/architecture_check.py",
}

errors = []

for path in Path("app").rglob("*.py"):
    rel = str(path)

    if rel in ALLOW_FILES:
        continue

    text = path.read_text(encoding="utf-8")

    for line_no, line in enumerate(text.splitlines(), start=1):
        if any(token in line for token in FORBIDDEN):
            errors.append(f"{rel}:{line_no}: {line.strip()}")

if errors:
    print("Forbidden direct message sending found:")
    print("\n".join(errors))
    raise SystemExit(1)

print("Architecture check passed")
