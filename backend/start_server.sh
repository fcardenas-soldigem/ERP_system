#!/bin/bash

echo "Iniciando servidor Django..."

# Activar entorno virtual
source venv/bin/activate

# Limpiar variables de DB para que .env tenga prioridad (via load_dotenv override=True)
unset DB_USER DB_PASSWORD DB_NAME DB_HOST DB_PORT

# Iniciar servidor
python manage.py runserver 0.0.0.0:8080
