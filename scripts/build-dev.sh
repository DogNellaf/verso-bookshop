#!/usr/bin/env bash
# Bootstraps and runs the bookshop project (Django REST backend + Vue frontend)
# in development mode on Linux/macOS.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
VENV_DIR="$BACKEND_DIR/.venv"

echo "==> Setting up backend"
if [ ! -x "$VENV_DIR/bin/python" ]; then
  python3 -m venv "$VENV_DIR"
fi
source "$VENV_DIR/bin/activate"
pip install -q --upgrade pip
pip install -q -r "$BACKEND_DIR/requirements.txt"
python "$BACKEND_DIR/manage.py" migrate

echo "==> Installing frontend dependencies"
if command -v pnpm >/dev/null 2>&1; then
  (cd "$FRONTEND_DIR" && pnpm install)
else
  (cd "$FRONTEND_DIR" && npm install)
fi

cleanup() {
  echo "==> Shutting down"
  kill "${BACKEND_PID:-}" "${FRONTEND_PID:-}" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "==> Starting backend (http://127.0.0.1:8000)"
python "$BACKEND_DIR/manage.py" runserver 127.0.0.1:8000 &
BACKEND_PID=$!

echo "==> Starting frontend (http://127.0.0.1:5173)"
if command -v pnpm >/dev/null 2>&1; then
  (cd "$FRONTEND_DIR" && pnpm run dev) &
else
  (cd "$FRONTEND_DIR" && npm run dev) &
fi
FRONTEND_PID=$!

wait "$BACKEND_PID" "$FRONTEND_PID"
