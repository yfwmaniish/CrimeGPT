FROM python:3.11-slim

# Python runtime hygiene
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# System deps:
#   libpq for psycopg2, build tools for any wheels that need compiling,
#   libreoffice-writer (+ fonts) for headless docx->PDF export (Track C).
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        libreoffice-writer \
        fonts-dejavu \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install the CPU-only build of torch first so the heavy CUDA wheels are never
# pulled in by sentence-transformers.
RUN pip install --upgrade pip \
    && pip install torch==2.5.1 --index-url https://download.pytorch.org/whl/cpu

COPY requirements.txt .
RUN pip install -r requirements.txt

# Bake the embedding model into the image so retrieval is fully local at runtime
# (no download on first request, and tests don't need network).
ENV HF_HOME=/opt/hf-cache
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

COPY . .

EXPOSE 8000

# Default command is overridden in docker-compose (runs migrate + runserver).
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
