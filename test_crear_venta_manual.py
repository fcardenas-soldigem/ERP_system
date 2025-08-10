#!/usr/bin/env python3
import os, sys, django
sys.path.append('/Users/renatocardenas/Desktop/ERP/ERP_system/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.ventas.serializers import VentaSerializer
from apps.authentication.models import CustomUser
from apps.inventario.models import Producto

def test_estructura_venta():
    """Probar la estructura correcta para crear ventas"""
    print("🔍 PROBANDO ESTRUCTURA DE VENTA")
    print("=" * 50)
    
    # Obtener usuario con empresa
    user = CustomUser.objects.filter(empresa__isnull=False).first()
    print(f"Usuario: {user.username}")
    print(f"Empresa: {user.empresa.nombre}")
    
    # Obtener un producto con stock
    producto = Producto.objects.filter(
        empresa=user.empresa, 
        is_active=True,
        stock_total__gt=0
    ).first()
    
    if not producto:
        print("❌ No hay productos con stock")
        return
    
    print(f"Producto encontrado: {producto.sku} - {producto.nombre}")
    print(f"Stock disponible: {producto.get_stock_total()}")
    print(f"Precio venta: {producto.precio_venta}")
    
    # Obtener cliente
    from apps.ventas.models import Cliente
    cliente = Cliente.objects.filter(empresa=user.empresa, activo=True).first()
    
    if not cliente:
        print("❌ No hay clientes activos")
        return
    
    print(f"Cliente encontrado: {cliente.nombre}")
    
    # Mock request
    class MockRequest:
        def __init__(self, user):
            self.user = user
    
    # INTENTO 1: Estructura básica sin detalles
    print("\n🧪 INTENTO 1: Solo datos básicos de venta")
    venta_data_basica = {
        'cliente_id': cliente.id,
        'fecha_emision': '2025-06-11',
        'estado': 'pendiente',
        'tipo_venta': 'contado',
        'metodo_pago': 'efectivo',
        'igv_incluido': True,
        'notas': 'Venta de prueba desde backend'
    }
    
    context = {'request': MockRequest(user)}
    serializer1 = VentaSerializer(data=venta_data_basica, context=context)
    
    if serializer1.is_valid():
        print("✅ Datos básicos válidos")
        try:
            venta1 = serializer1.save()
            print(f"✅ Venta básica creada: {venta1.numero}")
            print(f"   Total: {venta1.total}")
        except Exception as e:
            print(f"❌ Error creando venta básica: {e}")
    else:
        print(f"❌ Errores en datos básicos: {serializer1.errors}")
    
    # INTENTO 2: Con detalles en initial_data (como hace el VentaSerializer original)
    print("\n🧪 INTENTO 2: Con detalles en initial_data")
    venta_data_completa = venta_data_basica.copy()
    
    detalles_data = [{
        'producto': producto.id,
        'cantidad': 2,
        'precio_unitario': float(producto.precio_venta)
    }]
    
    # Crear serializer con initial_data que incluye detalles
    serializer2 = VentaSerializer(data=venta_data_basica, context=context)
    serializer2.initial_data = {
        **venta_data_basica,
        'detalles': detalles_data
    }
    
    if serializer2.is_valid():
        print("✅ Datos con detalles válidos")
        try:
            venta2 = serializer2.save()
            print(f"✅ Venta con detalles creada: {venta2.numero}")
            print(f"   Total: {venta2.total}")
            print(f"   Detalles: {venta2.detalles.count()}")
        except Exception as e:
            print(f"❌ Error creando venta con detalles: {e}")
            import traceback
            traceback.print_exc()
    else:
        print(f"❌ Errores en datos con detalles: {serializer2.errors}")

if __name__ == "__main__":
    test_estructura_venta() 