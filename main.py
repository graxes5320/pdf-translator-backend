from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import fitz
import httpx
import os
import uvicorn
import itertools

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ⚠️ 5 Gmail hesabını buraya yaz (MyMemory'ye kayıtlı olmalı)
EMAILS = [
    "toprakayazsahan@gmail.com",
    "sahanyilmaz285@gmail.com",
    "sahan2646@gmail.com",
    "yilmazsahan235@gmail.com",
    "yilmaxsahan@gmail.com",
]

# Her istek farklı e-posta kullanır (round-robin)
email_cycle = itertools.cycle(EMAILS)

@app.get("/")
def root():
    return {"status": "PDF Çevirmen Backend çalışıyor ✅"}

@app.post("/extract-text")
async def extract_text(file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Sadece PDF dosyası gönderin")
    try:
        contents = await file.read()
        doc = fitz.open(stream=contents, filetype="pdf")
        page_count = doc.page_count
        full_text = ""
        for page in doc:
            full_text += page.get_text() + "\n\n"
        doc.close()
        text = full_text.strip()
        if not text:
            raise HTTPException(status_code=422, detail="PDF'den metin okunamadı.")
        return {"success": True, "text": text, "page_count": page_count}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Hata: {str(e)}")

@app.post("/translate")
async def translate(body: dict):
    text = body.get("text", "")
    target_lang = body.get("target_lang", "tr")
    source_lang = body.get("source_lang", "autodetect")

    if not text:
        raise HTTPException(status_code=400, detail="Metin boş olamaz")

    chunks = split_text(text)
    translated_chunks = []

    async with httpx.AsyncClient(timeout=30) as client:
        for chunk in chunks:
            # Her chunk için sıradaki e-postayı kullan
            email = next(email_cycle)

            response = await client.get(
                "https://api.mymemory.translated.net/get",
                params={
                    "q": chunk,
                    "langpair": f"{source_lang}|{target_lang}",
                    "de": email,
                }
            )
            data = response.json()

            if data.get("responseStatus") == 200:
                translated_chunks.append(data["responseData"]["translatedText"])
            else:
                raise HTTPException(
                    status_code=502,
                    detail=f"Çeviri hatası: {data.get('responseDetails')}"
                )

    return {
        "success": True,
        "translated_text": "\n".join(translated_chunks)
    }

def split_text(text: str, max_length: int = 450) -> list:
    import re
    sentences = re.split(r'(?<=[.!?\n])\s+', text)
    chunks = []
    current = ""
    for sentence in sentences:
        if len(current) + len(sentence) > max_length:
            if current:
                chunks.append(current.strip())
            current = sentence
        else:
            current += " " + sentence
    if current.strip():
        chunks.append(current.strip())
    return chunks if chunks else [text]

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
