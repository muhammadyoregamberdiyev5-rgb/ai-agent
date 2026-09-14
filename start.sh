#!/usr/bin/env bash
set -euo pipefail

MODEL_PATH="${MODEL_PATH:-/app/models/model.gguf}"
MODEL_URL="${MODEL_URL:-https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF/resolve/main/qwen2.5-3b-instruct-q4_k_m.gguf}"

mkdir -p "$(dirname "$MODEL_PATH")"

if [ ! -f "$MODEL_PATH" ]; then
  echo "[start.sh] Model topilmadi, yuklab olinmoqda: $MODEL_URL"
  wget -q --show-progress -O "$MODEL_PATH.part" "$MODEL_URL"
  mv "$MODEL_PATH.part" "$MODEL_PATH"
  echo "[start.sh] Model yuklandi: $MODEL_PATH"
else
  echo "[start.sh] Model allaqachon mavjud: $MODEL_PATH"
fi

echo "[start.sh] FastAPI gateway ishga tushirilmoqda (port: ${PORT:-8080})..."
exec python3 -m uvicorn app:app --host 0.0.0.0 --port "${PORT:-8080}"
