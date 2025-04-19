# --- builder stage: install deps ---
    FROM python:3.10-slim AS builder
    WORKDIR /app
    
    # install build tools (only for compiling any wheels)
    RUN apt-get update && \
        apt-get install -y --no-install-recommends build-essential git && \
        rm -rf /var/lib/apt/lists/*
    
    COPY requirements.txt .
    RUN pip install --no-cache-dir --upgrade pip && \
        pip install --no-cache-dir -r requirements.txt
    
    # --- final stage: copy just the runtime bits ---
    FROM python:3.10-slim
    WORKDIR /app
    
    # copy only installed libs from builder
    COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
    # copy your code
    COPY . .
    
    # Let Render (and Docker) know the app listens on 8000
    EXPOSE 8000
    
    # Use UVICORN directly to avoid extra memory overhead of reloaders
    CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]