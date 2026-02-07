#!/usr/bin/env bash
set -euo pipefail

NAME="${1:-orzalan}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

pyinstaller \
  --noconfirm \
  --clean \
  --name "$NAME" \
  --windowed \
  --onedir \
  --specpath . \
  --distpath dist \
  --workpath build \
  orzalan.spec

mkdir -p "dist/$NAME/assets"
cp -R assets/* "dist/$NAME/assets/"

echo "Build listo en dist/$NAME"
