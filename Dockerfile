# Use Python base image
FROM python:3.10

# Set working directory inside container
WORKDIR /app

# Copy requirements first (for caching)
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy all project files (including config.py)
COPY . .

# Run the application
CMD ["python", "app/main.py"]
