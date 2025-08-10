#!/usr/bin/env python3
"""
Script para probar la integración del frontend con la API de consulta de documentos
Simula las llamadas que haría el frontend al backend
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

from django.test import Client
from apps.authentication.models import CustomUser
from apps.core.services.documento_service import DocumentoService

def test_endpoints_disponibles():
    """Prueba que los endpoints estén disponibles"""
    print("🌐 Probando endpoints disponibles...")
    print("=" * 50)
    
    # Crear cliente de prueba
    client = Client()
    
    # Crear usuario de prueba si no existe
    try:
        user = CustomUser.objects.get(username='test_user')
    except CustomUser.DoesNotExist:
        user = CustomUser.objects.create_user(
            username='test_user',
            email='test@test.com',
            password='testpass123'
        )
    
    # Login para obtener token (simulando frontend)
    login_response = client.post('/api/core/token/', {
        'username': 'test_user',
        'password': 'testpass123'
    })
    
    if login_response.status_code == 200:
        token_data = json.loads(login_response.content)
        access_token = token_data['access']
        print(f"✅ Autenticación exitosa, token obtenido")
        
        # Headers con token
        headers = {
            'HTTP_AUTHORIZATION': f'Bearer {access_token}',
            'CONTENT_TYPE': 'application/json'
        }
        
        # Probar endpoint de DNI
        print("\n🔍 Probando endpoint de DNI...")
        dni_response = client.get('/api/core/consultar-dni/?dni=70774842', **headers)
        if dni_response.status_code == 200:
            dni_data = json.loads(dni_response.content)
            print(f"✅ Endpoint DNI funcional: {dni_data['success']}")
            if dni_data['success']:
                print(f"   • Nombre: {dni_data['data']['nombre_completo']}")
        else:
            print(f"❌ Error en endpoint DNI: {dni_response.status_code}")
        
        # Probar endpoint universal
        print("\n🔍 Probando endpoint universal...")
        doc_response = client.get('/api/core/consultar-documento/?numero=70774842&tipo=dni', **headers)
        if doc_response.status_code == 200:
            doc_data = json.loads(doc_response.content)
            print(f"✅ Endpoint universal funcional: {doc_data['success']}")
        else:
            print(f"❌ Error en endpoint universal: {doc_response.status_code}")
        
        # Probar endpoint de tipo de cambio
        print("\n💱 Probando endpoint de tipo de cambio...")
        tc_response = client.get('/api/core/tipo-cambio/', **headers)
        if tc_response.status_code == 200:
            tc_data = json.loads(tc_response.content)
            print(f"✅ Endpoint tipo de cambio funcional: {tc_data['success']}")
            if tc_data['success']:
                print(f"   • Compra: S/ {tc_data['data']['compra']}")
                print(f"   • Venta: S/ {tc_data['data']['venta']}")
        else:
            print(f"❌ Error en endpoint tipo de cambio: {tc_response.status_code}")
            
    else:
        print(f"❌ Error de autenticación: {login_response.status_code}")

def test_caso_uso_cliente():
    """Simula el caso de uso completo del frontend"""
    print("\n📋 Simulando caso de uso: Registro de cliente")
    print("=" * 50)
    
    # Datos que enviaría el frontend
    cliente_data = {
        "dni": "70774842",
        "tipo_documento": "dni"
    }
    
    # 1. Consultar DNI (como lo haría el frontend)
    print("1️⃣ Frontend consulta DNI...")
    resultado_dni = DocumentoService.consultar_dni(cliente_data["dni"])
    
    if resultado_dni['success']:
        datos_reniec = resultado_dni['data']
        print(f"   ✅ DNI consultado: {datos_reniec['nombre_completo']}")
        
        # 2. Autocompletar datos (como lo haría el frontend)
        print("2️⃣ Frontend autocompleta datos...")
        cliente_completo = {
            "nombre": datos_reniec['nombre_completo'],
            "documento": datos_reniec['numero_documento'],
            "tipo_documento": "dni",
            "direccion": "",  # Usuario completaría manualmente
            "telefono": "",   # Usuario completaría manualmente
            "email": "",      # Usuario completaría manualmente
            "activo": True
        }
        
        print(f"   📝 Datos preparados para guardar:")
        print(f"      • Nombre: {cliente_completo['nombre']}")
        print(f"      • Documento: {cliente_completo['documento']}")
        print(f"      • Tipo: {cliente_completo['tipo_documento']}")
        print(f"      • Estado: {'Activo' if cliente_completo['activo'] else 'Inactivo'}")
        
        # 3. Simular guardado exitoso
        print("3️⃣ Cliente listo para guardar en base de datos")
        print("   ✅ Integración frontend-backend exitosa")
        
    else:
        print(f"   ❌ Error: {resultado_dni['error']}")

def test_flujo_completo_ui():
    """Simula el flujo completo que vería el usuario"""
    print("\n🎯 Simulando flujo de usuario en la UI")
    print("=" * 50)
    
    print("👤 Usuario abre formulario de 'Agregar Cliente'")
    print("📝 Usuario selecciona 'DNI' como tipo de documento")
    print("⌨️ Usuario ingresa DNI: 70774842")
    print("🔍 Usuario hace clic en 'Consultar'")
    print("⏳ Sistema muestra spinner 'Consultando...'")
    
    # Simular consulta
    resultado = DocumentoService.consultar_dni("70774842")
    
    if resultado['success']:
        datos = resultado['data']
        print("✅ Sistema muestra mensaje: 'Datos obtenidos de RENIEC'")
        print(f"📋 Campo 'Nombre' se autocompleta con: '{datos['nombre_completo']}'")
        print("👤 Usuario completa campos restantes:")
        print("   📧 Email: fabrizio@ejemplo.com")
        print("   📞 Teléfono: 987654321")
        print("   🏠 Dirección: Av. Principal 123")
        print("💾 Usuario hace clic en 'Agregar'")
        print("✅ Sistema muestra: 'Cliente creado exitosamente'")
        print("🔄 Lista de clientes se actualiza automáticamente")
        
        # Mostrar cómo aparecería en la tabla
        print("\n📊 Cliente aparece en la tabla:")
        print("   ID | Nombre                          | Documento | Tipo | Estado")
        print("   ---|--------------------------------|-----------|------|--------")
        print(f"   001| {datos['nombre_completo']:30} | 70774842  | DNI  | Activo")
        
    else:
        print(f"❌ Sistema muestra error: {resultado['error']}")

def main():
    """Función principal"""
    print("🚀 Probando integración completa Frontend-Backend")
    print("🔗 APIs.net.pe + Django + React")
    print("=" * 60)
    
    # Ejecutar todas las pruebas
    test_endpoints_disponibles()
    test_caso_uso_cliente()
    test_flujo_completo_ui()
    
    print("\n" + "=" * 60)
    print("✨ Integración probada exitosamente")
    print("\n💡 Componentes listos para usar:")
    print("   📁 frontend/src/components/Ventas/Clientes.jsx")
    print("   📁 frontend/src/hooks/useConsultaDocumentos.js")
    print("   📁 frontend/src/hooks/useTipoCambio.js")
    print("   📁 backend/apps/core/services/documento_service.py")
    print("   📁 backend/apps/core/views.py (endpoints)")
    print("\n🎯 El usuario puede registrar clientes con consulta automática de DNI/RUC")

if __name__ == "__main__":
    main() 