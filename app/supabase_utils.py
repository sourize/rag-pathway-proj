import logging
from app.supabase_helper import create_client, get_signed_url
from app.config import SUPABASE_URL, SUPABASE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def list_files(bucket_name: str) -> list:
    """Lists all files in a Supabase storage bucket."""
    files = supabase.storage.from_(bucket_name).list()
    if not files:
        logging.error("No files found in the bucket.")
        return []
    return [f["name"] for f in files if isinstance(f, dict) and "name" in f and not f["name"].startswith(".")]