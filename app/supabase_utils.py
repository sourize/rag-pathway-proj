import logging
from app.supabase_helper import create_client, get_signed_url
from app.config import SUPABASE_URL, SUPABASE_KEY

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def list_files(bucket_name: str) -> list[str]:
    items = supabase.storage.from_(bucket_name).list()
    return [o.get("name") if isinstance(o, dict) else o for o in items]