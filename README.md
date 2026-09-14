# Qwen2.5-3B O'zbek AI Agent — Railway uchun (papkasiz versiya)

Bu versiya avvalgisidan farqli o'laroq **hech qanday subpapka ishlatmaydi** —
barcha fayllar (shu jumladan 309 ta skill fayli) bitta darajada, repo
tub papkasida turadi. Bu GitHub veb-interfeysida (drag & drop bilan fayl
tashlash) yuklash uchun qulay, chunki brauzer orqali papka tuzilmasini
saqlab yuklash har doim ham ishonchli emas.

## Loyiha tuzilishi (hammasi bitta darajada)

```
.
├── Dockerfile                          # prebuilt llama.cpp image'dan foydalanadi (tez build)
├── app.py                              # FastAPI gateway: Uzbek prompt + skill router
├── start.sh                            # Model yuklab, serverni ko'taradi
├── requirements.txt
├── railway.json
├── skill__academic__academic-historian.md
├── skill__academic__academic-psychologist.md
├── ... (jami 309 ta skill__*.md fayl)
└── README.md
```

Har bir skill fayli `skill__<kategoriya>__<nomi>.md` deb nomlangan
(masalan `skill__academic__academic-historian.md`). `app.py` ishga
tushganda shu papkadagi barcha `skill__*.md` fayllarini o'qib, indeks
quradi va foydalanuvchi xabariga mos kelganini avtomatik topadi.

## Nima o'zgardi (oldingi build xatosidan keyin)

1. **Papkalar olib tashlandi** — GitHub'ga qo'lda (drag & drop) fayl
   tashlaganda papka tuzilmasi buzilib qolishi mumkin edi. Endi hammasi
   flat (bitta darajada) fayllar.
2. **Dockerfile tezlashtirildi** — avvalgi versiyada llama.cpp manbadan
   (`cmake`) qurilardi, bu Railway build mashinasida vaqt/xotira
   yetishmasligi sababli qulashi mumkin edi. Endi tayyor
   `ghcr.io/ggml-org/llama.cpp:server` image'idan faqat kerakli binary
   fayl (`llama-server`) olinadi — build bir necha soniyada tugaydi.

## GitHub'ga yuklash

1. Zip'ni ochib, ichidagi barcha fayllarni (hammasi bitta darajada,
   papkasiz) yangi bo'sh GitHub repo'sining asosiy sahifasiga
   **drag & drop** qiling — endi hech qanday papka yo'q, shuning uchun
   muammo bo'lmasligi kerak.
2. Yoki terminal orqali:

```bash
cd qwen-agent-railway-flat
git init
git add .
git commit -m "Qwen2.5-3B Uzbek AI agent - flat, Railway uchun"
git branch -M main
git remote add origin https://github.com/USERNAME/REPO-NOMI.git
git push -u origin main
```

> Model fayli (`.gguf`) `.gitignore` orqali repo'ga qo'shilmaydi — u
> konteyner ishga tushganda avtomatik yuklab olinadi.

## Railway'da deploy qilish

1. [railway.app](https://railway.app) → **New Project** →
   **Deploy from GitHub repo** → repo'ni tanlang.
2. Railway `Dockerfile`ni avtomatik topib, tez build qiladi (endi
   og'ir `cmake` bosqichi yo'q).
3. **Variables** (ixtiyoriy):

   | O'zgaruvchi | Standart qiymat | Izoh |
   |---|---|---|
   | `MODEL_URL` | Qwen2.5-3B-Instruct Q4_K_M | Boshqa GGUF model havolasi |
   | `CTX_SIZE` | `8192` | Kontekst oynasi hajmi |
   | `MAX_SKILLS_INJECTED` | `2` | Har so'rovga nechta skill qo'shilishi |

4. **Settings → Networking → Generate Domain**.
5. Birinchi ishga tushishda model (~1.9GB) yuklanadi — 2-5 daqiqa kutish
   normal, shu payt `/health` "starting" holatini qaytaradi.

### Tavsiya: Volume qo'shish

`Settings → Volumes → New Volume`, Mount path: `/app/models` — shunda
model har deploy'da qayta yuklanmaydi.

## Sinab ko'rish

```bash
curl https://SIZNING-DOMAIN.up.railway.app/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "Salom! O'\''zing haqingda gapirib ber."}]}'
```

## Agar build yana xato bersa

**View logs** tugmasini bosib, aniq xato matnini yuboring — masalan:
- `wget: unable to resolve host` → Railway build muhitida tarmoq
  cheklovi bo'lishi mumkin (model runtime'da yuklanadi, bu build emas,
  deploy bosqichida bo'ladi, shuning uchun bu odatda muammo emas).
- `permission denied: ./start.sh` → repo'ga yuklaganda faylning ijro
  etish huquqi (`chmod +x`) yo'qolgan bo'lishi mumkin; Dockerfile
  ichida `RUN chmod +x start.sh` bor, shuning uchun bu avtomatik
  tuzatiladi.
- Boshqa xato bo'lsa — logdagi qizil matnni menga tashlang, birga
  ko'ramiz.
