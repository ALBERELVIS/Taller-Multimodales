#!/bin/sh
set -e
ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
cd "$ROOT"
if [ ! -x .venv/bin/python ]; then
  python3 -m venv .venv
fi
if [ "$1" != "--skip-install" ]; then
  .venv/bin/python -m pip install --upgrade pip
  .venv/bin/python -m pip install -r requirements.txt
fi
export PYTHONPATH="$ROOT/src"
.venv/bin/python -m helios.doctor
.venv/bin/python scripts/build_demo_case.py
if [ "$1" != "--skip-models" ]; then
  .venv/bin/python scripts/pull_models.py
fi
exec .venv/bin/python -m streamlit run app/streamlit_app.py
