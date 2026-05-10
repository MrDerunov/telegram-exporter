#!/usr/bin/env bash
# Обновляет версию в pyproject.toml и создаёт git-тег.
# Использование: ./scripts/bump_version.sh 1.2.3
#
# После выполнения — пуш тега запустит CI-сборку:
#   git push origin v1.2.3

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

VERSION="${1:-}"
if [ -z "$VERSION" ]; then
  echo "Использование: $0 <версия>" >&2
  echo "Пример: $0 1.2.3" >&2
  exit 1
fi

# Проверка формата (X.Y.Z или X.Y.Z-rcN)
if ! echo "$VERSION" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9.]+)?$'; then
  echo "Ошибка: версия '$VERSION' не соответствует формату X.Y.Z" >&2
  exit 1
fi

# 1. pyproject.toml
if ! grep -q '^version = ' pyproject.toml; then
  echo "Ошибка: не найден version в pyproject.toml" >&2
  exit 1
fi
sed -i "s/^version = \".*\"/version = \"$VERSION\"/" pyproject.toml
echo "✓ pyproject.toml → $VERSION"

# 2. Генерация _version.py (используется при сборке PyInstaller)
echo "VERSION = \"$VERSION\"" > tg_exporter_cli/_version.py
echo "✓ tg_exporter_cli/_version.py → $VERSION"

# 3. Git
git add pyproject.toml
git add -f tg_exporter_cli/_version.py
git commit -m "release: v$VERSION" || { echo "Нет изменений для коммита" >&2; exit 1; }

TAG="v$VERSION"
if git rev-parse "$TAG" >/dev/null 2>&1; then
  echo "Тег $TAG уже существует, удаляю локально..."
  git tag -d "$TAG"
fi
git tag -a "$TAG" -m "v$VERSION"
echo "✓ git tag $TAG создан"

echo ""
echo "Готово. Следующий шаг — пуш тега в origin:"
echo "  git push origin main && git push origin $TAG"
