#!/usr/bin/env python3
"""
Script de prueba para el DocumentoService actualizado
Ejecutar desde el directorio backend con: python test_documento_service.py
"""

import os
import sys
import django

# Configurar Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.core.services.documento_service import DocumentoService
from datetime import datetime

def test_dni():
    """Prueba consulta de DNI"""
    print("🔍 Probando consulta de DNI...")
    
    # DNI de prueba (puedes usar uno real para probar)
    dni_prueba = "46027897"  # Del ejemplo de la documentación
    
    resultado = DocumentoService.consultar_dni(dni_prueba)
    
    if resultado['success']:
        print(f"✅ DNI {dni_prueba} consultado exitosamente:")
        datos = resultado['data']
        print(f"   • Nombres: {datos['nombres']}")
        print(f"   • Apellido Paterno: {datos['apellido_paterno']}")
        print(f"   • Apellido Materno: {datos['apellido_materno']}")
        print(f"   • Nombre Completo: {datos['nombre_completo']}")
    else:
        print(f"❌ Error consultando DNI: {resultado['error']}")
    
    print()

def test_ruc():
    """Prueba consulta de RUC"""
    print("🔍 Probando consulta de RUC...")
    
    # RUC de prueba (puedes usar uno real para probar)
    ruc_prueba = "10460278975"  # Del ejemplo de la documentación
    
    resultado = DocumentoService.consultar_ruc(ruc_prueba)
    
    if resultado['success']:
        print(f"✅ RUC {ruc_prueba} consultado exitosamente:")
        datos = resultado['data']
        print(f"   • RUC: {datos['ruc']}")
        print(f"   • Razón Social: {datos['razon_social']}")
        print(f"   • Estado: {datos['estado']}")
        print(f"   • Condición: {datos['condicion']}")
        if datos['direccion']:
            print(f"   • Dirección: {datos['direccion']}")
    else:
        print(f"❌ Error consultando RUC: {resultado['error']}")
    
    print()

def test_tipo_cambio():
    """Prueba consulta de tipo de cambio"""
    print("💱 Probando consulta de tipo de cambio del día...")
    
    resultado = DocumentoService.consultar_tipo_cambio()
    
    if resultado['success']:
        print("✅ Tipo de cambio consultado exitosamente:")
        datos = resultado['data']
        print(f"   • Fecha: {datos['fecha']}")
        print(f"   • Compra: S/ {datos['compra']}")
        print(f"   • Venta: S/ {datos['venta']}")
        print(f"   • Origen: {datos['origen']}")
    else:
        print(f"❌ Error consultando tipo de cambio: {resultado['error']}")
    
    print()

def test_tipo_cambio_fecha():
    """Prueba consulta de tipo de cambio por fecha"""
    print("💱 Probando consulta de tipo de cambio por fecha...")
    
    fecha_prueba = "2024-01-15"
    resultado = DocumentoService.consultar_tipo_cambio(fecha_prueba)
    
    if resultado['success']:
        print(f"✅ Tipo de cambio del {fecha_prueba} consultado exitosamente:")
        datos = resultado['data']
        print(f"   • Fecha: {datos['fecha']}")
        print(f"   • Compra: S/ {datos['compra']}")
        print(f"   • Venta: S/ {datos['venta']}")
        print(f"   • Origen: {datos['origen']}")
    else:
        print(f"❌ Error consultando tipo de cambio: {resultado['error']}")
    
    print()

def test_servicio_directo():
    """Prueba el servicio directo usando la clase como en la documentación oficial"""
    print("🧪 Probando el servicio directo (estilo documentación oficial)...")
    
    # Crear instancia del servicio
    api_consultas = DocumentoService()
    
    # Prueba DNI directo
    print("📋 Consultando DNI directo...")
    person_data = api_consultas.get_person("46027897")
    if person_data:
        print(f"✅ Datos de persona: {person_data}")
    else:
        print("❌ No se pudo consultar DNI")
    
    # Prueba RUC directo
    print("🏢 Consultando RUC directo...")
    company_data = api_consultas.get_company("10460278975")
    if company_data:
        print(f"✅ Datos de empresa: {company_data}")
    else:
        print("❌ No se pudo consultar RUC")
    
    # Prueba tipo de cambio directo
    print("💰 Consultando tipo de cambio directo...")
    exchange_data = api_consultas.get_exchange_rate_today()
    if exchange_data:
        print(f"✅ Tipo de cambio: {exchange_data}")
    else:
        print("❌ No se pudo consultar tipo de cambio")
    
    print()

def test_validaciones():
    """Prueba las validaciones"""
    print("🔒 Probando validaciones...")
    
    # DNI inválido
    resultado = DocumentoService.consultar_dni("123")
    print(f"DNI inválido (123): {resultado['error']}")
    
    # RUC inválido
    resultado = DocumentoService.consultar_ruc("123")
    print(f"RUC inválido (123): {resultado['error']}")
    
    # Tipo de documento inválido
    resultado = DocumentoService.consultar_documento("12345678", "cedula")
    print(f"Tipo inválido (cedula): {resultado['error']}")
    
    print()

def main():
    """Función principal de pruebas"""
    print("🚀 Iniciando pruebas del DocumentoService actualizado")
    print("=" * 60)
    
    # Ejecutar todas las pruebas
    test_validaciones()
    test_dni()
    test_ruc()
    test_tipo_cambio()
    test_tipo_cambio_fecha()
    test_servicio_directo()
    
    print("=" * 60)
    print("✨ Pruebas completadas")
    print("\n💡 Notas:")
    print("   • Los DNI y RUC de prueba pueden no existir")
    print("   • Los errores son normales si los documentos no existen")
    print("   • El cache guarda los resultados por 1 hora (documentos) y 30 min (tipo cambio)")
    print("   • Verifica que tu token de API sea válido y tenga créditos")

if __name__ == "__main__":
    main() 