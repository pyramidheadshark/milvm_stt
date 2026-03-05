# Voice Transcriber

[![CI](https://github.com/pyramidheadshark/milvm-stt/actions/workflows/ci.yml/badge.svg)](https://github.com/pyramidheadshark/milvm-stt/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/pyramidheadshark/milvm-stt/graph/badge.svg)](https://codecov.io/gh/pyramidheadshark/milvm-stt)
[![Release](https://img.shields.io/github/v/release/pyramidheadshark/milvm-stt)](https://github.com/pyramidheadshark/milvm-stt/releases/latest)

Трей-приложение для Windows: записал голосовую заметку — получил текст с заголовком через несколько секунд.

Работает на [OpenRouter](https://openrouter.ai/) + Google Gemini. Данные хранятся локально, никуда не отправляются кроме аудио на транскрибацию.

---

## Возможности

- **Запись прямо в приложении** — через микрофон браузера, без сторонних программ
- **Загрузка файла** — поддерживаются OGG, MP3, WAV, WebM, M4A, AAC, FLAC (до 25 МБ)
- **Автоматический заголовок** — модель генерирует краткий заголовок на русском
- **История и поиск** — все транскрибации сохраняются локально в SQLite, есть полнотекстовый поиск и пагинация
- **Настройки в приложении** — API ключ и модель меняются без редактирования файлов
- **Восстановление аудио** — если транскрибация упала, аудиофайл сохраняется и доступен для повторной попытки
- **Трей** — приложение живёт в системном трее, окно открывается по клику

---

## Установка

### Готовый .exe (Windows)

1. Скачать `VoiceTranscriber.exe` из [Releases](https://github.com/pyramidheadshark/milvm-stt/releases/latest)
2. Запустить — при первом запуске автоматически откроется панель настроек
3. Ввести [API ключ OpenRouter](https://openrouter.ai/keys) и нажать Save

Больше ничего не нужно. Данные и настройки хранятся в папке рядом с `.exe`.

### Из исходников

Требования: Python 3.11+, [uv](https://docs.astral.sh/uv/getting-started/installation/)

```bash
git clone https://github.com/pyramidheadshark/milvm-stt.git
cd milvm-stt
uv sync
uv run python tray.py
```

---

## Настройки

Открыть панель настроек — кнопка **⚙** в заголовке окна.

| Параметр | Описание |
|---|---|
| API Key | Ключ OpenRouter. Получить на [openrouter.ai/keys](https://openrouter.ai/keys) |
| Model | ID модели OpenRouter с поддержкой аудио. По умолчанию — `google/gemini-2.5-flash-lite-preview-09-2025` |

Изменения применяются сразу, без перезапуска.

Альтернативно — через `.env` в папке с `.exe`:

```env
OPENROUTER_API_KEY=sk-or-v1-...
MODEL=google/gemini-2.5-flash-lite-preview-09-2025
PORT=8000
```

Список моделей с поддержкой аудио: [openrouter.ai/models?input_modalities=audio](https://openrouter.ai/models?fmt=cards&input_modalities=audio)

---

## Стоимость

Модель по умолчанию: `google/gemini-2.5-flash-lite-preview-09-2025`

| Тип токенов | Цена |
|---|---|
| Аудио | $0.30 / 1M |
| Текст (выход) | $0.40 / 1M |

Заметка 1–2 минуты ≈ **$0.001–0.003**. При активном использовании (20 заметок/день) — около **$1–2 в месяц**.

---

## Разработка

```bash
uv sync
make dev          # веб-режим с hot-reload
make tray         # трей-приложение
make build        # собрать .exe
```

Полный список команд: `make help`

### Тесты

```bash
uv run pytest --cov=. -q
```

81 тест, покрытие 95%. CI запускается на каждый push: ruff + mypy + pytest.

### Релиз

```bash
git tag v0.X.Y && git push origin v0.X.Y
```

GitHub Actions автоматически соберёт `.exe` и опубликует GitHub Release.

Правила версий: `PATCH` — фиксы и мелкие улучшения, `MINOR` — новые фичи, `MAJOR` — breaking changes.

---

## Архитектура

```
├── tray.py              # точка входа — системный трей + окно pywebview
├── main.py              # FastAPI: все эндпоинты
├── config.py            # конфигурация, write_settings, reload_config
├── paths.py             # разрешение путей (dev / PyInstaller bundle)
├── services/
│   ├── transcriber.py   # OpenRouter API, retry, парсинг ответа
│   └── storage.py       # SQLite, история, failed audio
├── templates/
│   └── index.html       # весь UI — vanilla JS, без сборки
├── assets/              # иконки
├── tests/               # 81 тест
└── .github/workflows/
    ├── ci.yml           # lint + typecheck + test
    └── release.yml      # build .exe → GitHub Release
```

**Стек:** FastAPI · pywebview · pystray · aiosqlite · httpx · Jinja2 · uv · PyInstaller

**Поток транскрибации:**

```
микрофон → MediaRecorder (WebM/Opus)
         → POST /transcribe
         → base64 + input_audio → OpenRouter API
         → парсинг TITLE / TEXT
         → SQLite + возврат в UI
```

При ошибке API аудио сохраняется как `FAILED_*.ogg` — доступно для скачивания из UI.
