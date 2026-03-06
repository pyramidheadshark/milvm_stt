import os

from dotenv import load_dotenv

from paths import DOTENV_PATH

load_dotenv(DOTENV_PATH)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
MODEL = os.getenv("MODEL", "google/gemini-2.5-flash-lite-preview-09-2025")
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))

TRANSCRIBE_PROMPT = """Ты — ассистент для транскрибации аудио.

КРИТИЧЕСКИ ВАЖНО: твой ответ должен содержать ТОЛЬКО две строки в точном формате ниже. Никаких вступлений, пояснений, markdown-разметки, звёздочек, заключений или любого другого текста — только эти две строки:

TITLE: <заголовок на русском>
TEXT: <транскрибация>

Правила транскрибации:
- Транскрибируй ДОСЛОВНО на языке говорящего
- Убери слова-паразиты (э, ну, короче, вот, значит, uh, um, like и т.п.) и точные повторения
- Не добавляй интерпретации и комментарии

Правила заголовка:
- ВСЕГДА на русском языке, вне зависимости от языка аудио
- 2-4 ключевых смысловых концепции из содержания, 4-8 слов
- Конкретный и содержательный, не общий
- Хорошо: "Идея приложения для трекинга привычек", "Список задач на спринт"
- Плохо: "Голосовая заметка", "Запись", "Мысли", "Untitled"

Ещё раз — твой ответ должен быть СТРОГО в таком формате и ничего больше:
TITLE: <заголовок на русском>
TEXT: <транскрибация>"""

_REQUIRED = {"OPENROUTER_API_KEY": OPENROUTER_API_KEY}


def validate_config() -> None:
    missing = [k for k, v in _REQUIRED.items() if not v]
    if missing:
        raise RuntimeError(
            f"Missing required env vars: {', '.join(missing)}. Check your .env file."
        )


def reload_config() -> None:
    global OPENROUTER_API_KEY, MODEL, _REQUIRED
    load_dotenv(DOTENV_PATH, override=True)
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
    MODEL = os.getenv("MODEL", "google/gemini-2.5-flash-lite-preview-09-2025")
    _REQUIRED = {"OPENROUTER_API_KEY": OPENROUTER_API_KEY}


def write_settings(api_key: str, model: str) -> None:
    updates: dict[str, str] = {}
    if api_key:
        updates["OPENROUTER_API_KEY"] = api_key
    if model:
        updates["MODEL"] = model
    if not updates:
        return

    lines: list[str] = []
    if os.path.exists(DOTENV_PATH):
        with open(DOTENV_PATH, encoding="utf-8") as f:
            lines = f.readlines()

    updated_keys: set[str] = set()
    new_lines: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key = stripped.split("=", 1)[0].strip()
            if key in updates:
                new_lines.append(f"{key}={updates[key]}\n")
                updated_keys.add(key)
                continue
        new_lines.append(line)

    for key, val in updates.items():
        if key not in updated_keys:
            new_lines.append(f"{key}={val}\n")

    with open(DOTENV_PATH, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

    reload_config()


SUPPORTED_FORMATS = {
    "audio/ogg": "ogg",
    "audio/mpeg": "mp3",
    "audio/mp3": "mp3",
    "audio/wav": "wav",
    "audio/x-wav": "wav",
    "audio/webm": "webm",
    "audio/mp4": "mp4",
    "audio/m4a": "m4a",
    "audio/aac": "aac",
    "audio/flac": "flac",
}
