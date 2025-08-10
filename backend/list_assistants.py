#!/usr/bin/env python
import os
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.conf import settings
from openai import OpenAI

def list_assistants():
    print('🔍 LISTANDO ASISTENTES DISPONIBLES')
    print('='*50)
    
    try:
        # Crear cliente OpenAI
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        
        # Listar asistentes
        print('📡 Obteniendo lista de asistentes...')
        assistants = client.beta.assistants.list()
        
        print(f'Total asistentes encontrados: {len(assistants.data)}')
        print()
        
        for i, assistant in enumerate(assistants.data, 1):
            print(f'{i}. ID: {assistant.id}')
            print(f'   Nombre: {assistant.name}')
            print(f'   Descripción: {assistant.description}')
            print(f'   Modelo: {assistant.model}')
            print(f'   Creado: {assistant.created_at}')
            print()
        
        # Verificar el asistente configurado
        configured_id = settings.OPENAI_ASSISTANT_ID
        print(f'🔍 Asistente configurado en settings: {configured_id}')
        
        # Buscar si el asistente configurado existe
        found = False
        for assistant in assistants.data:
            if assistant.id == configured_id:
                print(f'✅ ¡El asistente configurado SÍ existe!')
                print(f'   Nombre: {assistant.name}')
                found = True
                break
        
        if not found:
            print(f'❌ El asistente configurado NO existe en tu cuenta')
            if assistants.data:
                print(f'💡 Sugerencia: Usa uno de los asistentes listados arriba')
        
    except Exception as e:
        print(f'❌ Error: {str(e)}')

if __name__ == '__main__':
    list_assistants() 