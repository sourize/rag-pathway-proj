# RAG (Retrieval-Augmented Generation) System

A real-time document processing system that reads files from Supabase storage, processes them, and generates embeddings using Hugging Face models.

## Features

- Real-time file monitoring from Supabase storage
- PDF and TXT file processing
- Text embedding generation using Hugging Face models
- Docker containerization
- Pathway for real-time data processing

## Prerequisites

- Python 3.10+
- Docker
- Supabase account and credentials
- Hugging Face account (optional)

## Environment Variables

Create a `.env` file with the following variables:

```env
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
```

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/rag.git
cd rag
```

2. Build and run with Docker:
```bash
docker-compose up --build
```

## Project Structure

```
rag/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── supabase_utils.py
│   ├── file_processing.py
│   └── embeddings.py
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

## Usage

The system will automatically:
1. Monitor the Supabase bucket for new files
2. Process PDF and TXT files
3. Generate embeddings using the configured Hugging Face model
4. Display processed data in real-time

## License

MIT License 