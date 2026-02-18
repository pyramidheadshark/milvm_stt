from dotenv import load_dotenv
from paths import DOTENV_PATH
import os

load_dotenv(DOTENV_PATH)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
MODEL = os.getenv("MODEL", "google/gemini-2.5-flash-lite-preview-09-2025")
HOST  = os.getenv("HOST", "0.0.0.0")
PORT  = int(os.getenv("PORT", "8000"))

TRANSCRIBE_PROMPT = """Ты — ассистент для транскрибации аудио. Твоя задача:
1. Транскрибируй аудио ДОСЛОВНО на языке говорящего.
2. Убери слова-паразиты (э, ну, короче, вот, значит, uh, um, like, you know и т.п.) и точные повторения.
3. НЕ добавляй интерпретации, форматирование markdown или комментарии.
4. Придумай заголовок, который:
   - ВСЕГДА написан на русском языке, вне зависимости от языка аудио
   - Отражает 2-4 ключевых смысловых слова или концепции из содержания
   - Краткий (4-8 слов), конкретный и содержательный — не общий
   - Примеры ХОРОШИХ заголовков: "Идея приложения для трекинга привычек", "Список задач на спринт", "Рефлексия после встречи с командой"
   - Примеры ПЛОХИХ заголовков: "Голосовая заметка", "Запись", "Мысли", "Untitled"

Формат ответа — строго следуй этой структуре:
TITLE: <заголовок на русском>
TEXT: <транскрибация>"""

SUPPORTED_FORMATS = {
    "audio/ogg":  "ogg",
    "audio/mpeg": "mp3",
    "audio/mp3":  "mp3",
    "audio/wav":  "wav",
    "audio/x-wav":"wav",
    "audio/webm": "webm",
    "audio/mp4":  "mp4",
    "audio/m4a":  "m4a",
    "audio/aac":  "aac",
    "audio/flac": "flac",
}
