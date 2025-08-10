import os
import django
from django.db import connection

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

def create_user_database():
    """
    Crea la base de datos user_1_db para el primer usuario.
    """
    try:
        with connection.cursor() as cursor:
            # Crear la base de datos
            cursor.execute("CREATE DATABASE user_1_db")
            print("Base de datos user_1_db creada exitosamente.")
    except Exception as e:
        print(f"Error al crear la base de datos: {e}")

if __name__ == "__main__":
    create_user_database() 