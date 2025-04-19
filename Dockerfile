# --- builder stage ---
    FROM python:3.10-slim AS builder
    WORKDIR /app
    
    RUN apt-get update && \
        apt-get install -y --no-install-recommends build-essential git && \
        rm -rf /var/lib/apt/lists/*
    
    COPY requirements.txt .
    RUN pip install --no-cache-dir --upgrade pip && \
        pip install --no-cache-dir -r requirements.txt
    
    # --- final stage ---
    FROM python:3.10-slim
    WORKDIR /app
    
    # ✅ Copy BOTH site-packages AND bin
    COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
    COPY --from=builder /usr/local/bin /usr/local/bin
    
    COPY .env .env

    COPY . .
    
    EXPOSE 8000
    CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
    