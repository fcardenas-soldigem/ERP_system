#!/usr/bin/env python
import os
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.conf import settings

def validar_configuracion():
    print('🔍 VALIDACIÓN DE CONFIGURACIÓN OPENAI')
    print('='*50)
    
    # Verificar variables de entorno
    print(f'OPENAI_API_KEY: {"✅ Configurada" if settings.OPENAI_API_KEY else "❌ No encontrada"}')
    print(f'OPENAI_ASSISTANT_ID: {"✅ Configurada" if settings.OPENAI_ASSISTANT_ID else "❌ No encontrada"}')
    print(f'OPENAI_MODEL: {getattr(settings, "OPENAI_MODEL", "❌ No encontrada")}')
    
    # Si están configuradas, mostrar preview
    if settings.OPENAI_API_KEY:
        print(f'API_KEY preview: {settings.OPENAI_API_KEY[:20]}...')
    if settings.OPENAI_ASSISTANT_ID:
        print(f'ASSISTANT_ID: {settings.OPENAI_ASSISTANT_ID}')
    
    print('\n🔍 VALIDACIÓN DE IMPORTACIONES')
    print('='*50)
    
    # Verificar importaciones
    try:
        from apps.ai_assistant.services import AIAssistantService
        print('✅ AIAssistantService importado correctamente')
    except Exception as e:
        print(f'❌ Error importando AIAssistantService: {e}')
    
    try:
        from apps.ai_assistant.services import AnalistaComercialService  
        print('✅ AnalistaComercialService importado correctamente')
    except Exception as e:
        print(f'❌ Error importando AnalistaComercialService: {e}')
    
    # Verificar cliente OpenAI
    try:
        from openai import OpenAI
        if settings.OPENAI_API_KEY:
            client = OpenAI(api_key=settings.OPENAI_API_KEY)
            print('✅ Cliente OpenAI creado correctamente')
        else:
            print('❌ No se puede crear cliente OpenAI - API Key faltante')
    except Exception as e:
        print(f'❌ Error creando cliente OpenAI: {e}')
    
    # Verificar anthropic
    try:
        import anthropic
        print('✅ Anthropic importado correctamente')
    except Exception as e:
        print(f'❌ Error importando Anthropic: {e}')
    
    print('\n🔍 VALIDACIÓN DE ARCHIVOS DE CONFIGURACIÓN')
    print('='*50)
    
    # Verificar archivo .env
    env_paths = ['.env', '../.env', 'backend/.env']
    env_found = False
    for path in env_paths:
        if os.path.exists(path):
            print(f'✅ Archivo .env encontrado en: {path}')
            env_found = True
            break
    
    if not env_found:
        print('❌ Archivo .env no encontrado')
        print('💡 Debes crear el archivo .env con:')
        print('   OPENAI_API_KEY=tu_api_key')
        print('   OPENAI_ASSISTANT_ID=tu_assistant_id')

if __name__ == '__main__':
    validar_configuracion() 