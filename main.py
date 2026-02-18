from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import fitz
import httpx
import os
import uvicorn

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Railway'de environment variable olarak ekleyeceğiz
DEEPL_API_KEY = os.environ.get("DEEPL_API_KEY", "")

# DeepL Free API endpoint (key sonu :fx ise free demek)
DEEPL_URL = "https://api-free.deepl.com/v2/translate"

# DeepL dil kodları (bazıları MyMemory'den farklı)
LANG_MAP = {
    "tr": "TR",
    "en": "EN-US",
    "de": "DE",
    "fr": "FR",
    "es": "ES",
    "it": "IT",
    "pt": "PT-PT",
    "ru": "RU",
    "ar": "AR",
    "zh": "ZH",
    "ja": "JA",
    "ko": "KO",
    "nl": "NL",
    "pl": "PL",
    "sv": "SV",
}

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

    if not text:
        raise HTTPException(status_code=400, detail="Metin boş olamaz")

    if not DEEPL_API_KEY:
        raise HTTPException(status_code=500, detail="DEEPL_API_KEY tanımlı değil")

    # DeepL dil koduna çevir
    deepl_target = LANG_MAP.get(target_lang, target_lang.upper())

    # DeepL tek istekte büyük metin kabul eder (max 128KB)
    # Yine de güvenlik için 3000 karakterlik parçalara bölelim
    chunks = split_text(text, max_length=3000)
    translated_chunks = []

    async with httpx.AsyncClient(timeout=60) as client:
        for chunk in chunks:
            response = await client.post(
                DEEPL_URL,
                headers={
                    "Authorization": f"DeepL-Auth-Key {DEEPL_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "text": [chunk],
                    "target_lang": deepl_target,
                    "source_lang": None,  # otomatik algıla
                }
            )

            if response.status_code == 456:
                raise HTTPException(status_code=429, detail="DeepL aylık karakter limiti doldu")
            elif response.status_code == 403:
                raise HTTPException(status_code=403, detail="DeepL API key geçersiz")
            elif response.status_code != 200:
                raise HTTPException(status_code=502, detail=f"DeepL hatası: {response.text}")

            data = response.json()
            translated_chunks.append(data["translations"][0]["text"])

    return {
        "success": True,
        "translated_text": "\n".join(translated_chunks)
    }

def split_text(text: str, max_length: int = 3000) -> list:
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
