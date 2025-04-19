import os
import time
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np
import faiss
import requests
import fitz  # pymupdf
from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from huggingface_hub import InferenceClient

from app.config import BUCKET_NAME
from app.supabase_utils import list_files, supabase

# ———— Logging ————
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# ———— FastAPI setup ————
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET","POST"],
    allow_headers=["*"],
)

class QARequest(BaseModel):
    question: str

# ———— HF Inference Clients ————
HF_TOKEN = os.getenv("HF_API_TOKEN")
embed_client = InferenceClient(model="sentence-transformers/all-MiniLM-L6-v2", token=HF_TOKEN)
qa_client    = InferenceClient(model="distilbert-base-uncased-distilled-squad", token=HF_TOKEN)

# ———— FAISS vector store ————
EMBED_DIM = 384
faiss_index = faiss.IndexFlatL2(EMBED_DIM)
id_to_meta: dict[int, dict] = {}

# ———— Helpers ————

def chunk_text(text: str, chunk_size: int = 512):
    words = text.split()
    for i in range(0, len(words), chunk_size):
        yield " ".join(words[i : i + chunk_size])

def embed_text(text: str) -> np.ndarray:
    raw = embed_client.feature_extraction(text)
    arr = np.array(raw, dtype="float32")
    if arr.ndim == 2:
        arr = arr.mean(axis=0)
    norm = np.linalg.norm(arr)
    return (arr/norm) if norm > 0 else arr

def download_and_extract(name: str):
    # identical to before, using supabase.create_signed_url → requests → pymupdf
    signed = supabase.storage.from_(BUCKET_NAME).create_signed_url(name, 3600)["signedUrl"]
    r = requests.get(signed, timeout=10)
    if r.status_code != 200:
        logging.error(f"download {name} → {r.status_code}")
        return None
    path = f"/tmp/{name}"
    with open(path, "wb") as f:
        f.write(r.content)
    if name.lower().endswith(".txt"):
        txt = open(path, encoding="utf-8").read()
    else:
        doc = fitz.open(path)
        txt = "\n".join(p.get_text() for p in doc)
        doc.close()
    return txt

# ———— Indexing Loop ————
lock = threading.Lock()
next_id = 0

def update_and_index():
    global next_id
    files = list_files(BUCKET_NAME)
    if not files:
        logging.info("No files to index.")
        return

    def fetch(fn):
        return fn, download_and_extract(fn)

    with ThreadPoolExecutor(4) as ex:
        for fn, content in ex.map(fetch, files):
            if not content:
                continue
            for chunk in chunk_text(content):
                try:
                    vec = embed_text(chunk)
                except Exception as e:
                    logging.warning(f"embed {fn} chunk: {e}")
                    continue
                with lock:
                    faiss_index.add(vec.reshape(1,-1))
                    id_to_meta[next_id] = {"filename": fn, "chunk": chunk}
                    next_id += 1
            logging.info(f"Indexed {fn}")

@app.on_event("startup")
def startup_index():
    # give FastAPI a moment then index once
    threading.Thread(target=lambda: (time.sleep(2), update_and_index()), daemon=True).start()

# ———— QA endpoint (remote HF Inference) ————
@app.post("/qa")
def qa(req: QARequest):
    q = req.question.strip()
    if not q:
        raise HTTPException(400, "No question")
    q_vec = embed_text(q)
    D, I = faiss_index.search(q_vec.reshape(1,-1), 3)
    ctxs = [ id_to_meta[i]["chunk"] for i in I[0] if i in id_to_meta ]
    if not ctxs:
        return {"answer":"No context."}
    payload = {"inputs": {"question": q, "context": "\n".join(ctxs)}}
    out = qa_client.request(payload)  # generic request
    return {
      "question": q,
      "answer": out.get("answer",""),
      "score": out.get("score",0.0),
      "context_used": ctxs
    }

# ———— Upload & Reindex ————
@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    b = file.filename.replace(" ", "_")
    data = await file.read()
    res = supabase.storage.from_(BUCKET_NAME).upload(b, data)
    if isinstance(res, dict) and res.get("statusCode") == 409:
        return {"message": f"{b} already exists"}
    return {"message": f"Uploaded {b}"}

@app.post("/reindex")
def reindex(bg: BackgroundTasks):
    bg.add_task(update_and_index)
    return {"message":"reindexing"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, workers=1)
