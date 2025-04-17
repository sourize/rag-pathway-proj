import os
import time
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np
import faiss
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from transformers import pipeline
from huggingface_hub import InferenceClient

from app.config import BUCKET_NAME
from app.supabase_utils import list_files
from app.file_processing import download_and_extract

# ———— Logging ————
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# ———— FastAPI setup ————
app = FastAPI()

class QARequest(BaseModel):
    question: str

# ———— Hugging Face QA model ————
qa_model = pipeline("question-answering", model="distilbert-base-uncased-distilled-squad")

# ———— FAISS vector store ————
EMBED_DIM = 384
faiss_index = faiss.IndexFlatL2(EMBED_DIM)    # L2 on normalized vectors = cosine
id_to_meta: dict[int, dict] = {}              # map vector-id -> {"filename": str, "chunk": str}

# ———— Chunking function ————
def chunk_text(text: str, chunk_size: int = 512):
    words = text.split()
    for i in range(0, len(words), chunk_size):
        yield " ".join(words[i : i + chunk_size])

# ———— Embedding via Hugging Face Inference ————
hf_client = InferenceClient(
    "sentence-transformers/all-MiniLM-L6-v2",
    token=os.getenv("HF_API_TOKEN"),
)

def embed_text(text: str) -> np.ndarray:
    """
    Returns a normalized embedding vector of dimension EMBED_DIM.
    Handles token-level outputs by mean-pooling if necessary.
    """
    raw = hf_client.feature_extraction(text)
    # raw may be List[float] or List[List[float]]
    if isinstance(raw, list) and raw and isinstance(raw[0], list):
        # token-level vectors: mean-pool
        vec = np.mean(np.array(raw, dtype="float32"), axis=0)
    else:
        vec = np.array(raw, dtype="float32")

    if vec.ndim != 1 or vec.shape[0] != EMBED_DIM:
        raise ValueError(f"Unexpected embedding shape: {vec.shape}, expected ({EMBED_DIM},)")

    # normalize for cosine similarity
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec /= norm
    return vec

# ———— Real‑time ingest & index ————
lock = threading.Lock()
next_id = 0

def update_and_index():
    global next_id
    files = list_files(BUCKET_NAME)
    if not files:
        logging.warning("No files in bucket.")
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

            logging.info(f"✅ Indexed file: {fn}")

def run_index_loop():
    while True:
        logging.info("🔄 Ingest & index cycle")
        update_and_index()
        time.sleep(60)

# ———— QA endpoint ————
@app.post("/qa")
def qa(req: QARequest):
    question = req.question.strip()
    if not question:
        raise HTTPException(400, "Missing question")

    # Embed & normalize query
    try:
        q_vec = embed_text(question)
    except Exception as e:
        logging.error(f"Failed to embed question: {e}")
        raise HTTPException(500, "Embedding error")

    # Search top‑k
    D, I = faiss_index.search(q_vec.reshape(1, -1), 3)
    contexts = [id_to_meta[idx]["chunk"] for idx in I[0] if idx in id_to_meta]

    if not contexts:
        return {"answer": "No relevant context found."}

    combined_context = "\n".join(contexts)
    try:
        result = qa_model(question=question, context=combined_context)
        answer = result.get("answer", "")
        score = result.get("score", 0.0)
    except Exception as e:
        logging.error(f"QA model error: {e}")
        raise HTTPException(500, "QA model error")

    return {
        "question": question,
        "answer": answer,
        "score": score,
        "context_used": contexts,
    }

# ———— Main ————
if __name__ == "__main__":
    # Start indexing in background
    threading.Thread(target=run_index_loop, daemon=True).start()
    # Launch the API
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
