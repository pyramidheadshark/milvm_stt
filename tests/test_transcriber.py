from services.transcriber import _clean_text, _detect_format, _parse_response, _strip_markdown


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
