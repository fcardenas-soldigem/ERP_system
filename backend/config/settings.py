"""
Configuración principal de Django para tu proyecto ERP_system.
"""

import os
from pathlib import Path
from datetime import timedelta
import django
from dotenv import load_dotenv

# BASE_DIR apunta a la carpeta "backend"
BASE_DIR = Path(__file__).resolve().parent.parent

# Cargar variables de entorno. Se prefiere .env.local (desarrollo) si existe;
# si no, .env. Así el dev no apunta a producción por accidente: .env.local trae
# la BD local (DB_HOST=localhost). Las credenciales de prod viven en
# .env.production, que NO se carga por defecto. Todos estos archivos están en
# .gitignore. Para forzar prod localmente: DOTENV_FILE=.env.production.
_dotenv_override = os.getenv('DOTENV_FILE')
_env_local = os.path.join(BASE_DIR, '.env.local')
_env_default = os.path.join(BASE_DIR, '.env')
if _dotenv_override:
    _dotenv_path = os.path.join(BASE_DIR, _dotenv_override)
elif os.path.exists(_env_local):
    _dotenv_path = _env_local
else:
    _dotenv_path = _env_default
load_dotenv(_dotenv_path, override=True)

# === SECURITY: SECRET KEYS ===
# CRITICAL: Must be set via environment variables in production
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY')
if not SECRET_KEY:
    raise ValueError("DJANGO_SECRET_KEY environment variable must be set")

# JWT Signing Key (separate from Django SECRET_KEY for better security)
JWT_SIGNING_KEY = os.getenv('JWT_SIGNING_KEY')
if not JWT_SIGNING_KEY:
    raise ValueError("JWT_SIGNING_KEY environment variable must be set")

# === APIS.NET.PE CONFIGURATION ===
# Token para consultas de DNI/RUC en APIs.net.pe
APIS_NET_PE_TOKEN = os.getenv('APIS_NET_PE_TOKEN')
if not APIS_NET_PE_TOKEN:
    raise ValueError("APIS_NET_PE_TOKEN environment variable must be set")

# Modo de depuración
DEBUG = os.getenv('DJANGO_DEBUG', 'False').lower() == 'true'

# Hosts permitidos - NUNCA usar '*' en producción
ALLOWED_HOSTS = os.getenv('DJANGO_ALLOWED_HOSTS', '').split(',') if os.getenv('DJANGO_ALLOWED_HOSTS') else []
if not ALLOWED_HOSTS or '*' in ALLOWED_HOSTS:
    if not DEBUG:
        raise ValueError("DJANGO_ALLOWED_HOSTS must be explicitly set in production (not '*')")

# Confianza para orígenes detrás de proxy (Cloud Run) y CSRF
# Importante: incluye el dominio exacto del servicio y el comodín de run.app
CSRF_TRUSTED_ORIGINS = [
    'https://erp-backend-25656632090.southamerica-west1.run.app',
    'https://*.run.app',
    'https://erp.soldigem.com.pe',
    'https://api.soldigem.com.pe',
    'http://localhost:3000',
]
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True

# === SECURITY HEADERS Y COOKIES ===
# Forzar HTTPS en producción (solo cuando no estés detrás de un proxy que ya lo hace)
# SECURE_SSL_REDIRECT = not DEBUG  # Descomenta si quieres forzar redirect en Django

# Cookies seguras (solo HTTPS)
SESSION_COOKIE_SECURE = not DEBUG  # True en producción
CSRF_COOKIE_SECURE = not DEBUG     # True en producción
SESSION_COOKIE_HTTPONLY = True     # Previene acceso desde JavaScript
CSRF_COOKIE_HTTPONLY = True        # Previene acceso desde JavaScript
SESSION_COOKIE_SAMESITE = 'None'   # Cross-domain Vercel→Cloud Run (requiere Secure=True, ya activo en prod)
CSRF_COOKIE_SAMESITE = 'None'      # Idem — Django mantiene CSRF token-based protection

# HSTS (HTTP Strict Transport Security) - fuerza HTTPS en el navegador
SECURE_HSTS_SECONDS = 31536000 if not DEBUG else 0  # 1 año en producción
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_HSTS_PRELOAD = not DEBUG

# Content Security y otras protecciones
SECURE_CONTENT_TYPE_NOSNIFF = True    # Previene MIME-type sniffing
X_FRAME_OPTIONS = 'DENY'              # Previene clickjacking
SECURE_BROWSER_XSS_FILTER = True      # XSS filter (legacy pero útil)
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'

# Aplicaciones instaladas
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third party apps
    'rest_framework',
    'corsheaders',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    
    # Local apps
    'apps.authentication',
    'apps.empresas',
    'apps.ventas',
    'apps.compras',
    'apps.inventario',
    'apps.dashboard',
    'apps.ai_assistant',
    'apps.core',
    'apps.ml_models',  # Machine Learning models
    'apps.cotizaciones',  # Cotizaciones
    'apps.produccion',   # Producción
    'apps.finanzas',     # Módulo de Finanzas
    'apps.importador',   # Importador Excel
    'apps.guias',        # Guías de Remisión
    'apps.servicios',    # Órdenes de Servicio de Reparación
    'apps.leads',        # Captura de leads (landing acceso anticipado)
    'apps.agente',       # Agente MCP (tokens, log de auditoría, endpoint /api/mcp/)
]

# Middleware
MIDDLEWARE = [
    'apps.core.middleware.request_context.RequestContextMiddleware',  # request_id/contexto de logs (primero)
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'apps.core.middleware.tenant.TenantMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# Configuraciones de URL
ROOT_URLCONF = 'config.urls'

# Configuraciones de plantillas
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],  # si usas carpeta "templates" en backend/
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# Configuración WSGI
WSGI_APPLICATION = 'config.wsgi.application'

# Configuración de la base de datos
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME', 'ERP_system'),
        'USER': os.getenv('DB_USER', 'postgres'),
        'PASSWORD': os.getenv('DB_PASSWORD', ''),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '5432'),
        'CONN_MAX_AGE': 60,
        'CONN_HEALTH_CHECKS': True,
        'ATOMIC_REQUESTS': False,
        'OPTIONS': {
            'connect_timeout': 30,
            'keepalives': 1,
            'keepalives_idle': 30,
            'keepalives_interval': 10,
            'keepalives_count': 5,
            'sslmode': 'require' if ('supabase' in os.getenv('DB_HOST', '') or 'pooler' in os.getenv('DB_HOST', '')) else 'prefer',
        }
    }
}

# ========================================
# CACHE CONFIGURATION
# ========================================
# Usar Redis si está disponible, sino memoria local
REDIS_URL = os.getenv('REDIS_URL', None)

if REDIS_URL:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'LOCATION': REDIS_URL,
            'KEY_PREFIX': 'erp',
            'TIMEOUT': 300,  # 5 minutos por defecto
        }
    }
    SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
    SESSION_CACHE_ALIAS = 'default'
else:
    # Cache en memoria local (para desarrollo o si no hay Redis)
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'unique-snowflake',
            'TIMEOUT': 300,  # 5 minutos
            'OPTIONS': {
                'MAX_ENTRIES': 1000
            }
        }
    }

# Timeouts de cache específicos (en segundos)
CACHE_TIMEOUTS = {
    'productos': 120,        # 2 minutos - cambia frecuentemente
    'categorias': 600,       # 10 minutos - cambia poco
    'almacenes': 600,        # 10 minutos
    'inventario_mp': 60,     # 1 minuto - crítico
    'inventario_pt': 60,     # 1 minuto - crítico
    'resumen': 30,           # 30 segundos
    'alertas': 60,           # 1 minuto
    'estadisticas': 300,     # 5 minutos
}

# Validadores de contraseñas
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Configuraciones de internacionalización
LANGUAGE_CODE = 'es'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True

# Archivos estáticos
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# ============================================================================
# ALMACENAMIENTO DE ARCHIVOS (media) — GCS en prod, disco local en dev
# ============================================================================
# La selección es por entorno, controlada por GS_BUCKET_NAME:
#   - Definido  → Google Cloud Storage (persistente; sobrevive deploys).
#   - Ausente   → FileSystemStorage en MEDIA_ROOT (desarrollo local, igual que hoy).
#
# Firma de URLs SIN archivo de llave: en Cloud Run la credencial por defecto es la
# Service Account del servicio. django-storages/google-cloud-storage firman las URLs
# (v4) vía la API IAM `signBlob` (iam.serviceAccounts.signBlob), para lo cual la SA
# tiene el rol roles/iam.serviceAccountTokenCreator sobre sí misma. No se monta ningún
# JSON de credenciales: se usan las credenciales por defecto del entorno (ADC) y
# GS_PROJECT_ID para resolver el proyecto. Si alguna vez GS_CREDENTIALS fuese necesario,
# se inyectaría por env; hoy no hace falta.
GS_BUCKET_NAME = os.getenv('GS_BUCKET_NAME')
GS_PROJECT_ID = os.getenv('GS_PROJECT_ID')
# Firma vía IAM signBlob (django-storages >= 1.14.6): la SA del servicio (metadata,
# sin llave privada) firma las URLs llamando a la API iam.serviceAccounts.signBlob.
# GS_SA_EMAIL es la SA que firma; por defecto la Compute Engine default SA del proyecto.
# Debe tener rol roles/iam.serviceAccountTokenCreator sobre sí misma.
GS_SA_EMAIL = os.getenv('GS_SA_EMAIL', '25656632090-compute@developer.gserviceaccount.com')

_STATICFILES_STORAGE = {
    # WhiteNoise: estáticos comprimidos con manifest (incluye admin)
    'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
}

if GS_BUCKET_NAME:
    STORAGES = {
        'default': {
            'BACKEND': 'storages.backends.gcloud.GoogleCloudStorage',
            'OPTIONS': {
                'bucket_name': GS_BUCKET_NAME,
                'project_id': GS_PROJECT_ID,
                'default_acl': None,          # bucket con uniform bucket-level access
                'querystring_auth': True,     # bucket privado → URLs firmadas
                'iam_sign_blob': True,        # firma vía IAM (SA sin llave privada en Cloud Run)
                'sa_email': GS_SA_EMAIL,      # SA que firma (equiv. GS_SA_EMAIL)
                'expiration': timedelta(minutes=15),  # equiv. GS_EXPIRATION
                'file_overwrite': False,      # nombres uuid; nunca pisar
            },
        },
        'staticfiles': _STATICFILES_STORAGE,
    }
else:
    STORAGES = {
        'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
        'staticfiles': _STATICFILES_STORAGE,
    }

# Validación de uploads (tipos y tamaño) — usada por los FileField/ImageField.
ALLOWED_UPLOAD_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png', 'webp'}
MAX_UPLOAD_SIZE_MB = 10

# Modelo de usuario personalizado
AUTH_USER_MODEL = 'authentication.CustomUser'

# Configuraciones de REST Framework
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'apps.core.authentication.JWTAuthenticationConContexto',  # SimpleJWT + user/empresa en logs
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    # Rate del endpoint público de leads (scope 'leads'); se aplica solo en esa
    # view, no afecta al resto de la API.
    'DEFAULT_THROTTLE_RATES': {
        'leads': '5/hour',
        'mcp': '60/min',   # por token (agente MCP)
    },
}

# Configuraciones de Simple JWT
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=6),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': False,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': JWT_SIGNING_KEY,  # Usa variable de entorno separada
    'VERIFYING_KEY': None,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
}

# Configuraciones de CORS - Restringidas por seguridad
# NUNCA usar CORS_ALLOW_ALL_ORIGINS en producción
CORS_ALLOWED_ORIGINS = os.getenv('CORS_ALLOWED_ORIGINS', '').split(',') if os.getenv('CORS_ALLOWED_ORIGINS') else []
if not CORS_ALLOWED_ORIGINS and not DEBUG:
    raise ValueError("CORS_ALLOWED_ORIGINS must be explicitly set in production")

CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTHENTICATION_BACKENDS = [
    'apps.authentication.backends.EmailBackend',
    'django.contrib.auth.backends.ModelBackend',
]

# === LLM (asistente IA) — capa propia, sin API de Assistants ===
# LLM_PROVIDER: 'vertex' (Gemini en Vertex AI, ADC, sin API key; por defecto) u 'openai'
# (cualquier API compatible con chat.completions: LLM_BASE_URL + LLM_API_KEY).
# Modelos verificados en la doc de Vertex (2026-10-16): gemini-3.1-flash-lite (GA, solo
# endpoints global/us/eu) y gemini-2.5-flash-lite (GA, se retira el 2026-10-20).
LLM_PROVIDER = os.getenv('LLM_PROVIDER', 'vertex').lower()
LLM_MODEL = os.getenv('LLM_MODEL', 'gemini-3.1-flash-lite')
LLM_LOCATION = os.getenv('LLM_LOCATION', 'global')
LLM_PROJECT = os.getenv('LLM_PROJECT', os.getenv('GS_PROJECT_ID', ''))
LLM_BASE_URL = os.getenv('LLM_BASE_URL') or None
LLM_API_KEY = os.getenv('LLM_API_KEY')
LLM_TIMEOUT = float(os.getenv('LLM_TIMEOUT', '30'))      # segundos → 502 si se excede
LLM_HISTORIAL_N = int(os.getenv('LLM_HISTORIAL_N', '20'))  # mensajes de contexto por turno
# Tools que MODIFICAN datos (crear_venta, crear_compra): por defecto NO se exponen al modelo
# (quedan fuera del schema) y el ejecutor las rechaza. Activar solo con confirmación UI.
LLM_WRITE_TOOLS = os.getenv('LLM_WRITE_TOOLS', 'false').lower() in ('1', 'true', 'yes')


# Configuración para archivos temporales
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Logging estructurado (B3): JSON a stdout para Cloud Logging (severity, message,
# request_id, path, empresa_id, user_id). LOG_FORMAT=text para leer en consola local
# (por defecto: text si DEBUG, json si no). Nunca datos personales ni montos en logs.
LOG_FORMAT = os.getenv('LOG_FORMAT', 'text' if DEBUG else 'json').lower()
_LOG_FORMATTER = 'json' if LOG_FORMAT == 'json' else 'verbose'
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'request_context': {'()': 'apps.core.logging_json.RequestContextFilter'},
    },
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {name} [req={request_id} emp={empresa_id} user={user_id}] {message}',
            'style': '{',
        },
        'json': {'()': 'apps.core.logging_json.JSONFormatter'},
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': _LOG_FORMATTER,
            'filters': ['request_context'],
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
    'loggers': {
        'django.request': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': False,
        },
        'django.server': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': False,
        },
        'apps': {
            'handlers': ['console'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
        'apps.core.middleware.tenant': {
            'handlers': ['console'],
            'level': 'DEBUG' if DEBUG else 'WARNING',
            'propagate': False,
        },
    },
}

