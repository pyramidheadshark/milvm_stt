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
git clone https://github.com/pyramidheadshark/milvm-stt.git
cd milvm-stt

uv sync
cp .env.example .env
# Открыть .env и указать OPENROUTER_API_KEY

make tray        # трей-приложение (Linux / macOS)
make run         # только веб-режим (браузер)
```

**Windows** — скачать `.exe` из [Releases](https://github.com/pyramidheadshark/milvm-stt/releases/latest),
положить `.env` рядом с `.exe` и запустить.

Или запустить из исходников: `uv run python tray.py`

---

## Настройка API ключа

Два способа:

1. **В приложении**: кнопка ⚙ в заголовке → ввести ключ → Save settings (применяется сразу, без перезапуска)
2. **Через `.env`**: создать `.env` рядом с `.exe`, указать `OPENROUTER_API_KEY=sk-or-v1-...`

---

## Переменные `.env`

| Переменная | По умолчанию | Описание |
|---|---|---|
| `OPENROUTER_API_KEY` | — | Обязательно. Получить на openrouter.ai/keys |
| `MODEL` | `google/gemini-2.5-flash-lite-preview-09-2025` | Любая модель OpenRouter с поддержкой аудио |
| `PORT` | `8000` | Изменить если порт занят |
| `HOST` | `127.0.0.1` | Не менять без необходимости |

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
uv sync
make build
# → dist/VoiceTranscriber.exe
```

Готовый `.exe` автоматически публикуется в [GitHub Releases](https://github.com/pyramidheadshark/milvm-stt/releases) при создании тега `v*.*.*`.

---

## Архитектура

```
milvm-stt/
├── tray.py                  # Точка входа — трей-иконка + окно pywebview
├── main.py                  # FastAPI — роуты и lifecycle
├── config.py                # Настройки, write_settings, reload_config
├── paths.py                 # Разрешение путей (dev vs PyInstaller бандл)
├── build.py                 # Скрипт сборки PyInstaller
├── services/
│   ├── transcriber.py       # Запрос в OpenRouter API + парсинг ответа
│   └── storage.py           # SQLite + файлы транскрибаций + failed audio
├── templates/
│   └── index.html           # Весь UI — vanilla JS + HTMX-стиль, без сборки
├── assets/
│   ├── icon.png             # Иконка приложения
│   └── icon.ico             # Иконка для Windows
├── tests/                   # 57 тестов, coverage 78%
├── .github/workflows/
│   ├── ci.yml               # ruff + mypy + pytest на каждый push
│   └── release.yml          # Сборка .exe и публикация релиза на тег v*.*.*
├── pyproject.toml           # Зависимости (uv)
└── Makefile
```

**Стек:** FastAPI · pywebview · pystray · aiosqlite · httpx · Jinja2 · uv

**Как работает транскрибация:**

1. Браузер записывает аудио через `MediaRecorder API` (WebM/Opus) или принимает загруженный файл
2. FastAPI получает файл через `multipart/form-data`, проверяет размер (макс. 25 МБ)
3. Аудио кодируется в `base64` и отправляется в OpenRouter с типом `input_audio`
4. Gemini возвращает русский заголовок + дословную транскрибацию
5. Сохраняется в SQLite, отображается в UI с поиском и пагинацией
6. При ошибке API: аудио сохраняется как `FAILED_*.ogg` — можно скачать из UI

---

## Стоимость

Модель по умолчанию: `google/gemini-2.5-flash-lite-preview-09-2025`

| | Цена |
|---|---|
| Аудио токены | $0.30 / 1M |
| Выходные токены | $0.40 / 1M |

Голосовая заметка 1–2 минуты обходится примерно в **$0.001–0.003**.

Работает любая модель OpenRouter с поддержкой аудио — указать в `MODEL` в `.env` или через настройки в приложении.
Список моделей: [openrouter.ai/models?input_modalities=audio](https://openrouter.ai/models?fmt=cards&input_modalities=audio)
