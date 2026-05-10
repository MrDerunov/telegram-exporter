#!/usr/bin/env bash
# Обновляет версию в pyproject.toml (для ручного minor/major bump).
# Автоинкремент patch делает CI при ручном запуске экшна.
#
# Использование:
#   ./scripts/bump_version.sh 1.1.0
#   git add pyproject.toml && git commit -m "bump: v1.1.0" && git push
#
# Затем: Actions → Build release artifacts → Run workflow

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

VERSION="${1:-}"
if [ -z "$VERSION" ]; then
  echo "Использование: $0 <версия>" >&2
  echo "Пример: $0 1.1.0" >&2
  exit 1
fi

if ! echo "$VERSION" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9.]+)?$'; then
  echo "Ошибка: версия '$VERSION' не соответствует формату X.Y.Z" >&2
  exit 1
fi

sed -i "s/^version = \".*\"/version = \"$VERSION\"/" pyproject.toml
echo "✓ pyproject.toml → $VERSION"
echo ""
echo "Дальше:"
echo "  git add pyproject.toml && git commit -m \"bump: v$VERSION\" && git push"
echo "  Затем Actions → Build release artifacts → Run workflow"
