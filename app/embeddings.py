from transformers import AutoTokenizer, AutoModel
import torch
import logging

class TextEmbedder:
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L3-v2"):
        """Initialize the text embedder with a specific model."""
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModel.from_pretrained(model_name).to(self.device)
        logging.info(f"Initialized TextEmbedder with model: {model_name} on device: {self.device}")

    def get_embedding(self, text: str) -> list[float]:
        """Generate embeddings for the given text."""
        try:
            # Tokenize the text
            inputs = self.tokenizer(text, return_tensors="pt", padding=True, truncation=True, max_length=512)
            inputs = {k: v.to(self.device) for k, v in inputs.items()}

            # Generate embeddings
            with torch.no_grad():
                outputs = self.model(**inputs)
                # Use CLS token embedding (first token)
                embeddings = outputs.last_hidden_state[:, 0, :].cpu().numpy()[0]
                
            return embeddings.tolist()
        except Exception as e:
            logging.error(f"Error generating embeddings: {e}")
            return None

# Initialize a global embedder instance
embedder = TextEmbedder() 