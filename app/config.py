import os
from dotenv import load_dotenv

load_dotenv()

BUCKET_NAME = "rag-data" 

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
BUCKET_NAME    = os.getenv("SUPABASE_BUCKET", "rag-data")
SUPABASE_URL   = os.getenv("SUPABASE_URL")
SUPABASE_KEY   = os.getenv("SUPABASE_KEY")
SUPABASE_DB    = os.getenv("SUPABASE_DB")
SUPABASE_USER  = os.getenv("SUPABASE_USER")
SUPABASE_PASS  = os.getenv("SUPABASE_PASSWORD")
SUPABASE_HOST  = os.getenv("SUPABASE_HOST")
SUPABASE_PORT  = int(os.getenv("SUPABASE_PORT", 5432))