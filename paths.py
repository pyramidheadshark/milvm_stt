"""
Central path resolution.
When frozen by PyInstaller (--onefile), runtime files (templates, assets)
are unpacked to sys._MEIPASS. User data (transcripts, .env) must stay
next to the exe so they survive updates — we use the exe's directory for that.
"""

import os
import sys


def _frozen_bundle_dir() -> str:
    return (
        sys._MEIPASS  # type: ignore[attr-defined]
        if getattr(sys, "frozen", False)
        else os.path.dirname(os.path.abspath(__file__))
    )


def _user_data_dir() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


BUNDLE_DIR = _frozen_bundle_dir()
USER_DATA_DIR = _user_data_dir()

TEMPLATES_DIR = os.path.join(BUNDLE_DIR, "templates")
ASSETS_DIR = os.path.join(BUNDLE_DIR, "assets")
TRANSCRIPTS_DIR = os.path.join(USER_DATA_DIR, "transcripts")
DB_PATH = os.path.join(TRANSCRIPTS_DIR, "history.db")
DOTENV_PATH = os.path.join(USER_DATA_DIR, ".env")
