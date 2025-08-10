import os
import django
from django.db import connection
from django.core.management import call_command
import sys

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

USER_ID = 1  # Cambia este valor por el ID del usuario que corresponda
DB_NAME = f'user_{USER_ID}_db'


def create_user_database():
    try:
        with connection.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE {DB_NAME}")
            print(f"Base de datos {DB_NAME} creada exitosamente.")
    except Exception as e:
        print(f"Error al crear la base de datos (puede que ya exista): {e}")


def migrate_user_database():
    from django.conf import settings
    # Guardar el nombre original
    original_db_name = settings.DATABASES['default']['NAME']
    # Cambiar temporalmente la base de datos por defecto
    settings.DATABASES['default']['NAME'] = DB_NAME
    print(f"Aplicando migraciones en la base de datos {DB_NAME}...")
    try:
        call_command('migrate', database='default', interactive=False)
        print(f"Migraciones aplicadas correctamente en {DB_NAME}.")
    except Exception as e:
        print(f"Error al aplicar migraciones: {e}")
    finally:
        # Restaurar el nombre original
        settings.DATABASES['default']['NAME'] = original_db_name


if __name__ == "__main__":
    create_user_database()
    migrate_user_database() 