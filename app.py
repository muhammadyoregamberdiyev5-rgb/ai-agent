"""
Qwen2.5-3B-Instruct AI Agent — Railway uchun gateway
======================================================
Bu FastAPI ilova quyidagilarni bajaradi:
  1. Orqa fonda ishlayotgan llama.cpp server (Qwen2.5-3B-Instruct GGUF) bilan gaplashadi
  2. Har bir so'rovga o'zbek tilida ravon javob berish uchun tizim ko'rsatmasini qo'shadi
  3. skills/ papkasidagi 300+ SKILL.md fayllarini indekslaydi va foydalanuvchi
     xabariga eng mos keladigan 1-2 ta skill'ni topib, kontekstga qo'shadi
     (xuddi Claude'dagi "Skills" tizimi kabi, lekin soddalashtirilgan)
  4. OpenAI-mos /v1/chat/completions endpoint'ini tashqariga chiqaradi
"""

import os
import re
import json
import time
import glob
import subprocess
import threading
from pathlib import Path
from typing import Optional

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse

# ----------------------------------------------------------------------------
# Sozlamalar
# ----------------------------------------------------------------------------
SKILLS_DIR = Path(__file__).parent / "skills"
LLAMA_HOST = "127.0.0.1"
LLAMA_PORT = 8081
LLAMA_BASE_URL = f"http://{LLAMA_HOST}:{LLAMA_PORT}"
PUBLIC_PORT = int(os.environ.get("PORT", 8080))
MAX_SKILLS_INJECTED = int(os.environ.get("MAX_SKILLS_INJECTED", 2))
MAX_SKILL_CHARS = int(os.environ.get("MAX_SKILL_CHARS", 3500))

UZBEK_SYSTEM_PROMPT = """Sen foydali, bilimdon va samimiy AI agentsan. Quyidagi qoidalarga QATʼIY amal qil:

1. TIL: Har doim o'zbek tilida javob ber (foydalanuvchi boshqa tilda yozmasa). Lotin
   alifbosida yoz, agar foydalanuvchi kirill alifbosida yozsa — shunda kirillda javob ber.
   Grammatik xatolarsiz, tabiiy va ravon o'zbekcha ishlat — so'zma-so'z tarjima qilingandek
   emas, balki jonli, kundalik nutqqa yaqin uslubda yoz.
2. TO'LIQLIK: Javoblaringni qisqartirma yoki to'xtatib qo'yma — savolga to'liq va aniq javob
   ber. Agar vazifa bir necha qadamdan iborat bo'lsa, hammasini ketma-ket bajarib chiq.
3. ANIQLIK: Ishonchsiz bo'lsang, taxmin qilganingni aytib o't. Hech qachon
   noto'g'ri ma'lumotni ishonch bilan aytma.
4. USLUB: Do'stona, lekin professional bo'l. Kerak bo'lganda ro'yxat, kod bloklari yoki
   qadamlar bilan tuzilgan javob ber.
"""


# ----------------------------------------------------------------------------
# Skill indeksi — skills/ ichidagi barcha SKILL.md fayllarini o'qib,
# nomi + tavsifi bo'yicha kalit so'z indeksini quradi
# ----------------------------------------------------------------------------
class SkillIndex:
    def __init__(self, root: Path):
        self.root = root
        self.entries = []  # [{path, name, description, tags, text_lower}]
        self._build()

    def _parse_frontmatter(self, content: str):
        """SKILL.md fayllaridagi --- ... --- YAML frontmatter'dan
        name/description/tags maydonlarini soddalashtirilgan tarzda ajratadi."""
        name, description, tags = "", "", ""
        if content.startswith("---"):
            end = content.find("\n---", 3)
            if end != -1:
                fm = content[3:end]
                m = re.search(r"^name:\s*(.+)$", fm, re.MULTILINE)
                if m:
                    name = m.group(1).strip()
                m = re.search(r"^description:\s*(.+)$", fm, re.MULTILINE)
                if m:
                    description = m.group(1).strip()
                m = re.search(r"^tags:\s*\[(.+)\]$", fm, re.MULTILINE)
                if m:
                    tags = m.group(1).strip()
        if not name:
            # papka nomidan foydalanish
            name = ""
        return name, description, tags

    def _build(self):
        for path in glob.glob(str(self.root / "**" / "SKILL.md"), recursive=True):
            p = Path(path)
            try:
                content = p.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            name, description, tags = self._parse_frontmatter(content)
            if not name:
                name = p.parent.name
            blob = f"{name} {description} {tags}".lower()
            self.entries.append(
                {
                    "path": p,
                    "name": name,
                    "description": description or "",
                    "tags": tags,
                    "search_blob": blob,
                }
            )
        print(f"[skills] {len(self.entries)} ta SKILL.md indekslandi ({self.root})")

    def search(self, query: str, top_k: int = 2, min_score: int = 2):
        """Juda sodda kalit-so'z mos kelish darajasi bo'yicha eng yaqin skill'larni topadi."""
        words = set(re.findall(r"[a-zA-Zʼ'\w]{3,}", query.lower()))
        if not words:
            return []
        scored = []
        for e in self.entries:
            score = sum(1 for w in words if w in e["search_blob"])
            if score >= min_score:
                scored.append((score, e))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [e for _, e in scored[:top_k]]


skill_index: Optional[SkillIndex] = None


def load_skill_context(user_message: str) -> str:
    if skill_index is None:
        return ""
    matches = skill_index.search(user_message, top_k=MAX_SKILLS_INJECTED)
    if not matches:
        return ""
    blocks = []
    for m in matches:
        try:
            text = m["path"].read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        text = text[:MAX_SKILL_CHARS]
        blocks.append(f"### Skill: {m['name']}\n{text}")
    if not blocks:
        return ""
    return (
        "\n\nQuyida joriy so'rovga mos bo'lishi mumkin bo'lgan ichki ko'rsatmalar "
        "(SKILLS) bor. Ulardan foydali qismlarini o'z javobingda qo'llan, lekin "
        "foydalanuvchiga bu \"skill fayli\" ekanini aytib o'tirma:\n\n"
        + "\n\n---\n\n".join(blocks)
    )


# ----------------------------------------------------------------------------
# llama.cpp serverni orqa fonda ishga tushirish
# ----------------------------------------------------------------------------
def start_llama_server():
    model_path = os.environ.get("MODEL_PATH", "/app/models/model.gguf")
    ctx_size = os.environ.get("CTX_SIZE", "8192")
    threads = os.environ.get("LLAMA_THREADS", str(os.cpu_count() or 4))

    cmd = [
        "llama-server",
        "--model", model_path,
        "--host", LLAMA_HOST,
        "--port", str(LLAMA_PORT),
        "--ctx-size", ctx_size,
        "--threads", threads,
        "--chat-template", "chatml",
    ]
    print(f"[llama.cpp] ishga tushirilmoqda: {' '.join(cmd)}")
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

    def _pipe_logs():
        for line in proc.stdout:
            print(f"[llama.cpp] {line.rstrip()}")

    threading.Thread(target=_pipe_logs, daemon=True).start()
    return proc


# ----------------------------------------------------------------------------
# FastAPI ilova
# ----------------------------------------------------------------------------
app = FastAPI(title="Qwen2.5-3B Uzbek AI Agent")
_llama_proc = None


@app.on_event("startup")
def on_startup():
    global skill_index, _llama_proc
    skill_index = SkillIndex(SKILLS_DIR)
    _llama_proc = start_llama_server()


@app.get("/")
def root():
    return {"status": "ok", "model": "qwen2.5-3b-instruct", "skills_loaded": len(skill_index.entries) if skill_index else 0}


@app.get("/health")
async def health():
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(f"{LLAMA_BASE_URL}/health")
            return JSONResponse(status_code=r.status_code, content=r.json())
    except Exception as e:
        return JSONResponse(status_code=503, content={"status": "starting", "detail": str(e)})


@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    body = await request.json()
    messages = body.get("messages", [])

    # oxirgi foydalanuvchi xabarini topamiz -> skill qidirish uchun
    last_user_msg = ""
    for m in reversed(messages):
        if m.get("role") == "user":
            last_user_msg = m.get("content", "")
            break

    skill_context = load_skill_context(last_user_msg)

    has_system = any(m.get("role") == "system" for m in messages)
    system_text = UZBEK_SYSTEM_PROMPT + skill_context

    if has_system:
        for m in messages:
            if m.get("role") == "system":
                m["content"] = system_text + "\n\n" + m.get("content", "")
                break
    else:
        messages = [{"role": "system", "content": system_text}] + messages

    body["messages"] = messages
    body.setdefault("max_tokens", 1024)
    body.setdefault("temperature", 0.7)

    stream = body.get("stream", False)

    async with httpx.AsyncClient(timeout=300) as client:
        if stream:
            async def event_stream():
                async with client.stream(
                    "POST", f"{LLAMA_BASE_URL}/v1/chat/completions", json=body
                ) as r:
                    async for chunk in r.aiter_bytes():
                        yield chunk

            return StreamingResponse(event_stream(), media_type="text/event-stream")
        else:
            r = await client.post(f"{LLAMA_BASE_URL}/v1/chat/completions", json=body)
            return JSONResponse(status_code=r.status_code, content=r.json())


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=PUBLIC_PORT)
