from unittest.mock import patch

import pytest

from config import validate_config


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
