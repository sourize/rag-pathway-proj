import os
import time
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np
import faiss
from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from transformers import pipeline
from huggingface_hub import InferenceClient

from app.config import BUCKET_NAME
from app.supabase_utils import list_files, supabase
from app.file_processing import download_and_extract

# ———— Logging ————
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# ———— FastAPI setup ————
app = FastAPI()

app.add_middleware(
  CORSMiddleware,
  allow_origins=["*"],            # for prod lock this down to your domain
  allow_credentials=True,
  allow_methods=["GET","POST"],
  allow_headers=["*"],
)


@app.get("/")
def health() -> dict:
    return {"status": "ok", "message": "Service is up"}

class QARequest(BaseModel):
    question: str

# ———— Hugging Face QA model ————
qa_model = pipeline(
    "question-answering",
    model="distilbert-base-uncased-distilled-squad"
)

# ———— FAISS vector store ————
EMBED_DIM = 384
faiss_index = faiss.IndexFlatL2(EMBED_DIM)
id_to_meta: dict[int, dict] = {}

# ———— Chunking ————
def chunk_text(text: str, chunk_size: int = 512):
    words = text.split()
    for i in range(0, len(words), chunk_size):
        yield " ".join(words[i : i + chunk_size])

# ———— Embedding ————
hf_client = InferenceClient(
    repo_id="sentence-transformers/all-MiniLM-L6-v2",
    token=os.getenv("HF_API_TOKEN"),
)

def embed_text(text: str) -> np.ndarray:
    raw = hf_client.feature_extraction(text)
    # mean-pool if token-level
    if isinstance(raw, list) and raw and isinstance(raw[0], list):
        vec = np.mean(np.array(raw, dtype="float32"), axis=0)
    else:
        vec = np.array(raw, dtype="float32")
    if vec.shape != (EMBED_DIM,):
        raise ValueError(f"Unexpected embedding shape: {vec.shape}")
    norm = np.linalg.norm(vec)
    return vec / norm if norm > 0 else vec

# ———— Indexing loop ————
lock = threading.Lock()
next_id = 0

def update_and_index():
    global next_id
    files = list_files(BUCKET_NAME)
    if not files:
        logging.warning("No files to index.")
        return

    def fetch(fn: str):
        _, content = download_and_extract(fn)
        return fn, content

    with ThreadPoolExecutor(max_workers=4) as ex:
        futures = {ex.submit(fetch, fn): fn for fn in files}
        for future in as_completed(futures):
            fn, content = future.result()
            if not content:
                continue
            for chunk in chunk_text(content):
                try:
                    vec = embed_text(chunk)
                except Exception as e:
                    logging.warning(f"Skipping chunk from {fn}: {e}")
                    continue
                with lock:
                    vid = next_id
                    next_id += 1
                    faiss_index.add(vec.reshape(1, -1))
                    id_to_meta[vid] = {"filename": fn, "chunk": chunk}
            logging.info(f"Indexed {fn}")

@app.on_event("startup")
def start_index():
    # Delay slightly to let other startup tasks complete
    threading.Thread(target=lambda: (time.sleep(2), update_and_index()), daemon=True).start()

# ———— QA endpoint ————
@app.post("/qa")
def qa(req: QARequest):
    q = req.question.strip()
    if not q:
        raise HTTPException(400, "Missing question")

    try:
        q_vec = embed_text(q)
    except Exception:
        raise HTTPException(500, "Embedding error")

    D, I = faiss_index.search(q_vec.reshape(1, -1), 3)
    contexts = [id_to_meta[i]["chunk"] for i in I[0] if i in id_to_meta]
    if not contexts:
        return {"answer": "No relevant context found."}

    ctx = "\n".join(contexts)
    try:
        out = qa_model(question=q, context=ctx)
    except Exception:
        raise HTTPException(500, "QA model error")
    return {"question": q, "answer": out.get("answer", ""), "score": out.get("score", 0.0), "context_used": contexts}

# ———— Upload & Reindex ————
@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        res = supabase.storage.from_(BUCKET_NAME).upload(file.filename, contents)

        # Check if Supabase returned a conflict
        if isinstance(res, dict) and res.get("statusCode") == 409:
            return JSONResponse(
                status_code=200,
                content={"message": f"File {file.filename} already exists."}
            )

        return {"message": f"Uploaded {file.filename}"}

    except Exception as e:
        print("Upload failed:", e)
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@app.post("/reindex")
def reindex(background_tasks: BackgroundTasks):
    background_tasks.add_task(update_and_index)
    return {"message": "Reindex started"}

# ———— Run ————
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)