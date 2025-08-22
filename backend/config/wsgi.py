"""
WSGI config for config project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

# En Cloud Run, aseguramos servir los estáticos del admin incluso si no hubo
# collectstatic, añadiendo explícitamente su directorio a WhiteNoise.
try:
    from whitenoise import WhiteNoise
    from django.conf import settings
except Exception:
    WhiteNoise = None

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

application = get_wsgi_application()

if WhiteNoise is not None:
    # Envolver la app con WhiteNoise y registrar el directorio de admin
    application = WhiteNoise(application)
    try:
        application.add_files(settings.ADMIN_STATIC_DIR, prefix='static/admin/')
    except Exception:
        # Si por alguna razón no existe la ruta, continuamos sin bloquear
        pass
