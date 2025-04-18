import os
import logging
import requests
import fitz  # PyMuPDF
from app.supabase_utils import supabase

CACHE_DIR = "/app/files"
os.makedirs(CACHE_DIR, exist_ok=True)


def download_and_extract(filename: str) -> tuple[str, str]:
    url = supabase.storage.from_("rag-data").create_signed_url(filename, 3600)["signedUrl"]
    local = os.path.join(CACHE_DIR, filename)
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        with open(local, "wb") as f:
            f.write(r.content)
    except Exception as e:
        logging.error(f"Download {filename}: {e}")
        return filename, None

    try:
        if filename.lower().endswith(".txt"):
            txt = open(local, "r", encoding="utf-8").read()
        else:
            doc = fitz.open(local)
            txt = "\n".join([p.get_text() for p in doc])
            doc.close()
        return filename, txt.strip()
    except Exception as e:
        logging.error(f"Extract {filename}: {e}")
        return filename, None