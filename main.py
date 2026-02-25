from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from config import HOST, PORT, SUPPORTED_FORMATS
from paths import TEMPLATES_DIR
from services.storage import (
    delete_transcription,
    get_history,
    init_db,
    save_failed_audio,
    save_transcription,
    search_history,
)
from services.transcriber import transcribe_audio


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
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
        raise HTTPException(502, f"{e} | Аудио сохранено: {saved_path}") from e

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


if __name__ == "__main__":
    uvicorn.run("main:app", host=HOST, port=PORT, reload=False)
