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

# Copy backend code requirements (cuando el contexto es backend/)
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt && pip install gunicorn

# Copiamos todo el código del backend
COPY . /app

# Default envs (override in runtime)
ENV DJANGO_SETTINGS_MODULE=config.settings \
    DJANGO_ALLOWED_HOSTS=* \
    DJANGO_DEBUG=False

# Collect static (empaqueta a /app/staticfiles con manifest)
RUN python manage.py collectstatic --noinput

# Expose app port
EXPOSE 8080

# Start: gunicorn (los estáticos ya fueron colectados en build)
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8080", "--workers", "3", "--timeout", "120"]
