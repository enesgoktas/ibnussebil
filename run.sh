#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
API_DIR="$ROOT/api"
WEB_DIR="$ROOT/web"
PYTHON="${PYTHON:-python3.11}"

if ! command -v "$PYTHON" >/dev/null 2>&1; then
  PYTHON="python3"
fi

if [ ! -d "$API_DIR/.venv" ]; then
  echo "→ Python sanal ortamı kuruluyor..."
  "$PYTHON" -m venv "$API_DIR/.venv"
  "$API_DIR/.venv/bin/pip" install --upgrade pip >/dev/null
  "$API_DIR/.venv/bin/pip" install -r "$API_DIR/requirements.txt"
fi

if [ ! -d "$WEB_DIR/node_modules" ]; then
  echo "→ Web bağımlılıkları kuruluyor..."
  (cd "$WEB_DIR" && npm install)
fi

if [ ! -f "$API_DIR/ibnussebil.db" ]; then
  echo "→ Demo verisi hazırlanıyor..."
  (cd "$API_DIR" && .venv/bin/python -m app.seed_demo)
fi

echo ""
echo "  İbnüssebil başlıyor"
echo "  API: http://127.0.0.1:8000/api/health"
echo "  Web: http://localhost:5173"
echo ""

(cd "$API_DIR" && .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload) &
API_PID=$!
trap 'kill "$API_PID" 2>/dev/null || true' EXIT

(cd "$WEB_DIR" && npm run dev)
