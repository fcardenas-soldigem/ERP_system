#!/usr/bin/env python3
"""
Prueba específica del DNI 70774842
"""

import os
import sys
import django

# Configurar Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.core.services.documento_service import DocumentoService

def main():
    print('🔍 Probando consulta del DNI: 70774842')
    print('=' * 50)

    # Consultar el DNI específico
    dni_prueba = '70774842'
    resultado = DocumentoService.consultar_dni(dni_prueba)

    if resultado['success']:
        print(f'✅ DNI {dni_prueba} consultado exitosamente:')
        datos = resultado['data']
        print(f'   • Nombres: {datos["nombres"]}')
        print(f'   • Apellido Paterno: {datos["apellido_paterno"]}')
        print(f'   • Apellido Materno: {datos["apellido_materno"]}')
        print(f'   • Número Documento: {datos["numero_documento"]}')
        print(f'   • Nombre Completo: {datos["nombre_completo"]}')
        print()
        print('📋 Datos formateados para usar en formularios:')
        print(f'   - Nombre para cliente: "{datos["nombre_completo"]}"')
        print(f'   - DNI verificado: {datos["numero_documento"]}')
    else:
        print(f'❌ Error consultando DNI {dni_prueba}:')
        print(f'   • Error: {resultado["error"]}')

    print()
    print('🧪 También probando con el servicio directo (estilo API original):')

    # Crear instancia del servicio
    api = DocumentoService()
    datos_directos = api.get_person(dni_prueba)

    if datos_directos:
        print('✅ Datos obtenidos directamente de la API:')
        print(f'   • Respuesta completa: {datos_directos}')
        print()
        print('📝 Detalles adicionales disponibles:')
        for key, value in datos_directos.items():
            print(f'   - {key}: {value}')
    else:
        print('❌ No se pudieron obtener datos directos')

    print()
    print('💡 Esta consulta quedó guardada en cache por 1 hora para optimizar futuras consultas.')
    print('🔄 Si ejecutas la consulta nuevamente, será instantánea desde el cache.')

if __name__ == "__main__":
    main() 