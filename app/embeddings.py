from sentence_transformers import SentenceTransformer

#model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2") #larger model

model = SentenceTransformer("sentence-transformers/paraphrase-MiniLM-L3-v2")  # smaller-lighter model


def generate_embedding(text: str) -> list:
    return model.encode(text).tolist()