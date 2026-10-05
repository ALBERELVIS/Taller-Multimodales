#!/bin/sh
set -e
cd /app
export PYTHONPATH=/app/src
python scripts/build_demo_case.py
exec python -m streamlit run app/streamlit_app.py --server.address=0.0.0.0 --server.port=8501
