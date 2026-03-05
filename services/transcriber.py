import asyncio
import base64
import re

import httpx

import config
from config import SUPPORTED_FORMATS, TRANSCRIBE_PROMPT

RETRY_ATTEMPTS = 3
RETRY_DELAY = 2.0

_ARTIFACT_PREFIX = re.compile(
    r"^[\s\S]{0,120}?(?:"
    r"вот\s+(?:ваша\s+)?(?:транскрип|запись|текст|расшиф)|"
    r"(?:конечно|пожалуйста)[!,.]?\s|"
    r"транскрипци[яю]\s+(?:аудио|записи|файла)|"
    r"here\s+is\s+(?:the\s+)?(?:transcri|text)|"
    r"certainly|sure[,!]"
    r")[^:]*[:\n]",
    re.IGNORECASE,
)

_ARTIFACT_SUFFIX = re.compile(
    r"\n+(?:"
    r"(?:могу\s+(?:с\s+чем.то\s+)?(?:ещё\s+)?помочь)|"
    r"(?:если|если\s+у\s+вас|обращайтесь|не\s+стесняйтесь)|"
    r"(?:рад\s+(?:был\s+)?помочь|буду\s+рад)|"
    r"(?:надеюсь[,\s]|успехов[!.]|удачи[!.]|хорошего\s+дня)|"
    r"(?:если\s+(?:возникнут|есть|появятся)\s+вопросы?)|"
    r"(?:если\s+что.то\s+непонятно)|"
    r"(?:пожалуйста[,\s]+обращайтесь)|"
    r"(?:if\s+you\s+(?:need|have|want)|feel\s+free|let\s+me\s+know)|"
    r"(?:happy\s+to\s+help|glad\s+to\s+help|hope\s+(?:this|that)\s+helps?)|"
    r"(?:best\s+(?:of\s+luck|regards)|good\s+luck)"
    r")[\s\S]*$",
    re.IGNORECASE,
)


def _detect_format(content_type: str, filename: str) -> str:
    fmt = SUPPORTED_FORMATS.get(content_type.split(";")[0].strip())
    if fmt:
        return fmt
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return {
        "ogg": "ogg",
        "mp3": "mp3",
        "wav": "wav",
        "webm": "webm",
        "mp4": "mp4",
        "m4a": "m4a",
        "aac": "aac",
        "flac": "flac",
    }.get(ext, "mp3")


def _strip_markdown(text: str) -> str:
    text = re.sub(r"\*{1,3}([^*\n]+)\*{1,3}", r"\1", text)
    text = re.sub(r"_{1,3}([^_\n]+)_{1,3}", r"\1", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    return text.strip()


def _clean_text(text: str) -> str:
    text = _ARTIFACT_PREFIX.sub("", text, count=1).strip()
    text = _ARTIFACT_SUFFIX.sub("", text).strip()
    return text


def _parse_response(raw: str) -> tuple[str, str]:
    cleaned = _strip_markdown(raw)

    title_match = re.search(
        r"TITLE\s*:\s*(.+?)(?=\n\s*TEXT\s*:)", cleaned, re.IGNORECASE | re.DOTALL
    )
    text_match = re.search(r"TEXT\s*:\s*(.+)", cleaned, re.IGNORECASE | re.DOTALL)

    title = title_match.group(1).strip() if title_match else ""
    text = text_match.group(1).strip() if text_match else ""

    if not title and not text:
        lines = [ln.strip() for ln in cleaned.splitlines() if ln.strip()]
        title = lines[0] if lines else "Без названия"
        text = "\n".join(lines[1:]) if len(lines) > 1 else cleaned

    if not title:
        title = "Без названия"
    if not text:
        text = _clean_text(cleaned)

    title = re.sub(r"\s+", " ", title).strip()
    text = _clean_text(text)

    return title, text


async def _call_api(audio_b64: str, audio_format: str) -> str:
    payload = {
        "model": config.MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": TRANSCRIBE_PROMPT},
                    {
                        "type": "input_audio",
                        "input_audio": {"data": audio_b64, "format": audio_format},
                    },
                ],
            }
        ],
    }
    async with httpx.AsyncClient(timeout=90.0) as client:
        response = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {config.OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/voice-transcriber",
                "X-Title": "Voice Transcriber",
            },
            json=payload,
        )
    if response.status_code != 200:
        raise RuntimeError(f"OpenRouter {response.status_code}: {response.text[:300]}")
    return response.json()["choices"][0]["message"]["content"]


async def transcribe_audio(audio_bytes: bytes, content_type: str, filename: str) -> dict:
    if not config.OPENROUTER_API_KEY:
        raise ValueError("OPENROUTER_API_KEY не задан. Откройте настройки (⚙) и введите ключ.")

    audio_format = _detect_format(content_type, filename)
    audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")

    last_error: Exception | None = None

    for attempt in range(1, RETRY_ATTEMPTS + 1):
        try:
            raw_text = await _call_api(audio_b64, audio_format)
            title, text = _parse_response(raw_text)
            return {"title": title, "text": text}
        except Exception as e:
            last_error = e
            if attempt < RETRY_ATTEMPTS:
                await asyncio.sleep(RETRY_DELAY * attempt)

    raise RuntimeError(f"Все {RETRY_ATTEMPTS} попытки завершились ошибкой: {last_error}")
