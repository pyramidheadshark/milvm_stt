"""
Build: uv run python build.py
Output: dist/VoiceTranscriber.exe (Windows) or dist/VoiceTranscriber (Linux/macOS)

What PyInstaller needs to know:
- templates/ and assets/ go into the bundle (MEIPASS) — read-only runtime files
- .env and transcripts/ stay next to the exe  — user data, not bundled
- paths.py handles the MEIPASS vs dev-mode resolution at runtime
"""
import subprocess
import sys
import os

APP_NAME = "VoiceTranscriber"
ENTRY    = "tray.py"
SEP      = ";" if sys.platform == "win32" else ":"


def main():
    try:
        import PyInstaller
    except ImportError:
        print("Installing PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

    here     = os.path.dirname(os.path.abspath(__file__))
    icon_ico = os.path.join(here, "assets", "icon.ico")
    icon_png = os.path.join(here, "assets", "icon.png")

    args = [
        "pyinstaller",
        "--noconfirm",
        "--clean",
        f"--name={APP_NAME}",
        "--onefile",
        "--noconsole",
        "--add-data", f"templates{SEP}templates",
        "--add-data", f"assets{SEP}assets",
        "--add-data", f"paths.py{SEP}.",
        "--collect-all", "webview",
        "--collect-all", "pystray",
        "--hidden-import", "uvicorn.lifespan.on",
        "--hidden-import", "uvicorn.protocols.websockets.auto",
        "--hidden-import", "uvicorn.protocols.http.auto",
        "--hidden-import", "uvicorn.logging",
        "--hidden-import", "aiosqlite",
        "--hidden-import", "jinja2",
        "--hidden-import", "multipart",
        "--hidden-import", "dotenv",
    ]

    if sys.platform == "win32" and os.path.exists(icon_ico):
        args += ["--icon", icon_ico]
    elif os.path.exists(icon_png):
        args += ["--icon", icon_png]

    args.append(ENTRY)

    print(f"Building {APP_NAME}...")
    result = subprocess.run(args, cwd=here)

    if result.returncode == 0:
        ext  = ".exe" if sys.platform == "win32" else ""
        dist = os.path.join(here, "dist", f"{APP_NAME}{ext}")
        print(f"\nBuild successful: {dist}")
        print(f"Place .env next to the exe before running.")
    else:
        print("\nBuild failed.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
