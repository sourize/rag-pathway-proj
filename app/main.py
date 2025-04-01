import time
import logging
import pathway as pw
from concurrent.futures import ThreadPoolExecutor, as_completed
from app.supabase_utils import list_files
from app.file_processing import download_and_extract
from app.config import BUCKET_NAME
from app.embeddings import generate_embedding

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class FileSchema(pw.Schema):
    filename: str
    content: str
    embedding: list

def update_file_data() -> list[tuple[str, str, list]]:

    file_list = list_files(BUCKET_NAME)
    if not file_list:
        logging.error("No files found in the bucket.")
        return []

    all_data = []
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(download_and_extract, file_name): file_name for file_name in file_list}
        
        for future in as_completed(futures):
            file_name = futures[future]
            try:
                content = future.result()[1]
                if content:
                    embedding = generate_embedding(content)
                    all_data.append((file_name, content, embedding))
            except Exception as e:
                logging.error(f"Error processing {file_name}: {e}")
    
    return all_data

# Real-time update loop
while True:
    loop_start = time.time()
    logging.info("=== Starting a new update cycle ===")
    
    data_rows = update_file_data()
    if data_rows:
        table = pw.debug.table_from_rows(FileSchema, data_rows)
        table.debug("RealTimeFiles")
        
        print("\nProcessed Data:")
        for fname, content, embedding in data_rows:
            print(f"\nFile: {fname}\n{'-'*40}\nContent:\n{content}\n{'-'*40}\nEmbedding:\n{embedding}\n{'-'*40}")
            
    else:
        logging.info("No file data to display.")
    
    elapsed = time.time() - loop_start
    logging.info("Cycle completed in %.2f seconds. Sleeping for 60 seconds...\n", elapsed)
    time.sleep(60)
