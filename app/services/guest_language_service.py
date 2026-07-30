import html
import json
from pathlib import Path

import langcodes

from app.services.language_pack_service import LanguagePackService


AUTH_PHRASES = [
    "Вход", "Вход в кабинет", "Выберите удобный способ входа.",
    "Войти по email и паролю", "Пароль", "Войти в кабинет", "Не помню пароль",
    "Войти через Telegram", "Получить код в Telegram", "Выбрать язык",
    "Язык интерфейса", "Выберите язык авторизации", "Найти язык", "Найти",
    "Введите название языка", "Популярные языки", "Вернуться ко входу",
    "Установка языка", "Подготавливаем перевод интерфейса", "Язык установлен",
    "Подтвердите вход", "Код подтверждения", "Подтвердить и войти",
    "Защитите аккаунт", "Двухфакторная аутентификация обязательна. Выберите приложение, которым будете подтверждать каждый вход.",
    "Шаг 1 из 3", "Выбор приложения", "Настроить приложение",
    "До завершения всех трёх шагов доступ к кабинету закрыт.",
    "Шаг 2 из 3", "Добавление аккаунта", "Ключ для ручного ввода",
    "Код из приложения", "Проверить код", "Подключение 2FA",
    "Сохраните резервные коды", "Шаг 3 из 3", "Защита от потери телефона",
    "Я сохранил резервные коды в безопасном месте", "Завершить настройку и войти",
    "Резервные коды", "Одноразовый доступ", "Отправить код", "Регистрация",
    "Повторите пароль", "Создать аккаунт", "Введите код", "Войти",
    "Мы отправили шестизначный код в Telegram.",
    "Код из приложения обновляется каждые 30 секунд. Один и тот же код нельзя использовать повторно.",
    "Потеряли телефон? Используйте резервный код или обратитесь к платформенному администратору либо оператору.",
    "Каждый резервный код позволяет войти один раз, если телефон недоступен. Сохраните их в менеджере паролей или распечатайте.",
    "После завершения этот список больше не будет показан. Не храните его вместе с телефоном.",
    "Не удаляйте аккаунт из приложения после проверки — код потребуется при каждом входе.",
    "Настройка 2FA", "Подтверждение входа", "Подтверждение", "Ошибка",
    "На главную", "Не удалось продолжить", "Вернуться ко входу",
    "Подключите", "Установите и откройте", "на телефоне.",
    "Наведите камеру на QR-код ниже. Если сканирование недоступно, выберите ручной ввод и укажите ключ.",
    "После добавления аккаунта приложение покажет шестизначный код. Введите его в форму.",
    "Откройте Яндекс Ключ. Нажмите знак «+», выберите добавление аккаунта по QR-коду и разрешите доступ к камере.",
    "Откройте Microsoft Authenticator. Нажмите «+», выберите «Другая учётная запись», затем выберите сканирование QR-кода.",
    "Откройте Google Authenticator. Нажмите «+» и выберите «Сканировать QR-код».",
    "Введите шестизначный код из", "или один резервный код.",
    "Укажите рабочий email сотрудника. Мы отправим код для входа, если адрес найден и почта настроена.",
    "Код действует 15 минут.", "Установить новый пароль", "Новый пароль",
    "Повторите новый пароль", "Сохранить пароль и продолжить",
    "Сеанс настройки истёк. Выполните вход ещё раз.", "Аккаунт недоступен.",
    "Код не подошёл. Проверьте время на телефоне и повторите настройку.",
    "Неверный, просроченный или уже использованный код.",
]

EN_OVERRIDES = {
    "Вход": "Sign in",
    "Вход в кабинет": "Sign in",
    "Выберите удобный способ входа.": "Choose how you would like to sign in.",
    "Войти по email и паролю": "Sign in with email and password",
    "Войти в кабинет": "Sign in",
    "Не помню пароль": "Forgot password",
    "Войти через Telegram": "Sign in with Telegram",
    "Получить код в Telegram": "Get a code in Telegram",
    "Выбрать язык": "Choose language",
    "Язык интерфейса": "Interface language",
    "Выберите язык авторизации": "Choose the language for sign-in",
    "Подтвердите вход": "Confirm sign-in",
    "Подтвердить и войти": "Confirm and sign in",
}


class GuestLanguageService:
    @staticmethod
    def path(code: str) -> Path:
        safe = code.replace("/", "-")
        return Path(__file__).resolve().parent.parent / "locales" / safe / "web_auth.json"

    @staticmethod
    def installed(code: str) -> bool:
        return code == "ru" or GuestLanguageService.path(code).exists()

    @staticmethod
    def load(code: str) -> dict[str, str]:
        if code == "ru":
            return {value: value for value in AUTH_PHRASES}
        path = GuestLanguageService.path(code)
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def install(query: str) -> dict:
        meta = LanguagePackService.resolve_language(query)
        code = meta["code"]
        if code == "ru":
            return meta
        path = GuestLanguageService.path(code)
        existing = {}
        if path.exists():
            existing = json.loads(path.read_text(encoding="utf-8"))
        missing = [phrase for phrase in AUTH_PHRASES if phrase not in existing]
        if missing:
            translated = LanguagePackService._translate_values(missing, code)
            existing.update(dict(zip(missing, translated)))
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(existing, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        if code.split("-")[0].casefold() == "en":
            existing.update(EN_OVERRIDES)
            path.write_text(
                json.dumps(existing, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        return meta

    @staticmethod
    def translate_html(document: str, code: str) -> str:
        if code == "ru":
            return document
        translations = GuestLanguageService.load(code)
        for source in sorted(translations, key=len, reverse=True):
            document = document.replace(source, html.escape(translations[source], quote=True))
        return document

    @staticmethod
    def flag(code: str) -> str:
        try:
            territory = langcodes.Language.get(code).maximize().territory or "UN"
        except Exception:
            territory = "UN"
        if len(territory) != 2 or not territory.isalpha():
            territory = "UN"
        return "".join(chr(127397 + ord(character)) for character in territory.upper())
