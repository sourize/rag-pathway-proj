import os
import requests

HF_API_TOKEN = os.getenv("HF_API_TOKEN")
API_URL = "https://api-inference.huggingface.co/pipeline/feature-extraction/sentence-transformers/paraphrase-MiniLM-L3-v2"
HEADERS = {"Authorization": f"Bearer {HF_API_TOKEN}"}

def generate_embedding(text: str):
    if not text.strip():
        return [0.0] * 384
    response = requests.post(API_URL, headers=HEADERS, json={"inputs": text})
    response.raise_for_status()
    return response.json()[0]  # 384-dim vector

def answer_question(query: str, context: str):
    # Optional: you can use another QA-compatible model like deepset/roberta-base-squad2
    api_url = "https://api-inference.huggingface.co/models/deepset/roberta-base-squad2"
    payload = {
        "inputs": {
            "question": query,
            "context": context
        }
    }
    response = requests.post(api_url, headers=HEADERS, json=payload)
    response.raise_for_status()
    return response.json().get("answer", "Sorry, couldn't find an answer.")
