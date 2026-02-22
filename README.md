# Voice Transcriber

Локальное приложение для мгновенной транскрибации голосовых заметок через [OpenRouter](https://openrouter.ai/) + Google Gemini.  
Записывает аудио прямо в браузере, транскрибирует за несколько секунд, сохраняет историю локально.

Работает как трей-приложение — клик по иконке открывает окно, закрытие скрывает в трей.

---

## Требования

- Python 3.11+
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- [Ключ OpenRouter API](https://openrouter.ai/keys)

---

## Быстрый старт

```bash
git clone https://github.com/you/voice-transcriber.git
cd voice-transcriber

uv sync
cp .env.example .env
# Открыть .env и указать OPENROUTER_API_KEY

make tray        # трей-приложение (Linux / macOS)
make run         # только веб-режим (браузер)
```

**Windows** — запустить `uv run python tray.py` из терминала,  
либо добавить в автозапуск через ярлык на `tray.py`.

---

## Настройка — `.env`

| Переменная | По умолчанию | Описание |
|---|---|---|
| `OPENROUTER_API_KEY` | — | Обязательно. Получить на openrouter.ai/keys |
| `MODEL` | `google/gemini-2.5-flash-lite-preview-09-2025` | Любая модель OpenRouter с поддержкой аудио |
| `PORT` | `8000` | Изменить если порт занят |
| `HOST` | `0.0.0.0` | Указать `127.0.0.1` чтобы закрыть доступ из локальной сети |

---

## Make-команды

```bash
make setup       # Первоначальная настройка (создаёт .env, ставит зависимости)
make install     # Установить / синхронизировать зависимости
make tray        # Запустить трей-приложение (foreground)
make tray-bg     # Запустить трей-приложение в фоне (Linux / macOS)
make run         # Веб-режим, открывает браузер
make dev         # Веб-режим с hot-reload
make build       # Собрать .exe через PyInstaller
make clean       # Удалить кэш Python
```

---

## Сборка исполняемого файла

```bash
uv sync --group dev
make build
# → dist/VoiceTranscriber.exe
```

Положить `.env` рядом с `.exe` перед запуском. Папка `transcripts/` создаётся автоматически при первом запуске.

---

## Архитектура

```
voice-transcriber/
├── tray.py                  # Точка входа — трей-иконка + окно pywebview
├── main.py                  # FastAPI — роуты и lifecycle
├── config.py                # Настройки и промпт из .env
├── paths.py                 # Разрешение путей (dev vs PyInstaller бандл)
├── build.py                 # Скрипт сборки PyInstaller
├── services/
│   ├── transcriber.py       # Запрос в OpenRouter API
│   └── storage.py           # SQLite + .txt файлы
├── templates/
│   └── index.html           # Весь UI — vanilla JS, без сборки
├── assets/
│   ├── icon.png             # Иконка приложения
│   └── icon.ico             # Иконка для Windows
├── transcripts/             # Данные — в .gitignore
│   ├── history.db           # SQLite база
│   └── *.txt                # Текстовые файлы транскрибаций
├── pyproject.toml           # Зависимости (uv)
└── Makefile                 # Команды для Linux / macOS / Windows
```

**Стек:** FastAPI · pywebview · pystray · aiosqlite · httpx · Jinja2 · uv

**Как работает транскрибация:**

1. Браузер записывает аудио через `MediaRecorder API` (WebM/Opus) или принимает загруженный файл
2. FastAPI получает файл через `multipart/form-data`, проверяет размер (макс. 25 МБ)
3. Аудио кодируется в `base64` и отправляется в OpenRouter с типом `input_audio`
4. Gemini возвращает русский заголовок + дословную транскрибацию
5. Сохраняется в SQLite и `.txt`, отображается в UI с поиском и пагинацией

---

## Стоимость

Модель по умолчанию: `google/gemini-2.5-flash-lite-preview-09-2025`

| | Цена |
|---|---|
| Аудио токены | $0.30 / 1M |
| Выходные токены | $0.40 / 1M |

Голосовая заметка 1–2 минуты обходится примерно в **$0.001–0.003**.

Работает любая модель OpenRouter с поддержкой аудио — указать в `MODEL` в `.env`.  
Список моделей: [openrouter.ai/models?input_modalities=audio](https://openrouter.ai/models?fmt=cards&input_modalities=audio)
