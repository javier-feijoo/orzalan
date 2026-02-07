#!/usr/bin/env bash
set -euo pipefail

NAME="${1:-orzalan}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi

source .venv/bin/activate
pip install -r requirements.txt

rm -rf build dist

pyinstaller \
  --noconfirm \
  --clean \
  orzalan.spec

mkdir -p "dist/$NAME/assets"
cp -R assets/* "dist/$NAME/assets/"

tar -czf "dist/${NAME}.tar.gz" -C dist "$NAME"

echo "Build listo en dist/$NAME"
echo "Tar listo en dist/${NAME}.tar.gz"
