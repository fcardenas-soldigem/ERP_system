from django.db.models import Q, Sum, Count, Avg
from django.utils import timezone
from datetime import datetime, timedelta
from apps.ventas.models import Venta, Cliente
from apps.inventario.models import Producto, Stock
from apps.compras.models import Compra

class AnalistaExecutor:
    def __init__(self, user):
        self.user = user
        self.empresa = user.empresa

    def execute_function(self, function_name, arguments):
        """Ejecutar función de análisis"""
        if function_name == 'analizar_ventas':
            return self.analizar_ventas(**arguments)
        elif function_name == 'analizar_inventario':
            return self.analizar_inventario(**arguments)
        elif function_name == 'analizar_clientes':
            return self.analizar_clientes(**arguments)
        elif function_name == 'consulta_libre':
            return self.consulta_libre(**arguments)
        else:
            return {
                'success': False,
                'error': f'Función {function_name} no reconocida para análisis'
            }

    def analizar_ventas(self, **kwargs):
        """Analizar performance de ventas"""
        try:
            periodo = kwargs.get('periodo', 'mes')
            fecha_inicio = kwargs.get('fecha_inicio')
            fecha_fin = kwargs.get('fecha_fin')
            
            # Definir período si no se especifican fechas
            if not fecha_inicio or not fecha_fin:
                ahora = timezone.now()
                if periodo == 'semana':
                    fecha_inicio = ahora - timedelta(days=7)
                elif periodo == 'mes':
                    fecha_inicio = ahora - timedelta(days=30)
                elif periodo == 'trimestre':
                    fecha_inicio = ahora - timedelta(days=90)
                elif periodo == 'año':
                    fecha_inicio = ahora - timedelta(days=365)
                else:
                    fecha_inicio = ahora - timedelta(days=30)
                fecha_fin = ahora
            else:
                fecha_inicio = datetime.strptime(fecha_inicio, '%Y-%m-%d')
                fecha_fin = datetime.strptime(fecha_fin, '%Y-%m-%d')

            # Obtener ventas del período
            ventas = Venta.objects.filter(
                empresa=self.empresa,
                fecha_emision__range=[fecha_inicio, fecha_fin],
                estado__in=['pendiente', 'pagado', 'completado']
            )

            # Calcular métricas
            total_ventas = ventas.count()
            monto_total = ventas.aggregate(total=Sum('total'))['total'] or 0
            promedio_venta = ventas.aggregate(promedio=Avg('total'))['promedio'] or 0
            
            # Top productos vendidos
            from apps.ventas.models import DetalleVenta
            top_productos = DetalleVenta.objects.filter(
                venta__in=ventas
            ).values(
                'producto__nombre', 'producto__sku'
            ).annotate(
                cantidad_total=Sum('cantidad'),
                ingresos=Sum('subtotal')
            ).order_by('-cantidad_total')[:5]

            # Ventas por día (últimos 7 días)
            ventas_por_dia = []
            for i in range(7):
                fecha = timezone.now().date() - timedelta(days=i)
                ventas_dia = ventas.filter(fecha_emision=fecha).aggregate(
                    total=Sum('total'), count=Count('id')
                )
                ventas_por_dia.append({
                    'fecha': fecha.strftime('%Y-%m-%d'),
                    'total': float(ventas_dia['total'] or 0),
                    'cantidad': ventas_dia['count']
                })
            
            return {
                'success': True,
                'periodo': periodo,
                'fecha_inicio': fecha_inicio.strftime('%Y-%m-%d'),
                'fecha_fin': fecha_fin.strftime('%Y-%m-%d'),
                'metricas': {
                    'total_ventas': total_ventas,
                    'monto_total': float(monto_total),
                    'promedio_venta': float(promedio_venta),
                },
                'top_productos': list(top_productos),
                'ventas_por_dia': ventas_por_dia,
                'mensaje': f'📊 Análisis de ventas del {periodo}: {total_ventas} ventas por S/ {monto_total:,.2f}'
            }

        except Exception as e:
            return {
                'success': False,
                'error': f'Error analizando ventas: {str(e)}'
            }

    def analizar_inventario(self, **kwargs):
        """Analizar estado del inventario"""
        try:
            categoria = kwargs.get('categoria')
            stock_minimo = kwargs.get('stock_minimo', 10)

            # Filtrar productos
            productos = Producto.objects.filter(empresa=self.empresa)
            if categoria:
                productos = productos.filter(categoria__icontains=categoria)

            # Productos con stock bajo
            productos_bajo_stock = []
            for producto in productos:
                stock_actual = producto.get_stock()
                if stock_actual < stock_minimo:
                    productos_bajo_stock.append({
                        'sku': producto.sku,
                        'nombre': producto.nombre,
                        'stock_actual': float(stock_actual),
                        'stock_minimo': stock_minimo,
                        'categoria': getattr(producto, 'categoria', 'Sin categoría')
                    })

            # Total productos
            total_productos = productos.count()
            productos_sin_stock = productos.filter(
                stocks__cantidad=0
            ).distinct().count()

            # Valor total del inventario
            valor_inventario = 0
            for producto in productos:
                stock = producto.get_stock()
                precio = producto.precio_venta or 0
                valor_inventario += stock * precio

            return {
                'success': True,
                'metricas': {
                    'total_productos': total_productos,
                    'productos_bajo_stock': len(productos_bajo_stock),
                    'productos_sin_stock': productos_sin_stock,
                    'valor_inventario': float(valor_inventario)
                },
                'productos_bajo_stock': productos_bajo_stock[:10],  # Top 10
                'stock_minimo_filtro': stock_minimo,
                'categoria_filtro': categoria,
                'mensaje': f'📦 Análisis de inventario: {len(productos_bajo_stock)} productos con stock bajo (< {stock_minimo})'
            }

        except Exception as e:
            return {
                'success': False,
                'error': f'Error analizando inventario: {str(e)}'
            }

    def analizar_clientes(self, **kwargs):
        """Analizar comportamiento de clientes"""
        try:
            periodo = kwargs.get('periodo', 'mes')
            top_clientes = kwargs.get('top_clientes', 10)

            # Definir período
            ahora = timezone.now()
            if periodo == 'semana':
                fecha_inicio = ahora - timedelta(days=7)
            elif periodo == 'mes':
                fecha_inicio = ahora - timedelta(days=30)
            elif periodo == 'trimestre':
                fecha_inicio = ahora - timedelta(days=90)
            elif periodo == 'año':
                fecha_inicio = ahora - timedelta(days=365)
            else:
                fecha_inicio = ahora - timedelta(days=30)

            # Top clientes por monto
            clientes_por_monto = Cliente.objects.filter(
                empresa=self.empresa,
                ventas__fecha_emision__gte=fecha_inicio
            ).annotate(
                total_compras=Sum('ventas__total'),
                num_ventas=Count('ventas')
            ).order_by('-total_compras')[:top_clientes]

            # Top clientes por frecuencia
            clientes_por_frecuencia = Cliente.objects.filter(
                empresa=self.empresa,
                ventas__fecha_emision__gte=fecha_inicio
            ).annotate(
                num_ventas=Count('ventas'),
                total_compras=Sum('ventas__total')
            ).order_by('-num_ventas')[:top_clientes]

            # Nuevos clientes
            nuevos_clientes = Cliente.objects.filter(
                empresa=self.empresa,
                fecha_registro__gte=fecha_inicio
            ).count()

            # Clientes activos
            clientes_activos = Cliente.objects.filter(
                empresa=self.empresa,
                ventas__fecha_emision__gte=fecha_inicio
            ).distinct().count()

            return {
                'success': True,
                'periodo': periodo,
                'metricas': {
                    'nuevos_clientes': nuevos_clientes,
                    'clientes_activos': clientes_activos,
                    'total_clientes': Cliente.objects.filter(empresa=self.empresa).count()
                },
                'top_clientes_monto': [
                    {
                        'nombre': cliente.nombre,
                        'documento': cliente.documento,
                        'total_compras': float(cliente.total_compras or 0),
                        'num_ventas': cliente.num_ventas
                    } for cliente in clientes_por_monto
                ],
                'top_clientes_frecuencia': [
                    {
                        'nombre': cliente.nombre,
                        'documento': cliente.documento,
                        'num_ventas': cliente.num_ventas,
                        'total_compras': float(cliente.total_compras or 0)
                    } for cliente in clientes_por_frecuencia
                ],
                'mensaje': f'👥 Análisis de clientes del {periodo}: {clientes_activos} clientes activos, {nuevos_clientes} nuevos'
            }

        except Exception as e:
            return {
                'success': False,
                'error': f'Error analizando clientes: {str(e)}'
            }

    def consulta_libre(self, **kwargs):
        """Responder consultas libres sobre datos comerciales"""
        try:
            consulta = kwargs.get('consulta', '').lower()
            
            # Métricas básicas para responder
            ahora = timezone.now()
            hace_30_dias = ahora - timedelta(days=30)
            
            # Datos generales
            total_ventas_mes = Venta.objects.filter(
                empresa=self.empresa,
                fecha_emision__gte=hace_30_dias
            ).aggregate(
                count=Count('id'),
                total=Sum('total')
            )
            
            total_productos = Producto.objects.filter(empresa=self.empresa).count()
            total_clientes = Cliente.objects.filter(empresa=self.empresa).count()
            
            # Productos más vendidos
            from apps.ventas.models import DetalleVenta
            producto_top = DetalleVenta.objects.filter(
                venta__empresa=self.empresa,
                venta__fecha_emision__gte=hace_30_dias
            ).values('producto__nombre').annotate(
                total_vendido=Sum('cantidad')
            ).order_by('-total_vendido').first()

            respuesta_contextual = ""
            
            # Generar respuesta según el tipo de consulta
            if any(palabra in consulta for palabra in ['ventas', 'vender', 'ingresos', 'facturación']):
                respuesta_contextual = f"""
📊 **Resumen de Ventas (últimos 30 días):**
• Total ventas: {total_ventas_mes['count']} por S/ {total_ventas_mes['total'] or 0:,.2f}
• Promedio por venta: S/ {(total_ventas_mes['total'] or 0) / max(total_ventas_mes['count'], 1):,.2f}
• Producto más vendido: {producto_top['producto__nombre'] if producto_top else 'N/A'}
"""
            elif any(palabra in consulta for palabra in ['productos', 'inventario', 'stock']):
                productos_bajo_stock = 0
                for producto in Producto.objects.filter(empresa=self.empresa):
                    if producto.get_stock() < 10:
                        productos_bajo_stock += 1
                        
                respuesta_contextual = f"""
📦 **Estado del Inventario:**
• Total productos: {total_productos}
• Productos con stock bajo (<10): {productos_bajo_stock}
• Necesita revisión de stock para reposición
"""
            elif any(palabra in consulta for palabra in ['clientes', 'compradores']):
                clientes_activos = Cliente.objects.filter(
                    empresa=self.empresa,
                    ventas__fecha_emision__gte=hace_30_dias
                ).distinct().count()
                
                respuesta_contextual = f"""
👥 **Análisis de Clientes:**
• Total clientes: {total_clientes}
• Clientes activos (últimos 30 días): {clientes_activos}
• Tasa de actividad: {(clientes_activos/max(total_clientes,1)*100):.1f}%
"""
            else:
                respuesta_contextual = f"""
📈 **Resumen General del Negocio:**
• Ventas del mes: {total_ventas_mes['count']} por S/ {total_ventas_mes['total'] or 0:,.2f}
• Total productos: {total_productos}
• Total clientes: {total_clientes}

¿Te gustaría que profundice en algún área específica?
"""

            return {
                'success': True,
                'consulta_original': kwargs.get('consulta'),
                'respuesta': respuesta_contextual.strip(),
                'datos_contexto': {
                    'ventas_mes': total_ventas_mes,
                    'total_productos': total_productos,
                    'total_clientes': total_clientes,
                    'producto_top': producto_top
                },
                'mensaje': '🤖 Consulta procesada exitosamente'
            }

        except Exception as e:
            return {
                'success': False,
                'error': f'Error procesando consulta: {str(e)}'
            } 