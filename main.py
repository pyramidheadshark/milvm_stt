import os
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

import config
from config import HOST, PORT, SUPPORTED_FORMATS, validate_config, write_settings
from paths import TEMPLATES_DIR
from services.storage import (
    delete_transcription,
    get_failed_audio_path,
    get_history,
    init_db,
    list_failed_audio,
    save_failed_audio,
    save_transcription,
    search_history,
)
from services.transcriber import transcribe_audio


@asynccontextmanager
async def lifespan(app: FastAPI):
    import logging

    await init_db()
    try:
        validate_config()
    except RuntimeError as e:
        logging.warning("Config warning: %s", e)
    yield


app = FastAPI(title="Voice Transcriber", lifespan=lifespan)
templates = Jinja2Templates(directory=TEMPLATES_DIR)

MAX_FILE_SIZE_MB = 25
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    history = await get_history()
    return templates.TemplateResponse(request, "index.html", {"history": history})


@app.post("/transcribe")
async def transcribe(file: UploadFile = File(...)):  # noqa: B008
    audio_bytes = await file.read()

    if len(audio_bytes) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(400, f"File too large. Max size: {MAX_FILE_SIZE_MB}MB")

    if len(audio_bytes) == 0:
        raise HTTPException(400, "Empty file received")

    content_type = file.content_type or "audio/ogg"
    filename = file.filename or "recording.ogg"

    base_ct = content_type.split(";")[0].strip()
    if base_ct not in SUPPORTED_FORMATS and not any(
        filename.endswith(f".{ext}") for ext in ["ogg", "mp3", "wav", "webm", "m4a", "aac", "flac"]
    ):
        raise HTTPException(400, f"Unsupported format: {content_type}")

    try:
        result = await transcribe_audio(audio_bytes, content_type, filename)
    except ValueError as e:
        raise HTTPException(500, str(e)) from e
    except RuntimeError as e:
        saved_path = await save_failed_audio(audio_bytes, filename)
        raise HTTPException(
            502, {"message": str(e), "saved_filename": os.path.basename(saved_path)}
        ) from e

    record = await save_transcription(result["title"], result["text"], filename)
    return JSONResponse(record)


@app.get("/history")
async def history():
    return JSONResponse(await get_history())


@app.get("/search")
async def search(q: str = Query(..., min_length=1)):
    return JSONResponse(await search_history(q))


@app.delete("/transcription/{record_id}")
async def delete(record_id: int):
    ok = await delete_transcription(record_id)
    if not ok:
        raise HTTPException(404, "Record not found")
    return JSONResponse({"deleted": record_id})


@app.get("/failed-audio")
async def get_failed_audio_list():
    return JSONResponse(list_failed_audio())


@app.get("/failed-audio/{filename}")
async def download_failed_audio(filename: str):
    if "/" in filename or "\\" in filename or filename.startswith("."):
        raise HTTPException(400, "Invalid filename")
    path = get_failed_audio_path(filename)
    if not path:
        raise HTTPException(404, "File not found")
    return FileResponse(path, filename=filename)


@app.get("/settings")
async def get_settings():
    key = config.OPENROUTER_API_KEY
    hint = f"sk-or-...{key[-4:]}" if len(key) > 8 else ("(задан)" if key else "(не задан)")
    return JSONResponse({"api_key_hint": hint, "api_key_set": bool(key), "model": config.MODEL})


@app.post("/settings")
async def post_settings(request: Request):
    data = await request.json()
    api_key = str(data.get("api_key", "")).strip()
    model = str(data.get("model", "")).strip()
    if not api_key and not model:
        raise HTTPException(400, "No settings to save")
    write_settings(api_key, model)
    return JSONResponse({"ok": True})


if __name__ == "__main__":
    uvicorn.run("main:app", host=HOST, port=PORT, reload=False)
