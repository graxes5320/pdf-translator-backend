from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import fitz  # PyMuPDF
import uvicorn

app = FastAPI()

# Mobil uygulamadan gelen isteklere izin ver
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"status": "PDF Çevirmen Backend çalışıyor ✅"}

@app.post("/extract-text")
async def extract_text(file: UploadFile = File(...)):
    # Sadece PDF kabul et
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Sadece PDF dosyası gönderin")

    try:
        contents = await file.read()
        doc = fitz.open(stream=contents, filetype="pdf")

        full_text = ""
        for page in doc:
            full_text += page.get_text() + "\n\n"

        doc.close()

        text = full_text.strip()
        if not text:
            raise HTTPException(
                status_code=422,
                detail="PDF'den metin okunamadı. Taranmış veya resim tabanlı olabilir."
            )

        return {
            "success": True,
            "text": text,
            "page_count": doc.page_count if not doc.is_closed else len(full_text.split("\n\n"))
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Hata: {str(e)}")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
