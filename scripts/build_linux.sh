#!/usr/bin/env bash
# Linux build: PyInstaller --onefile --console → tar.gz.
# Консольное приложение tg-exporter (Click CLI), entry point: tg_exporter_cli/main.py.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# Версия для вшивания в бинарник
VERSION="${TG_EXPORTER_VERSION:-0.0.0}"
echo "VERSION = \"$VERSION\"" > tg_exporter_cli/_version.py
echo "Версия сборки: $VERSION"

pip install pyinstaller &>/dev/null || { echo "Ошибка: не удалось установить pyinstaller" >&2; exit 1; }
pip install -e . &>/dev/null || { echo "Ошибка: не удалось установить проект" >&2; exit 1; }

pyinstaller --onefile --console --name tg-exporter \
  --exclude-module customtkinter \
  --exclude-module app_legacy \
  --exclude-module app \
  --collect-all telethon \
  --collect-all faster_whisper \
  --collect-all ctranslate2 \
  --collect-all tokenizers \
  --collect-all imageio_ffmpeg \
  --collect-all tg_exporter \
  --hidden-import tg_exporter.services.transcription.factory \
  tg_exporter_cli/main.py

EXE_PATH="dist/tg-exporter"
ARCHIVE_NAME="${ARCHIVE_NAME:-tg-exporter-linux-x86_64.tar.gz}"
ARCHIVE_PATH="dist/$ARCHIVE_NAME"

if [ ! -f "$EXE_PATH" ]; then
  echo "Ошибка: PyInstaller не создал $EXE_PATH" >&2
  exit 1
fi

rm -f "$ARCHIVE_PATH"
tar -czf "$ARCHIVE_PATH" -C "dist" tg-exporter

echo "Архив готов: $ARCHIVE_PATH"
