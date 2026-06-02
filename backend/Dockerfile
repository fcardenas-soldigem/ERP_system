# syntax=docker/dockerfile:1
FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    POETRY_VIRTUALENVS_CREATE=false

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev curl && \
    rm -rf /var/lib/apt/lists/*

# Copy backend code requirements (cuando el contexto es la raíz)
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt && pip install gunicorn

# Copiamos todo el código del backend
COPY backend/ /app

# Default envs (override in runtime)
ENV DJANGO_SETTINGS_MODULE=config.settings \
    DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1 \
    DJANGO_DEBUG=False

# Collect static (empaqueta a /app/staticfiles con manifest)
RUN python manage.py collectstatic --noinput

# === SECURITY: Run as non-root user ===
# Crear usuario sin privilegios
RUN groupadd -r appuser && useradd -r -g appuser -u 1000 appuser

# Dar permisos al usuario sobre los archivos necesarios
RUN chown -R appuser:appuser /app

# Cambiar a usuario no-root
USER appuser

# Expose app port
EXPOSE 8080

# gthread: 2 workers x 4 threads = 8 slots concurrentes con ~60% menos RAM que 8 workers sync
# --worker-class gthread es requerido para que --threads tenga efecto (sync worker lo ignora)
# --max-requests previene memory leaks en workers de larga vida en Cloud Run
CMD ["gunicorn", "config.wsgi:application", \
     "--bind", "0.0.0.0:8080", \
     "--worker-class", "gthread", \
     "--workers", "2", \
     "--threads", "4", \
     "--timeout", "120", \
     "--max-requests", "1000", \
     "--max-requests-jitter", "50"]
