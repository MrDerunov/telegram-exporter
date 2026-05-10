#!/usr/bin/env bash
# macOS build: PyInstaller --onefile --console → tar.gz.
# Консольное приложение tg-exporter (Click CLI), entry point: tg_exporter_cli/main.py.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# Архитектура сборки. Если переменная не задана — берём архитектуру хоста,
# чтобы не пытаться собрать x86_64-бинарь на Apple Silicon раннере.
if [ -z "${TARGET_ARCH:-}" ]; then
  HOST_ARCH="$(uname -m)"
  case "$HOST_ARCH" in
    arm64|aarch64) export TARGET_ARCH="arm64" ;;
    *)             export TARGET_ARCH="x86_64" ;;
  esac
fi
echo "Building for TARGET_ARCH=$TARGET_ARCH"

# Если собираемся в x86_64 на Apple Silicon — нужно самопереподнять скрипт
# через Rosetta (/usr/bin/arch -x86_64), иначе universal2-Python будет
# выполняться как arm64 и pyinstaller соберёт arm64-бинарь.
HOST_ARCH="$(uname -m)"
if [ "$TARGET_ARCH" = "x86_64" ] && [ "$HOST_ARCH" = "arm64" ] && [ "${_BUILD_REEXEC:-0}" != "1" ]; then
  if [ ! -x /usr/bin/arch ]; then
    echo "Ошибка: нет /usr/bin/arch для перезапуска под Rosetta" >&2
    exit 1
  fi
  echo "Перезапуск под Rosetta (arch -x86_64)..."
  _BUILD_REEXEC=1 exec /usr/bin/arch -x86_64 /bin/bash "$0" "$@"
fi

# Установка PyInstaller (CI ставит deps, этот шаг — подстраховка)
pip install pyinstaller &>/dev/null || { echo "Ошибка: не удалось установить pyinstaller" >&2; exit 1; }

pyinstaller --onefile --console --name tg-exporter \
  --target-arch "$TARGET_ARCH" \
  --exclude-module customtkinter \
  --exclude-module app_legacy \
  --exclude-module app \
  --collect-all telethon \
  --collect-all faster_whisper \
  --collect-all ctranslate2 \
  --collect-all tokenizers \
  --collect-all imageio_ffmpeg \
  --collect-all tg_exporter \
  --hidden-import keyring.backends \
  --hidden-import tg_exporter.services.transcription.factory \
  tg_exporter_cli/main.py

EXE_PATH="dist/tg-exporter"
ARCHIVE_NAME="${ARCHIVE_NAME:-tg-exporter-mac-$TARGET_ARCH.tar.gz}"
ARCHIVE_PATH="dist/$ARCHIVE_NAME"

if [ ! -f "$EXE_PATH" ]; then
  echo "Ошибка: PyInstaller не создал $EXE_PATH" >&2
  exit 1
fi

rm -f "$ARCHIVE_PATH"
tar -czf "$ARCHIVE_PATH" -C "dist" tg-exporter

echo "Архив готов: $ARCHIVE_PATH"
