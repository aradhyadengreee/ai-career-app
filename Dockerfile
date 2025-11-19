# Dockerfile (example, adapt python version if needed)
FROM python:3.11-slim

# Install system deps for chroma and huggingface models (curl, git, build essentials if needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create app dir
WORKDIR /app

# Copy requirements first for layer caching
COPY requirements.txt /app/requirements.txt

# Install python deps
RUN pip install --upgrade pip setuptools wheel \
 && pip install -r /app/requirements.txt

# Copy application code and data
COPY . /app

# ensure cache + chroma dir exist and have perms
RUN mkdir -p /app/chroma-db /root/.cache/huggingface /root/.cache/torch \
 && chmod -R 755 /app/chroma-db

# Run the preload step at build time to download embeddings & build vector DB
# This will run preload.py (created above) which should import vector_db.py and create a persistent DB in /app/chroma-db
RUN python /app/preload.py

# Expose port (Cloud Run expects 8080)
ENV PORT=8080
EXPOSE 8080

# Start the app with Gunicorn (adjust module name if your app object differs)
CMD ["gunicorn", "app:app", "-b", "0.0.0.0:8080", "--workers", "1", "--threads", "4", "--timeout", "300"]
