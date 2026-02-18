import base64
import httpx
from config import OPENROUTER_API_KEY, MODEL, TRANSCRIBE_PROMPT, SUPPORTED_FORMATS


def _detect_format(content_type: str, filename: str) -> str:
    fmt = SUPPORTED_FORMATS.get(content_type.split(";")[0].strip())
    if fmt:
        return fmt

    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    ext_map = {
        "ogg": "ogg", "mp3": "mp3", "wav": "wav",
        "webm": "webm", "mp4": "mp4", "m4a": "m4a",
        "aac": "aac", "flac": "flac",
    }
    return ext_map.get(ext, "mp3")


def _parse_response(raw: str) -> tuple[str, str]:
    title = "Untitled"
    text = raw.strip()

    lines = raw.strip().splitlines()
    title_line = next((l for l in lines if l.startswith("TITLE:")), None)
    text_line = next((i for i, l in enumerate(lines) if l.startswith("TEXT:")), None)

    if title_line:
        title = title_line.replace("TITLE:", "").strip()
    if text_line is not None:
        text = "\n".join(lines[text_line:]).replace("TEXT:", "", 1).strip()

    return title, text


async def transcribe_audio(audio_bytes: bytes, content_type: str, filename: str) -> dict:
    if not OPENROUTER_API_KEY:
        raise ValueError("OPENROUTER_API_KEY is not set in .env")

    audio_format = _detect_format(content_type, filename)
    audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")

    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": TRANSCRIBE_PROMPT,
                    },
                    {
                        "type": "input_audio",
                        "input_audio": {
                            "data": audio_b64,
                            "format": audio_format,
                        },
                    },
                ],
            }
        ],
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/voice-transcriber",
                "X-Title": "Voice Transcriber",
            },
            json=payload,
        )

    if response.status_code != 200:
        raise RuntimeError(f"OpenRouter error {response.status_code}: {response.text}")

    data = response.json()
    raw_text = data["choices"][0]["message"]["content"]
    title, text = _parse_response(raw_text)

    return {"title": title, "text": text}
