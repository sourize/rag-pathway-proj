from supabase import create_client
from app.config import SUPABASE_URL, SUPABASE_KEY

# Initialize Supabase Client
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def upload_file(file_path, storage_bucket="rag-data"):
    with open(file_path, "rb") as file:
        response = supabase.storage.from_(storage_bucket).upload(file_path, file)
        print("File uploaded:", response)

def get_signed_url(file_name, storage_bucket="rag-data"):
    response = supabase.storage.from_(storage_bucket).create_signed_url(file_name, expires_in=3600)
    return response.get("signedURL")

