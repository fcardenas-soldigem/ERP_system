#!/usr/bin/env python
import os
import django
import requests
import json

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import AccessToken

def test_api():
    print('🔍 PRUEBA DE API AI THREADS')
    print('='*50)
    
    # Obtener token de usuario
    User = get_user_model()
    try:
        user = User.objects.first()
        if not user:
            print('❌ No hay usuarios en la base de datos')
            return
        
        # Generar token
        token = AccessToken.for_user(user)
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {str(token)}'
        }
        
        print(f'✅ Usuario encontrado: {user.email}')
        print(f'✅ Token generado: {str(token)[:20]}...')
        
        # Probar crear thread
        print('\n📡 Probando crear thread...')
        response = requests.post(
            'http://localhost:8000/api/ai/threads/',
            headers=headers
        )
        
        print(f'Status Code: {response.status_code}')
        print(f'Response: {response.text}')
        
        if response.status_code == 200 or response.status_code == 201:
            print('✅ API funcionando correctamente')
            thread_data = response.json()
            thread_id = thread_data.get('thread_id')
            
            # Probar enviar mensaje
            if thread_id:
                print(f'\n📨 Probando enviar mensaje a thread {thread_id}...')
                message_response = requests.post(
                    f'http://localhost:8000/api/ai/threads/{thread_id}/messages/',
                    headers=headers,
                    json={'content': 'Hola, ¿cómo estás?'}
                )
                print(f'Status Code: {message_response.status_code}')
                print(f'Response: {message_response.text}')
        else:
            print('❌ Error en la API')
            
    except Exception as e:
        print(f'❌ Error: {str(e)}')

if __name__ == '__main__':
    test_api() 