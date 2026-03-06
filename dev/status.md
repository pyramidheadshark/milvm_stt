# Project Status

> **IMPORTANT**: This file is loaded at the start of every Claude Code session.
> Keep it accurate. Update it before ending any session.
> This is the single source of truth for project state.

---

## Business Goal

Desktop tray-приложение для транскрибации голосовых заметок через OpenRouter (Gemini Flash), упакованное в .exe для личного использования.

---

## Current Phase

- [x] Phase 0: Intake & Requirements
- [ ] Phase 1: Design Document
- [x] Phase 2: Environment Setup
- [x] Phase 3: Development Loop (v0.3.0, повреждён — восстановлен)
- [x] Phase 4: UI/UX улучшения — ЗАВЕРШЁН
- [ ] Phase 5: Deploy (push to remote, tag release)

**Active phase**: Phase 5 — публикация релиза

---

## Backlog

Tasks in priority order. Check off when done.

- [ ] Push to remote + создать тег v0.4.0 → GitHub Actions соберёт .exe и опубликует релиз

**Completed (most recent first):**
- [x] Phase 4: settings UI, failed audio recovery, compact UI, release pipeline — 3ce90ff — 2026-03-06
- [x] Phase 3: validate_config, PORT fix in tray, mypy clean, 45/45 тестов — cda1bb9 — 2026-03-06
- [x] Phase 1: CI исправлен, тесты 42/42, coverage 87.8%, ruff+mypy чистые — ec002aa — 2026-03-06
- [x] Phase 0: cleanup — удалены битые артефакты, зафиксированы .github/ и dev/ — e67691b — 2026-03-06
- [x] feat: v0.3.0 — tray app, pywebview, retry logic, save failed audio — 858d1a7

---

## Phase 4 Deliverables

All 7 issues addressed in commit 3ce90ff:

1. **Failed audio recovery** — FAILED_*.ogg сохраняется при 502; эндпоинты /failed-audio + /failed-audio/{filename}; frontend показывает ссылку "Download audio"
2. **Artifact regex** — расширен: могу помочь, надеюсь, glad/hope this helps, best regards и др.
3. **Tray sluggishness** — убран лишний поток в hide_window; `_window.hide()` вызывается напрямую
4. **GitHub Release pipeline** — `.github/workflows/release.yml`; триггер `v*.*.*` → build .exe → GitHub Release
5. **In-app settings** — панель с API key + model; POST /settings с hot-reload через reload_config()
6. **Compact UI** — уменьшены отступы, кнопка записи 66→58px, visualizer 88→78px
7. **Styled scrollbar** — 4px thin scrollbar вместо скрытого

Tests: **57/57**, coverage **78%**

---

## Architecture Decisions

| Decision | Choice | Date |
|---|---|---|
| Web framework | FastAPI + uvicorn | initial |
| UI | PyWebView (embedded browser window) + Jinja2 templates | initial |
| Transcription | OpenRouter API (Gemini Flash) | initial |
| Storage | SQLite via aiosqlite | initial |
| Packaging | PyInstaller → .exe | initial |
| Tray | pystray + pillow | initial |
| Config hot-reload | write_settings() → .env → reload_config() с global vars | 2026-03-06 |
| Patch target in tests | `main.X` not `module.X` when main uses `from module import X` | 2026-03-06 |

---

## Known Gotchas

- `patch("module.write_settings")` не работает если `main.py` делает `from module import write_settings` — патчить `"main.write_settings"`
- `transcriber.py` обращается к `config.OPENROUTER_API_KEY` через модуль (не import) для hot-reload поддержки
- `services/__init__.py` нужен чтобы mypy не видел services/storage.py дважды

---

## Files to Know

| File | Purpose |
|------|---------|
| `main.py` | FastAPI app: все эндпоинты |
| `config.py` | Конфигурация + write_settings + reload_config |
| `paths.py` | Резолвинг путей (PyInstaller MEIPASS) |
| `services/transcriber.py` | OpenRouter API вызов + парсинг ответа |
| `services/storage.py` | SQLite + файловое хранилище |
| `templates/index.html` | UI: запись, история, поиск, настройки |
| `tray.py` | Системный трей (pystray) |
| `build.py` | PyInstaller build script |
| `.github/workflows/ci.yml` | CI: ruff + mypy + pytest |
| `.github/workflows/release.yml` | Release: build .exe на тег v*.*.* |
| `dist/` | Готовые .exe — НЕ УДАЛЯТЬ |

---

*Last updated: 2026-03-06 by Claude Code*
