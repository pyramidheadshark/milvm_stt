import aiosqlite
import os
from datetime import datetime
from paths import DB_PATH, TRANSCRIPTS_DIR


async def init_db():
    os.makedirs(TRANSCRIPTS_DIR, exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS transcriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                text TEXT NOT NULL,
                filename TEXT,
                created_at TEXT NOT NULL
            )
        """)
        await db.commit()


async def save_transcription(title: str, text: str, filename: str) -> dict:
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO transcriptions (title, text, filename, created_at) VALUES (?, ?, ?, ?)",
            (title, text, filename, created_at)
        )
        await db.commit()
        record_id = cursor.lastrowid

    txt_path = os.path.join(TRANSCRIPTS_DIR, f"{record_id:04d}_{_safe_name(title)}.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(f"Title: {title}\n")
        f.write(f"Date: {created_at}\n")
        f.write(f"Source: {filename}\n")
        f.write("-" * 40 + "\n\n")
        f.write(text)

    return {
        "id": record_id,
        "title": title,
        "text": text,
        "filename": filename,
        "created_at": created_at,
    }


async def get_history(limit: int = 200) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM transcriptions ORDER BY id DESC LIMIT ?", (limit,)
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def search_history(query: str, limit: int = 200) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        like = f"%{query}%"
        cursor = await db.execute(
            "SELECT * FROM transcriptions WHERE title LIKE ? OR text LIKE ? ORDER BY id DESC LIMIT ?",
            (like, like, limit)
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def delete_transcription(record_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT title FROM transcriptions WHERE id = ?", (record_id,)
        )
        row = await cursor.fetchone()
        if not row:
            return False

        txt_path = os.path.join(TRANSCRIPTS_DIR, f"{record_id:04d}_{_safe_name(row[0])}.txt")
        if os.path.exists(txt_path):
            os.remove(txt_path)

        await db.execute("DELETE FROM transcriptions WHERE id = ?", (record_id,))
        await db.commit()
        return True


async def save_failed_audio(audio_bytes: bytes, filename: str) -> str:
    os.makedirs(TRANSCRIPTS_DIR, exist_ok=True)
    from datetime import datetime
    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
    name = f"FAILED_{ts}_{filename}"
    path = os.path.join(TRANSCRIPTS_DIR, name)
    with open(path, "wb") as f:
        f.write(audio_bytes)
    return path


def _safe_name(name: str) -> str:
    safe = "".join(c if c.isalnum() or c in " -_" else "" for c in name)
    return safe.strip().replace(" ", "_")[:50]
