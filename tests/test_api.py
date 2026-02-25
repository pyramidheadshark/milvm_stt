import os
import tempfile
from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, patch

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

os.environ.setdefault("OPENROUTER_API_KEY", "test-key")


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")

        with (
            patch("services.storage.TRANSCRIPTS_DIR", tmpdir),
            patch("services.storage.DB_PATH", db_path),
        ):
            from services.storage import init_db

            await init_db()

            from main import app

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                yield ac


class TestIndexEndpoint:
    async def test_index_returns_200(self, client: AsyncClient):
        resp = await client.get("/")
        assert resp.status_code == 200
        assert "Voice Transcriber" in resp.text

    async def test_index_content_type_html(self, client: AsyncClient):
        resp = await client.get("/")
        assert "text/html" in resp.headers["content-type"]


class TestHistoryEndpoint:
    async def test_history_returns_list(self, client: AsyncClient):
        resp = await client.get("/history")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    async def test_history_empty_initially(self, client: AsyncClient):
        resp = await client.get("/history")
        assert resp.json() == []


class TestSearchEndpoint:
    async def test_search_requires_query(self, client: AsyncClient):
        resp = await client.get("/search")
        assert resp.status_code == 422

    async def test_search_empty_query_rejected(self, client: AsyncClient):
        resp = await client.get("/search?q=")
        assert resp.status_code == 422

    async def test_search_returns_list(self, client: AsyncClient):
        resp = await client.get("/search?q=test")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


class TestTranscribeEndpoint:
    async def test_empty_file_rejected(self, client: AsyncClient):
        resp = await client.post(
            "/transcribe",
            files={"file": ("empty.ogg", b"", "audio/ogg")},
        )
        assert resp.status_code == 400
        assert "Empty" in resp.json()["detail"]

    async def test_file_too_large_rejected(self, client: AsyncClient):
        big = b"x" * (26 * 1024 * 1024)
        resp = await client.post(
            "/transcribe",
            files={"file": ("big.ogg", big, "audio/ogg")},
        )
        assert resp.status_code == 400
        assert "too large" in resp.json()["detail"].lower()

    async def test_no_api_key_raises_500(self, client: AsyncClient):
        with patch("services.transcriber.OPENROUTER_API_KEY", ""):
            resp = await client.post(
                "/transcribe",
                files={"file": ("test.ogg", b"fake-audio-data", "audio/ogg")},
            )
        assert resp.status_code == 500
        assert "OPENROUTER_API_KEY" in resp.json()["detail"]

    async def test_successful_transcription(self, client: AsyncClient):
        mock_result = {"title": "Тестовый заголовок", "text": "Тестовый текст записи."}
        with patch(
            "main.transcribe_audio",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            resp = await client.post(
                "/transcribe",
                files={"file": ("test.ogg", b"fake-audio-data", "audio/ogg")},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "Тестовый заголовок"
        assert data["text"] == "Тестовый текст записи."
        assert "id" in data
        assert "created_at" in data

    async def test_transcription_saved_to_history(self, client: AsyncClient):
        mock_result = {"title": "Для истории", "text": "Текст для истории."}
        with patch(
            "main.transcribe_audio",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            await client.post(
                "/transcribe",
                files={"file": ("test.ogg", b"fake-audio-data", "audio/ogg")},
            )

        history = (await client.get("/history")).json()
        assert any(r["title"] == "Для истории" for r in history)

    async def test_api_error_returns_502(self, client: AsyncClient):
        with patch(
            "main.transcribe_audio",
            new_callable=AsyncMock,
            side_effect=RuntimeError("API недоступен"),
        ):
            resp = await client.post(
                "/transcribe",
                files={"file": ("test.ogg", b"fake-audio-data", "audio/ogg")},
            )
        assert resp.status_code == 502


class TestDeleteEndpoint:
    async def test_delete_nonexistent_returns_404(self, client: AsyncClient):
        resp = await client.delete("/transcription/99999")
        assert resp.status_code == 404

    async def test_delete_existing_record(self, client: AsyncClient):
        mock_result = {"title": "Удалить меня", "text": "Текст для удаления."}
        with patch(
            "main.transcribe_audio",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            post_resp = await client.post(
                "/transcribe",
                files={"file": ("test.ogg", b"fake-audio-data", "audio/ogg")},
            )
        record_id = post_resp.json()["id"]

        del_resp = await client.delete(f"/transcription/{record_id}")
        assert del_resp.status_code == 200
        assert del_resp.json()["deleted"] == record_id

        history = (await client.get("/history")).json()
        assert not any(r["id"] == record_id for r in history)
