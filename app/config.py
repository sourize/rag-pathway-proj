import os
from dotenv import load_dotenv

load_dotenv()

BUCKET_NAME = "rag-data" 

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
