import json
from pathlib import Path

BASE_PATH = Path(__file__).resolve().parent.parent / "locales"


class LanguageRepository:
    @staticmethod
    def language_dir(code: str) -> Path:
        return BASE_PATH / code

    @staticmethod
    def exists(code: str) -> bool:
        path = LanguageRepository.language_dir(code)
        return (
            (path / "meta.json").exists()
            and (path / "common.json").exists()
            and (path / "buttons.json").exists()
        )

    @staticmethod
    def read_json(code: str, filename: str) -> dict:
        path = LanguageRepository.language_dir(code) / filename
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def write_json(code: str, filename: str, data: dict) -> None:
        path = LanguageRepository.language_dir(code) / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    @staticmethod
    def meta(code: str) -> dict:
        return LanguageRepository.read_json(code, "meta.json")

    @staticmethod
    def common(code: str) -> dict:
        return LanguageRepository.read_json(code, "common.json")

    @staticmethod
    def buttons(code: str) -> dict:
        return LanguageRepository.read_json(code, "buttons.json")

    @staticmethod
    def save_pack(code: str, *, meta: dict, common: dict, buttons: dict) -> None:
        LanguageRepository.write_json(code, "meta.json", meta)
        LanguageRepository.write_json(code, "common.json", common)
        LanguageRepository.write_json(code, "buttons.json", buttons)


    @staticmethod
    def installed_codes() -> list[str]:
        return sorted(
            path.name
            for path in BASE_PATH.iterdir()
            if path.is_dir()
            and (path / "meta.json").exists()
            and (path / "common.json").exists()
            and (path / "buttons.json").exists()
        )

    @staticmethod
    def delete_pack(code: str) -> None:
        import shutil

        protected = {"ru", "en"}

        if code in protected:
            return

        path = LanguageRepository.language_dir(code)

        if path.exists() and path.is_dir():
            shutil.rmtree(path)
