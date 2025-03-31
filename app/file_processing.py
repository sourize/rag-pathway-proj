import os
import requests
import fitz  
import hashlib
import logging
from app.supabase_utils import get_signed_url

# Cache for file content
cache = {}

def compute_hash(file_path: str) -> str:
    """Compute MD5 hash of a file to check for changes."""
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def download_and_extract(file_name: str) -> tuple[str, str]:
    """
    Downloads a file from Supabase and extracts text (TXT/PDF).
    Uses caching to avoid redundant processing.
    """
    file_url = get_signed_url(file_name)
    if not file_url:
        logging.error(f"[{file_name}] Failed to retrieve URL.")
        return (file_name, None)

    folder_path = "/app/files"
    os.makedirs(folder_path, exist_ok=True)
    local_file = os.path.join(folder_path, file_name)

    response = requests.get(file_url)
    if response.status_code == 200:
        with open(local_file, "wb") as f:
            f.write(response.content)
        logging.info(f"[{file_name}] Downloaded.")
    else:
        logging.error(f"[{file_name}] Failed to download: {response.status_code}")
        return (file_name, None)

    file_hash = compute_hash(local_file)
    if file_name in cache and cache[file_name][0] == file_hash:
        logging.info(f"[{file_name}] Using cached content.")
        return (file_name, cache[file_name][1])

    # Extract content
    content = extract_text(local_file, file_name)
    if content:
        cache[file_name] = (file_hash, content)
    return (file_name, content)

def extract_text(file_path: str, file_name: str) -> str:
    """Extracts text from .txt or .pdf files."""
    if file_name.endswith(".txt"):
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read().strip()
    elif file_name.endswith(".pdf"):
        try:
            doc = fitz.open(file_path)
            return "\n".join([page.get_text() for page in doc])
        except Exception as e:
            logging.error(f"[{file_name}] Error processing PDF: {e}")
    return None
