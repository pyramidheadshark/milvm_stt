import os
from unittest.mock import patch

import pytest

import config
from config import reload_config, validate_config, write_settings


class TestValidateConfig:
    def test_passes_with_api_key_set(self):
        with (
            patch("config.OPENROUTER_API_KEY", "sk-or-v1-test"),
            patch("config._REQUIRED", {"OPENROUTER_API_KEY": "sk-or-v1-test"}),
        ):
            validate_config()

    def test_raises_when_api_key_missing(self):
        with (
            patch("config._REQUIRED", {"OPENROUTER_API_KEY": ""}),
            pytest.raises(RuntimeError, match="OPENROUTER_API_KEY"),
        ):
            validate_config()

    def test_error_message_mentions_env_file(self):
        with (
            patch("config._REQUIRED", {"OPENROUTER_API_KEY": ""}),
            pytest.raises(RuntimeError, match=".env"),
        ):
            validate_config()


class TestWriteSettings:
    @pytest.fixture(autouse=True)
    def temp_dotenv(self, tmp_path):
        self.dotenv = str(tmp_path / ".env")

    def _read(self) -> str:
        with open(self.dotenv) as f:
            return f.read()

    def test_creates_file_with_api_key(self):
        with patch("config.DOTENV_PATH", self.dotenv), patch("config.reload_config"):
            write_settings("sk-or-v1-new", "")
        assert "OPENROUTER_API_KEY=sk-or-v1-new" in self._read()

    def test_creates_file_with_model(self):
        with patch("config.DOTENV_PATH", self.dotenv), patch("config.reload_config"):
            write_settings("", "google/gemini-flash")
        assert "MODEL=google/gemini-flash" in self._read()

    def test_updates_existing_key(self):
        with open(self.dotenv, "w") as f:
            f.write("OPENROUTER_API_KEY=old-key\n")
        with patch("config.DOTENV_PATH", self.dotenv), patch("config.reload_config"):
            write_settings("sk-or-v1-new", "")
        content = self._read()
        assert "OPENROUTER_API_KEY=sk-or-v1-new" in content
        assert "old-key" not in content

    def test_appends_new_key_preserving_other_lines(self):
        with open(self.dotenv, "w") as f:
            f.write("OTHER_KEY=value\n")
        with patch("config.DOTENV_PATH", self.dotenv), patch("config.reload_config"):
            write_settings("sk-or-v1-test", "")
        content = self._read()
        assert "OTHER_KEY=value" in content
        assert "OPENROUTER_API_KEY=sk-or-v1-test" in content

    def test_preserves_comments(self):
        with open(self.dotenv, "w") as f:
            f.write("# My comment\nOPENROUTER_API_KEY=old\n")
        with patch("config.DOTENV_PATH", self.dotenv), patch("config.reload_config"):
            write_settings("sk-new", "")
        assert "# My comment" in self._read()

    def test_writes_both_key_and_model(self):
        with patch("config.DOTENV_PATH", self.dotenv), patch("config.reload_config"):
            write_settings("sk-or-v1-x", "custom/model")
        content = self._read()
        assert "OPENROUTER_API_KEY=sk-or-v1-x" in content
        assert "MODEL=custom/model" in content

    def test_no_op_when_both_empty(self):
        with patch("config.DOTENV_PATH", self.dotenv), patch("config.reload_config") as mock_reload:
            write_settings("", "")
        assert not os.path.exists(self.dotenv)
        mock_reload.assert_not_called()

    def test_calls_reload_config(self):
        with patch("config.DOTENV_PATH", self.dotenv), patch("config.reload_config") as mock_reload:
            write_settings("sk-test", "")
        mock_reload.assert_called_once()


class TestReloadConfig:
    @pytest.fixture(autouse=True)
    def restore_config_globals(self):
        orig_key = config.OPENROUTER_API_KEY
        orig_model = config.MODEL
        orig_required = config._REQUIRED.copy()
        orig_env = {k: os.environ.get(k) for k in ["OPENROUTER_API_KEY", "MODEL"]}
        yield
        config.OPENROUTER_API_KEY = orig_key
        config.MODEL = orig_model
        config._REQUIRED = orig_required
        for k, v in orig_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def test_updates_api_key_from_dotenv(self, tmp_path):
        dotenv = tmp_path / ".env"
        dotenv.write_text("OPENROUTER_API_KEY=sk-or-v1-reloaded\n")
        with patch("config.DOTENV_PATH", str(dotenv)):
            reload_config()
        assert config.OPENROUTER_API_KEY == "sk-or-v1-reloaded"

    def test_updates_model_from_dotenv(self, tmp_path):
        dotenv = tmp_path / ".env"
        dotenv.write_text("MODEL=custom/model-test\n")
        with patch("config.DOTENV_PATH", str(dotenv)):
            reload_config()
        assert config.MODEL == "custom/model-test"

    def test_updates_required_dict(self, tmp_path):
        dotenv = tmp_path / ".env"
        dotenv.write_text("OPENROUTER_API_KEY=sk-or-v1-check\n")
        with patch("config.DOTENV_PATH", str(dotenv)):
            reload_config()
        assert config._REQUIRED["OPENROUTER_API_KEY"] == "sk-or-v1-check"

    def test_empty_dotenv_clears_key(self, tmp_path):
        dotenv = tmp_path / ".env"
        dotenv.write_text("")
        os.environ.pop("OPENROUTER_API_KEY", None)
        with patch("config.DOTENV_PATH", str(dotenv)):
            reload_config()
        assert config.OPENROUTER_API_KEY == ""
