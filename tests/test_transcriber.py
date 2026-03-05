import base64
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.transcriber import (
    RETRY_ATTEMPTS,
    _call_api,
    _clean_text,
    _detect_format,
    _parse_response,
    _strip_markdown,
    transcribe_audio,
)


class TestStripMarkdown:
    def test_removes_bold(self):
        assert _strip_markdown("**bold**") == "bold"

    def test_removes_italic(self):
        assert _strip_markdown("*italic*") == "italic"

    def test_removes_triple_bold(self):
        assert _strip_markdown("***both***") == "both"

    def test_removes_underscore_italic(self):
        assert _strip_markdown("_italic_") == "italic"

    def test_removes_code(self):
        assert _strip_markdown("`code`") == "code"

    def test_strips_whitespace(self):
        assert _strip_markdown("  hello  ") == "hello"

    def test_plain_text_unchanged(self):
        assert _strip_markdown("plain text") == "plain text"


class TestParseResponse:
    def test_standard_format(self):
        raw = "TITLE: Идея приложения\nTEXT: Хочу сделать приложение для трекинга."
        title, text = _parse_response(raw)
        assert title == "Идея приложения"
        assert text == "Хочу сделать приложение для трекинга."

    def test_case_insensitive(self):
        raw = "title: Заголовок\ntext: Текст записи"
        title, text = _parse_response(raw)
        assert title == "Заголовок"
        assert "Текст записи" in text

    def test_strips_markdown_from_fields(self):
        raw = "TITLE: **Важная идея**\nTEXT: Нужно сделать *срочно*."
        title, text = _parse_response(raw)
        assert title == "Важная идея"
        assert "срочно" in text
        assert "*" not in title

    def test_fallback_no_format(self):
        raw = "Просто текст без форматирования заголовка и тела"
        title, text = _parse_response(raw)
        assert title != ""
        assert len(title) > 0

    def test_empty_response_gets_default_title(self):
        title, text = _parse_response("")
        assert title == "Без названия"

    def test_only_title_line(self):
        raw = "TITLE: Только заголовок\nTEXT: "
        title, text = _parse_response(raw)
        assert title == "Только заголовок"

    def test_multiline_text(self):
        raw = "TITLE: Встреча\nTEXT: Обсудили план.\nУточнили сроки.\nЗафиксировали."
        title, text = _parse_response(raw)
        assert title == "Встреча"
        assert "Обсудили план." in text
        assert "Зафиксировали." in text

    def test_strips_prefix_artifact(self):
        raw = "Конечно! Вот ваша транскрипция:\nTITLE: Чистый заголовок\nTEXT: Чистый текст"
        title, text = _parse_response(raw)
        assert title == "Чистый заголовок"
        assert text == "Чистый текст"

    def test_title_whitespace_normalized(self):
        raw = "TITLE:   Много   пробелов   \nTEXT: Текст"
        title, text = _parse_response(raw)
        assert "  " not in title

    def test_english_response(self):
        raw = "TITLE: Meeting Notes\nTEXT: We discussed the roadmap for Q2."
        title, text = _parse_response(raw)
        assert title == "Meeting Notes"
        assert "Q2" in text


class TestDetectFormat:
    def test_known_content_type_ogg(self):
        assert _detect_format("audio/ogg", "file.ogg") == "ogg"

    def test_known_content_type_mp3(self):
        assert _detect_format("audio/mpeg", "file.mp3") == "mp3"

    def test_content_type_with_codec(self):
        assert _detect_format("audio/webm;codecs=opus", "file.webm") == "webm"

    def test_fallback_to_extension(self):
        assert _detect_format("application/octet-stream", "recording.wav") == "wav"

    def test_unknown_falls_back_to_mp3(self):
        assert _detect_format("audio/unknown", "file.xyz") == "mp3"

    def test_m4a_extension(self):
        assert _detect_format("application/octet-stream", "voice.m4a") == "m4a"

    def test_flac_content_type(self):
        assert _detect_format("audio/flac", "file.flac") == "flac"


class TestCleanText:
    def test_removes_suffix_artifact_ru(self):
        text = "Основной текст\n\nЕсли у вас возникнут вопросы, обращайтесь!"
        result = _clean_text(text)
        assert "обращайтесь" not in result
        assert "Основной текст" in result

    def test_removes_suffix_artifact_en(self):
        text = "Main text\n\nFeel free to ask if you need anything!"
        result = _clean_text(text)
        assert "Feel free" not in result
        assert "Main text" in result

    def test_removes_mogu_pomoch(self):
        text = "Полезная запись встречи.\n\nМогу с чем-то ещё помочь?"
        result = _clean_text(text)
        assert "Могу" not in result
        assert "Полезная запись" in result

    def test_removes_nadeius(self):
        text = "Текст заметки.\n\nНадеюсь, это было полезно!"
        result = _clean_text(text)
        assert "Надеюсь" not in result
        assert "Текст заметки" in result

    def test_removes_hope_this_helps(self):
        text = "Meeting notes.\n\nHope this helps!"
        result = _clean_text(text)
        assert "Hope" not in result
        assert "Meeting notes" in result

    def test_removes_glad_to_help(self):
        text = "Project update.\n\nGlad to help with anything else!"
        result = _clean_text(text)
        assert "Glad" not in result
        assert "Project update" in result

    def test_clean_text_unchanged(self):
        text = "Просто обычный текст без артефактов."
        assert _clean_text(text) == text


def _make_httpx_mock(
    status_code: int = 200, content: str = "TITLE: T\nTEXT: X", response_text: str = ""
):
    mock_response = MagicMock()
    mock_response.status_code = status_code
    mock_response.json.return_value = {"choices": [{"message": {"content": content}}]}
    mock_response.text = response_text or content
    mock_post = AsyncMock(return_value=mock_response)

    mock_client = AsyncMock()
    mock_client.post = mock_post

    mock_client_cls = MagicMock()
    mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

    return mock_client_cls, mock_post


class TestCallApi:
    async def test_returns_content_on_200(self):
        mock_cls, _ = _make_httpx_mock(content="TITLE: Result\nTEXT: Body")
        with patch("services.transcriber.httpx.AsyncClient", mock_cls):
            result = await _call_api("b64data", "ogg")
        assert result == "TITLE: Result\nTEXT: Body"

    async def test_sends_authorization_header(self):
        mock_cls, mock_post = _make_httpx_mock()
        with (
            patch("services.transcriber.httpx.AsyncClient", mock_cls),
            patch("services.transcriber.config.OPENROUTER_API_KEY", "sk-test-key"),
        ):
            await _call_api("b64data", "ogg")
        headers = mock_post.call_args.kwargs["headers"]
        assert headers["Authorization"] == "Bearer sk-test-key"

    async def test_sends_model_from_config(self):
        mock_cls, mock_post = _make_httpx_mock()
        with (
            patch("services.transcriber.httpx.AsyncClient", mock_cls),
            patch("services.transcriber.config.MODEL", "custom/model-xyz"),
        ):
            await _call_api("b64data", "ogg")
        payload = mock_post.call_args.kwargs["json"]
        assert payload["model"] == "custom/model-xyz"

    async def test_sends_audio_b64_and_format_in_payload(self):
        mock_cls, mock_post = _make_httpx_mock()
        with patch("services.transcriber.httpx.AsyncClient", mock_cls):
            await _call_api("myaudiodata==", "webm")
        payload = mock_post.call_args.kwargs["json"]
        audio_part = payload["messages"][0]["content"][1]
        assert audio_part["type"] == "input_audio"
        assert audio_part["input_audio"]["data"] == "myaudiodata=="
        assert audio_part["input_audio"]["format"] == "webm"

    async def test_raises_runtime_error_on_non_200(self):
        mock_cls, _ = _make_httpx_mock(status_code=429, response_text="Rate limit exceeded")
        with (
            patch("services.transcriber.httpx.AsyncClient", mock_cls),
            pytest.raises(RuntimeError, match="429"),
        ):
            await _call_api("b64data", "ogg")

    async def test_raises_on_500_with_text(self):
        mock_cls, _ = _make_httpx_mock(status_code=500, response_text="Internal error")
        with (
            patch("services.transcriber.httpx.AsyncClient", mock_cls),
            pytest.raises(RuntimeError, match="500"),
        ):
            await _call_api("b64data", "ogg")


class TestTranscribeAudio:
    async def test_raises_value_error_without_api_key(self):
        with (
            patch("services.transcriber.config.OPENROUTER_API_KEY", ""),
            pytest.raises(ValueError, match="OPENROUTER_API_KEY"),
        ):
            await transcribe_audio(b"audio", "audio/ogg", "test.ogg")

    async def test_returns_title_and_text(self):
        with (
            patch("services.transcriber._call_api", new_callable=AsyncMock) as mock_api,
            patch("services.transcriber.config.OPENROUTER_API_KEY", "sk-test"),
        ):
            mock_api.return_value = "TITLE: My Title\nTEXT: My content here."
            result = await transcribe_audio(b"audio", "audio/ogg", "test.ogg")
        assert result["title"] == "My Title"
        assert result["text"] == "My content here."

    async def test_encodes_audio_to_base64(self):
        captured: dict = {}

        async def fake_call(b64: str, fmt: str) -> str:
            captured["b64"] = b64
            captured["fmt"] = fmt
            return "TITLE: T\nTEXT: X"

        with (
            patch("services.transcriber._call_api", side_effect=fake_call),
            patch("services.transcriber.config.OPENROUTER_API_KEY", "sk-test"),
        ):
            await transcribe_audio(b"raw audio bytes", "audio/webm", "rec.webm")

        assert captured["b64"] == base64.b64encode(b"raw audio bytes").decode()
        assert captured["fmt"] == "webm"

    async def test_retries_on_failure_and_succeeds(self):
        with (
            patch("services.transcriber._call_api", new_callable=AsyncMock) as mock_api,
            patch("services.transcriber.config.OPENROUTER_API_KEY", "sk-test"),
            patch("services.transcriber.asyncio.sleep", new_callable=AsyncMock),
        ):
            mock_api.side_effect = [
                RuntimeError("fail 1"),
                RuntimeError("fail 2"),
                "TITLE: OK\nTEXT: Done",
            ]
            result = await transcribe_audio(b"audio", "audio/ogg", "test.ogg")
        assert result["title"] == "OK"
        assert mock_api.call_count == 3

    async def test_raises_after_all_retries_exhausted(self):
        with (
            patch("services.transcriber._call_api", new_callable=AsyncMock) as mock_api,
            patch("services.transcriber.config.OPENROUTER_API_KEY", "sk-test"),
            patch("services.transcriber.asyncio.sleep", new_callable=AsyncMock),
        ):
            mock_api.side_effect = RuntimeError("API down")
            with pytest.raises(RuntimeError, match="попытки"):
                await transcribe_audio(b"audio", "audio/ogg", "test.ogg")
        assert mock_api.call_count == RETRY_ATTEMPTS

    async def test_no_sleep_on_last_attempt(self):
        with (
            patch("services.transcriber._call_api", new_callable=AsyncMock) as mock_api,
            patch("services.transcriber.config.OPENROUTER_API_KEY", "sk-test"),
            patch("services.transcriber.asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
        ):
            mock_api.side_effect = RuntimeError("fail")
            with pytest.raises(RuntimeError):
                await transcribe_audio(b"audio", "audio/ogg", "test.ogg")
        assert mock_sleep.call_count == RETRY_ATTEMPTS - 1
