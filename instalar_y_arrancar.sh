#!/usr/bin/env bash
# Instalación y arranque para macOS/Linux (en Windows usamos INSTALAR_Y_ARRANCAR.bat).
set -euo pipefail
cd "$(dirname "$0")"
export UV_CACHE_DIR="$PWD/.tools/uv-cache" UV_PYTHON_INSTALL_DIR="$PWD/.tools/python"
if [ ! -x .tools/uv/uv ]; then
  curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR="$PWD/.tools/uv" UV_NO_MODIFY_PATH=1 sh
fi
.tools/uv/uv sync --frozen --python 3.12
.venv/bin/python scripts/check_system.py
LIGHT=""; command -v nvidia-smi >/dev/null || LIGHT="--light"
.venv/bin/python scripts/download_models.py $LIGHT
.venv/bin/python scripts/build_index.py
[ -f models/.complete ] && export DD_OFFLINE=1
.venv/bin/python -m app.main
