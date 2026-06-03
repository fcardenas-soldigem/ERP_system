# syntax=docker/dockerfile:1
# ═══════════════════════════════════════════════════════════════════════════════
# Stage 1: builder
# Instala y compila todas las dependencias Python.
# build-essential + libpq-dev son necesarios para compilar psycopg2 y otros
# paquetes con extensiones C, pero NO se necesitan en runtime.
# Al mantenerlos solo en este stage, la imagen final queda ~600MB más liviana.
# ═══════════════════════════════════════════════════════════════════════════════
FROM python:3.11-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Instalar dependencias en /install (directorio aislado).
# COPY solo el requirements.txt primero → Docker reutiliza este layer
# mientras requirements.txt no cambie, incluso si el código sí cambia.
COPY backend/requirements.txt /tmp/requirements.txt
RUN pip install --prefix=/install --no-cache-dir -r /tmp/requirements.txt \
    && pip install --prefix=/install --no-cache-dir gunicorn


# ═══════════════════════════════════════════════════════════════════════════════
# Stage 2: final
# Imagen de producción: solo lo estrictamente necesario para ejecutar Django.
# No contiene gcc, make, headers de compilación ni código fuente de pip.
# Resultado esperado: ~200MB vs ~800MB de una imagen single-stage.
# ═══════════════════════════════════════════════════════════════════════════════
FROM python:3.11-slim AS final

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Runtime deps únicamente:
# - libpq5: cliente PostgreSQL en runtime (psycopg2-binary lo bundlea, pero
#   lo incluimos como buena práctica para futuros cambios a psycopg2 no-binary)
# - curl: necesario para el HEALTHCHECK de Cloud Run
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq5 \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Copiar packages Python compilados desde el stage builder.
# /install fue creado con --prefix=/install, que mapea a la estructura
# estándar de /usr/local (lib/python3.11/site-packages, bin/, etc.)
COPY --from=builder /install /usr/local

# Copiar código del backend.
# Este COPY va DESPUÉS del COPY de dependencias para maximizar cache hits:
# cambios en el código no invalidan el layer de dependencias.
COPY backend/ /app

# Variables de entorno para build-time (requeridas por collectstatic).
# Los valores de producción reales se inyectan en Cloud Run como secrets/env vars.
ENV DJANGO_SETTINGS_MODULE=config.settings \
    DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1 \
    DJANGO_DEBUG=False

# Valores dummy para satisfacer el raise ValueError de settings.py durante el build.
# NUNCA se usan en producción — los secretos reales viven en GCP Secret Manager
# y se inyectan en Cloud Run al arrancar el contenedor, sobreescribiendo estos valores.
ARG DJANGO_SECRET_KEY=dummy-build-key-not-used-in-prod
ARG JWT_SIGNING_KEY=dummy-jwt-signing-key-not-used-in-prod
ARG APIS_NET_PE_TOKEN=dummy-apis-token-not-used-in-prod
ARG CORS_ALLOWED_ORIGINS=http://localhost:3000
ENV DJANGO_SECRET_KEY=${DJANGO_SECRET_KEY} \
    JWT_SIGNING_KEY=${JWT_SIGNING_KEY} \
    APIS_NET_PE_TOKEN=${APIS_NET_PE_TOKEN} \
    CORS_ALLOWED_ORIGINS=${CORS_ALLOWED_ORIGINS}

# Recolectar archivos estáticos (WhiteNoise los sirve en producción).
# Se ejecuta aquí una sola vez durante el build, no en cada arranque.
RUN python manage.py collectstatic --noinput

# === SEGURIDAD: ejecutar como usuario sin privilegios ===
RUN groupadd -r appuser && useradd -r -g appuser -u 1000 appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8080

# Healthcheck para Cloud Run y docker-compose local.
# Cloud Run usa esto para determinar si el contenedor está listo antes de
# enrutar tráfico. Intervalo de 30s evita spam de requests al iniciar.
# Nota: en Cloud Run también se configura startup probe en el service YAML.
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8080/api/health/ || exit 1

# Gunicorn con gthread worker:
# - --worker-class gthread: requerido para que --threads tenga efecto.
#   Con el worker sync por defecto, --threads es ignorado silenciosamente.
# - 2 workers × 4 threads = 8 slots concurrentes con ~60% menos RAM que 8 workers sync.
#   Óptimo para 1 vCPU de Cloud Run.
# - --max-requests + --jitter: recicla workers periódicamente para prevenir
#   memory leaks en procesos de larga vida sin downtime (jitter evita reinicio simultáneo).
# - --access-logfile - / --error-logfile -: logs a stdout/stderr para Cloud Run Logging.
CMD ["gunicorn", "config.wsgi:application", \
     "--bind", "0.0.0.0:8080", \
     "--worker-class", "gthread", \
     "--workers", "2", \
     "--threads", "4", \
     "--timeout", "120", \
     "--max-requests", "1000", \
     "--max-requests-jitter", "100", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "--log-level", "info"]
