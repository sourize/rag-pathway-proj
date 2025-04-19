# Dockerfile
FROM python:3.10-slim

# runtime system libraries
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      libgl1 libglib2.0-0 \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# copy just the trimmed requirements
COPY requirements.txt .

# install them
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

# copy your code
COPY ./app ./app

# expose the port
EXPOSE 8000

# launch uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
