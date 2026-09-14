# Qwen2.5-3B O'zbek AI Agent — Railway uchun

Bu loyiha **Qwen2.5-3B-Instruct** modelini (LM Studio'da ishlatgan model bilan bir xil)
Railway'da server sifatida ishga tushiradi. Model **llama.cpp** orqali ishlaydi,
uning ustida esa o'zbek tilida ravon gaplashadigan va 300+ ta ichki "skill"
(ko'rsatma) faylidan kerakli bo'lganini avtomatik topib ishlatadigan
FastAPI gateway (`app.py`) turadi.

## Loyiha tuzilishi

```
.
├── Dockerfile          # llama.cpp + Python gateway'ni build qiladi
├── app.py              # FastAPI gateway: Uzbek prompt + skill router + OpenAI-mos API
├── start.sh            # Konteyner ishga tushganda modelni yuklab, serverni ko'taradi
├── requirements.txt    # Python bog'liqliklari
├── railway.json        # Railway deploy sozlamalari
└── skills/             # 300+ SKILL.md fayllari (kerak bo'lganda avtomatik ishlatiladi)
```

## Qanday ishlaydi

1. Konteyner ishga tushganda `start.sh` Hugging Face'dan
   `qwen2.5-3b-instruct-q4_k_m.gguf` faylini yuklab oladi (agar u allaqachon
   mavjud bo'lmasa).
2. `llama-server` (llama.cpp) fon rejimida 8081-portda ishga tushadi.
3. FastAPI gateway (`app.py`) tashqi portda (Railway avtomatik beradigan `$PORT`)
   ishlaydi va har bir so'rovga:
   - o'zbek tilida ravon va to'liq javob berish haqidagi tizim ko'rsatmasini,
   - foydalanuvchi xabariga mos keladigan 1–2 ta `SKILL.md` faylining
     kontekstini
   qo'shib, so'ngra llama.cpp serverga yuboradi.
4. Natija OpenAI bilan mos `/v1/chat/completions` formatida qaytadi — ya'ni
   uni istalgan OpenAI-mos client (LM Studio, LangChain, oddiy `curl`,
   Telegram bot va h.k.) bilan ishlatsa bo'ladi.

## GitHub'ga yuklash

1. Bu papkani (zip'dan chiqargan holda) kompyuteringizga saqlang.
2. GitHub'da yangi **bo'sh** repository yarating (README/gitignore qo'shmasdan).
3. Terminalda:

```bash
cd qwen-agent-railway
git init
git add .
git commit -m "Qwen2.5-3B Uzbek AI agent - Railway uchun"
git branch -M main
git remote add origin https://github.com/USERNAME/REPO-NOMI.git
git push -u origin main
```

> **Eslatma:** `skills/` papkasi ~15MB, model fayli esa (`.gguf`) `.gitignore`
> orqali repo'ga qo'shilmaydi — u Railway konteyner ishga tushganda avtomatik
> yuklab olinadi, shuning uchun repo yengil qoladi.

## Railway'da deploy qilish

1. [railway.app](https://railway.app) ga kiring → **New Project** →
   **Deploy from GitHub repo** → yuqorida yaratgan repo'ni tanlang.
2. Railway `Dockerfile`ni avtomatik topadi va build qiladi.
3. **Variables** bo'limida (ixtiyoriy, standart qiymatlar allaqachon ishlaydi):
   | O'zgaruvchi | Standart qiymat | Izoh |
   |---|---|---|
   | `MODEL_URL` | Qwen2.5-3B-Instruct Q4_K_M | Boshqa GGUF model havolasi bilan almashtirsa bo'ladi |
   | `CTX_SIZE` | `8192` | Kontekst oynasi hajmi (token) |
   | `MAX_SKILLS_INJECTED` | `2` | Har bir so'rovga nechta skill qo'shilishi |
4. **Settings → Networking** bo'limida **Generate Domain** tugmasini bosing.
5. Birinchi ishga tushishda model yuklanishi 2–5 daqiqa vaqt olishi mumkin
   (~2GB) — bu vaqtda `/health` endpoint "starting" holatini qaytaradi.

### Diskni saqlab qolish (tavsiya etiladi)

Railway'da **Volume** qo'shib, uni `/app/models` papkasiga ulasangiz, model
har deploy'da qayta yuklanmaydi:
`Settings → Volumes → New Volume` → Mount path: `/app/models`.

## Sinab ko'rish

Deploy tugagach:

```bash
curl https://SIZNING-DOMAIN.up.railway.app/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "Salom! O'\''zing haqingda qisqacha gapirib ber."}
    ]
  }'
```

Streaming (token-by-token) javob kerak bo'lsa, so'rovga `"stream": true`
qo'shing.

## Skill tizimi qanday ishlaydi

`skills/` papkasidagi har bir `SKILL.md` fayli quyidagi formatga ega:

```
---
name: skill-nomi
description: Bu skill nima uchun va qachon ishlatilishi
tags: [teg1, teg2]
---
... ko'rsatma matni ...
```

Foydalanuvchi xabari kelganda, gateway shu fayllarning `name`/`description`/
`tags` maydonlaridan sodda kalit-so'z moslashtirish orqali eng mos 1–2 tasini
tanlaydi va ularning matnini modelga yashirin kontekst sifatida beradi.
Bu — to'liq semantik qidiruv emas, balki tezkor va bepul ishlaydigan oddiy
usul. Agar aniqroq (embedding-asosidagi) qidiruv kerak bo'lsa, buni keyinroq
`sentence-transformers` bilan kengaytirish mumkin — shunda ayting, shuni ham
qo'shib beraman.

## Boshqa modelga almashtirish

`MODEL_URL` environment variable'ini istalgan boshqa GGUF fayl havolasiga
o'zgartiring (masalan, `qwen2.5-coder-3b-instruct`). Model formati GGUF va
chat-template mos bo'lsa, hech narsani o'zgartirish shart emas.

## Cheklovlar

- Railway'ning bepul/standart tarifida GPU yo'q — model CPU'da ishlaydi.
  3B model uchun bu odatda yetarli tezlikda ishlaydi, lekin katta (7B+)
  modellar uchun javob sekinroq bo'lishi mumkin.
- Bepul tarifda RAM cheklangan bo'lishi mumkin — agar konteyner xotira
  yetishmasligi tufayli qulasa, `CTX_SIZE`ni kamaytiring (masalan, `4096`)
  yoki rejangizni yangilang.
