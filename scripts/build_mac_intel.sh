#!/usr/bin/env bash
# Сборка под Intel (x86_64) macOS.
# На Mac с Apple Silicon (M1/M2) запускает сборку через Rosetta (arch -x86_64).
# Нужен x86_64 Python: например, установите Python с python.org (Intel) или используйте CI.

set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

export TARGET_ARCH="x86_64"
export ARCHIVE_NAME="tg-exporter-mac-x86_64.tar.gz"

echo "Сборка для Intel (x86_64). Архив: $ARCHIVE_NAME"
chmod +x ./scripts/build_mac.sh
./scripts/build_mac.sh
echo "Готово: dist/$ARCHIVE_NAME"
