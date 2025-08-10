#!/usr/bin/env python
import os
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from apps.empresas.models import Empresa

def check_users():
    print('🔍 VERIFICACIÓN DE USUARIOS Y EMPRESAS')
    print('='*50)
    
    User = get_user_model()
    users = User.objects.all()
    
    print(f'Total usuarios: {users.count()}')
    
    for user in users:
        print(f'\nUsuario: {user.email}')
        print(f'Empresa: {user.empresa}')
        print(f'Empresa ID: {user.empresa.id if user.empresa else "❌ SIN EMPRESA"}')
    
    print('\n🏢 EMPRESAS DISPONIBLES:')
    empresas = Empresa.objects.all()
    for empresa in empresas:
        print(f'- ID: {empresa.id}, Nombre: {empresa.nombre}')
    
    # Asignar empresa al usuario sin empresa
    users_sin_empresa = users.filter(empresa__isnull=True)
    if users_sin_empresa.exists() and empresas.exists():
        print('\n🔧 ASIGNANDO EMPRESA A USUARIOS SIN EMPRESA...')
        primera_empresa = empresas.first()
        for user in users_sin_empresa:
            user.empresa = primera_empresa
            user.save()
            print(f'✅ Usuario {user.email} asignado a empresa {primera_empresa.nombre}')

if __name__ == '__main__':
    check_users() 