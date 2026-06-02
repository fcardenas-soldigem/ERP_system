from django.db.models import Q
from apps.ventas.models import Cliente
from apps.inventario.models import Producto
from apps.ventas.serializers import VentaSerializer
from datetime import date

class VentasExecutor:
    def __init__(self, user):
        self.user = user
        self.empresa = user.empresa

    def crear_venta(self, **kwargs):
        """Crear una nueva venta"""
        try:
            
            # Validar cliente
            cliente_id = kwargs.get('cliente_id')
            try:
                cliente = Cliente.objects.get(id=cliente_id, empresa=self.empresa)
            except Cliente.DoesNotExist:
                return {
                    'success': False,
                    'error': f'Cliente con ID {cliente_id} no encontrado en tu empresa'
                }

            # Validar productos
            productos_data = kwargs.get('productos', [])
            if not productos_data:
                return {
                    'success': False,
                    'error': 'Debe incluir al menos un producto en la venta'
                }

            detalles_data = []
            for producto_data in productos_data:
                try:
                    producto = Producto.objects.get(
                        sku=producto_data['producto_sku'],
                        empresa=self.empresa
                    )
                    
                    # Validar stock
                    stock_disponible = producto.get_stock_total()
                    if stock_disponible < producto_data['cantidad']:
                        return {
                            'success': False,
                            'error': f'Stock insuficiente para {producto.nombre}. Disponible: {stock_disponible}, Solicitado: {producto_data["cantidad"]}'
                        }
                    
                    detalles_data.append({
                        'producto': producto.id,
                        'cantidad': producto_data['cantidad'],
                        'precio_unitario': producto_data['precio_unitario']
                    })
                    
                except Producto.DoesNotExist:
                    return {
                        'success': False,
                        'error': f'Producto con SKU {producto_data["producto_sku"]} no encontrado'
                    }

            # Preparar datos de venta
            venta_data = {
                'cliente_id': cliente_id,
                'fecha_emision': date.today(),
                'estado': 'pendiente',
                'tipo_venta': kwargs.get('tipo_venta'),
                'metodo_pago': kwargs.get('metodo_pago'),
                'igv_incluido': kwargs.get('igv_incluido', True),
                'notas': kwargs.get('notas', '')
            }


            # Crear la venta usando el serializer
            datos_completos = venta_data.copy()
            datos_completos['detalles'] = detalles_data
            
            context = {'request': type('Request', (), {'user': self.user})()}
            serializer = VentaSerializer(data=datos_completos, context=context)
            
            if serializer.is_valid():
                venta = serializer.save()
                return {
                    'success': True,
                    'venta_id': venta.id,
                    'numero': venta.numero,
                    'cliente': venta.cliente.nombre,
                    'subtotal': float(venta.subtotal),
                    'igv': float(venta.igv),
                    'total': float(venta.total),
                    'estado': venta.estado,
                    'tipo_venta': venta.get_tipo_venta_display(),
                    'productos_vendidos': venta.detalles.count(),
                    'mensaje': f'✅ Venta {venta.numero} creada exitosamente para {venta.cliente.nombre} por S/ {venta.total}. Stock actualizado automáticamente.'
                }
            else:
                return {
                    'success': False,
                    'error': f'Error en validación: {serializer.errors}'
                }

        except Exception as e:
            return {
                'success': False,
                'error': f'Error interno: {str(e)}'
            }

    def buscar_productos(self, **kwargs):
        """Buscar productos por nombre, descripción o SKU"""
        try:
            query = kwargs.get('query', '').strip()
            if not query:
                return {
                    'success': False,
                    'error': 'Debe proporcionar un término de búsqueda'
                }

            productos = Producto.objects.filter(
                Q(nombre__icontains=query) |
                Q(descripcion__icontains=query) |
                Q(sku__icontains=query),
                empresa=self.empresa
            )[:10]  # Limitar a 10 resultados

            resultados = []
            for producto in productos:
                resultados.append({
                    'sku': producto.sku,
                    'nombre': producto.nombre,
                    'stock': float(producto.get_stock_total()),
                    'precio_venta': float(producto.precio_venta) if producto.precio_venta else 0,
                    'unidad_medida': producto.get_unidad_medida_display()
                })

            return {
                'success': True,
                'productos': resultados,
                'total_encontrados': len(resultados)
            }

        except Exception as e:
            return {
                'success': False,
                'error': f'Error en búsqueda: {str(e)}'
            }

    def buscar_clientes(self, **kwargs):
        """Buscar clientes por nombre o documento"""
        try:
            query = kwargs.get('query', '').strip()
            if not query:
                return {
                    'success': False,
                    'error': 'Debe proporcionar un término de búsqueda'
                }

            clientes = Cliente.objects.filter(
                Q(nombre__icontains=query) |
                Q(documento__icontains=query),
                empresa=self.empresa
            )[:10]  # Limitar a 10 resultados

            resultados = []
            for cliente in clientes:
                resultados.append({
                    'id': cliente.id,
                    'nombre': cliente.nombre,
                    'documento': cliente.documento,
                    'tipo_documento': cliente.get_tipo_documento_display()
                })

            return {
                'success': True,
                'clientes': resultados,
                'total_encontrados': len(resultados)
            }

        except Exception as e:
            return {
                'success': False,
                'error': f'Error en búsqueda: {str(e)}'
            } 