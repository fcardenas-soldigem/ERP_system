import json
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from django.db.models import Q
from apps.ventas.models import Venta, DetalleVenta, Cliente
from apps.ventas.serializers import VentaSerializer
from apps.compras.models import Compra, CompraDetalle, Proveedor
from apps.compras.serializers import CompraSerializer
from apps.inventario.models import Producto, Almacen
from ..tools.erp_tools import CrearVentaParams, CrearCompraParams, BuscarProductosParams, BuscarClientesParams

class FunctionExecutor:
    """
    Ejecutor de funciones para el asistente IA
    Maneja la creación de ventas y compras usando la infraestructura existente
    """
    
    def __init__(self, user):
        self.user = user
        self.empresa = user.empresa
        if not self.empresa:
            raise ValueError("El usuario no tiene una empresa asignada")

    @transaction.atomic
    def crear_venta(self, params_dict):
        """Ejecutar creación de venta usando VentaSerializer"""
        try:
            
            # Crear objeto Pydantic para validación
            params = CrearVentaParams(**params_dict)
            
            # Validar que el cliente existe y pertenece a la empresa
            try:
                cliente = Cliente.objects.get(id=params.cliente_id, empresa=self.empresa)
            except Cliente.DoesNotExist:
                return {
                    'success': False,
                    'error': f'Cliente con ID {params.cliente_id} no encontrado en la empresa'
                }
            
            # Validar productos y calcular stock disponible
            productos_validados = []
            total_estimado = Decimal('0')
            
            for producto_data in params.productos:
                try:
                    producto = Producto.objects.get(
                        sku=producto_data.producto_sku, 
                        empresa=self.empresa,
                        is_active=True
                    )
                    
                    # Verificar stock disponible
                    stock_actual = producto.get_stock_total()
                    if stock_actual < producto_data.cantidad:
                        return {
                            'success': False,
                            'error': f'Stock insuficiente para {producto.nombre}. Disponible: {stock_actual}, Solicitado: {producto_data.cantidad}'
                        }
                    
                    productos_validados.append({
                        'producto': producto,
                        'cantidad': producto_data.cantidad,
                        'precio_unitario': producto_data.precio_unitario
                    })
                    
                    # Calcular total estimado
                    subtotal_producto = Decimal(str(producto_data.cantidad)) * Decimal(str(producto_data.precio_unitario))
                    total_estimado += subtotal_producto
                    
                    
                except Producto.DoesNotExist:
                    return {
                        'success': False,
                        'error': f'Producto con SKU "{producto_data.producto_sku}" no encontrado o inactivo'
                    }
            
            # Preparar datos para VentaSerializer
            detalles_data = []
            for item in productos_validados:
                detalles_data.append({
                    'producto': item['producto'].id,
                    'cantidad': item['cantidad'],
                    'precio_unitario': float(item['precio_unitario'])
                })
            
            venta_data = {
                'cliente_id': params.cliente_id,
                'fecha_emision': timezone.now().date(),
                'estado': 'pendiente',  # Siempre inicia como pendiente
                'tipo_venta': params.tipo_venta,
                'metodo_pago': params.metodo_pago,
                'igv_incluido': params.igv_incluido,
                'notas': params.notas or ''
                # NO incluir 'detalles' aquí - los pasaremos por separado
            }
            
            
            # Crear mock request para el serializer
            class MockRequest:
                def __init__(self, user):
                    self.user = user
            
            # Preparar datos completos incluyendo detalles
            # El VentaSerializer NECESITA detalles para funcionar correctamente
            datos_completos = venta_data.copy()
            datos_completos['detalles'] = detalles_data
            
            # Crear usando VentaSerializer existente con datos completos
            context = {'request': MockRequest(self.user)}
            serializer = VentaSerializer(data=datos_completos, context=context)
            
            if serializer.is_valid():
                venta = serializer.save()
                
                # El serializer ya maneja:
                # - Actualización de totales
                # - Actualización de stock (resta productos vendidos)
                # - Generación de número de venta
                
                
                return {
                    'success': True,
                    'venta_id': venta.id,
                    'numero': venta.numero,
                    'cliente': cliente.nombre,
                    'subtotal': float(venta.subtotal),
                    'igv': float(venta.igv),
                    'total': float(venta.total),
                    'estado': venta.estado,
                    'tipo_venta': venta.get_tipo_venta_display() if hasattr(venta, 'get_tipo_venta_display') else venta.tipo_venta,
                    'productos_vendidos': len(detalles_data),
                    'mensaje': f'✅ Venta {venta.numero} creada exitosamente para {cliente.nombre} por S/ {venta.total}. Stock actualizado automáticamente.'
                }
            else:
                return {
                    'success': False,
                    'error': f'Error de validación: {serializer.errors}'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'Error inesperado al crear venta: {str(e)}'
            }

    @transaction.atomic
    def crear_compra(self, params_dict):
        """Ejecutar creación de compra usando CompraSerializer"""
        try:
            
            # Crear objeto Pydantic para validación
            params = CrearCompraParams(**params_dict)
            
            # Validar que el proveedor existe y pertenece a la empresa
            try:
                proveedor = Proveedor.objects.get(id=params.proveedor_id, empresa=self.empresa)
            except Proveedor.DoesNotExist:
                return {
                    'success': False,
                    'error': f'Proveedor con ID {params.proveedor_id} no encontrado en la empresa'
                }
            
            # Validar que el almacén existe y pertenece a la empresa
            try:
                almacen = Almacen.objects.get(id=params.almacen_id, empresa=self.empresa)
            except Almacen.DoesNotExist:
                return {
                    'success': False,
                    'error': f'Almacén con ID {params.almacen_id} no encontrado en la empresa'
                }
            
            # Validar productos
            productos_validados = []
            total_estimado = Decimal('0')
            
            for producto_data in params.productos:
                try:
                    producto = Producto.objects.get(
                        sku=producto_data.producto_sku, 
                        empresa=self.empresa,
                        is_active=True
                    )
                    
                    productos_validados.append({
                        'producto': producto,
                        'cantidad': producto_data.cantidad,
                        'precio_unitario': producto_data.precio_unitario
                    })
                    
                    # Calcular total estimado
                    subtotal_producto = Decimal(str(producto_data.cantidad)) * Decimal(str(producto_data.precio_unitario))
                    total_estimado += subtotal_producto
                    
                    
                except Producto.DoesNotExist:
                    return {
                        'success': False,
                        'error': f'Producto con SKU "{producto_data.producto_sku}" no encontrado o inactivo'
                    }
            
            # Preparar datos para CompraSerializer
            detalles_data = []
            for item in productos_validados:
                detalles_data.append({
                    'producto': item['producto'].id,
                    'cantidad': item['cantidad'],
                    'precio_unitario': float(item['precio_unitario'])
                })
            
            compra_data = {
                'proveedor': params.proveedor_id,
                'almacen': params.almacen_id,
                'fecha_emision': timezone.now().date(),
                'tipo_compra': params.tipo_compra,
                'estado': 'pendiente',  # Siempre inicia como pendiente
                'metodo_pago': params.metodo_pago,
                'igv_incluido': params.igv_incluido,
                'detalles': detalles_data  # CompraSerializer maneja esto correctamente con pop()
            }
            
            
            # Crear mock request para el serializer
            class MockRequest:
                def __init__(self, user):
                    self.user = user
            
            # Crear usando CompraSerializer existente
            context = {'request': MockRequest(self.user)}
            serializer = CompraSerializer(data=compra_data, context=context)
            
            if serializer.is_valid():
                compra = serializer.save(empresa=self.empresa)
                
                # El serializer ya maneja:
                # - Actualización de totales  
                # - Actualización de stock (suma productos comprados) si estado = 'pagada' o 'pendiente'
                # - Generación de número de compra
                
                
                return {
                    'success': True,
                    'compra_id': compra.id,
                    'numero': compra.numero,
                    'proveedor': proveedor.razon_social,
                    'almacen': almacen.nombre,
                    'subtotal': float(compra.subtotal),
                    'igv': float(compra.igv),
                    'total': float(compra.total),
                    'estado': compra.estado,
                    'tipo_compra': compra.get_tipo_compra_display() if hasattr(compra, 'get_tipo_compra_display') else compra.tipo_compra,
                    'productos_comprados': len(detalles_data),
                    'mensaje': f'✅ Compra {compra.numero} creada exitosamente a {proveedor.razon_social} por S/ {compra.total}. Stock actualizado automáticamente.'
                }
            else:
                return {
                    'success': False,
                    'error': f'Error de validación: {serializer.errors}'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'Error inesperado al crear compra: {str(e)}'
            }

    def buscar_productos(self, params_dict):
        """Buscar productos por nombre, descripción o SKU"""
        try:
            params = BuscarProductosParams(**params_dict)
            termino = params.termino_busqueda.strip()
            
            
            # Buscar productos por nombre, descripción o SKU
            productos = Producto.objects.filter(
                Q(nombre__icontains=termino) |
                Q(descripcion__icontains=termino) |
                Q(sku__icontains=termino),
                empresa=self.empresa,
                is_active=True
            ).order_by('nombre')[:params.limite]
            
            if not productos:
                return {
                    'success': True,
                    'productos': [],
                    'mensaje': f'No se encontraron productos que coincidan con "{termino}"'
                }
            
            productos_info = []
            for producto in productos:
                stock_total = producto.get_stock_total()
                productos_info.append({
                    'sku': producto.sku,
                    'nombre': producto.nombre,
                    'descripcion': producto.descripcion or '',
                    'precio_venta': float(producto.precio_venta) if producto.precio_venta else 0.0,
                    'stock_total': stock_total,
                    'unidad_medida': getattr(producto, 'unidad_medida', 'unidad')
                })
            
            
            return {
                'success': True,
                'productos': productos_info,
                'total_encontrados': len(productos_info),
                'mensaje': f'Se encontraron {len(productos_info)} productos que coinciden con "{termino}"'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Error al buscar productos: {str(e)}'
            }

    def execute_function(self, function_name, arguments):
        """Ejecutar función según el nombre"""
        
        if function_name == "crear_venta":
            return self.crear_venta(arguments)
        elif function_name == "crear_compra":
            return self.crear_compra(arguments)
        elif function_name == "buscar_productos":
            return self.buscar_productos(arguments)
        else:
            return {
                'success': False,
                'error': f'Función {function_name} no reconocida. Funciones disponibles: crear_venta, crear_compra, buscar_productos'
            } 