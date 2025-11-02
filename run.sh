#!/usr/bin/env bash
set -euo pipefail

UVICORN_BIN=${UVICORN_BIN:-uvicorn}
HOST=${HOST:-0.0.0.0}
PORT=${PORT:-8000}
APP=${APP:-main:app}

exec "$UVICORN_BIN" "$APP" --host "$HOST" --port "$PORT"
