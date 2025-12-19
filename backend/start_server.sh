#!/bin/bash

# Script para iniciar el servidor Django con las configuraciones correctas

echo "🚀 Iniciando servidor Django..."

# Activar entorno virtual
source venv/bin/activate

# Configurar variables de entorno
export DB_USER=erp_user
export DB_PASSWORD=""
export DB_NAME=ERP_system
export DB_HOST=localhost
export DB_PORT=5432

# Iniciar servidor
python manage.py runserver 0.0.0.0:8080

