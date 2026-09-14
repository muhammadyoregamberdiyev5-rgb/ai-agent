FROM python:3.11-slim AS base

# --- Tizim paketlari va llama.cpp uchun build vositalari ---
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential cmake git wget curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# --- llama.cpp ni manbadan build qilish (llama-server binary) ---
RUN git clone --depth 1 https://github.com/ggerganov/llama.cpp /opt/llama.cpp \
    && cmake -S /opt/llama.cpp -B /opt/llama.cpp/build \
        -DCMAKE_BUILD_TYPE=Release -DLLAMA_CURL=OFF \
    && cmake --build /opt/llama.cpp/build --target llama-server -j$(nproc) \
    && cp /opt/llama.cpp/build/bin/llama-server /usr/local/bin/llama-server \
    && rm -rf /opt/llama.cpp/build/CMakeFiles

WORKDIR /app

# --- Python bog'liqliklari ---
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --- Ilova kodi va skills kutubxonasi ---
COPY app.py start.sh ./
COPY skills/ ./skills/

RUN chmod +x start.sh && mkdir -p /app/models

ENV PORT=8080
ENV MODEL_PATH=/app/models/model.gguf
ENV CTX_SIZE=8192

EXPOSE 8080

CMD ["./start.sh"]
