#!/usr/bin/env python3
"""
Script simple para diagnosticar problemas de autenticación
"""

import os
import sys
import django
import requests
import json

# Configurar Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

def test_authentication():
    """Prueba la autenticación paso a paso"""
    print("🔐 Probando autenticación...")
    
    base_url = 'http://localhost:8000'
    
    # 1. Probar login (usando un usuario que debería existir)
    print("\n1️⃣ Probando login...")
    login_data = {
        'email': 'test@test.com',  # Usuario con contraseña conocida
        'password': 'test123'      # Contraseña que acabamos de establecer
    }
    
    try:
        response = requests.post(f'{base_url}/api/core/token/', json=login_data)
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            tokens = response.json()
            print("   ✅ Login exitoso")
            print(f"   Access token: {tokens['access'][:50]}...")
            print(f"   Refresh token: {tokens['refresh'][:50]}...")
            
            # 2. Probar consulta con token
            print("\n2️⃣ Probando consulta con token...")
            headers = {
                'Authorization': f'Bearer {tokens["access"]}',
                'Content-Type': 'application/json'
            }
            
            consulta_response = requests.get(
                f'{base_url}/api/core/consultar-documento/?numero=70774842&tipo=dni',
                headers=headers
            )
            
            print(f"   Status: {consulta_response.status_code}")
            
            if consulta_response.status_code == 200:
                print("   ✅ Consulta exitosa")
                data = consulta_response.json()
                if data.get('success'):
                    print(f"   Datos: {data['data']['nombre_completo']}")
                else:
                    print(f"   Error en respuesta: {data.get('error')}")
            else:
                print(f"   ❌ Error en consulta: {consulta_response.text}")
                
        else:
            print(f"   ❌ Error en login: {response.text}")
            
    except Exception as e:
        print(f"   ❌ Error de conexión: {e}")

def test_without_auth():
    """Prueba sin autenticación para verificar el error 401"""
    print("\n🚫 Probando sin autenticación...")
    
    base_url = 'http://localhost:8000'
    
    try:
        response = requests.get(f'{base_url}/api/core/consultar-documento/?numero=70774842&tipo=dni')
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 401:
            print("   ✅ Error 401 correcto (sin auth)")
        else:
            print(f"   ❓ Status inesperado: {response.text}")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")

if __name__ == "__main__":
    print("🚀 Diagnóstico de Autenticación")
    print("=" * 40)
    
    test_without_auth()
    test_authentication()
    
    print("\n" + "=" * 40)
    print("✅ Diagnóstico completado") 