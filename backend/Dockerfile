FROM python:3.11-slim

# Python runtime hygiene
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# System deps:
#   libpq for psycopg2, build tools for any wheels that need compiling,
#   libreoffice is added in a later week for PDF export (kept out for a slim Day 1 image).
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

EXPOSE 8000

# Default command is overridden in docker-compose (runs migrate + runserver).
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
