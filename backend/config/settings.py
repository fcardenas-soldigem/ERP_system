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

# Cargar variables de entorno desde .env (override=True para que .env siempre tenga prioridad)
load_dotenv(os.path.join(BASE_DIR, '.env'), override=True)

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
SESSION_COOKIE_SAMESITE = 'Lax'    # Protección CSRF adicional
CSRF_COOKIE_SAMESITE = 'Lax'

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
]

# Middleware
MIDDLEWARE = [
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
            'OPTIONS': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            },
            'KEY_PREFIX': 'erp',
            'TIMEOUT': 300,  # 5 minutos por defecto
        }
    }
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
# WhiteNoise: servir estáticos comprimidos con manifest (incluye admin)
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Modelo de usuario personalizado
AUTH_USER_MODEL = 'authentication.CustomUser'

# Configuraciones de REST Framework
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20
}

# Configuraciones de Simple JWT
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),  # Reducido de 1 día a 15 minutos por seguridad
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

# OpenAI Configuration
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OPENAI_ASSISTANT_ID = os.getenv('OPENAI_ASSISTANT_ID')
OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4')

# Claude API Configuration (para Analista Comercial)
CLAUDE_API_KEY = os.getenv('CLAUDE_API_KEY')

# Configuración para archivos temporales
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Logging estructurado para Cloud Run
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {name} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
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

