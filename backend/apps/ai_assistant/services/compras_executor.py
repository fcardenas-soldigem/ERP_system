from django.db.models import Q
from apps.compras.models import Proveedor, Compra
from apps.inventario.models import Producto, Almacen
from apps.compras.serializers import CompraSerializer
from datetime import date, datetime

class ComprasExecutor:
    def __init__(self, user):
        self.user = user
        self.empresa = user.empresa

    def crear_compra(self, **kwargs):
        """Crear una nueva orden de compra"""
        try:
            
            # Validar proveedor
            proveedor_id = kwargs.get('proveedor_id')
            try:
                proveedor = Proveedor.objects.get(id=proveedor_id, empresa=self.empresa)
            except Proveedor.DoesNotExist:
                return {
                    'success': False,
                    'error': f'Proveedor con ID {proveedor_id} no encontrado en tu empresa'
                }

            # Validar almacén
            almacen_id = kwargs.get('almacen_id')
            try:
                almacen = Almacen.objects.get(id=almacen_id, empresa=self.empresa)
            except Almacen.DoesNotExist:
                return {
                    'success': False,
                    'error': f'Almacén con ID {almacen_id} no encontrado en tu empresa'
                }

            # Validar productos
            productos_data = kwargs.get('productos', [])
            if not productos_data:
                return {
                    'success': False,
                    'error': 'Debe incluir al menos un producto en la compra'
                }

            detalles_data = []
            for producto_data in productos_data:
                try:
                    producto = Producto.objects.get(
                        sku=producto_data['producto_sku'],
                        empresa=self.empresa
                    )
                    
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

            # Preparar datos de compra
            fecha_entrega = kwargs.get('fecha_entrega')
            if fecha_entrega:
                try:
                    fecha_entrega = datetime.strptime(fecha_entrega, '%Y-%m-%d').date()
                except ValueError:
                    fecha_entrega = None

            compra_data = {
                'proveedor': proveedor_id,
                'almacen': almacen_id,
                'fecha_emision': date.today(),
                'estado': 'pendiente',
                'tipo_compra': kwargs.get('tipo_compra'),
                'metodo_pago': kwargs.get('metodo_pago'),
                'notas': kwargs.get('notas', '')
            }


            # Crear la compra usando el serializer
            datos_completos = compra_data.copy()
            datos_completos['detalles'] = detalles_data
            
            
            context = {'request': type('Request', (), {'user': self.user})()}
            serializer = CompraSerializer(data=datos_completos, context=context)
            
            if serializer.is_valid():
                compra = serializer.save()
                return {
                    'success': True,
                    'compra_id': compra.id,
                    'numero': compra.numero,
                    'proveedor': compra.proveedor.razon_social,
                    'almacen': almacen.nombre,
                    'subtotal': float(compra.subtotal),
                    'igv': float(compra.igv),
                    'total': float(compra.total),
                    'estado': compra.estado,
                    'tipo_compra': compra.get_tipo_compra_display(),
                    'productos_comprados': compra.detalles.count(),
                    'mensaje': f'✅ Compra {compra.numero} creada exitosamente para {compra.proveedor.razon_social} por S/ {compra.total}. Productos se recibirán en {almacen.nombre}.'
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
                    'precio_compra': float(producto.precio_compra) if producto.precio_compra else 0,
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

    def buscar_proveedores(self, **kwargs):
        """Buscar proveedores por nombre o documento"""
        try:
            query = kwargs.get('query', '').strip()
            if not query:
                return {
                    'success': False,
                    'error': 'Debe proporcionar un término de búsqueda'
                }

            proveedores = Proveedor.objects.filter(
                Q(razon_social__icontains=query) |
                Q(ruc__icontains=query),
                empresa=self.empresa,
                activo=True
            )[:10]  # Limitar a 10 resultados

            resultados = []
            for proveedor in proveedores:
                resultados.append({
                    'id': proveedor.id,
                    'razon_social': proveedor.razon_social,
                    'ruc': proveedor.ruc,
                    'direccion': proveedor.direccion or 'N/A',
                    'telefono': proveedor.telefono or 'N/A',
                    'email': proveedor.email or 'N/A'
                })

            return {
                'success': True,
                'proveedores': resultados,
                'total_encontrados': len(resultados)
            }

        except Exception as e:
            return {
                'success': False,
                'error': f'Error en búsqueda: {str(e)}'
            }

    def buscar_almacenes(self, **kwargs):
        """Buscar almacenes por nombre o dirección"""
        try:
            query = kwargs.get('query', '').strip()
            if not query:
                return {
                    'success': False,
                    'error': 'Debe proporcionar un término de búsqueda'
                }

            almacenes = Almacen.objects.filter(
                Q(nombre__icontains=query) |
                Q(direccion__icontains=query),
                empresa=self.empresa,
                is_active=True
            )[:10]  # Limitar a 10 resultados

            resultados = []
            for almacen in almacenes:
                resultados.append({
                    'id': almacen.id,
                    'nombre': almacen.nombre,
                    'direccion': almacen.direccion or 'N/A',
                    'telefono': almacen.telefono or 'N/A',
                    'encargado': almacen.encargado or 'N/A'
                })

            return {
                'success': True,
                'almacenes': resultados,
                'total_encontrados': len(resultados)
            }

        except Exception as e:
            return {
                'success': False,
                'error': f'Error en búsqueda: {str(e)}'
            } 