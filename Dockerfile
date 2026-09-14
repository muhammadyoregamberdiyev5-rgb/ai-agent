# --- 1-BOSQICH: tayyor (prebuilt) llama.cpp server binary'sini olamiz ---
# Manbadan cmake bilan qurish o'rniga, rasmiy ggml-org image'idan llama-server
# binary faylini olib chiqamiz — bu build'ni ancha tezlashtiradi va
# resurs/vaqt tufayli build xato berish ehtimolini kamaytiradi.
FROM ghcr.io/ggml-org/llama.cpp:server AS llama

# --- 2-BOSQICH: Python gateway ---
FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    wget ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY --from=llama /app/llama-server /usr/local/bin/llama-server
RUN chmod +x /usr/local/bin/llama-server

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Hammasi bitta darajada (papkasiz) nusxalanadi: app.py, start.sh,
# skill__*.md fayllar va hokazo.
COPY . .

RUN chmod +x start.sh && mkdir -p /app/models

ENV PORT=8080
ENV MODEL_PATH=/app/models/model.gguf
ENV CTX_SIZE=8192

EXPOSE 8080

CMD ["./start.sh"]
